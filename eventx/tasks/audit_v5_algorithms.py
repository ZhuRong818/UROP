"""Bounded algorithm audit on opened May–July discovery; never a V5-R test.

Run: .venv/bin/python -m eventx.tasks.audit_v5_algorithms
All model grids and sampling limits are written before fitting. Old artifacts are
read-only; a separate output directory refuses overwrite. No holdout rows are read.
"""
from __future__ import annotations

import json
import platform
import warnings
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import scipy
import sklearn
from scipy.optimize import minimize
from scipy.special import expit
from sklearn.compose import ColumnTransformer
from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.exceptions import ConvergenceWarning
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import SplineTransformer, StandardScaler
from threadpoolctl import threadpool_limits

from eventx.features.v5_market import market_values
from eventx.tasks.build_v4_discovery_examples import EXAMPLE_DTYPE
from eventx.tasks.prepare_v4_discovery_news_quality import EVENT_DTYPE
from eventx.tasks.run_v4_discovery_models import OOF_DTYPE
from eventx.tasks.run_v4_exploratory_novelty_diffusion import reconstruct_oof_indices
from eventx.tasks.run_v5_residual_feasibility import (
    EXAMPLES, EXAMPLES_MANIFEST, OOF, OOF_MANIFEST, EVENTS, EVENT_MANIFEST,
    MARKETS, FUTURE, START_US, read_jsonl, terminal_metadata, metric, point_loss,
    sha256_file, verify_manifest, REPO_ROOT,
)

OUT = REPO_ROOT / "data/v5/algorithm_audit_20260907"
CAP = 60000
SEED = 907
FAMILIES = ("linear", "spline", "tree")
BUNDLES = ("no_terminal", "market", "timing", "semantic")
MINUTE_US = 60_000_000


def write_json(path, value):
    temp = path.with_suffix(path.suffix + ".tmp")
    temp.write_text(json.dumps(value, indent=2, sort_keys=True, allow_nan=False) + "\n")
    temp.replace(path)


def recent_news(oof, events):
    """Exact (t-30m,t] aggregation; zero exposure keeps all summaries zero."""
    out = np.zeros((len(oof), 5), dtype=np.float64)
    for market in np.unique(oof["market"]):
        rows = np.flatnonzero(oof["market"] == market)
        a, b = np.searchsorted(events["market"], [market, market + 1])
        ev = events[a:b]
        times = ev["timestamp_us"]
        grid = START_US + oof["minute"][rows].astype(np.int64) * MINUTE_US
        left = np.searchsorted(times, grid - 30 * MINUTE_US, side="right")
        right = np.searchsorted(times, grid, side="right")
        product = ev["relevance"].astype(float) * ev["novelty"].astype(float)
        for i, lo, hi, t in zip(rows, left, right, grid):
            if hi > lo:
                out[i] = (1, hi - lo, (t - times[hi - 1]) / MINUTE_US,
                          product[lo:hi].max(), product[hi - 1])
    return out


def offset_objective(beta, x, y, offset, penalty):
    z = offset + x @ beta
    value = np.mean(np.logaddexp(0, z) - y * z) + penalty * np.dot(beta, beta) / 2
    grad = x.T @ (expit(z) - y) / len(y) + penalty * beta
    return float(value), grad


def offset_sanity():
    """Demonstrate fixed offset and refit-then-subtract are different objectives."""
    x = np.ones((100, 1))
    y = np.r_[np.ones(20), np.zeros(80)]
    offset = np.full(100, np.log(.2 / .8))
    result = minimize(offset_objective, np.zeros(1), args=(x, y, offset, .1),
                      jac=True, method="L-BFGS-B")
    standalone = minimize(offset_objective, np.zeros(1),
                          args=(x, y, np.zeros(100), .1), jac=True, method="L-BFGS-B")
    assert result.success and standalone.success
    assert abs(result.x[0]) < 1e-8
    return {"true_offset_correction": float(result.x[0]),
            "standalone_minus_baseline_correction": float(standalone.x[0] - offset[0]),
            "note": "same penalty, already calibrated baseline; objectives differ"}


def sample(mask, seed):
    idx = np.flatnonzero(mask)
    if len(idx) > CAP:
        idx = np.sort(np.random.default_rng(seed).choice(idx, CAP, replace=False))
    return idx


def split_masks(rows, fold):
    start = (fold * 11) * 1440
    tune_start = ((fold - 1) * 11) * 1440
    return ((rows["fold"] < fold - 1) & (rows["minute"] + 30 < tune_start),
            rows["fold"] == fold - 1,
            (rows["fold"] < fold) & (rows["minute"] + 30 < start),
            rows["fold"] == fold)


def matrix_for(market, news, bundle, train):
    if bundle == "no_terminal":
        return market[:, [*range(12), 14]], {}
    if bundle == "market":
        return market, {}
    cap = float(np.quantile(news[train, 1], .99))
    timing = np.column_stack((news[:, 0], np.log1p(np.minimum(news[:, 1], cap)),
                              news[:, 2]))
    x = np.column_stack((market, timing))
    if bundle == "semantic":
        x = np.column_stack((x, news[:, 3:5], news[:, 3] * market[:, 12]))
    return x, {"train_only_article_count_cap": cap}


def fit_model(family, param, x, y):
    if family == "tree":
        model = HistGradientBoostingClassifier(max_iter=int(param), learning_rate=.05,
                    max_leaf_nodes=7, max_depth=3, min_samples_leaf=100,
                    l2_regularization=10, early_stopping=False, random_state=SEED)
    else:
        steps = []
        if family == "spline":
            varying = np.flatnonzero(np.ptp(x, axis=0) > 1e-10)
            steps.append(ColumnTransformer([
                ("splines", SplineTransformer(n_knots=4, degree=2,
                    knots="quantile", include_bias=False, extrapolation="linear"), varying)
            ], remainder="passthrough"))
        steps.extend([StandardScaler(), LogisticRegression(C=param, solver="lbfgs",
                       max_iter=2000, tol=1e-7, random_state=SEED)])
        model = make_pipeline(*steps)
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        model.fit(x, y)
    conv = [str(w.message) for w in caught if issubclass(w.category, ConvergenceWarning)]
    fit = {"parameter": param, "converged": not conv, "convergence_warnings": conv}
    fit["iterations"] = int(model.n_iter_ if family == "tree" else model[-1].n_iter_[0])
    return model, fit


def block_interval(rows, delta):
    """Market-cluster bootstrap; descriptive, no selection-adjusted inference."""
    _, inverse = np.unique(rows["market"], return_inverse=True)
    sums = np.bincount(inverse, weights=delta)
    counts = np.bincount(inverse)
    rng = np.random.default_rng(SEED)
    draws = rng.integers(0, len(sums), (1000, len(sums)))
    values = sums[draws].sum(1) / counts[draws].sum(1)
    return {"mean": float(delta.mean()), "market_balanced_mean": float((sums/counts).mean()),
            "market_cluster_95_interval": np.quantile(values, [.025, .975]).tolist(),
            "markets": len(sums), "samples": 1000,
            "limitation": "opened-data, unadjusted for model search or shared calendar shocks"}


def main():
    if OUT.exists():
        raise SystemExit("Audit output exists; preserve it and create another version")
    for p in (FUTURE / "consumption_receipt.json", FUTURE / "examples/examples.bin",
              FUTURE / "evaluation/result.json"):
        if p.exists():
            raise SystemExit("Protected v4 interval may have been opened; refusing audit")
    for p in (EXAMPLES_MANIFEST, OOF_MANIFEST, EVENT_MANIFEST):
        verify_manifest(p)
    OUT.mkdir(parents=True)
    contract = {"version": "algorithm-audit-20260907", "role": "opened-data exploratory audit",
                "not_v5_r_promotion": True, "train_cap": CAP, "seed": SEED,
                "outer_folds": [3, 4, 5], "horizon_purge_minutes": 30,
                "families": {"linear": [.01, .1], "spline": [.01, .1], "tree": [100, 200]},
                "bundles": list(BUNDLES), "early_stopping": False,
                "semantic_limit": "inherited full-discovery TF-IDF/SVD; not strict temporal OOF",
                "terminal_limit": "snapshot terminal metadata lacks as-of version proof",
                "created_at": datetime.now(timezone.utc).isoformat(),
                "inputs": [{"path": str(p.relative_to(REPO_ROOT)), "sha256": sha256_file(p)}
                           for p in (EXAMPLES, OOF, EVENTS, MARKETS)],
                "python": platform.python_version(), "numpy": np.__version__,
                "scipy": scipy.__version__, "sklearn": sklearn.__version__}
    write_json(OUT / "contract.json", contract)
    examples = np.memmap(EXAMPLES, mode="r", dtype=EXAMPLE_DTYPE)
    oof = np.memmap(OOF, mode="r", dtype=OOF_DTYPE)
    events = np.memmap(EVENTS, mode="r", dtype=EVENT_DTYPE)
    assert np.max(oof["minute"]) < 66 * 1440
    idx = reconstruct_oof_indices(examples, oof)
    terminal, known = terminal_metadata(list(read_jsonl(MARKETS)))
    market = market_values(examples["features"][idx, :12], oof["market"], oof["minute"],
                           examples["price_age"][idx], terminal, known)
    news = recent_news(oof, events)
    assert np.all(np.isfinite(market)) and np.all(np.isfinite(news))
    selected_rows = np.flatnonzero(oof["fold"] >= 3)
    final = np.asarray(oof[selected_rows])
    predictions = {f"{f}_{b}": np.zeros(len(final)) for f in FAMILIES for b in BUNDLES}
    folds = []
    with threadpool_limits(limits=2):
        for fold in (3, 4, 5):
            im, tm, om, vm = split_masks(oof, fold)
            train, tune, outer, val = (sample(im, SEED+fold), sample(tm, SEED+fold+10),
                                      sample(om, SEED+fold+20), np.flatnonzero(vm))
            for a, b in ((train, tune), (outer, val)):
                assert oof["minute"][a].max() + 30 < oof["minute"][b].min()
                assert not np.intersect1d(oof["market"][a], oof["market"][b]).size
            entry = {"fold": fold, "inner_train_rows": len(train), "tune_rows": len(tune),
                     "outer_train_rows": len(outer), "validation_rows": len(val),
                     "old_outer_rows_with_horizon_overlap": int(np.sum(
                         (oof["fold"] < fold) & (oof["minute"]+30 >= fold*11*1440))),
                     "fits": {}}
            for family in FAMILIES:
                for bundle in BUNDLES:
                    key = f"{family}_{bundle}"
                    x, _ = matrix_for(market, news, bundle, train)
                    trials = []
                    for param in contract["families"][family]:
                        model, fit = fit_model(family, param, x[train], oof["label"][train])
                        score = model.predict_proba(x[tune])[:, 1]
                        trials.append({**fit, "tune_log_loss": float(point_loss(oof["label"][tune], score).mean())})
                    valid = [r for r in trials if r["converged"]]
                    if not valid:
                        raise RuntimeError(f"No converged tuning fit: {key}")
                    chosen = min(valid, key=lambda r: (r["tune_log_loss"], r["parameter"]))
                    x, preprocessing = matrix_for(market, news, bundle, outer)
                    model, fit = fit_model(family, chosen["parameter"], x[outer], oof["label"][outer])
                    if not fit["converged"]:
                        raise RuntimeError(f"Final fit did not converge: {key}")
                    score = model.predict_proba(x[val])[:, 1]
                    predictions[key][final["fold"] == fold] = score
                    entry["fits"][key] = {"trials": trials, "selected": chosen,
                        "final_fit": fit, "preprocessing": preprocessing,
                        "metrics": metric(oof["label"][val], score)}
                    print(f"fold {fold}: {key} LL={entry['fits'][key]['metrics']['log_loss']:.6f}", flush=True)
            folds.append(entry)
            write_json(OUT / "checkpoint.json", {"completed_folds": folds})
    labels = final["label"]
    metrics = {k: metric(labels, p) for k, p in predictions.items()}
    comparisons = {}
    pairs = [(f"{f}_market", f"{f}_timing") for f in FAMILIES]
    pairs += [(f"{f}_timing", f"{f}_semantic") for f in FAMILIES]
    pairs += [(f"{f}_no_terminal", f"{f}_market") for f in FAMILIES]
    pairs += [("linear_market", f"{f}_market") for f in ("spline", "tree")]
    masks = {"all": np.ones(len(final), bool), "exposed_30m": news[selected_rows, 0] > 0,
             "unexposed_30m": news[selected_rows, 0] == 0,
             "fresh_30m": examples["price_age"][idx[selected_rows]] <= 30}
    for base, candidate in pairs:
        delta = point_loss(labels, predictions[base]) - point_loss(labels, predictions[candidate])
        comparisons[candidate + "_vs_" + base] = {
            "all": block_interval(final, delta),
            "subsets": {name: {"rows": int(mask.sum()),
                               "ll_improvement": float(delta[mask].mean()) if mask.any() else None}
                        for name, mask in masks.items()},
            "fold_improvement": {str(f): float(delta[final["fold"] == f].mean()) for f in (3,4,5)}}
    np.savez_compressed(OUT / "predictions.npz", market=final["market"], minute=final["minute"],
                        fold=final["fold"], label=labels, **predictions)
    report = {"status": "complete", "contract": contract, "rows": len(final),
              "exposed_rows": int(masks["exposed_30m"].sum()), "metrics": metrics,
              "comparisons": comparisons, "folds": folds, "offset_sanity": offset_sanity(),
              "protected_outcomes_read": False, "all_final_fits_converged": True,
              "point_in_time_semantic_validation": False,
              "note": "Historical diagnostic only; not original V5-R; no automatic promotion"}
    write_json(OUT / "report.json", report)
    paths = [OUT / "contract.json", OUT / "report.json", OUT / "predictions.npz", Path(__file__)]
    write_json(OUT / "manifest.json", {"artifacts": [
        {"path": str(p.relative_to(REPO_ROOT)), "sha256": sha256_file(p)} for p in paths]})
    print(json.dumps({"status": "complete", "rows": len(final), "metrics": metrics}, indent=2))


if __name__ == "__main__":
    main()
