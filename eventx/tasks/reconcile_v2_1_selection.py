"""Reconcile the closed EventX v2.1 selection window for every candidate market.

The job is restart-safe. It seeds a SQLite registry from the prospective extract,
then refetches the exact closed window from each venue's trade-history endpoint.
Canonical JSONL outputs are emitted only after every candidate endpoint completes.
"""

from __future__ import annotations

import argparse
from collections import Counter
from datetime import datetime, timedelta, timezone
import hashlib
import json
from pathlib import Path
import sqlite3
from typing import Any, Iterator

from eventx.ingest.client import FindataClient
from eventx.settings import REPO_ROOT
from eventx.tasks.build_v2_selection_activity import trade_identity


DEFAULT_PROTOCOL = REPO_ROOT / "eventx" / "release" / "v2_1" / "protocol.json"
DEFAULT_MARKETS = REPO_ROOT / "data" / "v2_1" / "taxonomy" / "market_categories.jsonl"
DEFAULT_PROSPECTIVE = REPO_ROOT / "data" / "v2_1" / "prospective"
DEFAULT_OUTPUT = REPO_ROOT / "data" / "v2_1" / "selection" / "reconciled"
TIMESTAMP_KEY = {"polymarket": "ts", "kalshi": "created_time"}


def parse_utc(value: str) -> datetime:
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def rfc3339(value: datetime) -> str:
    return value.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def read_jsonl(path: Path) -> Iterator[dict[str, Any]]:
    with path.open() as handle:
        for line_number, line in enumerate(handle, start=1):
            if not line.strip():
                continue
            value = json.loads(line)
            if not isinstance(value, dict):
                raise ValueError(f"{path}:{line_number} must be a JSON object")
            yield value


def load_object(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text())
    if not isinstance(value, dict):
        raise ValueError(f"{path} must contain a JSON object")
    return value


def response_rows(value: Any) -> list[dict[str, Any]]:
    if isinstance(value, list):
        return [row for row in value if isinstance(row, dict)]
    if isinstance(value, dict):
        for key in ("data", "trades", "results", "items"):
            rows = value.get(key)
            if isinstance(rows, list):
                return [row for row in rows if isinstance(row, dict)]
    return []


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def sha256_line_prefix(path: Path, line_count: int) -> tuple[str, int]:
    """Hash the exact append-only byte prefix consumed during prospective seeding."""
    digest = hashlib.sha256()
    bytes_read = 0
    with path.open("rb") as handle:
        for index in range(line_count):
            line = handle.readline()
            if not line:
                raise ValueError(
                    f"{path} now has fewer than the {line_count} seeded lines "
                    f"(stopped at {index})"
                )
            digest.update(line)
            bytes_read += len(line)
    return digest.hexdigest(), bytes_read


def stable_json(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), default=str)


def relative(path: Path) -> str:
    return str(path.resolve().relative_to(REPO_ROOT.resolve()))


def atomic_json(path: Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n")
    temporary.replace(path)


def atomic_jsonl(path: Path, rows: Iterator[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    with temporary.open("w") as handle:
        for row in rows:
            handle.write(json.dumps(row, sort_keys=True) + "\n")
    temporary.replace(path)


def init_database(path: Path) -> sqlite3.Connection:
    path.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(path)
    connection.execute("PRAGMA journal_mode=WAL")
    connection.execute("PRAGMA synchronous=FULL")
    connection.executescript(
        """
        CREATE TABLE IF NOT EXISTS meta (
            name TEXT PRIMARY KEY,
            value TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS market_status (
            venue TEXT NOT NULL,
            market_id TEXT NOT NULL,
            status TEXT NOT NULL DEFAULT 'pending',
            next_to TEXT,
            pages INTEGER NOT NULL DEFAULT 0,
            rows_seen INTEGER NOT NULL DEFAULT 0,
            new_records INTEGER NOT NULL DEFAULT 0,
            last_error TEXT,
            updated_at TEXT,
            PRIMARY KEY (venue, market_id)
        );
        CREATE TABLE IF NOT EXISTS records (
            record_key TEXT PRIMARY KEY,
            venue TEXT NOT NULL,
            market_id TEXT NOT NULL,
            event_ts TEXT NOT NULL,
            record_json TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS retrievals (
            record_key TEXT NOT NULL,
            source TEXT NOT NULL,
            retrieved_at TEXT NOT NULL,
            source_endpoint TEXT NOT NULL,
            PRIMARY KEY (record_key, source, retrieved_at),
            FOREIGN KEY (record_key) REFERENCES records(record_key)
        );
        """
    )
    connection.commit()
    return connection


def meta_get(connection: sqlite3.Connection, name: str) -> str | None:
    row = connection.execute("SELECT value FROM meta WHERE name = ?", (name,)).fetchone()
    return str(row[0]) if row else None


def meta_set(connection: sqlite3.Connection, name: str, value: str) -> None:
    connection.execute(
        "INSERT INTO meta(name, value) VALUES (?, ?) "
        "ON CONFLICT(name) DO UPDATE SET value = excluded.value",
        (name, value),
    )


def load_candidates(path: Path) -> list[tuple[str, str]]:
    candidates: list[tuple[str, str]] = []
    seen: set[tuple[str, str]] = set()
    for row in read_jsonl(path):
        if row.get("is_binary") is not True or row.get("canonical_side") is not True:
            continue
        key = (str(row.get("venue") or ""), str(row.get("market_id") or ""))
        if key[0] not in TIMESTAMP_KEY or not key[1] or key in seen:
            raise ValueError(f"invalid or duplicate candidate {key}")
        seen.add(key)
        candidates.append(key)
    return sorted(candidates)


def add_record(
    connection: sqlite3.Connection,
    *,
    venue: str,
    market_id: str,
    row: dict[str, Any],
    source: str,
    retrieved_at: str,
    endpoint: str,
    start: datetime,
    end: datetime,
) -> bool:
    timestamp_value = row.get(TIMESTAMP_KEY[venue])
    if timestamp_value in (None, ""):
        return False
    timestamp = parse_utc(str(timestamp_value))
    if not start <= timestamp < end:
        return False
    normalized = {**row, "market_id": market_id, "venue": venue}
    key = trade_identity(normalized, venue)
    inserted = connection.execute(
        "INSERT OR IGNORE INTO records(record_key, venue, market_id, event_ts, record_json) "
        "VALUES (?, ?, ?, ?, ?)",
        (key, venue, market_id, rfc3339(timestamp), stable_json(normalized)),
    ).rowcount
    connection.execute(
        "INSERT OR IGNORE INTO retrievals(record_key, source, retrieved_at, source_endpoint) "
        "VALUES (?, ?, ?, ?)",
        (key, source, retrieved_at, endpoint),
    )
    return bool(inserted)


def seed_prospective(
    connection: sqlite3.Connection,
    *,
    prospective_root: Path,
    protocol_id: str,
    candidates: set[tuple[str, str]],
    start: datetime,
    end: datetime,
) -> dict[str, Any]:
    existing = meta_get(connection, "prospective_seed_report")
    if existing is not None:
        return json.loads(existing)
    report: dict[str, Any] = {"files": {}, "inserted_records": 0, "rows_scanned": 0}
    for venue in TIMESTAMP_KEY:
        path = prospective_root / "raw" / f"trades_{venue}.jsonl"
        rows_scanned = 0
        inserted = 0
        for envelope in read_jsonl(path):
            rows_scanned += 1
            if envelope.get("_protocol_id") != protocol_id:
                raise ValueError(f"{path} contains a different protocol ID")
            row = envelope.get("record")
            if not isinstance(row, dict):
                continue
            market_id = str(row.get("market_id") or "")
            if (venue, market_id) not in candidates:
                continue
            inserted += int(
                add_record(
                    connection,
                    venue=venue,
                    market_id=market_id,
                    row=row,
                    source="prospective_incremental",
                    retrieved_at=str(envelope.get("_retrieved_at") or ""),
                    endpoint=str(envelope.get("_source_endpoint") or ""),
                    start=start,
                    end=end,
                )
            )
        report["rows_scanned"] += rows_scanned
        report["inserted_records"] += inserted
        report["files"][relative(path)] = {
            "bytes_at_seed": path.stat().st_size,
            "rows_scanned": rows_scanned,
            "selection_records_inserted": inserted,
        }
    meta_set(connection, "prospective_seed_report", stable_json(report))
    connection.commit()
    return report


def verify_collector_cursors(
    collector_db: Path,
    candidates: list[tuple[str, str]],
    end: datetime,
) -> dict[str, Any]:
    connection = sqlite3.connect(f"file:{collector_db}?mode=ro", uri=True)
    try:
        cursor_values = {
            str(name): str(value)
            for name, value in connection.execute(
                "SELECT name, value FROM checkpoints WHERE name LIKE 'trade_since:%'"
            )
        }
    finally:
        connection.close()
    cutoff = end - timedelta(minutes=5)
    missing: list[str] = []
    before_cutoff: list[str] = []
    for venue, market_id in candidates:
        name = f"trade_since:{venue}:{market_id}"
        value = cursor_values.get(name)
        if value is None:
            missing.append(f"{venue}:{market_id}")
        elif parse_utc(value) < cutoff:
            before_cutoff.append(f"{venue}:{market_id}")
    return {
        "at_or_after_cutoff": len(candidates) - len(missing) - len(before_cutoff),
        "before_cutoff": before_cutoff,
        "cutoff_required": rfc3339(cutoff),
        "missing": missing,
        "status": "complete" if not missing and not before_cutoff else "incomplete",
        "total_candidates": len(candidates),
    }


def fetch_market(
    connection: sqlite3.Connection,
    client: FindataClient,
    *,
    venue: str,
    market_id: str,
    start: datetime,
    end: datetime,
    page_limit: int,
    max_pages: int,
    protocol_id: str,
) -> None:
    status_row = connection.execute(
        "SELECT status, next_to, pages, rows_seen, new_records FROM market_status "
        "WHERE venue = ? AND market_id = ?",
        (venue, market_id),
    ).fetchone()
    if status_row is None:
        raise ValueError(f"missing market status for {venue}:{market_id}")
    if status_row[0] == "done":
        return
    page_to = parse_utc(status_row[1]) if status_row[1] else end
    pages = int(status_row[2])
    rows_seen = int(status_row[3])
    new_records = int(status_row[4])
    endpoint = f"/prediction-markets/trades/{venue}/{market_id}"
    previous_oldest: datetime | None = None
    connection.execute(
        "UPDATE market_status SET status = 'running', last_error = NULL, updated_at = ? "
        "WHERE venue = ? AND market_id = ?",
        (rfc3339(utc_now()), venue, market_id),
    )
    connection.commit()
    try:
        for _ in range(max_pages):
            retrieved_at = rfc3339(utc_now())
            response = client.get(
                endpoint,
                **{
                    "from": rfc3339(start),
                    "to": rfc3339(page_to),
                    "limit": page_limit,
                },
            )
            rows = response_rows(response)
            rows_seen += len(rows)
            timestamps: list[datetime] = []
            for raw in rows:
                value = raw.get(TIMESTAMP_KEY[venue])
                if value in (None, ""):
                    continue
                timestamp = parse_utc(str(value))
                timestamps.append(timestamp)
                new_records += int(
                    add_record(
                        connection,
                        venue=venue,
                        market_id=market_id,
                        row=raw,
                        source="bounded_history_reconciliation",
                        retrieved_at=retrieved_at,
                        endpoint=endpoint,
                        start=start,
                        end=end,
                    )
                )
            pages += 1
            complete = len(rows) < page_limit
            if not rows:
                complete = True
            elif not timestamps:
                raise ValueError("trade page contains no parseable timestamps")
            else:
                oldest = min(timestamps)
                if oldest <= start:
                    complete = True
                if previous_oldest is not None and oldest >= previous_oldest:
                    raise ValueError("backward pagination made no timestamp progress")
                previous_oldest = oldest
                page_to = oldest
            connection.execute(
                "UPDATE market_status SET next_to = ?, pages = ?, rows_seen = ?, "
                "new_records = ?, updated_at = ? WHERE venue = ? AND market_id = ?",
                (
                    rfc3339(page_to),
                    pages,
                    rows_seen,
                    new_records,
                    rfc3339(utc_now()),
                    venue,
                    market_id,
                ),
            )
            connection.commit()
            if complete:
                connection.execute(
                    "UPDATE market_status SET status = 'done', last_error = NULL, updated_at = ? "
                    "WHERE venue = ? AND market_id = ?",
                    (rfc3339(utc_now()), venue, market_id),
                )
                connection.commit()
                return
        raise RuntimeError(f"exceeded {max_pages} pages")
    except Exception as exc:
        connection.execute(
            "UPDATE market_status SET status = 'error', last_error = ?, updated_at = ? "
            "WHERE venue = ? AND market_id = ?",
            (f"{type(exc).__name__}: {exc}"[:500], rfc3339(utc_now()), venue, market_id),
        )
        connection.commit()
        raise


def emit_outputs(
    connection: sqlite3.Connection,
    *,
    output: Path,
    protocol: dict[str, Any],
    protocol_path: Path,
    markets_path: Path,
    start: datetime,
    end: datetime,
    candidates: list[tuple[str, str]],
    cursor_report: dict[str, Any],
    seed_report: dict[str, Any],
) -> dict[str, Any]:
    status_counts = dict(
        connection.execute(
            "SELECT status, COUNT(*) FROM market_status GROUP BY status ORDER BY status"
        ).fetchall()
    )
    if status_counts != {"done": len(candidates)}:
        raise RuntimeError(f"cannot finalize incomplete reconciliation: {status_counts}")
    output_paths: dict[str, Path] = {}
    record_counts: dict[str, int] = {}
    markets_with_records: dict[str, int] = {}
    for venue in TIMESTAMP_KEY:
        path = output / f"trades_{venue}.jsonl"
        output_paths[venue] = path
        rows = connection.execute(
            "SELECT r.record_key, r.event_ts, r.record_json FROM records r "
            "WHERE r.venue = ? ORDER BY r.market_id, r.event_ts, r.record_key",
            (venue,),
        ).fetchall()

        def serialized_rows() -> Iterator[dict[str, Any]]:
            for record_key, event_ts, record_json in rows:
                record = json.loads(record_json)
                retrievals = [
                    {
                        "retrieved_at": retrieved_at,
                        "source": source,
                        "source_endpoint": endpoint,
                    }
                    for source, retrieved_at, endpoint in connection.execute(
                        "SELECT source, retrieved_at, source_endpoint FROM retrievals "
                        "WHERE record_key = ? ORDER BY retrieved_at, source",
                        (record_key,),
                    )
                ]
                yield {
                    **record,
                    "_event_ts": event_ts,
                    "_protocol_id": protocol["protocol_id"],
                    "_record_key": record_key,
                    "_retrievals": retrievals,
                }

        atomic_jsonl(path, serialized_rows())
        record_counts[venue] = len(rows)
        markets_with_records[venue] = int(
            connection.execute(
                "SELECT COUNT(DISTINCT market_id) FROM records WHERE venue = ?",
                (venue,),
            ).fetchone()[0]
        )
    zero_trade_counts: dict[str, int] = {}
    for venue in TIMESTAMP_KEY:
        zero_trade_counts[venue] = int(
            connection.execute(
                "SELECT COUNT(*) FROM market_status s WHERE s.venue = ? AND NOT EXISTS "
                "(SELECT 1 FROM records r WHERE r.venue = s.venue AND r.market_id = s.market_id)",
                (venue,),
            ).fetchone()[0]
        )
    coverage = {
        "candidate_markets": dict(Counter(venue for venue, _ in candidates)),
        "collector_cursor_evidence": cursor_report,
        "endpoint_status_counts": status_counts,
        "label_blind": True,
        "labels_read": [],
        "markets_with_selection_trades": markets_with_records,
        "protocol_id": protocol["protocol_id"],
        "selection_end_exclusive": rfc3339(end),
        "selection_records": record_counts,
        "selection_start": rfc3339(start),
        "status": "complete",
        "zero_trade_markets": zero_trade_counts,
    }
    coverage_path = output / "coverage_report.json"
    atomic_json(coverage_path, coverage)
    prospective_seed_evidence = json.loads(stable_json(seed_report))
    for relative_path, specification in prospective_seed_evidence.get("files", {}).items():
        source_path = REPO_ROOT / relative_path
        digest, prefix_bytes = sha256_line_prefix(
            source_path,
            int(specification["rows_scanned"]),
        )
        specification["seeded_prefix_bytes"] = prefix_bytes
        specification["seeded_prefix_sha256"] = digest
    manifest = {
        "completed_at": rfc3339(utc_now()),
        "input_hashes": {
            relative(markets_path): sha256_file(markets_path),
            relative(protocol_path): sha256_file(protocol_path),
        },
        "label_blind": True,
        "labels_read": [],
        "outputs": {
            relative(path): {
                "bytes": path.stat().st_size,
                "sha256": sha256_file(path),
            }
            for path in [*output_paths.values(), coverage_path]
        },
        "prospective_seed": prospective_seed_evidence,
        "protocol_id": protocol["protocol_id"],
        "selection_end_exclusive": rfc3339(end),
        "selection_start": rfc3339(start),
        "status": "complete",
    }
    atomic_json(output / "reconciliation_manifest.json", manifest)
    return {"coverage": coverage, "manifest": manifest}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--protocol", type=Path, default=DEFAULT_PROTOCOL)
    parser.add_argument("--markets", type=Path, default=DEFAULT_MARKETS)
    parser.add_argument("--prospective-root", type=Path, default=DEFAULT_PROSPECTIVE)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--rpm", type=int, default=30)
    parser.add_argument("--page-limit", type=int, default=1000)
    parser.add_argument("--max-pages", type=int, default=10_000)
    parser.add_argument("--max-markets", type=int)
    parser.add_argument("--as-of", help="UTC RFC3339 time; deterministic seal check")
    args = parser.parse_args()
    protocol = load_object(args.protocol)
    if protocol.get("status") != "preregistered_labels_uninspected":
        raise SystemExit("protocol is not label-uninspected")
    start = parse_utc(protocol["windows"]["selection"]["start"])
    end = parse_utc(protocol["windows"]["selection"]["end_exclusive"])
    now = parse_utc(args.as_of) if args.as_of else utc_now()
    if now < end:
        raise SystemExit(f"temporal seal: selection closes at {rfc3339(end)}")
    if args.rpm <= 0 or args.page_limit <= 0 or args.max_pages <= 0:
        raise SystemExit("rpm, page-limit, and max-pages must be positive")
    candidates = load_candidates(args.markets)
    output = args.output.resolve()
    connection = init_database(output / "reconciliation.sqlite3")
    try:
        candidate_material = stable_json(candidates)
        candidate_hash = hashlib.sha256(candidate_material.encode()).hexdigest()
        prior_hash = meta_get(connection, "candidate_hash")
        if prior_hash not in (None, candidate_hash):
            raise ValueError("candidate set changed after reconciliation started")
        meta_set(connection, "candidate_hash", candidate_hash)
        meta_set(connection, "protocol_id", str(protocol["protocol_id"]))
        meta_set(connection, "selection_start", rfc3339(start))
        meta_set(connection, "selection_end_exclusive", rfc3339(end))
        for venue, market_id in candidates:
            connection.execute(
                "INSERT OR IGNORE INTO market_status(venue, market_id) VALUES (?, ?)",
                (venue, market_id),
            )
        connection.commit()
        seed_report = seed_prospective(
            connection,
            prospective_root=args.prospective_root,
            protocol_id=str(protocol["protocol_id"]),
            candidates=set(candidates),
            start=start,
            end=end,
        )
        cursor_report = verify_collector_cursors(
            args.prospective_root / "state" / "collector.sqlite3",
            candidates,
            end,
        )
        if cursor_report["status"] != "complete":
            raise RuntimeError("prospective collector cursors do not cover the selection cutoff")
        pending = connection.execute(
            "SELECT venue, market_id FROM market_status WHERE status != 'done' "
            "ORDER BY venue, market_id"
        ).fetchall()
        if args.max_markets is not None:
            pending = pending[: args.max_markets]
        errors = 0
        with FindataClient(rpm=args.rpm, timeout=60.0) as client:
            for index, (venue, market_id) in enumerate(pending, start=1):
                try:
                    fetch_market(
                        connection,
                        client,
                        venue=str(venue),
                        market_id=str(market_id),
                        start=start,
                        end=end,
                        page_limit=args.page_limit,
                        max_pages=args.max_pages,
                        protocol_id=str(protocol["protocol_id"]),
                    )
                except Exception as exc:
                    errors += 1
                    print(
                        f"error {venue}:{market_id}: {type(exc).__name__}: {exc}",
                        flush=True,
                    )
                if index % 50 == 0 or index == len(pending):
                    counts = dict(
                        connection.execute(
                            "SELECT status, COUNT(*) FROM market_status GROUP BY status"
                        ).fetchall()
                    )
                    print(
                        stable_json(
                            {
                                "attempted_this_run": index,
                                "errors_this_run": errors,
                                "market_status": counts,
                                "remaining_this_run": len(pending) - index,
                            }
                        ),
                        flush=True,
                    )
        if args.max_markets is not None:
            return
        if errors:
            raise SystemExit(f"reconciliation has {errors} endpoint errors; rerun to retry")
        result = emit_outputs(
            connection,
            output=output,
            protocol=protocol,
            protocol_path=args.protocol,
            markets_path=args.markets,
            start=start,
            end=end,
            candidates=candidates,
            cursor_report=cursor_report,
            seed_report=seed_report,
        )
        print(json.dumps(result["coverage"], indent=2, sort_keys=True))
    finally:
        connection.close()


if __name__ == "__main__":
    main()
