"""Fit a dependency-free market-only logistic baseline on the EventX toy slice."""

from __future__ import annotations

import argparse
import json
import math
import random
from pathlib import Path
from typing import Any, Iterator

from eventx.settings import REPO_ROOT

FEATURES = [
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


def read_jsonl(path: Path) -> Iterator[dict[str, Any]]:
    with path.open() as handle:
        for line in handle:
            if line.strip():
                yield json.loads(line)


def reservoir_add(
    reservoir: list[tuple[list[float], int]], item: tuple[list[float], int],
    seen: int, limit: int, rng: random.Random,
) -> None:
    if len(reservoir) < limit:
        reservoir.append(item)
        return
    index = rng.randrange(seen)
    if index < limit:
        reservoir[index] = item


def load_rows(
    path: Path,
    stride: int,
    limit: int,
) -> tuple[dict[str, list[tuple[list[float], int]]], dict[str, int]]:
    rows: dict[str, list[tuple[list[float], int]]] = {
        "train": [],
        "validation": [],
        "test": [],
    }
    seen = {split: 0 for split in rows}
    rng = random.Random(7)
    for row in read_jsonl(path):
        split = row.get("split")
        if not row.get("eligible") or split not in seen:
            continue
        minute = int(row["ts"][14:16])
        if minute % stride:
            continue
        vector = [math.log1p(float(row[name])) if name.startswith("notional_") else float(row[name]) for name in FEATURES]
        item = (vector, int(row["y_jump"]))
        seen[split] += 1
        reservoir_add(rows[split], item, seen[split], limit, rng)
    return rows, seen


def standardize(
    train: list[tuple[list[float], int]],
    evaluation: list[list[tuple[list[float], int]]],
) -> tuple[list[float], list[float]]:
    width = len(FEATURES)
    means = [sum(row[0][j] for row in train) / len(train) for j in range(width)]
    scales = []
    for j in range(width):
        variance = sum((row[0][j] - means[j]) ** 2 for row in train) / len(train)
        scales.append(max(math.sqrt(variance), 1.0e-8))
    for rows in [train, *evaluation]:
        for vector, _label in rows:
            for j in range(width):
                vector[j] = (vector[j] - means[j]) / scales[j]
    return means, scales


def sigmoid(value: float) -> float:
    if value >= 0:
        z = math.exp(-min(value, 40))
        return 1 / (1 + z)
    z = math.exp(max(value, -40))
    return z / (1 + z)


def fit_logistic(
    train: list[tuple[list[float], int]], epochs: int, learning_rate: float, l2: float,
) -> tuple[float, list[float]]:
    rng = random.Random(11)
    intercept = 0.0
    weights = [0.0] * len(FEATURES)
    step = 0
    for _ in range(epochs):
        rng.shuffle(train)
        for vector, label in train:
            prediction = sigmoid(intercept + sum(w * x for w, x in zip(weights, vector)))
            error = prediction - label
            rate = learning_rate / math.sqrt(1 + step / 10_000)
            intercept -= rate * error
            for j, value in enumerate(vector):
                weights[j] -= rate * (error * value + l2 * weights[j])
            step += 1
    return intercept, weights


def average_precision(labels: list[int], scores: list[float]) -> float | None:
    positives = sum(labels)
    if positives == 0:
        return None
    ranked = sorted(zip(scores, labels), key=lambda pair: pair[0], reverse=True)
    true_positives = false_positives = 0
    ap = 0.0
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
        ap += recall_increment * precision
    return ap


def metrics(labels: list[int], scores: list[float]) -> dict[str, Any]:
    return {
        "rows": len(labels),
        "jump_rate": sum(labels) / len(labels),
        "mean_prediction": sum(scores) / len(scores),
        "brier": sum((label - score) ** 2 for label, score in zip(labels, scores)) / len(labels),
        "average_precision": average_precision(labels, scores),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Run EventX toy market-only b0 baseline")
    parser.add_argument("--labels", type=Path)
    parser.add_argument("--out", type=Path)
    parser.add_argument("--freeze-manifest", type=Path)
    parser.add_argument("--stride", type=int, default=5)
    parser.add_argument("--max-rows-per-split", type=int, default=250_000)
    parser.add_argument("--epochs", type=int, default=8)
    args = parser.parse_args()

    labels_path = args.labels or REPO_ROOT / "data" / "v1" / "toy" / "labels_30m.jsonl"
    out_path = args.out or REPO_ROOT / "data" / "v1" / "toy" / "b0_results.json"
    freeze_path = args.freeze_manifest or REPO_ROOT / "data" / "v1" / "toy" / "frozen_manifest.json"
    if not freeze_path.exists():
        raise SystemExit("Freeze the toy dataset before fitting B0.")
    freeze = json.loads(freeze_path.read_text())
    rows, seen = load_rows(labels_path, args.stride, args.max_rows_per_split)
    train = rows["train"]
    if (
        any(not rows[split] for split in ("train", "validation", "test"))
        or len({label for _vector, label in train}) < 2
    ):
        result = {
            "status": "insufficient_class_coverage",
            "sampled": {split: len(values) for split, values in rows.items()},
            "eligible_seen": seen,
            "dataset_id": freeze.get("dataset_id"),
        }
    else:
        means, scales = standardize(train, [rows["validation"], rows["test"]])
        intercept, weights = fit_logistic(train, args.epochs, 0.02, 1.0e-4)
        prevalence = sum(label for _vector, label in train) / len(train)
        evaluation = {}
        for split in ("validation", "test"):
            labels = [label for _vector, label in rows[split]]
            predictions = [
                sigmoid(intercept + sum(w * x for w, x in zip(weights, vector)))
                for vector, _label in rows[split]
            ]
            evaluation[split] = {
                "prevalence_baseline": metrics(labels, [prevalence] * len(labels)),
                "b0_market_only": metrics(labels, predictions),
            }
        result = {
            "status": "ok",
            "model": "standardized_logistic_sgd",
            "dataset_id": freeze.get("dataset_id"),
            "selection_basis": freeze.get("selection_basis"),
            "features": FEATURES,
            "stride_min": args.stride,
            "eligible_seen": seen,
            "sampled": {split: len(values) for split, values in rows.items()},
            "evaluation": evaluation,
            "test_usage": "final_evaluation_only; do not tune features or hyperparameters on test metrics",
            "coefficients": {name: weight for name, weight in zip(FEATURES, weights)},
            "intercept": intercept,
            "standardization": {name: {"mean": mean, "scale": scale} for name, mean, scale in zip(FEATURES, means, scales)},
        }
    out_path.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
    print(json.dumps(result, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
