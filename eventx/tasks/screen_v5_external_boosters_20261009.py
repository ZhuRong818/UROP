"""Adaptive, opened-data market-only LightGBM/XGBoost/CatBoost screen.

Run: .venv/bin/python -m eventx.tasks.screen_v5_external_boosters_20261009
This follows the earlier sklearn screen and is not an independent evaluation.
"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

import catboost
import numpy as np
from catboost import CatBoostClassifier
from threadpoolctl import threadpool_limits

try:
    import lightgbm
    from lightgbm import LGBMClassifier
    LIGHTGBM_ERROR = None
except Exception as error:
    lightgbm = None
    LGBMClassifier = None
    LIGHTGBM_ERROR = str(error)

try:
    import xgboost
    from xgboost import XGBClassifier
    XGBOOST_ERROR = None
except Exception as error:
    xgboost = None
    XGBClassifier = None
    XGBOOST_ERROR = str(error)

from eventx.features.v5_market import market_values
from eventx.tasks.audit_v5_algorithms import SEED, block_interval, sample
from eventx.tasks.build_v4_discovery_examples import EXAMPLE_DTYPE
from eventx.tasks.run_v4_discovery_models import OOF_DTYPE
from eventx.tasks.run_v4_exploratory_novelty_diffusion import reconstruct_oof_indices
from eventx.tasks.run_v5_residual_feasibility import (
    EXAMPLES, EXAMPLES_MANIFEST, FUTURE, MARKETS, OOF, OOF_MANIFEST, REPO_ROOT,
    metric, point_loss, read_jsonl, sha256_file, terminal_metadata, verify_manifest,
)

OLD_AUDIT = REPO_ROOT / "data/v5/algorithm_audit_20260907"
SKLEARN_SCREEN = REPO_ROOT / "data/v5/market_learner_screen_20261009"
OUT = REPO_ROOT / "data/v5/external_booster_screen_20261009"
CONFIGS = (
    ("lgbm_15_300", "lightgbm", {"n_estimators": 300, "num_leaves": 15, "max_depth": 4}),
    ("lgbm_31_600", "lightgbm", {"n_estimators": 600, "num_leaves": 31, "max_depth": 5}),
    ("xgb_3_300", "xgboost", {"n_estimators": 300, "max_depth": 3}),
    ("xgb_5_600", "xgboost", {"n_estimators": 600, "max_depth": 5}),
    ("cat_4_300", "catboost", {"iterations": 300, "depth": 4}),
    ("cat_6_600", "catboost", {"iterations": 600, "depth": 6}),
)


def write_json(path: Path, value: dict) -> None:
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(value, indent=2, sort_keys=True, allow_nan=False) + "\n")
    temporary.replace(path)


def make_model(family: str, parameters: dict):
    if family == "lightgbm":
        if LGBMClassifier is None:
            raise RuntimeError(f"LightGBM unavailable: {LIGHTGBM_ERROR}")
        return LGBMClassifier(
            learning_rate=.05, min_child_samples=100, reg_lambda=10.0,
            colsample_bytree=.9, subsample=.8, subsample_freq=1,
            random_state=SEED, n_jobs=2, verbosity=-1, **parameters,
        )
    if family == "xgboost":
        if XGBClassifier is None:
            raise RuntimeError(f"XGBoost unavailable: {XGBOOST_ERROR}")
        return XGBClassifier(
            learning_rate=.05, min_child_weight=50, reg_lambda=10.0,
            subsample=.8, colsample_bytree=.9, tree_method="hist",
            objective="binary:logistic", eval_metric="logloss",
            random_state=SEED, n_jobs=2, **parameters,
        )
    if family == "catboost":
        return CatBoostClassifier(
            learning_rate=.05, l2_leaf_reg=10.0, loss_function="Logloss",
            random_seed=SEED, thread_count=2, verbose=False,
            allow_writing_files=False, **parameters,
        )
    raise ValueError(family)


def main() -> None:
    if OUT.exists():
        raise SystemExit("Preserve existing booster output; create a new version")
    for path in (FUTURE / "consumption_receipt.json", FUTURE / "examples/examples.bin",
                 FUTURE / "evaluation/result.json"):
        if path.exists():
            raise SystemExit("Protected V4 artifact exists; refusing opened-data screen")
    verify_manifest(EXAMPLES_MANIFEST)
    verify_manifest(OOF_MANIFEST)
    verify_manifest(OLD_AUDIT / "manifest.json")
    verify_manifest(SKLEARN_SCREEN / "manifest.json")
    OUT.mkdir(parents=True)
    contract = {
        "role": "adaptive opened-data market-only external-booster screen",
        "baseline": "frozen tree_no_terminal and prior fold4-selected hgb_7_600",
        "adaptive_followup_to": str((SKLEARN_SCREEN / "report.json").relative_to(REPO_ROOT)),
        "selection_fold": 4, "later_reporting_fold": 5,
        "later_fold_already_opened": True,
        "training": "same 60000-row deterministic outer cap, no-terminal market columns, 30-minute purge and disjoint market IDs as prior screen",
        "configs": [{"name": name, "family": family, "parameters": parameters}
                    for name, family, parameters in CONFIGS],
        "metric": "row mean log loss primary; Brier and AP secondary",
        "versions": {"lightgbm": lightgbm.__version__ if lightgbm else None,
                     "xgboost": xgboost.__version__ if xgboost else None,
                     "catboost": catboost.__version__},
        "dependency_failures": {"lightgbm": LIGHTGBM_ERROR, "xgboost": XGBOOST_ERROR},
        "limits": ["model search on opened outcomes", "unadjusted market bootstrap",
                   "snapshot metadata may affect upstream eligibility",
                   "market groups do not certify event-family/calendar independence"],
        "inputs": [{"path": str(path.relative_to(REPO_ROOT)), "sha256": sha256_file(path)}
                   for path in (EXAMPLES, OOF, MARKETS, OLD_AUDIT / "predictions.npz",
                                SKLEARN_SCREEN / "predictions.npz")],
        "created_at": datetime.now(timezone.utc).isoformat(),
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
    with np.load(OLD_AUDIT / "predictions.npz", allow_pickle=False) as old:
        for name in ("market", "minute", "fold", "label"):
            if not np.array_equal(old[name], oof[name][selected_rows]):
                raise RuntimeError(f"Frozen row mismatch: {name}")
        frozen_tree = old["tree_no_terminal"].copy()
    with np.load(SKLEARN_SCREEN / "predictions.npz", allow_pickle=False) as prior:
        prior_selected = {str(fold): prior[f"hgb_7_600__fold{fold}"].copy() for fold in (4, 5)}
    results = {}
    predictions = {}
    with threadpool_limits(limits=2):
        for fold in (4, 5):
            start = fold * 11 * 1440
            train = sample((oof["fold"] < fold) & (oof["minute"] + 30 < start), SEED + fold + 20)
            validation = np.flatnonzero(oof["fold"] == fold)
            if oof["minute"][train].max() + 30 >= oof["minute"][validation].min():
                raise RuntimeError("Horizon purge failure")
            if np.intersect1d(oof["market"][train], oof["market"][validation]).size:
                raise RuntimeError("Market group overlap")
            if len(prior_selected[str(fold)]) != len(validation):
                raise RuntimeError("Prior score row mismatch")
            print(f"Fold {fold}: {len(train)} training, {len(validation)} validation", flush=True)
            for name, family, parameters in CONFIGS:
                entry = results.setdefault(name, {"family": family, "parameters": parameters, "folds": {}})
                try:
                    model = make_model(family, parameters)
                    model.fit(matrix[train], oof["label"][train])
                    score = model.predict_proba(matrix[validation])[:, 1]
                    if not np.all(np.isfinite(score)):
                        raise RuntimeError("Nonfinite score")
                    entry["folds"][str(fold)] = {"status": "complete",
                                                 "metrics": metric(oof["label"][validation], score)}
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
    comparisons = None
    if eligible:
        name, chosen = min(eligible, key=lambda pair: (pair[1]["folds"]["4"]["metrics"]["log_loss"], pair[0]))
        selected = {"name": name, "fold4_log_loss": chosen["folds"]["4"]["metrics"]["log_loss"],
                    "fold5_log_loss": chosen["folds"]["5"]["metrics"]["log_loss"]}
        final_mask = oof["fold"][selected_rows] == 5
        y = oof["label"][selected_rows][final_mask]
        market = oof["market"][selected_rows][final_mask]
        candidate = predictions[f"{name}__fold5"]
        old_reference = frozen_tree[final_mask]
        prior_reference = prior_selected["5"]
        comparisons = {
            "selected_vs_frozen_tree": block_interval({"market": market},
                point_loss(y, old_reference) - point_loss(y, candidate)),
            "selected_vs_prior_hgb": block_interval({"market": market},
                point_loss(y, prior_reference) - point_loss(y, candidate)),
            "selected_fold5_brier": chosen["folds"]["5"]["metrics"]["brier"],
            "selected_fold5_ap": chosen["folds"]["5"]["metrics"]["average_precision"],
            "prior_hgb_fold5_metrics": metric(y, prior_reference),
            "frozen_tree_fold5_metrics": metric(y, old_reference),
        }
    np.savez_compressed(OUT / "predictions.npz", **predictions)
    report = {"status": "complete", "role": contract["role"], "results": results,
              "selected_on_fold4": selected, "selected_fold5_comparisons": comparisons,
              "protected_outcomes_read": False, "candidate_promotion": False}
    write_json(OUT / "report.json", report)
    artifacts = [OUT / "contract.json", OUT / "report.json", OUT / "predictions.npz", Path(__file__)]
    write_json(OUT / "manifest.json", {"artifacts": [
        {"path": str(path.relative_to(REPO_ROOT)), "sha256": sha256_file(path)} for path in artifacts
    ]})
    print(json.dumps({"status": "complete", "selected_on_fold4": selected,
                      "selected_fold5_comparisons": comparisons}, indent=2))


if __name__ == "__main__":
    main()
