"""Continuously materialize sealed daily Lumid inputs for EventX v4."""

from __future__ import annotations

import argparse
from datetime import datetime, timedelta, timezone
import json
import os
from pathlib import Path
import time
from typing import Any, Iterator

import httpx

from eventx.settings import ApiSettings, REPO_ROOT
from eventx.tasks.audit_v3_historical_feasibility import parse_utc
from eventx.tasks.export_v3_historical_feasibility import (
    compact_receipt,
    download,
    retrieve_with_retry,
    sha256_file,
    sql_literal,
)


PROTOCOL = REPO_ROOT / "eventx/release/v4/protocol.json"
COHORT = REPO_ROOT / "data/v4/confirmatory/cohort_gate/cohort.jsonl"
OUTPUT = REPO_ROOT / "data/v4/confirmatory/sealed_inputs"
STATE = OUTPUT / "collector_state.json"
LOCK = OUTPUT / "collector.lock"
LOGICAL_NEWS_START = parse_utc("2026-08-30T00:00:00Z")
TRADE_START = parse_utc("2026-09-06T00:00:00Z")
END = parse_utc("2026-10-30T00:00:00Z")
BATCH_SIZE = 50


def rfc3339(value: datetime) -> str:
    return value.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


def atomic_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n")
    os.replace(temporary, path)


def read_jsonl(path: Path) -> Iterator[dict[str, Any]]:
    with path.open(encoding="utf-8") as handle:
        for line in handle:
            if line.strip():
                yield json.loads(line)


def batches(values: list[Any], size: int = BATCH_SIZE) -> Iterator[list[Any]]:
    for start in range(0, len(values), size):
        yield values[start : start + size]


def news_sql(start: datetime, end: datetime) -> str:
    return f"""SELECT a.id, a.published_at, a.ingest_ts, a.symbol,
       a.related_symbols, a.publisher, a.author, a.category, a.headline,
       a.summary, a.url, a.source, a.source_endpoint, a.source_run_id,
       r.started_at AS run_started_at, r.ended_at AS run_ended_at,
       r.status AS run_status
FROM news.articles a
JOIN provenance.runs r ON r.run_id = a.source_run_id
WHERE a.ingest_ts >= TIMESTAMPTZ '{rfc3339(start)}'
  AND a.ingest_ts < TIMESTAMPTZ '{rfc3339(end)}'
  AND a.published_at >= TIMESTAMPTZ '{rfc3339(start - timedelta(days=1))}'
  AND a.published_at < TIMESTAMPTZ '{rfc3339(end)}'
  AND a.ingest_ts >= a.published_at
  AND a.ingest_ts <= a.published_at + INTERVAL '24 hours'
  AND a.ingest_ts >= r.started_at
  AND (r.ended_at IS NULL OR r.ended_at >= r.started_at)
ORDER BY a.id"""


def trade_sql(start: datetime, end: datetime, pairs: list[tuple[str, str]]) -> str:
    keys = ", ".join(
        f"({sql_literal(condition)}, {sql_literal(asset)})"
        for condition, asset in pairs
    )
    return f"""SELECT condition_id, asset_id, trade_id, ts, price, size
FROM prediction_markets.polymarket_trades
WHERE ts >= TIMESTAMPTZ '{rfc3339(start)}'
  AND ts < TIMESTAMPTZ '{rfc3339(end)}'
  AND trade_id IS NOT NULL
  AND price BETWEEN 0 AND 1
  AND size > 0
  AND (condition_id, COALESCE(asset_id, '')) IN ({keys})
ORDER BY condition_id, asset_id, ts, trade_id"""


def materialize(
    client: httpx.Client, kind: str, day: datetime, name: str, sql: str
) -> dict[str, Any]:
    root = OUTPUT / kind / day.date().isoformat()
    data = root / f"{name}.jsonl"
    receipt_path = root / f"{name}_receipt.json"
    sql_path = root / f"{name}.sql"
    if data.exists() and receipt_path.exists() and sql_path.exists():
        return {"status": "already_materialized", "path": str(data.relative_to(REPO_ROOT))}
    root.mkdir(parents=True, exist_ok=True)
    sql_path.write_text(sql + "\n", encoding="utf-8")
    receipt, ledger = retrieve_with_retry(client, sql, attempts=1, delays=[])
    download(client, str(receipt["materialized_uri"]), data)
    if data.stat().st_size < 0:
        raise RuntimeError("impossible materialized file size")
    atomic_json(receipt_path, {
        "receipt": compact_receipt(receipt),
        "retry_ledger": ledger,
        "data_sha256": sha256_file(data),
        "sql_sha256": sha256_file(sql_path),
    })
    return {
        "status": "materialized",
        "path": str(data.relative_to(REPO_ROOT)),
        "rowcount": int(receipt.get("rowcount") or 0),
    }


def initial_state() -> dict[str, Any]:
    return {
        "protocol_id": "eventx-v4-confirmatory-polymarket-20260902",
        "status": "collecting_sealed_inputs",
        "next_news_day": rfc3339(LOGICAL_NEWS_START),
        "next_trade_day": rfc3339(TRADE_START),
        "completed_news_days": 0,
        "completed_trade_days": 0,
        "last_success_at": None,
        "last_error": None,
        "labels_predictions_or_metrics_computed": False,
    }


def collect_available_days(client: httpx.Client, state: dict[str, Any]) -> bool:
    now = datetime.now(timezone.utc)
    today = datetime(now.year, now.month, now.day, tzinfo=timezone.utc)
    progressed = False
    news_day = parse_utc(str(state["next_news_day"]))
    while news_day < min(today, END):
        materialize(
            client,
            "news",
            news_day,
            "articles",
            news_sql(news_day, news_day + timedelta(days=1)),
        )
        news_day += timedelta(days=1)
        state["next_news_day"] = rfc3339(news_day)
        state["completed_news_days"] += 1
        state["last_success_at"] = rfc3339(datetime.now(timezone.utc))
        state["last_error"] = None
        atomic_json(STATE, state)
        progressed = True
        print(f"sealed v4 news through {state['next_news_day']}", flush=True)

    trade_day = parse_utc(str(state["next_trade_day"]))
    cohort = list(read_jsonl(COHORT))
    pairs = [
        (str(row["market_id"]), str(row["canonical_yes_asset_id"]))
        for row in cohort
    ]
    while trade_day < min(today, END):
        for number, group in enumerate(batches(pairs), start=1):
            materialize(
                client,
                "trades",
                trade_day,
                f"batch_{number:03d}",
                trade_sql(trade_day, trade_day + timedelta(days=1), group),
            )
        trade_day += timedelta(days=1)
        state["next_trade_day"] = rfc3339(trade_day)
        state["completed_trade_days"] += 1
        state["last_success_at"] = rfc3339(datetime.now(timezone.utc))
        state["last_error"] = None
        atomic_json(STATE, state)
        progressed = True
        print(f"sealed v4 trades through {state['next_trade_day']}", flush=True)
    if news_day >= END and trade_day >= END:
        state["status"] = "sealed_collection_complete_pending_data_gate"
        atomic_json(STATE, state)
    return progressed


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--continuous", action="store_true")
    args = parser.parse_args()
    protocol = json.loads(PROTOCOL.read_text(encoding="utf-8"))
    if protocol.get("protocol_id") != "eventx-v4-confirmatory-polymarket-20260902":
        raise SystemExit("wrong v4 protocol")
    OUTPUT.mkdir(parents=True, exist_ok=True)
    if LOCK.exists():
        raise SystemExit("v4 collector lock exists")
    atomic_json(LOCK, {"pid": os.getpid(), "started_at": rfc3339(datetime.now(timezone.utc))})
    state = json.loads(STATE.read_text()) if STATE.exists() else initial_state()
    settings = ApiSettings.from_env()
    try:
        with httpx.Client(
            base_url=settings.base_url,
            headers={"Authorization": f"Bearer {settings.token}"},
            timeout=httpx.Timeout(1800.0),
            follow_redirects=True,
        ) as client:
            while True:
                try:
                    collect_available_days(client, state)
                except Exception as exc:
                    state["last_error"] = {
                        "at": rfc3339(datetime.now(timezone.utc)),
                        "type": type(exc).__name__,
                        "message": str(exc)[:1000],
                    }
                    atomic_json(STATE, state)
                    if not args.continuous:
                        raise
                if not args.continuous or state["status"] != "collecting_sealed_inputs":
                    break
                time.sleep(60)
    finally:
        if LOCK.exists():
            LOCK.unlink()
    print(json.dumps(state, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
