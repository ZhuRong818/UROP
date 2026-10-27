"""Freeze the v3.1 holdout retrieval and one-shot evaluation implementation."""

from __future__ import annotations

from datetime import datetime, timezone
import json
import os
from pathlib import Path
from typing import Any

import numpy as np

from eventx.settings import REPO_ROOT
from eventx.tasks.prepare_v3_1_historical_development_arrays import sha256_file
from eventx.tasks.run_v3_1_historical_development_models import OOF_DTYPE
from eventx.tasks.test_v3_1_historical_holdout import main as test_holdout


RELEASE = REPO_ROOT / "eventx/release/v3_1_historical_primary"
DATA = REPO_ROOT / "data/v3_1_historical/primary"
MANIFEST = RELEASE / "holdout_implementation_manifest.json"
CONFIG = RELEASE / "holdout_evaluation_config.json"
TEST_RECEIPT = RELEASE / "holdout_synthetic_test_receipt.json"
OOF = DATA / "development/oof_predictions.bin"
HOLDOUT = DATA / "holdout"
CANDIDATE = RELEASE / "candidate.json"
CANDIDATE_MANIFEST = RELEASE / "candidate_manifest.json"


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


def main() -> None:
    if any(path.exists() for path in (MANIFEST, CONFIG, TEST_RECEIPT)):
        raise SystemExit("holdout implementation is already frozen")
    if HOLDOUT.exists():
        raise SystemExit("holdout data exists before implementation freeze")
    verify_manifest(CANDIDATE_MANIFEST)
    candidate = json.loads(CANDIDATE.read_text(encoding="utf-8"))
    if candidate.get("candidate") != "b0":
        raise SystemExit("frozen candidate is not B0")
    count = OOF.stat().st_size // OOF_DTYPE.itemsize
    oof = np.memmap(OOF, mode="r", dtype=OOF_DTYPE, shape=(count,))
    alert_threshold = float(np.quantile(np.asarray(oof["b0"]), 0.90, method="linear"))
    test_holdout()
    now = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
    atomic_json(
        CONFIG,
        {
            "protocol_id": candidate["protocol_id"],
            "frozen_at": now,
            "candidate": "b0",
            "alert_probability_threshold": alert_threshold,
            "alert_threshold_source": (
                "90th percentile of frozen development OOF B0 probabilities"
            ),
            "alert_threshold_quantile_method": "linear",
            "decision_thresholds": [0.05, 0.10, 0.15, 0.20, 0.25, 0.30, 0.40, 0.50],
            "historical_holdout_read": False,
        },
    )
    atomic_json(
        TEST_RECEIPT,
        {
            "protocol_id": candidate["protocol_id"],
            "completed_at": now,
            "status": "synthetic_holdout_contract_passed_before_holdout_retrieval",
            "historical_holdout_read": False,
            "tests": [
                "left_context_and_future_append_invariance",
                "b0_only_feature_contract",
                "manual_frozen_ensemble_prediction",
            ],
        },
    )
    artifacts = (
        RELEASE / "protocol.json",
        CANDIDATE,
        CANDIDATE_MANIFEST,
        RELEASE / "HOLDOUT_IMPLEMENTATION_SPEC.md",
        CONFIG,
        DATA / "development/prepared/manifest.json",
        REPO_ROOT / "eventx/tasks/fetch_v3_historical_development_trades.py",
        REPO_ROOT / "eventx/tasks/fetch_v3_1_historical_holdout_trades.py",
        REPO_ROOT / "eventx/tasks/build_v3_1_historical_holdout_examples.py",
        REPO_ROOT / "eventx/tasks/evaluate_v3_1_historical_holdout.py",
        REPO_ROOT / "eventx/tasks/test_v3_1_historical_holdout.py",
        Path(__file__).resolve(),
        TEST_RECEIPT,
    )
    atomic_json(
        MANIFEST,
        {
            "protocol_id": candidate["protocol_id"],
            "manifest_id": "eventx-v3.1-historical-holdout-implementation-20260902",
            "status": "frozen_after_candidate_before_historical_holdout_retrieval",
            "candidate": "b0",
            "candidate_count": 1,
            "historical_holdout_read": False,
            "artifacts": [
                {"path": relative(path), "sha256": sha256_file(path)}
                for path in artifacts
            ],
        },
    )
    print(json.dumps({
        "status": "holdout_implementation_frozen",
        "candidate": "b0",
        "alert_probability_threshold": alert_threshold,
        "historical_holdout_read": False,
    }, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
