"""Opened-data market-only learner screen against the frozen no-terminal tree.

Run: .venv/bin/python -m eventx.tasks.screen_v5_market_learners_20261009
Fold 4 selects; fold 5 reports. Neither is an untouched research holdout.
"""
from __future__ import annotations

import json
import warnings
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import sklearn
from sklearn.ensemble import ExtraTreesClassifier, HistGradientBoostingClassifier, RandomForestClassifier
from sklearn.exceptions import ConvergenceWarning
from sklearn.neural_network import MLPClassifier
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler
from threadpoolctl import threadpool_limits

from eventx.features.v5_market import market_values
from eventx.tasks.audit_v5_algorithms import SEED, block_interval, sample
from eventx.tasks.build_v4_discovery_examples import EXAMPLE_DTYPE
from eventx.tasks.run_v4_discovery_models import OOF_DTYPE
from eventx.tasks.run_v4_exploratory_novelty_diffusion import reconstruct_oof_indices
from eventx.tasks.run_v5_residual_feasibility import (
    EXAMPLES, EXAMPLES_MANIFEST, FUTURE, MARKETS, OOF, OOF_MANIFEST, REPO_ROOT,
    metric, point_loss, read_jsonl, sha256_file, terminal_metadata, verify_manifest,
)

PARENT = REPO_ROOT / "data/v5/algorithm_audit_20260907"
OUT = REPO_ROOT / "data/v5/market_learner_screen_20261009"
CONFIGS = (
    ("hgb_7_300", "hgb", {"max_iter": 300, "learning_rate": .05, "max_leaf_nodes": 7, "max_depth": 3, "min_samples_leaf": 100, "l2_regularization": 10.0}),
    ("hgb_15_300", "hgb", {"max_iter": 300, "learning_rate": .05, "max_leaf_nodes": 15, "max_depth": 4, "min_samples_leaf": 100, "l2_regularization": 10.0}),
    ("hgb_15_500", "hgb", {"max_iter": 500, "learning_rate": .05, "max_leaf_nodes": 15, "max_depth": 5, "min_samples_leaf": 50, "l2_regularization": 5.0}),
    ("hgb_31_300", "hgb", {"max_iter": 300, "learning_rate": .05, "max_leaf_nodes": 31, "max_depth": 5, "min_samples_leaf": 100, "l2_regularization": 20.0}),
    ("hgb_7_600", "hgb", {"max_iter": 600, "learning_rate": .05, "max_leaf_nodes": 7, "max_depth": 3, "min_samples_leaf": 100, "l2_regularization": 10.0}),
    ("extra_trees_300", "extra_trees", {"n_estimators": 300, "max_depth": 12, "min_samples_leaf": 50}),
    ("random_forest_300", "random_forest", {"n_estimators": 300, "max_depth": 12, "min_samples_leaf": 50}),
    ("mlp_32_16", "mlp", {"hidden_layer_sizes": [32, 16], "alpha": .1, "max_iter": 250}),
)


def write_json(path: Path, value: dict) -> None:
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(value, indent=2, sort_keys=True, allow_nan=False) + "\n")
    temporary.replace(path)


def make_model(family: str, params: dict):
    if family == "hgb":
        return HistGradientBoostingClassifier(early_stopping=False, random_state=SEED, **params)
    if family == "extra_trees":
        return ExtraTreesClassifier(n_jobs=2, max_features=1.0, random_state=SEED, **params)
    if family == "random_forest":
        return RandomForestClassifier(n_jobs=2, max_features=1.0, random_state=SEED, **params)
    if family == "mlp":
        return make_pipeline(StandardScaler(), MLPClassifier(
            early_stopping=True, validation_fraction=.2, n_iter_no_change=12,
            random_state=SEED, **params))
    raise ValueError(family)


def main() -> None:
    if OUT.exists():
        raise SystemExit("Preserve the existing screen; create a new version")
    for path in (FUTURE / "consumption_receipt.json", FUTURE / "examples/examples.bin",
                 FUTURE / "evaluation/result.json"):
        if path.exists():
            raise SystemExit("Protected V4 artifact exists; refusing opened-data screen")
    verify_manifest(EXAMPLES_MANIFEST)
    verify_manifest(OOF_MANIFEST)
    verify_manifest(PARENT / "manifest.json")
    OUT.mkdir(parents=True)
    contract = {
        "role": "opened-development market-only learner screen",
        "baseline": "frozen tree_no_terminal OOF predictions",
        "train_cap": 60000,
        "seed": SEED,
        "training": "same outer-train caps and validation rows as parent audit, with 30-minute purge and market disjointness",
        "selection_fold": 4,
        "later_reporting_fold": 5,
        "later_fold_already_opened": True,
        "features": "parent audit market_values columns 0..11 and 14, excluding terminal predictors",
        "metric": "row mean log loss primary; Brier and AP secondary",
        "configs": [{"name": name, "family": family, "parameters": parameters}
                    for name, family, parameters in CONFIGS],
        "limits": ["post-selection opened data", "upstream eligibility may inherit snapshot metadata",
                   "market clusters do not certify event-family/calendar independence"],
        "inputs": [{"path": str(path.relative_to(REPO_ROOT)), "sha256": sha256_file(path)}
                   for path in (EXAMPLES, OOF, MARKETS, PARENT / "predictions.npz")],
        "created_at": datetime.now(timezone.utc).isoformat(),
        "scikit_learn": sklearn.__version__,
    }
    write_json(OUT / "contract.json", contract)

    examples = np.memmap(EXAMPLES, mode="r", dtype=EXAMPLE_DTYPE)
    oof = np.memmap(OOF, mode="r", dtype=OOF_DTYPE)
    indices = reconstruct_oof_indices(examples, oof)
    terminal, known = terminal_metadata(list(read_jsonl(MARKETS)))
    matrix = market_values(examples["features"][indices, :12], oof["market"],
                           oof["minute"], examples["price_age"][indices],
                           terminal, known)[:, [*range(12), 14]]
    if not np.all(np.isfinite(matrix)):
        raise RuntimeError("Nonfinite market inputs")
    selected_rows = np.flatnonzero(oof["fold"] >= 3)
    with np.load(PARENT / "predictions.npz", allow_pickle=False) as frozen:
        for name in ("market", "minute", "fold", "label"):
            if not np.array_equal(frozen[name], oof[name][selected_rows]):
                raise RuntimeError(f"Frozen row mismatch: {name}")
        baseline = frozen["tree_no_terminal"].copy()
    results = {}
    predictions = {}
    with threadpool_limits(limits=2):
        for fold in (4, 5):
            start = fold * 11 * 1440
            train_mask = (oof["fold"] < fold) & (oof["minute"] + 30 < start)
            train = sample(train_mask, SEED + fold + 20)
            validation = np.flatnonzero(oof["fold"] == fold)
            if oof["minute"][train].max() + 30 >= oof["minute"][validation].min():
                raise RuntimeError("Horizon purge failure")
            if np.intersect1d(oof["market"][train], oof["market"][validation]).size:
                raise RuntimeError("Market group overlap")
            print(f"Fold {fold}: {len(train)} training, {len(validation)} validation", flush=True)
            for name, family, parameters in CONFIGS:
                entry = results.setdefault(name, {"family": family, "parameters": parameters, "folds": {}})
                try:
                    model = make_model(family, parameters)
                    with warnings.catch_warnings(record=True) as caught:
                        warnings.simplefilter("always", ConvergenceWarning)
                        model.fit(matrix[train], oof["label"][train])
                    conv = [str(w.message) for w in caught if issubclass(w.category, ConvergenceWarning)]
                    if conv:
                        raise RuntimeError("; ".join(conv))
                    score = model.predict_proba(matrix[validation])[:, 1]
                    if not np.all(np.isfinite(score)):
                        raise RuntimeError("Nonfinite score")
                    entry["folds"][str(fold)] = {"status": "complete", "metrics": metric(oof["label"][validation], score),
                                                 "baseline_metrics": metric(oof["label"][validation], baseline[oof["fold"][selected_rows] == fold])}
                    predictions[f"{name}__fold{fold}"] = score
                except Exception as error:
                    entry["folds"][str(fold)] = {"status": "failed", "error": str(error)}
                result = entry["folds"][str(fold)]
                print(f"  {name}: {result['status']}" + (f" LL={result['metrics']['log_loss']:.6f}"
                      if result["status"] == "complete" else ""), flush=True)
            write_json(OUT / "checkpoint.json", {"results": results})

    eligible = [(name, value) for name, value in results.items()
                if all(value["folds"].get(str(f), {}).get("status") == "complete" for f in (4, 5))]
    selected = None
    comparison = None
    if eligible:
        name, chosen = min(eligible, key=lambda pair: (pair[1]["folds"]["4"]["metrics"]["log_loss"], pair[0]))
        selected = {"name": name,
                    "fold4_log_loss": chosen["folds"]["4"]["metrics"]["log_loss"],
                    "fold5_log_loss": chosen["folds"]["5"]["metrics"]["log_loss"]}
        final_mask = oof["fold"][selected_rows] == 5
        score = predictions[f"{name}__fold5"]
        reference = baseline[final_mask]
        difference = point_loss(oof["label"][selected_rows][final_mask], reference) - point_loss(oof["label"][selected_rows][final_mask], score)
        comparison = {"selected_vs_frozen_tree_log_loss": block_interval(
                          {"market": oof["market"][selected_rows][final_mask]}, difference),
                      "selected_vs_frozen_tree_brier_improvement": float(
                          chosen["folds"]["5"]["baseline_metrics"]["brier"] -
                          chosen["folds"]["5"]["metrics"]["brier"]),
                      "selected_vs_frozen_tree_ap_gain": float(
                          chosen["folds"]["5"]["metrics"]["average_precision"] -
                          chosen["folds"]["5"]["baseline_metrics"]["average_precision"])}
    np.savez_compressed(OUT / "predictions.npz", **predictions)
    report = {"status": "complete", "role": contract["role"], "results": results,
              "selected_on_fold4": selected, "selected_fold5_comparison": comparison,
              "protected_outcomes_read": False, "candidate_promotion": False}
    write_json(OUT / "report.json", report)
    artifacts = [OUT / "contract.json", OUT / "report.json", OUT / "predictions.npz", Path(__file__)]
    write_json(OUT / "manifest.json", {"artifacts": [
        {"path": str(path.relative_to(REPO_ROOT)), "sha256": sha256_file(path)} for path in artifacts
    ]})
    print(json.dumps({"status": "complete", "selected_on_fold4": selected,
                      "selected_fold5_comparison": comparison}, indent=2))


if __name__ == "__main__":
    main()
