"""Validation-only EventX B0 versus structured-news B1 comparison."""

from __future__ import annotations

import argparse
import json
import math
from datetime import datetime
from pathlib import Path
from typing import Any, Iterator, NamedTuple

from eventx.features.build_kol_features import hash_file, parse_ts
from eventx.settings import REPO_ROOT
from eventx.tasks.run_b1 import MARKET_FEATURES, metrics, model_result, transform

NEWS_FEATURES = [
    "news_article_count_60m",
    "news_article_count_360m",
    "news_article_count_1440m",
    "news_unique_publishers_60m",
    "news_unique_publishers_360m",
    "news_unique_publishers_1440m",
    "news_unique_categories_60m",
    "news_unique_categories_360m",
    "news_unique_categories_1440m",
    "news_publisher_entropy_24h",
    "news_top_publisher_share_24h",
    "news_has_history",
    "news_minutes_since_latest",
    "news_prior_24h_count_excluding_6h",
    "news_activity_burst_log_6h_vs_prior_24h",
    "news_symbol_mapped",
]
NEWS_CORE_FEATURES = [
    "news_article_count_60m",
    "news_article_count_360m",
    "news_article_count_1440m",
    "news_symbol_mapped",
]


class NewsExample(NamedTuple):
    market: list[float]
    news: list[float]
    label: int
    news_active_24h: bool
    market_id: str
    ts: datetime


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


def news_transform(name: str, value: Any) -> float:
    number = float(value)
    log_families = (
        "news_article_count_",
        "news_unique_publishers_",
        "news_unique_categories_",
        "news_minutes_since_",
        "news_prior_",
    )
    return math.log1p(number) if name.startswith(log_families) else number


def selected_news_vector(
    example: NewsExample,
    feature_names: list[str],
) -> list[float]:
    by_name = dict(zip(NEWS_FEATURES, example.news))
    return [by_name[name] for name in feature_names]


def load_train_validation(
    labels_path: Path,
    features_path: Path,
    cadence_min: int,
) -> tuple[dict[str, list[NewsExample]], dict[str, Any]]:
    feature_rows = iter(read_jsonl(features_path))
    feature = next(feature_rows, None)
    datasets: dict[str, list[NewsExample]] = {"train": [], "validation": []}
    matched_rows = test_rows_skipped = 0
    for label_row in read_jsonl(labels_path):
        timestamp = str(label_row["ts"])
        minute = int(timestamp[11:13]) * 60 + int(timestamp[14:16])
        if timestamp[17:19] != "00" or minute % cadence_min:
            continue
        if feature is None or row_key(label_row) != row_key(feature):
            raise SystemExit("News feature and label artifacts are not aligned.")
        matched_rows += 1
        split = str(label_row["split"])
        if split == "test":
            test_rows_skipped += 1
        elif split in datasets and int(label_row["eligible"]):
            datasets[split].append(
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
                    ts=parse_ts(timestamp),
                )
            )
        feature = next(feature_rows, None)
    if feature is not None or next(feature_rows, None) is not None:
        raise SystemExit("News feature artifact has unmatched trailing rows.")
    return datasets, {
        "cadence_rows_matched": matched_rows,
        "test_feature_rows_skipped_without_accessing_y_jump": test_rows_skipped,
        "examples": {split: len(rows) for split, rows in datasets.items()},
        "positives": {
            split: sum(example.label for example in rows)
            for split, rows in datasets.items()
        },
        "news_active_24h": {
            split: sum(example.news_active_24h for example in rows)
            for split, rows in datasets.items()
        },
    }


def subset_metrics(
    examples: list[NewsExample],
    scores: list[float],
    active: bool,
) -> dict[str, Any] | None:
    indices = [
        index
        for index, example in enumerate(examples)
        if example.news_active_24h is active
    ]
    if not indices:
        return None
    return metrics(
        [examples[index].label for index in indices],
        [scores[index] for index in indices],
    )


def main() -> None:
    parser = argparse.ArgumentParser(description="Run EventX structured-news B1 validation")
    parser.add_argument("--labels", type=Path)
    parser.add_argument("--features", type=Path)
    parser.add_argument("--feature-report", type=Path)
    parser.add_argument("--out", type=Path)
    parser.add_argument("--epochs", type=int, default=8)
    parser.add_argument("--feature-set", choices=["core", "rich"], default="core")
    args = parser.parse_args()

    root = REPO_ROOT / "data" / "v1" / "toy"
    labels_path = args.labels or root / "labels_30m.jsonl"
    features_path = args.features or root / "news_features_5m.jsonl"
    report_path = args.feature_report or root / "news_features_5m_report.json"
    out_path = args.out or root / "news_b1_validation_results_5m.json"
    report = json.loads(report_path.read_text())
    if hash_file(features_path)["sha256"] != report["artifact"]["sha256"]:
        raise SystemExit("News feature artifact hash does not match its report.")
    if not report["point_in_time_validation"]["passed"]:
        raise SystemExit("News feature artifact failed point-in-time validation.")

    datasets, load_stats = load_train_validation(
        labels_path,
        features_path,
        int(report["cadence_min"]),
    )
    train = datasets["train"]
    validation = datasets["validation"]
    train_labels = [example.label for example in train]
    validation_labels = [example.label for example in validation]
    selected_features = (
        NEWS_CORE_FEATURES if args.feature_set == "core" else NEWS_FEATURES
    )
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
    b0_metrics = b0["validation"]
    b1_metrics = b1["validation"]
    result = {
        "status": "validation_complete_test_untouched",
        "dataset_id": report["dataset_id"],
        "news_rule_id": report["news_rule_id"],
        "model": "standardized_logistic_sgd",
        "feature_set": args.feature_set,
        "fixed_hyperparameters": {
            "epochs": args.epochs,
            "learning_rate": 0.02,
            "l2": 1.0e-4,
            "shuffle_seed": 11,
        },
        "features": {
            "b0_market_only": MARKET_FEATURES,
            "b1_market_plus_news": MARKET_FEATURES + selected_features,
        },
        "load_validation": load_stats,
        "validation": {
            "b0_market_only": b0_metrics,
            "b1_market_plus_news": b1_metrics,
            "incremental_b1_over_b0": {
                "delta_average_precision": float(b1_metrics["average_precision"])
                - float(b0_metrics["average_precision"]),
                "brier_improvement": float(b0_metrics["brier"])
                - float(b1_metrics["brier"]),
            },
            "news_active_24h": {
                "rows": sum(example.news_active_24h for example in validation),
                "b0_market_only": subset_metrics(validation, b0_scores, True),
                "b1_market_plus_news": subset_metrics(validation, b1_scores, True),
            },
            "news_inactive_24h": {
                "rows": sum(not example.news_active_24h for example in validation),
                "b0_market_only": subset_metrics(validation, b0_scores, False),
                "b1_market_plus_news": subset_metrics(validation, b1_scores, False),
            },
        },
        "locked_candidate_models": {
            "b0_market_only": b0,
            "b1_market_plus_news": b1,
        },
        "test_policy": (
            "Test feature rows are alignment-checked and skipped before y_jump access. "
            "No test label or metric is present."
        ),
        "inputs": {
            "labels": str(labels_path.resolve().relative_to(REPO_ROOT)),
            "features": str(features_path.resolve().relative_to(REPO_ROOT)),
            "feature_report": str(report_path.resolve().relative_to(REPO_ROOT)),
        },
    }
    out_path.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
    print(json.dumps(result["validation"], indent=2, sort_keys=True))
    print(f"Wrote validation-only result: {out_path}")


if __name__ == "__main__":
    main()
