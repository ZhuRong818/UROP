"""Verify the completed v3.1 artifact chain without rerunning any evaluator."""

from __future__ import annotations

from datetime import datetime, timezone
import json
import os
from pathlib import Path
from typing import Any

from eventx.settings import REPO_ROOT
from eventx.tasks.prepare_v3_1_historical_development_arrays import sha256_file


RELEASE = REPO_ROOT / "eventx/release/v3_1_historical_primary"
DATA = REPO_ROOT / "data/v3_1_historical/primary"
REPORT = DATA / "completion_verification.json"


def relative(path: Path) -> str:
    return str(path.relative_to(REPO_ROOT))


def verify_manifest(path: Path) -> int:
    value = json.loads(path.read_text(encoding="utf-8"))
    artifacts = value.get("artifacts", [])
    for artifact in artifacts:
        artifact_path = REPO_ROOT / str(artifact["path"])
        if not artifact_path.is_file() or sha256_file(artifact_path) != str(
            artifact["sha256"]
        ):
            raise RuntimeError(f"hash-lock failure: {artifact_path}")
    return len(artifacts)


def atomic_json(path: Path, value: Any) -> None:
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n")
    os.replace(temporary, path)


def main() -> None:
    manifests = (
        RELEASE / "preregistration_manifest.json",
        RELEASE / "implementation_manifest.json",
        RELEASE / "candidate_manifest.json",
        RELEASE / "holdout_receipt_amendment_manifest.json",
        DATA / "development/examples_manifest.json",
        DATA / "holdout/trade_data_gate_manifest.json",
        DATA / "holdout/examples_manifest.json",
        DATA / "holdout/evaluation_manifest.json",
    )
    counts = {relative(path): verify_manifest(path) for path in manifests}
    protocol = json.loads((RELEASE / "protocol.json").read_text(encoding="utf-8"))
    selection = json.loads(
        (DATA / "development/selection_result.json").read_text(encoding="utf-8")
    )
    candidate = json.loads((RELEASE / "candidate.json").read_text(encoding="utf-8"))
    receipt = json.loads(
        (DATA / "holdout/holdout_consumption_receipt.json").read_text(encoding="utf-8")
    )
    result = json.loads(
        (DATA / "holdout/evaluation_result.json").read_text(encoding="utf-8")
    )
    checks = {
        "protocol_id_consistent": len({
            protocol["protocol_id"],
            selection["protocol_id"],
            candidate["protocol_id"],
            receipt["protocol_id"],
            result["protocol_id"],
        }) == 1,
        "all_development_promotion_gates_failed": not any(
            selection["promotion_gates"].values()
        ),
        "development_selected_b0": selection["selected_candidate"] == "b0",
        "exactly_one_b0_candidate_frozen": candidate["candidate"] == "b0",
        "candidate_precedes_holdout_consumption": candidate["frozen_at"]
        < receipt["consumed_at"],
        "holdout_reruns_prohibited": receipt["reruns_permitted"] is False,
        "pre_receipt_label_summary_disclosed": receipt.get(
            "pre_receipt_label_summary_read"
        ) is True,
        "no_performance_metric_preceded_receipt": receipt.get(
            "predictions_or_performance_metrics_read_before_receipt"
        ) is False,
        "one_shot_result_complete": result["status"]
        == "one_shot_historical_holdout_complete_with_disclosed_deviation",
        "holdout_evaluated_b0_only": result["candidate"] == "b0"
        and result["news_incremental_model_evaluated_on_holdout"] is False,
        "result_rows_match_receipt": result["rows"]
        == receipt["holdout_examples"]["rows"],
    }
    passed = all(checks.values())
    report = {
        "protocol_id": protocol["protocol_id"],
        "verified_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "status": "complete_verified_reruns_prohibited" if passed else "failed",
        "integrity_pass": passed,
        "manifests": counts,
        "checks": checks,
        "development_selected_candidate": selection["selected_candidate"],
        "holdout_result_status": result["status"],
        "verifier": {
            "path": relative(Path(__file__).resolve()),
            "sha256": sha256_file(Path(__file__).resolve()),
        },
    }
    atomic_json(REPORT, report)
    if not passed:
        raise SystemExit(json.dumps(report, indent=2, sort_keys=True))
    print(json.dumps(report, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
