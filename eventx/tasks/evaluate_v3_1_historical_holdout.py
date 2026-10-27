"""Consume and evaluate the single frozen EventX v3.1 historical candidate once."""

from __future__ import annotations

from datetime import datetime, timezone
import json
import os
from pathlib import Path
from typing import Any

import numpy as np

from eventx.settings import REPO_ROOT
from eventx.tasks.build_v3_1_historical_development_examples import EXAMPLE_DTYPE
from eventx.tasks.prepare_v3_1_historical_development_arrays import sha256_file
from eventx.tasks.run_v3_1_historical_development_models import metrics


RELEASE = REPO_ROOT / "eventx/release/v3_1_historical_primary"
HOLDOUT = REPO_ROOT / "data/v3_1_historical/primary/holdout"
CANDIDATE = RELEASE / "candidate.json"
CANDIDATE_MANIFEST = RELEASE / "candidate_manifest.json"
IMPLEMENTATION_MANIFEST = RELEASE / "holdout_implementation_manifest.json"
AMENDMENT_MANIFEST = RELEASE / "holdout_receipt_amendment_manifest.json"
CONFIG = RELEASE / "holdout_evaluation_config.json"
EXAMPLES = HOLDOUT / "examples.bin"
EXAMPLES_MANIFEST = HOLDOUT / "examples_manifest.json"
RECEIPT = HOLDOUT / "holdout_consumption_receipt.json"
RESULT = HOLDOUT / "evaluation_result.json"
RESULT_MANIFEST = HOLDOUT / "evaluation_manifest.json"
BATCH_ROWS = 65_536
LOG_COLUMNS = (6, 7, 8, 9)


def relative(path: Path) -> str:
    return str(path.relative_to(REPO_ROOT))


def atomic_json(path: Path, value: Any) -> None:
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n")
    os.replace(temporary, path)


def verify_manifest(path: Path) -> None:
    value = json.loads(path.read_text(encoding="utf-8"))
    for artifact in value.get("artifacts", []):
        artifact_path = REPO_ROOT / str(artifact["path"])
        if not artifact_path.is_file() or sha256_file(artifact_path) != str(
            artifact["sha256"]
        ):
            raise RuntimeError(f"hash-lock failure: {artifact_path}")


def predict_frozen(candidate: dict[str, Any], examples: np.ndarray) -> np.ndarray:
    model = candidate["model"]
    names = list(model["feature_names"])
    width = len(names)
    if candidate.get("candidate") != "b0" or width != 12:
        raise RuntimeError("unexpected frozen candidate specification")
    means = np.asarray(model["means"], dtype=np.float64)
    scales = np.asarray(model["scales"], dtype=np.float64)
    if len(means) != width or len(scales) != width or np.any(scales <= 0.0):
        raise RuntimeError("invalid frozen scaling parameters")
    scores = np.zeros(len(examples), dtype=np.float64)
    for start in range(0, len(examples), BATCH_ROWS):
        stop = min(start + BATCH_ROWS, len(examples))
        values = np.asarray(examples["features"][start:stop, :width], dtype=np.float64).copy()
        for column in LOG_COLUMNS:
            values[:, column] = np.log1p(values[:, column])
        values = (values - means) / scales
        for frozen in model["models"]:
            coefficients = np.asarray(frozen["coefficients"], dtype=np.float64)
            if len(coefficients) != width:
                raise RuntimeError("invalid frozen coefficient vector")
            logits = np.clip(
                values @ coefficients + float(frozen["intercept"]), -709.0, 709.0
            )
            scores[start:stop] += 1.0 / (1.0 + np.exp(-logits))
    scores /= len(model["models"])
    return scores


def evaluate_subset(
    labels: np.ndarray, scores: np.ndarray, indices: np.ndarray
) -> dict[str, Any] | None:
    if not len(indices):
        return None
    return metrics(labels[indices], scores[indices])


def alert_summary(
    labels: np.ndarray, scores: np.ndarray, threshold: float
) -> dict[str, Any]:
    alerts = scores >= threshold
    count = int(alerts.sum())
    true_positive = int(np.sum(alerts & (labels == 1)))
    positives = int(labels.sum())
    return {
        "development_frozen_probability_threshold": threshold,
        "alerts": count,
        "alert_rate": count / len(labels),
        "positive_predictive_value": true_positive / count if count else None,
        "sensitivity": true_positive / positives if positives else None,
        "nominal_forecast_lead_time_minutes": 30,
        "lead_time_interpretation": (
            "Every alert at t targets the preregistered outcome at t+30; no "
            "post-hoc intrahorizon event-time metric is introduced."
        ),
    }


def decision_curve(
    labels: np.ndarray, scores: np.ndarray, thresholds: list[float]
) -> list[dict[str, float]]:
    prevalence = float(labels.mean())
    rows = len(labels)
    output = []
    for threshold in thresholds:
        selected = scores >= threshold
        true_positive = float(np.sum(selected & (labels == 1)))
        false_positive = float(np.sum(selected & (labels == 0)))
        odds = threshold / (1.0 - threshold)
        output.append({
            "threshold": threshold,
            "candidate_net_benefit": true_positive / rows - false_positive / rows * odds,
            "treat_all_net_benefit": prevalence - (1.0 - prevalence) * odds,
            "treat_none_net_benefit": 0.0,
        })
    return output


def main() -> None:
    if RESULT.exists() or RESULT_MANIFEST.exists():
        raise SystemExit("historical holdout result exists; rerun prohibited")
    if RECEIPT.exists():
        raise SystemExit("historical holdout receipt exists; consumption is irreversible")
    verify_manifest(CANDIDATE_MANIFEST)
    verify_manifest(AMENDMENT_MANIFEST)
    verify_manifest(EXAMPLES_MANIFEST)
    candidate = json.loads(CANDIDATE.read_text(encoding="utf-8"))
    config = json.loads(CONFIG.read_text(encoding="utf-8"))
    count = EXAMPLES.stat().st_size // EXAMPLE_DTYPE.itemsize
    if not count or count * EXAMPLE_DTYPE.itemsize != EXAMPLES.stat().st_size:
        raise RuntimeError("invalid holdout example artifact")

    # The immutable receipt is written before labels, predictions, or metrics are read.
    receipt = {
        "protocol_id": candidate["protocol_id"],
        "consumed_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "status": (
            "historical_holdout_irreversibly_consumed_before_prediction_or_"
            "performance_metric_read_with_disclosed_label_summary_deviation"
        ),
        "reruns_permitted": False,
        "candidate": {
            "path": relative(CANDIDATE),
            "sha256": sha256_file(CANDIDATE),
        },
        "holdout_examples": {
            "path": relative(EXAMPLES),
            "sha256": sha256_file(EXAMPLES),
            "rows": count,
        },
        "evaluation_implementation": {
            "path": relative(AMENDMENT_MANIFEST),
            "sha256": sha256_file(AMENDMENT_MANIFEST),
        },
        "pre_receipt_label_summary_read": True,
        "pre_receipt_label_summary": {
            "rows": 211718,
            "positives": 26381,
            "prevalence": 0.12460442664298738,
        },
        "predictions_or_performance_metrics_read_before_receipt": False,
        "deviation": {
            "path": relative(RELEASE / "HOLDOUT_PROTOCOL_DEVIATION.md"),
            "sha256": sha256_file(RELEASE / "HOLDOUT_PROTOCOL_DEVIATION.md"),
        },
    }
    atomic_json(RECEIPT, receipt)

    examples = np.memmap(EXAMPLES, mode="r", dtype=EXAMPLE_DTYPE, shape=(count,))
    labels = np.asarray(examples["label"], dtype=np.uint8)
    scores = predict_frozen(candidate, examples)
    all_indices = np.arange(count, dtype=np.int64)
    by_venue = {}
    for name, value in (("kalshi", 0), ("polymarket", 1)):
        by_venue[name] = evaluate_subset(
            labels, scores, np.flatnonzero(examples["venue"] == value)
        )
    freshness = {
        "le_30_minutes": evaluate_subset(
            labels, scores, np.flatnonzero(examples["price_age"] <= 30.0)
        ),
        "le_60_minutes": evaluate_subset(
            labels, scores, np.flatnonzero(examples["price_age"] <= 60.0)
        ),
        "gt_60_minutes": evaluate_subset(
            labels, scores, np.flatnonzero(examples["price_age"] > 60.0)
        ),
    }
    result = {
        "protocol_id": candidate["protocol_id"],
        "completed_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "status": "one_shot_historical_holdout_complete_with_disclosed_deviation",
        "candidate": candidate["candidate"],
        "candidate_count": 1,
        "news_incremental_model_evaluated_on_holdout": False,
        "news_incremental_inference": (
            "B1 failed all development promotion gates; the holdout evaluates only "
            "the preregistered B0 fallback and cannot rescue B1."
        ),
        "rows": count,
        "primary_and_calibration_metrics": evaluate_subset(
            labels, scores, all_indices
        ),
        "by_venue": by_venue,
        "price_freshness_robustness": freshness,
        "trade_arrival_diagnostic": {
            "price_age_le_5_minutes": evaluate_subset(
                labels, scores, np.flatnonzero(examples["price_age"] <= 5.0)
            ),
            "price_age_gt_5_minutes": evaluate_subset(
                labels, scores, np.flatnonzero(examples["price_age"] > 5.0)
            ),
        },
        "alert_operating_point": alert_summary(
            labels, scores, float(config["alert_probability_threshold"])
        ),
        "decision_curve": decision_curve(
            labels, scores, [float(value) for value in config["decision_thresholds"]]
        ),
        "consumption_receipt": {
            "path": relative(RECEIPT),
            "sha256": sha256_file(RECEIPT),
        },
    }
    atomic_json(RESULT, result)
    atomic_json(
        RESULT_MANIFEST,
        {
            "protocol_id": candidate["protocol_id"],
            "status": "one_shot_historical_holdout_complete_rerun_prohibited",
            "artifacts": [
                {"path": relative(path), "sha256": sha256_file(path)}
                for path in (
                    CANDIDATE,
                    CANDIDATE_MANIFEST,
                    IMPLEMENTATION_MANIFEST,
                    AMENDMENT_MANIFEST,
                    CONFIG,
                    EXAMPLES_MANIFEST,
                    RECEIPT,
                    RESULT,
                    Path(__file__).resolve(),
                )
            ],
        },
    )
    print(json.dumps(result, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
