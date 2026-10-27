"""Run historical v4 B3 coefficient, convergence, and regularization diagnostics."""

from __future__ import annotations

import csv
from datetime import datetime, timezone
import json
import os
from pathlib import Path
from typing import Any

import numpy as np
from sklearn.linear_model import SGDClassifier

from eventx.settings import REPO_ROOT
from eventx.tasks.build_v4_discovery_examples import EXAMPLE_DTYPE, FEATURE_NAMES
from eventx.tasks.prepare_v3_1_historical_development_arrays import sha256_file
from eventx.tasks.run_v4_discovery_models import (
    BATCH_ROWS,
    FOLDS,
    LEARNING_RATE,
    LOG_COLUMNS,
    transformed,
)


EXAMPLES = REPO_ROOT / "data/v4/discovery/examples/examples.bin"
EXAMPLES_MANIFEST = REPO_ROOT / "data/v4/discovery/examples/manifest.json"
FUTURE = REPO_ROOT / "data/v4/confirmatory"
OUTPUT = REPO_ROOT / "data/v5/design_diagnostics/solver"
REPORT = OUTPUT / "report.json"
COEFFICIENTS = OUTPUT / "coefficient_stability.csv"
TRAJECTORY = OUTPUT / "convergence.csv"
REGULARIZATION = OUTPUT / "regularization.csv"
SUMMARY = OUTPUT / "SUMMARY.md"
MANIFEST = OUTPUT / "manifest.json"
WIDTH = 28
SEED = 11
FIXED_EPOCHS = 5
CONVERGENCE_EPOCHS = 15
DIAGNOSTIC_TRAIN_ROWS = 200_000


def relative(path: Path) -> str:
    return str(path.relative_to(REPO_ROOT))


def atomic_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n")
    os.replace(temporary, path)


def atomic_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    fields = list(dict.fromkeys(key for row in rows for key in row))
    temporary = path.with_suffix(path.suffix + ".tmp")
    with temporary.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)
    os.replace(temporary, path)


def verify_manifest(path: Path) -> None:
    manifest = json.loads(path.read_text(encoding="utf-8"))
    for artifact in manifest.get("artifacts", []):
        target = REPO_ROOT / str(artifact["path"])
        if not target.is_file() or sha256_file(target) != str(artifact["sha256"]):
            raise RuntimeError(f"hash-lock failure: {target}")


def calculate_scaler(examples: np.ndarray, indices: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    total = np.zeros(WIDTH, dtype=np.float64)
    total_sq = np.zeros(WIDTH, dtype=np.float64)
    rows = 0
    for start in range(0, len(indices), BATCH_ROWS):
        values = transformed(examples["features"][indices[start:start + BATCH_ROWS]], WIDTH)
        total += values.sum(axis=0, dtype=np.float64)
        total_sq += np.square(values).sum(axis=0, dtype=np.float64)
        rows += len(values)
    means = total / rows
    scales = np.sqrt(np.maximum(0.0, total_sq / rows - means * means))
    scales[scales == 0] = 1.0
    return means, scales


def scores(
    classifier: SGDClassifier,
    examples: np.ndarray,
    indices: np.ndarray,
    means: np.ndarray,
    scales: np.ndarray,
) -> np.ndarray:
    output = np.empty(len(indices), dtype=np.float64)
    for start in range(0, len(indices), BATCH_ROWS):
        chosen = indices[start:start + BATCH_ROWS]
        values = (transformed(examples["features"][chosen], WIDTH) - means) / scales
        output[start:start + len(chosen)] = classifier.predict_proba(values)[:, 1]
    return output


def log_loss(labels: np.ndarray, probabilities: np.ndarray) -> float:
    labels = np.asarray(labels, dtype=np.float64)
    probabilities = np.clip(np.asarray(probabilities, dtype=np.float64), 1e-7, 1 - 1e-7)
    return float(-np.mean(labels * np.log(probabilities) + (1 - labels) * np.log(1 - probabilities)))


def train_trajectory(
    examples: np.ndarray,
    train: np.ndarray,
    validation: np.ndarray,
    means: np.ndarray,
    scales: np.ndarray,
    *,
    penalty: str,
    alpha: float,
    l1_ratio: float,
    epochs: int,
    label: str,
) -> tuple[SGDClassifier, list[dict[str, Any]]]:
    classifier = SGDClassifier(
        loss="log_loss",
        penalty=penalty,
        alpha=alpha,
        l1_ratio=l1_ratio,
        fit_intercept=True,
        max_iter=1,
        tol=None,
        shuffle=False,
        learning_rate="constant",
        eta0=LEARNING_RATE,
        average=False,
        random_state=SEED,
    )
    rng = np.random.default_rng(SEED)
    diagnostic_rng = np.random.default_rng(911)
    diagnostic_train = np.sort(
        diagnostic_rng.choice(train, size=min(DIAGNOSTIC_TRAIN_ROWS, len(train)), replace=False)
    )
    history = []
    first = True
    for epoch in range(1, epochs + 1):
        order = rng.permutation(train)
        for start in range(0, len(order), BATCH_ROWS):
            chosen = order[start:start + BATCH_ROWS]
            values = (transformed(examples["features"][chosen], WIDTH) - means) / scales
            classifier.partial_fit(
                values,
                np.asarray(examples["label"][chosen], dtype=np.uint8),
                classes=np.asarray([0, 1], dtype=np.uint8) if first else None,
            )
            first = False
        train_scores = scores(classifier, examples, diagnostic_train, means, scales)
        validation_scores = scores(classifier, examples, validation, means, scales)
        history.append({
            "configuration": label,
            "epoch": epoch,
            "penalty": penalty,
            "alpha": alpha,
            "l1_ratio": l1_ratio if penalty == "elasticnet" else None,
            "train_sample_rows": len(diagnostic_train),
            "train_sample_log_loss": log_loss(examples["label"][diagnostic_train], train_scores),
            "validation_rows": len(validation),
            "validation_log_loss": log_loss(examples["label"][validation], validation_scores),
            "nonzero_coefficients": int(np.sum(np.abs(classifier.coef_[0]) > 1e-12)),
            "coefficient_l2_norm": float(np.linalg.norm(classifier.coef_[0])),
        })
        print(f"{label}: epoch {epoch}/{epochs}", flush=True)
    return classifier, history


def main() -> None:
    outputs = (REPORT, COEFFICIENTS, TRAJECTORY, REGULARIZATION, SUMMARY, MANIFEST)
    if any(path.exists() for path in outputs):
        raise SystemExit("v5 solver diagnostic already exists")
    forbidden = (FUTURE / "consumption_receipt.json", FUTURE / "examples/examples.bin", FUTURE / "evaluation/result.json")
    if any(path.exists() for path in forbidden):
        raise SystemExit("solver diagnosis refused after future holdout consumption")
    verify_manifest(EXAMPLES_MANIFEST)
    count = EXAMPLES.stat().st_size // EXAMPLE_DTYPE.itemsize
    examples = np.memmap(EXAMPLES, mode="r", dtype=EXAMPLE_DTYPE, shape=(count,))

    fold_models = []
    fold_histories = []
    for fold, held_group, validation_start, validation_end in FOLDS:
        train = np.flatnonzero((examples["minute"] < validation_start - 30) & (examples["group"] != held_group))
        validation = np.flatnonzero((examples["minute"] >= validation_start) & (examples["minute"] < validation_end) & (examples["group"] == held_group))
        means, scales = calculate_scaler(examples, train)
        model, history = train_trajectory(
            examples, train, validation, means, scales,
            penalty="l2", alpha=0.0001, l1_ratio=0.0,
            epochs=FIXED_EPOCHS, label=f"fold_{fold}_original_l2",
        )
        fold_models.append(np.asarray(model.coef_[0], dtype=np.float64).copy())
        fold_histories.append({"fold": fold, "train_rows": len(train), "validation_rows": len(validation), "history": history})

    coefficients = np.vstack(fold_models)
    coefficient_rows = []
    for column, feature in enumerate(FEATURE_NAMES):
        values = coefficients[:, column]
        nonzero = values[np.abs(values) > 1e-12]
        coefficient_rows.append({
            "feature": feature,
            **{f"fold_{fold + 1}": float(values[fold]) for fold in range(len(FOLDS))},
            "mean": float(values.mean()),
            "std": float(values.std()),
            "minimum": float(values.min()),
            "maximum": float(values.max()),
            "positive_folds": int(np.sum(values > 0)),
            "negative_folds": int(np.sum(values < 0)),
            "sign_consistent_nonzero": bool(len(nonzero) and (np.all(nonzero > 0) or np.all(nonzero < 0))),
        })

    fold, held_group, validation_start, validation_end = FOLDS[-1]
    train = np.flatnonzero((examples["minute"] < validation_start - 30) & (examples["group"] != held_group))
    validation = np.flatnonzero((examples["minute"] >= validation_start) & (examples["minute"] < validation_end) & (examples["group"] == held_group))
    means, scales = calculate_scaler(examples, train)
    _model, convergence = train_trajectory(
        examples, train, validation, means, scales,
        penalty="l2", alpha=0.0001, l1_ratio=0.0,
        epochs=CONVERGENCE_EPOCHS, label="fold_5_convergence_l2_1e-4",
    )
    configurations = (
        ("l2_1e-5", "l2", 0.00001, 0.0),
        ("l2_1e-3", "l2", 0.001, 0.0),
        ("elasticnet_l1ratio_0.1", "elasticnet", 0.0001, 0.1),
        ("elasticnet_l1ratio_0.5", "elasticnet", 0.0001, 0.5),
        ("elasticnet_l1ratio_0.9", "elasticnet", 0.0001, 0.9),
    )
    regularization_rows = []
    for label, penalty, alpha, ratio in configurations:
        _candidate, history = train_trajectory(
            examples, train, validation, means, scales,
            penalty=penalty, alpha=alpha, l1_ratio=ratio,
            epochs=8, label=f"fold_5_{label}",
        )
        best = min(history, key=lambda row: row["validation_log_loss"])
        regularization_rows.append({
            "configuration": label,
            "penalty": penalty,
            "alpha": alpha,
            "l1_ratio": ratio if penalty == "elasticnet" else None,
            "best_epoch": best["epoch"],
            "best_validation_log_loss": best["validation_log_loss"],
            "epoch_5_validation_log_loss": history[4]["validation_log_loss"],
            "epoch_8_validation_log_loss": history[-1]["validation_log_loss"],
            "nonzero_coefficients_at_best_epoch_report": best["nonzero_coefficients"],
        })

    original_fold5 = convergence[4]["validation_log_loss"]
    best_convergence = min(convergence, key=lambda row: row["validation_log_loss"])
    all_news_columns = range(12, 28)
    news_sign_instability = int(sum(not coefficient_rows[column]["sign_consistent_nonzero"] for column in all_news_columns))
    OUTPUT.mkdir(parents=True, exist_ok=True)
    atomic_csv(COEFFICIENTS, coefficient_rows)
    atomic_csv(TRAJECTORY, convergence)
    atomic_csv(REGULARIZATION, regularization_rows)
    report = {
        "diagnostic_id": "eventx-v5-pre-design-solver-diagnostics-20260903",
        "created_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "status": "complete",
        "role": "one-seed historical optimization diagnostic; not model selection or confirmation",
        "future_v4_data_read": False,
        "frozen_v4_changed": False,
        "fixed_architecture_fold_runs": fold_histories,
        "coefficient_stability": {
            "folds": len(FOLDS),
            "seed": SEED,
            "news_features_with_sign_instability": news_sign_instability,
            "news_feature_count": len(tuple(all_news_columns)),
            "table": relative(COEFFICIENTS),
        },
        "fold_5_convergence": {
            "epochs": CONVERGENCE_EPOCHS,
            "epoch_5_validation_log_loss": original_fold5,
            "best_epoch": best_convergence["epoch"],
            "best_validation_log_loss": best_convergence["validation_log_loss"],
            "change_best_minus_epoch_5": best_convergence["validation_log_loss"] - original_fold5,
        },
        "fold_5_regularization": regularization_rows,
        "limitations": [
            "one diagnostic seed rather than the frozen three-seed ensemble",
            "regularization comparison is one representative outer fold",
            "results guide a separate v5 design and cannot alter v4",
        ],
    }
    atomic_json(REPORT, report)
    best_regularization = min(regularization_rows, key=lambda row: row["best_validation_log_loss"])
    SUMMARY.write_text(
        "# EventX v5 solver diagnostics\n\n"
        "Historical diagnostic only; no future v4 data was read.\n\n"
        f"- Original fold-5 epoch-5 validation log loss: `{original_fold5:.6f}`.\n"
        f"- Best original-configuration epoch: {best_convergence['epoch']} with "
        f"`{best_convergence['validation_log_loss']:.6f}`.\n"
        f"- Best tested alternative on fold 5: `{best_regularization['configuration']}` "
        f"at epoch {best_regularization['best_epoch']} with "
        f"`{best_regularization['best_validation_log_loss']:.6f}`.\n"
        f"- News features with coefficient-sign instability across five one-seed "
        f"fold fits: {news_sign_instability}/{len(tuple(all_news_columns))}.\n\n"
        "These results distinguish optimization/regularization weaknesses from the "
        "feature-state failure diagnosed separately. They do not select a v5 model.\n",
        encoding="utf-8",
    )
    atomic_json(MANIFEST, {
        "diagnostic_id": report["diagnostic_id"],
        "status": report["status"],
        "artifacts": [{"path": relative(path), "sha256": sha256_file(path)} for path in (REPORT, COEFFICIENTS, TRAJECTORY, REGULARIZATION, SUMMARY, Path(__file__).resolve())],
        "inputs": [{"path": relative(path), "sha256": sha256_file(path)} for path in (EXAMPLES, EXAMPLES_MANIFEST)],
    })
    print(json.dumps({
        "status": report["status"],
        "future_v4_data_read": False,
        "coefficient_stability": report["coefficient_stability"],
        "fold_5_convergence": report["fold_5_convergence"],
        "best_regularization": best_regularization,
    }, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
