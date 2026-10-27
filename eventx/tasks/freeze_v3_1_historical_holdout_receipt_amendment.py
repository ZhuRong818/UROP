"""Freeze the truthfulness-only receipt amendment before holdout performance scoring."""

from __future__ import annotations

from datetime import datetime, timezone
import json
import os
from pathlib import Path
from typing import Any

from eventx.settings import REPO_ROOT
from eventx.tasks.prepare_v3_1_historical_development_arrays import sha256_file
from eventx.tasks.test_v3_1_historical_holdout import main as test_holdout


RELEASE = REPO_ROOT / "eventx/release/v3_1_historical_primary"
HOLDOUT = REPO_ROOT / "data/v3_1_historical/primary/holdout"
ORIGINAL = RELEASE / "holdout_implementation_manifest.json"
AMENDMENT = RELEASE / "holdout_receipt_amendment_manifest.json"
EVALUATOR = REPO_ROOT / "eventx/tasks/evaluate_v3_1_historical_holdout.py"
ORIGINAL_EVALUATOR_SHA256 = (
    "e3bbde92a596e4874e425fa19ccca3ebc974b12f48f1e6677d7c8601908ff14c"
)


def relative(path: Path) -> str:
    return str(path.relative_to(REPO_ROOT))


def atomic_json(path: Path, value: Any) -> None:
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n")
    os.replace(temporary, path)


def main() -> None:
    if AMENDMENT.exists():
        raise SystemExit("holdout receipt amendment already frozen")
    if (HOLDOUT / "holdout_consumption_receipt.json").exists() or (
        HOLDOUT / "evaluation_result.json"
    ).exists():
        raise SystemExit("performance evaluation already started")
    original = json.loads(ORIGINAL.read_text(encoding="utf-8"))
    recorded = {
        str(item["path"]): str(item["sha256"])
        for item in original.get("artifacts", [])
    }
    evaluator_path = relative(EVALUATOR)
    if recorded.get(evaluator_path) != ORIGINAL_EVALUATOR_SHA256:
        raise RuntimeError("unexpected original evaluator hash")
    for path_text, expected in recorded.items():
        if path_text == evaluator_path:
            continue
        path = REPO_ROOT / path_text
        if not path.is_file() or sha256_file(path) != expected:
            raise RuntimeError(f"original non-evaluator artifact changed: {path}")
    examples_report = json.loads(
        (HOLDOUT / "examples_report.json").read_text(encoding="utf-8")
    )
    if (
        examples_report.get("rows") != 211718
        or examples_report.get("positives") != 26381
    ):
        raise RuntimeError("unexpected disclosed label summary")
    test_holdout()
    artifacts = (
        ORIGINAL,
        RELEASE / "candidate.json",
        RELEASE / "candidate_manifest.json",
        RELEASE / "HOLDOUT_PROTOCOL_DEVIATION.md",
        RELEASE / "holdout_evaluation_config.json",
        HOLDOUT / "examples_manifest.json",
        EVALUATOR,
        REPO_ROOT / "eventx/tasks/test_v3_1_historical_holdout.py",
        Path(__file__).resolve(),
    )
    atomic_json(
        AMENDMENT,
        {
            "protocol_id": "eventx-v3.1-historical-primary-20260902",
            "frozen_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
            "status": "truthfulness_only_receipt_amendment_before_performance_scoring",
            "candidate_changed": False,
            "statistical_calculation_changed": False,
            "holdout_predictions_or_performance_metrics_read": False,
            "original_evaluator_sha256": ORIGINAL_EVALUATOR_SHA256,
            "amended_evaluator_sha256": sha256_file(EVALUATOR),
            "artifacts": [
                {"path": relative(path), "sha256": sha256_file(path)}
                for path in artifacts
            ],
        },
    )
    print(json.dumps({
        "status": "holdout_receipt_amendment_frozen",
        "candidate_changed": False,
        "statistical_calculation_changed": False,
        "holdout_predictions_or_performance_metrics_read": False,
    }, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
