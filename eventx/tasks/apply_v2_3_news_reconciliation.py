"""Persist verified EventX news reconciliation closures without reading labels."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import sqlite3
from typing import Any

from eventx.settings import REPO_ROOT


DEFAULT_DATABASE = (
    REPO_ROOT / "data/v2_3_1/prospective_news/state/news_collector.sqlite3"
)
DEFAULT_OUTPUT = (
    REPO_ROOT
    / "data/v2_3_1/continuity/reconciliation_application_20260901.json"
)


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def resolve(path_text: str) -> Path:
    path = Path(path_text)
    return path if path.is_absolute() else REPO_ROOT / path


def parse_utc(value: Any) -> datetime:
    parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        raise ValueError(f"timestamp must include timezone: {value!r}")
    return parsed.astimezone(timezone.utc)


def relative(path: Path) -> str:
    try:
        return str(path.resolve().relative_to(REPO_ROOT))
    except ValueError:
        return str(path.resolve())


def atomic_json(path: Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(
        json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    temporary.replace(path)


def validate_reconciliation(item: dict[str, Any]) -> tuple[Path, dict[str, Any]]:
    manifest_path = resolve(str(item["reconciled_by"]))
    if sha256_file(manifest_path) != item["reconciliation_sha256"]:
        raise RuntimeError(f"reconciliation hash mismatch: {manifest_path}")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if manifest.get("integrity_pass") is not True:
        raise RuntimeError(f"reconciliation integrity did not pass: {manifest_path}")
    window = manifest.get("warehouse_window") or {}
    coverage_start = parse_utc(window["start_inclusive"])
    coverage_end = parse_utc(window["end_exclusive"])
    interval_start = parse_utc(item["start_at"])
    interval_end = parse_utc(item["end_at"])
    if coverage_start > interval_start or coverage_end < interval_end:
        raise RuntimeError(f"reconciliation does not cover interval: {item['interval_id']}")
    return manifest_path, manifest


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--continuity-report", type=Path, required=True)
    parser.add_argument("--database", type=Path, default=DEFAULT_DATABASE)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()

    report = json.loads(args.continuity_report.read_text(encoding="utf-8"))
    if report.get("label_blind") is not True or report.get("labels_read") != []:
        raise SystemExit("continuity report does not preserve the label seal")
    items = report.get("prelaunch_reconciled_intervals") or []
    validated: list[tuple[dict[str, Any], Path, dict[str, Any]]] = []
    for item in items:
        manifest_path, manifest = validate_reconciliation(item)
        validated.append((item, manifest_path, manifest))

    applied_at = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
    newly_reconciled = 0
    already_reconciled = 0
    with sqlite3.connect(args.database, timeout=30) as connection:
        connection.execute("BEGIN IMMEDIATE")
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS censoring_reconciliations (
                interval_id TEXT PRIMARY KEY,
                reconciled_at TEXT NOT NULL,
                continuity_report_path TEXT NOT NULL,
                continuity_report_sha256 TEXT NOT NULL,
                warehouse_manifest_path TEXT NOT NULL,
                warehouse_manifest_sha256 TEXT NOT NULL,
                evidence_json TEXT NOT NULL
            )
            """
        )
        for item, manifest_path, _manifest in validated:
            observed = connection.execute(
                """
                SELECT start_at, end_at, reason, status
                FROM censoring_intervals
                WHERE interval_id = ?
                """,
                (item["interval_id"],),
            ).fetchone()
            expected = (item["start_at"], item["end_at"], item["reason"])
            if observed is None or observed[:3] != expected:
                raise RuntimeError(
                    f"collector interval mismatch for {item['interval_id']}"
                )
            already_reconciled += int(observed[3] == "reconciled")
            newly_reconciled += int(observed[3] != "reconciled")
            connection.execute(
                """
                INSERT OR IGNORE INTO censoring_reconciliations(
                    interval_id, reconciled_at, continuity_report_path,
                    continuity_report_sha256, warehouse_manifest_path,
                    warehouse_manifest_sha256, evidence_json
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    item["interval_id"],
                    applied_at,
                    relative(args.continuity_report),
                    sha256_file(args.continuity_report),
                    relative(manifest_path),
                    sha256_file(manifest_path),
                    json.dumps(item, sort_keys=True),
                ),
            )
            connection.execute(
                "UPDATE censoring_intervals SET status = 'reconciled' "
                "WHERE interval_id = ?",
                (item["interval_id"],),
            )
        connection.commit()

    receipt = {
        "already_reconciled": already_reconciled,
        "applied_at": applied_at,
        "continuity_report": relative(args.continuity_report),
        "continuity_report_sha256": sha256_file(args.continuity_report),
        "database": relative(args.database),
        "label_blind": True,
        "labels_read": [],
        "newly_reconciled": newly_reconciled,
        "reconciled_intervals": len(validated),
        "status": "applied",
    }
    atomic_json(args.output, receipt)
    print(json.dumps(receipt, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
