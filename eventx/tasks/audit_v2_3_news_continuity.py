"""Audit EventX v2.3 news request continuity without reading outcome labels."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
from typing import Any

from eventx.settings import REPO_ROOT


DEFAULT_ROOT = REPO_ROOT / "data" / "v2_3_1" / "prospective_news"
DEFAULT_OUTPUT = (
    REPO_ROOT / "data" / "v2_3_1" / "continuity" / "gap_audit_20260827.json"
)


def parse_utc(value: Any) -> datetime | None:
    if value in (None, ""):
        return None
    try:
        parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except (TypeError, ValueError):
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    with path.open() as handle:
        for line_number, line in enumerate(handle, start=1):
            if not line.strip():
                continue
            value = json.loads(line)
            if not isinstance(value, dict):
                raise ValueError(f"{path}:{line_number} is not an object")
            rows.append(value)
    return rows


def relative(path: Path) -> str:
    try:
        return str(path.resolve().relative_to(REPO_ROOT))
    except ValueError:
        return str(path.resolve())


def audit(
    root: Path,
    *,
    max_gap_seconds: float,
    cap_rows: int,
    warehouse_reconciliation_manifests: list[Path] | None = None,
) -> dict[str, Any]:
    requests_path = root / "raw" / "news_requests.jsonl"
    health_path = root / "health.json"
    rows = read_jsonl(requests_path)
    health = json.loads(health_path.read_text())
    successes = sorted(
        (
            row
            for row in rows
            if row.get("status") == "success" and parse_utc(row.get("completed_at"))
        ),
        key=lambda row: parse_utc(row["completed_at"]) or datetime.min.replace(
            tzinfo=timezone.utc
        ),
    )
    failures = [row for row in rows if row.get("status") != "success"]
    warehouse_reconciliations: list[dict[str, Any]] = []
    for manifest_path in warehouse_reconciliation_manifests or []:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        coverage = manifest.get("warehouse_window") or {}
        warehouse_reconciliations.append(
            {
                "coverage_end": parse_utc(coverage.get("end_exclusive")),
                "coverage_start": parse_utc(coverage.get("start_inclusive")),
                "integrity_pass": manifest.get("integrity_pass") is True,
                "manifest": manifest_path,
                "warehouse_window": coverage,
            }
        )

    def covering_reconciliation(
        interval_start: datetime | None, interval_end: datetime | None
    ) -> dict[str, Any] | None:
        if interval_start is None or interval_end is None:
            return None
        for candidate in warehouse_reconciliations:
            coverage_start = candidate["coverage_start"]
            coverage_end = candidate["coverage_end"]
            if (
                candidate["integrity_pass"]
                and coverage_start is not None
                and coverage_end is not None
                and coverage_start <= interval_start
                and coverage_end >= interval_end
            ):
                return candidate
        return None

    gaps: list[dict[str, Any]] = []
    for previous, recovery in zip(successes, successes[1:]):
        previous_completed = parse_utc(previous.get("completed_at"))
        recovery_completed = parse_utc(recovery.get("completed_at"))
        assert previous_completed is not None and recovery_completed is not None
        gap_seconds = (recovery_completed - previous_completed).total_seconds()
        if gap_seconds <= max_gap_seconds:
            continue
        requested_since = parse_utc((recovery.get("params") or {}).get("since"))
        response_rows = recovery.get("response_rows")
        uncapped = isinstance(response_rows, int) and response_rows < cap_rows
        checkpoint_covers_gap = (
            requested_since is not None and requested_since <= previous_completed
        )
        errors_in_gap = [
            {
                "completed_at": row.get("completed_at"),
                "error": row.get("error"),
                "started_at": row.get("started_at"),
            }
            for row in failures
            if (
                (completed := parse_utc(row.get("completed_at"))) is not None
                and previous_completed < completed <= recovery_completed
            )
        ]
        gap = {
                "checkpoint_covers_gap_start": checkpoint_covers_gap,
                "errors_during_gap": errors_in_gap,
                "gap_seconds": gap_seconds,
                "recovered_by_uncapped_response": uncapped and checkpoint_covers_gap,
                "recovery_completed_at": recovery.get("completed_at"),
                "recovery_request_since": (recovery.get("params") or {}).get("since"),
                "recovery_response_rows": response_rows,
                "recovery_response_sha256": recovery.get("response_sha256"),
                "start_at": previous.get("completed_at"),
            }
        reconciliation = covering_reconciliation(
            previous_completed, recovery_completed
        )
        gap["recovered_by_warehouse"] = reconciliation is not None
        if reconciliation is not None:
            manifest_path = reconciliation["manifest"]
            gap["reconciled_by"] = relative(manifest_path)
            gap["reconciliation_sha256"] = sha256(manifest_path)
            gap["warehouse_window"] = reconciliation["warehouse_window"]
        gaps.append(gap)

    trailing_failures: list[dict[str, Any]] = []
    if successes:
        last_success = parse_utc(successes[-1].get("completed_at"))
        assert last_success is not None
        trailing_failures = [
            row
            for row in failures
            if (parse_utc(row.get("completed_at")) or last_success) > last_success
        ]
    operational_unresolved = [
        gap
        for gap in gaps
        if not gap["recovered_by_uncapped_response"]
        and not gap["recovered_by_warehouse"]
    ]
    if trailing_failures:
        operational_unresolved.append(
            {
                "reason": "failed_requests_after_last_success",
                "request_count": len(trailing_failures),
            }
        )
    prelaunch = health.get("unresolved_censoring_intervals") or []
    prelaunch_reconciled: list[dict[str, Any]] = []
    prelaunch_unresolved: list[dict[str, Any]] = []
    for interval in prelaunch:
        interval_start = parse_utc(interval.get("start_at"))
        interval_end = parse_utc(interval.get("end_at"))
        reconciliation = covering_reconciliation(interval_start, interval_end)
        if reconciliation is not None:
            manifest_path = reconciliation["manifest"]
            prelaunch_reconciled.append(
                {
                    **interval,
                    "reconciled_by": relative(manifest_path),
                    "reconciliation_sha256": sha256(manifest_path),
                    "warehouse_window": reconciliation["warehouse_window"],
                }
            )
        else:
            prelaunch_unresolved.append(interval)
    input_hashes = {
        "health": {
            "path": relative(health_path),
            "sha256": sha256(health_path),
        },
        "request_ledger": {
            "path": relative(requests_path),
            "sha256": sha256(requests_path),
        },
    }
    input_hashes["warehouse_reconciliations"] = [
        {"path": relative(path), "sha256": sha256(path)}
        for path in warehouse_reconciliation_manifests or []
    ]
    return {
        "audited_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "contract_id": health.get("contract_id"),
        "gap_rule_seconds": max_gap_seconds,
        "input_hashes": input_hashes,
        "label_blind": True,
        "labels_read": [],
        "operational_gap_windows": gaps,
        "prelaunch_reconciled_intervals": prelaunch_reconciled,
        "prelaunch_unresolved_intervals": prelaunch_unresolved,
        "protocol_id": health.get("protocol_id"),
        "status": (
            "incomplete_prelaunch_reconciliation_required"
            if prelaunch_unresolved and not operational_unresolved
            else "incomplete_operational_and_prelaunch_reconciliation_required"
            if prelaunch_unresolved
            else "operational_gaps_unresolved"
            if operational_unresolved
            else "continuity_reconciled_with_warehouse"
            if prelaunch_reconciled
            else "operational_continuity_reconciled"
        ),
        "summary": {
            "failed_requests": len(failures),
            "operational_gap_windows": len(gaps),
            "operational_gaps_recovered": len(gaps) - len(operational_unresolved),
            "operational_gaps_unresolved": len(operational_unresolved),
            "prelaunch_intervals_reconciled": len(prelaunch_reconciled),
            "prelaunch_intervals_unresolved": len(prelaunch_unresolved),
            "requests": len(rows),
            "successful_requests": len(successes),
        },
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=DEFAULT_ROOT)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--max-gap-seconds", type=float, default=300.0)
    parser.add_argument("--cap-rows", type=int, default=200)
    parser.add_argument(
        "--warehouse-reconciliation-manifest",
        type=Path,
        action="append",
        default=[],
    )
    args = parser.parse_args()
    result = audit(
        args.root,
        max_gap_seconds=args.max_gap_seconds,
        cap_rows=args.cap_rows,
        warehouse_reconciliation_manifests=args.warehouse_reconciliation_manifest,
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    temporary = args.output.with_suffix(args.output.suffix + ".tmp")
    temporary.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
    temporary.replace(args.output)
    print(json.dumps({"output": relative(args.output), **result["summary"], "status": result["status"]}, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
