"""Label-blind integrity and continuity gate for retrieved v3.1 holdout trades."""

from __future__ import annotations

from collections import Counter
from datetime import timedelta
import json
import os
from pathlib import Path
from typing import Any, Iterator

import numpy as np

from eventx.settings import REPO_ROOT
from eventx.tasks.export_v3_historical_feasibility import parse_utc, rfc3339
from eventx.tasks.prepare_v3_1_historical_development_arrays import (
    TRADE_DTYPE,
    sha256_file,
)


ROOT = REPO_ROOT / "data/v3_1_historical/primary/holdout"
TRADES = ROOT / "trades"
REPORT = ROOT / "trade_data_gate.json"
MANIFEST = ROOT / "trade_data_gate_manifest.json"
EXAMPLES = ROOT / "examples.bin"
RECEIPT = ROOT / "holdout_consumption_receipt.json"
RESULT = ROOT / "evaluation_result.json"
DEVELOPMENT_TRADES = (
    REPO_ROOT / "data/v3_1_historical/primary/development/prepared/trades.bin"
)


def relative(path: Path) -> str:
    return str(path.relative_to(REPO_ROOT))


def atomic_json(path: Path, value: Any) -> None:
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n")
    os.replace(temporary, path)


def read_jsonl(path: Path) -> Iterator[dict[str, Any]]:
    with path.open(encoding="utf-8") as handle:
        for line in handle:
            if line.strip():
                yield json.loads(line)


def audit_venue(venue: str) -> dict[str, Any]:
    path = TRADES / venue / "manifest.json"
    manifest = json.loads(path.read_text(encoding="utf-8"))
    days = []
    total_rows = 0
    zero_notional = 0
    all_markets: set[str] = set()
    expected_start = parse_utc("2026-07-22T00:00:00Z")
    for day_number, artifact in enumerate(manifest["artifacts"], start=1):
        start = parse_utc(str(artifact["start"]))
        end = parse_utc(str(artifact["end_exclusive"]))
        if start != expected_start or end != start + timedelta(days=1):
            raise RuntimeError(f"non-contiguous {venue} partition {artifact['tag']}")
        expected_start = end
        for field in ("query", "data", "receipt"):
            artifact_path = REPO_ROOT / str(artifact[f"{field}_path"])
            if sha256_file(artifact_path) != str(artifact[f"{field}_sha256"]):
                raise RuntimeError(f"{venue} {field} hash mismatch: {artifact_path}")
        page_path = REPO_ROOT / str(artifact["data_path"])
        rows = 0
        markets: set[str] = set()
        first = None
        last = None
        for row in read_jsonl(page_path):
            rows += 1
            if venue == "kalshi":
                market = str(row["ticker"])
                value = float(row["count"])
                timestamp = parse_utc(str(row["created_time"]))
            else:
                market = str(row["condition_id"])
                value = float(row["size"])
                timestamp = parse_utc(str(row["ts"]))
            if not start <= timestamp < end:
                raise RuntimeError(f"out-of-window {venue} row in {page_path}")
            zero_notional += int(value == 0.0)
            markets.add(market)
            all_markets.add(market)
            first = timestamp if first is None else min(first, timestamp)
            last = timestamp if last is None else max(last, timestamp)
        expected_rows = int(artifact["summary"]["rows"])
        if rows != expected_rows:
            raise RuntimeError(f"{venue} row mismatch: {rows} != {expected_rows}")
        total_rows += rows
        days.append({
            "date": start.date().isoformat(),
            "rows": rows,
            "active_markets": len(markets),
            "first_timestamp": rfc3339(first) if first else None,
            "last_timestamp": rfc3339(last) if last else None,
        })
    checks = {
        "retrieval_manifest_passed": manifest.get("integrity_pass") is True,
        "exactly_17_contiguous_days": len(days) == 17
        and expected_start == parse_utc("2026-08-08T00:00:00Z"),
        "every_day_has_rows": all(day["rows"] > 0 for day in days),
        "manifest_rowcount_matches": total_rows == int(manifest["rows"]),
        "no_conflicting_duplicate_keys": all(
            int(item["summary"].get("conflicting_duplicate_keys", 0)) == 0
            for item in manifest["artifacts"]
        ),
    }
    return {
        "venue": venue,
        "rows": total_rows,
        "zero_notional_rows_to_exclude": zero_notional,
        "markets_with_any_holdout_execution": len(all_markets),
        "days": days,
        "checks": checks,
        "integrity_pass": all(checks.values()),
        "source_manifest": {"path": relative(path), "sha256": sha256_file(path)},
    }


def development_tail() -> list[dict[str, int | str]]:
    count = DEVELOPMENT_TRADES.stat().st_size // TRADE_DTYPE.itemsize
    values = np.memmap(
        DEVELOPMENT_TRADES, mode="r", dtype=TRADE_DTYPE, shape=(count,)
    )
    day_us = 86_400 * 1_000_000
    day = np.asarray(values["timestamp_us"] // day_us, dtype=np.int64)
    unique, counts = np.unique(day, return_counts=True)
    return [
        {
            "date": str(np.datetime64(int(value), "D")),
            "rows": int(rows),
            "active_markets": int(len(np.unique(values["market"][day == value]))),
        }
        for value, rows in zip(unique[-17:], counts[-17:])
    ]


def main() -> None:
    if REPORT.exists() or MANIFEST.exists():
        raise SystemExit("holdout trade data gate already exists")
    if EXAMPLES.exists() or RECEIPT.exists() or RESULT.exists():
        raise SystemExit("holdout labels or metrics exist before trade data gate")
    venue_reports = {venue: audit_venue(venue) for venue in ("kalshi", "polymarket")}
    checks = {
        "both_venue_integrity_gates_pass": all(
            value["integrity_pass"] for value in venue_reports.values()
        ),
        "all_34_bounded_daily_partitions_nonempty": all(
            day["rows"] > 0
            for value in venue_reports.values()
            for day in value["days"]
        ),
        "labels_predictions_or_metrics_read": False,
    }
    passed = (
        checks["both_venue_integrity_gates_pass"]
        and checks["all_34_bounded_daily_partitions_nonempty"]
        and checks["labels_predictions_or_metrics_read"] is False
    )
    development = development_tail()
    holdout_daily_rows = [
        sum(venue_reports[venue]["days"][index]["rows"] for venue in venue_reports)
        for index in range(17)
    ]
    report = {
        "protocol_id": "eventx-v3.1-historical-primary-20260902",
        "status": "passed_source_bounded_holdout_trade_gate" if passed else "failed",
        "integrity_pass": passed,
        "label_blind": True,
        "holdout_prices_retrieved": True,
        "labels_predictions_or_metrics_read": False,
        "source_claim": (
            "Complete bounded retrieval of rows present in Lumid; this does not "
            "claim completeness of the global prediction-market universe."
        ),
        "venue_reports": venue_reports,
        "continuity_context": {
            "last_17_development_days": development,
            "holdout_daily_rows_both_venues": holdout_daily_rows,
            "development_tail_median_rows": float(
                np.median([int(value["rows"]) for value in development])
            ),
            "holdout_median_rows": float(np.median(holdout_daily_rows)),
            "interpretation": (
                "Volume declines with frozen-cohort attrition, but both sources have "
                "nonempty exact-bound daily coverage throughout the holdout."
            ),
        },
        "checks": checks,
    }
    atomic_json(REPORT, report)
    atomic_json(
        MANIFEST,
        {
            "protocol_id": report["protocol_id"],
            "status": report["status"],
            "labels_predictions_or_metrics_read": False,
            "artifacts": [
                {"path": relative(path), "sha256": sha256_file(path)}
                for path in (
                    TRADES / "kalshi/manifest.json",
                    TRADES / "polymarket/manifest.json",
                    DEVELOPMENT_TRADES,
                    REPORT,
                    Path(__file__).resolve(),
                )
            ],
        },
    )
    print(json.dumps({
        "status": report["status"],
        "integrity_pass": passed,
        "venue_rows": {key: value["rows"] for key, value in venue_reports.items()},
        "holdout_median_daily_rows": report["continuity_context"]["holdout_median_rows"],
        "development_tail_median_daily_rows": report["continuity_context"]["development_tail_median_rows"],
        "labels_predictions_or_metrics_read": False,
    }, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
