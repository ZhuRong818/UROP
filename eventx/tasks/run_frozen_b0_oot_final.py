"""Run the one-shot canonical B0 evaluation on the frozen OOT holdout."""

from __future__ import annotations

import argparse
import json
from datetime import UTC, datetime
from pathlib import Path

from eventx.features.build_kol_features import parse_ts
from eventx.settings import REPO_ROOT
from eventx.tasks.freeze_toy import hash_file
from eventx.tasks.run_b1 import MARKET_FEATURES, metrics, model_result, transform
from eventx.tasks.run_b0 import read_jsonl


def cadence_match(timestamp: str, cadence_min: int) -> bool:
    minute = int(timestamp[11:13]) * 60 + int(timestamp[14:16])
    return timestamp[17:19] == "00" and minute % cadence_min == 0


def load_training_rows(
    labels_path: Path,
    cadence_min: int,
    training_end_exclusive: datetime,
) -> tuple[list[list[float]], list[int]]:
    vectors = []
    labels = []
    for row in read_jsonl(labels_path):
        timestamp = str(row["ts"])
        if not cadence_match(timestamp, cadence_min):
            continue
        if parse_ts(timestamp) < training_end_exclusive and int(row["eligible"]):
            vectors.append([transform(name, row[name]) for name in MARKET_FEATURES])
            labels.append(int(row["y_jump"]))
    return vectors, labels


def load_holdout_rows(
    labels_path: Path,
    cadence_min: int,
    holdout_start: datetime,
    holdout_end: datetime,
) -> tuple[list[list[float]], list[int], set[str]]:
    vectors = []
    labels = []
    markets = set()
    for row in read_jsonl(labels_path):
        timestamp = str(row["ts"])
        if not cadence_match(timestamp, cadence_min) or not int(row["eligible"]):
            continue
        timestamp_dt = parse_ts(timestamp)
        if not holdout_start <= timestamp_dt <= holdout_end:
            raise SystemExit(f"Eligible OOT row outside frozen holdout: {timestamp}")
        vectors.append([transform(name, row[name]) for name in MARKET_FEATURES])
        labels.append(int(row["y_jump"]))
        markets.add(str(row["market_id"]))
    return vectors, labels, markets


def relative(path: Path) -> str:
    return str(path.resolve().relative_to(REPO_ROOT.resolve()))


def main() -> None:
    parser = argparse.ArgumentParser(description="Run frozen EventX B0 on OOT holdout")
    parser.add_argument("--holdout-freeze", type=Path)
    parser.add_argument("--out", type=Path)
    args = parser.parse_args()
    root = REPO_ROOT / "data" / "v1_oot_20260723_20260730"
    freeze_path = args.holdout_freeze or root / "frozen_holdout_manifest.json"
    out_path = args.out or root / "b0_oot_final_result.json"
    receipt_path = root / "holdout_consumption_receipt.json"
    if not freeze_path.exists():
        raise SystemExit(f"Missing OOT freeze manifest: {freeze_path}")
    freeze = json.loads(freeze_path.read_text())

    # Authorization and one-shot checks deliberately precede opening either label file.
    if freeze["holdout_integrity"]["status"] != "untouched":
        raise SystemExit("OOT EVALUATION BLOCKED: holdout is not marked untouched.")
    if not freeze["confirmatory_evaluation"]["allowed"]:
        raise SystemExit("OOT EVALUATION BLOCKED: manifest does not authorize evaluation.")
    if out_path.exists() or receipt_path.exists():
        raise SystemExit("ONE-SHOT GUARD: OOT holdout has already been consumed.")
    evaluator_path = Path(__file__).resolve()
    evaluator_hash = hash_file(evaluator_path)["sha256"]
    if evaluator_hash != freeze["confirmatory_evaluation"]["evaluator"]["sha256"]:
        raise SystemExit("Frozen OOT evaluator source hash mismatch.")
    baseline = freeze["baseline_contract"]
    if baseline["features"] != MARKET_FEATURES:
        raise SystemExit("Frozen baseline feature contract mismatch.")
    if baseline["fixed_hyperparameters"] != {
        "epochs": 8,
        "l2": 1.0e-4,
        "learning_rate": 0.02,
        "shuffle_seed": 11,
    }:
        raise SystemExit("Frozen baseline hyperparameter contract mismatch.")

    training_path = REPO_ROOT / freeze["inputs"]["training_labels"]["path"]
    holdout_path = REPO_ROOT / freeze["inputs"]["holdout_labels"]["path"]
    if hash_file(training_path)["sha256"] != freeze["inputs"]["training_labels"]["sha256"]:
        raise SystemExit("Frozen training-label hash mismatch.")
    if hash_file(holdout_path)["sha256"] != freeze["inputs"]["holdout_labels"]["sha256"]:
        raise SystemExit("Frozen holdout-label hash mismatch.")
    cadence_min = int(baseline["cadence_min"])
    train_vectors, train_labels = load_training_rows(
        training_path,
        cadence_min,
        parse_ts(baseline["training_end_exclusive"]),
    )
    test_vectors, test_labels, test_markets = load_holdout_rows(
        holdout_path,
        cadence_min,
        parse_ts(freeze["holdout_integrity"]["start"]),
        parse_ts(freeze["holdout_integrity"]["end"]),
    )
    if len(train_labels) != int(baseline["expected_training_rows"]):
        raise SystemExit("Canonical training-row count changed after freeze.")
    if len(test_labels) != int(freeze["holdout_integrity"]["expected_evaluation_rows"]):
        raise SystemExit("OOT evaluation-row count changed after freeze.")
    if (
        not train_labels
        or not test_labels
        or len(set(train_labels)) < 2
        or len(set(test_labels)) < 2
    ):
        raise SystemExit("Frozen OOT evaluation lacks binary class coverage.")

    model, scores = model_result(
        train_vectors,
        train_labels,
        test_vectors,
        test_labels,
        MARKET_FEATURES,
        epochs=int(baseline["fixed_hyperparameters"]["epochs"]),
    )
    prevalence = sum(train_labels) / len(train_labels)
    result = {
        "status": "one_shot_oot_confirmatory_evaluation_complete",
        "dataset_id": freeze["dataset_id"],
        "baseline": "b0_market_only",
        "freeze_manifest": {
            "path": relative(freeze_path),
            "sha256": hash_file(freeze_path)["sha256"],
        },
        "evaluation_rows": len(test_labels),
        "evaluation_markets": len(test_markets),
        "test": {
            "prevalence_baseline": metrics(
                test_labels,
                [prevalence] * len(test_labels),
            ),
            "b0_market_only": metrics(test_labels, scores),
        },
        "locked_model": model,
        "policy": (
            "This result consumes the frozen OOT holdout. No feature, model, "
            "eligibility, or hyperparameter changes may be justified from it."
        ),
        "inputs": {
            "training_labels_sha256": freeze["inputs"]["training_labels"]["sha256"],
            "holdout_labels_sha256": freeze["inputs"]["holdout_labels"]["sha256"],
            "evaluator_sha256": evaluator_hash,
        },
    }
    result_tmp = out_path.with_suffix(".json.tmp")
    result_tmp.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
    result_tmp.replace(out_path)
    receipt = {
        "status": "consumed",
        "consumed_at": datetime.now(UTC).isoformat().replace("+00:00", "Z"),
        "dataset_id": freeze["dataset_id"],
        "freeze_manifest_sha256": result["freeze_manifest"]["sha256"],
        "result": {
            "path": relative(out_path),
            **hash_file(out_path),
        },
        "rerun_permitted": False,
    }
    receipt_tmp = receipt_path.with_suffix(".json.tmp")
    receipt_tmp.write_text(json.dumps(receipt, indent=2, sort_keys=True) + "\n")
    receipt_tmp.replace(receipt_path)
    print(
        json.dumps(
            {
                "status": result["status"],
                "evaluation_rows": result["evaluation_rows"],
                "evaluation_markets": result["evaluation_markets"],
                "test": result["test"],
                "result": str(out_path),
                "receipt": str(receipt_path),
            },
            indent=2,
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
