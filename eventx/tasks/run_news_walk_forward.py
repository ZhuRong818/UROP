"""Purged walk-forward evaluation of the EventX structured-news B1 baseline."""

from __future__ import annotations

import argparse
import json
import math
from collections import defaultdict
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Iterator

from eventx.features.build_kol_features import hash_file, parse_ts
from eventx.settings import REPO_ROOT
from eventx.tasks.run_b1 import MARKET_FEATURES, metrics, model_result, transform
from eventx.tasks.run_b1_walk_forward import fold_boundaries, sign_test_p_value, summary
from eventx.tasks.run_news_baseline import (
    NEWS_CORE_FEATURES,
    NEWS_FEATURES,
    NewsExample,
    news_transform,
    row_key,
    selected_news_vector,
)
from eventx.tasks.validate_b1_robustness import block_bootstrap


def read_jsonl(path: Path) -> Iterator[dict[str, Any]]:
    with path.open() as handle:
        for line in handle:
            if line.strip():
                yield json.loads(line)


def load_pretest_examples(
    labels_path: Path,
    features_path: Path,
    cadence_min: int,
    pretest_end: datetime,
) -> tuple[list[NewsExample], dict[str, int]]:
    feature_rows = iter(read_jsonl(features_path))
    feature = next(feature_rows, None)
    examples = []
    matched = ineligible = skipped = 0
    for label_row in read_jsonl(labels_path):
        timestamp = str(label_row["ts"])
        minute = int(timestamp[11:13]) * 60 + int(timestamp[14:16])
        if timestamp[17:19] != "00" or minute % cadence_min:
            continue
        if feature is None or row_key(label_row) != row_key(feature):
            raise SystemExit("News feature and label artifacts are not aligned.")
        matched += 1
        timestamp_dt = parse_ts(timestamp)
        if timestamp_dt >= pretest_end:
            skipped += 1
        elif not int(label_row["eligible"]):
            ineligible += 1
        else:
            examples.append(
                NewsExample(
                    market=[
                        transform(name, label_row[name]) for name in MARKET_FEATURES
                    ],
                    news=[
                        news_transform(name, feature[name]) for name in NEWS_FEATURES
                    ],
                    label=int(label_row["y_jump"]),
                    news_active_24h=int(feature["news_article_count_1440m"]) > 0,
                    market_id=str(label_row["market_id"]),
                    ts=timestamp_dt,
                )
            )
        feature = next(feature_rows, None)
    if feature is not None or next(feature_rows, None) is not None:
        raise SystemExit("News feature artifact has unmatched trailing rows.")
    examples.sort(key=lambda example: (example.ts, example.market_id))
    return examples, {
        "cadence_rows_matched": matched,
        "ineligible_pretest_rows": ineligible,
        "post_pretest_rows_skipped_without_accessing_y_jump": skipped,
    }


def pair_metrics(
    labels: list[int],
    b0_scores: list[float],
    b1_scores: list[float],
) -> dict[str, Any]:
    b0 = metrics(labels, b0_scores)
    b1 = metrics(labels, b1_scores)
    return {
        "b0_market_only": b0,
        "b1_market_plus_news": b1,
        "incremental_b1_over_b0": {
            "delta_average_precision": float(b1["average_precision"])
            - float(b0["average_precision"]),
            "brier_improvement": float(b0["brier"]) - float(b1["brier"]),
        },
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Run EventX news B1 walk-forward CV")
    parser.add_argument("--labels", type=Path)
    parser.add_argument("--features", type=Path)
    parser.add_argument("--feature-report", type=Path)
    parser.add_argument("--toy-freeze", type=Path)
    parser.add_argument("--out", type=Path)
    parser.add_argument("--n-splits", type=int, default=5)
    parser.add_argument("--purge-min", type=int, default=30)
    parser.add_argument("--epochs", type=int, default=8)
    parser.add_argument("--bootstrap-samples", type=int, default=2000)
    parser.add_argument("--block-minutes", type=int, default=360)
    parser.add_argument("--feature-set", choices=["core", "rich"], default="core")
    args = parser.parse_args()

    root = REPO_ROOT / "data" / "v1" / "toy"
    labels_path = args.labels or root / "labels_30m.jsonl"
    features_path = args.features or root / "news_features_5m.jsonl"
    report_path = args.feature_report or root / "news_features_5m_report.json"
    freeze_path = args.toy_freeze or root / "frozen_manifest.json"
    out_path = args.out or root / "news_b1_walk_forward_cv_5m.json"
    report = json.loads(report_path.read_text())
    freeze = json.loads(freeze_path.read_text())
    if hash_file(features_path)["sha256"] != report["artifact"]["sha256"]:
        raise SystemExit("News feature artifact hash does not match its report.")
    test_start = parse_ts(freeze["split_boundaries"]["test_start"])
    pretest_start = parse_ts(freeze["window"]["start"])
    pretest_end = test_start - timedelta(minutes=args.purge_min)
    cadence_min = int(report["cadence_min"])
    examples, load_stats = load_pretest_examples(
        labels_path,
        features_path,
        cadence_min,
        pretest_end,
    )
    purge = timedelta(minutes=args.purge_min)
    selected_features = (
        NEWS_CORE_FEATURES if args.feature_set == "core" else NEWS_FEATURES
    )
    boundaries = fold_boundaries(pretest_start, pretest_end, args.n_splits)
    folds = []
    oof_examples: list[NewsExample] = []
    oof_fold_numbers: list[int] = []
    oof_labels: list[int] = []
    oof_b0_scores: list[float] = []
    oof_b1_scores: list[float] = []
    for fold_number, (validation_start, validation_end) in enumerate(
        boundaries,
        start=1,
    ):
        training_end = validation_start - purge
        train = [example for example in examples if example.ts < training_end]
        validation = [
            example
            for example in examples
            if validation_start <= example.ts < validation_end
        ]
        train_labels = [example.label for example in train]
        validation_labels = [example.label for example in validation]
        if not train or not validation or len(set(train_labels)) < 2:
            raise SystemExit(f"Fold {fold_number} lacks usable class coverage.")
        b0, b0_scores = model_result(
            [example.market for example in train],
            train_labels,
            [example.market for example in validation],
            validation_labels,
            MARKET_FEATURES,
            args.epochs,
        )
        b1, b1_scores = model_result(
            [
                example.market + selected_news_vector(example, selected_features)
                for example in train
            ],
            train_labels,
            [
                example.market + selected_news_vector(example, selected_features)
                for example in validation
            ],
            validation_labels,
            MARKET_FEATURES + selected_features,
            args.epochs,
        )
        comparison = pair_metrics(validation_labels, b0_scores, b1_scores)
        active = sum(example.news_active_24h for example in validation)
        folds.append(
            {
                "fold": fold_number,
                "training_end_exclusive": training_end.isoformat().replace(
                    "+00:00", "Z"
                ),
                "validation_start": validation_start.isoformat().replace("+00:00", "Z"),
                "validation_end_exclusive": validation_end.isoformat().replace(
                    "+00:00", "Z"
                ),
                "train_rows": len(train),
                "train_positives": sum(train_labels),
                "validation_rows": len(validation),
                "validation_positives": sum(validation_labels),
                "news_active_24h_rows": active,
                "news_active_24h_share": active / len(validation),
                **comparison,
                "model_coefficients": {
                    "b0_market_only": b0["coefficients"],
                    "b1_market_plus_news": b1["coefficients"],
                },
            }
        )
        oof_examples.extend(validation)
        oof_fold_numbers.extend([fold_number] * len(validation))
        oof_labels.extend(validation_labels)
        oof_b0_scores.extend(b0_scores)
        oof_b1_scores.extend(b1_scores)

    oof = pair_metrics(oof_labels, oof_b0_scores, oof_b1_scores)
    fold_ap = [
        float(fold["incremental_b1_over_b0"]["delta_average_precision"])
        for fold in folds
    ]
    fold_brier = [
        float(fold["incremental_b1_over_b0"]["brier_improvement"]) for fold in folds
    ]
    positive_ap = sum(value > 0 for value in fold_ap)
    positive_brier = sum(value > 0 for value in fold_brier)
    groups: dict[str, list[int]] = defaultdict(list)
    for index, (fold_number, example) in enumerate(
        zip(oof_fold_numbers, oof_examples)
    ):
        groups[f"{fold_number}:{example.market_id}"].append(index)
    for indices in groups.values():
        indices.sort(key=lambda index: oof_examples[index].ts)
    bootstrap = block_bootstrap(
        oof_labels,
        oof_b0_scores,
        oof_b1_scores,
        dict(groups),
        block_rows=math.ceil(args.block_minutes / cadence_min),
        cadence_min=cadence_min,
        samples=args.bootstrap_samples,
        seed=53,
    )
    aggregate = oof["incremental_b1_over_b0"]
    stability_gate = {
        "aggregate_delta_average_precision_positive": float(
            aggregate["delta_average_precision"]
        )
        > 0,
        "aggregate_brier_improvement_positive": float(
            aggregate["brier_improvement"]
        )
        > 0,
        "average_precision_positive_in_at_least_4_of_5_folds": positive_ap
        >= math.ceil(args.n_splits * 0.8),
        "brier_positive_in_at_least_4_of_5_folds": positive_brier
        >= math.ceil(args.n_splits * 0.8),
        "bootstrap_brier_ci_lower_above_zero": float(
            bootstrap["brier_improvement"]["ci_95_lower"]
        )
        > 0,
    }
    stability_gate["passed"] = all(stability_gate.values())
    result = {
        "status": (
            "ready_to_freeze" if stability_gate["passed"] else "do_not_freeze"
        ),
        "dataset_id": report["dataset_id"],
        "news_rule_id": report["news_rule_id"],
        "feature_set": args.feature_set,
        "news_features": selected_features,
        "protocol": {
            "type": "5-fold purged expanding-window",
            "cadence_min": cadence_min,
            "purge_min": args.purge_min,
            "pretest_label_end_exclusive": pretest_end.isoformat().replace(
                "+00:00", "Z"
            ),
        },
        "load_validation": load_stats,
        "folds": folds,
        "out_of_fold": {"rows": len(oof_labels), "positives": sum(oof_labels), **oof},
        "fold_stability": {
            "delta_average_precision": {
                **summary(fold_ap),
                "positive_folds": positive_ap,
                "one_sided_sign_test_p_value": sign_test_p_value(
                    positive_ap,
                    args.n_splits,
                ),
            },
            "brier_improvement": {
                **summary(fold_brier),
                "positive_folds": positive_brier,
                "one_sided_sign_test_p_value": sign_test_p_value(
                    positive_brier,
                    args.n_splits,
                ),
            },
        },
        "paired_block_bootstrap": bootstrap,
        "freeze_gate": stability_gate,
        "test_policy": (
            "Only pre-test labels ending before the frozen test boundary are used. "
            "No test label or metric is accessed."
        ),
        "inputs": {
            "labels": str(labels_path.resolve().relative_to(REPO_ROOT)),
            "features": str(features_path.resolve().relative_to(REPO_ROOT)),
            "feature_report": str(report_path.resolve().relative_to(REPO_ROOT)),
            "toy_freeze": str(freeze_path.resolve().relative_to(REPO_ROOT)),
        },
    }
    out_path.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
    print(
        json.dumps(
            {
                "status": result["status"],
                "out_of_fold": result["out_of_fold"],
                "fold_stability": result["fold_stability"],
                "bootstrap": {
                    "delta_average_precision": bootstrap[
                        "delta_average_precision"
                    ],
                    "brier_improvement": bootstrap["brier_improvement"],
                },
                "freeze_gate": result["freeze_gate"],
                "folds": [
                    {
                        "fold": fold["fold"],
                        "validation_rows": fold["validation_rows"],
                        "validation_positives": fold["validation_positives"],
                        "news_active_24h_rows": fold["news_active_24h_rows"],
                        **fold["incremental_b1_over_b0"],
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
