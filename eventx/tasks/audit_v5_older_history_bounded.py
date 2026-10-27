"""Bounded follow-up for older Lumid trade and metadata coverage.

The initial aggregate scan established zero news ingestion before 17 May 2026 but
timed out on three large prediction-market tables. This follow-up uses narrow indexed
windows and returns only counts/boundary records; no prices or labels are selected.
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


START = "2026-01-01T00:00:00Z"
CUTOFF = "2026-05-17T00:00:00Z"
RECENT_START = "2026-05-01T00:00:00Z"
OUTPUT = REPO_ROOT / "data/v5/label_blind/older_history_probe_bounded"
REPORT = OUTPUT / "report.json"
MANIFEST = OUTPUT / "manifest.json"
QUERIES = {
    "kalshi_2026_boundary": f"""SELECT MIN(created_time) AS first_time,
       MAX(created_time) AS last_time, COUNT(*) AS rows,
       COUNT(DISTINCT ticker) AS markets
FROM prediction_markets.kalshi_trades
WHERE created_time >= TIMESTAMPTZ '{START}'
  AND created_time < TIMESTAMPTZ '{CUTOFF}'""",
    "polymarket_2026_boundary": f"""SELECT MIN(ts) AS first_time,
       MAX(ts) AS last_time, COUNT(*) AS rows,
       COUNT(DISTINCT condition_id) AS markets
FROM prediction_markets.polymarket_trades
WHERE ts >= TIMESTAMPTZ '{START}'
  AND ts < TIMESTAMPTZ '{CUTOFF}'""",
    "kalshi_may_boundary": f"""SELECT MIN(created_time) AS first_time,
       MAX(created_time) AS last_time, COUNT(*) AS rows,
       COUNT(DISTINCT ticker) AS markets
FROM prediction_markets.kalshi_trades
WHERE created_time >= TIMESTAMPTZ '{RECENT_START}'
  AND created_time < TIMESTAMPTZ '{CUTOFF}'""",
    "polymarket_may_boundary": f"""SELECT MIN(ts) AS first_time,
       MAX(ts) AS last_time, COUNT(*) AS rows,
       COUNT(DISTINCT condition_id) AS markets
FROM prediction_markets.polymarket_trades
WHERE ts >= TIMESTAMPTZ '{RECENT_START}'
  AND ts < TIMESTAMPTZ '{CUTOFF}'""",
    "kalshi_pre_cutoff_metadata": f"""SELECT ticker, ingest_ts
FROM prediction_markets.kalshi_markets
WHERE ingest_ts < TIMESTAMPTZ '{CUTOFF}'
ORDER BY ingest_ts DESC
LIMIT 1""",
    "polymarket_pre_cutoff_metadata": f"""SELECT condition_id, ingest_ts
FROM prediction_markets.polymarket_markets
WHERE ingest_ts < TIMESTAMPTZ '{CUTOFF}'
ORDER BY ingest_ts DESC
LIMIT 1""",
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
        raise SystemExit("bounded older-history probe already exists")
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
                download_limit_bytes=200_000,
                capture_jsonl_rows=True,
            )
            results[name] = result
            print(
                json.dumps(
                    {
                        "query": name,
                        "submit_status": result.get("submit", {}).get("status_code"),
                        "rows": result.get("downloaded_rows"),
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
        "audit_id": "eventx-v5-older-history-bounded-probe-20260903",
        "created_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "status": "complete" if successful else "incomplete",
        "window": {"start_inclusive": START, "end_exclusive": CUTOFF},
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
