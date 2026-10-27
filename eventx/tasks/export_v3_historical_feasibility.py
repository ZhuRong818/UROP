"""Export label-blind Lumid inputs for the EventX historical feasibility gate.

This task never reads prediction-market outcomes and never constructs labels. It
materialises bounded news, trade-activity and market-metadata datasets through
Lumid's read-only ``POST /retrieve`` route, then records SQL, receipts and hashes.
"""

from __future__ import annotations

import argparse
from datetime import datetime, timedelta, timezone
import hashlib
import json
import os
from pathlib import Path
import shutil
import time
from typing import Any

import httpx

from eventx.settings import ApiSettings, REPO_ROOT


DEFAULT_PROTOCOL = REPO_ROOT / "eventx/release/v3_historical/feasibility_protocol.json"
DEFAULT_OUTPUT = REPO_ROOT / "data/v3_historical/feasibility/raw"
DATASETS = (
    "news",
    "kalshi_activity",
    "polymarket_activity",
    "kalshi_markets",
    "polymarket_markets",
)
PROHIBITED_NAMES = {
    "forward_logodds",
    "forward_return",
    "label",
    "metric",
    "prediction",
    "target",
    "y",
    "y_jump",
}


class RetrieveFailure(RuntimeError):
    """A failed Lumid retrieval with its complete retry evidence attached."""

    def __init__(self, message: str, ledger: list[dict[str, Any]]) -> None:
        super().__init__(message)
        self.ledger = ledger


def parse_utc(value: str) -> datetime:
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        raise ValueError(f"timestamp must include timezone: {value!r}")
    return parsed.astimezone(timezone.utc)


def rfc3339(value: datetime) -> str:
    return value.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def atomic_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(
        json.dumps(value, indent=2, sort_keys=True, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    os.replace(temporary, path)


def atomic_jsonl_rows(path: Path, rows: list[dict[str, Any]]) -> None:
    temporary = path.with_suffix(path.suffix + ".tmp")
    with temporary.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, sort_keys=True) + "\n")
        handle.flush()
        os.fsync(handle.fileno())
    os.replace(temporary, path)


def ensure_free_space(path: Path, min_free_gib: float) -> int:
    """Fail closed before a retrieval can exhaust the working volume."""

    if min_free_gib < 0:
        raise ValueError("minimum free space cannot be negative")
    probe = path
    while not probe.exists():
        if probe.parent == probe:
            raise RuntimeError(f"cannot find an existing parent for {path}")
        probe = probe.parent
    free_bytes = shutil.disk_usage(probe).free
    required_bytes = int(min_free_gib * 1024**3)
    if free_bytes < required_bytes:
        raise RuntimeError(
            "disk safety floor reached: "
            f"{free_bytes / 1024**3:.2f} GiB free < {min_free_gib:.2f} GiB required"
        )
    return free_bytes


def compact_receipt(receipt: dict[str, Any]) -> dict[str, Any]:
    """Retain provenance fields without duplicating SQL and signed URLs."""

    fields = (
        "materialized_uri",
        "output_format",
        "replay_latency_ms",
        "rowcount",
        "run_id",
        "size_bytes",
    )
    return {name: receipt.get(name) for name in fields}


def load_protocol(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError("feasibility protocol must be an object")
    if value.get("labels_permitted") is not False or value.get("outcomes_permitted") is not False:
        raise ValueError("feasibility protocol does not preserve the label/outcome seal")
    return value


def sql_literal(value: str) -> str:
    return "'" + value.replace("'", "''") + "'"


def build_sql(
    dataset: str,
    start: datetime,
    end: datetime,
    *,
    after_key: tuple[str, ...] | None = None,
    page_limit: int = 1000,
) -> str:
    start_text = rfc3339(start)
    end_text = rfc3339(end)
    if dataset == "news":
        return f"""SELECT id, published_at, ingest_ts, symbol, related_symbols,
       publisher, author, category, headline, summary, body,
       lsa_summary, luhn_summary, textrank_summary, lexrank_summary,
       url, image, source, source_endpoint, source_run_id, raw
FROM news.articles
WHERE published_at IS NOT NULL
  AND ingest_ts IS NOT NULL
  AND published_at >= TIMESTAMPTZ '{start_text}' - INTERVAL '24 hours'
  AND published_at < TIMESTAMPTZ '{end_text}'
  AND ingest_ts >= TIMESTAMPTZ '{start_text}'
  AND ingest_ts < TIMESTAMPTZ '{end_text}'
  AND ingest_ts >= published_at
  AND ingest_ts <= published_at + INTERVAL '24 hours'
ORDER BY id"""
    if dataset == "kalshi_activity":
        after = (
            f"  AND ticker > {sql_literal(after_key[0])}\n" if after_key else ""
        )
        return f"""SELECT ticker,
       COUNT(DISTINCT trade_id) AS trades,
       COUNT(DISTINCT (created_time AT TIME ZONE 'UTC')::date) AS active_days,
       MIN(created_time) AS first_trade_ts,
       MAX(created_time) AS last_trade_ts
FROM prediction_markets.kalshi_trades
WHERE created_time >= TIMESTAMPTZ '{start_text}'
  AND created_time < TIMESTAMPTZ '{end_text}'
  AND trade_id IS NOT NULL
  AND yes_price BETWEEN 0 AND 100
{after.rstrip()}
GROUP BY ticker
ORDER BY ticker
LIMIT {page_limit}"""
    if dataset == "polymarket_activity":
        after = ""
        if after_key:
            after = (
                "  AND (condition_id, COALESCE(asset_id, '')) > "
                f"({sql_literal(after_key[0])}, {sql_literal(after_key[1])})\n"
        )
        return f"""SELECT condition_id, COALESCE(asset_id, '') AS asset_id,
       COUNT(DISTINCT trade_id) AS trades,
       COUNT(DISTINCT (ts AT TIME ZONE 'UTC')::date) AS active_days,
       MIN(ts) AS first_trade_ts,
       MAX(ts) AS last_trade_ts
FROM prediction_markets.polymarket_trades
WHERE ts >= TIMESTAMPTZ '{start_text}'
  AND ts < TIMESTAMPTZ '{end_text}'
  AND condition_id IS NOT NULL
  AND trade_id IS NOT NULL
  AND price BETWEEN 0 AND 1
{after.rstrip()}
GROUP BY condition_id, COALESCE(asset_id, '')
ORDER BY condition_id, COALESCE(asset_id, '')
LIMIT {page_limit}"""
    if dataset == "kalshi_markets":
        return f"""WITH active AS (
    SELECT DISTINCT ticker
    FROM prediction_markets.kalshi_trades
    WHERE created_time >= TIMESTAMPTZ '{start_text}'
      AND created_time < TIMESTAMPTZ '{end_text}'
)
SELECT DISTINCT ON (m.ticker)
       m.ticker, m.event_ticker, m.title, m.yes_sub_title, m.no_sub_title,
       m.market_type, m.open_time, m.close_time, m.expiration_time,
       m.ingest_ts, m.source, m.source_endpoint, m.source_run_id
FROM prediction_markets.kalshi_markets m
JOIN active a ON a.ticker = m.ticker
WHERE m.ingest_ts < TIMESTAMPTZ '{end_text}'
{('  AND m.ticker > ' + sql_literal(after_key[0])) if after_key else ''}
ORDER BY m.ticker, m.ingest_ts ASC
LIMIT {page_limit}"""
    if dataset == "polymarket_markets":
        return f"""WITH active AS (
    SELECT DISTINCT condition_id
    FROM prediction_markets.polymarket_trades
    WHERE ts >= TIMESTAMPTZ '{start_text}'
      AND ts < TIMESTAMPTZ '{end_text}'
      AND condition_id IS NOT NULL
)
SELECT DISTINCT ON (m.condition_id)
       m.id, m.condition_id, m.question, m.slug, m.outcomes,
       m.clob_token_ids, m.start_date, m.end_date,
       m.ingest_ts, m.source, m.source_endpoint, m.source_run_id
FROM prediction_markets.polymarket_markets m
JOIN active a ON a.condition_id = m.condition_id
WHERE m.ingest_ts < TIMESTAMPTZ '{end_text}'
{('  AND m.condition_id > ' + sql_literal(after_key[0])) if after_key else ''}
ORDER BY m.condition_id, m.ingest_ts ASC
LIMIT {page_limit}"""
    raise ValueError(f"unknown dataset: {dataset}")


def retrieve_with_retry(
    client: httpx.Client,
    sql: str,
    *,
    attempts: int,
    delays: list[float],
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    ledger: list[dict[str, Any]] = []
    for attempt in range(1, attempts + 1):
        started = datetime.now(timezone.utc)
        try:
            response = client.post(
                "/retrieve", json={"sql": sql, "output_format": "jsonl"}
            )
            if response.is_error:
                raise RuntimeError(
                    f"Lumid /retrieve HTTP {response.status_code}: "
                    f"{response.text[:1500]}"
                )
            receipt = response.json()
            if not isinstance(receipt, dict) or not receipt.get("materialized_uri"):
                raise RuntimeError("/retrieve returned no materialized_uri")
            ledger.append(
                {
                    "attempt": attempt,
                    "completed_at": rfc3339(datetime.now(timezone.utc)),
                    "started_at": rfc3339(started),
                    "status": "success",
                }
            )
            return receipt, ledger
        except (httpx.HTTPError, RuntimeError, ValueError) as exc:
            ledger.append(
                {
                    "attempt": attempt,
                    "completed_at": rfc3339(datetime.now(timezone.utc)),
                    "error_type": type(exc).__name__,
                    "message": str(exc)[:1000],
                    "started_at": rfc3339(started),
                    "status": "failed",
                }
            )
            if attempt >= attempts:
                raise RetrieveFailure(str(exc), ledger) from exc
            time.sleep(delays[min(attempt - 1, len(delays) - 1)])
    raise AssertionError("retry loop ended unexpectedly")


def retrieve_recorded(
    client: httpx.Client,
    sql: str,
    *,
    attempts: int,
    delays: list[float],
    context: dict[str, Any],
    all_ledgers: list[dict[str, Any]],
    retry_path: Path,
) -> dict[str, Any]:
    recorded_context = {
        **context,
        "sql_sha256": hashlib.sha256(sql.encode("utf-8")).hexdigest(),
    }
    try:
        receipt, ledger = retrieve_with_retry(
            client, sql, attempts=attempts, delays=delays
        )
    except RetrieveFailure as exc:
        all_ledgers.append({**recorded_context, "attempts": exc.ledger})
        atomic_json(retry_path, all_ledgers)
        raise
    all_ledgers.append({**recorded_context, "attempts": ledger})
    atomic_json(retry_path, all_ledgers)
    return receipt


def download(client: httpx.Client, uri: str, destination: Path) -> None:
    temporary = destination.with_suffix(destination.suffix + ".part")
    with client.stream("GET", uri) as response:
        response.raise_for_status()
        with temporary.open("wb") as handle:
            for chunk in response.iter_bytes(1024 * 1024):
                handle.write(chunk)
            handle.flush()
            os.fsync(handle.fileno())
    os.replace(temporary, destination)


def summarize(path: Path, dataset: str, start: datetime, end: datetime) -> dict[str, Any]:
    rows = 0
    invalid_json = 0
    duplicate_keys = 0
    out_of_window = 0
    keys: set[str] = set()
    timely_news = 0
    late_news = 0
    missing_time = 0
    for line_number, line in enumerate(path.open(encoding="utf-8"), start=1):
        if not line.strip():
            continue
        rows += 1
        try:
            row = json.loads(line)
        except json.JSONDecodeError as exc:
            invalid_json += 1
            raise RuntimeError(f"invalid JSON at {path}:{line_number}: {exc}") from exc
        prohibited = PROHIBITED_NAMES.intersection(key.lower() for key in row)
        if prohibited:
            raise RuntimeError(f"prohibited outcome fields in {dataset}: {sorted(prohibited)}")
        if dataset == "news":
            key = str(row.get("id") or "")
            published_text = row.get("published_at")
            ingest_text = row.get("ingest_ts")
            if not published_text or not ingest_text:
                missing_time += 1
            else:
                published = parse_utc(str(published_text))
                ingest = parse_utc(str(ingest_text))
                available = max(published, ingest)
                if not start <= available < end:
                    out_of_window += 1
                if (ingest - published).total_seconds() <= 24 * 3600:
                    timely_news += 1
                else:
                    late_news += 1
        elif dataset == "kalshi_activity":
            key = str(row.get("ticker") or "")
        elif dataset == "polymarket_activity":
            key = f"{row.get('condition_id') or ''}:{row.get('asset_id') or ''}"
        elif dataset == "kalshi_markets":
            key = str(row.get("ticker") or "")
        else:
            key = str(row.get("condition_id") or "")
        if not key:
            raise RuntimeError(f"missing natural key in {dataset} row {line_number}")
        if key in keys:
            duplicate_keys += 1
        keys.add(key)
    return {
        "rows": rows,
        "unique_keys": len(keys),
        "duplicate_key_rows": duplicate_keys,
        "invalid_json_rows": invalid_json,
        "out_of_window_rows": out_of_window,
        "news_missing_availability_rows": missing_time,
        "news_timely_rows": timely_news,
        "news_late_backfill_rows": late_news,
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("dataset", choices=DATASETS)
    parser.add_argument("--protocol", type=Path, default=DEFAULT_PROTOCOL)
    parser.add_argument("--output-root", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--timeout", type=float, default=900.0)
    parser.add_argument("--attempts", type=int, default=3)
    parser.add_argument("--retry-delays", default="30,120,300")
    parser.add_argument("--min-free-gib", type=float, default=5.0)
    parser.add_argument("--force", action="store_true")
    return parser.parse_args()


def page_last_key(path: Path, dataset: str) -> tuple[str, ...]:
    last: dict[str, Any] | None = None
    with path.open(encoding="utf-8") as handle:
        for line in handle:
            if line.strip():
                value = json.loads(line)
                if not isinstance(value, dict):
                    raise RuntimeError(f"non-object page row in {path}")
                last = value
    if last is None:
        raise RuntimeError(f"cannot derive last key from empty page {path}")
    if dataset in {"kalshi_activity", "kalshi_markets"}:
        return (str(last.get("ticker") or ""),)
    if dataset == "polymarket_activity":
        return (
            str(last.get("condition_id") or ""),
            str(last.get("asset_id") or ""),
        )
    return (str(last.get("condition_id") or ""),)


def append_file(source: Path, destination_handle: Any) -> None:
    with source.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            destination_handle.write(chunk)


def load_checkpoint(
    path: Path,
    *,
    protocol_id: str,
    protocol_sha256: str,
    dataset: str,
) -> dict[str, Any] | None:
    if not path.is_file():
        return None
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise RuntimeError(f"invalid checkpoint object: {path}")
    expected = (protocol_id, protocol_sha256, dataset)
    observed = (
        value.get("protocol_id"),
        value.get("protocol_sha256"),
        value.get("dataset"),
    )
    if observed != expected:
        raise RuntimeError(
            f"checkpoint identity mismatch at {path}: {observed!r} != {expected!r}"
        )
    if value.get("labels_or_outcomes_read") is not False:
        raise RuntimeError(f"checkpoint does not preserve outcome seal: {path}")
    return value


def verify_checkpoint_page(artifact: dict[str, Any]) -> Path:
    query_path = Path(str(artifact["path"]))
    if not query_path.is_file():
        raise RuntimeError(f"checkpoint query is missing: {query_path}")
    if sha256_file(query_path) != artifact["sha256"]:
        raise RuntimeError(f"checkpoint query hash mismatch: {query_path}")
    page_path = Path(str(artifact["data_path"]))
    if not page_path.is_file():
        raise RuntimeError(f"checkpoint page is missing: {page_path}")
    if sha256_file(page_path) != artifact["data_sha256"]:
        raise RuntimeError(f"checkpoint page hash mismatch: {page_path}")
    return page_path


def bounded_chunks(
    start: datetime, end: datetime, *, days: int = 7
) -> list[tuple[datetime, datetime]]:
    chunks: list[tuple[datetime, datetime]] = []
    cursor = start
    while cursor < end:
        chunk_end = min(cursor + timedelta(days=days), end)
        chunks.append((cursor, chunk_end))
        cursor = chunk_end
    return chunks


def merge_activity_row(
    totals: dict[tuple[str, ...], dict[str, Any]],
    row: dict[str, Any],
    dataset: str,
) -> None:
    if dataset == "kalshi_activity":
        key = (str(row.get("ticker") or ""),)
    else:
        key = (
            str(row.get("condition_id") or ""),
            str(row.get("asset_id") or ""),
        )
    if not all(key):
        raise RuntimeError(f"missing activity key: {key}")
    current = totals.get(key)
    if current is None:
        totals[key] = dict(row)
        return
    current["trades"] = int(current.get("trades", 0)) + int(row.get("trades", 0))
    current["active_days"] = int(current.get("active_days", 0)) + int(
        row.get("active_days", 0)
    )
    current["first_trade_ts"] = min(
        str(current["first_trade_ts"]), str(row["first_trade_ts"])
    )
    current["last_trade_ts"] = max(
        str(current["last_trade_ts"]), str(row["last_trade_ts"])
    )


def activity_keys(
    raw_root: Path,
    dataset: str,
    *,
    min_active_days: int,
    min_trades: int,
) -> list[str]:
    """Return only keys that can still pass the frozen activity gates."""

    activity_dataset = (
        "kalshi_activity" if dataset == "kalshi_markets" else "polymarket_activity"
    )
    manifest_path = raw_root / activity_dataset / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if manifest.get("integrity_pass") is not True:
        raise RuntimeError(f"{activity_dataset} manifest is not valid")
    path = Path(manifest["artifacts"]["data"]["path"])
    keys: set[str] = set()
    for line in path.open(encoding="utf-8"):
        if not line.strip():
            continue
        row = json.loads(line)
        if (
            int(row.get("active_days", 0)) < min_active_days
            or int(row.get("trades", 0)) < min_trades
        ):
            continue
        value = (
            row.get("ticker")
            if dataset == "kalshi_markets"
            else row.get("condition_id")
        )
        if value:
            keys.add(str(value))
    return sorted(keys)


def key_fingerprint(keys: list[str]) -> str:
    return hashlib.sha256("\n".join(keys).encode("utf-8")).hexdigest()


def validate_metadata_checkpoint_universe(
    checkpoint: dict[str, Any],
    keys: list[str],
    eligibility_filter: dict[str, Any],
) -> None:
    expected = {
        "eligibility_filter": eligibility_filter,
        "key_count": len(keys),
        "key_sha256": key_fingerprint(keys),
    }
    observed = {name: checkpoint.get(name) for name in expected}
    if observed != expected:
        raise RuntimeError(
            "metadata checkpoint key-universe mismatch: "
            f"{observed!r} != {expected!r}"
        )


def build_market_batch_sql(
    dataset: str, keys: list[str], end: datetime
) -> str:
    values = ", ".join(sql_literal(value) for value in keys)
    end_text = rfc3339(end)
    if dataset == "kalshi_markets":
        return f"""SELECT DISTINCT ON (ticker)
       ticker, event_ticker, title, yes_sub_title, no_sub_title,
       market_type, open_time, close_time, expiration_time,
       ingest_ts, source, source_endpoint, source_run_id
FROM prediction_markets.kalshi_markets
WHERE ticker IN ({values})
  AND ingest_ts < TIMESTAMPTZ '{end_text}'
ORDER BY ticker, ingest_ts ASC"""
    return f"""SELECT DISTINCT ON (condition_id)
       id, condition_id, question, slug, outcomes, clob_token_ids,
       start_date, end_date, ingest_ts, source, source_endpoint,
       source_run_id
FROM prediction_markets.polymarket_markets
WHERE condition_id IN ({values})
  AND ingest_ts < TIMESTAMPTZ '{end_text}'
ORDER BY condition_id, ingest_ts ASC"""


def main() -> None:
    args = parse_args()
    protocol = load_protocol(args.protocol)
    start = parse_utc(protocol["window"]["start_inclusive"])
    end = parse_utc(protocol["window"]["end_exclusive"])
    root = args.output_root / args.dataset
    root.mkdir(parents=True, exist_ok=True)
    manifest_path = root / "manifest.json"
    if manifest_path.is_file() and not args.force:
        existing = json.loads(manifest_path.read_text(encoding="utf-8"))
        if existing.get("integrity_pass") is True:
            print(json.dumps({"dataset": args.dataset, "status": "skipped_valid_manifest"}))
            return
        raise SystemExit(f"existing non-passing manifest requires review: {manifest_path}")
    ensure_free_space(root, args.min_free_gib)

    query_path = root / "query.sql"
    data_path = root / f"{args.dataset}.jsonl"
    receipt_path = root / "retrieve_receipt.json"
    retry_path = root / "retry_ledger.json"
    checkpoint_path = root / "checkpoint.json"
    protocol_sha256 = sha256_file(args.protocol)
    settings = ApiSettings.from_env()
    delays = [float(value) for value in args.retry_delays.split(",") if value.strip()]
    if not delays:
        raise SystemExit("--retry-delays must contain at least one value")
    started = datetime.now(timezone.utc)
    receipts: list[dict[str, Any]] = []
    all_ledgers: list[dict[str, Any]] = []
    if retry_path.is_file() and not args.force:
        previous_ledgers = json.loads(retry_path.read_text(encoding="utf-8"))
        if not isinstance(previous_ledgers, list):
            raise RuntimeError(f"invalid retry ledger: {retry_path}")
        all_ledgers = previous_ledgers
    query_artifacts: list[dict[str, Any]] = []
    with httpx.Client(
        base_url=settings.base_url,
        headers={"Authorization": f"Bearer {settings.token}"},
        timeout=httpx.Timeout(args.timeout),
        follow_redirects=True,
    ) as client:
        if args.dataset == "news":
            sql = build_sql(args.dataset, start, end)
            query_path.write_text(sql + "\n", encoding="utf-8")
            receipt = retrieve_recorded(
                client,
                sql,
                attempts=args.attempts,
                delays=delays,
                context={"page": 1},
                all_ledgers=all_ledgers,
                retry_path=retry_path,
            )
            receipts.append(compact_receipt(receipt))
            ensure_free_space(root, args.min_free_gib)
            download(client, str(receipt["materialized_uri"]), data_path)
            query_artifacts.append(
                {"page": 1, "path": str(query_path), "sha256": sha256_file(query_path)}
            )
        elif args.dataset in {"kalshi_activity", "polymarket_activity"}:
            pages_root = root / "pages"
            pages_root.mkdir(parents=True, exist_ok=True)
            totals: dict[tuple[str, ...], dict[str, Any]] = {}
            checkpoint = None if args.force else load_checkpoint(
                checkpoint_path,
                protocol_id=str(protocol["protocol_id"]),
                protocol_sha256=protocol_sha256,
                dataset=args.dataset,
            )
            completed_chunks = 0
            if checkpoint is not None:
                completed_chunks = int(checkpoint.get("completed_chunks", 0))
                receipts = list(checkpoint.get("receipts", []))
                query_artifacts = list(checkpoint.get("query_artifacts", []))
                for artifact in query_artifacts:
                    page_path = verify_checkpoint_page(artifact)
                    for line in page_path.read_text(encoding="utf-8").splitlines():
                        if line.strip():
                            merge_activity_row(totals, json.loads(line), args.dataset)
            activity_chunk_days = int(
                protocol.get("retrieval", {}).get("activity_chunk_days", 1)
            )
            activity_page_limit = int(
                protocol.get("retrieval", {}).get("activity_page_limit", 1000)
            )
            if activity_chunk_days < 1:
                raise ValueError("activity_chunk_days must be at least one")
            if not 1 <= activity_page_limit <= 1000:
                raise ValueError("activity_page_limit must be between 1 and 1000")
            for chunk_number, (chunk_start, chunk_end) in enumerate(
                bounded_chunks(start, end, days=activity_chunk_days), start=1
            ):
                if chunk_number <= completed_chunks:
                    continue
                after_key: tuple[str, ...] | None = None
                for page_number in range(1, 10001):
                    sql = build_sql(
                        args.dataset,
                        chunk_start,
                        chunk_end,
                        after_key=after_key,
                        page_limit=activity_page_limit,
                    )
                    page_query = pages_root / (
                        f"query_{chunk_number:03d}_{page_number:05d}.sql"
                    )
                    page_query.write_text(sql + "\n", encoding="utf-8")
                    context = {
                        "chunk": chunk_number,
                        "chunk_start": rfc3339(chunk_start),
                        "chunk_end_exclusive": rfc3339(chunk_end),
                        "page": page_number,
                    }
                    receipt = retrieve_recorded(
                        client,
                        sql,
                        attempts=args.attempts,
                        delays=delays,
                        context=context,
                        all_ledgers=all_ledgers,
                        retry_path=retry_path,
                    )
                    page_rows = int(receipt.get("rowcount", -1))
                    if page_rows < 0 or page_rows > activity_page_limit:
                        raise RuntimeError(
                            f"invalid {args.dataset} page rowcount: {page_rows}"
                        )
                    page_path = pages_root / (
                        f"page_{chunk_number:03d}_{page_number:05d}.jsonl"
                    )
                    ensure_free_space(root, args.min_free_gib)
                    download(client, str(receipt["materialized_uri"]), page_path)
                    for row in (
                        json.loads(line)
                        for line in page_path.read_text(encoding="utf-8").splitlines()
                        if line.strip()
                    ):
                        merge_activity_row(totals, row, args.dataset)
                    receipts.append(
                        {
                            "chunk": chunk_number,
                            "page": page_number,
                            **compact_receipt(receipt),
                        }
                    )
                    query_artifacts.append(
                        {
                            "chunk": chunk_number,
                            "chunk_start": rfc3339(chunk_start),
                            "chunk_end_exclusive": rfc3339(chunk_end),
                            "page": page_number,
                            "path": str(page_query),
                            "sha256": sha256_file(page_query),
                            "data_path": str(page_path),
                            "data_sha256": sha256_file(page_path),
                            "rowcount": page_rows,
                        }
                    )
                    if page_rows < activity_page_limit:
                        break
                    next_key = page_last_key(page_path, args.dataset)
                    if not all(next_key) or next_key == after_key:
                        raise RuntimeError(
                            f"non-advancing {args.dataset} pagination key: {next_key}"
                        )
                    after_key = next_key
                else:
                    raise RuntimeError(f"{args.dataset} exceeded pagination safety limit")
                atomic_json(
                    checkpoint_path,
                    {
                        "protocol_id": protocol["protocol_id"],
                        "protocol_sha256": protocol_sha256,
                        "dataset": args.dataset,
                        "completed_chunks": chunk_number,
                        "receipts": receipts,
                        "query_artifacts": query_artifacts,
                        "labels_or_outcomes_read": False,
                        "updated_at": rfc3339(datetime.now(timezone.utc)),
                    },
                )
            atomic_jsonl_rows(data_path, [totals[key] for key in sorted(totals)])
            atomic_json(root / "query_index.json", query_artifacts)
            query_path = root / "query_index.json"
        else:
            pages_root = root / "pages"
            pages_root.mkdir(parents=True, exist_ok=True)
            min_active_days = int(
                protocol["cohort"]["min_active_trading_days_per_market"]
            )
            min_trades = int(
                protocol["cohort"]["min_canonical_yes_trades_per_market"]
            )
            keys = activity_keys(
                args.output_root,
                args.dataset,
                min_active_days=min_active_days,
                min_trades=min_trades,
            )
            eligibility_filter = {
                "min_active_days": min_active_days,
                "min_trades": min_trades,
                "rule": "activity_key_can_pass_both_frozen_cohort_gates",
            }
            keys_sha256 = key_fingerprint(keys)
            market_batch_size = int(
                protocol.get("retrieval", {}).get("market_metadata_batch_size", 100)
            )
            if not 1 <= market_batch_size <= 1000:
                raise ValueError("market_metadata_batch_size must be between 1 and 1000")
            checkpoint = None if args.force else load_checkpoint(
                checkpoint_path,
                protocol_id=str(protocol["protocol_id"]),
                protocol_sha256=protocol_sha256,
                dataset=args.dataset,
            )
            completed_batches = 0
            if checkpoint is not None:
                validate_metadata_checkpoint_universe(
                    checkpoint, keys, eligibility_filter
                )
                completed_batches = int(checkpoint.get("completed_batches", 0))
                receipts = list(checkpoint.get("receipts", []))
                query_artifacts = list(checkpoint.get("query_artifacts", []))
            combined_temporary = data_path.with_suffix(data_path.suffix + ".part")
            with combined_temporary.open("wb") as combined:
                for artifact in query_artifacts:
                    append_file(verify_checkpoint_page(artifact), combined)
                for batch_number, offset in enumerate(
                    range(0, len(keys), market_batch_size), start=1
                ):
                    if batch_number <= completed_batches:
                        continue
                    batch = keys[offset : offset + market_batch_size]
                    sql = build_market_batch_sql(args.dataset, batch, end)
                    page_query = pages_root / f"query_{batch_number:05d}.sql"
                    page_query.write_text(sql + "\n", encoding="utf-8")
                    receipt = retrieve_recorded(
                        client,
                        sql,
                        attempts=args.attempts,
                        delays=delays,
                        context={"batch": batch_number},
                        all_ledgers=all_ledgers,
                        retry_path=retry_path,
                    )
                    page_rows = int(receipt.get("rowcount", -1))
                    if page_rows < 0 or page_rows > len(batch):
                        raise RuntimeError(
                            f"invalid {args.dataset} batch rowcount: {page_rows}"
                        )
                    page_path = pages_root / f"page_{batch_number:05d}.jsonl"
                    ensure_free_space(root, args.min_free_gib)
                    download(client, str(receipt["materialized_uri"]), page_path)
                    append_file(page_path, combined)
                    receipts.append(
                        {"batch": batch_number, **compact_receipt(receipt)}
                    )
                    query_artifacts.append(
                        {
                            "batch": batch_number,
                            "keys": len(batch),
                            "path": str(page_query),
                            "sha256": sha256_file(page_query),
                            "data_path": str(page_path),
                            "data_sha256": sha256_file(page_path),
                            "rowcount": page_rows,
                        }
                    )
                    atomic_json(
                        checkpoint_path,
                        {
                            "protocol_id": protocol["protocol_id"],
                            "protocol_sha256": protocol_sha256,
                            "dataset": args.dataset,
                            "completed_batches": batch_number,
                            "eligibility_filter": eligibility_filter,
                            "key_count": len(keys),
                            "key_sha256": keys_sha256,
                            "receipts": receipts,
                            "query_artifacts": query_artifacts,
                            "labels_or_outcomes_read": False,
                            "updated_at": rfc3339(datetime.now(timezone.utc)),
                        },
                    )
                combined.flush()
                os.fsync(combined.fileno())
            os.replace(combined_temporary, data_path)
            atomic_json(root / "query_index.json", query_artifacts)
            query_path = root / "query_index.json"

    atomic_json(receipt_path, receipts)
    atomic_json(retry_path, all_ledgers)

    summary = summarize(data_path, args.dataset, start, end)
    receipt_rowcount = sum(int(value.get("rowcount", -1)) for value in receipts)
    expected_output_rows = (
        summary["unique_keys"]
        if args.dataset in {"kalshi_activity", "polymarket_activity"}
        else receipt_rowcount
    )
    integrity_pass = (
        summary["rows"] == expected_output_rows
        and summary["duplicate_key_rows"] == 0
        and summary["invalid_json_rows"] == 0
        and summary["out_of_window_rows"] == 0
        and summary["news_missing_availability_rows"] == 0
    )
    manifest = {
        "protocol_id": protocol["protocol_id"],
        "purpose": "label-blind historical feasibility input",
        "dataset": args.dataset,
        "window": protocol["window"],
        "source": {
            "base_url": settings.base_url,
            "endpoint": "/retrieve",
            "retrieve_run_ids": [value.get("run_id") for value in receipts],
        },
        "started_at": rfc3339(started),
        "completed_at": rfc3339(datetime.now(timezone.utc)),
        "labels_or_outcomes_read": False,
        "summary": summary,
        "retrieve_rowcount": receipt_rowcount,
        "pages": len(receipts),
        "integrity_pass": integrity_pass,
        "artifacts": {
            "data": {"path": str(data_path), "sha256": sha256_file(data_path), "bytes": data_path.stat().st_size},
            "query": {"path": str(query_path), "sha256": sha256_file(query_path)},
            "receipt": {"path": str(receipt_path), "sha256": sha256_file(receipt_path)},
            "retry_ledger": {"path": str(retry_path), "sha256": sha256_file(retry_path)},
            **(
                {
                    "checkpoint": {
                        "path": str(checkpoint_path),
                        "sha256": sha256_file(checkpoint_path),
                    }
                }
                if checkpoint_path.is_file()
                else {}
            ),
        },
    }
    atomic_json(manifest_path, manifest)
    print(json.dumps(manifest, indent=2, sort_keys=True))
    if not integrity_pass:
        raise SystemExit(f"{args.dataset} integrity checks failed")


if __name__ == "__main__":
    main()
