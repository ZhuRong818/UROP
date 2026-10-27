"""Broad, bounded method screen on opened observed-news V5 development rows.

Run: .venv/bin/python -m eventx.tasks.screen_v5_observed_news_methods_20261009
This is exploratory model selection, not an independent or protected evaluation.
"""
from __future__ import annotations

import json
import warnings
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import sklearn
from scipy.optimize import minimize
from scipy.special import expit, logit
from sklearn.ensemble import ExtraTreesClassifier, HistGradientBoostingClassifier, RandomForestClassifier
from sklearn.exceptions import ConvergenceWarning
from sklearn.linear_model import LogisticRegression
from sklearn.neural_network import MLPClassifier
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import PolynomialFeatures, SplineTransformer, StandardScaler
from threadpoolctl import threadpool_limits

from eventx.tasks.audit_v5_algorithms import MINUTE_US, START_US, block_interval, recent_news
from eventx.tasks.prepare_v4_discovery_news_quality import EVENT_DTYPE
from eventx.tasks.run_v4_discovery_models import OOF_DTYPE
from eventx.tasks.run_v5_residual_feasibility import (
    EVENT_MANIFEST, EVENTS, FUTURE, OOF, OOF_MANIFEST, REPO_ROOT,
    metric, point_loss, sha256_file, verify_manifest,
)

PARENT = REPO_ROOT / "data/v5/algorithm_audit_20260907"
PREVIOUS = REPO_ROOT / "data/v5/opened_news_offset_trial_20261009"
OUT = REPO_ROOT / "data/v5/observed_news_method_screen_20261009"
TIERS = {
    "context": (0,),
    "timing": tuple(range(7)),
    "semantic": tuple(range(16)),
}
FEATURE_NAMES = (
    "baseline_logit", "log1p_count_30m", "latest_age_over_30m",
    "log1p_count_5m", "log1p_count_15m", "distinct_publishers_30m",
    "max_diffusion_publishers_30m", "max_relevance_30m",
    "mean_relevance_30m", "max_novelty_30m", "mean_novelty_30m",
    "max_relevance_novelty_30m", "mean_relevance_novelty_30m",
    "latest_relevance_novelty", "max_relevance_novelty_15m",
    "latest_relevance",
)
VARIANTS = (
    ("offset_ridge_001", "offset", {"penalty": 0.001, "basis": "linear"}),
    ("offset_ridge_01", "offset", {"penalty": 0.01, "basis": "linear"}),
    ("offset_ridge_1", "offset", {"penalty": 0.1, "basis": "linear"}),
    ("offset_quadratic", "offset", {"penalty": 0.01, "basis": "quadratic"}),
    ("spline_logit", "spline_logit", {"C": 0.1}),
    ("hist_gb_small", "hist_gb", {"max_iter": 100, "max_leaf_nodes": 3, "min_samples_leaf": 50}),
    ("hist_gb_deep", "hist_gb", {"max_iter": 160, "max_leaf_nodes": 7, "min_samples_leaf": 50}),
    ("extra_trees", "extra_trees", {"n_estimators": 200, "max_depth": 6, "min_samples_leaf": 30}),
    ("random_forest", "random_forest", {"n_estimators": 200, "max_depth": 6, "min_samples_leaf": 30}),
    ("small_mlp", "mlp", {"hidden_layer_sizes": [16], "alpha": 0.1, "max_iter": 250}),
)


def write_json(path: Path, value: dict) -> None:
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(value, indent=2, sort_keys=True, allow_nan=False) + "\n")
    temporary.replace(path)


def observed_features(rows: dict, events: np.ndarray, news: np.ndarray) -> np.ndarray:
    """Compute bounded, as-recorded 5/15/30-minute article summaries."""
    exposed = np.flatnonzero(news[:, 0] > 0)
    p0 = rows["tree_no_terminal"]
    matrix = np.zeros((len(exposed), len(FEATURE_NAMES)), dtype=np.float64)
    matrix[:, 0] = logit(np.clip(p0[exposed], 1e-7, 1 - 1e-7))
    matrix[:, 1] = np.log1p(news[exposed, 1])
    matrix[:, 2] = news[exposed, 2] / 30.0
    index_to_output = {int(row): position for position, row in enumerate(exposed)}
    for market in np.unique(rows["market"][exposed]):
        market_rows = exposed[rows["market"][exposed] == market]
        left, right = np.searchsorted(events["market"], [market, market + 1])
        market_events = events[left:right]
        times = market_events["timestamp_us"]
        for row in market_rows:
            t = START_US + int(rows["minute"][row]) * MINUTE_US
            hi = np.searchsorted(times, t, side="right")
            lo30 = np.searchsorted(times, t - 30 * MINUTE_US, side="right")
            lo15 = np.searchsorted(times, t - 15 * MINUTE_US, side="right")
            lo5 = np.searchsorted(times, t - 5 * MINUTE_US, side="right")
            if hi <= lo30:
                raise RuntimeError("Observed-news exposure disagrees with event window")
            ev = market_events[lo30:hi]
            relevance = ev["relevance"].astype(np.float64)
            novelty = ev["novelty"].astype(np.float64)
            product = relevance * novelty
            out = matrix[index_to_output[int(row)]]
            out[3] = np.log1p(hi - lo5)
            out[4] = np.log1p(hi - lo15)
            out[5] = len(np.unique(ev["publisher"]))
            out[6] = np.max(ev["diffusion_publishers"])
            out[7] = relevance.max()
            out[8] = relevance.mean()
            out[9] = novelty.max()
            out[10] = novelty.mean()
            out[11] = product.max()
            out[12] = product.mean()
            out[13] = product[-1]
            out[14] = np.max(product[lo15-lo30:]) if hi > lo15 else 0.0
            out[15] = relevance[-1]
    if not np.all(np.isfinite(matrix)):
        raise RuntimeError("Nonfinite observed-news features")
    return matrix


def fit_offset(
    train_x: np.ndarray, y: np.ndarray, baseline: np.ndarray,
    eval_x: np.ndarray, eval_baseline: np.ndarray, penalty: float, basis: str,
) -> tuple[np.ndarray, dict]:
    mean = train_x.mean(axis=0)
    scale = train_x.std(axis=0)
    scale[scale < 1e-12] = 1.0
    a = (train_x - mean) / scale
    b = (eval_x - mean) / scale
    if basis == "quadratic":
        transform = PolynomialFeatures(degree=2, include_bias=False)
        a = transform.fit_transform(a)
        b = transform.transform(b)
        if a.shape[1] > 150:
            raise RuntimeError("Quadratic feature budget exceeded")
    second_scale = a.std(axis=0)
    second_scale[second_scale < 1e-12] = 1.0
    a /= second_scale
    b /= second_scale
    design = np.column_stack((np.ones(len(a)), a))
    offset = logit(np.clip(baseline, 1e-7, 1 - 1e-7))

    def objective(beta: np.ndarray) -> tuple[float, np.ndarray]:
        z = offset + design @ beta
        value = np.mean(np.logaddexp(0.0, z) - y * z)
        value += .5 * penalty * np.dot(beta[1:], beta[1:])
        gradient = design.T @ (expit(z) - y) / len(y)
        gradient[1:] += penalty * beta[1:]
        return float(value), gradient

    result = minimize(
        objective, np.zeros(design.shape[1]), jac=True, method="L-BFGS-B",
        options={"maxiter": 1500, "gtol": 1e-7, "ftol": 1e-12},
    )
    if not result.success:
        raise RuntimeError(f"Offset fit failed: {result.message}")
    correction = result.x[0] + b @ result.x[1:]
    score = expit(logit(np.clip(eval_baseline, 1e-7, 1 - 1e-7)) + correction)
    return score, {"iterations": int(result.nit), "coefficient_count": len(result.x),
                   "gradient_max_abs": float(np.max(np.abs(result.jac)))}


def fit_candidate(
    family: str, parameters: dict, train_x: np.ndarray, train_y: np.ndarray,
    train_base: np.ndarray, eval_x: np.ndarray, eval_base: np.ndarray,
) -> tuple[np.ndarray, dict]:
    if family == "offset":
        return fit_offset(train_x, train_y, train_base, eval_x, eval_base,
                          parameters["penalty"], parameters["basis"])
    if family == "spline_logit":
        model = make_pipeline(
            StandardScaler(),
            SplineTransformer(n_knots=4, degree=2, knots="quantile",
                              include_bias=False, extrapolation="linear"),
            StandardScaler(),
            LogisticRegression(C=parameters["C"], solver="lbfgs",
                               max_iter=1500, tol=1e-7, random_state=907),
        )
    elif family == "hist_gb":
        model = HistGradientBoostingClassifier(
            learning_rate=.05, l2_regularization=10.0, max_depth=3,
            early_stopping=False, random_state=907, **parameters,
        )
    elif family == "extra_trees":
        model = ExtraTreesClassifier(n_jobs=2, max_features=1.0,
                                     random_state=907, **parameters)
    elif family == "random_forest":
        model = RandomForestClassifier(n_jobs=2, max_features=1.0,
                                       random_state=907, **parameters)
    elif family == "mlp":
        model = make_pipeline(
            StandardScaler(),
            MLPClassifier(solver="adam", early_stopping=True, validation_fraction=.2,
                          n_iter_no_change=12, random_state=907, **parameters),
        )
    else:
        raise ValueError(family)
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always", ConvergenceWarning)
        model.fit(train_x, train_y)
    convergence = [str(w.message) for w in caught if issubclass(w.category, ConvergenceWarning)]
    if convergence:
        raise RuntimeError("; ".join(convergence))
    score = model.predict_proba(eval_x)[:, 1]
    return score, {"fit_class": type(model).__name__, "warnings": convergence}


def main() -> None:
    if OUT.exists():
        raise SystemExit("Preserve existing method-screen output; create a new version")
    for path in (FUTURE / "consumption_receipt.json", FUTURE / "examples/examples.bin",
                 FUTURE / "evaluation/result.json"):
        if path.exists():
            raise SystemExit("Protected V4 artifact exists; refusing opened-data screen")
    verify_manifest(OOF_MANIFEST)
    verify_manifest(EVENT_MANIFEST)
    verify_manifest(PARENT / "manifest.json")
    verify_manifest(PREVIOUS / "manifest.json")
    OUT.mkdir(parents=True)
    contract = {
        "role": "opened-development broad observed-news method screen",
        "selection_fold": 4,
        "later_reporting_fold": 5,
        "later_fold_already_opened_by_prior_trial": True,
        "source_policy": "Score only rows with recorded recent article; unobserved feed is not zero news",
        "baseline": "frozen tree_no_terminal OOF probability",
        "feature_names": list(FEATURE_NAMES),
        "tiers": {name: list(indices) for name, indices in TIERS.items()},
        "variants": [{"name": name, "family": family, "parameters": parameters}
                     for name, family, parameters in VARIANTS],
        "selection": "minimum fold-4 observed-news log loss separately for context-only and news-feature tiers; report every candidate and its fold-5 score",
        "training": "fold 3 for fold 4; folds 3-4 for fold 5, 30-minute label-horizon purge, market-disjoint",
        "metric": "mean row log loss primary; Brier and AP secondary",
        "bootstrap": "1000 market-cluster resamples, seed 907, descriptive and unadjusted for model search",
        "known_limits": ["opened outcome and source-uncertified exploratory screen",
                         "historical semantic model saw later development text",
                         "market groups may share event and calendar shocks",
                         "earlier market-baseline construction may inherit snapshot metadata"],
        "inputs": [{"path": str(path.relative_to(REPO_ROOT)), "sha256": sha256_file(path)}
                   for path in (PARENT / "predictions.npz", OOF, EVENTS)],
        "created_at": datetime.now(timezone.utc).isoformat(),
        "python_scikit_learn": sklearn.__version__,
    }
    write_json(OUT / "contract.json", contract)

    oof = np.memmap(OOF, mode="r", dtype=OOF_DTYPE)
    events = np.memmap(EVENTS, mode="r", dtype=EVENT_DTYPE)
    selected = np.flatnonzero(oof["fold"] >= 3)
    with np.load(PARENT / "predictions.npz", allow_pickle=False) as frozen:
        rows = {key: frozen[key].copy() for key in
                ("market", "minute", "fold", "label", "tree_no_terminal")}
    for key in ("market", "minute", "fold", "label"):
        if not np.array_equal(rows[key], oof[key][selected]):
            raise RuntimeError(f"Frozen row mismatch: {key}")
    news = recent_news(oof, events)[selected]
    exposure = news[:, 0] > 0
    exposed_index = np.flatnonzero(exposure)
    x = observed_features(rows, events, news)
    y = rows["label"][exposed_index]
    market = rows["market"][exposed_index]
    minute = rows["minute"][exposed_index]
    fold = rows["fold"][exposed_index]
    p0 = rows["tree_no_terminal"][exposed_index]
    if not np.all((p0 > 0) & (p0 < 1)):
        raise RuntimeError("Invalid baseline probability")
    results = {}
    predictions = {}
    with threadpool_limits(limits=2):
        for outer in (4, 5):
            eval_mask = fold == outer
            eval_start = int(minute[eval_mask].min())
            train_mask = (fold >= 3) & (fold < outer) & (minute + 30 < eval_start)
            train = np.flatnonzero(train_mask)
            validation = np.flatnonzero(eval_mask)
            if not len(train) or np.intersect1d(market[train], market[validation]).size:
                raise RuntimeError(f"Group split failure in fold {outer}")
            if minute[train].max() + 30 >= eval_start:
                raise RuntimeError(f"Purge failure in fold {outer}")
            if len(np.unique(y[train])) != 2:
                raise RuntimeError(f"Single-class training fold {outer}")
            print(f"Fold {outer}: {len(train)} training, {len(validation)} validation", flush=True)
            for tier, columns in TIERS.items():
                for name, family, parameters in VARIANTS:
                    key = f"{tier}__{name}"
                    entry = results.setdefault(key, {"tier": tier, "name": name,
                                                     "family": family, "parameters": parameters,
                                                     "folds": {}})
                    try:
                        score, fit = fit_candidate(
                            family, parameters, x[train][:, columns], y[train], p0[train],
                            x[validation][:, columns], p0[validation],
                        )
                        if not np.all(np.isfinite(score)):
                            raise RuntimeError("Nonfinite scores")
                        fold_metrics = metric(y[validation], score)
                        entry["folds"][str(outer)] = {"status": "complete", "metrics": fold_metrics,
                                                       "fit": fit}
                        predictions[f"{key}__fold{outer}"] = score
                    except Exception as error:
                        entry["folds"][str(outer)] = {"status": "failed", "error": str(error)}
                    print(f"  {key}: {entry['folds'][str(outer)]['status']}"
                          + (f" LL={entry['folds'][str(outer)]['metrics']['log_loss']:.6f}"
                             if entry['folds'][str(outer)]['status'] == 'complete' else ''), flush=True)
            write_json(OUT / "checkpoint.json", {"results": results})

    fold5 = fold == 5
    fold4 = fold == 4
    eligible = [(key, result) for key, result in results.items()
                if result["folds"].get("4", {}).get("status") == "complete"
                and result["folds"].get("5", {}).get("status") == "complete"]
    selected = {}
    for group, tiers in (("context", ("context",)), ("news", ("timing", "semantic"))):
        choices = [(key, result) for key, result in eligible if result["tier"] in tiers]
        if not choices:
            selected[group] = None
            continue
        key, value = min(choices, key=lambda pair: (pair[1]["folds"]["4"]["metrics"]["log_loss"], pair[0]))
        selected[group] = {"key": key,
                           "fold4_log_loss": value["folds"]["4"]["metrics"]["log_loss"],
                           "fold5_log_loss": value["folds"]["5"]["metrics"]["log_loss"]}
    selected_comparison = None
    if selected["context"] and selected["news"]:
        context_key = selected["context"]["key"]
        news_key = selected["news"]["key"]
        context_score = predictions[f"{context_key}__fold5"]
        news_score = predictions[f"{news_key}__fold5"]
        difference = point_loss(y[fold5], context_score) - point_loss(y[fold5], news_score)
        selected_comparison = {
            "news_vs_context_log_loss": block_interval({"market": market[fold5]}, difference),
            "news_vs_context_brier_improvement": float(metric(y[fold5], context_score)["brier"] - metric(y[fold5], news_score)["brier"]),
            "news_vs_context_average_precision_gain": float(metric(y[fold5], news_score)["average_precision"] - metric(y[fold5], context_score)["average_precision"]),
            "context_vs_frozen_tree_log_loss": float(point_loss(y[fold5], p0[fold5]).mean() - point_loss(y[fold5], context_score).mean()),
            "news_vs_frozen_tree_log_loss": float(point_loss(y[fold5], p0[fold5]).mean() - point_loss(y[fold5], news_score).mean()),
        }
    np.savez_compressed(OUT / "predictions.npz", market4=market[fold4], label4=y[fold4],
                        market5=market[fold5], label5=y[fold5], baseline4=p0[fold4],
                        baseline5=p0[fold5], **predictions)
    report = {"status": "complete", "role": contract["role"],
              "observed_news_rows": len(exposed_index), "fold4_rows": int(fold4.sum()),
              "fold5_rows": int(fold5.sum()), "fold5_markets": int(np.unique(market[fold5]).size),
              "baseline_fold4": metric(y[fold4], p0[fold4]),
              "baseline_fold5": metric(y[fold5], p0[fold5]),
              "results": results, "selected_on_fold4": selected,
              "selected_fold5_comparison": selected_comparison,
              "protected_outcomes_read": False, "source_certification_claim": False,
              "candidate_promotion": False}
    write_json(OUT / "report.json", report)
    artifacts = [OUT / "contract.json", OUT / "report.json", OUT / "predictions.npz", Path(__file__)]
    write_json(OUT / "manifest.json", {"artifacts": [
        {"path": str(path.relative_to(REPO_ROOT)), "sha256": sha256_file(path)} for path in artifacts
    ]})
    print(json.dumps({"status": "complete", "selected_on_fold4": selected,
                      "selected_fold5_comparison": selected_comparison}, indent=2))


if __name__ == "__main__":
    main()
