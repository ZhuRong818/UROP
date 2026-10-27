"""Audit Lumid ingestion-run timestamps for historical EventX news availability.

This task is label-blind. It joins ``news.articles.source_run_id`` to
``provenance.runs.run_id`` through Lumid's read-only ``POST /retrieve`` endpoint and
tests a conservative availability clock based on the article and ingestion-run
timestamps.  The clock is the maximum of publication, row ingestion, run start, and
run end (when present).  A missing run end is therefore allowed, but an unmatched run
or a row timestamp before its run start fails closed.
It never reads prediction-market outcomes, labels, prices, predictions, or metrics.
"""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
import os
from pathlib import Path
from typing import Any

import httpx

from eventx.settings import ApiSettings, REPO_ROOT
from eventx.tasks.export_v3_historical_feasibility import (
    compact_receipt,
    download,
    parse_utc,
    retrieve_with_retry,
    rfc3339,
    sha256_file,
)


DEFAULT_PROTOCOL = REPO_ROOT / "eventx/release/v3_historical/feasibility_protocol.json"
DEFAULT_OUTPUT = REPO_ROOT / "data/v3_historical/provenance_audit_v2"


def atomic_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(
        json.dumps(value, indent=2, sort_keys=True, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    os.replace(temporary, path)


def relative(path: Path) -> str:
    try:
        return str(path.resolve().relative_to(REPO_ROOT))
    except ValueError:
        return str(path.resolve())


def build_sql(start: str, end: str) -> str:
    return f"""WITH candidate AS (
    SELECT id, published_at, ingest_ts, source, source_endpoint, source_run_id
    FROM news.articles
    WHERE published_at IS NOT NULL
      AND ingest_ts IS NOT NULL
      AND published_at >= TIMESTAMPTZ '{start}' - INTERVAL '24 hours'
      AND published_at < TIMESTAMPTZ '{end}'
      AND ingest_ts >= TIMESTAMPTZ '{start}'
      AND ingest_ts < TIMESTAMPTZ '{end}'
      AND ingest_ts >= published_at
      AND ingest_ts <= published_at + INTERVAL '24 hours'
), joined AS (
    SELECT c.*, r.run_id, r.started_at, r.ended_at, r.status,
           GREATEST(
               c.published_at,
               c.ingest_ts,
               r.started_at,
               COALESCE(r.ended_at, c.ingest_ts)
           ) AS conservative_available_at
    FROM candidate c
    LEFT JOIN provenance.runs r ON r.run_id = c.source_run_id
), grouped AS (
    SELECT COALESCE(source, '<missing>') AS source,
           COALESCE(source_endpoint, '<missing>') AS source_endpoint,
           COUNT(*)::bigint AS candidate_rows,
           COUNT(*) FILTER (WHERE source_run_id IS NULL)::bigint AS missing_source_run_id,
           COUNT(*) FILTER (WHERE run_id IS NULL)::bigint AS unmatched_source_run_id,
           COUNT(*) FILTER (WHERE ended_at IS NULL)::bigint AS missing_run_ended_at,
           COUNT(*) FILTER (WHERE started_at IS NULL)::bigint AS missing_run_started_at,
           COUNT(*) FILTER (WHERE ended_at < started_at)::bigint AS ended_before_started,
           COUNT(*) FILTER (WHERE ended_at < ingest_ts)::bigint AS ended_before_ingest,
           COUNT(*) FILTER (WHERE ingest_ts < started_at)::bigint AS ingest_before_run_start,
           COUNT(*) FILTER (WHERE ended_at < published_at)::bigint AS ended_before_publication,
           COUNT(*) FILTER (
               WHERE conservative_available_at < TIMESTAMPTZ '{start}'
                  OR conservative_available_at >= TIMESTAMPTZ '{end}'
           )::bigint AS provenance_available_outside_window,
           COUNT(*) FILTER (
               WHERE conservative_available_at > published_at + INTERVAL '24 hours'
           )::bigint AS provenance_lag_over_24h,
           COUNT(*) FILTER (
               WHERE run_id IS NOT NULL
                 AND started_at IS NOT NULL
                 AND ingest_ts >= started_at
                 AND (ended_at IS NULL OR ended_at >= started_at)
                 AND conservative_available_at >= TIMESTAMPTZ '{start}'
                 AND conservative_available_at < TIMESTAMPTZ '{end}'
                 AND conservative_available_at <= published_at + INTERVAL '24 hours'
           )::bigint AS final_point_in_time_rows,
           MIN(started_at) AS min_run_started_at,
           MAX(ended_at) AS max_run_ended_at,
           MIN(EXTRACT(EPOCH FROM (ended_at - ingest_ts))) AS min_end_minus_ingest_seconds,
           MAX(EXTRACT(EPOCH FROM (ended_at - ingest_ts))) AS max_end_minus_ingest_seconds,
           STRING_AGG(DISTINCT COALESCE(status, '<missing>'), ',' ORDER BY COALESCE(status, '<missing>')) AS run_statuses
    FROM joined
    GROUP BY source, source_endpoint
)
SELECT * FROM grouped
UNION ALL
SELECT '__all__' AS source,
       '__all__' AS source_endpoint,
       SUM(candidate_rows)::bigint,
       SUM(missing_source_run_id)::bigint,
       SUM(unmatched_source_run_id)::bigint,
       SUM(missing_run_ended_at)::bigint,
       SUM(missing_run_started_at)::bigint,
       SUM(ended_before_started)::bigint,
       SUM(ended_before_ingest)::bigint,
       SUM(ingest_before_run_start)::bigint,
       SUM(ended_before_publication)::bigint,
       SUM(provenance_available_outside_window)::bigint,
       SUM(provenance_lag_over_24h)::bigint,
       SUM(final_point_in_time_rows)::bigint,
       MIN(min_run_started_at),
       MAX(max_run_ended_at),
       MIN(min_end_minus_ingest_seconds),
       MAX(max_end_minus_ingest_seconds),
       STRING_AGG(DISTINCT run_statuses, ',' ORDER BY run_statuses)
FROM grouped
ORDER BY source, source_endpoint"""


def load_rows(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    with path.open(encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, start=1):
            if not line.strip():
                continue
            value = json.loads(line)
            if not isinstance(value, dict):
                raise ValueError(f"{path}:{line_number} is not an object")
            rows.append(value)
    return rows


def integer(row: dict[str, Any], key: str) -> int:
    return int(row.get(key) or 0)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--protocol", type=Path, default=DEFAULT_PROTOCOL)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--timeout", type=float, default=900.0)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    protocol = json.loads(args.protocol.read_text(encoding="utf-8"))
    if protocol.get("labels_permitted") is not False:
        raise SystemExit("protocol does not preserve label seal")
    if protocol.get("outcomes_permitted") is not False:
        raise SystemExit("protocol does not preserve outcome seal")
    start = rfc3339(parse_utc(protocol["window"]["start_inclusive"]))
    end = rfc3339(parse_utc(protocol["window"]["end_exclusive"]))
    args.output.mkdir(parents=True, exist_ok=True)
    sql = build_sql(start, end)
    query_path = args.output / "query.sql"
    data_path = args.output / "result.jsonl"
    receipt_path = args.output / "retrieve_receipt.json"
    query_path.write_text(sql + "\n", encoding="utf-8")

    settings = ApiSettings.from_env()
    with httpx.Client(
        base_url=settings.base_url,
        headers={"Authorization": f"Bearer {settings.token}"},
        timeout=httpx.Timeout(args.timeout),
        follow_redirects=True,
    ) as client:
        receipt, retry_ledger = retrieve_with_retry(
            client, sql, attempts=3, delays=[10.0, 30.0, 120.0]
        )
        download(client, str(receipt["materialized_uri"]), data_path)
    atomic_json(
        receipt_path,
        {"receipt": compact_receipt(receipt), "retry_ledger": retry_ledger},
    )

    rows = load_rows(data_path)
    aggregate = next(
        (row for row in rows if row.get("source") == "__all__"), None
    )
    if aggregate is None:
        raise RuntimeError("provenance audit returned no aggregate row")
    required_zero = (
        "missing_source_run_id",
        "unmatched_source_run_id",
        "missing_run_started_at",
        "ended_before_started",
        "ingest_before_run_start",
        "provenance_available_outside_window",
    )
    gates = {
        "candidate_rows_nonzero": integer(aggregate, "candidate_rows") > 0,
        "complete_source_run_join": all(
            integer(aggregate, key) == 0
            for key in ("missing_source_run_id", "unmatched_source_run_id")
        ),
        "complete_run_start_timestamps": integer(
            aggregate, "missing_run_started_at"
        )
        == 0,
        "valid_required_timestamp_ordering": all(
            integer(aggregate, key) == 0
            for key in (
                "ended_before_started",
                "ingest_before_run_start",
            )
        ),
        "final_point_in_time_rows_nonzero": integer(
            aggregate, "final_point_in_time_rows"
        )
        > 0,
        "final_rows_within_window": integer(
            aggregate, "provenance_available_outside_window"
        )
        == 0,
    }
    report = {
        "artifacts": {
            "query": {
                "bytes": query_path.stat().st_size,
                "path": relative(query_path),
                "sha256": sha256_file(query_path),
            },
            "result": {
                "bytes": data_path.stat().st_size,
                "path": relative(data_path),
                "sha256": sha256_file(data_path),
            },
            "retrieve_receipt": {
                "bytes": receipt_path.stat().st_size,
                "path": relative(receipt_path),
                "sha256": sha256_file(receipt_path),
            },
        },
        "audited_at": rfc3339(datetime.now(timezone.utc)),
        "availability_candidate": (
            "max(published_at, ingest_ts, provenance.runs.started_at, "
            "provenance.runs.ended_at when present)"
        ),
        "availability_filter": (
            "exclude rows whose conservative available_at is more than 24 hours "
            "after published_at; missing run end is allowed only when the source-run "
            "join and run start checks pass"
        ),
        "by_source_endpoint": [
            row for row in rows if row.get("source") != "__all__"
        ],
        "gates": gates,
        "integrity_pass": all(gates.values()),
        "label_blind": True,
        "labels_or_outcomes_read": False,
        "semantics_conclusion": (
            "source_run_id is complete and ingest_ts never precedes its joined run "
            "start; the conservative maximum clock cannot place a row before its "
            "observed Lumid ingestion run"
        ),
        "protocol_id": protocol["protocol_id"],
        "required_zero_fields": {
            key: integer(aggregate, key) for key in required_zero
        },
        "summary": aggregate,
        "window": protocol["window"],
    }
    report_path = args.output / "report.json"
    atomic_json(report_path, report)
    print(json.dumps(report, indent=2, sort_keys=True))
    if not report["integrity_pass"]:
        raise SystemExit("historical provenance audit failed")


if __name__ == "__main__":
    main()
