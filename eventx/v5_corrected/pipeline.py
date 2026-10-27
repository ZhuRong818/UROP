"""Nested forward/family cross-fitting with exposed-only fixed-offset stacking.

No legacy predictions are accepted. A fitted stack keeps OOF scores for residual
training and refits its deployment base on the complete permitted training scope.
"""

from dataclasses import dataclass
import warnings

import numpy as np
from scipy.special import logit
from sklearn.compose import ColumnTransformer
from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.exceptions import ConvergenceWarning
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import SplineTransformer, StandardScaler
from threadpoolctl import threadpool_limits

from .offset import OffsetLogistic, probabilities


def market_model(kind="linear", regularization=1.0, nonlinear_columns=None):
    """Fresh models only; shallow trees retained as an unpromoted benchmark."""
    logistic = LogisticRegression(C=regularization, max_iter=2000, tol=1e-8)
    if kind == "linear":
        return make_pipeline(StandardScaler(), logistic)
    if kind == "spline":
        if nonlinear_columns is None or not len(nonlinear_columns):
            raise ValueError("Specify the frozen nonlinear column set; never spline every input implicitly")
        basis = ColumnTransformer([
            ("nonlinear", SplineTransformer(n_knots=4, degree=2, include_bias=False,
                                            extrapolation="linear"), list(nonlinear_columns))],
            remainder="passthrough")
        return make_pipeline(basis,
                             StandardScaler(), logistic)
    if kind == "shallow_tree":
        return HistGradientBoostingClassifier(
            max_iter=100, max_depth=3, max_leaf_nodes=7, min_samples_leaf=100,
            l2_regularization=10, learning_rate=.05, early_stopping=False, random_state=907)
    raise ValueError(f"Unknown market benchmark: {kind}")


def fit_base(model, x, y):
    if len(np.unique(y)) != 2:
        raise ValueError("Base training partition needs both labels")
    with warnings.catch_warnings(), threadpool_limits(limits=2):
        warnings.simplefilter("error", ConvergenceWarning)
        model.fit(x, y)
    return model


def predict_base(model, x):
    with threadpool_limits(limits=2):
        return probabilities(model.predict_proba(x)[:, 1])


def residual_matrix(batch, p0):
    return np.column_stack([batch.residual, p0, logit(probabilities(p0))])


@dataclass(frozen=True)
class Candidate:
    l1: float
    l2: float
    kappa: float


@dataclass
class FittedStack:
    features: object
    base: object
    residual: OffsetLogistic
    candidate: Candidate
    oof_ids: np.ndarray
    oof_p0: np.ndarray
    excluded_warmup_ids: np.ndarray

    def predict(self, ids):
        batch = self.features.transform(ids)
        p0 = predict_base(self.base, batch.market)
        prediction = self.residual.predict(
            residual_matrix(batch, p0), p0, batch.exposed, self.candidate.kappa)
        if not np.array_equal(prediction[~batch.exposed], p0[~batch.exposed]):
            raise AssertionError("Unexposed equality invariant failed")
        return p0, prediction


class NestedOffsetTrainer:
    def __init__(self, source, labels, base_factory, crossfit_folds):
        self.source, self.index = source, source.index
        self.labels = np.asarray(labels)
        if self.labels.shape != self.index.decision.shape or not np.isin(self.labels, [0, 1]).all():
            raise ValueError("Aligned binary training labels required")
        self.base_factory = base_factory
        self.crossfit_folds = tuple(crossfit_folds)
        self.ledger = []

    def _record(self, stage, parent, train, valid, features):
        self.ledger.append({
            "stage": stage,
            "parent_ids": np.asarray(parent).tolist(), "train_ids": np.asarray(train).tolist(),
            "valid_ids": np.asarray(valid).tolist(),
            "train_families": sorted(set(self.index.family[train])),
            "valid_families": sorted(set(self.index.family[valid])),
            "max_train_label_end": int(self.index.label_end[train].max()),
            "feature_provenance": features.provenance,
        })

    def crossfit(self, parent, stage):
        scores = {}
        for fold, train, valid in self.index.available_folds(parent, self.crossfit_folds):
            if any(int(i) in scores for i in valid):
                raise ValueError("Overlapping OOF validation rows; freeze a disjoint schedule")
            features = self.source.fit(train)
            base = fit_base(self.base_factory(), features.transform(train).market, self.labels[train])
            p0 = predict_base(base, features.transform(valid).market)
            scores.update(zip(map(int, valid), map(float, p0)))
            self._record(f"{stage}/base_oof/{fold.name}", parent, train, valid, features)
        if not scores:
            raise ValueError("No honest base OOF rows inside this training partition")
        ids = np.array(sorted(scores), dtype=int)
        return ids, np.array([scores[int(i)] for i in ids])

    def fit_stack(self, parent, candidate, stage="final"):
        if not 0 <= candidate.kappa <= 1:
            raise ValueError("Invalid shrinkage")
        parent = np.asarray(parent, dtype=int)
        oof_ids, oof_p0 = self.crossfit(parent, stage)
        features = self.source.fit(parent)
        batch = features.transform(oof_ids)
        residual = OffsetLogistic(l1=candidate.l1, l2=candidate.l2).fit(
            residual_matrix(batch, oof_p0), self.labels[oof_ids], oof_p0, batch.exposed)
        # Never replace oof_p0 with predictions of this all-parent deployment fit.
        base = fit_base(self.base_factory(), features.transform(parent).market, self.labels[parent])
        self._record(f"{stage}/deployment_base", parent, parent, np.array([], dtype=int), features)
        excluded = np.setdiff1d(parent, oof_ids)
        self.ledger.append({"stage": f"{stage}/offset", "train_ids": oof_ids.tolist(),
                            "excluded_no_oof_ids": excluded.tolist(),
                            "n_exposed": residual.n_exposed_, "solver": residual.status_,
                            "iterations": residual.n_iter_, "kkt_residual": residual.kkt_residual_})
        return FittedStack(features, base, residual, candidate, oof_ids, oof_p0, excluded)

    def fit_outer(self, outer_fold, tuning_folds, candidates):
        """Inner losses choose the supplied grid; outer labels are never scored."""
        all_ids = np.arange(len(self.labels))
        outer_train, outer_valid = self.index.split(all_ids, outer_fold)
        candidates = tuple(candidates)
        inner = list(self.index.available_folds(outer_train, tuning_folds))
        if not candidates or not inner:
            raise ValueError("Need a prespecified candidate grid and usable inner folds")
        losses = []
        for number, candidate in enumerate(candidates):
            total, count = 0.0, 0
            seen = set()
            for fold, train, valid in inner:
                if seen.intersection(map(int, valid)):
                    raise ValueError("Overlapping inner validation rows")
                seen.update(map(int, valid))
                stack = self.fit_stack(train, candidate, f"inner/{number}/{fold.name}")
                _, p = stack.predict(valid)
                p = probabilities(p)
                y = self.labels[valid]
                total += float(-(y * np.log(p) + (1-y) * np.log1p(-p)).sum())
                count += len(valid)
                self._record(f"inner/{number}/{fold.name}/validation", outer_train,
                             train, valid, stack.features)
            losses.append(total / count)
        selected = int(np.argmin(losses))  # input grid order breaks exact ties
        final = self.fit_stack(outer_train, candidates[selected], "outer_final")
        self._record("outer_validation", all_ids, outer_train, outer_valid, final.features)
        return final, outer_valid, {"inner_losses": losses, "selected": selected,
                                    "outer_labels_inspected": False}
