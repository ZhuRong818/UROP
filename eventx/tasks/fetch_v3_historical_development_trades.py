"""Fetch hash-verified development trades for the frozen EventX v3 cohort.

Only the development interval is queried.  Historical holdout prices, labels,
predictions, outcomes, and metrics are neither requested nor read.
"""

from __future__ import annotations

import argparse
from datetime import datetime, timedelta, timezone
import json
import os
from pathlib import Path
import shutil
from typing import Any, Iterator

import httpx

from eventx.settings import ApiSettings, REPO_ROOT
from eventx.tasks.export_v3_historical_feasibility import (
    compact_receipt,
    download,
    parse_utc,
    RetrieveFailure,
    retrieve_with_retry,
    rfc3339,
    sha256_file,
    sql_literal,
)


PROTOCOL_PATH = REPO_ROOT / "eventx/release/v3_historical_primary/protocol.json"
PREREG_MANIFEST = (
    REPO_ROOT
    / "eventx/release/v3_historical_primary/preregistration_manifest.json"
)
POWER_MANIFEST = REPO_ROOT / "data/v3_historical/primary/power/manifest.json"
DEFAULT_OUTPUT = REPO_ROOT / "data/v3_historical/primary/development/trades"
DEVELOPMENT_START = "2026-05-17T00:00:00Z"
DEVELOPMENT_END = "2026-07-22T00:00:00Z"
MIN_SPLIT_MINUTES = 15


def atomic_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n")
    os.replace(temporary, path)


def read_jsonl(path: Path) -> Iterator[dict[str, Any]]:
    with path.open(encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, start=1):
            if not line.strip():
                continue
            value = json.loads(line)
            if not isinstance(value, dict):
                raise RuntimeError(f"{path}:{line_number} is not an object")
            yield value


def verify_hash_manifest(path: Path) -> None:
    value = json.loads(path.read_text(encoding="utf-8"))
    for artifact in value.get("artifacts", []):
        artifact_path = REPO_ROOT / str(artifact["path"])
        if not artifact_path.is_file() or sha256_file(artifact_path) != artifact["sha256"]:
            raise RuntimeError(f"hash manifest failure: {artifact['path']}")


def ensure_space(path: Path, minimum_gib: float) -> None:
    free = shutil.disk_usage(path).free
    if free < int(minimum_gib * 1024**3):
        raise RuntimeError(
            f"disk safety floor reached: {free / 1024**3:.2f} GiB < {minimum_gib:.2f} GiB"
        )


def cohort_by_venue(protocol: dict[str, Any]) -> dict[str, list[dict[str, Any]]]:
    path = REPO_ROOT / protocol["cohort"]["path"]
    if sha256_file(path) != protocol["cohort"]["sha256"]:
        raise RuntimeError("frozen cohort hash mismatch")
    grouped = {"kalshi": [], "polymarket": []}
    for row in read_jsonl(path):
        grouped[str(row["venue"])].append(row)
    for values in grouped.values():
        values.sort(key=lambda row: str(row["market_id"]))
    return grouped


def query(venue: str, cohort: list[dict[str, Any]], start: datetime, end: datetime) -> str:
    start_text = rfc3339(start)
    end_text = rfc3339(end)
    if venue == "kalshi":
        keys = ",".join(sql_literal(str(row["market_id"])) for row in cohort)
        return f"""SELECT trade_id, ticker, created_time, count, yes_price
FROM prediction_markets.kalshi_trades
WHERE created_time >= TIMESTAMPTZ '{start_text}'
  AND created_time < TIMESTAMPTZ '{end_text}'
  AND trade_id IS NOT NULL
  AND yes_price BETWEEN 0 AND 100
  AND ticker IN ({keys})
ORDER BY ticker, created_time, trade_id"""
    pairs = ",".join(
        "(" + sql_literal(str(row["market_id"])) + ","
        + sql_literal(str(row["canonical_yes_asset_id"])) + ")"
        for row in cohort
    )
    return f"""SELECT trade_id, condition_id, asset_id, ts, price, size
FROM prediction_markets.polymarket_trades
WHERE ts >= TIMESTAMPTZ '{start_text}'
  AND ts < TIMESTAMPTZ '{end_text}'
  AND trade_id IS NOT NULL
  AND price BETWEEN 0 AND 1
  AND (condition_id, COALESCE(asset_id, '')) IN ({pairs})
ORDER BY condition_id, asset_id, ts, trade_id"""


def validate_page(
    path: Path,
    venue: str,
    allowed: set[tuple[str, str]],
    start: datetime,
    end: datetime,
    expected_rows: int,
) -> dict[str, Any]:
    rows = 0
    trade_keys: dict[tuple[str, str], tuple[Any, ...]] = {}
    exact_duplicate_rows = 0
    conflicting_duplicate_keys = 0
    min_ts: datetime | None = None
    max_ts: datetime | None = None
    for row in read_jsonl(path):
        rows += 1
        trade_id = str(row.get("trade_id") or "")
        if not trade_id:
            raise RuntimeError(f"missing trade id in {path}")
        if venue == "kalshi":
            key = (str(row.get("ticker") or ""), "")
            timestamp = parse_utc(str(row["created_time"]))
            price = float(row["yes_price"])
            if not 0 <= price <= 100:
                raise RuntimeError(f"invalid Kalshi price in {path}")
        else:
            key = (
                str(row.get("condition_id") or ""),
                str(row.get("asset_id") or ""),
            )
            timestamp = parse_utc(str(row["ts"]))
            price = float(row["price"])
            if not 0 <= price <= 1:
                raise RuntimeError(f"invalid Polymarket price in {path}")
        trade_key = (trade_id, rfc3339(timestamp))
        signature = (
            key,
            row.get("count") if venue == "kalshi" else row.get("size"),
            row.get("yes_price") if venue == "kalshi" else row.get("price"),
        )
        previous = trade_keys.get(trade_key)
        if previous is not None:
            if previous == signature:
                exact_duplicate_rows += 1
            else:
                conflicting_duplicate_keys += 1
        else:
            trade_keys[trade_key] = signature
        if key not in allowed:
            raise RuntimeError(f"out-of-cohort trade in {path}: {key}")
        if not start <= timestamp < end:
            raise RuntimeError(f"out-of-window trade in {path}: {timestamp}")
        min_ts = timestamp if min_ts is None else min(min_ts, timestamp)
        max_ts = timestamp if max_ts is None else max(max_ts, timestamp)
    if rows != expected_rows:
        raise RuntimeError(f"rowcount mismatch in {path}: {rows} != {expected_rows}")
    if conflicting_duplicate_keys:
        raise RuntimeError(
            "conflicting duplicate (trade_id, timestamp) keys within "
            f"{path}: {conflicting_duplicate_keys}"
        )
    return {
        "rows": rows,
        "unique_trade_keys": len(trade_keys),
        "trade_key": "(trade_id, venue_trade_timestamp)",
        "exact_duplicate_rows_to_collapse": exact_duplicate_rows,
        "conflicting_duplicate_keys": conflicting_duplicate_keys,
        "min_ts": rfc3339(min_ts) if min_ts else None,
        "max_ts": rfc3339(max_ts) if max_ts else None,
    }


def base_intervals(start: datetime, end: datetime) -> list[tuple[datetime, datetime]]:
    values = []
    cursor = start
    while cursor < end:
        right = min(cursor + timedelta(days=1), end)
        values.append((cursor, right))
        cursor = right
    return values


def fetch_venue(
    client: httpx.Client,
    venue: str,
    cohort: list[dict[str, Any]],
    output: Path,
    minimum_free_gib: float,
) -> dict[str, Any]:
    root = output / venue
    pages_root = root / "pages"
    pages_root.mkdir(parents=True, exist_ok=True)
    checkpoint_path = root / "checkpoint.json"
    manifest_path = root / "manifest.json"
    if manifest_path.is_file():
        value = json.loads(manifest_path.read_text(encoding="utf-8"))
        if value.get("integrity_pass") is True:
            return value
        raise RuntimeError(f"existing non-passing manifest requires review: {manifest_path}")
    checkpoint = (
        json.loads(checkpoint_path.read_text(encoding="utf-8"))
        if checkpoint_path.is_file()
        else {"completed_days": 0, "artifacts": []}
    )
    artifacts = list(checkpoint.get("artifacts", []))
    completed_days = int(checkpoint.get("completed_days", 0))
    start = parse_utc(DEVELOPMENT_START)
    end = parse_utc(DEVELOPMENT_END)
    allowed = {
        (
            str(row["market_id"]),
            "" if venue == "kalshi" else str(row["canonical_yes_asset_id"]),
        )
        for row in cohort
    }
    for artifact in artifacts:
        page_path = REPO_ROOT / str(artifact["data_path"])
        if sha256_file(page_path) != artifact["data_sha256"]:
            raise RuntimeError(f"checkpoint data hash mismatch: {page_path}")
        artifact["summary"] = validate_page(
            page_path,
            venue,
            allowed,
            parse_utc(str(artifact["start"])),
            parse_utc(str(artifact["end_exclusive"])),
            int(artifact["summary"]["rows"]),
        )

    def fetch_interval(left: datetime, right: datetime, tag: str) -> list[dict[str, Any]]:
        sql = query(venue, cohort, left, right)
        query_path = pages_root / f"query_{tag}.sql"
        timed_out_path = pages_root / f"query_{tag}_timed_out.sql"
        page_path = pages_root / f"trades_{tag}.jsonl"
        receipt_path = pages_root / f"receipt_{tag}.json"
        expected_query = sql + "\n"
        if timed_out_path.is_file() and timed_out_path.read_text(encoding="utf-8") == expected_query:
            midpoint = left + (right - left) / 2
            return [
                *fetch_interval(left, midpoint, tag + "a"),
                *fetch_interval(midpoint, right, tag + "b"),
            ]
        if all(path.is_file() for path in (query_path, page_path, receipt_path)):
            if query_path.read_text(encoding="utf-8") != expected_query:
                raise RuntimeError(f"resumed query changed: {query_path}")
            receipt_value = json.loads(receipt_path.read_text(encoding="utf-8"))
            expected_rows = int(receipt_value["receipt"]["rowcount"])
            summary = validate_page(
                page_path, venue, allowed, left, right, expected_rows
            )
            return [{
                "tag": tag,
                "start": rfc3339(left),
                "end_exclusive": rfc3339(right),
                "query_path": str(query_path.relative_to(REPO_ROOT)),
                "query_sha256": sha256_file(query_path),
                "data_path": str(page_path.relative_to(REPO_ROOT)),
                "data_sha256": sha256_file(page_path),
                "receipt_path": str(receipt_path.relative_to(REPO_ROOT)),
                "receipt_sha256": sha256_file(receipt_path),
                "summary": summary,
                "resumed": True,
            }]
        query_path.write_text(expected_query, encoding="utf-8")
        try:
            receipt, retry_ledger = retrieve_with_retry(
                client, sql, attempts=1, delays=[10.0]
            )
        except RetrieveFailure as exc:
            error_text = str(exc).lower()
            needs_split = "statement timeout" in error_text or "row cap" in error_text
            if needs_split and (right - left).total_seconds() / 60 > MIN_SPLIT_MINUTES:
                query_path.rename(timed_out_path)
                midpoint = left + (right - left) / 2
                return [
                    *fetch_interval(left, midpoint, tag + "a"),
                    *fetch_interval(midpoint, right, tag + "b"),
                ]
            receipt, retry_ledger = retrieve_with_retry(
                client, sql, attempts=3, delays=[10.0, 30.0, 120.0]
            )
        ensure_space(output, minimum_free_gib)
        download(client, str(receipt["materialized_uri"]), page_path)
        atomic_json(
            receipt_path,
            {"receipt": compact_receipt(receipt), "retry_ledger": retry_ledger},
        )
        summary = validate_page(
            page_path, venue, allowed, left, right, int(receipt["rowcount"])
        )
        return [{
            "tag": tag,
            "start": rfc3339(left),
            "end_exclusive": rfc3339(right),
            "query_path": str(query_path.relative_to(REPO_ROOT)),
            "query_sha256": sha256_file(query_path),
            "data_path": str(page_path.relative_to(REPO_ROOT)),
            "data_sha256": sha256_file(page_path),
            "receipt_path": str(receipt_path.relative_to(REPO_ROOT)),
            "receipt_sha256": sha256_file(receipt_path),
            "summary": summary,
            "resumed": False,
        }]

    intervals = base_intervals(start, end)
    for day_number, (left, right) in enumerate(intervals, start=1):
        if day_number <= completed_days:
            continue
        day_artifacts = fetch_interval(left, right, f"{day_number:03d}")
        artifacts.extend(day_artifacts)
        completed_days = day_number
        atomic_json(
            checkpoint_path,
            {
                "protocol_id": "eventx-v3-historical-primary-20260902",
                "venue": venue,
                "completed_days": completed_days,
                "artifacts": artifacts,
                "labels_or_outcomes_read": False,
                "holdout_prices_read": False,
                "updated_at": rfc3339(datetime.now(timezone.utc)),
            },
        )
    total_rows = sum(int(item["summary"]["rows"]) for item in artifacts)
    total_unique = sum(
        int(item["summary"]["unique_trade_keys"]) for item in artifacts
    )
    total_exact_duplicates = sum(
        int(item["summary"].get("exact_duplicate_rows_to_collapse", 0))
        for item in artifacts
    )
    manifest = {
        "protocol_id": "eventx-v3-historical-primary-20260902",
        "venue": venue,
        "window": {"start": DEVELOPMENT_START, "end_exclusive": DEVELOPMENT_END},
        "cohort_markets": len(cohort),
        "pages": len(artifacts),
        "rows": total_rows,
        "unique_trade_keys": total_unique,
        "exact_duplicate_rows_to_collapse": total_exact_duplicates,
        "artifacts": artifacts,
        "checkpoint_sha256": sha256_file(checkpoint_path),
        "integrity_pass": completed_days == len(intervals) and total_unique > 0,
        "labels_or_outcomes_read": False,
        "holdout_prices_read": False,
        "completed_at": rfc3339(datetime.now(timezone.utc)),
    }
    atomic_json(manifest_path, manifest)
    return manifest


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--venue", choices=["kalshi", "polymarket", "both"], default="both")
    parser.add_argument("--timeout", type=float, default=1800.0)
    parser.add_argument("--minimum-free-gib", type=float, default=10.0)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    verify_hash_manifest(PREREG_MANIFEST)
    verify_hash_manifest(POWER_MANIFEST)
    protocol = json.loads(PROTOCOL_PATH.read_text(encoding="utf-8"))
    if protocol.get("status") != "preregistered_before_prices_labels_or_outcomes":
        raise SystemExit("historical protocol is not in its pre-label state")
    if (REPO_ROOT / "data/v3_historical/primary/holdout").exists():
        raise SystemExit("historical holdout directory exists before candidate freeze")
    if (REPO_ROOT / "data/v3_historical/primary/development/labels.jsonl").exists():
        raise SystemExit("development labels already exist")
    args.output.mkdir(parents=True, exist_ok=True)
    ensure_space(args.output, args.minimum_free_gib)
    grouped = cohort_by_venue(protocol)
    venues = ("kalshi", "polymarket") if args.venue == "both" else (args.venue,)
    settings = ApiSettings.from_env()
    summaries = {}
    with httpx.Client(
        base_url=settings.base_url,
        headers={"Authorization": f"Bearer {settings.token}"},
        timeout=httpx.Timeout(args.timeout),
        follow_redirects=True,
    ) as client:
        for venue in venues:
            summaries[venue] = fetch_venue(
                client,
                venue,
                grouped[venue],
                args.output,
                args.minimum_free_gib,
            )
    print(json.dumps({
        "status": "development_trades_complete",
        "labels_or_outcomes_read": False,
        "holdout_prices_read": False,
        "venues": {
            venue: {
                "rows": value["rows"],
                "pages": value["pages"],
                "integrity_pass": value["integrity_pass"],
            }
            for venue, value in summaries.items()
        },
    }, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
