"""Build a label-blind EventX v2 planning and ingestion coverage snapshot."""

from __future__ import annotations

import argparse
from collections import Counter
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
from typing import Any

from eventx.settings import REPO_ROOT


DEFAULT_PROTOCOL = REPO_ROOT / "eventx" / "release" / "v2_1" / "protocol.json"
DEFAULT_MANIFEST = (
    REPO_ROOT / "eventx" / "release" / "v2_1" / "preregistration_manifest.json"
)
DEFAULT_OUTPUT_DIR = REPO_ROOT / "data" / "v2_1" / "planning"
VENUE_INPUTS = {
    "polymarket": {
        "roster": REPO_ROOT / "data" / "v1" / "raw" / "instruments_polymarket.jsonl",
        "checkpoint": REPO_ROOT
        / "data"
        / "v1"
        / "checkpoints"
        / "trades_polymarket.json",
        "trades": REPO_ROOT / "data" / "v1" / "raw" / "trades_polymarket.jsonl",
    },
    "kalshi": {
        "roster": REPO_ROOT / "data" / "v1" / "raw" / "instruments_kalshi.jsonl",
        "checkpoint": REPO_ROOT
        / "data"
        / "v1"
        / "checkpoints"
        / "trades_kalshi.json",
        "trades": REPO_ROOT / "data" / "v1" / "raw" / "trades_kalshi.jsonl",
    },
}


def load_object(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text())
    if not isinstance(value, dict):
        raise ValueError(f"{path} must contain a JSON object")
    return value


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def relative(path: Path) -> str:
    return str(path.resolve().relative_to(REPO_ROOT.resolve()))


def utc_timestamp(value: float) -> str:
    return datetime.fromtimestamp(value, timezone.utc).isoformat().replace("+00:00", "Z")


def parse_utc(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def distinct_roster_ids(path: Path, venue: str) -> set[str]:
    identifiers: set[str] = set()
    if not path.exists():
        return identifiers
    with path.open() as handle:
        for line_number, line in enumerate(handle, start=1):
            if not line.strip():
                continue
            row = json.loads(line)
            if row.get("venue") not in (None, venue):
                raise ValueError(
                    f"{path}:{line_number} has venue {row.get('venue')!r}, expected {venue!r}"
                )
            market_id = row.get("market_id")
            if market_id:
                identifiers.add(str(market_id))
    return identifiers


def file_state(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {"exists": False, "path": relative(path)}
    stat = path.stat()
    return {
        "bytes": stat.st_size,
        "exists": True,
        "modified_at": utc_timestamp(stat.st_mtime),
        "path": relative(path),
    }


def preregistration_state(manifest_path: Path) -> dict[str, Any]:
    manifest = load_object(manifest_path)
    failures: list[str] = []
    if manifest.get("locked") is not True:
        failures.append("manifest is not locked")
    if manifest.get("status") != "preregistered_labels_uninspected":
        failures.append("unexpected manifest status")
    for name, specification in manifest.get("artifacts", {}).items():
        path = REPO_ROOT / specification["path"]
        if not path.is_file():
            failures.append(f"{name}: missing")
            continue
        if path.stat().st_size != specification.get("bytes"):
            failures.append(f"{name}: byte mismatch")
        if sha256_file(path) != specification.get("sha256"):
            failures.append(f"{name}: hash mismatch")
    return {
        "failures": failures,
        "manifest_path": relative(manifest_path),
        "manifest_sha256": sha256_file(manifest_path),
        "status": "verified" if not failures else "failed",
    }


def checkpoint_state(
    checkpoint_path: Path,
    roster_ids: set[str],
    trades_path: Path,
) -> dict[str, Any]:
    checkpoint_file = file_state(checkpoint_path)
    raw_file = file_state(trades_path)
    if not checkpoint_path.exists():
        return {
            "checkpoint": checkpoint_file,
            "completed_roster_markets": 0,
            "completion_fraction": 0.0 if roster_ids else None,
            "done_keys": 0,
            "nonzero_keys": 0,
            "raw_trades": raw_file,
            "rows_reported": 0,
            "status_counts": {},
        }

    checkpoint = load_object(checkpoint_path)
    statuses = Counter(
        str(value.get("status", "missing"))
        for value in checkpoint.values()
        if isinstance(value, dict)
    )
    done_ids = {
        str(key)
        for key, value in checkpoint.items()
        if isinstance(value, dict) and value.get("status") == "done"
    }
    rows = sum(
        int(value.get("n_rows", 0) or 0)
        for value in checkpoint.values()
        if isinstance(value, dict)
    )
    nonzero = sum(
        1
        for value in checkpoint.values()
        if isinstance(value, dict) and int(value.get("n_rows", 0) or 0) > 0
    )
    completed_roster = len(done_ids & roster_ids)
    return {
        "checkpoint": checkpoint_file,
        "completed_roster_markets": completed_roster,
        "completion_fraction": (
            completed_roster / len(roster_ids) if roster_ids else None
        ),
        "done_keys": len(done_ids),
        "extra_done_keys_not_in_roster": len(done_ids - roster_ids),
        "nonzero_keys": nonzero,
        "raw_trades": raw_file,
        "rows_reported": rows,
        "status_counts": dict(sorted(statuses.items())),
    }


def window_state(now: datetime, start: datetime, end: datetime) -> str:
    if now < start:
        return "not_started"
    if now < end:
        return "open"
    return "closed"


def render_markdown(snapshot: dict[str, Any]) -> str:
    lines = [
        "# EventX v2 label-blind coverage snapshot",
        "",
        f"- Generated: `{snapshot['generated_at']}`",
        f"- Protocol: `{snapshot['protocol_id']}`",
        f"- Preregistration: `{snapshot['preregistration']['status']}`",
        f"- Overall readiness: `{snapshot['readiness']['status']}`",
        "- Labels read: `false`",
        "",
        "## Windows",
        "",
        "| Window | State | Start | End (exclusive) |",
        "|---|---:|---:|---:|",
    ]
    for name, window in snapshot["windows"].items():
        lines.append(
            f"| {name} | {window['state']} | {window['start']} | "
            f"{window['end_exclusive']} |"
        )
    lines.extend(
        [
            "",
            "## Archival bulk trade coverage",
            "",
            "| Venue | Roster markets | Completed | Coverage | Rows | Nonzero markets |",
            "|---|---:|---:|---:|---:|---:|",
        ]
    )
    for venue, state in snapshot["venues"].items():
        fraction = state["trade_fetch"]["completion_fraction"]
        percentage = "n/a" if fraction is None else f"{100 * fraction:.2f}%"
        lines.append(
            f"| {venue} | {state['roster_distinct_markets']:,} | "
            f"{state['trade_fetch']['completed_roster_markets']:,} | {percentage} | "
            f"{state['trade_fetch']['rows_reported']:,} | "
            f"{state['trade_fetch']['nonzero_keys']:,} |"
        )
    lines.extend(
        [
            "",
            "## Guardrails",
            "",
            "- This report reads only the frozen v2 protocol/manifest, instrument rosters, "
            "trade checkpoints, and file metadata.",
            "- It does not open label, feature, prediction, metric, or result files.",
            "- Archival bulk completion is operational context; the prospective selection "
            "window still governs the v2 cohort.",
            "",
        ]
    )
    return "\n".join(lines)


def atomic_write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(content)
    temporary.replace(path)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--protocol", type=Path, default=DEFAULT_PROTOCOL)
    parser.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument(
        "--as-of",
        help="UTC RFC3339 time for deterministic testing; defaults to the current time",
    )
    args = parser.parse_args()

    protocol = load_object(args.protocol)
    now = parse_utc(args.as_of) if args.as_of else datetime.now(timezone.utc)
    windows: dict[str, Any] = {}
    for name, specification in protocol["windows"].items():
        start = parse_utc(specification["start"])
        end = parse_utc(specification["end_exclusive"])
        windows[name] = {
            "end_exclusive": specification["end_exclusive"],
            "start": specification["start"],
            "state": window_state(now, start, end),
        }

    venues: dict[str, Any] = {}
    bulk_complete = True
    for venue, paths in VENUE_INPUTS.items():
        roster_ids = distinct_roster_ids(paths["roster"], venue)
        trade_fetch = checkpoint_state(paths["checkpoint"], roster_ids, paths["trades"])
        completion = trade_fetch["completion_fraction"]
        if completion is None or completion < 1.0:
            bulk_complete = False
        venues[venue] = {
            "roster": file_state(paths["roster"]),
            "roster_distinct_markets": len(roster_ids),
            "trade_fetch": trade_fetch,
        }

    preregistration = preregistration_state(args.manifest)
    selection_state = windows["selection"]["state"]
    if preregistration["status"] != "verified":
        readiness_status = "blocked_preregistration_verification_failed"
    elif selection_state == "not_started" and not bulk_complete:
        readiness_status = "planning_fetch_incomplete_selection_not_started"
    elif selection_state == "not_started":
        readiness_status = "planning_selection_not_started"
    elif not bulk_complete:
        readiness_status = "selection_open_archival_fetch_incomplete"
    else:
        readiness_status = "selection_collection_ready"

    snapshot = {
        "generated_at": now.isoformat().replace("+00:00", "Z"),
        "input_allowlist": [
            relative(args.protocol),
            relative(args.manifest),
            *[
                relative(path)
                for paths in VENUE_INPUTS.values()
                for path in (paths["roster"], paths["checkpoint"], paths["trades"])
            ],
        ],
        "label_blind": {
            "feature_paths_read": [],
            "label_paths_read": [],
            "metric_paths_read": [],
            "prediction_paths_read": [],
            "result_paths_read": [],
            "value": True,
        },
        "preregistration": preregistration,
        "protocol_id": protocol["protocol_id"],
        "protocol_path": relative(args.protocol),
        "protocol_sha256": sha256_file(args.protocol),
        "readiness": {
            "archival_bulk_trade_fetch_complete": bulk_complete,
            "selection_window_state": selection_state,
            "status": readiness_status,
        },
        "snapshot_schema": 1,
        "venues": venues,
        "windows": windows,
    }
    output_dir = args.output_dir
    atomic_write(
        output_dir / "coverage_snapshot.json",
        json.dumps(snapshot, indent=2, sort_keys=True) + "\n",
    )
    atomic_write(output_dir / "coverage_snapshot.md", render_markdown(snapshot))
    print(json.dumps(snapshot["readiness"], indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
