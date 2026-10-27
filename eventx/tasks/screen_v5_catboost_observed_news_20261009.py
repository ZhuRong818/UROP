"""Adaptive CatBoost comparison of context, timing, and semantic news tiers.

Run: .venv/bin/python -m eventx.tasks.screen_v5_catboost_observed_news_20261009
Opened V5 development only; the later fold is already outcome-open.
"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

import catboost
import numpy as np
from catboost import CatBoostClassifier

from eventx.tasks.audit_v5_algorithms import block_interval, recent_news
from eventx.tasks.prepare_v4_discovery_news_quality import EVENT_DTYPE
from eventx.tasks.run_v4_discovery_models import OOF_DTYPE
from eventx.tasks.run_v5_residual_feasibility import (
    EVENT_MANIFEST, EVENTS, FUTURE, OOF, OOF_MANIFEST, REPO_ROOT,
    metric, point_loss, sha256_file, verify_manifest,
)
from eventx.tasks.screen_v5_observed_news_methods_20261009 import (
    FEATURE_NAMES, TIERS, observed_features,
)

PARENT = REPO_ROOT / "data/v5/algorithm_audit_20260907"
EARLIER = REPO_ROOT / "data/v5/observed_news_method_screen_20261009"
OUT = REPO_ROOT / "data/v5/catboost_observed_news_screen_20261009"
CONFIGS = (("cat_4_300", {"iterations": 300, "depth": 4}),
           ("cat_6_600", {"iterations": 600, "depth": 6}))


def write_json(path: Path, value: dict) -> None:
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(value, indent=2, sort_keys=True, allow_nan=False) + "\n")
    temporary.replace(path)


def main() -> None:
    if OUT.exists():
        raise SystemExit("Preserve existing CatBoost screen; create a new version")
    for path in (FUTURE / "consumption_receipt.json", FUTURE / "examples/examples.bin",
                 FUTURE / "evaluation/result.json"):
        if path.exists():
            raise SystemExit("Protected V4 artifact exists; refusing opened-data screen")
    verify_manifest(OOF_MANIFEST)
    verify_manifest(EVENT_MANIFEST)
    verify_manifest(PARENT / "manifest.json")
    verify_manifest(EARLIER / "manifest.json")
    OUT.mkdir(parents=True)
    contract = {
        "role": "adaptive opened-data observed-news CatBoost tier screen",
        "followup_to": str((EARLIER / "report.json").relative_to(REPO_ROOT)),
        "selection_fold": 4, "later_reporting_fold": 5,
        "later_fold_already_opened": True,
        "source_policy": "only rows with recorded recent article; no missing-feed zero-news inference",
        "tiers": {name: list(indices) for name, indices in TIERS.items()},
        "feature_names": list(FEATURE_NAMES),
        "configs": [{"name": name, "parameters": parameters} for name, parameters in CONFIGS],
        "model_parameters_common": {"learning_rate": .05, "l2_leaf_reg": 10.0},
        "training": "fold 3 to fold 4; folds 3-4 to fold 5, 30-minute purge, market disjoint",
        "metric": "row mean log loss primary; Brier and AP secondary",
        "catboost_version": catboost.__version__,
        "limits": ["opened outcome and adaptive model search", "uncertified source versions and feed completeness",
                   "historical semantic representation saw later text",
                   "market groups do not certify family/calendar independence"],
        "inputs": [{"path": str(path.relative_to(REPO_ROOT)), "sha256": sha256_file(path)}
                   for path in (PARENT / "predictions.npz", OOF, EVENTS,
                                EARLIER / "predictions.npz")],
        "created_at": datetime.now(timezone.utc).isoformat(),
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
    exposed = np.flatnonzero(news[:, 0] > 0)
    matrix = observed_features(rows, events, news)
    y = rows["label"][exposed]
    market = rows["market"][exposed]
    minute = rows["minute"][exposed]
    fold = rows["fold"][exposed]
    with np.load(EARLIER / "predictions.npz", allow_pickle=False) as earlier:
        for current in (4, 5):
            mask = fold == current
            if not np.array_equal(market[mask], earlier[f"market{current}"]) or not np.array_equal(y[mask], earlier[f"label{current}"]):
                raise RuntimeError(f"Earlier observed row mismatch: {current}")
    results = {}
    scores = {}
    for current in (4, 5):
        validation_mask = fold == current
        eval_start = int(minute[validation_mask].min())
        training_mask = (fold >= 3) & (fold < current) & (minute + 30 < eval_start)
        train = np.flatnonzero(training_mask)
        validation = np.flatnonzero(validation_mask)
        if not len(train) or np.intersect1d(market[train], market[validation]).size:
            raise RuntimeError("Market group split failure")
        if minute[train].max() + 30 >= eval_start:
            raise RuntimeError("Horizon purge failure")
        print(f"Fold {current}: {len(train)} train, {len(validation)} validation", flush=True)
        for tier, columns in TIERS.items():
            for name, parameters in CONFIGS:
                key = f"{tier}__{name}"
                entry = results.setdefault(key, {"tier": tier, "name": name,
                                                 "parameters": parameters, "folds": {}})
                try:
                    model = CatBoostClassifier(
                        learning_rate=.05, l2_leaf_reg=10.0, loss_function="Logloss",
                        random_seed=907, thread_count=2, verbose=False,
                        allow_writing_files=False, **parameters,
                    )
                    model.fit(matrix[train][:, columns], y[train])
                    score = model.predict_proba(matrix[validation][:, columns])[:, 1]
                    if not np.all(np.isfinite(score)):
                        raise RuntimeError("Nonfinite score")
                    entry["folds"][str(current)] = {"status": "complete", "metrics": metric(y[validation], score)}
                    scores[f"{key}__fold{current}"] = score
                except Exception as error:
                    entry["folds"][str(current)] = {"status": "failed", "error": str(error)}
                result = entry["folds"][str(current)]
                print(f"  {key}: {result['status']}" + (f" LL={result['metrics']['log_loss']:.6f}"
                      if result["status"] == "complete" else ""), flush=True)
        write_json(OUT / "checkpoint.json", {"results": results})

    eligible = [(key, value) for key, value in results.items()
                if all(value["folds"].get(str(f), {}).get("status") == "complete" for f in (4, 5))]
    selected = {}
    for group, tiers in (("context", ("context",)), ("news", ("timing", "semantic"))):
        options = [(key, value) for key, value in eligible if value["tier"] in tiers]
        if not options:
            selected[group] = None
            continue
        key, value = min(options, key=lambda pair: (pair[1]["folds"]["4"]["metrics"]["log_loss"], pair[0]))
        selected[group] = {"key": key,
                           "fold4_log_loss": value["folds"]["4"]["metrics"]["log_loss"],
                           "fold5_log_loss": value["folds"]["5"]["metrics"]["log_loss"]}
    comparison = None
    if selected["context"] and selected["news"]:
        mask = fold == 5
        context = scores[f"{selected['context']['key']}__fold5"]
        news_score = scores[f"{selected['news']['key']}__fold5"]
        comparison = {"news_vs_context_log_loss": block_interval(
                          {"market": market[mask]}, point_loss(y[mask], context)-point_loss(y[mask], news_score)),
                      "news_vs_context_brier_improvement": float(metric(y[mask], context)["brier"]-metric(y[mask], news_score)["brier"]),
                      "news_vs_context_ap_gain": float(metric(y[mask], news_score)["average_precision"]-metric(y[mask], context)["average_precision"])}
    np.savez_compressed(OUT / "predictions.npz", **scores)
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
