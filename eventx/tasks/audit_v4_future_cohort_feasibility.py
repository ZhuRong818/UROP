"""Fetch a label-blind feasibility cohort for the proposed v4 future holdout."""

from __future__ import annotations

from collections import Counter
from datetime import datetime, timezone
import json
import os
from pathlib import Path
from typing import Any, Iterator

import httpx

from eventx.settings import ApiSettings, REPO_ROOT
from eventx.tasks.audit_v3_historical_feasibility import parse_json_array, parse_utc
from eventx.tasks.build_v2_1_taxonomy import classify
from eventx.tasks.export_v3_historical_feasibility import (
    compact_receipt,
    download,
    retrieve_with_retry,
    sha256_file,
    sql_literal,
)


OUTPUT = REPO_ROOT / "data/v4/discovery/future_cohort_feasibility"
SELECTION_START = "2026-08-04T00:00:00Z"
SELECTION_END = "2026-09-02T00:00:00Z"
RECENT_AFTER = "2026-09-01T00:00:00Z"
HOLDOUT_START = "2026-09-04T00:00:00Z"
HOLDOUT_END = "2026-10-30T00:00:00Z"


BATCH_SIZE = 250


def relative(path: Path) -> str:
    return str(path.relative_to(REPO_ROOT))


def atomic_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n")
    os.replace(temporary, path)


def atomic_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    temporary = path.with_suffix(path.suffix + ".tmp")
    with temporary.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, sort_keys=True) + "\n")
    os.replace(temporary, path)


def read_jsonl(path: Path) -> Iterator[dict[str, Any]]:
    with path.open(encoding="utf-8") as handle:
        for line in handle:
            if line.strip():
                yield json.loads(line)


def later_timestamp(*values: Any) -> str | None:
    available = [str(value) for value in values if value]
    if not available:
        return None
    return max(available, key=parse_utc)


def materialize(client: httpx.Client, name: str, sql: str) -> dict[str, Any]:
    sql_path = OUTPUT / f"{name}.sql"
    data_path = OUTPUT / f"{name}.jsonl"
    receipt_path = OUTPUT / f"{name}_receipt.json"
    sql_path.write_text(sql + "\n", encoding="utf-8")
    receipt, ledger = retrieve_with_retry(
        client, sql, attempts=3, delays=[10.0, 30.0, 120.0]
    )
    download(client, str(receipt["materialized_uri"]), data_path)
    atomic_json(receipt_path, {"receipt": compact_receipt(receipt), "retry_ledger": ledger})
    rows = list(read_jsonl(data_path))
    if len(rows) != int(receipt.get("rowcount") or 0):
        raise RuntimeError(f"{name} receipt/download row-count mismatch")
    return {
        "rows": rows,
        "artifacts": [
            {"path": relative(path), "sha256": sha256_file(path)}
            for path in (sql_path, data_path, receipt_path)
        ],
    }


def latest_rows(rows: list[dict[str, Any]], key: str) -> list[dict[str, Any]]:
    output: dict[str, dict[str, Any]] = {}
    for row in rows:
        value = str(row.get(key) or "")
        if not value:
            continue
        current = output.get(value)
        if current is None or parse_utc(str(row["ingest_ts"])) > parse_utc(
            str(current["ingest_ts"])
        ):
            output[value] = row
    return [output[value] for value in sorted(output)]


def batches(values: list[Any], size: int = BATCH_SIZE) -> Iterator[list[Any]]:
    for start in range(0, len(values), size):
        yield values[start : start + size]


def active_roster(client: httpx.Client, venue: str) -> dict[str, Any]:
    response = client.get("/api/v1/lqt/markets", params={"venue": venue})
    response.raise_for_status()
    payload = response.json()
    rows = payload.get("markets", [])
    if not isinstance(rows, list):
        raise RuntimeError(f"unexpected active roster for {venue}")
    path = OUTPUT / f"{venue}_active_roster.json"
    atomic_json(path, payload)
    return {
        "rows": rows,
        "as_of_ns": payload.get("as_of_ns"),
        "artifacts": [{"path": relative(path), "sha256": sha256_file(path)}],
    }


def kalshi_metadata_sql(tickers: list[str]) -> str:
    keys = ", ".join(sql_literal(value) for value in tickers)
    return f"""SELECT DISTINCT ON (ticker)
       ticker, event_ticker, title, yes_sub_title, no_sub_title,
       close_time, expiration_time, ingest_ts
FROM prediction_markets.kalshi_markets
WHERE ingest_ts < TIMESTAMPTZ '{SELECTION_END}'
  AND ticker IN ({keys})
ORDER BY ticker, ingest_ts DESC"""


def polymarket_metadata_sql(condition_ids: list[str]) -> str:
    keys = ", ".join(sql_literal(value) for value in condition_ids)
    return f"""SELECT DISTINCT ON (condition_id)
       condition_id, question, slug, outcomes, clob_token_ids, end_date, ingest_ts
FROM prediction_markets.polymarket_markets
WHERE ingest_ts < TIMESTAMPTZ '{SELECTION_END}'
  AND condition_id IN ({keys})
ORDER BY condition_id, ingest_ts DESC"""


def kalshi_activity_sql(tickers: list[str]) -> str:
    keys = ", ".join(sql_literal(value) for value in tickers)
    return f"""SELECT ticker,
       COUNT(DISTINCT (trade_id, created_time))::bigint AS executions,
       COUNT(DISTINCT (created_time AT TIME ZONE 'UTC')::date)::bigint AS active_days,
       MIN(created_time) AS first_trade_ts,
       MAX(created_time) AS last_trade_ts,
       SUM(count)::double precision AS payout_notional
FROM prediction_markets.kalshi_trades
WHERE created_time >= TIMESTAMPTZ '{SELECTION_START}'
  AND created_time < TIMESTAMPTZ '{SELECTION_END}'
  AND trade_id IS NOT NULL
  AND yes_price BETWEEN 0 AND 100
  AND count > 0
  AND ticker IN ({keys})
GROUP BY ticker
HAVING COUNT(DISTINCT (trade_id, created_time)) >= 100
   AND COUNT(DISTINCT (created_time AT TIME ZONE 'UTC')::date) >= 10
   AND MAX(created_time) >= TIMESTAMPTZ '{RECENT_AFTER}'
ORDER BY ticker"""


def polymarket_activity_sql(pairs: list[tuple[str, str]]) -> str:
    keys = ", ".join(
        f"({sql_literal(condition)}, {sql_literal(asset)})"
        for condition, asset in pairs
    )
    return f"""SELECT condition_id, COALESCE(asset_id, '') AS asset_id,
       COUNT(DISTINCT (trade_id, ts))::bigint AS executions,
       COUNT(DISTINCT (ts AT TIME ZONE 'UTC')::date)::bigint AS active_days,
       MIN(ts) AS first_trade_ts,
       MAX(ts) AS last_trade_ts,
       SUM(size)::double precision AS payout_notional
FROM prediction_markets.polymarket_trades
WHERE ts >= TIMESTAMPTZ '{SELECTION_START}'
  AND ts < TIMESTAMPTZ '{SELECTION_END}'
  AND condition_id IS NOT NULL
  AND trade_id IS NOT NULL
  AND price BETWEEN 0 AND 1
  AND size > 0
  AND (condition_id, COALESCE(asset_id, '')) IN ({keys})
GROUP BY condition_id, COALESCE(asset_id, '')
HAVING COUNT(DISTINCT (trade_id, ts)) >= 100
   AND COUNT(DISTINCT (ts AT TIME ZONE 'UTC')::date) >= 10
   AND MAX(ts) >= TIMESTAMPTZ '{RECENT_AFTER}'
ORDER BY condition_id, asset_id"""


def materialize_batches(
    client: httpx.Client,
    prefix: str,
    groups: Iterator[list[Any]],
    sql_builder: Any,
) -> dict[str, Any]:
    rows: list[dict[str, Any]] = []
    artifacts: list[dict[str, str]] = []
    for number, group in enumerate(groups, start=1):
        result = materialize(client, f"{prefix}_{number:04d}", sql_builder(group))
        rows.extend(result["rows"])
        artifacts.extend(result["artifacts"])
        print(f"{prefix}: completed batch {number}; eligible rows={len(rows)}", flush=True)
    return {"rows": rows, "artifacts": artifacts}


def main() -> None:
    report_path = OUTPUT / "report.json"
    manifest_path = OUTPUT / "manifest.json"
    cohort_path = OUTPUT / "eligible_markets.jsonl"
    if report_path.exists() or manifest_path.exists() or cohort_path.exists():
        raise SystemExit("v4 future-cohort feasibility artifact already exists")
    OUTPUT.mkdir(parents=True, exist_ok=True)
    settings = ApiSettings.from_env()
    with httpx.Client(
        base_url=settings.base_url,
        headers={"Authorization": f"Bearer {settings.token}"},
        timeout=httpx.Timeout(1800.0),
        follow_redirects=True,
    ) as client:
        kalshi_roster = active_roster(client, "kalshi")
        poly_roster = active_roster(client, "polymarket")
        kalshi_ids = sorted(
            {str(row["market_id"]) for row in kalshi_roster["rows"] if row.get("market_id")}
        )
        poly_ids = sorted(
            {str(row["market_id"]) for row in poly_roster["rows"] if row.get("market_id")}
        )
        kalshi_metadata_result = materialize_batches(
            client,
            "kalshi_metadata",
            batches(kalshi_ids),
            kalshi_metadata_sql,
        )
        poly_metadata_result = materialize_batches(
            client,
            "polymarket_metadata",
            batches(poly_ids),
            polymarket_metadata_sql,
        )
        kalshi_latest = latest_rows(kalshi_metadata_result["rows"], "ticker")
        poly_latest = latest_rows(poly_metadata_result["rows"], "condition_id")
        kalshi_metadata = [
            row
            for row in kalshi_latest
            if later_timestamp(row.get("close_time"), row.get("expiration_time"))
            and parse_utc(
                str(later_timestamp(row.get("close_time"), row.get("expiration_time")))
            ) >= parse_utc(HOLDOUT_END)
        ]
        poly_metadata = [
            row
            for row in poly_latest
            if row.get("end_date")
            and parse_utc(str(row["end_date"])) >= parse_utc(HOLDOUT_END)
        ]
        kalshi = materialize_batches(
            client,
            "kalshi_activity",
            batches([str(row["ticker"]) for row in kalshi_metadata]),
            kalshi_activity_sql,
        )
        poly_pairs: list[tuple[str, str]] = []
        for row in poly_metadata:
            outcomes = parse_json_array(row.get("outcomes"))
            assets = parse_json_array(row.get("clob_token_ids"))
            yes = [index for index, value in enumerate(outcomes) if str(value).lower() == "yes"]
            if len(yes) == 1 and yes[0] < len(assets):
                poly_pairs.append((str(row["condition_id"]), str(assets[yes[0]])))
        poly = materialize_batches(
            client,
            "polymarket_activity",
            batches(poly_pairs),
            polymarket_activity_sql,
        )

    kalshi_metadata_by_id = {str(row["ticker"]): row for row in kalshi_metadata}
    poly_metadata_by_id = {
        str(row["condition_id"]): row for row in poly_metadata
    }

    markets: list[dict[str, Any]] = []
    drops: Counter[str] = Counter()
    for row in kalshi["rows"]:
        metadata = kalshi_metadata_by_id[str(row["ticker"])]
        question = " ".join(
            value for value in (
                str(metadata.get("title") or "").strip(),
                str(metadata.get("yes_sub_title") or "").strip(),
            ) if value
        )
        if not question:
            drops["kalshi_missing_question"] += 1
            continue
        category, _ = classify(question)
        markets.append({
            "venue": "kalshi",
            "market_id": str(row["ticker"]),
            "canonical_yes_asset_id": "YES",
            "event_cluster": "kalshi:" + str(metadata.get("event_ticker") or row["ticker"]),
            "question": question,
            "category": category,
            "executions": int(row["executions"]),
            "active_days": int(row["active_days"]),
            "last_trade_ts": row["last_trade_ts"],
            "terminal_time": later_timestamp(
                metadata.get("close_time"), metadata.get("expiration_time")
            ),
            "metadata_ingest_ts": metadata["ingest_ts"],
        })
    for row in poly["rows"]:
        metadata = poly_metadata_by_id[str(row["condition_id"])]
        outcomes = parse_json_array(metadata.get("outcomes"))
        assets = parse_json_array(metadata.get("clob_token_ids"))
        yes = [index for index, value in enumerate(outcomes) if str(value).lower() == "yes"]
        if len(yes) != 1 or yes[0] >= len(assets):
            drops["polymarket_no_unique_yes"] += 1
            continue
        yes_asset = str(assets[yes[0]])
        if str(row.get("asset_id") or "") != yes_asset:
            drops["polymarket_non_yes_activity_row"] += 1
            continue
        question = str(metadata.get("question") or "").strip()
        if not question:
            drops["polymarket_missing_question"] += 1
            continue
        category, _ = classify(question)
        markets.append({
            "venue": "polymarket",
            "market_id": str(row["condition_id"]),
            "canonical_yes_asset_id": yes_asset,
            "event_cluster": "polymarket:condition:" + str(row["condition_id"]),
            "question": question,
            "category": category,
            "executions": int(row["executions"]),
            "active_days": int(row["active_days"]),
            "last_trade_ts": row["last_trade_ts"],
            "terminal_time": metadata["end_date"],
            "metadata_ingest_ts": metadata["ingest_ts"],
        })
    markets.sort(key=lambda row: (row["venue"], row["market_id"]))
    atomic_jsonl(cohort_path, markets)
    by_venue = Counter(row["venue"] for row in markets)
    by_category = Counter(row["category"] for row in markets)
    clusters = Counter(row["event_cluster"] for row in markets)
    checks = {
        "at_least_500_event_clusters": len(clusters) >= 500,
        "at_least_50_markets_each_venue": all(by_venue[key] >= 50 for key in ("kalshi", "polymarket")),
        "all_terminal_after_holdout": all(
            row["terminal_time"] is not None
            and parse_utc(str(row["terminal_time"])) >= parse_utc(HOLDOUT_END)
            for row in markets
        ),
        "all_recent_before_selection_cutoff": all(
            parse_utc(str(row["last_trade_ts"])) >= parse_utc(RECENT_AFTER)
            for row in markets
        ),
        "labels_prices_predictions_or_outcomes_read": False,
    }
    passed = (
        all(value for key, value in checks.items() if key != "labels_prices_predictions_or_outcomes_read")
        and checks["labels_prices_predictions_or_outcomes_read"] is False
    )
    report = {
        "audit_id": "eventx-v4-future-cohort-feasibility-20260902",
        "created_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "status": "passed" if passed else "failed",
        "integrity_pass": passed,
        "label_blind": True,
        "windows": {
            "selection_activity": f"[{SELECTION_START}, {SELECTION_END})",
            "recent_activity_after": RECENT_AFTER,
            "embargo": f"[{SELECTION_END}, {HOLDOUT_START})",
            "proposed_holdout": f"[{HOLDOUT_START}, {HOLDOUT_END})",
        },
        "markets": len(markets),
        "event_clusters": len(clusters),
        "markets_in_multi_contract_clusters": sum(value for value in clusters.values() if value > 1),
        "largest_event_cluster": max(clusters.values(), default=0),
        "by_venue": dict(by_venue),
        "by_category": dict(by_category),
        "drop_reasons": dict(drops),
        "checks": checks,
        "cohort": {"path": relative(cohort_path), "sha256": sha256_file(cohort_path)},
        "metadata_candidates": {
            "selection_cutoff": SELECTION_END,
            "active_roster_endpoint": "/api/v1/lqt/markets",
            "kalshi_active_roster": len(kalshi_ids),
            "kalshi_roster_as_of_ns": kalshi_roster["as_of_ns"],
            "kalshi_rows": len(kalshi_metadata_result["rows"]),
            "kalshi_unique_markets_before_terminal_filter": len(kalshi_latest),
            "kalshi_unique_markets": len(kalshi_metadata),
            "polymarket_active_roster": len(poly_ids),
            "polymarket_roster_as_of_ns": poly_roster["as_of_ns"],
            "polymarket_rows": len(poly_metadata_result["rows"]),
            "polymarket_unique_markets_before_terminal_filter": len(poly_latest),
            "polymarket_unique_markets": len(poly_metadata),
            "polymarket_unique_yes_pairs": len(poly_pairs),
        },
        "source_artifacts": (
            kalshi_roster["artifacts"]
            + poly_roster["artifacts"]
            + kalshi_metadata_result["artifacts"]
            + poly_metadata_result["artifacts"]
            + kalshi["artifacts"]
            + poly["artifacts"]
        ),
    }
    atomic_json(report_path, report)
    atomic_json(
        manifest_path,
        {
            "audit_id": report["audit_id"],
            "status": report["status"],
            "artifacts": [
                {"path": relative(path), "sha256": sha256_file(path)}
                for path in (report_path, cohort_path, Path(__file__).resolve())
            ] + report["source_artifacts"],
        },
    )
    print(json.dumps({
        "status": report["status"],
        "markets": report["markets"],
        "event_clusters": report["event_clusters"],
        "by_venue": report["by_venue"],
        "by_category": report["by_category"],
        "drop_reasons": report["drop_reasons"],
        "checks": report["checks"],
    }, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
