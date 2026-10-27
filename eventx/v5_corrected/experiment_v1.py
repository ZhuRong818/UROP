"""V5 method-v1 integration; no file loading, holdout access or implicit label opening.

Caller must supply source-certified PIT records and a predeclared fold schedule.
This module does not authorize dataset admission or replace a consumption receipt.
"""

from dataclasses import dataclass
import hashlib

import numpy as np

from eventx.features.v5_market import MARKET_FEATURE_NAMES, NONLINEAR_COLUMNS
from .matched_controls_v1 import matched_matrices
from .offset import OffsetLogistic
from .pipeline import market_model, fit_base, predict_base
from .splits import Fold

ARMS = ("context", "timing", "timing_matched", "news")
BASE_C = (.001, .01, .1)
# Ordered tie policy: smaller kappa, larger lambda, larger alpha.
GRID = tuple((lam, alpha, kappa) for kappa in (0., .25, .5, 1.)
             for lam in (1., .1, .01) for alpha in (.5, 0.))


def ll(y, p):
    p = np.clip(np.asarray(p, float), 1e-12, 1-1e-12)
    return -(y*np.log(p)+(1-y)*np.log1p(-p))


def family_groups(families):
    ordered = sorted(set(families), key=lambda f: hashlib.sha256(
        ("v5r-family-v1|"+f).encode()).digest())
    return tuple(frozenset(ordered[i::5]) for i in range(5))


def crossed_folds(families, windows):
    if len(windows) != 5 or any(a >= b for a, b in windows):
        raise ValueError("Exactly five nonempty outer windows required")
    if any(windows[i][1] > windows[i+1][0] for i in range(4)):
        raise ValueError("Outer time windows must be ordered and disjoint")
    groups = family_groups(families)
    if any(not group for group in groups):
        raise ValueError("Five nonempty family groups required")
    return tuple(Fold(f"time{t}/family{g}", start, end, group)
                 for t, (start, end) in enumerate(windows)
                 for g, group in enumerate(groups))


@dataclass
class Batch:
    market: np.ndarray
    news: np.ndarray
    exposed: np.ndarray

    def matrices(self, p0):
        return matched_matrices(self.market, MARKET_FEATURE_NAMES, p0, self.exposed,
                                self.news[:, 2], self.news[:, 3],
                                self.news[:, 0], self.news[:, 1])


class NamedPITSource:
    """Adapt the existing raw PIT reference to canonical named market/control inputs."""
    def __init__(self, source, decision_feature_names):
        self.source, self.index = source, source.index
        self.names = tuple(decision_feature_names) + (
            "log1p_minutes_to_scheduled_terminal", "terminal_unknown")
        if (source.residual_kind != "news" or len(set(self.names)) != 15
                or set(self.names) != set(MARKET_FEATURE_NAMES)
                or any(len(d.market_values) != 13 for d in source.decisions)):
            raise ValueError("Require named 13 decision inputs plus PIT terminal fields")

    def fit(self, train):
        fitted = self.source.fit(train)
        order = [self.names.index(n) for n in MARKET_FEATURE_NAMES]

        class Features:
            provenance = fitted.provenance

            def transform(self, ids):
                batch = fitted.transform(ids)
                return Batch(batch.market[:, order], batch.residual[:, -5:], batch.exposed)

        return Features()


@dataclass
class Bundle:
    features: object
    base: object
    residuals: dict
    selections: dict
    oof_ids: np.ndarray
    oof_p0: np.ndarray
    diagnostics: dict

    def predict(self, ids):
        batch = self.features.transform(ids)
        p0 = predict_base(self.base, batch.market)
        matrices = batch.matrices(p0)
        result = {"nonlinear": p0}
        for arm, model in self.residuals.items():
            result[arm] = model.predict(matrices[arm], p0, batch.exposed,
                                        self.selections[arm][2])
            if not np.array_equal(result[arm][~batch.exposed], p0[~batch.exposed]):
                raise AssertionError("Exact unexposed equality failed")
        return result


class ExperimentTrainer:
    """One immutable source/label scope per trainer; caches never cross experiments.

    Base regularization is selected inside *each* OOF training scope. Meta tuning
    fits fresh OOF stacks inside its training scopes. Only explicitly indexed
    training/tuning labels are accessed, never outer labels (which may be NaN).
    """
    def __init__(self, source, labels, base_folds, oof_folds):
        self.source, self.index, self.labels = source, source.index, labels
        self.base_folds, self.oof_folds = tuple(base_folds), tuple(oof_folds)
        self.ledger, self.base_cache, self.context_cache = [], {}, {}

    def y(self, ids):
        y = np.asarray(self.labels[ids], float)
        if y.shape != (len(ids),) or not np.isin(y, [0, 1]).all():
            raise ValueError("Required training labels missing/nonbinary")
        self.ledger.append({"stage": "labels_accessed", "ids": ids.tolist()})
        return y

    def partitions(self, parent, folds):
        result = list(self.index.available_folds(parent, folds))
        if not result:
            raise ValueError("No structurally usable nested folds; no in-sample fallback")
        seen = set()
        for fold, train, valid in result:
            if seen.intersection(map(int, valid)):
                raise ValueError("Overlapping nested validation rows")
            seen.update(map(int, valid))
            self.ledger.append({"stage": "split", "fold": fold.name,
                                "parent": np.asarray(parent).tolist(), "train": train.tolist(),
                                "valid": valid.tolist()})
        return result

    def selected_base(self, parent, kind="spline"):
        key = (kind, tuple(map(int, parent)))
        if key in self.base_cache:
            return self.base_cache[key]
        scores = np.zeros(len(BASE_C))
        count = 0
        for _, train, valid in self.partitions(parent, self.base_folds):
            features = self.source.fit(train)
            xt, xv = features.transform(train).market, features.transform(valid).market
            yt, yv = self.y(train), self.y(valid)
            for j, c in enumerate(BASE_C):
                model = fit_base(market_model(kind, c, NONLINEAR_COLUMNS), xt, yt)
                scores[j] += ll(yv, predict_base(model, xv)).sum()
            count += len(valid)
        selected = BASE_C[int(np.argmin(scores))]
        features = self.source.fit(parent)
        model = fit_base(market_model(kind, selected, NONLINEAR_COLUMNS),
                         features.transform(parent).market, self.y(parent))
        self.ledger.append({"stage": "base_selection", "kind": kind,
                            "parent": np.asarray(parent).tolist(), "C": selected,
                            "inner_losses": (scores/count).tolist(),
                            "feature_provenance": features.provenance})
        self.base_cache[key] = features, model
        return features, model

    def context(self, parent):
        key = tuple(map(int, parent))
        if key in self.context_cache:
            return self.context_cache[key]
        scores = {}
        for _, train, valid in self.partitions(parent, self.oof_folds):
            features, base = self.selected_base(train)
            p = predict_base(base, features.transform(valid).market)
            scores.update(zip(map(int, valid), map(float, p)))
        ids = np.array(sorted(scores), dtype=int)
        p0 = np.array([scores[int(i)] for i in ids])
        features, base = self.selected_base(parent)
        batch = features.transform(ids)
        result = (features, base, ids, p0, batch, batch.matrices(p0))
        self.context_cache[key] = result
        return result

    def fit_models(self, parent, specifications):
        features, base, ids, p0, batch, matrices = self.context(parent)
        y = self.y(ids)
        models, diagnostics = {}, {}
        for arm, (lam, alpha, _) in specifications.items():
            if arm not in ARMS:
                raise ValueError("Unknown residual arm")
            model = OffsetLogistic(l1=lam*alpha, l2=lam*(1-alpha)).fit(
                matrices[arm], y, p0, batch.exposed)
            models[arm] = model
            x = matrices[arm][batch.exposed]
            diagnostics[arm] = {"columns": x.shape[1], "exposed_rows": len(x),
                "rank": int(np.linalg.matrix_rank(x)) if len(x) else 0,
                "constant_columns": np.flatnonzero(np.ptp(x, axis=0) == 0).tolist() if len(x) else [],
                "coefficient_norm": float(np.linalg.norm(model.coef_)),
                "kkt_residual": model.kkt_residual_, "solver_status": model.status_}
        diagnostics["excluded_no_oof_ids"] = np.setdiff1d(parent, ids).tolist()
        return Bundle(features, base, models, specifications, ids, p0, diagnostics)

    def fit_outer(self, outer, tuning_folds):
        parent, valid = self.index.split(np.arange(len(self.index.decision)), outer)
        losses = {arm: np.zeros(len(GRID)) for arm in ARMS}
        count = 0
        for _, train, inner_valid in self.partitions(parent, tuning_folds):
            yv = self.y(inner_valid)
            # kappa only changes prediction; solve the six penalized models once.
            for lam in (1., .1, .01):
                for alpha in (.5, 0.):
                    bundle = self.fit_models(train, {a: (lam, alpha, 1.) for a in ARMS})
                    batch = bundle.features.transform(inner_valid)
                    p0 = predict_base(bundle.base, batch.market)
                    matrices = batch.matrices(p0)
                    for j, spec in enumerate(GRID):
                        if spec[:2] != (lam, alpha):
                            continue
                        for arm in ARMS:
                            p = bundle.residuals[arm].predict(matrices[arm], p0, batch.exposed, spec[2])
                            losses[arm][j] += ll(yv, p).sum()
            count += len(inner_valid)
        selected = {a: GRID[int(np.argmin(losses[a]))] for a in ARMS}
        bundle = self.fit_models(parent, selected)
        linear_features, linear = self.selected_base(parent, "linear")
        predictions = bundle.predict(valid)
        predictions["linear"] = predict_base(linear, linear_features.transform(valid).market)
        return bundle, valid, predictions, {"selected": selected,
            "inner_losses": {a: (losses[a]/count).tolist() for a in ARMS},
            "outer_labels_read": False}
