"""Fetch the sealed EventX v3.1 historical-holdout trade covariates.

This task is runnable only after the single development candidate and the holdout
implementation have been hash-frozen. It retrieves the fixed interval
[2026-07-22, 2026-08-08) for the corrected cohort and supports exact resume.
"""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
from typing import Any

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
)
from eventx.tasks.fetch_v3_historical_development_trades import (
    atomic_json,
    base_intervals,
    cohort_by_venue,
    ensure_space,
    query,
    validate_page,
)


PROTOCOL = REPO_ROOT / "eventx/release/v3_1_historical_primary/protocol.json"
CANDIDATE_MANIFEST = (
    REPO_ROOT / "eventx/release/v3_1_historical_primary/candidate_manifest.json"
)
HOLDOUT_IMPLEMENTATION_MANIFEST = (
    REPO_ROOT
    / "eventx/release/v3_1_historical_primary/holdout_implementation_manifest.json"
)
DEFAULT_OUTPUT = REPO_ROOT / "data/v3_1_historical/primary/holdout/trades"
HOLDOUT_START = "2026-07-22T00:00:00Z"
HOLDOUT_END = "2026-08-08T00:00:00Z"
MIN_SPLIT_MINUTES = 15


def relative(path: Path) -> str:
    return str(path.relative_to(REPO_ROOT))


def verify_hash_manifest(path: Path) -> None:
    value = json.loads(path.read_text(encoding="utf-8"))
    for artifact in value.get("artifacts", []):
        artifact_path = REPO_ROOT / str(artifact["path"])
        if not artifact_path.is_file() or sha256_file(artifact_path) != str(
            artifact["sha256"]
        ):
            raise RuntimeError(f"hash manifest failure: {artifact_path}")


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
    start = parse_utc(HOLDOUT_START)
    end = parse_utc(HOLDOUT_END)
    allowed = {
        (
            str(row["market_id"]),
            "" if venue == "kalshi" else str(row["canonical_yes_asset_id"]),
        )
        for row in cohort
    }

    for artifact in artifacts:
        page_path = REPO_ROOT / str(artifact["data_path"])
        if sha256_file(page_path) != str(artifact["data_sha256"]):
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
        if timed_out_path.is_file() and timed_out_path.read_text(
            encoding="utf-8"
        ) == expected_query:
            midpoint = left + (right - left) / 2
            return [
                *fetch_interval(left, midpoint, tag + "a"),
                *fetch_interval(midpoint, right, tag + "b"),
            ]
        if all(path.is_file() for path in (query_path, page_path, receipt_path)):
            if query_path.read_text(encoding="utf-8") != expected_query:
                raise RuntimeError(f"resumed query changed: {query_path}")
            receipt_value = json.loads(receipt_path.read_text(encoding="utf-8"))
            summary = validate_page(
                page_path,
                venue,
                allowed,
                left,
                right,
                int(receipt_value["receipt"]["rowcount"]),
            )
            return [{
                "tag": tag,
                "start": rfc3339(left),
                "end_exclusive": rfc3339(right),
                "query_path": relative(query_path),
                "query_sha256": sha256_file(query_path),
                "data_path": relative(page_path),
                "data_sha256": sha256_file(page_path),
                "receipt_path": relative(receipt_path),
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
            "query_path": relative(query_path),
            "query_sha256": sha256_file(query_path),
            "data_path": relative(page_path),
            "data_sha256": sha256_file(page_path),
            "receipt_path": relative(receipt_path),
            "receipt_sha256": sha256_file(receipt_path),
            "summary": summary,
            "resumed": False,
        }]

    intervals = base_intervals(start, end)
    for day_number, (left, right) in enumerate(intervals, start=1):
        if day_number <= completed_days:
            continue
        artifacts.extend(fetch_interval(left, right, f"{day_number:03d}"))
        completed_days = day_number
        atomic_json(
            checkpoint_path,
            {
                "protocol_id": "eventx-v3.1-historical-primary-20260902",
                "venue": venue,
                "completed_days": completed_days,
                "artifacts": artifacts,
                "holdout_prices_read": True,
                "holdout_metrics_read": False,
                "updated_at": rfc3339(datetime.now(timezone.utc)),
            },
        )

    total_rows = sum(int(item["summary"]["rows"]) for item in artifacts)
    total_unique = sum(
        int(item["summary"]["unique_trade_keys"]) for item in artifacts
    )
    manifest = {
        "protocol_id": "eventx-v3.1-historical-primary-20260902",
        "venue": venue,
        "window": {"start": HOLDOUT_START, "end_exclusive": HOLDOUT_END},
        "cohort_markets": len(cohort),
        "pages": len(artifacts),
        "rows": total_rows,
        "unique_trade_keys": total_unique,
        "exact_duplicate_rows_to_collapse": sum(
            int(item["summary"].get("exact_duplicate_rows_to_collapse", 0))
            for item in artifacts
        ),
        "artifacts": artifacts,
        "checkpoint_sha256": sha256_file(checkpoint_path),
        "integrity_pass": completed_days == len(intervals) and total_unique > 0,
        "holdout_prices_read": True,
        "holdout_metrics_read": False,
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
    verify_hash_manifest(CANDIDATE_MANIFEST)
    verify_hash_manifest(HOLDOUT_IMPLEMENTATION_MANIFEST)
    candidate_manifest = json.loads(CANDIDATE_MANIFEST.read_text(encoding="utf-8"))
    if candidate_manifest.get("candidate_count") != 1:
        raise SystemExit("exactly one frozen candidate is required")
    protocol = json.loads(PROTOCOL.read_text(encoding="utf-8"))
    if protocol["windows"]["one_shot_holdout"] != (
        "[2026-07-22T00:00:00Z, 2026-08-08T00:00:00Z)"
    ):
        raise SystemExit("holdout window differs from frozen protocol")
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
                client, venue, grouped[venue], args.output, args.minimum_free_gib
            )
    print(json.dumps({
        "status": "holdout_trade_covariates_retrieved_metrics_unread",
        "holdout_prices_read": True,
        "holdout_metrics_read": False,
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
