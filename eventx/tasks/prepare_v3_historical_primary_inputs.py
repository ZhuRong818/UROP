"""Prepare label-blind inputs for the EventX historical B0/B1 study.

The task materialises conservatively timed Lumid news and development-only market
activity/metadata.  It deliberately excludes trade prices, outcomes, forward returns,
labels, predictions, and metrics.  Cohort eligibility and news-support gates are based
only on the development prefix; the elapsed holdout cannot affect selection.
"""

from __future__ import annotations

import argparse
from collections import Counter
from datetime import datetime, timezone
import hashlib
import json
import math
import os
from pathlib import Path
from typing import Any, Iterator

import httpx

from eventx.features.v2_1_association import associate, market_spec, normalized_tokens
from eventx.settings import ApiSettings, REPO_ROOT
from eventx.tasks.audit_v3_historical_feasibility import parse_json_array
from eventx.tasks.build_v2_1_taxonomy import TAXONOMY_VERSION, classify
from eventx.tasks.collect_v2_3_news_v2 import normalize_url
from eventx.tasks.export_v3_historical_feasibility import (
    compact_receipt,
    download,
    parse_utc,
    RetrieveFailure,
    retrieve_with_retry,
    rfc3339,
    sha256_file,
    sql_literal,
)


DEFAULT_OUTPUT = REPO_ROOT / "data/v3_historical/primary/label_blind_inputs"
START = "2026-05-17T00:00:00Z"
DEVELOPMENT_END = "2026-07-22T00:00:00Z"
HOLDOUT_END = "2026-08-08T00:00:00Z"
PROTOCOL_ID = "eventx-v3-historical-primary-candidate-20260902"
PROHIBITED_FIELDS = {
    "forward_logodds",
    "forward_return",
    "label",
    "metric",
    "prediction",
    "result",
    "target",
    "y",
    "y_jump",
    "yes_price",
    "no_price",
    "price",
}


def atomic_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(
        json.dumps(value, indent=2, sort_keys=True, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    os.replace(temporary, path)


def atomic_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    with temporary.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, sort_keys=True, ensure_ascii=False) + "\n")
    os.replace(temporary, path)


def relative(path: Path) -> str:
    try:
        return str(path.resolve().relative_to(REPO_ROOT))
    except ValueError:
        return str(path.resolve())


def read_jsonl(path: Path) -> Iterator[dict[str, Any]]:
    with path.open(encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, start=1):
            if not line.strip():
                continue
            value = json.loads(line)
            if not isinstance(value, dict):
                raise ValueError(f"{path}:{line_number} is not an object")
            prohibited = PROHIBITED_FIELDS.intersection(key.lower() for key in value)
            if prohibited:
                raise ValueError(
                    f"{path}:{line_number} contains prohibited fields: {sorted(prohibited)}"
                )
            yield value


def news_sql() -> str:
    return f"""WITH candidate AS (
    SELECT a.id, a.published_at, a.ingest_ts, a.symbol, a.related_symbols,
           a.publisher, a.author, a.category, a.headline, a.summary, a.url,
           a.source, a.source_endpoint, a.source_run_id,
           r.started_at AS run_started_at, r.ended_at AS run_ended_at,
           r.status AS run_status,
           GREATEST(
               a.published_at,
               a.ingest_ts,
               r.started_at,
               COALESCE(r.ended_at, a.ingest_ts)
           ) AS available_at
    FROM news.articles a
    JOIN provenance.runs r ON r.run_id = a.source_run_id
    WHERE a.published_at IS NOT NULL
      AND a.ingest_ts IS NOT NULL
      AND a.published_at >= TIMESTAMPTZ '{START}' - INTERVAL '24 hours'
      AND a.published_at < TIMESTAMPTZ '{HOLDOUT_END}'
      AND a.ingest_ts >= TIMESTAMPTZ '{START}'
      AND a.ingest_ts < TIMESTAMPTZ '{HOLDOUT_END}'
      AND a.ingest_ts >= a.published_at
      AND a.ingest_ts <= a.published_at + INTERVAL '24 hours'
      AND a.ingest_ts >= r.started_at
      AND (r.ended_at IS NULL OR r.ended_at >= r.started_at)
)
SELECT *
FROM candidate
WHERE available_at >= TIMESTAMPTZ '{START}'
  AND available_at < TIMESTAMPTZ '{HOLDOUT_END}'
  AND available_at <= published_at + INTERVAL '24 hours'
ORDER BY id"""


def kalshi_candidates_sql() -> str:
    return f"""WITH activity AS (
    SELECT ticker, COUNT(DISTINCT trade_id)::bigint AS trades,
           COUNT(DISTINCT (created_time AT TIME ZONE 'UTC')::date)::bigint AS active_days,
           MIN(created_time) AS first_trade_ts, MAX(created_time) AS last_trade_ts
    FROM prediction_markets.kalshi_trades
    WHERE created_time >= TIMESTAMPTZ '{START}'
      AND created_time < TIMESTAMPTZ '{DEVELOPMENT_END}'
      AND trade_id IS NOT NULL
      AND yes_price BETWEEN 0 AND 100
    GROUP BY ticker
    HAVING COUNT(DISTINCT trade_id) >= 100
       AND COUNT(DISTINCT (created_time AT TIME ZONE 'UTC')::date) >= 10
)
SELECT a.ticker, a.trades, a.active_days, a.first_trade_ts, a.last_trade_ts,
       m.event_ticker, m.title, m.yes_sub_title, m.no_sub_title,
       m.market_type, m.open_time, m.close_time, m.expiration_time,
       m.ingest_ts AS metadata_ingest_ts, m.source AS metadata_source,
       m.source_endpoint AS metadata_source_endpoint,
       m.source_run_id AS metadata_source_run_id
FROM activity a
JOIN LATERAL (
    SELECT ticker, event_ticker, title, yes_sub_title, no_sub_title,
           market_type, open_time, close_time, expiration_time,
           ingest_ts, source, source_endpoint, source_run_id
    FROM prediction_markets.kalshi_markets
    WHERE ticker = a.ticker
      AND ingest_ts < TIMESTAMPTZ '{DEVELOPMENT_END}'
    ORDER BY ingest_ts ASC
    LIMIT 1
) m ON TRUE
ORDER BY a.ticker"""


def polymarket_candidates_sql() -> str:
    return f"""WITH activity AS (
    SELECT condition_id, COALESCE(asset_id, '') AS asset_id,
           COUNT(DISTINCT trade_id)::bigint AS trades,
           COUNT(DISTINCT (ts AT TIME ZONE 'UTC')::date)::bigint AS active_days,
           MIN(ts) AS first_trade_ts, MAX(ts) AS last_trade_ts
    FROM prediction_markets.polymarket_trades
    WHERE ts >= TIMESTAMPTZ '{START}'
      AND ts < TIMESTAMPTZ '{DEVELOPMENT_END}'
      AND condition_id IS NOT NULL
      AND trade_id IS NOT NULL
      AND price BETWEEN 0 AND 1
    GROUP BY condition_id, COALESCE(asset_id, '')
    HAVING COUNT(DISTINCT trade_id) >= 100
       AND COUNT(DISTINCT (ts AT TIME ZONE 'UTC')::date) >= 10
), metadata AS (
    SELECT DISTINCT ON (condition_id)
           condition_id, question, slug, outcomes, clob_token_ids,
           start_date, end_date, ingest_ts, source, source_endpoint, source_run_id
    FROM prediction_markets.polymarket_markets
    WHERE ingest_ts < TIMESTAMPTZ '{DEVELOPMENT_END}'
    ORDER BY condition_id, ingest_ts ASC
)
SELECT a.condition_id, a.asset_id, a.trades, a.active_days,
       a.first_trade_ts, a.last_trade_ts,
       m.question, m.slug, m.outcomes, m.clob_token_ids,
       m.start_date, m.end_date, m.ingest_ts AS metadata_ingest_ts,
       m.source AS metadata_source, m.source_endpoint AS metadata_source_endpoint,
       m.source_run_id AS metadata_source_run_id
FROM activity a
JOIN metadata m ON m.condition_id = a.condition_id
ORDER BY a.condition_id, a.asset_id"""


QUERIES = {"news": news_sql}


def materialise(
    client: httpx.Client, name: str, sql: str, root: Path
) -> dict[str, Any]:
    query_path = root / f"{name}.sql"
    data_path = root / f"{name}.jsonl"
    receipt_path = root / f"{name}_receipt.json"
    query_path.write_text(sql + "\n", encoding="utf-8")
    receipt, retry_ledger = retrieve_with_retry(
        client, sql, attempts=3, delays=[10.0, 30.0, 120.0]
    )
    download(client, str(receipt["materialized_uri"]), data_path)
    atomic_json(
        receipt_path,
        {"receipt": compact_receipt(receipt), "retry_ledger": retry_ledger},
    )
    return {
        "query": {
            "path": relative(query_path),
            "sha256": sha256_file(query_path),
        },
        "data": {
            "bytes": data_path.stat().st_size,
            "path": relative(data_path),
            "sha256": sha256_file(data_path),
        },
        "receipt": {
            "path": relative(receipt_path),
            "sha256": sha256_file(receipt_path),
        },
        "rowcount": int(receipt.get("rowcount") or 0),
    }


def feasibility_cohort() -> list[dict[str, Any]]:
    path = (
        REPO_ROOT
        / "data/v3_historical/feasibility/audit/eligible_markets.jsonl"
    )
    return list(read_jsonl(path))


def candidate_batch_sql(venue: str, markets: list[dict[str, Any]]) -> str:
    if venue == "kalshi":
        keys = ", ".join(sql_literal(str(row["market_id"])) for row in markets)
        return f"""SELECT ticker, COUNT(DISTINCT trade_id)::bigint AS trades,
       COUNT(DISTINCT (created_time AT TIME ZONE 'UTC')::date)::bigint AS active_days,
       MIN(created_time) AS first_trade_ts, MAX(created_time) AS last_trade_ts
FROM prediction_markets.kalshi_trades
WHERE created_time >= TIMESTAMPTZ '{START}'
  AND created_time < TIMESTAMPTZ '{DEVELOPMENT_END}'
  AND trade_id IS NOT NULL
  AND yes_price BETWEEN 0 AND 100
  AND ticker IN ({keys})
GROUP BY ticker
HAVING COUNT(DISTINCT trade_id) >= 100
   AND COUNT(DISTINCT (created_time AT TIME ZONE 'UTC')::date) >= 10
ORDER BY ticker"""
    pairs = ", ".join(
        "(" + sql_literal(str(row["market_id"])) + ", "
        + sql_literal(str(row["canonical_yes_asset_id"])) + ")"
        for row in markets
    )
    return f"""SELECT condition_id, COALESCE(asset_id, '') AS asset_id,
       COUNT(DISTINCT trade_id)::bigint AS trades,
       COUNT(DISTINCT (ts AT TIME ZONE 'UTC')::date)::bigint AS active_days,
       MIN(ts) AS first_trade_ts, MAX(ts) AS last_trade_ts
FROM prediction_markets.polymarket_trades
WHERE ts >= TIMESTAMPTZ '{START}'
  AND ts < TIMESTAMPTZ '{DEVELOPMENT_END}'
  AND trade_id IS NOT NULL
  AND price BETWEEN 0 AND 1
  AND (condition_id, COALESCE(asset_id, '')) IN ({pairs})
GROUP BY condition_id, COALESCE(asset_id, '')
HAVING COUNT(DISTINCT trade_id) >= 100
   AND COUNT(DISTINCT (ts AT TIME ZONE 'UTC')::date) >= 10
ORDER BY condition_id, COALESCE(asset_id, '')"""


def materialise_candidate_batches(
    client: httpx.Client,
    venue: str,
    markets: list[dict[str, Any]],
    root: Path,
    batch_size: int,
) -> dict[str, Any]:
    name = f"{venue}_candidates"
    batch_root = root / f"{name}_batches"
    batch_root.mkdir(parents=True, exist_ok=True)
    rows: list[dict[str, Any]] = []
    artifacts: list[dict[str, Any]] = []

    def fetch(batch: list[dict[str, Any]], tag: str) -> None:
        sql = candidate_batch_sql(venue, batch)
        query_path = batch_root / f"query_{tag}.sql"
        timed_out_path = batch_root / f"query_{tag}_timed_out.sql"
        page_path = batch_root / f"data_{tag}.jsonl"
        receipt_path = batch_root / f"receipt_{tag}.json"
        expected_query = sql + "\n"
        if timed_out_path.is_file() and timed_out_path.read_text(
            encoding="utf-8"
        ) == expected_query:
            midpoint = len(batch) // 2
            fetch(batch[:midpoint], tag + "a")
            fetch(batch[midpoint:], tag + "b")
            return
        if all(path.is_file() for path in (query_path, page_path, receipt_path)):
            if query_path.read_text(encoding="utf-8") != expected_query:
                raise RuntimeError(f"{name} batch {tag} query changed during resume")
            page_rows = list(read_jsonl(page_path))
            receipt_value = json.loads(receipt_path.read_text(encoding="utf-8"))
            expected_rows = int(
                receipt_value.get("receipt", {}).get("rowcount") or 0
            )
            if len(page_rows) != expected_rows:
                raise RuntimeError(f"{name} batch {tag} resumed rowcount mismatch")
            rows.extend(page_rows)
            artifacts.append(
                {
                    "batch": tag,
                    "input_markets": len(batch),
                    "query_sha256": sha256_file(query_path),
                    "data_sha256": sha256_file(page_path),
                    "receipt_sha256": sha256_file(receipt_path),
                    "rowcount": len(page_rows),
                    "resumed": True,
                }
            )
            return
        query_path.write_text(expected_query, encoding="utf-8")
        try:
            receipt, retry_ledger = retrieve_with_retry(
                client, sql, attempts=1, delays=[10.0]
            )
        except RetrieveFailure as exc:
            if "statement timeout" not in str(exc).lower() or len(batch) <= 25:
                receipt, retry_ledger = retrieve_with_retry(
                    client, sql, attempts=3, delays=[10.0, 30.0, 120.0]
                )
            else:
                midpoint = len(batch) // 2
                query_path.rename(timed_out_path)
                fetch(batch[:midpoint], tag + "a")
                fetch(batch[midpoint:], tag + "b")
                return
        download(client, str(receipt["materialized_uri"]), page_path)
        atomic_json(
            receipt_path,
            {"receipt": compact_receipt(receipt), "retry_ledger": retry_ledger},
        )
        page_rows = list(read_jsonl(page_path))
        if len(page_rows) != int(receipt.get("rowcount") or 0):
            raise RuntimeError(f"{name} batch {tag} rowcount mismatch")
        rows.extend(page_rows)
        artifacts.append(
            {
                "batch": tag,
                "input_markets": len(batch),
                "query_sha256": sha256_file(query_path),
                "data_sha256": sha256_file(page_path),
                "receipt_sha256": sha256_file(receipt_path),
                "rowcount": len(page_rows),
            }
        )

    for batch_number, offset in enumerate(range(0, len(markets), batch_size), start=1):
        fetch(markets[offset : offset + batch_size], f"{batch_number:04d}")
    key_name = "ticker" if venue == "kalshi" else "condition_id"
    rows.sort(key=lambda row: (str(row[key_name]), str(row.get("asset_id") or "")))
    keys = [(str(row[key_name]), str(row.get("asset_id") or "")) for row in rows]
    if len(keys) != len(set(keys)):
        raise RuntimeError(f"duplicate {name} aggregate key")
    data_path = root / f"{name}.jsonl"
    index_path = root / f"{name}_query_index.json"
    atomic_jsonl(data_path, rows)
    atomic_json(index_path, artifacts)
    return {
        "data": {
            "bytes": data_path.stat().st_size,
            "path": relative(data_path),
            "sha256": sha256_file(data_path),
        },
        "query_index": {
            "path": relative(index_path),
            "sha256": sha256_file(index_path),
        },
        "batches": len(artifacts),
        "rowcount": len(rows),
    }


def derive_candidates_from_frozen_pages(
    venue: str,
    markets: list[dict[str, Any]],
    root: Path,
) -> dict[str, Any]:
    dataset = f"{venue}_activity"
    source_root = REPO_ROOT / "data/v3_historical/feasibility/raw" / dataset
    manifest_path = source_root / "manifest.json"
    index_path = source_root / "query_index.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if manifest.get("integrity_pass") is not True:
        raise RuntimeError(f"frozen {dataset} source manifest did not pass")
    if sha256_file(index_path) != manifest["artifacts"]["query"]["sha256"]:
        raise RuntimeError(f"frozen {dataset} query index hash mismatch")
    desired = {
        (
            str(row["market_id"]),
            "" if venue == "kalshi" else str(row["canonical_yes_asset_id"]),
        )
        for row in markets
    }
    totals: dict[tuple[str, str], dict[str, Any]] = {}
    pages_used = 0
    rows_scanned = 0
    desired_rows = 0
    development_end = parse_utc(DEVELOPMENT_END)
    artifacts = json.loads(index_path.read_text(encoding="utf-8"))
    if not isinstance(artifacts, list):
        raise RuntimeError(f"invalid frozen {dataset} query index")
    for artifact in artifacts:
        if parse_utc(str(artifact["chunk_end_exclusive"])) > development_end:
            continue
        page_path = Path(str(artifact["data_path"]))
        digest = hashlib.sha256()
        with page_path.open("rb") as handle:
            for raw_line in handle:
                digest.update(raw_line)
                if not raw_line.strip():
                    continue
                rows_scanned += 1
                row = json.loads(raw_line)
                key = (
                    str(row.get("ticker") or row.get("condition_id") or ""),
                    "" if venue == "kalshi" else str(row.get("asset_id") or ""),
                )
                if key not in desired:
                    continue
                desired_rows += 1
                current = totals.get(key)
                if current is None:
                    totals[key] = dict(row)
                    continue
                current["trades"] = int(current["trades"]) + int(row["trades"])
                current["active_days"] = int(current["active_days"]) + int(
                    row["active_days"]
                )
                current["first_trade_ts"] = min(
                    str(current["first_trade_ts"]), str(row["first_trade_ts"])
                )
                current["last_trade_ts"] = max(
                    str(current["last_trade_ts"]), str(row["last_trade_ts"])
                )
        if digest.hexdigest() != artifact["data_sha256"]:
            raise RuntimeError(f"frozen activity page hash mismatch: {page_path}")
        pages_used += 1
    rows = [
        totals[key]
        for key in sorted(totals)
        if int(totals[key]["trades"]) >= 100
        and int(totals[key]["active_days"]) >= 10
    ]
    data_path = root / f"{venue}_candidates.jsonl"
    atomic_jsonl(data_path, rows)
    return {
        "derivation": "local merge of hash-verified frozen one-day Lumid activity pages",
        "source_manifest": {
            "path": relative(manifest_path),
            "sha256": sha256_file(manifest_path),
        },
        "source_query_index": {
            "path": relative(index_path),
            "sha256": sha256_file(index_path),
        },
        "development_pages_used": pages_used,
        "source_rows_scanned": rows_scanned,
        "desired_market_day_rows": desired_rows,
        "data": {
            "bytes": data_path.stat().st_size,
            "path": relative(data_path),
            "sha256": sha256_file(data_path),
        },
        "rowcount": len(rows),
    }


def build_markets(root: Path) -> tuple[list[dict[str, Any]], Counter[str]]:
    drops: Counter[str] = Counter()
    markets: list[dict[str, Any]] = []
    development_end = parse_utc(DEVELOPMENT_END)
    feasibility = {
        (str(row["venue"]), str(row["market_id"])): row
        for row in feasibility_cohort()
    }
    kalshi_metadata_path = (
        REPO_ROOT
        / "data/v3_historical/feasibility/raw/kalshi_markets/kalshi_markets.jsonl"
    )
    poly_metadata_path = (
        REPO_ROOT
        / "data/v3_historical/feasibility/raw/polymarket_markets/polymarket_markets.jsonl"
    )
    kalshi_metadata = {
        str(row["ticker"]): row for row in read_jsonl(kalshi_metadata_path)
    }
    poly_metadata = {
        str(row["condition_id"]): row for row in read_jsonl(poly_metadata_path)
    }
    for row in read_jsonl(root / "kalshi_candidates.jsonl"):
        market_id = str(row["ticker"])
        metadata = kalshi_metadata.get(market_id)
        prior = feasibility.get(("kalshi", market_id))
        if metadata is None or prior is None:
            drops["kalshi_missing_frozen_metadata"] += 1
            continue
        if parse_utc(str(metadata["ingest_ts"])) >= development_end:
            drops["kalshi_metadata_not_available_by_development_close"] += 1
            continue
        question = str(metadata.get("title") or "").strip()
        if not question:
            drops["kalshi_missing_question"] += 1
            continue
        category, _ = classify(question)
        markets.append(
            {
                "active_days": int(row["active_days"]),
                "canonical_yes_asset_id": "YES",
                "category": category,
                "first_trade_ts": row["first_trade_ts"],
                "last_trade_ts": row["last_trade_ts"],
                "market_id": market_id,
                "question": question,
                "taxonomy_version": TAXONOMY_VERSION,
                "trades": int(row["trades"]),
                "venue": "kalshi",
            }
        )

    for activity in read_jsonl(root / "polymarket_candidates.jsonl"):
        condition_id = str(activity["condition_id"])
        metadata = poly_metadata.get(condition_id)
        prior = feasibility.get(("polymarket", condition_id))
        if metadata is None or prior is None:
            drops["polymarket_missing_frozen_metadata"] += 1
            continue
        if parse_utc(str(metadata["ingest_ts"])) >= development_end:
            drops["polymarket_metadata_not_available_by_development_close"] += 1
            continue
        outcomes = parse_json_array(metadata.get("outcomes"))
        assets = parse_json_array(metadata.get("clob_token_ids"))
        yes_indices = [
            index
            for index, outcome in enumerate(outcomes)
            if outcome.strip().lower() == "yes"
        ]
        if len(yes_indices) != 1 or yes_indices[0] >= len(assets):
            drops["polymarket_no_unique_canonical_yes"] += 1
            continue
        yes_asset = assets[yes_indices[0]]
        if str(activity.get("asset_id") or "") != yes_asset:
            drops["polymarket_yes_below_development_activity_gate"] += 1
            continue
        question = str(metadata.get("question") or "").strip()
        if not question:
            drops["polymarket_missing_question"] += 1
            continue
        category, _ = classify(question)
        markets.append(
            {
                "active_days": int(activity["active_days"]),
                "canonical_yes_asset_id": yes_asset,
                "category": category,
                "first_trade_ts": activity["first_trade_ts"],
                "last_trade_ts": activity["last_trade_ts"],
                "market_id": condition_id,
                "question": question,
                "taxonomy_version": TAXONOMY_VERSION,
                "trades": int(activity["trades"]),
                "venue": "polymarket",
            }
        )
    markets.sort(key=lambda row: (row["venue"], row["market_id"]))
    keys = {(row["venue"], row["market_id"]) for row in markets}
    if len(keys) != len(markets):
        raise ValueError("duplicate market in development-only cohort")
    return markets, drops


def load_development_news(root: Path) -> tuple[list[dict[str, Any]], dict[str, int]]:
    development_end = parse_utc(DEVELOPMENT_END)
    identities: dict[str, dict[str, Any]] = {}
    duplicate_rows = 0
    for row in read_jsonl(root / "news.jsonl"):
        available = parse_utc(str(row["available_at"]))
        if available >= development_end:
            continue
        published = parse_utc(str(row["published_at"]))
        text = " ".join(
            str(row.get(field) or "").strip()
            for field in ("headline", "summary")
            if str(row.get(field) or "").strip()
        )
        if not text:
            continue
        url = str(row.get("url") or "").strip()
        try:
            normalised = normalize_url(url) if url else ""
        except ValueError:
            normalised = ""
        identity = f"url:{normalised}" if normalised else f"id:{row['id']}"
        candidate = {
            "available_at": available,
            "doc_id": str(row["id"]),
            "published_at": published,
            "text": text,
            "tokens": normalized_tokens(text),
        }
        current = identities.get(identity)
        if current is None:
            identities[identity] = {
                "document": candidate,
                "published_values": {rfc3339(published)},
            }
            continue
        duplicate_rows += 1
        current["published_values"].add(rfc3339(published))
        existing = current["document"]
        if (candidate["available_at"], candidate["doc_id"]) < (
            existing["available_at"],
            existing["doc_id"],
        ):
            current["document"] = candidate
    documents: list[dict[str, Any]] = []
    conflicts = 0
    for identity, value in identities.items():
        if identity.startswith("url:") and len(value["published_values"]) > 1:
            conflicts += 1
            continue
        documents.append(value["document"])
    documents.sort(key=lambda row: (row["available_at"], row["doc_id"]))
    return documents, {
        "development_documents": len(documents),
        "duplicate_identity_rows": duplicate_rows,
        "timestamp_conflict_identities_excluded": conflicts,
        "usable_calendar_days": len(
            {row["available_at"].date().isoformat() for row in documents}
        ),
    }


def association_counts(
    markets: list[dict[str, Any]], documents: list[dict[str, Any]]
) -> list[dict[str, Any]]:
    token_index: dict[str, set[int]] = {}
    for index, document in enumerate(documents):
        for token in document["tokens"]:
            token_index.setdefault(token, set()).add(index)
    development_end = parse_utc(DEVELOPMENT_END)
    rows: list[dict[str, Any]] = []
    for market in markets:
        active_start = parse_utc(str(market["first_trade_ts"]))
        active_end = min(parse_utc(str(market["last_trade_ts"])), development_end)
        spec = market_spec(market["question"], market["category"])
        seeds = set(spec.anchors) | set(spec.event_terms) | set(spec.keywords)
        for phrase in spec.phrases:
            seeds.update(normalized_tokens(phrase))
        candidates: set[int] = set()
        for term in seeds:
            candidates.update(token_index.get(term, set()))
        matched: list[str] = []
        for index in sorted(candidates):
            document = documents[index]
            if not active_start <= document["available_at"] <= active_end:
                continue
            reasons, _ = associate(spec, document["text"])
            if reasons:
                matched.append(document["doc_id"])
        rows.append(
            {
                "association_count": len(matched),
                "category": market["category"],
                "market_id": market["market_id"],
                "venue": market["venue"],
            }
        )
    return rows


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--timeout", type=float, default=1800.0)
    parser.add_argument("--candidate-batch-size", type=int, default=500)
    parser.add_argument("--reuse", action="store_true")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    args.output.mkdir(parents=True, exist_ok=True)
    artifacts: dict[str, Any] = {}
    settings = ApiSettings.from_env()
    with httpx.Client(
        base_url=settings.base_url,
        headers={"Authorization": f"Bearer {settings.token}"},
        timeout=httpx.Timeout(args.timeout),
        follow_redirects=True,
    ) as client:
        for name, builder in QUERIES.items():
            data_path = args.output / f"{name}.jsonl"
            receipt_path = args.output / f"{name}_receipt.json"
            query_path = args.output / f"{name}.sql"
            if args.reuse and all(
                path.is_file() for path in (data_path, receipt_path, query_path)
            ):
                receipt_value = json.loads(receipt_path.read_text(encoding="utf-8"))
                artifacts[name] = {
                    "query": {
                        "path": relative(query_path),
                        "sha256": sha256_file(query_path),
                    },
                    "data": {
                        "bytes": data_path.stat().st_size,
                        "path": relative(data_path),
                        "sha256": sha256_file(data_path),
                    },
                    "receipt": {
                        "path": relative(receipt_path),
                        "sha256": sha256_file(receipt_path),
                    },
                    "rowcount": int(
                        receipt_value.get("receipt", {}).get("rowcount") or 0
                    ),
                }
            else:
                artifacts[name] = materialise(client, name, builder(), args.output)
    feasibility = feasibility_cohort()
    for venue in ("kalshi", "polymarket"):
        venue_markets = [row for row in feasibility if row["venue"] == venue]
        artifacts[f"{venue}_candidates"] = derive_candidates_from_frozen_pages(
            venue, venue_markets, args.output
        )

    markets, drops = build_markets(args.output)
    documents, news_stats = load_development_news(args.output)
    counts = association_counts(markets, documents)
    cohort_path = args.output / "cohort.jsonl"
    counts_path = args.output / "development_association_counts.jsonl"
    atomic_jsonl(cohort_path, markets)
    atomic_jsonl(counts_path, counts)
    venue_counts = Counter(row["venue"] for row in markets)
    supported = sum(row["association_count"] >= 5 for row in counts)
    total_associations = sum(row["association_count"] for row in counts)
    maximum = max((row["association_count"] for row in counts), default=0)
    concentration = maximum / total_associations if total_associations else math.inf
    gates = {
        "development_cohort_markets_at_least_30": len(markets) >= 30,
        "development_cohort_each_venue_at_least_5": all(
            venue_counts.get(venue, 0) >= 5 for venue in ("kalshi", "polymarket")
        ),
        "development_markets_with_five_associations_at_least_20": supported >= 20,
        "development_associations_at_least_200": total_associations >= 200,
        "maximum_single_market_share_at_most_half": total_associations > 0
        and concentration <= 0.5,
        "development_news_calendar_days_at_least_56": news_stats[
            "usable_calendar_days"
        ]
        >= 56,
    }
    report = {
        "protocol_id": PROTOCOL_ID,
        "created_at": rfc3339(datetime.now(timezone.utc)),
        "status": "passed" if all(gates.values()) else "failed",
        "label_blind": True,
        "labels_or_outcomes_read": False,
        "holdout_covariates_used_for_selection": False,
        "window": {
            "start": START,
            "development_end_exclusive": DEVELOPMENT_END,
            "holdout_end_exclusive": HOLDOUT_END,
        },
        "availability": (
            "max(published_at, ingest_ts, joined run_started_at, joined run_ended_at "
            "when present), with final lag <=24h"
        ),
        "cohort_rule": (
            "all markets with earliest pre-development-close metadata, unique "
            "canonical YES, >=100 development trades and >=10 development active days"
        ),
        "cohort": {
            "markets": len(markets),
            "by_venue": dict(sorted(venue_counts.items())),
            "drop_reasons": dict(sorted(drops.items())),
            "path": relative(cohort_path),
            "sha256": sha256_file(cohort_path),
        },
        "news": news_stats,
        "development_associations": {
            "markets_with_at_least_five": supported,
            "total": total_associations,
            "maximum_for_one_market": maximum,
            "maximum_market_share": (
                concentration if math.isfinite(concentration) else None
            ),
            "path": relative(counts_path),
            "sha256": sha256_file(counts_path),
        },
        "gates": gates,
        "integrity_pass": all(gates.values()),
        "artifacts": artifacts,
    }
    atomic_json(args.output / "report.json", report)
    print(json.dumps(report, indent=2, sort_keys=True))
    if not report["integrity_pass"]:
        raise SystemExit("historical primary label-blind input gate failed")


if __name__ == "__main__":
    main()
