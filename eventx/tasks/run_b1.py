"""Compare market-only B0 with market-plus-KOL B1 on validation only.

The default command never reads a test label into a model row or reports test metrics.
It fixes B0 and B1 to the same eligible 30-minute observations and uses the same
dependency-free logistic learner for a controlled incremental-feature comparison.
"""

from __future__ import annotations

import argparse
import json
import math
import random
from datetime import datetime
from pathlib import Path
from typing import Any, Iterator, NamedTuple

from eventx.features.build_kol_features import cadence_match, hash_file, parse_ts
from eventx.settings import REPO_ROOT

MARKET_FEATURES = [
    "price_logodds",
    "momentum_5m",
    "momentum_30m",
    "momentum_120m",
    "realized_vol_30m",
    "realized_vol_240m",
    "trade_count_60m",
    "trade_count_240m",
    "notional_60m",
    "notional_240m",
    "minutes_since_trade",
]
KOL_FEATURES = [
    "kol_tweet_count_30m",
    "kol_tweet_count_120m",
    "kol_tweet_count_360m",
    "kol_tweet_count_1440m",
    "kol_unique_handles_30m",
    "kol_unique_handles_120m",
    "kol_unique_handles_360m",
    "kol_unique_handles_1440m",
    "kol_handle_entropy_24h",
    "kol_top_handle_share_24h",
    "kol_has_history",
    "kol_minutes_since_latest",
    "kol_prior_24h_count_excluding_2h",
    "kol_activity_burst_log_2h_vs_prior_24h",
]


class Example(NamedTuple):
    market: list[float]
    kol: list[float]
    label: int
    kol_active_24h: bool
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


def transform(name: str, value: Any) -> float:
    number = float(value)
    log_families = (
        "notional_",
        "trade_count_",
        "kol_tweet_count_",
        "kol_unique_handles_",
        "kol_minutes_since_",
        "kol_prior_",
    )
    return math.log1p(number) if name.startswith(log_families) else number


def load_train_validation(
    labels_path: Path,
    features_path: Path,
    cadence_min: int,
) -> tuple[dict[str, list[Example]], dict[str, Any]]:
    feature_rows = iter(read_jsonl(features_path))
    feature = next(feature_rows, None)
    datasets: dict[str, list[Example]] = {"train": [], "validation": []}
    matched_rows = 0
    test_feature_rows_skipped = 0
    for label_row in read_jsonl(labels_path):
        timestamp = str(label_row["ts"])
        ts_minute = int(timestamp[11:13]) * 60 + int(timestamp[14:16])
        if (
            timestamp[17:19] != "00"
            or ts_minute % cadence_min
            or not cadence_match(
                # Avoid reparsing all timestamps via datetime.fromisoformat here.
                _timestamp_for_cadence(timestamp),
                cadence_min,
            )
        ):
            continue
        if feature is None:
            raise SystemExit("Feature artifact ended before the cadence-filtered labels.")
        if row_key(label_row) != row_key(feature):
            raise SystemExit(
                "Feature/label key mismatch: "
                f"label={row_key(label_row)} feature={row_key(feature)}"
            )
        matched_rows += 1
        split = str(label_row["split"])
        if split == "test":
            test_feature_rows_skipped += 1
        elif split in datasets and int(label_row["eligible"]):
            market = [transform(name, label_row[name]) for name in MARKET_FEATURES]
            kol = [transform(name, feature[name]) for name in KOL_FEATURES]
            datasets[split].append(
                Example(
                    market=market,
                    kol=kol,
                    label=int(label_row["y_jump"]),
                    kol_active_24h=int(feature["kol_tweet_count_1440m"]) > 0,
                    market_id=str(label_row["market_id"]),
                    ts=parse_ts(timestamp),
                )
            )
        feature = next(feature_rows, None)
    if feature is not None or next(feature_rows, None) is not None:
        raise SystemExit("Feature artifact has unmatched trailing rows.")
    stats = {
        "cadence_rows_matched": matched_rows,
        "test_feature_rows_skipped_without_accessing_y_jump": test_feature_rows_skipped,
        "examples": {split: len(rows) for split, rows in datasets.items()},
        "jump_counts": {
            split: sum(example.label for example in rows) for split, rows in datasets.items()
        },
        "kol_active_24h": {
            split: sum(example.kol_active_24h for example in rows)
            for split, rows in datasets.items()
        },
    }
    return datasets, stats


def _timestamp_for_cadence(value: str) -> datetime:
    """Parse only because cadence_match is the single cadence contract."""
    return parse_ts(value)


def standardization(
    rows: list[list[float]],
) -> tuple[list[float], list[float]]:
    width = len(rows[0])
    means = [sum(row[j] for row in rows) / len(rows) for j in range(width)]
    scales = []
    for j in range(width):
        variance = sum((row[j] - means[j]) ** 2 for row in rows) / len(rows)
        scales.append(max(math.sqrt(variance), 1.0e-8))
    return means, scales


def standardized(
    rows: list[list[float]],
    means: list[float],
    scales: list[float],
) -> list[list[float]]:
    return [
        [(value - means[j]) / scales[j] for j, value in enumerate(row)]
        for row in rows
    ]


def sigmoid(value: float) -> float:
    if value >= 0:
        z = math.exp(-min(value, 40))
        return 1 / (1 + z)
    z = math.exp(max(value, -40))
    return z / (1 + z)


def fit_logistic(
    vectors: list[list[float]],
    labels: list[int],
    epochs: int,
    learning_rate: float,
    l2: float,
) -> tuple[float, list[float]]:
    rng = random.Random(11)
    order = list(range(len(vectors)))
    intercept = 0.0
    weights = [0.0] * len(vectors[0])
    step = 0
    for _ in range(epochs):
        rng.shuffle(order)
        for index in order:
            vector = vectors[index]
            label = labels[index]
            prediction = sigmoid(intercept + sum(w * x for w, x in zip(weights, vector)))
            error = prediction - label
            rate = learning_rate / math.sqrt(1 + step / 10_000)
            intercept -= rate * error
            for j, value in enumerate(vector):
                weights[j] -= rate * (error * value + l2 * weights[j])
            step += 1
    return intercept, weights


def predict(
    vectors: list[list[float]],
    intercept: float,
    weights: list[float],
) -> list[float]:
    return [
        sigmoid(intercept + sum(weight * value for weight, value in zip(weights, vector)))
        for vector in vectors
    ]


def average_precision(labels: list[int], scores: list[float]) -> float | None:
    positives = sum(labels)
    if not positives:
        return None
    ranked = sorted(zip(scores, labels), key=lambda pair: pair[0], reverse=True)
    true_positives = false_positives = 0
    result = 0.0
    index = 0
    while index < len(ranked):
        score = ranked[index][0]
        group_positives = group_size = 0
        while index < len(ranked) and ranked[index][0] == score:
            group_positives += ranked[index][1]
            group_size += 1
            index += 1
        previous_true_positives = true_positives
        true_positives += group_positives
        false_positives += group_size - group_positives
        precision = true_positives / (true_positives + false_positives)
        recall_increment = (true_positives - previous_true_positives) / positives
        result += recall_increment * precision
    return result


def metrics(labels: list[int], scores: list[float]) -> dict[str, float | int | None]:
    return {
        "rows": len(labels),
        "positives": sum(labels),
        "jump_rate": sum(labels) / len(labels),
        "mean_prediction": sum(scores) / len(scores),
        "brier": sum((label - score) ** 2 for label, score in zip(labels, scores))
        / len(labels),
        "average_precision": average_precision(labels, scores),
    }


def model_result(
    train_vectors: list[list[float]],
    train_labels: list[int],
    validation_vectors: list[list[float]],
    validation_labels: list[int],
    feature_names: list[str],
    epochs: int,
) -> tuple[dict[str, Any], list[float]]:
    means, scales = standardization(train_vectors)
    train_standardized = standardized(train_vectors, means, scales)
    validation_standardized = standardized(validation_vectors, means, scales)
    intercept, weights = fit_logistic(
        train_standardized,
        train_labels,
        epochs=epochs,
        learning_rate=0.02,
        l2=1.0e-4,
    )
    scores = predict(validation_standardized, intercept, weights)
    result = {
        "validation": metrics(validation_labels, scores),
        "intercept": intercept,
        "coefficients": dict(zip(feature_names, weights)),
        "standardization": {
            name: {"mean": mean, "scale": scale}
            for name, mean, scale in zip(feature_names, means, scales)
        },
    }
    return result, scores


def main() -> None:
    parser = argparse.ArgumentParser(description="Run EventX B0-vs-B1 validation comparison")
    parser.add_argument("--labels", type=Path)
    parser.add_argument("--features", type=Path)
    parser.add_argument("--feature-report", type=Path)
    parser.add_argument("--out", type=Path)
    parser.add_argument("--epochs", type=int, default=8)
    args = parser.parse_args()

    root = REPO_ROOT / "data" / "v1" / "toy"
    labels_path = args.labels or root / "labels_30m.jsonl"
    features_path = args.features or root / "kol_features_30m.jsonl"
    feature_report_path = args.feature_report or root / "kol_features_30m_report.json"
    out_path = args.out or root / "b1_validation_results.json"
    feature_report = json.loads(feature_report_path.read_text())
    if hash_file(features_path)["sha256"] != feature_report["artifact"]["sha256"]:
        raise SystemExit("KOL feature artifact hash does not match its report.")
    if not feature_report["point_in_time_validation"]["passed"]:
        raise SystemExit("KOL feature report did not pass point-in-time validation.")
    if not feature_report["feature_invariants"]["passed"]:
        raise SystemExit("KOL feature report did not pass invariant validation.")

    cadence_min = int(feature_report["cadence_min"])
    datasets, load_stats = load_train_validation(labels_path, features_path, cadence_min)
    train = datasets["train"]
    validation = datasets["validation"]
    if not train or not validation or len({example.label for example in train}) < 2:
        raise SystemExit("Insufficient train/validation class coverage.")
    train_labels = [example.label for example in train]
    validation_labels = [example.label for example in validation]
    b0_train = [example.market for example in train]
    b0_validation = [example.market for example in validation]
    b1_train = [example.market + example.kol for example in train]
    b1_validation = [example.market + example.kol for example in validation]

    b0, b0_scores = model_result(
        b0_train,
        train_labels,
        b0_validation,
        validation_labels,
        MARKET_FEATURES,
        args.epochs,
    )
    b1, b1_scores = model_result(
        b1_train,
        train_labels,
        b1_validation,
        validation_labels,
        MARKET_FEATURES + KOL_FEATURES,
        args.epochs,
    )
    prevalence = sum(train_labels) / len(train_labels)
    prevalence_metrics = metrics(validation_labels, [prevalence] * len(validation_labels))
    b0_metrics = b0["validation"]
    b1_metrics = b1["validation"]
    active_indices = [
        index for index, example in enumerate(validation) if example.kol_active_24h
    ]
    inactive_indices = [
        index for index, example in enumerate(validation) if not example.kol_active_24h
    ]

    def subset_metrics(scores: list[float], indices: list[int]) -> dict[str, Any] | None:
        if not indices:
            return None
        return metrics(
            [validation_labels[index] for index in indices],
            [scores[index] for index in indices],
        )

    result = {
        "status": "validation_complete_test_untouched",
        "dataset_id": feature_report["dataset_id"],
        "kol_rule_id": feature_report["kol_rule_id"],
        "model": "standardized_logistic_sgd",
        "fixed_hyperparameters": {
            "epochs": args.epochs,
            "learning_rate": 0.02,
            "l2": 1.0e-4,
            "shuffle_seed": 11,
        },
        "cadence_min": cadence_min,
        "load_validation": load_stats,
        "features": {
            "b0_market_only": MARKET_FEATURES,
            "b1_market_plus_kol": MARKET_FEATURES + KOL_FEATURES,
        },
        "validation": {
            "prevalence_baseline": prevalence_metrics,
            "b0_market_only": b0_metrics,
            "b1_market_plus_kol": b1_metrics,
            "incremental_b1_over_b0": {
                "delta_average_precision": (
                    float(b1_metrics["average_precision"])
                    - float(b0_metrics["average_precision"])
                ),
                "brier_improvement": float(b0_metrics["brier"]) - float(b1_metrics["brier"]),
            },
            "kol_active_24h": {
                "rows": len(active_indices),
                "b0_market_only": subset_metrics(b0_scores, active_indices),
                "b1_market_plus_kol": subset_metrics(b1_scores, active_indices),
            },
            "kol_inactive_24h": {
                "rows": len(inactive_indices),
                "b0_market_only": subset_metrics(b0_scores, inactive_indices),
                "b1_market_plus_kol": subset_metrics(b1_scores, inactive_indices),
            },
        },
        "locked_candidate_models": {
            "b0_market_only": b0,
            "b1_market_plus_kol": b1,
        },
        "test_policy": (
            "Test feature rows were alignment-checked and skipped before y_jump access. "
            "No test labels or metrics are present. Do not evaluate test until the full "
            "baseline ladder and model specifications are frozen."
        ),
        "inputs": {
            "labels": str(labels_path.resolve().relative_to(REPO_ROOT)),
            "features": str(features_path.resolve().relative_to(REPO_ROOT)),
            "feature_report": str(feature_report_path.resolve().relative_to(REPO_ROOT)),
        },
    }
    out_path.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
    print(json.dumps(result["validation"], indent=2, sort_keys=True))
    print(f"Wrote validation-only result: {out_path}")


if __name__ == "__main__":
    main()
