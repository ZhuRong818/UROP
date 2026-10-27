"""Run frozen v3.1 development B0/B1 folds and freeze one candidate."""

from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import json
import math
import os
from pathlib import Path
from typing import Any

import numpy as np
from sklearn.linear_model import LogisticRegression, SGDClassifier
from sklearn.metrics import average_precision_score, roc_auc_score

from eventx.settings import REPO_ROOT
from eventx.tasks.build_v3_1_historical_development_examples import (
    EXAMPLE_DTYPE,
    FEATURE_NAMES,
    sha256_file,
)


PROTOCOL = REPO_ROOT / "eventx/release/v3_1_historical_primary/protocol.json"
IMPLEMENTATION_MANIFEST = (
    REPO_ROOT / "eventx/release/v3_1_historical_primary/implementation_manifest.json"
)
EXAMPLES_ROOT = REPO_ROOT / "data/v3_1_historical/primary/development"
EXAMPLES = EXAMPLES_ROOT / "examples.bin"
EXAMPLES_MANIFEST = EXAMPLES_ROOT / "examples_manifest.json"
SELECTION_RESULT = EXAMPLES_ROOT / "selection_result.json"
OOF = EXAMPLES_ROOT / "oof_predictions.bin"
CANDIDATE = REPO_ROOT / "eventx/release/v3_1_historical_primary/candidate.json"
CANDIDATE_MANIFEST = (
    REPO_ROOT / "eventx/release/v3_1_historical_primary/candidate_manifest.json"
)
HOLDOUT = REPO_ROOT / "data/v3_1_historical/primary/holdout"
SEEDS = (11, 23, 47)
EPOCHS = 8
LEARNING_RATE = 0.02
L2 = 0.0001
BATCH_ROWS = 65_536
LOG_COLUMNS = (6, 7, 8, 9, 12, 13, 14)
FOLDS = (
    (1, 0, 11 * 1440, 22 * 1440),
    (2, 1, 22 * 1440, 33 * 1440),
    (3, 2, 33 * 1440, 44 * 1440),
    (4, 3, 44 * 1440, 55 * 1440),
    (5, 4, 55 * 1440, 66 * 1440),
)
OOF_DTYPE = np.dtype(
    [
        ("market", "<u4"),
        ("minute", "<i4"),
        ("venue", "u1"),
        ("fold", "u1"),
        ("label", "u1"),
        ("b0", "<f4"),
        ("b1", "<f4"),
        ("price_age", "<f4"),
        ("news_1440", "<f4"),
    ],
    align=False,
)


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
        artifact_path = REPO_ROOT / str(artifact["path"])
        if not artifact_path.is_file() or sha256_file(artifact_path) != str(
            artifact["sha256"]
        ):
            raise RuntimeError(f"hash-lock failure: {artifact_path}")


def transformed(values: np.ndarray, width: int) -> np.ndarray:
    output = np.asarray(values[:, :width], dtype=np.float64).copy()
    for column in LOG_COLUMNS:
        if column < width:
            output[:, column] = np.log1p(output[:, column])
    return output


def scaler(examples: np.ndarray, indices: np.ndarray, width: int) -> tuple[np.ndarray, np.ndarray]:
    total = np.zeros(width, dtype=np.float64)
    total_sq = np.zeros(width, dtype=np.float64)
    rows = 0
    for start in range(0, len(indices), BATCH_ROWS):
        batch = transformed(examples["features"][indices[start : start + BATCH_ROWS]], width)
        total += batch.sum(axis=0, dtype=np.float64)
        total_sq += np.square(batch).sum(axis=0, dtype=np.float64)
        rows += len(batch)
    means = total / rows
    variance = np.maximum(0.0, total_sq / rows - means * means)
    scales = np.sqrt(variance)
    scales[scales == 0.0] = 1.0
    return means, scales


def fit_seed(
    examples: np.ndarray,
    train_indices: np.ndarray,
    width: int,
    means: np.ndarray,
    scales: np.ndarray,
    seed: int,
    label: str,
) -> SGDClassifier:
    classifier = SGDClassifier(
        loss="log_loss",
        penalty="l2",
        alpha=L2,
        fit_intercept=True,
        max_iter=1,
        tol=None,
        shuffle=False,
        learning_rate="constant",
        eta0=LEARNING_RATE,
        average=False,
        random_state=seed,
    )
    rng = np.random.default_rng(seed)
    first = True
    for epoch in range(EPOCHS):
        order = rng.permutation(train_indices)
        for start in range(0, len(order), BATCH_ROWS):
            indices = order[start : start + BATCH_ROWS]
            values = (transformed(examples["features"][indices], width) - means) / scales
            labels = np.asarray(examples["label"][indices], dtype=np.uint8)
            if first:
                classifier.partial_fit(values, labels, classes=np.array([0, 1]))
                first = False
            else:
                classifier.partial_fit(values, labels)
        print(f"{label}: seed={seed} epoch={epoch + 1}/{EPOCHS}", flush=True)
    return classifier


def predict(
    classifier: SGDClassifier,
    examples: np.ndarray,
    indices: np.ndarray,
    width: int,
    means: np.ndarray,
    scales: np.ndarray,
) -> np.ndarray:
    output = np.empty(len(indices), dtype=np.float64)
    for start in range(0, len(indices), BATCH_ROWS):
        selected = indices[start : start + BATCH_ROWS]
        values = (transformed(examples["features"][selected], width) - means) / scales
        output[start : start + len(selected)] = classifier.predict_proba(values)[:, 1]
    return output


def ensemble(
    examples: np.ndarray,
    train_indices: np.ndarray,
    evaluation_indices: np.ndarray,
    width: int,
    label: str,
) -> tuple[np.ndarray, dict[str, Any]]:
    means, scales = scaler(examples, train_indices, width)
    predictions = np.zeros(len(evaluation_indices), dtype=np.float64)
    models = []
    for seed in SEEDS:
        classifier = fit_seed(
            examples, train_indices, width, means, scales, seed, label
        )
        predictions += predict(
            classifier, examples, evaluation_indices, width, means, scales
        )
        models.append(
            {
                "seed": seed,
                "intercept": float(classifier.intercept_[0]),
                "coefficients": [float(value) for value in classifier.coef_[0]],
            }
        )
    predictions /= len(SEEDS)
    return predictions, {
        "feature_names": list(FEATURE_NAMES[:width]),
        "means": [float(value) for value in means],
        "scales": [float(value) for value in scales],
        "models": models,
    }


def ece(labels: np.ndarray, scores: np.ndarray, bins: int = 10) -> float:
    order = np.argsort(scores, kind="stable")
    value = 0.0
    for indices in np.array_split(order, bins):
        if len(indices):
            value += len(indices) / len(labels) * abs(
                float(labels[indices].mean()) - float(scores[indices].mean())
            )
    return value


def calibration(labels: np.ndarray, scores: np.ndarray) -> dict[str, float | None]:
    clipped = np.clip(scores, 1.0e-8, 1.0 - 1.0e-8)
    logits = np.log(clipped / (1.0 - clipped)).reshape(-1, 1)
    if len(np.unique(labels)) < 2:
        return {"intercept": None, "slope": None}
    model = LogisticRegression(penalty=None, solver="lbfgs", max_iter=200)
    model.fit(logits, labels)
    return {
        "intercept": float(model.intercept_[0]),
        "slope": float(model.coef_[0, 0]),
    }


def metrics(labels: np.ndarray, scores: np.ndarray) -> dict[str, Any]:
    positives = int(labels.sum())
    return {
        "rows": len(labels),
        "positives": positives,
        "jump_rate": float(labels.mean()),
        "mean_prediction": float(scores.mean()),
        "average_precision": (
            float(average_precision_score(labels, scores)) if positives else None
        ),
        "brier": float(np.mean(np.square(labels - scores))),
        "roc_auc": (
            float(roc_auc_score(labels, scores)) if len(np.unique(labels)) == 2 else None
        ),
        "ece_10_equal_frequency": ece(labels, scores),
        "calibration": calibration(labels, scores),
    }


def paired_metrics(labels: np.ndarray, b0: np.ndarray, b1: np.ndarray) -> dict[str, Any]:
    left = metrics(labels, b0)
    right = metrics(labels, b1)
    delta_ap = (
        float(right["average_precision"]) - float(left["average_precision"])
        if left["average_precision"] is not None and right["average_precision"] is not None
        else None
    )
    return {
        "b0": left,
        "b1": right,
        "incremental_b1_over_b0": {
            "delta_average_precision": delta_ap,
            "brier_improvement": float(left["brier"]) - float(right["brier"]),
        },
    }


def circular_sums(values: np.ndarray, length: int) -> np.ndarray:
    if length <= 0 or length > len(values):
        raise ValueError("invalid circular block length")
    extended = np.concatenate((values, values[: length - 1])) if length > 1 else values
    cumulative = np.concatenate(([0.0], np.cumsum(extended, dtype=np.float64)))
    starts = np.arange(len(values), dtype=np.int64)
    return cumulative[starts + length] - cumulative[starts]


def brier_block_bootstrap(oof: np.ndarray) -> dict[str, Any]:
    improvement = np.square(oof["label"] - oof["b0"]) - np.square(
        oof["label"] - oof["b1"]
    )
    market_values = np.asarray(oof["market"], dtype=np.uint32)
    boundaries = np.flatnonzero(np.diff(market_values)) + 1
    boundaries = np.concatenate(([0], boundaries, [len(oof)]))
    samples = 5000
    rng = np.random.default_rng(61)
    totals = np.zeros(samples, dtype=np.float64)
    for group_index, (left, right) in enumerate(zip(boundaries[:-1], boundaries[1:])):
        values = np.asarray(improvement[left:right], dtype=np.float64)
        size = len(values)
        block = min(72, size)
        full = size // block
        remainder = size % block
        block_sums = circular_sums(values, block)
        starts = rng.integers(0, size, size=(samples, full))
        totals += block_sums[starts].sum(axis=1)
        if remainder:
            remainder_sums = circular_sums(values, remainder)
            totals += remainder_sums[rng.integers(0, size, size=samples)]
        if (group_index + 1) % 500 == 0:
            print(
                f"bootstrap prepared {group_index + 1}/{len(boundaries) - 1} markets",
                flush=True,
            )
    values = totals / len(oof)
    return {
        "method": "paired circular moving-block bootstrap stratified by market",
        "block_rows": 72,
        "nominal_block_minutes": 360,
        "samples": samples,
        "seed": 61,
        "mean": float(values.mean()),
        "median": float(np.median(values)),
        "ci_95_lower": float(np.quantile(values, 0.025)),
        "ci_95_upper": float(np.quantile(values, 0.975)),
        "probability_positive": float(np.mean(values > 0.0)),
    }


def model_hash(payload: dict[str, Any]) -> str:
    serialized = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
    return hashlib.sha256(serialized).hexdigest()


def main() -> None:
    if any(path.exists() for path in (SELECTION_RESULT, OOF, CANDIDATE, CANDIDATE_MANIFEST)):
        raise SystemExit("development selection artifact exists; rerun prohibited")
    if HOLDOUT.exists():
        raise SystemExit("historical holdout exists before candidate freeze")
    verify_manifest(IMPLEMENTATION_MANIFEST)
    verify_manifest(EXAMPLES_MANIFEST)
    count = EXAMPLES.stat().st_size // EXAMPLE_DTYPE.itemsize
    examples = np.memmap(EXAMPLES, mode="r", dtype=EXAMPLE_DTYPE, shape=(count,))
    oof_temporary = OOF.with_suffix(OOF.suffix + ".tmp")
    folds = []
    with oof_temporary.open("wb") as handle:
        for fold_number, held_group, validation_start, validation_end in FOLDS:
            train_indices = np.flatnonzero(
                (examples["minute"] < validation_start - 30)
                & (examples["group"] != held_group)
            )
            validation_indices = np.flatnonzero(
                (examples["minute"] >= validation_start)
                & (examples["minute"] < validation_end)
                & (examples["group"] == held_group)
            )
            train_labels = np.asarray(examples["label"][train_indices], dtype=np.uint8)
            validation_labels = np.asarray(
                examples["label"][validation_indices], dtype=np.uint8
            )
            if not len(train_indices) or not len(validation_indices):
                raise RuntimeError(f"fold {fold_number} has no train or validation rows")
            if len(np.unique(train_labels)) < 2 or len(np.unique(validation_labels)) < 2:
                raise RuntimeError(f"fold {fold_number} lacks binary class coverage")
            print(
                f"fold {fold_number}: train={len(train_indices)} validation={len(validation_indices)}",
                flush=True,
            )
            b0_scores, b0_models = ensemble(
                examples,
                train_indices,
                validation_indices,
                12,
                f"fold{fold_number}-b0",
            )
            b1_scores, b1_models = ensemble(
                examples,
                train_indices,
                validation_indices,
                16,
                f"fold{fold_number}-b1",
            )
            paired = paired_metrics(validation_labels, b0_scores, b1_scores)
            venue_metrics = {}
            for venue_name, venue_value in (("kalshi", 0), ("polymarket", 1)):
                subset = np.flatnonzero(examples["venue"][validation_indices] == venue_value)
                venue_metrics[venue_name] = (
                    paired_metrics(
                        validation_labels[subset], b0_scores[subset], b1_scores[subset]
                    )
                    if len(subset)
                    else None
                )
            fold_payload = {
                "fold": fold_number,
                "held_out_market_group": held_group,
                "training_rows": len(train_indices),
                "training_positives": int(train_labels.sum()),
                "validation_start_minute": validation_start,
                "validation_end_exclusive_minute": validation_end,
                "validation": paired,
                "validation_by_venue": venue_metrics,
                "models": {"b0": b0_models, "b1": b1_models},
            }
            fold_payload["model_sha256"] = model_hash(fold_payload["models"])
            folds.append(fold_payload)
            rows = np.empty(len(validation_indices), dtype=OOF_DTYPE)
            rows["market"] = examples["market"][validation_indices]
            rows["minute"] = examples["minute"][validation_indices]
            rows["venue"] = examples["venue"][validation_indices]
            rows["fold"] = fold_number
            rows["label"] = validation_labels
            rows["b0"] = b0_scores.astype(np.float32)
            rows["b1"] = b1_scores.astype(np.float32)
            rows["price_age"] = examples["price_age"][validation_indices]
            rows["news_1440"] = examples["features"][validation_indices, 14]
            rows.tofile(handle)
    os.replace(oof_temporary, OOF)
    oof_count = OOF.stat().st_size // OOF_DTYPE.itemsize
    oof = np.memmap(OOF, mode="r+", dtype=OOF_DTYPE, shape=(oof_count,))
    oof.sort(order=("market", "minute"), kind="quicksort")
    oof.flush()
    aggregate = paired_metrics(
        np.asarray(oof["label"], dtype=np.uint8),
        np.asarray(oof["b0"], dtype=np.float64),
        np.asarray(oof["b1"], dtype=np.float64),
    )
    aggregate_by_venue = {}
    for venue_name, venue_value in (("kalshi", 0), ("polymarket", 1)):
        subset = np.flatnonzero(oof["venue"] == venue_value)
        aggregate_by_venue[venue_name] = paired_metrics(
            np.asarray(oof["label"][subset], dtype=np.uint8),
            np.asarray(oof["b0"][subset], dtype=np.float64),
            np.asarray(oof["b1"][subset], dtype=np.float64),
        )
    bootstrap = brier_block_bootstrap(oof)
    fold_positive = sum(
        fold["validation"]["incremental_b1_over_b0"]["delta_average_precision"]
        is not None
        and fold["validation"]["incremental_b1_over_b0"]["delta_average_precision"]
        > 0.0
        and fold["validation"]["incremental_b1_over_b0"]["brier_improvement"] > 0.0
        for fold in folds
    )
    incremental = aggregate["incremental_b1_over_b0"]
    gates = {
        "h1_aggregate_delta_ap_positive": incremental["delta_average_precision"]
        is not None
        and incremental["delta_average_precision"] > 0.0,
        "h2_aggregate_brier_improvement_positive": incremental["brier_improvement"]
        > 0.0,
        "h3_both_positive_in_at_least_four_folds": fold_positive >= 4,
        "h4_bootstrap_brier_lower_bound_positive": bootstrap["ci_95_lower"] > 0.0,
        "h5_brier_nonnegative_each_venue": all(
            value["incremental_b1_over_b0"]["brier_improvement"] >= 0.0
            for value in aggregate_by_venue.values()
        ),
    }
    selected = "b1" if all(gates.values()) else "b0"
    selection = {
        "protocol_id": json.loads(PROTOCOL.read_text())["protocol_id"],
        "completed_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "status": "development_selection_complete_holdout_untouched",
        "historical_holdout_read": False,
        "development_rows": count,
        "oof_rows": oof_count,
        "folds": folds,
        "aggregate_oof": aggregate,
        "aggregate_oof_by_venue": aggregate_by_venue,
        "paired_brier_block_bootstrap": bootstrap,
        "folds_with_both_improvements_positive": fold_positive,
        "promotion_gates": gates,
        "selected_candidate": selected,
        "fallback_applied": selected == "b0",
        "oof_artifact": {
            "path": relative(OOF),
            "sha256": sha256_file(OOF),
            "bytes": OOF.stat().st_size,
            "dtype": OOF_DTYPE.descr,
        },
    }
    atomic_json(SELECTION_RESULT, selection)

    all_indices = np.arange(count, dtype=np.int64)
    width = 16 if selected == "b1" else 12
    _unused_scores, candidate_models = ensemble(
        examples,
        all_indices,
        np.empty(0, dtype=np.int64),
        width,
        f"final-{selected}",
    )
    candidate = {
        "protocol_id": selection["protocol_id"],
        "candidate": selected,
        "frozen_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "historical_holdout_read": False,
        "development_selection_result": {
            "path": relative(SELECTION_RESULT),
            "sha256": sha256_file(SELECTION_RESULT),
        },
        "training_rows": count,
        "training_positives": int(examples["label"].sum()),
        "model": candidate_models,
    }
    atomic_json(CANDIDATE, candidate)
    atomic_json(
        CANDIDATE_MANIFEST,
        {
            "protocol_id": selection["protocol_id"],
            "status": "one_candidate_frozen_before_historical_holdout",
            "candidate_count": 1,
            "historical_holdout_read": False,
            "artifacts": [
                {"path": relative(path), "sha256": sha256_file(path)}
                for path in (
                    PROTOCOL,
                    IMPLEMENTATION_MANIFEST,
                    EXAMPLES_MANIFEST,
                    Path(__file__).resolve(),
                    OOF,
                    SELECTION_RESULT,
                    CANDIDATE,
                )
            ],
        },
    )
    print(json.dumps({
        "aggregate_oof": aggregate,
        "bootstrap": bootstrap,
        "promotion_gates": gates,
        "selected_candidate": selected,
        "historical_holdout_read": False,
    }, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
