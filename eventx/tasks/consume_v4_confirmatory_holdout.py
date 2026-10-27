"""Write the irreversible EventX v4 holdout-consumption receipt."""

from __future__ import annotations

from datetime import datetime, timezone
import json
import os
from pathlib import Path
from typing import Any

from eventx.settings import REPO_ROOT
from eventx.tasks.prepare_v3_1_historical_development_arrays import sha256_file


PROTOCOL_ID = "eventx-v4-confirmatory-polymarket-20260902"
PROTOCOL = REPO_ROOT / "eventx/release/v4/protocol.json"
PREREGISTRATION = REPO_ROOT / "eventx/release/v4/preregistration_manifest.json"
COHORT = REPO_ROOT / "data/v4/confirmatory/cohort_gate/cohort.jsonl"
COLLECTION_GATE = REPO_ROOT / "data/v4/confirmatory/collection_gate/manifest.json"
MODEL_FREEZE = REPO_ROOT / "eventx/release/v4/model_freeze_manifest.json"
MODELS = REPO_ROOT / "data/v4/discovery/models/frozen_models.json"
IMPLEMENTATION = REPO_ROOT / "eventx/release/v4/holdout_implementation_manifest.json"
RECEIPT = REPO_ROOT / "data/v4/confirmatory/consumption_receipt.json"
FORBIDDEN = (
    REPO_ROOT / "data/v4/confirmatory/examples/examples.bin",
    REPO_ROOT / "data/v4/confirmatory/evaluation/result.json",
    REPO_ROOT / "data/v4/confirmatory/evaluation/predictions.bin",
    REPO_ROOT / "data/v4/confirmatory/evaluation/evaluation_attempt_receipt.json",
)


def relative(path: Path) -> str:
    return str(path.relative_to(REPO_ROOT))


def atomic_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n")
    os.replace(temporary, path)


def verify_manifest(path: Path, required_status: str | None = None) -> dict[str, Any]:
    manifest = json.loads(path.read_text(encoding="utf-8"))
    if required_status is not None and manifest.get("status") != required_status:
        raise RuntimeError(f"unexpected status for {path}: {manifest.get('status')}")
    for artifact in manifest.get("artifacts", []):
        target = REPO_ROOT / str(artifact["path"])
        if not target.is_file() or sha256_file(target) != str(artifact["sha256"]):
            raise RuntimeError(f"hash-lock failure: {target}")
    return manifest


def main() -> None:
    if RECEIPT.exists():
        raise SystemExit("v4 confirmatory holdout was already consumed")
    existing = [relative(path) for path in FORBIDDEN if path.exists()]
    if existing:
        raise SystemExit(f"refusing late receipt; downstream artifacts already exist: {existing}")
    protocol = json.loads(PROTOCOL.read_text(encoding="utf-8"))
    if protocol.get("protocol_id") != PROTOCOL_ID:
        raise SystemExit("wrong v4 protocol")
    verify_manifest(PREREGISTRATION)
    verify_manifest(COLLECTION_GATE, "passed")
    model_freeze = json.loads(MODEL_FREEZE.read_text(encoding="utf-8"))
    if model_freeze.get("status") != "all_confirmatory_models_frozen_before_2026-09-06_holdout":
        raise SystemExit("confirmatory models were not correctly frozen")
    implementation = verify_manifest(IMPLEMENTATION, "frozen_before_future_holdout")
    frozen = json.loads(MODELS.read_text(encoding="utf-8"))
    if frozen.get("model_bundle_sha256") != model_freeze.get("model_bundle_internal_sha256"):
        raise RuntimeError("model bundle internal hash mismatch")
    inputs = (PROTOCOL, PREREGISTRATION, COHORT, COLLECTION_GATE, MODEL_FREEZE, MODELS, IMPLEMENTATION)
    receipt = {
        "protocol_id": PROTOCOL_ID,
        "consumed_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "status": "future_holdout_irreversibly_consumed_before_label_summary",
        "evaluation_budget": 1,
        "evaluation_attempts_before_receipt": 0,
        "labels_prevalence_predictions_or_metrics_inspected_before_receipt": False,
        "implementation_status": implementation["status"],
        "inputs": [
            {"path": relative(path), "sha256": sha256_file(path)} for path in inputs
        ],
    }
    atomic_json(RECEIPT, receipt)
    print(json.dumps(receipt, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
