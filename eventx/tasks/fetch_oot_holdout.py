"""Snapshot fresh trades for the frozen EventX cohort into a separate extract."""

from __future__ import annotations

import argparse
import json
from datetime import timedelta
from pathlib import Path
from typing import Any

from eventx.features.build_kol_features import parse_ts
from eventx.ingest.client import FindataClient
from eventx.settings import REPO_ROOT
from eventx.tasks.freeze_toy import hash_file
from eventx.tasks.toy_slice import as_rfc3339, read_jsonl

DEFAULT_EXTRACT = "v1_oot_20260723_20260730"
DEFAULT_WARMUP_START = "2026-07-22T00:00:00Z"
DEFAULT_HOLDOUT_START = "2026-07-23T00:00:00Z"
DEFAULT_END = "2026-07-30T23:59:59Z"


def page_market_trades(
    client: FindataClient,
    market_id: str,
    extract: str,
    warmup_start: str,
    end: str,
    page_limit: int,
    max_pages: int,
) -> tuple[list[dict[str, Any]], int]:
    floor = parse_ts(warmup_start)
    ceiling = parse_ts(end)
    to_cursor = end
    by_trade_id: dict[str, dict[str, Any]] = {}
    calls = 0
    previous_oldest = None
    for _ in range(max_pages):
        response = client.get(
            f"/prediction-markets/trades/polymarket/{market_id}",
            limit=page_limit,
            **{"from": warmup_start, "to": to_cursor},
        )
        calls += 1
        if not isinstance(response, list) or not response:
            break
        valid_rows = [
            row
            for row in response
            if isinstance(row, dict)
            and row.get("ts")
            and floor <= parse_ts(str(row["ts"])) <= ceiling
        ]
        for row in valid_rows:
            trade_id = str(row.get("trade_id") or "")
            if not trade_id:
                raise SystemExit(f"Trade without trade_id for market {market_id}.")
            by_trade_id[trade_id] = {
                **row,
                "venue": "polymarket",
                "market_id": market_id,
                "_extract_version": extract,
            }
        oldest = min(parse_ts(str(row["ts"])) for row in response if row.get("ts"))
        if oldest <= floor or len(response) < page_limit:
            break
        if previous_oldest is not None and oldest >= previous_oldest:
            raise SystemExit(f"Trade cursor did not move for market {market_id}.")
        previous_oldest = oldest
        to_cursor = as_rfc3339(oldest - timedelta(microseconds=1))
    else:
        raise SystemExit(f"Trade pagination exceeded {max_pages} pages for {market_id}.")
    rows = sorted(
        by_trade_id.values(),
        key=lambda row: (str(row["ts"]), str(row["trade_id"])),
    )
    return rows, calls


def main() -> None:
    parser = argparse.ArgumentParser(description="Fetch EventX out-of-time holdout trades")
    parser.add_argument("--extract", default=DEFAULT_EXTRACT)
    parser.add_argument("--selected-markets", type=Path)
    parser.add_argument("--warmup-start", default=DEFAULT_WARMUP_START)
    parser.add_argument("--holdout-start", default=DEFAULT_HOLDOUT_START)
    parser.add_argument("--end", default=DEFAULT_END)
    parser.add_argument("--page-limit", type=int, default=1000)
    parser.add_argument("--max-pages", type=int, default=1000)
    args = parser.parse_args()
    warmup_start = parse_ts(args.warmup_start)
    holdout_start = parse_ts(args.holdout_start)
    end = parse_ts(args.end)
    if not warmup_start < holdout_start < end:
        raise SystemExit("Expected warmup_start < holdout_start < end.")

    selected_path = (
        args.selected_markets
        or REPO_ROOT / "data" / "v1" / "toy" / "selected_markets.jsonl"
    )
    selected = list(read_jsonl(selected_path))
    if len(selected) != 20:
        raise SystemExit(f"Expected frozen 20-market cohort, found {len(selected)}.")
    out_root = REPO_ROOT / "data" / args.extract
    raw_dir = out_root / "raw"
    raw_path = raw_dir / "trades_polymarket.jsonl"
    manifest_path = out_root / "fetch_manifest.json"
    if raw_path.exists() or manifest_path.exists():
        raise SystemExit(f"Refusing to replace existing OOT snapshot under {out_root}.")
    raw_dir.mkdir(parents=True, exist_ok=True)

    all_rows: list[dict[str, Any]] = []
    market_stats = []
    total_calls = 0
    with FindataClient() as client:
        for position, market in enumerate(selected, start=1):
            market_id = str(market["market_id"])
            rows, calls = page_market_trades(
                client,
                market_id,
                args.extract,
                args.warmup_start,
                args.end,
                args.page_limit,
                args.max_pages,
            )
            total_calls += calls
            all_rows.extend(rows)
            market_stats.append(
                {
                    "market_id": market_id,
                    "question": market["question"],
                    "rows": len(rows),
                    "oldest_ts": rows[0]["ts"] if rows else None,
                    "newest_ts": rows[-1]["ts"] if rows else None,
                    "calls": calls,
                }
            )
            print(
                f"[{position:02d}/{len(selected)}] {market_id}: "
                f"{len(rows)} rows in {calls} calls",
                flush=True,
            )
    all_rows.sort(
        key=lambda row: (
            str(row["market_id"]),
            str(row["ts"]),
            str(row["trade_id"]),
        )
    )
    temporary = raw_path.with_suffix(".jsonl.tmp")
    with temporary.open("w") as handle:
        for row in all_rows:
            handle.write(json.dumps(row, sort_keys=True) + "\n")
    temporary.replace(raw_path)
    manifest = {
        "status": "fresh_trade_snapshot_complete",
        "extract_version": args.extract,
        "venue": "polymarket",
        "cohort": {
            "path": str(selected_path.resolve().relative_to(REPO_ROOT)),
            "sha256": hash_file(selected_path)["sha256"],
            "markets": len(selected),
            "selection_basis": "previously_frozen_training_period_only",
        },
        "window": {
            "warmup_start": args.warmup_start,
            "holdout_start": args.holdout_start,
            "end": args.end,
        },
        "request_contract": {
            "endpoint": "/prediction-markets/trades/polymarket/{market_id}",
            "page_limit": args.page_limit,
            "time_bounded": True,
            "total_calls": total_calls,
        },
        "artifact": {
            "path": str(raw_path.resolve().relative_to(REPO_ROOT)),
            **hash_file(raw_path),
        },
        "market_coverage": market_stats,
        "label_policy": "No labels were constructed or inspected during this fetch.",
    }
    manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n")
    print(
        json.dumps(
            {
                "status": manifest["status"],
                "window": manifest["window"],
                "artifact": manifest["artifact"],
                "markets_with_rows": sum(row["rows"] > 0 for row in market_stats),
                "total_calls": total_calls,
                "manifest": str(manifest_path),
            },
            indent=2,
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
