"""Hash-freeze the complete EventX v4 holdout implementation before Sep 6."""

from __future__ import annotations

from datetime import datetime, timezone
import json
import os
from pathlib import Path
from typing import Any

from eventx.settings import REPO_ROOT
from eventx.tasks.prepare_v3_1_historical_development_arrays import sha256_file


OUTPUT = REPO_ROOT / "eventx/release/v4/holdout_implementation_manifest.json"
FILES = (
    REPO_ROOT / "eventx/features/v4_news.py",
    REPO_ROOT / "eventx/tasks/audit_v4_confirmatory_collection.py",
    REPO_ROOT / "eventx/tasks/consume_v4_confirmatory_holdout.py",
    REPO_ROOT / "eventx/tasks/prepare_v4_confirmatory_inputs.py",
    REPO_ROOT / "eventx/tasks/build_v4_confirmatory_examples.py",
    REPO_ROOT / "eventx/tasks/evaluate_v4_confirmatory.py",
    REPO_ROOT / "eventx/tasks/test_v4_news_features.py",
    REPO_ROOT / "eventx/tasks/test_v4_confirmatory_pipeline.py",
    REPO_ROOT / "eventx/tasks/build_v3_1_historical_development_examples.py",
    REPO_ROOT / "eventx/tasks/build_v4_discovery_examples.py",
    REPO_ROOT / "eventx/tasks/run_v4_discovery_models.py",
    REPO_ROOT / "data/v4/discovery/prepared/semantic_model.joblib",
    REPO_ROOT / "data/v4/discovery/models/frozen_models.json",
    REPO_ROOT / "eventx/release/v4/protocol.json",
    REPO_ROOT / "eventx/release/v4/model_freeze_manifest.json",
)


def relative(path: Path) -> str:
    return str(path.relative_to(REPO_ROOT))


def atomic_json(path: Path, value: Any) -> None:
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n")
    os.replace(temporary, path)


def main() -> None:
    if OUTPUT.exists():
        raise SystemExit("v4 holdout implementation is already frozen")
    missing = [relative(path) for path in FILES if not path.is_file()]
    if missing:
        raise SystemExit(f"cannot freeze missing implementation inputs: {missing}")
    manifest = {
        "protocol_id": "eventx-v4-confirmatory-polymarket-20260902",
        "created_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "status": "frozen_before_future_holdout",
        "future_holdout_start": "2026-09-06T00:00:00Z",
        "future_prices_labels_predictions_or_metrics_inspected": False,
        "execution_order": [
            "continuous sealed collection",
            "audit_v4_confirmatory_collection",
            "consume_v4_confirmatory_holdout",
            "prepare_v4_confirmatory_inputs",
            "build_v4_confirmatory_examples",
            "evaluate_v4_confirmatory",
        ],
        "artifacts": [{"path": relative(path), "sha256": sha256_file(path)} for path in FILES],
    }
    atomic_json(OUTPUT, manifest)
    print(json.dumps(manifest, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
