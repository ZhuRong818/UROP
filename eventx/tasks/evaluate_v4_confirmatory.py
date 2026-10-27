"""Perform the single permitted EventX v4 confirmatory evaluation."""

from __future__ import annotations

from datetime import datetime, timezone
import json
import os
from pathlib import Path
from typing import Any, Iterator

import numpy as np
from sklearn.metrics import average_precision_score, roc_auc_score

from eventx.settings import REPO_ROOT
from eventx.tasks.build_v4_confirmatory_examples import EXAMPLE_DTYPE
from eventx.tasks.prepare_v3_1_historical_development_arrays import sha256_file
from eventx.tasks.run_v4_discovery_models import LOG_COLUMNS, MODEL_WIDTHS


PROTOCOL_ID = "eventx-v4-confirmatory-polymarket-20260902"
EXAMPLES = REPO_ROOT / "data/v4/confirmatory/examples/examples.bin"
EXAMPLES_MANIFEST = REPO_ROOT / "data/v4/confirmatory/examples/manifest.json"
MARKETS = REPO_ROOT / "data/v4/confirmatory/prepared/market_index.jsonl"
MODELS = REPO_ROOT / "data/v4/discovery/models/frozen_models.json"
MODEL_FREEZE = REPO_ROOT / "eventx/release/v4/model_freeze_manifest.json"
CONSUMPTION_RECEIPT = REPO_ROOT / "data/v4/confirmatory/consumption_receipt.json"
OUTPUT = REPO_ROOT / "data/v4/confirmatory/evaluation"
ATTEMPT = OUTPUT / "evaluation_attempt_receipt.json"
PREDICTIONS = OUTPUT / "predictions.bin"
RESULT = OUTPUT / "result.json"
MANIFEST = OUTPUT / "manifest.json"
BOOTSTRAP_SAMPLES = 5000
BOOTSTRAP_SEED = 61
BLOCK_ROWS = 72
PREDICTION_DTYPE = np.dtype([
    ("market", "<u4"),
    ("minute", "<i4"),
    ("label", "u1"),
    ("trade_arrival", "u1"),
    ("price_age", "<f4"),
    ("b0", "<f4"),
    ("b1", "<f4"),
    ("b2", "<f4"),
    ("b3", "<f4"),
], align=False)


def relative(path: Path) -> str:
    return str(path.relative_to(REPO_ROOT))


def read_jsonl(path: Path) -> Iterator[dict[str, Any]]:
    with path.open(encoding="utf-8") as handle:
        for line in handle:
            if line.strip():
                yield json.loads(line)


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


def transformed(features: np.ndarray, width: int) -> np.ndarray:
    values = np.asarray(features[:, :width], dtype=np.float64).copy()
    for column in LOG_COLUMNS:
        if column < width:
            values[:, column] = np.log1p(values[:, column])
    return values


def frozen_predict(
    features: np.ndarray,
    bundle: dict[str, Any],
    name: str,
    batch_rows: int = 65_536,
) -> np.ndarray:
    model = bundle["models"][name]
    width = MODEL_WIDTHS[name]
    means = np.asarray(model["means"], dtype=np.float64)
    scales = np.asarray(model["scales"], dtype=np.float64)
    predictions = np.zeros(len(features), dtype=np.float64)
    for start in range(0, len(features), batch_rows):
        stop = min(len(features), start + batch_rows)
        values = (transformed(features[start:stop], width) - means) / scales
        for seed_model in model["models"]:
            coefficients = np.asarray(seed_model["coefficients"], dtype=np.float64)
            linear = values @ coefficients + float(seed_model["intercept"])
            predictions[start:stop] += 1.0 / (
                1.0 + np.exp(-np.clip(linear, -40.0, 40.0))
            )
    return predictions / len(model["models"])


def metric_set(labels: np.ndarray, scores: np.ndarray) -> dict[str, Any]:
    labels = np.asarray(labels, dtype=np.uint8)
    scores = np.clip(np.asarray(scores, dtype=np.float64), 1e-7, 1.0 - 1e-7)
    positives = int(labels.sum())
    bins = np.minimum((scores * 10).astype(np.int64), 9)
    ece = 0.0
    calibration = []
    for number in range(10):
        selected = bins == number
        if not np.any(selected):
            continue
        observed = float(labels[selected].mean())
        predicted = float(scores[selected].mean())
        count = int(selected.sum())
        ece += count / len(labels) * abs(observed - predicted)
        calibration.append({"bin": number, "rows": count, "mean_prediction": predicted, "observed_rate": observed})
    return {
        "rows": len(labels),
        "positives": positives,
        "prevalence": float(labels.mean()),
        "mean_prediction": float(scores.mean()),
        "log_loss": float(-np.mean(labels * np.log(scores) + (1 - labels) * np.log(1 - scores))),
        "brier": float(np.mean(np.square(labels - scores))),
        "average_precision": float(average_precision_score(labels, scores)) if positives else None,
        "roc_auc": float(roc_auc_score(labels, scores)) if len(np.unique(labels)) == 2 else None,
        "expected_calibration_error_10_bins": float(ece),
        "calibration": calibration,
    }


def compare(labels: np.ndarray, baseline: np.ndarray, candidate: np.ndarray) -> dict[str, Any]:
    left, right = metric_set(labels, baseline), metric_set(labels, candidate)
    return {
        "log_loss_improvement": float(left["log_loss"] - right["log_loss"]),
        "brier_improvement": float(left["brier"] - right["brier"]),
        "delta_average_precision": float(right["average_precision"] - left["average_precision"]) if left["average_precision"] is not None and right["average_precision"] is not None else None,
    }


def circular_block_totals(
    values: np.ndarray,
    samples: int,
    rng: np.random.Generator,
) -> np.ndarray:
    size = len(values)
    block = min(BLOCK_ROWS, size)
    full, remainder = divmod(size, block)
    extended = np.concatenate((values, values[: block - 1])) if block > 1 else values
    prefix = np.concatenate(([0.0], np.cumsum(extended, dtype=np.float64)))
    block_sums = prefix[np.arange(size) + block] - prefix[np.arange(size)]
    output = np.zeros(samples, dtype=np.float64)
    if full:
        starts = rng.integers(0, size, size=(samples, full))
        output += block_sums[starts].sum(axis=1)
    if remainder:
        rem_sums = prefix[np.arange(size) + remainder] - prefix[np.arange(size)]
        output += rem_sums[rng.integers(0, size, size=samples)]
    return output


def circular_block_pair(
    values: np.ndarray,
    weights: np.ndarray,
    samples: int,
    rng: np.random.Generator,
) -> tuple[np.ndarray, np.ndarray]:
    """Apply the same circular block draw to a numerator and denominator."""

    size = len(values)
    if not size or len(weights) != size:
        raise ValueError("paired circular inputs must be nonempty and aligned")
    block = min(BLOCK_ROWS, size)
    full, remainder = divmod(size, block)
    if block > 1:
        extended_values = np.concatenate((values, values[: block - 1]))
        extended_weights = np.concatenate((weights, weights[: block - 1]))
    else:
        extended_values, extended_weights = values, weights
    value_prefix = np.concatenate(([0.0], np.cumsum(extended_values, dtype=np.float64)))
    weight_prefix = np.concatenate(([0.0], np.cumsum(extended_weights, dtype=np.float64)))
    output_values = np.zeros(samples, dtype=np.float64)
    output_weights = np.zeros(samples, dtype=np.float64)
    if full:
        starts = rng.integers(0, size, size=(samples, full))
        block_values = value_prefix[np.arange(size) + block] - value_prefix[np.arange(size)]
        block_weights = weight_prefix[np.arange(size) + block] - weight_prefix[np.arange(size)]
        output_values += block_values[starts].sum(axis=1)
        output_weights += block_weights[starts].sum(axis=1)
    if remainder:
        starts = rng.integers(0, size, size=samples)
        partial_values = value_prefix[np.arange(size) + remainder] - value_prefix[np.arange(size)]
        partial_weights = weight_prefix[np.arange(size) + remainder] - weight_prefix[np.arange(size)]
        output_values += partial_values[starts]
        output_weights += partial_weights[starts]
    return output_values, output_weights


def market_time_block_totals(
    minutes: np.ndarray,
    values: np.ndarray,
    samples: int,
    rng: np.random.Generator,
) -> tuple[np.ndarray, np.ndarray]:
    """Resample complete 360-minute calendar blocks, retaining eligibility gaps."""

    minutes = np.asarray(minutes, dtype=np.int64)
    if len(minutes) != len(values) or not len(minutes):
        raise ValueError("market block inputs must be nonempty and aligned")
    slots = (minutes - minutes.min()) // 5
    if np.any(minutes != minutes.min() + slots * 5) or len(np.unique(slots)) != len(slots):
        raise ValueError("confirmatory grid is not unique five-minute UTC slots")
    span = int(slots.max()) + 1
    dense_values = np.zeros(span, dtype=np.float64)
    dense_weights = np.zeros(span, dtype=np.float64)
    dense_values[slots] = values
    dense_weights[slots] = 1.0
    return circular_block_pair(dense_values, dense_weights, samples, rng)


def two_level_bootstrap(
    markets: np.ndarray,
    minutes: np.ndarray,
    values: np.ndarray,
    samples: int = BOOTSTRAP_SAMPLES,
    seed: int = BOOTSTRAP_SEED,
) -> dict[str, Any]:
    if not len(markets) or len(markets) != len(values) or len(minutes) != len(values):
        raise ValueError("bootstrap requires nonempty aligned inputs")
    order = np.argsort(markets, kind="stable")
    ordered_markets = np.asarray(markets[order])
    ordered_minutes = np.asarray(minutes[order], dtype=np.int64)
    ordered_values = np.asarray(values[order], dtype=np.float64)
    boundaries = np.concatenate(([0], np.flatnonzero(np.diff(ordered_markets)) + 1, [len(order)]))
    unique = ordered_markets[boundaries[:-1]]
    rng = np.random.default_rng(seed)
    totals = np.empty((len(unique), samples), dtype=np.float64)
    weights = np.empty((len(unique), samples), dtype=np.float64)
    for index, (left, right) in enumerate(zip(boundaries[:-1], boundaries[1:])):
        totals[index], weights[index] = market_time_block_totals(
            ordered_minutes[left:right], ordered_values[left:right], samples, rng
        )
    draws = rng.integers(0, len(unique), size=(samples, len(unique)))
    sample_index = np.arange(samples)[:, None]
    denominators = weights[draws, sample_index].sum(axis=1)
    if np.any(denominators == 0):
        raise RuntimeError("bootstrap produced an empty eligible sample")
    estimates = totals[draws, sample_index].sum(axis=1) / denominators
    return {
        "estimand": "mean per-row log-loss improvement B0 minus B3",
        "method": "paired event-cluster bootstrap with circular 360-minute within-market blocks",
        "event_clusters": len(unique),
        "calendar_block_minutes": BLOCK_ROWS * 5,
        "samples": samples,
        "seed": seed,
        "mean": float(estimates.mean()),
        "ci_95_lower": float(np.quantile(estimates, 0.025)),
        "ci_95_upper": float(np.quantile(estimates, 0.975)),
        "probability_positive": float(np.mean(estimates > 0.0)),
    }


def evaluate_subset(predictions: np.ndarray, mask: np.ndarray) -> dict[str, Any]:
    rows = predictions[mask]
    if not len(rows):
        raise RuntimeError("confirmatory evaluation subset is empty")
    labels = np.asarray(rows["label"], dtype=np.uint8)
    model_metrics = {name: metric_set(labels, np.asarray(rows[name], dtype=np.float64)) for name in MODEL_WIDTHS}
    increments = {name: compare(labels, np.asarray(rows["b0"], dtype=np.float64), np.asarray(rows[name], dtype=np.float64)) for name in ("b1", "b2", "b3")}
    b0 = np.clip(np.asarray(rows["b0"], dtype=np.float64), 1e-7, 1 - 1e-7)
    b3 = np.clip(np.asarray(rows["b3"], dtype=np.float64), 1e-7, 1 - 1e-7)
    labels_float = labels.astype(np.float64)
    improvement = (-labels_float * np.log(b0) - (1 - labels_float) * np.log(1 - b0)) - (-labels_float * np.log(b3) - (1 - labels_float) * np.log(1 - b3))
    return {
        "models": model_metrics,
        "incremental_over_b0": increments,
        "b3_vs_b0_bootstrap": two_level_bootstrap(
            np.asarray(rows["market"]),
            np.asarray(rows["minute"]),
            improvement,
        ),
    }


def main() -> None:
    if any(path.exists() for path in (ATTEMPT, PREDICTIONS, RESULT, MANIFEST)):
        raise SystemExit("v4 confirmatory evaluation already attempted; rerun prohibited")
    verify_manifest(EXAMPLES_MANIFEST)
    consumption = json.loads(CONSUMPTION_RECEIPT.read_text(encoding="utf-8"))
    if consumption.get("status") != "future_holdout_irreversibly_consumed_before_label_summary":
        raise SystemExit("invalid consumption receipt")
    for artifact in consumption.get("inputs", []):
        target = REPO_ROOT / str(artifact["path"])
        if not target.is_file() or sha256_file(target) != str(artifact["sha256"]):
            raise RuntimeError(f"consumption-receipt hash failure: {target}")
    model_freeze = json.loads(MODEL_FREEZE.read_text(encoding="utf-8"))
    bundle = json.loads(MODELS.read_text(encoding="utf-8"))
    if bundle.get("model_bundle_sha256") != model_freeze.get("model_bundle_internal_sha256"):
        raise RuntimeError("frozen model bundle mismatch")
    OUTPUT.mkdir(parents=True, exist_ok=True)
    atomic_json(ATTEMPT, {
        "protocol_id": PROTOCOL_ID,
        "started_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "attempt": 1,
        "status": "one_shot_evaluation_started_before_reading_label_values",
        "examples_sha256": sha256_file(EXAMPLES),
        "labels_prevalence_predictions_or_metrics_read_before_receipt": False,
    })
    count = EXAMPLES.stat().st_size // EXAMPLE_DTYPE.itemsize
    examples = np.memmap(EXAMPLES, mode="r", dtype=EXAMPLE_DTYPE, shape=(count,))
    rows = np.empty(count, dtype=PREDICTION_DTYPE)
    for field in ("market", "minute", "label", "trade_arrival", "price_age"):
        rows[field] = examples[field]
    for name in MODEL_WIDTHS:
        rows[name] = frozen_predict(examples["features"], bundle, name)
    temporary = PREDICTIONS.with_suffix(PREDICTIONS.suffix + ".tmp")
    rows.tofile(temporary)
    os.replace(temporary, PREDICTIONS)
    primary_mask = rows["price_age"] <= 30.0
    robustness_mask = rows["price_age"] <= 60.0
    primary = evaluate_subset(rows, primary_mask)
    robustness = evaluate_subset(rows, robustness_mask)
    markets = list(read_jsonl(MARKETS))
    categories = {}
    for category in sorted({str(row["category"]) for row in markets}):
        members = np.asarray([int(row["market_index"]) for row in markets if str(row["category"]) == category], dtype=np.uint32)
        selected = primary_mask & np.isin(rows["market"], members)
        if np.sum(selected) and len(np.unique(rows["label"][selected])) == 2:
            categories[category] = {
                "event_clusters": int(len(np.unique(rows["market"][selected]))),
                "b3_vs_b0": compare(rows["label"][selected], rows["b0"][selected], rows["b3"][selected]),
            }
    trade_arrival = {}
    for value, label in ((0, "no_future_execution"), (1, "future_execution")):
        selected = primary_mask & (rows["trade_arrival"] == value)
        if np.sum(selected) and len(np.unique(rows["label"][selected])) == 2:
            trade_arrival[label] = {
                "rows": int(np.sum(selected)),
                "b3_vs_b0": compare(rows["label"][selected], rows["b0"][selected], rows["b3"][selected]),
            }
    contrast = primary["incremental_over_b0"]["b3"]
    bootstrap = primary["b3_vs_b0_bootstrap"]
    venue_clusters = len(np.unique(rows["market"][primary_mask]))
    venue_classes = len(np.unique(rows["label"][primary_mask])) == 2
    venue_estimate = float(contrast["log_loss_improvement"])
    conditions = {
        "log_loss_improvement_at_least_0_001": venue_estimate >= 0.001,
        "bootstrap_95_lower_above_zero": float(bootstrap["ci_95_lower"]) > 0.0,
        "brier_improvement_at_least_minus_0_0005": float(contrast["brier_improvement"]) >= -0.0005,
        "all_eligible_venue_estimates_nonnegative": not (venue_clusters >= 30 and venue_classes) or venue_estimate >= 0.0,
    }
    result = {
        "protocol_id": PROTOCOL_ID,
        "completed_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "status": "confirmatory_evaluation_complete",
        "evaluation_attempt": 1,
        "primary_price_age_le_30": primary,
        "robustness_price_age_le_60": robustness,
        "secondary_category_results": categories,
        "trade_arrival_diagnostic": trade_arrival,
        "confirmatory_conditions": conditions,
        "positive_claim_supported": all(conditions.values()),
        "claim_boundary": "frozen Polymarket cohort, interval, Lumid source, target, and model family only",
    }
    atomic_json(RESULT, result)
    atomic_json(MANIFEST, {
        "protocol_id": PROTOCOL_ID,
        "status": result["status"],
        "artifacts": [{"path": relative(path), "sha256": sha256_file(path)} for path in (ATTEMPT, PREDICTIONS, RESULT, Path(__file__).resolve())],
        "inputs": [{"path": relative(path), "sha256": sha256_file(path)} for path in (EXAMPLES, EXAMPLES_MANIFEST, MODELS, MODEL_FREEZE, CONSUMPTION_RECEIPT)],
    })
    print(json.dumps(result, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
