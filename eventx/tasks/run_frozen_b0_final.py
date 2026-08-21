"""Run a one-shot canonical B0 evaluation from an approved freeze manifest.

The evaluator refuses to open labels unless the manifest marks the holdout as
untouched and explicitly authorizes confirmatory evaluation. It also refuses
to replace an existing result.
"""

from __future__ import annotations

import argparse
import json
from datetime import datetime
from pathlib import Path
from typing import Any

from eventx.features.build_kol_features import parse_ts
from eventx.settings import REPO_ROOT
from eventx.tasks.freeze_toy import hash_file
from eventx.tasks.run_b1 import MARKET_FEATURES, metrics, model_result, transform


def read_jsonl(path: Path):
    with path.open() as handle:
        for line in handle:
            if line.strip():
                yield json.loads(line)


def load_frozen_rows(
    labels_path: Path,
    cadence_min: int,
    training_end_exclusive: datetime,
    test_start: datetime,
) -> tuple[list[list[float]], list[int], list[list[float]], list[int], dict[str, int]]:
    train_vectors: list[list[float]] = []
    train_labels: list[int] = []
    test_vectors: list[list[float]] = []
    test_labels: list[int] = []
    skipped_between_train_and_test = 0
    for row in read_jsonl(labels_path):
        timestamp = str(row["ts"])
        minute = int(timestamp[11:13]) * 60 + int(timestamp[14:16])
        if timestamp[17:19] != "00" or minute % cadence_min:
            continue
        timestamp_dt = parse_ts(timestamp)
        if timestamp_dt < training_end_exclusive:
            if int(row["eligible"]):
                train_vectors.append(
                    [transform(name, row[name]) for name in MARKET_FEATURES]
                )
                train_labels.append(int(row["y_jump"]))
        elif timestamp_dt < test_start:
            skipped_between_train_and_test += 1
        elif str(row["split"]) == "test" and int(row["eligible"]):
            test_vectors.append(
                [transform(name, row[name]) for name in MARKET_FEATURES]
            )
            test_labels.append(int(row["y_jump"]))
    return train_vectors, train_labels, test_vectors, test_labels, {
        "train_rows": len(train_labels),
        "train_positives": sum(train_labels),
        "test_rows": len(test_labels),
        "test_positives": sum(test_labels),
        "cadence_rows_in_boundary_gap_skipped": skipped_between_train_and_test,
    }


def relative(path: Path) -> str:
    return str(path.resolve().relative_to(REPO_ROOT.resolve()))


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the frozen one-shot EventX B0 test")
    parser.add_argument("--freeze-manifest", type=Path)
    parser.add_argument("--labels", type=Path)
    parser.add_argument("--out", type=Path)
    args = parser.parse_args()

    root = REPO_ROOT / "data" / "v1" / "toy"
    manifest_path = args.freeze_manifest or root / "final_baseline_freeze_manifest.json"
    out_path = args.out or root / "b0_canonical_final_test.json"
    if not manifest_path.exists():
        raise SystemExit(f"Missing final baseline freeze manifest: {manifest_path}")
    manifest = json.loads(manifest_path.read_text())

    # These checks deliberately precede opening the labels artifact.
    holdout = manifest["holdout_integrity"]
    authorization = manifest["confirmatory_evaluation"]
    if holdout["status"] != "untouched":
        raise SystemExit(
            "CONFIRMATORY EVALUATION BLOCKED: holdout status is "
            f"{holdout['status']!r}, not 'untouched'."
        )
    if not authorization["allowed"]:
        raise SystemExit(
            "CONFIRMATORY EVALUATION BLOCKED: freeze manifest does not authorize it."
        )
    if out_path.exists():
        raise SystemExit(f"ONE-SHOT GUARD: refusing to replace existing result: {out_path}")

    evaluator_path = Path(__file__).resolve()
    expected_evaluator_hash = authorization["evaluator"]["sha256"]
    if hash_file(evaluator_path)["sha256"] != expected_evaluator_hash:
        raise SystemExit("Frozen evaluator source hash mismatch.")
    if manifest["baseline"]["features"] != MARKET_FEATURES:
        raise SystemExit("Frozen B0 feature list does not match evaluator source.")
    hyperparameters = manifest["baseline"]["fixed_hyperparameters"]
    if hyperparameters != {
        "epochs": 8,
        "l2": 1.0e-4,
        "learning_rate": 0.02,
        "shuffle_seed": 11,
    }:
        raise SystemExit("Frozen B0 hyperparameters do not match evaluator source.")

    labels_path = args.labels or REPO_ROOT / manifest["inputs"]["labels"]["path"]
    if hash_file(labels_path)["sha256"] != manifest["inputs"]["labels"]["sha256"]:
        raise SystemExit("Frozen labels artifact hash mismatch.")
    cadence_min = int(manifest["baseline"]["cadence_min"])
    training_end = parse_ts(manifest["baseline"]["training_end_exclusive"])
    test_start = parse_ts(manifest["holdout_integrity"]["test_start"])
    train_vectors, train_labels, test_vectors, test_labels, load_stats = load_frozen_rows(
        labels_path,
        cadence_min,
        training_end,
        test_start,
    )
    if (
        not train_vectors
        or not test_vectors
        or len(set(train_labels)) < 2
        or len(set(test_labels)) < 2
    ):
        raise SystemExit("Frozen evaluation lacks usable binary class coverage.")
    expected_train_rows = int(manifest["baseline"]["expected_training_rows"])
    if len(train_labels) != expected_train_rows:
        raise SystemExit(
            f"Frozen training-row mismatch: {len(train_labels)} != {expected_train_rows}"
        )

    model, test_scores = model_result(
        train_vectors,
        train_labels,
        test_vectors,
        test_labels,
        MARKET_FEATURES,
        epochs=int(hyperparameters["epochs"]),
    )
    prevalence = sum(train_labels) / len(train_labels)
    result: dict[str, Any] = {
        "status": "confirmatory_test_complete_no_further_tuning_permitted",
        "dataset_id": manifest["dataset_id"],
        "freeze_manifest": {
            "path": relative(manifest_path),
            "sha256": hash_file(manifest_path)["sha256"],
        },
        "model": "b0_market_only",
        "features": MARKET_FEATURES,
        "fixed_hyperparameters": hyperparameters,
        "load_validation": load_stats,
        "test": {
            "prevalence_baseline": metrics(
                test_labels,
                [prevalence] * len(test_labels),
            ),
            "b0_market_only": metrics(test_labels, test_scores),
        },
        "locked_model": model,
        "policy": (
            "This is the sole authorized evaluation of the frozen specification. "
            "The result may not be used to change features, hyperparameters, or "
            "eligibility rules."
        ),
        "inputs": {
            "labels": {
                "path": relative(labels_path),
                "sha256": manifest["inputs"]["labels"]["sha256"],
            },
            "evaluator_sha256": expected_evaluator_hash,
        },
    }
    temporary = out_path.with_suffix(out_path.suffix + ".tmp")
    temporary.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
    temporary.replace(out_path)
    print(json.dumps(result["test"], indent=2, sort_keys=True))
    print(f"Wrote one-shot test result: {out_path}")


if __name__ == "__main__":
    main()
