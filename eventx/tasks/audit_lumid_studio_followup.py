"""Targeted read-only follow-up probes for the 2026-09-01 Lumid re-audit.

The task tests suspected regressions found by the comprehensive catalog and REST
audits. It uses only non-EventX prediction markets and aggregate metadata queries;
it never reads protected outcomes, EventX labels, or holdout data.
"""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import time
from typing import Any

import httpx

from eventx.settings import ApiSettings


DEFAULT_OUTPUT = Path(
    "data/v2_3_1/lumid_studio_audit_20260901/followup_report.json"
)
KALSHI_SAMPLES = (
    "KXBTC2026200-27JAN01-200000",
    "KXFEDDECISION-26SEP-H0",
)
POLYMARKET_CONTROL = (
    "0x836b850fc838195374862551a36f1c8691d96ff01e58b0a071f0fc1a0e357fb1"
)


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def payload_shape(payload: Any) -> dict[str, Any]:
    if isinstance(payload, list):
        return {
            "kind": "list",
            "rows": len(payload),
            "first_keys": sorted(payload[0])
            if payload and isinstance(payload[0], dict)
            else [],
        }
    if isinstance(payload, dict):
        return {"kind": "object", "keys": sorted(payload)}
    return {"kind": type(payload).__name__}


def get_probe(client: httpx.Client, name: str, path: str) -> dict[str, Any]:
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
                "exception": type(exc).__name__,
                "message": str(exc)[:500],
                "elapsed_seconds": time.perf_counter() - started,
            }
        )
        return result
    result.update(
        {
            "status_code": response.status_code,
            "content_type": response.headers.get("content-type"),
            "elapsed_seconds": time.perf_counter() - started,
        }
    )
    try:
        payload = response.json()
    except (ValueError, json.JSONDecodeError):
        result["text_preview"] = response.text[:500]
        return result
    result["shape"] = payload_shape(payload)
    if not response.is_success:
        result["detail"] = str(payload.get("detail"))[:500] if isinstance(payload, dict) else None
    if name in {"health", "news_stats", "lineage_runs"}:
        result["payload"] = payload
    return result


def retrieve_probe(
    client: httpx.Client,
    *,
    name: str,
    sql: str,
    capture_aggregate_rows: bool = False,
) -> dict[str, Any]:
    started = time.perf_counter()
    result: dict[str, Any] = {
        "name": name,
        "sql": sql,
        "sql_sha256": hashlib.sha256(sql.encode()).hexdigest(),
        "select_only": sql.lstrip().upper().startswith(("SELECT", "WITH")),
    }
    try:
        response = client.post(
            "/retrieve", json={"sql": sql, "output_format": "jsonl"}
        )
    except httpx.HTTPError as exc:
        result.update(
            {
                "exception": type(exc).__name__,
                "message": str(exc)[:500],
                "elapsed_seconds": time.perf_counter() - started,
            }
        )
        return result
    result["status_code"] = response.status_code
    result["elapsed_seconds"] = time.perf_counter() - started
    try:
        receipt = response.json()
    except (ValueError, json.JSONDecodeError):
        result["text_preview"] = response.text[:500]
        return result
    if not response.is_success:
        result["detail"] = str(receipt.get("detail"))[:1000]
        return result
    result["receipt"] = {
        key: value
        for key, value in receipt.items()
        if key
        in {
            "output_format",
            "rowcount",
            "run_id",
            "size_bytes",
            "replay_latency_ms",
        }
    }
    uri = receipt.get("materialized_uri")
    if not isinstance(uri, str) or not uri:
        return result
    download = client.get(uri)
    result["download_status_code"] = download.status_code
    result["download_sha256"] = hashlib.sha256(download.content).hexdigest()
    lines = [line for line in download.content.splitlines() if line.strip()]
    result["downloaded_rows"] = len(lines)
    if capture_aggregate_rows:
        result["aggregate_rows"] = [json.loads(line) for line in lines]
    return result


def openapi_summary(openapi: Any) -> dict[str, Any]:
    paths = openapi.get("paths", {}) if isinstance(openapi, dict) else {}
    operations: list[dict[str, Any]] = []
    for path, path_item in paths.items():
        if not isinstance(path_item, dict):
            continue
        for method, operation in path_item.items():
            if method.lower() in {"get", "post", "put", "patch", "delete"} and isinstance(operation, dict):
                operations.append(operation)
    latest = paths.get("/news/latest", {}).get("get", {})
    latest_limit = next(
        (
            item
            for item in latest.get("parameters", [])
            if item.get("name") == "limit"
        ),
        {},
    )
    return {
        "paths": len(paths),
        "operations": len(operations),
        "operations_only_documenting_200": sum(
            set(operation.get("responses", {})) == {"200"}
            for operation in operations
        ),
        "operations_without_response_content_schema": sum(
            not any(
                isinstance(response, dict) and response.get("content")
                for response in operation.get("responses", {}).values()
            )
            for operation in operations
        ),
        "news_latest_limit_schema": latest_limit.get("schema"),
        "retrieve_documented": "/retrieve" in paths,
        "retrieve_responses": paths.get("/retrieve", {})
        .get("post", {})
        .get("responses"),
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--timeout", type=float, default=65.0)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    settings = ApiSettings.from_env()
    report: dict[str, Any] = {
        "audit_id": "eventx-lumid-studio-followup-20260901",
        "created_at": utc_now(),
        "integrity": {
            "read_only": True,
            "labels_read": [],
            "outcomes_read": [],
            "protected_market_prices_read": [],
            "holdout_accessed": False,
            "prediction_market_samples_outside_frozen_cohort": True,
        },
        "samples": {
            "kalshi": list(KALSHI_SAMPLES),
            "polymarket_control": POLYMARKET_CONTROL,
        },
    }
    with httpx.Client(
        base_url=settings.base_url,
        headers={"Authorization": f"Bearer {settings.token}"},
        timeout=httpx.Timeout(args.timeout),
        follow_redirects=True,
    ) as client:
        print("probe=openapi status=started", flush=True)
        openapi = client.get("/openapi.json").json()
        report["openapi"] = openapi_summary(openapi)
        print("probe=openapi status=completed", flush=True)
        get_paths = [
            ("health", "/health"),
            ("news_stats", "/news/stats"),
            ("lineage_runs", "/catalog/lineage/runs"),
            ("news_latest_limit_negative", "/news/latest?since=2026-08-01T00:00:00Z&limit=-1"),
            ("news_latest_limit_zero", "/news/latest?since=2026-08-01T00:00:00Z&limit=0"),
            ("news_latest_limit_201", "/news/latest?since=2026-08-01T00:00:00Z&limit=201"),
            ("news_latest_limit_5000", "/news/latest?since=2026-08-01T00:00:00Z&limit=5000"),
        ]
        for ticker in KALSHI_SAMPLES:
            get_paths.extend(
                [
                    (f"kalshi_candles_default:{ticker}", f"/prediction-markets/candles/kalshi/{ticker}?limit=10"),
                    (f"kalshi_candles_1d:{ticker}", f"/prediction-markets/candles/kalshi/{ticker}?interval=1d&limit=10"),
                    (f"kalshi_candles_5m:{ticker}", f"/prediction-markets/candles/kalshi/{ticker}?interval=5m&limit=10"),
                ]
            )
        get_paths.extend(
            [
                (
                    "kalshi_candles_bounded",
                    "/prediction-markets/candles/kalshi/"
                    f"{KALSHI_SAMPLES[0]}?interval=1d&from=2026-08-01T00:00:00Z&"
                    "to=2026-09-01T00:00:00Z&limit=100",
                ),
                (
                    "kalshi_candles_unknown_market",
                    "/prediction-markets/candles/kalshi/EVENTX-NONEXISTENT?limit=10",
                ),
                (
                    "polymarket_candles_control",
                    f"/prediction-markets/candles/polymarket/{POLYMARKET_CONTROL}?limit=10",
                ),
            ]
        )
        report["get_probes"] = []
        for name, path in get_paths:
            print(f"probe={name} status=started", flush=True)
            result = get_probe(client, name, path)
            report["get_probes"].append(result)
            print(
                f"probe={name} status=completed "
                f"http={result.get('status_code')} "
                f"exception={result.get('exception')}",
                flush=True,
            )

        retrieve_specs = [
            {
                "name": "basic_select",
                "sql": "SELECT 1::integer AS ok",
            },
            {
                "name": "ordered_news_ids_limit_1500",
                "sql": "SELECT id FROM news.articles ORDER BY id LIMIT 1500",
            },
            {
                "name": "unbounded_news_full_text_count",
                "sql": (
                    "SELECT COUNT(*)::bigint AS rows FROM news.articles "
                    "WHERE search_tsv @@ plainto_tsquery('english', 'clarity act')"
                ),
            },
            {
                "name": "provenance_runs_summary",
                "sql": (
                    "SELECT COUNT(*)::bigint AS total, MIN(started_at) AS earliest, "
                    "MAX(started_at) AS latest, "
                    "COUNT(*) FILTER (WHERE started_at >= CURRENT_TIMESTAMP - "
                    "INTERVAL '30 days')::bigint AS last_30d "
                    "FROM provenance.runs"
                ),
                "capture_aggregate_rows": True,
            },
            {
                "name": "future_news_summary",
                "sql": (
                    "SELECT category, source, source_endpoint, COUNT(*)::bigint AS rows, "
                    "MIN(published_at) AS earliest_published_at, "
                    "MAX(published_at) AS latest_published_at, "
                    "MIN(ingest_ts) AS earliest_ingest_ts, "
                    "MAX(ingest_ts) AS latest_ingest_ts "
                    "FROM news.articles WHERE published_at > "
                    "CURRENT_TIMESTAMP + INTERVAL '1 day' "
                    "GROUP BY category, source, source_endpoint "
                    "ORDER BY rows DESC LIMIT 100"
                ),
                "capture_aggregate_rows": True,
            },
        ]
        report["retrieve_probes"] = []
        for spec in retrieve_specs:
            print(f"probe=retrieve:{spec['name']} status=started", flush=True)
            result = retrieve_probe(
                client,
                name=spec["name"],
                sql=spec["sql"],
                capture_aggregate_rows=spec.get("capture_aggregate_rows", False),
            )
            report["retrieve_probes"].append(result)
            print(
                f"probe=retrieve:{spec['name']} status=completed "
                f"http={result.get('status_code')} "
                f"exception={result.get('exception')}",
                flush=True,
            )

    args.output.parent.mkdir(parents=True, exist_ok=True)
    temporary = args.output.with_suffix(args.output.suffix + ".tmp")
    temporary.write_text(
        json.dumps(report, indent=2, sort_keys=True, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    temporary.replace(args.output)
    print(f"report={args.output}")


if __name__ == "__main__":
    main()
