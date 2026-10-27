"""Run nested EventX v4 discovery models and freeze future model parameters."""

from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
from typing import Any

import numpy as np
from sklearn.linear_model import SGDClassifier
from sklearn.metrics import average_precision_score, roc_auc_score

from eventx.settings import REPO_ROOT
from eventx.tasks.build_v4_discovery_examples import (
    EXAMPLE_DTYPE,
    FEATURE_NAMES,
    sha256_file,
)


EXAMPLES = REPO_ROOT / "data/v4/discovery/examples/examples.bin"
EXAMPLES_MANIFEST = REPO_ROOT / "data/v4/discovery/examples/manifest.json"
OUTPUT = REPO_ROOT / "data/v4/discovery/models"
OOF = OUTPUT / "oof_predictions.bin"
RESULT = OUTPUT / "result.json"
FROZEN_MODELS = OUTPUT / "frozen_models.json"
MANIFEST = OUTPUT / "manifest.json"
SEEDS = (11, 23, 47)
EPOCHS = 5
LEARNING_RATE = 0.02
L2 = 0.0001
BATCH_ROWS = 65_536
MODEL_WIDTHS = {"b0": 12, "b1": 16, "b2": 22, "b3": 28}
LOG_COLUMNS = tuple(range(6, 10)) + tuple(range(12, 15)) + tuple(range(16, 28))
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
        ("b2", "<f4"),
        ("b3", "<f4"),
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


def scaler(
    examples: np.ndarray, indices: np.ndarray, width: int
) -> tuple[np.ndarray, np.ndarray]:
    total = np.zeros(width, dtype=np.float64)
    total_sq = np.zeros(width, dtype=np.float64)
    rows = 0
    for start in range(0, len(indices), BATCH_ROWS):
        batch = transformed(
            examples["features"][indices[start : start + BATCH_ROWS]], width
        )
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
            classifier.partial_fit(
                values,
                labels,
                classes=np.asarray([0, 1], dtype=np.uint8) if first else None,
            )
            first = False
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
    evaluation_indices: np.ndarray | None,
    width: int,
    label: str,
) -> tuple[np.ndarray | None, dict[str, Any]]:
    means, scales = scaler(examples, train_indices, width)
    predictions = (
        np.zeros(len(evaluation_indices), dtype=np.float64)
        if evaluation_indices is not None
        else None
    )
    models = []
    for seed in SEEDS:
        classifier = fit_seed(
            examples, train_indices, width, means, scales, seed, label
        )
        if predictions is not None and evaluation_indices is not None:
            predictions += predict(
                classifier, examples, evaluation_indices, width, means, scales
            )
        models.append({
            "seed": seed,
            "intercept": float(classifier.intercept_[0]),
            "coefficients": [float(value) for value in classifier.coef_[0]],
        })
    if predictions is not None:
        predictions /= len(SEEDS)
    return predictions, {
        "feature_names": list(FEATURE_NAMES[:width]),
        "means": [float(value) for value in means],
        "scales": [float(value) for value in scales],
        "models": models,
    }


def metrics(labels: np.ndarray, scores: np.ndarray) -> dict[str, Any]:
    clipped = np.clip(np.asarray(scores, dtype=np.float64), 1e-7, 1.0 - 1e-7)
    labels_float = np.asarray(labels, dtype=np.float64)
    positives = int(labels_float.sum())
    return {
        "rows": len(labels),
        "positives": positives,
        "prevalence": float(labels_float.mean()),
        "mean_prediction": float(clipped.mean()),
        "log_loss": float(
            -np.mean(labels_float * np.log(clipped) + (1 - labels_float) * np.log(1 - clipped))
        ),
        "brier": float(np.mean(np.square(labels_float - clipped))),
        "average_precision": (
            float(average_precision_score(labels, clipped)) if positives else None
        ),
        "roc_auc": (
            float(roc_auc_score(labels, clipped)) if len(np.unique(labels)) == 2 else None
        ),
    }


def comparison(
    labels: np.ndarray, baseline: np.ndarray, model: np.ndarray
) -> dict[str, float | None]:
    left = metrics(labels, baseline)
    right = metrics(labels, model)
    return {
        "log_loss_improvement": float(left["log_loss"]) - float(right["log_loss"]),
        "brier_improvement": float(left["brier"]) - float(right["brier"]),
        "delta_average_precision": (
            float(right["average_precision"]) - float(left["average_precision"])
            if left["average_precision"] is not None and right["average_precision"] is not None
            else None
        ),
    }


def block_bootstrap(oof: np.ndarray) -> dict[str, Any]:
    labels = np.asarray(oof["label"], dtype=np.float64)
    b0 = np.clip(np.asarray(oof["b0"], dtype=np.float64), 1e-7, 1 - 1e-7)
    b3 = np.clip(np.asarray(oof["b3"], dtype=np.float64), 1e-7, 1 - 1e-7)
    values = -labels * np.log(b0) - (1 - labels) * np.log(1 - b0)
    values -= -labels * np.log(b3) - (1 - labels) * np.log(1 - b3)
    boundaries = np.concatenate(
        ([0], np.flatnonzero(np.diff(oof["market"])) + 1, [len(oof)])
    )
    samples = 2000
    rng = np.random.default_rng(61)
    totals = np.zeros(samples, dtype=np.float64)
    for left, right in zip(boundaries[:-1], boundaries[1:]):
        market_values = values[left:right]
        size = len(market_values)
        block = min(72, size)
        blocks = int(np.ceil(size / block))
        starts = rng.integers(0, size, size=(samples, blocks))
        indices = (starts[:, :, None] + np.arange(block)[None, None, :]) % size
        totals += market_values[indices.reshape(samples, -1)[:, :size]].sum(axis=1)
    estimates = totals / len(oof)
    return {
        "estimand": "out-of-fold log-loss improvement B0 minus B3",
        "method": "paired circular 360-minute blocks within market",
        "samples": samples,
        "seed": 61,
        "mean": float(estimates.mean()),
        "ci_95_lower": float(np.quantile(estimates, 0.025)),
        "ci_95_upper": float(np.quantile(estimates, 0.975)),
        "probability_positive": float(np.mean(estimates > 0)),
    }


def main() -> None:
    if any(path.exists() for path in (OOF, RESULT, FROZEN_MODELS, MANIFEST)):
        raise SystemExit("v4 discovery model artifact already exists")
    verify_manifest(EXAMPLES_MANIFEST)
    count = EXAMPLES.stat().st_size // EXAMPLE_DTYPE.itemsize
    examples = np.memmap(EXAMPLES, mode="r", dtype=EXAMPLE_DTYPE, shape=(count,))
    OUTPUT.mkdir(parents=True, exist_ok=True)
    temporary = OOF.with_suffix(OOF.suffix + ".tmp")
    folds = []
    with temporary.open("wb") as handle:
        for fold, held_group, validation_start, validation_end in FOLDS:
            train = np.flatnonzero(
                (examples["minute"] < validation_start - 30)
                & (examples["group"] != held_group)
            )
            validation = np.flatnonzero(
                (examples["minute"] >= validation_start)
                & (examples["minute"] < validation_end)
                & (examples["group"] == held_group)
            )
            if not len(train) or not len(validation):
                raise RuntimeError(f"empty v4 fold {fold}")
            predictions: dict[str, np.ndarray] = {}
            for name, width in MODEL_WIDTHS.items():
                values, _model = ensemble(
                    examples, train, validation, width, f"fold{fold}-{name}"
                )
                assert values is not None
                predictions[name] = values
            rows = np.empty(len(validation), dtype=OOF_DTYPE)
            for field in ("market", "minute", "venue", "label"):
                rows[field] = examples[field][validation]
            rows["fold"] = fold
            for name in MODEL_WIDTHS:
                rows[name] = predictions[name]
            rows.tofile(handle)
            labels = np.asarray(rows["label"], dtype=np.uint8)
            fold_metrics = {
                name: metrics(labels, np.asarray(rows[name], dtype=np.float64))
                for name in MODEL_WIDTHS
            }
            folds.append({
                "fold": fold,
                "held_group": held_group,
                "train_rows": len(train),
                "validation": fold_metrics,
                "incremental_over_b0": {
                    name: comparison(
                        labels,
                        np.asarray(rows["b0"], dtype=np.float64),
                        np.asarray(rows[name], dtype=np.float64),
                    )
                    for name in ("b1", "b2", "b3")
                },
            })
            print(f"completed v4 fold {fold}/5", flush=True)
    os.replace(temporary, OOF)
    oof_count = OOF.stat().st_size // OOF_DTYPE.itemsize
    oof = np.memmap(OOF, mode="r", dtype=OOF_DTYPE, shape=(oof_count,))
    labels = np.asarray(oof["label"], dtype=np.uint8)
    aggregate = {
        name: metrics(labels, np.asarray(oof[name], dtype=np.float64))
        for name in MODEL_WIDTHS
    }
    increments = {
        name: comparison(
            labels,
            np.asarray(oof["b0"], dtype=np.float64),
            np.asarray(oof[name], dtype=np.float64),
        )
        for name in ("b1", "b2", "b3")
    }
    result = {
        "protocol_id": "eventx-v4-confirmatory-20260902",
        "created_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "status": "discovery_nested_models_complete",
        "confirmatory_status": "not_tested_future_holdout_unopened",
        "historical_interval_outcomes_previously_opened": True,
        "folds": folds,
        "aggregate_oof": aggregate,
        "incremental_over_b0": increments,
        "b3_vs_b0_bootstrap": block_bootstrap(oof),
    }
    atomic_json(RESULT, result)
    all_rows = np.arange(len(examples), dtype=np.int64)
    frozen: dict[str, Any] = {
        "protocol_id": result["protocol_id"],
        "trained_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "training_interval": "[2026-05-17T00:00:00Z, 2026-07-22T00:00:00Z)",
        "training_outcomes_previously_opened": True,
        "future_holdout_predictions_required_for_all_models": True,
        "learner": {
            "type": "standardized logistic SGD seed ensemble",
            "seeds": list(SEEDS),
            "epochs": EPOCHS,
            "learning_rate": LEARNING_RATE,
            "l2": L2,
        },
        "models": {},
    }
    for name, width in MODEL_WIDTHS.items():
        _unused, model = ensemble(
            examples, all_rows, None, width, f"final-{name}"
        )
        frozen["models"][name] = model
    serialized = json.dumps(frozen, sort_keys=True, separators=(",", ":")).encode()
    frozen["model_bundle_sha256"] = hashlib.sha256(serialized).hexdigest()
    atomic_json(FROZEN_MODELS, frozen)
    atomic_json(
        MANIFEST,
        {
            "protocol_id": result["protocol_id"],
            "status": result["status"],
            "artifacts": [
                {"path": relative(path), "sha256": sha256_file(path)}
                for path in (OOF, RESULT, FROZEN_MODELS, Path(__file__).resolve())
            ],
            "inputs": [
                {"path": relative(EXAMPLES), "sha256": sha256_file(EXAMPLES)}
            ],
        },
    )
    print(json.dumps({
        "status": result["status"],
        "aggregate_oof": aggregate,
        "incremental_over_b0": increments,
        "b3_vs_b0_bootstrap": result["b3_vs_b0_bootstrap"],
        "model_bundle_sha256": frozen["model_bundle_sha256"],
    }, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
