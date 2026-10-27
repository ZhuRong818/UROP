"""Probe representative Lumid FinData REST features without mutating state.

This is a black-box read audit. It records status, latency, response shape and
freshness indicators, never raw rows. No DDL/DML, labels, outcomes or holdout data
are accessed.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import httpx

from eventx.settings import ApiSettings


DEFAULT_OUTPUT = Path("data/v2_3_1/lumid_studio_audit_20260829/rest_report.json")
KALSHI_TICKER = "KXBTC2026200-27JAN01-200000"
POLYMARKET_CONDITION = "0x836b850fc838195374862551a36f1c8691d96ff01e58b0a071f0fc1a0e357fb1"
FROZEN_EVENTX_MARKETS = {
    "KXGOVFLNOMR-26-JFIS",
    "CONTROLH-2026-R",
    "KXBALANCEPOWERCOMBO-27FEB-DD",
    "SENATEME-26-D",
    "0x8e1e5c26dec73aee98230dc0ef93a294142587ca24190c4728d4b7ff831a22e0",
    "0x5db999fad322cea2914535aae5517060c3f80ad6d8c0231cde2124a434d16846",
    "0x6557ff312837c0707d82bc2def893572289e012cff21a264593c6551f85d7e50",
    "0xe51b0cdb413eb9a18243e70c1f33705cdab18f4149b867f32f05650e758d8070",
    "0x9cb23d04b2ded06147482076688b69b487a8d982c63ebdda2ab3678cf27cf390",
    "0xdf8e2dc5860027decbe6164555c3c1c9645c3bd33e16b9dc57ca87125047d4a8",
    "0x1a01bf78f56a507fcb666d564d8c8b91b0750679163ed6e96746102c9b7d285d",
    "0x25fb28382075f418a944a781a9f8840e2f541152eea0d9798d1cabfa1466adbb",
    "0x67f3f8d0a0ecdfc008c99650284a4674388a8c3029b0eb7ca0abd65dde8d996f",
    "0x12dc2b61723b2a54fc1947a307389b5f32038e7a29a0e936ad1fe410b969d06a",
}


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def payload_summary(payload: Any) -> dict[str, Any]:
    if isinstance(payload, list):
        return {
            "kind": "list",
            "rows": len(payload),
            "first_keys": sorted(payload[0]) if payload and isinstance(payload[0], dict) else [],
            "empty": not payload,
        }
    if isinstance(payload, dict):
        result: dict[str, Any] = {
            "kind": "object",
            "keys": sorted(str(key) for key in payload),
        }
        for key in ("data", "items", "results", "trades", "markets", "events", "tweets"):
            value = payload.get(key)
            if isinstance(value, list):
                result["row_container"] = key
                result["rows"] = len(value)
                result["first_keys"] = (
                    sorted(value[0]) if value and isinstance(value[0], dict) else []
                )
                result["empty"] = not value
                break
        for key in (
            "as_of",
            "generated_at",
            "updated_at",
            "latest_ts",
            "oldest_ts",
            "min_ts",
            "max_ts",
        ):
            if key in payload and payload[key] is not None:
                result[key] = str(payload[key])
        return result
    return {"kind": type(payload).__name__}


def probe(client: httpx.Client, name: str, path: str) -> dict[str, Any]:
    started = time.perf_counter()
    result: dict[str, Any] = {
        "name": name,
        "path": path,
        "path_sha256": hashlib.sha256(path.encode()).hexdigest(),
    }
    try:
        response = client.get(path)
    except httpx.HTTPError as exc:
        result.update(
            {
                "status": "exception",
                "exception": type(exc).__name__,
                "message": str(exc)[:300],
                "elapsed_seconds": time.perf_counter() - started,
            }
        )
        return result
    result.update(
        {
            "status": response.status_code,
            "content_type": response.headers.get("content-type"),
            "bytes": len(response.content),
            "elapsed_seconds": time.perf_counter() - started,
        }
    )
    if response.is_success:
        try:
            result["payload"] = payload_summary(response.json())
        except (ValueError, json.JSONDecodeError):
            result["payload"] = {"kind": "non_json"}
    else:
        try:
            detail = response.json().get("detail")
        except (ValueError, json.JSONDecodeError, AttributeError):
            detail = response.text[:300]
        result["error"] = str(detail)[:300]
    return result


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--timeout", type=float, default=20.0)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    settings = ApiSettings.from_env()
    if {KALSHI_TICKER, POLYMARKET_CONDITION} & FROZEN_EVENTX_MARKETS:
        raise SystemExit("REST audit sample overlaps the frozen EventX cohort")
    headers = {"Authorization": f"Bearer {settings.token}"}
    endpoint_paths = [
        ("health", "/health"),
        ("status", "/status"),
        ("freshness", "/freshness"),
        ("news_stats", "/news/stats"),
        ("news_latest_limit_1", "/news/latest?since=2026-08-01T00:00:00Z&limit=1"),
        ("news_latest_limit_200", "/news/latest?since=2026-08-01T00:00:00Z&limit=200"),
        ("news_latest_limit_201", "/news/latest?since=2026-08-01T00:00:00Z&limit=201"),
        ("news_latest_cap_probe", "/news/latest?since=2026-08-01T00:00:00Z&limit=5000"),
        ("news_latest_zero_limit", "/news/latest?since=2026-08-01T00:00:00Z&limit=0"),
        ("news_search", "/news/search?q=clarity%20act&limit=10"),
        ("news_symbol", "/news/AAPL?limit=10"),
        ("news_symbol_sentiment", "/news/symbol-sentiment/AAPL"),
        ("kol_list", "/kols"),
        ("kol_archive_stats", "/kols/archive/stats"),
        ("kol_search", "/kols/tweets/search?q=clarity&limit=5"),
        ("prediction_events", "/prediction-markets/events?limit=5&status=open"),
        ("prediction_market_search", "/prediction-markets/markets/search?q=House&limit=5"),
        ("kalshi_market_detail", f"/prediction-markets/markets/kalshi/{KALSHI_TICKER}"),
        (
            "kalshi_trades",
            f"/prediction-markets/trades/kalshi/{KALSHI_TICKER}?limit=10",
        ),
        (
            "kalshi_orderbook",
            f"/prediction-markets/orderbook/kalshi/{KALSHI_TICKER}?limit=10",
        ),
        (
            "kalshi_candles",
            f"/prediction-markets/candles/kalshi/{KALSHI_TICKER}?limit=10",
        ),
        (
            "kalshi_open_interest",
            f"/prediction-markets/open-interest/kalshi/{KALSHI_TICKER}?limit=10",
        ),
        (
            "polymarket_market_detail",
            f"/prediction-markets/markets/polymarket/{POLYMARKET_CONDITION}",
        ),
        (
            "polymarket_trades",
            f"/prediction-markets/trades/polymarket/{POLYMARKET_CONDITION}?limit=10",
        ),
        (
            "polymarket_orderbook",
            f"/prediction-markets/orderbook/polymarket/{POLYMARKET_CONDITION}?limit=10",
        ),
        (
            "polymarket_candles",
            f"/prediction-markets/candles/polymarket/{POLYMARKET_CONDITION}?limit=10",
        ),
        (
            "polymarket_open_interest",
            f"/prediction-markets/open-interest/polymarket/{POLYMARKET_CONDITION}?limit=10",
        ),
        ("quotes", "/quotes?symbols=AAPL"),
        ("ohlc", "/ohlc/AAPL?interval=5min&limit=10"),
        ("fundamentals_latest", "/fundamentals/AAPL/latest"),
        ("macro_indicators", "/macro/economic-indicators?limit=5"),
    ]
    report = {
        "audit_id": f"eventx-lumid-studio-rest-read-only-audit-{datetime.now(timezone.utc):%Y%m%d}",
        "created_at": utc_now(),
        "non_frozen_samples": {
            "kalshi": KALSHI_TICKER,
            "polymarket": POLYMARKET_CONDITION,
        },
        "integrity": {
            "read_only": True,
            "ddl_or_dml_issued": False,
            "labels_read": [],
            "outcomes_read": [],
            "trade_prices_read": [],
            "holdout_accessed": False,
        },
    }
    with httpx.Client(
        base_url=settings.base_url,
        headers=headers,
        timeout=httpx.Timeout(args.timeout),
        follow_redirects=True,
    ) as client:
        results = [probe(client, name, path) for name, path in endpoint_paths]
    report["probes"] = results
    report["summary"] = {
        "total": len(results),
        "http_2xx": sum(1 for result in results if isinstance(result.get("status"), int) and 200 <= result["status"] < 300),
        "http_4xx": sum(1 for result in results if isinstance(result.get("status"), int) and 400 <= result["status"] < 500),
        "http_5xx": sum(1 for result in results if isinstance(result.get("status"), int) and result["status"] >= 500),
        "exceptions_or_timeouts": sum(1 for result in results if result.get("status") == "exception"),
        "empty_successes": sum(1 for result in results if result.get("payload", {}).get("empty") is True),
        "slow_over_5s": sum(1 for result in results if result.get("elapsed_seconds", 0) > 5),
        "news_latest_limit_observations": {
            result["name"]: {
                "status": result.get("status"),
                "rows": result.get("payload", {}).get("rows"),
                "error": result.get("error"),
            }
            for result in results
            if result["name"].startswith("news_latest_")
        },
        "non_json_successes": [
            result["name"]
            for result in results
            if isinstance(result.get("status"), int)
            and 200 <= result["status"] < 300
            and result.get("payload", {}).get("kind") == "non_json"
        ],
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(report, indent=2, sort_keys=True, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(report["summary"], indent=2, sort_keys=True))
    print(f"report={args.output}")


if __name__ == "__main__":
    main()
