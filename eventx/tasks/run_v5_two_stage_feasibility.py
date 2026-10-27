"""Explore trade-arrival/repricing factorization on historical discovery data."""

from __future__ import annotations

from datetime import datetime, timezone
import json
import os
from pathlib import Path
from typing import Any

import numpy as np
from sklearn.linear_model import SGDClassifier
from sklearn.metrics import average_precision_score, roc_auc_score

from eventx.features.v4_news import MINUTE_US
from eventx.settings import REPO_ROOT
from eventx.tasks.build_v4_discovery_examples import EXAMPLE_DTYPE
from eventx.tasks.evaluate_v4_confirmatory import two_level_bootstrap
from eventx.tasks.prepare_v3_1_historical_development_arrays import TRADE_DTYPE, sha256_file
from eventx.tasks.run_v4_discovery_models import BATCH_ROWS, FOLDS, LOG_COLUMNS, transformed


EXAMPLES = REPO_ROOT / "data/v4/discovery/examples/examples.bin"
EXAMPLES_MANIFEST = REPO_ROOT / "data/v4/discovery/examples/manifest.json"
TRADES = REPO_ROOT / "data/v3_1_historical/primary/development/prepared/trades.bin"
FUTURE = REPO_ROOT / "data/v4/confirmatory"
OUTPUT = REPO_ROOT / "data/v5/design_diagnostics/two_stage"
PREDICTIONS = OUTPUT / "predictions.bin"
REPORT = OUTPUT / "report.json"
SUMMARY = OUTPUT / "SUMMARY.md"
MANIFEST = OUTPUT / "manifest.json"
START_US = int(datetime(2026, 5, 17, tzinfo=timezone.utc).timestamp() * 1_000_000)
HORIZON_US = 30 * MINUTE_US
SEED = 11
EPOCHS = 3
ALPHA = 0.0001
L1_RATIO = 0.9
WIDTHS = (12, 28)
PREDICTION_DTYPE = np.dtype([
    ("market", "<u4"), ("minute", "<i4"), ("label", "u1"), ("trade_arrival", "u1"),
    ("trade_b0", "<f4"), ("trade_b3", "<f4"),
    ("conditional_b0", "<f4"), ("conditional_b3", "<f4"),
    ("product_b0", "<f4"), ("product_b3", "<f4"),
], align=False)


def relative(path: Path) -> str:
    return str(path.relative_to(REPO_ROOT))


def atomic_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n")
    os.replace(temporary, path)


def verify_manifest(path: Path) -> None:
    manifest = json.loads(path.read_text(encoding="utf-8"))
    for artifact in manifest.get("artifacts", []):
        target = REPO_ROOT / str(artifact["path"])
        if not target.is_file() or sha256_file(target) != str(artifact["sha256"]):
            raise RuntimeError(f"hash-lock failure: {target}")


def trade_arrivals(examples: np.ndarray, trades: np.ndarray) -> np.ndarray:
    output = np.zeros(len(examples), dtype=np.uint8)
    maximum = int(examples["market"].max())
    example_offsets = np.searchsorted(examples["market"], np.arange(maximum + 2, dtype=np.uint32), side="left")
    trade_offsets = np.searchsorted(trades["market"], np.arange(maximum + 2, dtype=np.uint32), side="left")
    for market in range(maximum + 1):
        left, right = int(example_offsets[market]), int(example_offsets[market + 1])
        if left == right:
            continue
        times = np.asarray(trades["timestamp_us"][trade_offsets[market]:trade_offsets[market + 1]], dtype=np.int64)
        grid = START_US + np.asarray(examples["minute"][left:right], dtype=np.int64) * MINUTE_US
        visible = np.searchsorted(times, grid, side="right")
        future = np.searchsorted(times, grid + HORIZON_US, side="right")
        output[left:right] = (future > visible).astype(np.uint8)
    if np.any(np.asarray(examples["label"], dtype=np.uint8) > output):
        raise RuntimeError("historical jump without a future trade")
    return output


def scaler(examples: np.ndarray, indices: np.ndarray, width: int) -> tuple[np.ndarray, np.ndarray]:
    total = np.zeros(width, dtype=np.float64)
    total_sq = np.zeros(width, dtype=np.float64)
    rows = 0
    for start in range(0, len(indices), BATCH_ROWS):
        values = transformed(examples["features"][indices[start:start + BATCH_ROWS]], width)
        total += values.sum(axis=0, dtype=np.float64)
        total_sq += np.square(values).sum(axis=0, dtype=np.float64)
        rows += len(values)
    means = total / rows
    scales = np.sqrt(np.maximum(0.0, total_sq / rows - means * means))
    scales[scales == 0] = 1.0
    return means, scales


def fit_predict(
    examples: np.ndarray,
    targets: np.ndarray,
    train: np.ndarray,
    validation: np.ndarray,
    width: int,
    label: str,
) -> np.ndarray:
    means, scales = scaler(examples, train, width)
    classifier = SGDClassifier(
        loss="log_loss", penalty="elasticnet", alpha=ALPHA, l1_ratio=L1_RATIO,
        fit_intercept=True, max_iter=1, tol=None, shuffle=False,
        learning_rate="constant", eta0=0.02, average=False, random_state=SEED,
    )
    rng = np.random.default_rng(SEED)
    first = True
    for epoch in range(EPOCHS):
        order = rng.permutation(train)
        for start in range(0, len(order), BATCH_ROWS):
            chosen = order[start:start + BATCH_ROWS]
            values = (transformed(examples["features"][chosen], width) - means) / scales
            classifier.partial_fit(
                values, targets[chosen],
                classes=np.asarray([0, 1], dtype=np.uint8) if first else None,
            )
            first = False
        print(f"{label}: epoch {epoch + 1}/{EPOCHS}", flush=True)
    output = np.empty(len(validation), dtype=np.float64)
    for start in range(0, len(validation), BATCH_ROWS):
        chosen = validation[start:start + BATCH_ROWS]
        values = (transformed(examples["features"][chosen], width) - means) / scales
        output[start:start + len(chosen)] = classifier.predict_proba(values)[:, 1]
    return output


def metric(labels: np.ndarray, scores: np.ndarray) -> dict[str, Any]:
    labels = np.asarray(labels, dtype=np.uint8)
    scores = np.clip(np.asarray(scores, dtype=np.float64), 1e-7, 1 - 1e-7)
    positives = int(labels.sum())
    return {
        "rows": len(labels), "positives": positives, "prevalence": float(labels.mean()),
        "log_loss": float(-np.mean(labels * np.log(scores) + (1 - labels) * np.log(1 - scores))),
        "brier": float(np.mean(np.square(labels - scores))),
        "average_precision": float(average_precision_score(labels, scores)) if positives else None,
        "roc_auc": float(roc_auc_score(labels, scores)) if len(np.unique(labels)) == 2 else None,
        "mean_prediction": float(scores.mean()),
    }


def compare(labels: np.ndarray, baseline: np.ndarray, candidate: np.ndarray) -> dict[str, float]:
    left, right = metric(labels, baseline), metric(labels, candidate)
    return {
        "log_loss_improvement": float(left["log_loss"] - right["log_loss"]),
        "brier_improvement": float(left["brier"] - right["brier"]),
        "delta_average_precision": float(right["average_precision"] - left["average_precision"]),
    }


def main() -> None:
    if any(path.exists() for path in (PREDICTIONS, REPORT, SUMMARY, MANIFEST)):
        raise SystemExit("v5 two-stage feasibility artifacts already exist")
    if any(path.exists() for path in (FUTURE / "consumption_receipt.json", FUTURE / "examples/examples.bin", FUTURE / "evaluation/result.json")):
        raise SystemExit("two-stage diagnosis refused after v4 future consumption")
    verify_manifest(EXAMPLES_MANIFEST)
    count = EXAMPLES.stat().st_size // EXAMPLE_DTYPE.itemsize
    trade_count = TRADES.stat().st_size // TRADE_DTYPE.itemsize
    examples = np.memmap(EXAMPLES, mode="r", dtype=EXAMPLE_DTYPE, shape=(count,))
    trades = np.memmap(TRADES, mode="r", dtype=TRADE_DTYPE, shape=(trade_count,))
    arrivals = trade_arrivals(examples, trades)
    OUTPUT.mkdir(parents=True, exist_ok=True)
    temporary = PREDICTIONS.with_suffix(PREDICTIONS.suffix + ".tmp")
    fold_reports = []
    with temporary.open("wb") as handle:
        for fold, held_group, validation_start, validation_end in FOLDS:
            train = np.flatnonzero((examples["minute"] < validation_start - 30) & (examples["group"] != held_group))
            validation = np.flatnonzero((examples["minute"] >= validation_start) & (examples["minute"] < validation_end) & (examples["group"] == held_group))
            conditional_train = train[arrivals[train] == 1]
            predictions = {}
            for name, width in (("b0", 12), ("b3", 28)):
                predictions[f"trade_{name}"] = fit_predict(examples, arrivals, train, validation, width, f"fold{fold}-trade-{name}")
                predictions[f"conditional_{name}"] = fit_predict(examples, np.asarray(examples["label"], dtype=np.uint8), conditional_train, validation, width, f"fold{fold}-conditional-{name}")
                predictions[f"product_{name}"] = predictions[f"trade_{name}"] * predictions[f"conditional_{name}"]
            rows = np.empty(len(validation), dtype=PREDICTION_DTYPE)
            rows["market"], rows["minute"] = examples["market"][validation], examples["minute"][validation]
            rows["label"], rows["trade_arrival"] = examples["label"][validation], arrivals[validation]
            for name in predictions:
                rows[name] = predictions[name]
            rows.tofile(handle)
            fold_reports.append({
                "fold": fold, "train_rows": len(train), "conditional_train_rows": len(conditional_train), "validation_rows": len(validation),
                "trade_b0": metric(rows["trade_arrival"], rows["trade_b0"]),
                "trade_b3": metric(rows["trade_arrival"], rows["trade_b3"]),
                "conditional_b0": metric(rows["label"][rows["trade_arrival"] == 1], rows["conditional_b0"][rows["trade_arrival"] == 1]),
                "conditional_b3": metric(rows["label"][rows["trade_arrival"] == 1], rows["conditional_b3"][rows["trade_arrival"] == 1]),
                "product_b0": metric(rows["label"], rows["product_b0"]),
                "product_b3": metric(rows["label"], rows["product_b3"]),
            })
    os.replace(temporary, PREDICTIONS)
    total = PREDICTIONS.stat().st_size // PREDICTION_DTYPE.itemsize
    predictions = np.memmap(PREDICTIONS, mode="r", dtype=PREDICTION_DTYPE, shape=(total,))
    trade_comparison = compare(predictions["trade_arrival"], predictions["trade_b0"], predictions["trade_b3"])
    traded = predictions["trade_arrival"] == 1
    conditional_comparison = compare(predictions["label"][traded], predictions["conditional_b0"][traded], predictions["conditional_b3"][traded])
    product_comparison = compare(predictions["label"], predictions["product_b0"], predictions["product_b3"])
    bootstrap_values = {}
    for name, target, baseline, candidate, mask in (
        ("trade_arrival_b3_vs_b0", predictions["trade_arrival"], predictions["trade_b0"], predictions["trade_b3"], np.ones(total, dtype=bool)),
        ("conditional_repricing_b3_vs_b0", predictions["label"], predictions["conditional_b0"], predictions["conditional_b3"], traded),
        ("product_jump_b3_vs_b0", predictions["label"], predictions["product_b0"], predictions["product_b3"], np.ones(total, dtype=bool)),
    ):
        labels = np.asarray(target[mask], dtype=np.float64)
        left = np.clip(np.asarray(baseline[mask], dtype=np.float64), 1e-7, 1 - 1e-7)
        right = np.clip(np.asarray(candidate[mask], dtype=np.float64), 1e-7, 1 - 1e-7)
        differences = (-labels * np.log(left) - (1 - labels) * np.log(1 - left)) - (-labels * np.log(right) - (1 - labels) * np.log(1 - right))
        result = two_level_bootstrap(predictions["market"][mask], predictions["minute"][mask], differences, samples=2000, seed=731)
        result["estimand"] = name
        bootstrap_values[name] = result
    report = {
        "diagnostic_id": "eventx-v5-two-stage-feasibility-20260903",
        "created_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "status": "complete",
        "role": "historical exploratory structural feasibility; not v5 model selection",
        "future_v4_data_read": False,
        "frozen_v4_changed": False,
        "learner": {"type": "elastic-net logistic SGD", "epochs": EPOCHS, "alpha": ALPHA, "l1_ratio": L1_RATIO, "seed": SEED},
        "folds": fold_reports,
        "aggregate": {
            "trade_arrival_b0": metric(predictions["trade_arrival"], predictions["trade_b0"]),
            "trade_arrival_b3": metric(predictions["trade_arrival"], predictions["trade_b3"]),
            "trade_arrival_comparison": trade_comparison,
            "conditional_repricing_b0": metric(predictions["label"][traded], predictions["conditional_b0"][traded]),
            "conditional_repricing_b3": metric(predictions["label"][traded], predictions["conditional_b3"][traded]),
            "conditional_repricing_comparison": conditional_comparison,
            "product_jump_b0": metric(predictions["label"], predictions["product_b0"]),
            "product_jump_b3": metric(predictions["label"], predictions["product_b3"]),
            "product_jump_comparison": product_comparison,
        },
        "paired_bootstraps": bootstrap_values,
        "limitations": [
            "uses v4 features and B0-v4 rather than the proposed time-to-terminal B0-v5",
            "hyperparameters were informed by a historical solver diagnostic",
            "one seed and therefore suitable only for architecture feasibility",
        ],
    }
    atomic_json(REPORT, report)
    SUMMARY.write_text(
        "# EventX v5 two-stage feasibility\n\n"
        "Historical exploratory result; the future v4 holdout was not read.\n\n"
        f"- News-feature improvement for predicting trade arrival: `{trade_comparison['log_loss_improvement']:.6f}`.\n"
        f"- News-feature improvement for jump risk conditional on a trade: `{conditional_comparison['log_loss_improvement']:.6f}`.\n"
        f"- News-feature improvement for the factorized product probability: `{product_comparison['log_loss_improvement']:.6f}`.\n\n"
        "This run tests whether the two-stage architecture is worth carrying into a "
        "fresh, nested v5 development procedure; it does not select or confirm v5.\n",
        encoding="utf-8",
    )
    atomic_json(MANIFEST, {
        "diagnostic_id": report["diagnostic_id"], "status": report["status"],
        "artifacts": [{"path": relative(path), "sha256": sha256_file(path)} for path in (PREDICTIONS, REPORT, SUMMARY, Path(__file__).resolve())],
        "inputs": [{"path": relative(path), "sha256": sha256_file(path)} for path in (EXAMPLES, EXAMPLES_MANIFEST, TRADES)],
    })
    print(json.dumps({"status": report["status"], "future_v4_data_read": False, "aggregate": report["aggregate"], "paired_bootstraps": bootstrap_values}, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
