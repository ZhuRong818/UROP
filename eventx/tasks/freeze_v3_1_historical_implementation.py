"""Freeze tested EventX v3.1 outcome-construction and model code."""

from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import importlib.metadata
import json
import os
from pathlib import Path
import platform
from typing import Any

from eventx.settings import REPO_ROOT
from eventx.tasks.test_v3_1_historical_development_examples import main as test_examples
from eventx.tasks.test_v3_1_historical_development_models import main as test_models


RELEASE = REPO_ROOT / "eventx/release/v3_1_historical_primary"
DATA = REPO_ROOT / "data/v3_1_historical/primary"
MANIFEST = RELEASE / "implementation_manifest.json"
TEST_RECEIPT = RELEASE / "synthetic_test_receipt.json"
PROHIBITED = (
    DATA / "development/examples.bin",
    DATA / "development/examples_report.json",
    DATA / "development/selection_result.json",
    DATA / "holdout",
)


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


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


def main() -> None:
    if MANIFEST.exists() or TEST_RECEIPT.exists():
        raise SystemExit("v3.1 implementation is already frozen")
    if any(path.exists() for path in PROHIBITED):
        raise SystemExit("outcome-bearing artifact exists before implementation freeze")
    verify_manifest(RELEASE / "preregistration_manifest.json")
    verify_manifest(DATA / "development/data_gate/manifest.json")
    verify_manifest(DATA / "development/prepared/manifest.json")
    test_examples()
    test_models()
    receipt = {
        "protocol_id": "eventx-v3.1-historical-primary-20260902",
        "completed_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "status": "synthetic_contract_tests_passed_before_development_labels",
        "labels_or_outcomes_read": False,
        "historical_holdout_read": False,
        "tests": [
            "point_in_time_example_construction",
            "fixed_logistic_sgd",
            "paired_circular_brier_bootstrap",
        ],
        "runtime": {
            "python": platform.python_version(),
            "numpy": importlib.metadata.version("numpy"),
            "scikit_learn": importlib.metadata.version("scikit-learn"),
            "scipy": importlib.metadata.version("scipy"),
        },
    }
    atomic_json(TEST_RECEIPT, receipt)
    artifacts = (
        RELEASE / "protocol.json",
        RELEASE / "preregistration_manifest.json",
        RELEASE / "IMPLEMENTATION_SPEC.md",
        RELEASE / "runtime_requirements.txt",
        DATA / "development/data_gate/manifest.json",
        DATA / "development/prepared/manifest.json",
        REPO_ROOT / "eventx/tasks/build_v3_1_historical_development_examples.py",
        REPO_ROOT / "eventx/tasks/run_v3_1_historical_development_models.py",
        REPO_ROOT / "eventx/tasks/test_v3_1_historical_development_examples.py",
        REPO_ROOT / "eventx/tasks/test_v3_1_historical_development_models.py",
        Path(__file__).resolve(),
        TEST_RECEIPT,
    )
    atomic_json(
        MANIFEST,
        {
            "protocol_id": receipt["protocol_id"],
            "manifest_id": "eventx-v3.1-historical-implementation-20260902",
            "status": "frozen_before_development_labels",
            "labels_or_outcomes_read": False,
            "historical_holdout_read": False,
            "runtime": receipt["runtime"],
            "artifacts": [
                {"path": relative(path), "sha256": sha256_file(path)}
                for path in artifacts
            ],
        },
    )
    print(json.dumps(receipt, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
