"""Verify the v4 holdout implementation freeze without reading future outcomes."""

from __future__ import annotations

from datetime import datetime, timezone
import json
import os
from pathlib import Path
from typing import Any

from eventx.settings import REPO_ROOT
from eventx.tasks.prepare_v3_1_historical_development_arrays import sha256_file


MANIFEST = REPO_ROOT / "eventx/release/v4/holdout_implementation_manifest.json"
REPORT = REPO_ROOT / "data/v4/confirmatory/pre_holdout_implementation_verification.json"
FORBIDDEN = (
    REPO_ROOT / "data/v4/confirmatory/collection_gate/report.json",
    REPO_ROOT / "data/v4/confirmatory/consumption_receipt.json",
    REPO_ROOT / "data/v4/confirmatory/examples/examples.bin",
    REPO_ROOT / "data/v4/confirmatory/evaluation/evaluation_attempt_receipt.json",
    REPO_ROOT / "data/v4/confirmatory/evaluation/result.json",
)


def atomic_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n")
    os.replace(temporary, path)


def main() -> None:
    if REPORT.exists():
        raise SystemExit("v4 implementation verification already exists")
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    failures = []
    for artifact in manifest["artifacts"]:
        path = REPO_ROOT / str(artifact["path"])
        if not path.is_file():
            failures.append(f"missing:{artifact['path']}")
        elif sha256_file(path) != str(artifact["sha256"]):
            failures.append(f"hash_mismatch:{artifact['path']}")
    checks = {
        "manifest_status_frozen": manifest.get("status") == "frozen_before_future_holdout",
        "verified_before_holdout": datetime.now(timezone.utc) < datetime(2026, 9, 6, tzinfo=timezone.utc),
        "all_frozen_hashes_match": not failures,
        "collection_gate_not_prematurely_run": not FORBIDDEN[0].exists(),
        "consumption_receipt_absent": not FORBIDDEN[1].exists(),
        "confirmatory_examples_absent": not FORBIDDEN[2].exists(),
        "evaluation_attempt_absent": not FORBIDDEN[3].exists(),
        "confirmatory_result_absent": not FORBIDDEN[4].exists(),
        "future_prices_labels_predictions_or_metrics_read": False,
    }
    passed = all(value is True for name, value in checks.items() if name != "future_prices_labels_predictions_or_metrics_read") and checks["future_prices_labels_predictions_or_metrics_read"] is False
    report = {
        "protocol_id": "eventx-v4-confirmatory-polymarket-20260902",
        "created_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "status": "passed" if passed else "failed",
        "checks": checks,
        "hash_failures": failures,
        "implementation_manifest": {
            "path": str(MANIFEST.relative_to(REPO_ROOT)),
            "sha256": sha256_file(MANIFEST),
        },
    }
    atomic_json(REPORT, report)
    print(json.dumps(report, indent=2, sort_keys=True))
    if not passed:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
