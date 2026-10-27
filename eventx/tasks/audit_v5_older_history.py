"""Label-blind probe for usable Lumid history before 17 May 2026.

Only aggregate source-coverage metadata are requested. The task does not retrieve
trade prices, construct labels, or inspect prediction-market outcomes.
"""

from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
from typing import Any

import httpx

from eventx.settings import ApiSettings, REPO_ROOT
from eventx.tasks.audit_lumid_studio_warehouse import materialize
from eventx.tasks.prepare_v3_1_historical_development_arrays import sha256_file


CUTOFF = "2026-05-17T00:00:00Z"
OUTPUT = REPO_ROOT / "data/v5/label_blind/older_history_probe"
REPORT = OUTPUT / "report.json"
MANIFEST = OUTPUT / "manifest.json"
QUERIES = {
    "news_summary": f"""SELECT MIN(published_at) AS min_published_at,
       MIN(ingest_ts) AS min_ingest_ts,
       MAX(ingest_ts) FILTER (WHERE ingest_ts < TIMESTAMPTZ '{CUTOFF}') AS max_pre_cutoff_ingest,
       COUNT(*) FILTER (WHERE published_at < TIMESTAMPTZ '{CUTOFF}') AS pre_cutoff_published_rows,
       COUNT(*) FILTER (WHERE ingest_ts < TIMESTAMPTZ '{CUTOFF}') AS pre_cutoff_available_rows
FROM news.articles""",
    "news_pre_cutoff_months": f"""SELECT DATE_TRUNC('month', ingest_ts) AS month,
       COUNT(*) AS rows,
       COUNT(DISTINCT id) AS unique_ids,
       COUNT(DISTINCT source_endpoint) AS source_endpoints
FROM news.articles
WHERE ingest_ts < TIMESTAMPTZ '{CUTOFF}'
GROUP BY 1
ORDER BY 1""",
    "kalshi_trade_summary": f"""SELECT MIN(created_time) AS min_trade_time,
       MAX(created_time) FILTER (WHERE created_time < TIMESTAMPTZ '{CUTOFF}') AS max_pre_cutoff_trade_time,
       COUNT(*) FILTER (WHERE created_time < TIMESTAMPTZ '{CUTOFF}') AS pre_cutoff_rows,
       COUNT(DISTINCT ticker) FILTER (WHERE created_time < TIMESTAMPTZ '{CUTOFF}') AS pre_cutoff_markets
FROM prediction_markets.kalshi_trades""",
    "polymarket_trade_summary": f"""SELECT MIN(ts) AS min_trade_time,
       MAX(ts) FILTER (WHERE ts < TIMESTAMPTZ '{CUTOFF}') AS max_pre_cutoff_trade_time,
       COUNT(*) FILTER (WHERE ts < TIMESTAMPTZ '{CUTOFF}') AS pre_cutoff_rows,
       COUNT(DISTINCT condition_id) FILTER (WHERE ts < TIMESTAMPTZ '{CUTOFF}') AS pre_cutoff_markets
FROM prediction_markets.polymarket_trades""",
    "kalshi_metadata_summary": f"""SELECT MIN(ingest_ts) AS min_ingest_ts,
       COUNT(*) FILTER (WHERE ingest_ts < TIMESTAMPTZ '{CUTOFF}') AS pre_cutoff_rows,
       COUNT(DISTINCT ticker) FILTER (WHERE ingest_ts < TIMESTAMPTZ '{CUTOFF}') AS pre_cutoff_markets
FROM prediction_markets.kalshi_markets""",
    "polymarket_metadata_summary": f"""SELECT MIN(ingest_ts) AS min_ingest_ts,
       COUNT(*) FILTER (WHERE ingest_ts < TIMESTAMPTZ '{CUTOFF}') AS pre_cutoff_rows,
       COUNT(DISTINCT condition_id) FILTER (WHERE ingest_ts < TIMESTAMPTZ '{CUTOFF}') AS pre_cutoff_markets
FROM prediction_markets.polymarket_markets""",
}


def atomic_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n")
    os.replace(temporary, path)


def relative(path: Path) -> str:
    return str(path.relative_to(REPO_ROOT))


def main() -> None:
    if REPORT.exists() or MANIFEST.exists():
        raise SystemExit("older-history probe already exists")
    settings = ApiSettings.from_env()
    results: dict[str, Any] = {}
    with httpx.Client(
        base_url=settings.base_url,
        headers={"Authorization": f"Bearer {settings.token}"},
        timeout=httpx.Timeout(300.0),
        follow_redirects=True,
    ) as client:
        for name, sql in QUERIES.items():
            result = materialize(
                client,
                name=name,
                sql=sql,
                output_format="jsonl",
                download_limit_bytes=2_000_000,
                capture_jsonl_rows=True,
            )
            results[name] = result
            print(
                json.dumps(
                    {
                        "query": name,
                        "submit_status": result.get("submit", {}).get("status_code"),
                        "rows": result.get("downloaded_rows"),
                        "exception": result.get("exception") or result.get("download_exception"),
                    },
                    sort_keys=True,
                ),
                flush=True,
            )
    successful = all(
        result.get("submit", {}).get("status_code") == 200
        and result.get("download_status_code") == 200
        and result.get("jsonl_parse_failures") == 0
        for result in results.values()
    )
    report = {
        "audit_id": "eventx-v5-older-history-label-blind-probe-20260903",
        "created_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "status": "complete" if successful else "incomplete",
        "cutoff": CUTOFF,
        "purpose": "test whether an older unused point-in-time interval exists",
        "labels_or_outcomes_read": False,
        "trade_prices_read": False,
        "future_v4_data_read": False,
        "queries": {
            name: {
                "sql": sql,
                "sql_sha256": hashlib.sha256(sql.encode("utf-8")).hexdigest(),
                "result": results[name],
            }
            for name, sql in QUERIES.items()
        },
    }
    atomic_json(REPORT, report)
    atomic_json(
        MANIFEST,
        {
            "audit_id": report["audit_id"],
            "status": report["status"],
            "artifacts": [
                {"path": relative(path), "sha256": sha256_file(path)}
                for path in (REPORT, Path(__file__).resolve())
            ],
        },
    )
    print(json.dumps({"status": report["status"], "report": relative(REPORT)}))


if __name__ == "__main__":
    main()
