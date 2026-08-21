"""Purged expanding-window cross-validation for EventX B0 versus B1."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Iterator

from eventx.features.build_kol_features import hash_file, parse_ts
from eventx.settings import REPO_ROOT
from eventx.tasks.run_b1 import (
    KOL_FEATURES,
    MARKET_FEATURES,
    Example,
    metrics,
    model_result,
    transform,
)


def read_jsonl(path: Path) -> Iterator[dict[str, Any]]:
    with path.open() as handle:
        for line in handle:
            if line.strip():
                yield json.loads(line)


def row_key(row: dict[str, Any]) -> tuple[str, str, str, str]:
    return (
        str(row["venue"]),
        str(row["market_id"]),
        str(row["outcome_id"]),
        str(row["ts"]),
    )


def load_pretest_examples(
    labels_path: Path,
    features_path: Path,
    cadence_min: int,
    pretest_end_exclusive: datetime,
) -> tuple[list[Example], dict[str, int]]:
    feature_rows = iter(read_jsonl(features_path))
    feature = next(feature_rows, None)
    examples: list[Example] = []
    stats = {
        "cadence_rows_matched": 0,
        "ineligible_pretest_rows": 0,
        "post_pretest_rows_skipped_without_accessing_y_jump": 0,
    }
    for label_row in read_jsonl(labels_path):
        timestamp = str(label_row["ts"])
        minute_of_day = int(timestamp[11:13]) * 60 + int(timestamp[14:16])
        if timestamp[17:19] != "00" or minute_of_day % cadence_min:
            continue
        if feature is None:
            raise SystemExit("Feature artifact ended before cadence-filtered labels.")
        if row_key(label_row) != row_key(feature):
            raise SystemExit(
                "Feature/label key mismatch: "
                f"label={row_key(label_row)} feature={row_key(feature)}"
            )
        stats["cadence_rows_matched"] += 1
        timestamp_dt = parse_ts(timestamp)
        if timestamp_dt >= pretest_end_exclusive:
            stats["post_pretest_rows_skipped_without_accessing_y_jump"] += 1
        elif not int(label_row["eligible"]):
            stats["ineligible_pretest_rows"] += 1
        else:
            examples.append(
                Example(
                    market=[transform(name, label_row[name]) for name in MARKET_FEATURES],
                    kol=[transform(name, feature[name]) for name in KOL_FEATURES],
                    label=int(label_row["y_jump"]),
                    kol_active_24h=int(feature["kol_tweet_count_1440m"]) > 0,
                    market_id=str(label_row["market_id"]),
                    ts=timestamp_dt,
                )
            )
        feature = next(feature_rows, None)
    if feature is not None or next(feature_rows, None) is not None:
        raise SystemExit("Feature artifact has unmatched trailing rows.")
    examples.sort(key=lambda example: (example.ts, example.market_id))
    return examples, stats


def fold_boundaries(
    start: datetime,
    end: datetime,
    n_splits: int,
) -> list[tuple[datetime, datetime]]:
    if n_splits <= 0 or end <= start:
        raise ValueError("Fold count and pre-test interval must be positive.")
    segment = (end - start) / (n_splits + 1)
    boundaries = []
    for fold_index in range(1, n_splits + 1):
        validation_start = start + segment * fold_index
        validation_end = (
            end if fold_index == n_splits else start + segment * (fold_index + 1)
        )
        boundaries.append((validation_start, validation_end))
    return boundaries


def sign_test_p_value(positive_folds: int, total_folds: int) -> float:
    if not 0 <= positive_folds <= total_folds:
        raise ValueError("Invalid sign-test counts.")
    return sum(
        math.comb(total_folds, successes)
        for successes in range(positive_folds, total_folds + 1)
    ) / (2**total_folds)


def summary(values: list[float]) -> dict[str, float]:
    return {
        "mean": sum(values) / len(values),
        "min": min(values),
        "max": max(values),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Run purged EventX B0-vs-B1 walk-forward CV")
    parser.add_argument("--labels", type=Path)
    parser.add_argument("--features", type=Path)
    parser.add_argument("--feature-report", type=Path)
    parser.add_argument("--toy-freeze", type=Path)
    parser.add_argument("--out", type=Path)
    parser.add_argument("--n-splits", type=int, default=5)
    parser.add_argument("--purge-min", type=int, default=30)
    parser.add_argument("--epochs", type=int, default=8)
    args = parser.parse_args()
    if args.n_splits <= 0 or args.purge_min <= 0 or args.epochs <= 0:
        raise SystemExit("Split count, purge duration, and epochs must be positive.")

    root = REPO_ROOT / "data" / "v1" / "toy"
    labels_path = args.labels or root / "labels_30m.jsonl"
    features_path = args.features or root / "kol_features_5m.jsonl"
    feature_report_path = args.feature_report or root / "kol_features_5m_report.json"
    toy_freeze_path = args.toy_freeze or root / "frozen_manifest.json"
    out_path = args.out or root / "b1_walk_forward_cv_5m.json"
    feature_report = json.loads(feature_report_path.read_text())
    toy_freeze = json.loads(toy_freeze_path.read_text())
    if feature_report["dataset_id"] != toy_freeze["dataset_id"]:
        raise SystemExit("Feature and frozen toy dataset IDs do not match.")
    if hash_file(features_path)["sha256"] != feature_report["artifact"]["sha256"]:
        raise SystemExit("KOL feature artifact hash does not match its report.")
    if not feature_report["point_in_time_validation"]["passed"]:
        raise SystemExit("Feature artifact did not pass point-in-time validation.")

    test_start = parse_ts(toy_freeze["split_boundaries"]["test_start"])
    pretest_start = parse_ts(toy_freeze["window"]["start"])
    pretest_end_exclusive = test_start - timedelta(minutes=args.purge_min)
    cadence_min = int(feature_report["cadence_min"])
    examples, load_stats = load_pretest_examples(
        labels_path,
        features_path,
        cadence_min,
        pretest_end_exclusive,
    )
    boundaries = fold_boundaries(pretest_start, pretest_end_exclusive, args.n_splits)
    purge = timedelta(minutes=args.purge_min)
    folds: list[dict[str, Any]] = []
    all_oof_labels: list[int] = []
    all_oof_b0_scores: list[float] = []
    all_oof_b1_scores: list[float] = []
    all_oof_keys: set[tuple[str, datetime]] = set()
    fold_model_hashes: list[str] = []
    for fold_number, (validation_start, validation_end) in enumerate(boundaries, start=1):
        training_end = validation_start - purge
        train = [example for example in examples if example.ts < training_end]
        validation = [
            example
            for example in examples
            if validation_start <= example.ts < validation_end
        ]
        if not train or not validation:
            raise SystemExit(f"Fold {fold_number} has no train or validation rows.")
        train_labels = [example.label for example in train]
        validation_labels = [example.label for example in validation]
        if len(set(train_labels)) < 2 or len(set(validation_labels)) < 2:
            raise SystemExit(f"Fold {fold_number} lacks binary class coverage.")

        b0, b0_scores = model_result(
            [example.market for example in train],
            train_labels,
            [example.market for example in validation],
            validation_labels,
            MARKET_FEATURES,
            epochs=args.epochs,
        )
        b1, b1_scores = model_result(
            [example.market + example.kol for example in train],
            train_labels,
            [example.market + example.kol for example in validation],
            validation_labels,
            MARKET_FEATURES + KOL_FEATURES,
            epochs=args.epochs,
        )
        b0_metrics = b0["validation"]
        b1_metrics = b1["validation"]
        delta_ap = float(b1_metrics["average_precision"]) - float(
            b0_metrics["average_precision"]
        )
        brier_improvement = float(b0_metrics["brier"]) - float(b1_metrics["brier"])
        active_indices = [
            index for index, example in enumerate(validation) if example.kol_active_24h
        ]
        model_payload = json.dumps(
            {"b0": b0, "b1": b1},
            sort_keys=True,
            separators=(",", ":"),
        )
        model_hash = hashlib.sha256(model_payload.encode()).hexdigest()
        fold_model_hashes.append(model_hash)
        folds.append(
            {
                "fold": fold_number,
                "training": {
                    "start": min(example.ts for example in train).isoformat().replace(
                        "+00:00", "Z"
                    ),
                    "end_exclusive": training_end.isoformat().replace("+00:00", "Z"),
                    "rows": len(train),
                    "positives": sum(train_labels),
                    "markets": len({example.market_id for example in train}),
                },
                "purge": {
                    "start": training_end.isoformat().replace("+00:00", "Z"),
                    "end": validation_start.isoformat().replace("+00:00", "Z"),
                    "minutes": args.purge_min,
                },
                "validation": {
                    "start": validation_start.isoformat().replace("+00:00", "Z"),
                    "end_exclusive": validation_end.isoformat().replace("+00:00", "Z"),
                    "rows": len(validation),
                    "positives": sum(validation_labels),
                    "markets": len({example.market_id for example in validation}),
                    "kol_active_24h_rows": len(active_indices),
                    "b0_market_only": b0_metrics,
                    "b1_market_plus_kol": b1_metrics,
                    "incremental_b1_over_b0": {
                        "delta_average_precision": delta_ap,
                        "brier_improvement": brier_improvement,
                    },
                },
                "model_sha256": model_hash,
            }
        )
        for example, label, b0_score, b1_score in zip(
            validation,
            validation_labels,
            b0_scores,
            b1_scores,
        ):
            key = (example.market_id, example.ts)
            if key in all_oof_keys:
                raise SystemExit(f"Duplicate out-of-fold prediction key: {key}")
            all_oof_keys.add(key)
            all_oof_labels.append(label)
            all_oof_b0_scores.append(b0_score)
            all_oof_b1_scores.append(b1_score)

    oof_b0 = metrics(all_oof_labels, all_oof_b0_scores)
    oof_b1 = metrics(all_oof_labels, all_oof_b1_scores)
    oof_delta_ap = float(oof_b1["average_precision"]) - float(oof_b0["average_precision"])
    oof_brier_improvement = float(oof_b0["brier"]) - float(oof_b1["brier"])
    fold_delta_ap = [
        float(fold["validation"]["incremental_b1_over_b0"]["delta_average_precision"])
        for fold in folds
    ]
    fold_brier = [
        float(fold["validation"]["incremental_b1_over_b0"]["brier_improvement"])
        for fold in folds
    ]
    positive_ap_folds = sum(value > 0 for value in fold_delta_ap)
    positive_brier_folds = sum(value > 0 for value in fold_brier)
    stability_gate = {
        "aggregate_delta_average_precision_positive": oof_delta_ap > 0,
        "aggregate_brier_improvement_positive": oof_brier_improvement > 0,
        "average_precision_positive_in_at_least_4_of_5_folds": positive_ap_folds
        >= math.ceil(args.n_splits * 0.8),
        "brier_positive_in_at_least_4_of_5_folds": positive_brier_folds
        >= math.ceil(args.n_splits * 0.8),
    }
    stability_gate["passed"] = all(stability_gate.values())
    result = {
        "status": (
            "temporally_stable_candidate"
            if stability_gate["passed"]
            else "temporal_instability_detected"
        ),
        "dataset_id": feature_report["dataset_id"],
        "kol_rule_id": feature_report["kol_rule_id"],
        "protocol": {
            "type": "expanding-window walk-forward",
            "n_splits": args.n_splits,
            "cadence_min": cadence_min,
            "label_horizon_min": args.purge_min,
            "purge_min": args.purge_min,
            "pretest_start": pretest_start.isoformat().replace("+00:00", "Z"),
            "pretest_label_end_exclusive": pretest_end_exclusive.isoformat().replace(
                "+00:00", "Z"
            ),
            "fold_construction": (
                "Divide pre-test time into n_splits+1 equal segments; use each segment "
                "after the first as validation and all earlier rows before a 30-minute "
                "purge as expanding training data."
            ),
        },
        "fixed_model_specification": {
            "model": "standardized_logistic_sgd",
            "epochs": args.epochs,
            "learning_rate": 0.02,
            "l2": 1.0e-4,
            "shuffle_seed": 11,
            "b0_features": MARKET_FEATURES,
            "b1_added_features": KOL_FEATURES,
        },
        "load_validation": load_stats,
        "folds": folds,
        "out_of_fold": {
            "rows": len(all_oof_labels),
            "positives": sum(all_oof_labels),
            "unique_keys": len(all_oof_keys),
            "b0_market_only": oof_b0,
            "b1_market_plus_kol": oof_b1,
            "incremental_b1_over_b0": {
                "delta_average_precision": oof_delta_ap,
                "brier_improvement": oof_brier_improvement,
            },
        },
        "fold_stability": {
            "delta_average_precision": {
                **summary(fold_delta_ap),
                "positive_folds": positive_ap_folds,
                "one_sided_sign_test_p_value": sign_test_p_value(
                    positive_ap_folds,
                    args.n_splits,
                ),
            },
            "brier_improvement": {
                **summary(fold_brier),
                "positive_folds": positive_brier_folds,
                "one_sided_sign_test_p_value": sign_test_p_value(
                    positive_brier_folds,
                    args.n_splits,
                ),
            },
        },
        "stability_gate": stability_gate,
        "fold_model_hashes": fold_model_hashes,
        "test_policy": (
            "Only labels ending before the frozen test boundary are used. Rows at or "
            "after test_start - horizon are alignment-checked and skipped before y_jump "
            "access. No test metrics are computed."
        ),
        "inputs": {
            "labels": str(labels_path.resolve().relative_to(REPO_ROOT)),
            "features": str(features_path.resolve().relative_to(REPO_ROOT)),
            "feature_report": str(feature_report_path.resolve().relative_to(REPO_ROOT)),
            "toy_freeze": str(toy_freeze_path.resolve().relative_to(REPO_ROOT)),
        },
    }
    out_path.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
    print(
        json.dumps(
            {
                "status": result["status"],
                "out_of_fold": result["out_of_fold"],
                "fold_stability": result["fold_stability"],
                "stability_gate": result["stability_gate"],
                "folds": [
                    {
                        "fold": fold["fold"],
                        "train_rows": fold["training"]["rows"],
                        "validation_rows": fold["validation"]["rows"],
                        "validation_positives": fold["validation"]["positives"],
                        **fold["validation"]["incremental_b1_over_b0"],
                    }
                    for fold in folds
                ],
                "output": str(out_path),
            },
            indent=2,
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
