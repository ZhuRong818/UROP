"""Verify the label-blind EventX multi-snapshot news availability ledger."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
import tempfile
from typing import Any

from eventx.settings import REPO_ROOT
from eventx.tasks.merge_v2_3_news_availability import merge


MANIFEST = REPO_ROOT / "eventx/release/v2_3_3/implementation_manifest.json"


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def write_receipt(root: Path, name: str, rows: list[dict[str, Any]]) -> Path:
    directory = root / name
    index = directory / "availability_index.jsonl"
    directory.mkdir(parents=True, exist_ok=True)
    index.write_text(
        "".join(json.dumps(row, sort_keys=True) + "\n" for row in rows),
        encoding="utf-8",
    )
    manifest = directory / "reconciliation_manifest.json"
    write_json(
        manifest,
        {
            "artifacts": {
                "availability_index": {
                    "bytes": index.stat().st_size,
                    "path": str(index),
                    "sha256": sha256(index),
                }
            },
            "integrity_pass": True,
            "labels_or_outcomes_read": False,
        },
    )
    return manifest


def row(
    warehouse_id: int,
    url: str,
    published_at: str,
    first_seen_at: str,
) -> dict[str, Any]:
    published = published_at
    available = max(published_at, first_seen_at)
    return {
        "available_at": available,
        "eventx_first_seen_at": first_seen_at,
        "eventx_first_seen_endpoint": "/retrieve",
        "eventx_first_seen_source": "warehouse_export_completion",
        "normalized_url": url,
        "published_at": published,
        "quarantined_timestamp_conflict": False,
        "warehouse_id": warehouse_id,
        "warehouse_ingest_ts": first_seen_at,
        "warehouse_source": "synthetic",
        "warehouse_source_endpoint": "synthetic:test",
        "warehouse_source_run_id": name_for_id(warehouse_id),
    }


def name_for_id(value: int) -> str:
    return f"synthetic-{value}"


def check(condition: bool, name: str, failures: list[str]) -> None:
    if not condition:
        failures.append(name)


def main() -> None:
    failures: list[str] = []
    with tempfile.TemporaryDirectory(prefix="eventx-availability-merge-") as temporary:
        root = Path(temporary)
        first = write_receipt(
            root,
            "first",
            [
                row(1, "https://example.test/one", "2026-09-01T10:00:00Z", "2026-09-01T11:00:00Z"),
                row(2, "https://example.test/conflict", "2026-09-01T10:00:00Z", "2026-09-01T11:00:00Z"),
            ],
        )
        second = write_receipt(
            root,
            "second",
            [
                row(1, "https://example.test/one", "2026-09-01T10:00:00Z", "2026-09-01T12:00:00Z"),
                row(3, "https://example.test/conflict", "2026-09-01T10:05:00Z", "2026-09-01T12:00:00Z"),
            ],
        )
        report = merge([first, second], root / "merged")
        output_rows = {
            str(value["warehouse_id"]): value
            for value in (
                json.loads(line)
                for line in (root / "merged/availability_index.jsonl")
                .read_text(encoding="utf-8")
                .splitlines()
                if line
            )
        }
        check(report["integrity_pass"] is True, "synthetic merge failed", failures)
        check(
            output_rows["1"]["eventx_first_seen_at"] == "2026-09-01T11:00:00Z",
            "earliest receipt was not preserved",
            failures,
        )
        check(
            output_rows["1"]["available_at"] == "2026-09-01T11:00:00Z",
            "availability rule was not recomputed",
            failures,
        )
        check(
            output_rows["1"]["availability_receipt_count"] == 2,
            "duplicate receipt count is wrong",
            failures,
        )
        check(
            output_rows["2"]["quarantined_timestamp_conflict"] is True
            and output_rows["3"]["quarantined_timestamp_conflict"] is True,
            "cross-snapshot timestamp conflict was not quarantined",
            failures,
        )
        check(
            report["summary"]["earlier_receipt_preserved_warehouse_ids"] == 1,
            "earlier-receipt audit count is wrong",
            failures,
        )
        index = first.parent / "availability_index.jsonl"
        index.write_text(index.read_text(encoding="utf-8") + "{}\n", encoding="utf-8")
        try:
            merge([first, second], root / "tampered")
        except ValueError:
            pass
        else:
            failures.append("tampered input hash was accepted")

    implementation = json.loads(MANIFEST.read_text(encoding="utf-8"))
    check(
        implementation.get("implementation_id")
        == "eventx-v2.3-news-availability-ledger-v1-20260902",
        "implementation ID mismatch",
        failures,
    )
    for name, artifact in implementation.get("artifacts", {}).items():
        path = REPO_ROOT / str(artifact.get("path", ""))
        check(path.is_file(), f"manifest artifact missing: {name}", failures)
        if path.is_file():
            check(path.stat().st_size == artifact.get("bytes"), f"byte mismatch: {name}", failures)
            check(sha256(path) == artifact.get("sha256"), f"hash mismatch: {name}", failures)
    print(
        json.dumps(
            {
                "checks": 8 + len(implementation.get("artifacts", {})) * 3,
                "failures": failures,
                "label_blind": True,
                "labels_or_outcomes_read": False,
                "status": "passed" if not failures else "failed",
            },
            indent=2,
            sort_keys=True,
        )
    )
    if failures:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
