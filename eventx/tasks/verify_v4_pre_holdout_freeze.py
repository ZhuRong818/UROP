"""Verify the complete EventX v4 freeze before the future holdout."""

from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
from typing import Any

from eventx.settings import REPO_ROOT
from eventx.tasks.prepare_v3_1_historical_development_arrays import sha256_file


DESIGN = REPO_ROOT / "eventx/release/v4/design_manifest.json"
PREREG = REPO_ROOT / "eventx/release/v4/preregistration_manifest.json"
COLLECTION = REPO_ROOT / "eventx/release/v4/collection_manifest.json"
MODEL = REPO_ROOT / "eventx/release/v4/model_freeze_manifest.json"
COHORT_REPORT = REPO_ROOT / "data/v4/confirmatory/cohort_gate/report.json"
COLLECTOR_STATE = REPO_ROOT / "data/v4/confirmatory/sealed_inputs/collector_state.json"
OUTPUT = REPO_ROOT / "data/v4/confirmatory/pre_holdout_verification.json"


def atomic_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n")
    os.replace(temporary, path)


def verify_hashes(mapping: dict[str, str], checks: dict[str, bool]) -> None:
    for name, expected in mapping.items():
        path = REPO_ROOT / name
        checks[f"hash:{name}"] = path.is_file() and sha256_file(path) == expected


def main() -> None:
    if OUTPUT.exists():
        raise SystemExit("v4 pre-holdout verification already exists")
    design = json.loads(DESIGN.read_text())
    prereg = json.loads(PREREG.read_text())
    collection = json.loads(COLLECTION.read_text())
    model = json.loads(MODEL.read_text())
    cohort = json.loads(COHORT_REPORT.read_text())
    state = json.loads(COLLECTOR_STATE.read_text())
    checks: dict[str, bool] = {}
    verify_hashes(design["hashes"], checks)
    verify_hashes(prereg["hashes"], checks)
    verify_hashes(model["hashes"], checks)
    checks["collection_protocol_hash"] = (
        sha256_file(REPO_ROOT / "eventx/release/v4/protocol.json")
        == collection["protocol_sha256"]
    )
    checks["collection_cohort_hash"] = (
        sha256_file(REPO_ROOT / "data/v4/confirmatory/cohort_gate/cohort.jsonl")
        == collection["cohort_sha256"]
    )
    checks["collection_code_hash"] = (
        sha256_file(REPO_ROOT / collection["collector"]["path"])
        == collection["collector"]["sha256"]
    )
    frozen = json.loads(
        (REPO_ROOT / "data/v4/discovery/models/frozen_models.json").read_text()
    )
    claimed = frozen.pop("model_bundle_sha256")
    calculated = hashlib.sha256(
        json.dumps(frozen, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()
    checks["internal_model_bundle_hash"] = (
        claimed == calculated == model["model_bundle_internal_sha256"]
    )
    checks["cohort_gate_passed"] = cohort.get("status") == "passed_and_frozen"
    checks["cohort_markets_470"] = cohort.get("markets") == 470
    checks["all_models_frozen"] = set(frozen["models"]) == {"b0", "b1", "b2", "b3"}
    checks["collector_has_no_labels_predictions_or_metrics"] = (
        state.get("labels_predictions_or_metrics_computed") is False
    )
    checks["holdout_not_started_at_verification"] = datetime.now(timezone.utc) < datetime(
        2026, 9, 6, tzinfo=timezone.utc
    )
    passed = all(checks.values())
    report = {
        "protocol_id": "eventx-v4-confirmatory-polymarket-20260902",
        "created_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "status": "passed" if passed else "failed",
        "checks_passed": sum(checks.values()),
        "checks_total": len(checks),
        "checks": checks,
    }
    atomic_json(OUTPUT, report)
    print(json.dumps(report, indent=2, sort_keys=True))
    if not passed:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
