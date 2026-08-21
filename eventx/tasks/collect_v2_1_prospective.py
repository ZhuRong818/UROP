"""Collect the prospective EventX v2.1 market, news, KOL, and metadata streams.

The collector is label-blind and append-only. It stores raw provider records with
retrieval provenance, uses a SQLite key registry for restart-safe deduplication, and
stops automatically at the active protocol's holdout boundary.
"""

from __future__ import annotations

import argparse
from collections.abc import Iterable
from datetime import datetime, timedelta, timezone
import fcntl
import hashlib
import json
import logging
from pathlib import Path
import signal
import sqlite3
import threading
import time
from typing import Any
from urllib.parse import urlsplit, urlunsplit

import httpx
from websockets.sync.client import connect as websocket_connect

from eventx.ingest.client import FindataClient
from eventx.settings import ApiSettings, REPO_ROOT


DEFAULT_PROTOCOL = REPO_ROOT / "eventx" / "release" / "v2_1" / "protocol.json"
DEFAULT_ROOT = REPO_ROOT / "data" / "v2_1" / "prospective"
DEFAULT_MARKET_ROSTER = REPO_ROOT / "data" / "v1" / "curated" / "markets.jsonl"
SOURCE_FILES = {
    "prediction_market_stream": "prediction_market_stream.jsonl",
    "news_stream": "news_stream.jsonl",
    "news_latest": "news_latest.jsonl",
    "kol_tweets": "kol_tweets.jsonl",
    "market_events": "market_events.jsonl",
    "trades_polymarket": "trades_polymarket.jsonl",
    "trades_kalshi": "trades_kalshi.jsonl",
}
ROW_KEYS = ("data", "articles", "tweets", "events", "markets", "results", "items")
TIMESTAMP_KEYS = (
    "ts",
    "published_at",
    "publishedAt",
    "published_date",
    "publishedDate",
    "created_at",
    "createdAt",
    "created_time",
    "date",
    "timestamp",
)

log = logging.getLogger(__name__)


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def rfc3339(value: datetime) -> str:
    return value.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


def parse_utc(value: Any) -> datetime | None:
    if value in (None, ""):
        return None
    try:
        parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def load_object(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text())
    if not isinstance(value, dict):
        raise ValueError(f"{path} must contain a JSON object")
    return value


def canonical_json(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), default=str)


def content_hash(value: Any) -> str:
    return hashlib.sha256(canonical_json(value).encode()).hexdigest()


def extract_rows(value: Any) -> list[dict[str, Any]]:
    if isinstance(value, list):
        return [row for row in value if isinstance(row, dict)]
    if not isinstance(value, dict):
        return []
    for key in ROW_KEYS:
        rows = value.get(key)
        if isinstance(rows, list):
            return [row for row in rows if isinstance(row, dict)]
    return [value]


def event_timestamp(row: dict[str, Any]) -> datetime | None:
    for key in TIMESTAMP_KEYS:
        parsed = parse_utc(row.get(key))
        if parsed is not None:
            return parsed
    return None


def first_value(row: dict[str, Any], keys: Iterable[str]) -> str | None:
    for key in keys:
        value = row.get(key)
        if value not in (None, ""):
            return str(value)
    return None


def record_key(source: str, row: dict[str, Any], *, snapshot_bucket: str | None = None) -> str:
    logical_source = "news" if source in {"news_latest", "news_stream"} else source
    if logical_source == "news":
        identifier = first_value(row, ("article_id", "id", "uuid", "url"))
    elif source == "kol_tweets":
        identifier = first_value(row, ("tweet_id", "id", "rest_id", "url"))
    elif source == "market_events":
        identifier = first_value(
            row,
            ("event_id", "id", "condition_id", "market_id", "ticker"),
        )
    else:
        identifier = first_value(
            row,
            (
                "trade_id",
                "id",
                "transaction_hash",
                "order_id",
                "sequence",
            ),
        )
    if source == "market_events":
        material = {
            "bucket": snapshot_bucket,
            "content": content_hash(row),
            "id": identifier,
        }
    elif identifier:
        material = {
            "content": content_hash(row),
            "id": identifier,
        }
    else:
        material = {"content": content_hash(row)}
    return hashlib.sha256(f"{logical_source}:{canonical_json(material)}".encode()).hexdigest()


def websocket_url(base_url: str, path: str) -> str:
    parts = urlsplit(base_url)
    scheme = "wss" if parts.scheme == "https" else "ws"
    joined_path = f"{parts.path.rstrip('/')}/{path.lstrip('/')}"
    return urlunsplit((scheme, parts.netloc, joined_path, "", ""))


class ProspectiveStore:
    """Raw JSONL plus SQLite deduplication/checkpoint registry."""

    def __init__(self, root: Path, protocol_id: str) -> None:
        self.root = root
        self.raw_dir = root / "raw"
        self.state_dir = root / "state"
        self.raw_dir.mkdir(parents=True, exist_ok=True)
        self.state_dir.mkdir(parents=True, exist_ok=True)
        self.protocol_id = protocol_id
        self._lock = threading.RLock()
        self._connection = sqlite3.connect(
            self.state_dir / "collector.sqlite3",
            check_same_thread=False,
        )
        self._connection.execute("PRAGMA journal_mode=WAL")
        self._connection.execute("PRAGMA synchronous=FULL")
        self._connection.executescript(
            """
            CREATE TABLE IF NOT EXISTS seen_records (
                source TEXT NOT NULL,
                record_key TEXT PRIMARY KEY,
                retrieved_at TEXT NOT NULL,
                event_ts TEXT
            );
            CREATE TABLE IF NOT EXISTS checkpoints (
                name TEXT PRIMARY KEY,
                value TEXT NOT NULL,
                updated_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS source_status (
                source TEXT PRIMARY KEY,
                records_written INTEGER NOT NULL DEFAULT 0,
                duplicates_skipped INTEGER NOT NULL DEFAULT 0,
                errors INTEGER NOT NULL DEFAULT 0,
                reconnects INTEGER NOT NULL DEFAULT 0,
                last_event_at TEXT,
                last_success_at TEXT,
                last_error TEXT
            );
            CREATE TABLE IF NOT EXISTS candidate_markets (
                venue TEXT NOT NULL,
                market_id TEXT NOT NULL,
                outcome_id TEXT,
                source TEXT NOT NULL,
                added_at TEXT NOT NULL,
                PRIMARY KEY (venue, market_id)
            );
            """
        )
        for source in SOURCE_FILES:
            self._connection.execute(
                "INSERT OR IGNORE INTO source_status(source) VALUES (?)",
                (source,),
            )
        self._connection.commit()

    def close(self) -> None:
        with self._lock:
            self._connection.commit()
            self._connection.close()

    def checkpoint(self, name: str) -> str | None:
        with self._lock:
            row = self._connection.execute(
                "SELECT value FROM checkpoints WHERE name = ?",
                (name,),
            ).fetchone()
        return str(row[0]) if row else None

    def add_candidate(
        self,
        venue: str,
        market_id: str,
        *,
        outcome_id: str | None,
        source: str,
    ) -> bool:
        with self._lock:
            cursor = self._connection.execute(
                """
                INSERT OR IGNORE INTO candidate_markets(
                    venue, market_id, outcome_id, source, added_at
                )
                VALUES (?, ?, ?, ?, ?)
                """,
                (venue, market_id, outcome_id, source, rfc3339(utc_now())),
            )
            self._connection.commit()
        return cursor.rowcount > 0

    def candidates(self) -> list[tuple[str, str]]:
        with self._lock:
            rows = self._connection.execute(
                """
                SELECT venue, market_id
                FROM candidate_markets
                ORDER BY venue, market_id
                """
            ).fetchall()
        return [(str(row[0]), str(row[1])) for row in rows]

    def set_checkpoint(self, name: str, value: str) -> None:
        now = rfc3339(utc_now())
        with self._lock:
            self._connection.execute(
                """
                INSERT INTO checkpoints(name, value, updated_at)
                VALUES (?, ?, ?)
                ON CONFLICT(name) DO UPDATE SET
                    value = excluded.value,
                    updated_at = excluded.updated_at
                """,
                (name, value, now),
            )
            self._connection.commit()

    def append(
        self,
        source: str,
        row: dict[str, Any],
        *,
        endpoint: str,
        snapshot_bucket: str | None = None,
    ) -> bool:
        retrieved_at = rfc3339(utc_now())
        timestamp = event_timestamp(row)
        timestamp_text = rfc3339(timestamp) if timestamp else None
        key = record_key(source, row, snapshot_bucket=snapshot_bucket)
        envelope = {
            "_event_ts": timestamp_text,
            "_protocol_id": self.protocol_id,
            "_record_key": key,
            "_retrieved_at": retrieved_at,
            "_source": source,
            "_source_endpoint": endpoint,
            "record": row,
        }
        with self._lock:
            cursor = self._connection.execute(
                """
                INSERT OR IGNORE INTO seen_records(source, record_key, retrieved_at, event_ts)
                VALUES (?, ?, ?, ?)
                """,
                (source, key, retrieved_at, timestamp_text),
            )
            if cursor.rowcount == 0:
                self._connection.execute(
                    """
                    UPDATE source_status
                    SET duplicates_skipped = duplicates_skipped + 1
                    WHERE source = ?
                    """,
                    (source,),
                )
                self._connection.commit()
                return False
            path = self.raw_dir / SOURCE_FILES[source]
            try:
                with path.open("a") as handle:
                    handle.write(json.dumps(envelope, default=str, sort_keys=True) + "\n")
                    handle.flush()
            except Exception:
                self._connection.rollback()
                raise
            self._connection.execute(
                """
                UPDATE source_status
                SET records_written = records_written + 1,
                    last_event_at = COALESCE(?, last_event_at),
                    last_success_at = ?,
                    last_error = NULL
                WHERE source = ?
                """,
                (timestamp_text, retrieved_at, source),
            )
            self._connection.commit()
        return True

    def success(self, source: str) -> None:
        now = rfc3339(utc_now())
        with self._lock:
            self._connection.execute(
                """
                UPDATE source_status
                SET last_success_at = ?, last_error = NULL
                WHERE source = ?
                """,
                (now, source),
            )
            self._connection.commit()

    def failure(self, source: str, message: str, *, reconnect: bool = False) -> None:
        sanitized = message[:500]
        with self._lock:
            self._connection.execute(
                """
                UPDATE source_status
                SET errors = errors + 1,
                    reconnects = reconnects + ?,
                    last_error = ?
                WHERE source = ?
                """,
                (int(reconnect), sanitized, source),
            )
            self._connection.commit()

    def health(self, *, started_at: str, stop_at: str) -> dict[str, Any]:
        with self._lock:
            rows = self._connection.execute(
                """
                SELECT source, records_written, duplicates_skipped, errors, reconnects,
                       last_event_at, last_success_at, last_error
                FROM source_status
                ORDER BY source
                """
            ).fetchall()
            checkpoints = dict(
                self._connection.execute(
                    "SELECT name, value FROM checkpoints ORDER BY name"
                ).fetchall()
            )
            candidate_count = int(
                self._connection.execute(
                    "SELECT COUNT(*) FROM candidate_markets"
                ).fetchone()[0]
            )
        sources = {
            row[0]: {
                "duplicates_skipped": row[2],
                "errors": row[3],
                "last_error": row[7],
                "last_event_at": row[5],
                "last_success_at": row[6],
                "reconnects": row[4],
                "records_written": row[1],
                "freshness_seconds": (
                    max(
                        0.0,
                        (utc_now() - parse_utc(row[5])).total_seconds(),
                    )
                    if parse_utc(row[5]) is not None
                    else None
                ),
            }
            for row in rows
        }
        return {
            "candidate_markets": candidate_count,
            "checkpoints": checkpoints,
            "generated_at": rfc3339(utc_now()),
            "label_blind": True,
            "labels_read": [],
            "protocol_id": self.protocol_id,
            "sources": sources,
            "started_at": started_at,
            "stop_at": stop_at,
        }


class ProspectiveCollector:
    def __init__(
        self,
        *,
        protocol: dict[str, Any],
        root: Path,
        market_roster: Path,
        poll_seconds: float,
        metadata_seconds: float,
        stop_at: datetime,
        enable_news_websocket: bool,
        enable_pm_sse: bool,
    ) -> None:
        self.protocol = protocol
        self.protocol_id = str(protocol["protocol_id"])
        self.settings = ApiSettings.from_env()
        self.store = ProspectiveStore(root, self.protocol_id)
        self.market_roster = market_roster
        self.poll_seconds = poll_seconds
        self.metadata_seconds = metadata_seconds
        self.stop_at = stop_at
        self.enable_news_websocket = enable_news_websocket
        self.enable_pm_sse = enable_pm_sse
        self.started_at = rfc3339(utc_now())
        self.stop_event = threading.Event()
        self.sse_thread = threading.Thread(
            target=self._run_prediction_market_stream,
            name="prediction-market-sse",
            daemon=True,
        )
        self.news_thread = threading.Thread(
            target=self._run_news_stream,
            name="news-websocket",
            daemon=True,
        )
        self.last_metadata_poll = 0.0
        self.last_health_write = 0.0
        warmup_start = protocol["windows"]["warmup"]["start"]
        existing_news_since = parse_utc(self.store.checkpoint("news_since"))
        if (
            existing_news_since is None
            or existing_news_since > utc_now() + timedelta(minutes=5)
        ):
            self.store.set_checkpoint("news_since", warmup_start)
        self._load_initial_candidates()
        self.trade_candidates = self.store.candidates()
        self.trade_index = int(self.store.checkpoint("trade_candidate_index") or 0)

    def _load_initial_candidates(self) -> None:
        required_close = parse_utc(
            self.protocol["cohort"]["thresholds"]["scheduled_close_at_or_after"]
        )
        assert required_close is not None
        terminal = {"closed", "determined", "finalized", "resolved", "settled"}
        if not self.market_roster.is_file():
            raise FileNotFoundError(self.market_roster)
        with self.market_roster.open() as handle:
            for line in handle:
                if not line.strip():
                    continue
                row = json.loads(line)
                if row.get("is_binary") is not True or row.get("canonical_side") is not True:
                    continue
                close = parse_utc(row.get("scheduled_close_ts"))
                if close is None or close < required_close:
                    continue
                if str(row.get("status") or "").lower() in terminal:
                    continue
                venue = str(row.get("venue") or "")
                market_id = str(row.get("market_id") or "")
                if venue not in {"polymarket", "kalshi"} or not market_id:
                    continue
                self.store.add_candidate(
                    venue,
                    market_id,
                    outcome_id=(
                        str(row["outcome_id"]) if row.get("outcome_id") is not None else None
                    ),
                    source="historical_metadata_prefilter",
                )

    def request_stop(self, *_args: object) -> None:
        self.stop_event.set()

    def _write_health(self) -> None:
        health = self.store.health(
            started_at=self.started_at,
            stop_at=rfc3339(self.stop_at),
        )
        health["optional_transports"] = {
            "news_websocket_enabled": self.enable_news_websocket,
            "prediction_market_sse_enabled": self.enable_pm_sse,
        }
        path = self.store.root / "health.json"
        temporary = path.with_suffix(".json.tmp")
        temporary.write_text(json.dumps(health, indent=2, sort_keys=True) + "\n")
        temporary.replace(path)

    def _run_prediction_market_stream(self) -> None:
        source = "prediction_market_stream"
        endpoint = "/prediction-markets/stream"
        delay = 1.0
        headers = {
            "Accept": "text/event-stream",
            "Authorization": f"Bearer {self.settings.token}",
        }
        while not self.stop_event.is_set() and utc_now() < self.stop_at:
            event_name: str | None = None
            data_lines: list[str] = []
            try:
                timeout = httpx.Timeout(connect=30.0, read=45.0, write=30.0, pool=30.0)
                with httpx.Client(
                    base_url=self.settings.base_url,
                    headers=headers,
                    timeout=timeout,
                ) as client:
                    with client.stream("GET", endpoint) as response:
                        response.raise_for_status()
                        self.store.success(source)
                        delay = 1.0
                        for line in response.iter_lines():
                            if self.stop_event.is_set() or utc_now() >= self.stop_at:
                                return
                            if line.startswith(":"):
                                self.store.success(source)
                                continue
                            if not line:
                                if not data_lines:
                                    continue
                                raw = "\n".join(data_lines)
                                data_lines = []
                                try:
                                    value = json.loads(raw)
                                except json.JSONDecodeError:
                                    value = {"event": event_name, "raw": raw}
                                if isinstance(value, dict):
                                    channel = str(value.get("channel") or event_name or "")
                                    if channel not in {"heartbeat", "subscribed"}:
                                        self.store.append(
                                            source,
                                            value,
                                            endpoint=endpoint,
                                        )
                                    else:
                                        self.store.success(source)
                                event_name = None
                                continue
                            if line.startswith("event:"):
                                event_name = line[6:].strip()
                            elif line.startswith("data:"):
                                data_lines.append(line[5:].lstrip())
            except Exception as exc:
                self.store.failure(source, f"{type(exc).__name__}: {exc}", reconnect=True)
                log.warning("prediction-market stream disconnected: %s", exc)
                self.stop_event.wait(delay)
                delay = min(delay * 2, 60.0)

    def _run_news_stream(self) -> None:
        source = "news_stream"
        endpoint = "/ws/news"
        url = websocket_url(self.settings.base_url, endpoint)
        delay = 1.0
        while not self.stop_event.is_set() and utc_now() < self.stop_at:
            try:
                with websocket_connect(
                    url,
                    additional_headers={
                        "Authorization": f"Bearer {self.settings.token}",
                    },
                    open_timeout=30,
                    close_timeout=5,
                    ping_interval=20,
                    ping_timeout=20,
                ) as connection:
                    self.store.success(source)
                    delay = 1.0
                    while not self.stop_event.is_set() and utc_now() < self.stop_at:
                        try:
                            raw = connection.recv(timeout=45)
                        except TimeoutError:
                            self.store.success(source)
                            continue
                        if raw is None:
                            break
                        if isinstance(raw, bytes):
                            raw = raw.decode("utf-8", errors="replace")
                        try:
                            value = json.loads(raw)
                        except json.JSONDecodeError:
                            value = {"raw": raw}
                        if isinstance(value, dict):
                            nested = value.get("data") or value.get("article")
                            rows = [nested] if isinstance(nested, dict) else [value]
                        else:
                            rows = extract_rows(value)
                        for row in rows:
                            self.store.append(source, row, endpoint=endpoint)
            except Exception as exc:
                self.store.failure(source, f"{type(exc).__name__}: {exc}", reconnect=True)
                log.warning("news stream disconnected: %s", exc)
                self.stop_event.wait(delay)
                delay = min(delay * 2, 60.0)

    def _poll_news(self, client: FindataClient) -> None:
        source = "news_latest"
        endpoint = "/news/latest"
        since = self.store.checkpoint("news_since")
        response = client.get(endpoint, since=since, limit=200)
        rows = extract_rows(response)
        latest = parse_utc(since)
        cursor_ceiling = utc_now() + timedelta(minutes=5)
        for row in rows:
            self.store.append(source, row, endpoint=endpoint)
            timestamp = event_timestamp(row)
            if (
                timestamp is not None
                and timestamp <= cursor_ceiling
                and (latest is None or timestamp > latest)
            ):
                latest = timestamp
        if latest is not None:
            overlap = latest - timedelta(minutes=5)
            self.store.set_checkpoint("news_since", rfc3339(overlap))
        self.store.success(source)

    def _poll_kols(self, client: FindataClient) -> None:
        source = "kol_tweets"
        endpoint = "/kols/tweets"
        response = client.get(endpoint, limit=1000)
        for row in extract_rows(response):
            self.store.append(source, row, endpoint=endpoint)
        self.store.success(source)

    def _poll_market_events(self, client: FindataClient) -> None:
        source = "market_events"
        endpoint = "/prediction-markets/events"
        snapshot_bucket = utc_now().strftime("%Y-%m-%dT%H")
        offset = 0
        limit = 200
        required_close = parse_utc(
            self.protocol["cohort"]["thresholds"]["scheduled_close_at_or_after"]
        )
        assert required_close is not None
        while not self.stop_event.is_set():
            response = client.get(
                endpoint,
                status="open",
                limit=limit,
                offset=offset,
            )
            rows = extract_rows(response)
            for row in rows:
                self.store.append(
                    source,
                    row,
                    endpoint=endpoint,
                    snapshot_bucket=snapshot_bucket,
                )
                close = parse_utc(row.get("end_date") or row.get("close_time"))
                if close is None or close < required_close:
                    continue
                if row.get("closed") is True or row.get("active") is False:
                    continue
                market_ids = row.get("market_ids") or []
                if isinstance(market_ids, str):
                    market_ids = [market_ids]
                if not isinstance(market_ids, list):
                    continue
                for value in market_ids:
                    market_id = str(value or "")
                    if not market_id:
                        continue
                    venue = "polymarket" if market_id.startswith("0x") else "kalshi"
                    self.store.add_candidate(
                        venue,
                        market_id,
                        outcome_id=None,
                        source="prospective_event_snapshot",
                    )
            if len(rows) < limit:
                break
            offset += limit
        self.store.set_checkpoint("market_events_snapshot", snapshot_bucket)
        self.store.success(source)
        self.trade_candidates = self.store.candidates()

    def _poll_one_candidate_trade_history(self, client: FindataClient) -> None:
        if not self.trade_candidates:
            return
        index = self.trade_index % len(self.trade_candidates)
        venue, market_id = self.trade_candidates[index]
        self.trade_index = (index + 1) % len(self.trade_candidates)
        self.store.set_checkpoint("trade_candidate_index", str(self.trade_index))

        source = f"trades_{venue}"
        endpoint = f"/prediction-markets/trades/{venue}/{market_id}"
        cursor_name = f"trade_since:{venue}:{market_id}"
        since_text = self.store.checkpoint(cursor_name) or self.protocol["windows"]["warmup"]["start"]
        since = parse_utc(since_text)
        assert since is not None
        window_end = utc_now()
        page_to = window_end
        previous_oldest: datetime | None = None
        complete = False
        for _ in range(20):
            response = client.get(
                endpoint,
                **{
                    "from": rfc3339(since),
                    "to": rfc3339(page_to),
                    "limit": 1000,
                },
            )
            rows = extract_rows(response)
            timestamps: list[datetime] = []
            for raw_row in rows:
                row = {
                    **raw_row,
                    "market_id": raw_row.get("market_id") or market_id,
                    "venue": raw_row.get("venue") or venue,
                }
                self.store.append(source, row, endpoint=endpoint)
                timestamp = event_timestamp(row)
                if timestamp is not None and timestamp <= window_end + timedelta(minutes=5):
                    timestamps.append(timestamp)
            if len(rows) < 1000:
                complete = True
                break
            if not timestamps:
                break
            oldest = min(timestamps)
            if oldest <= since:
                complete = True
                break
            if previous_oldest is not None and oldest >= previous_oldest:
                break
            previous_oldest = oldest
            page_to = oldest
        if complete:
            self.store.set_checkpoint(
                cursor_name,
                rfc3339(max(since, window_end - timedelta(minutes=5))),
            )
        else:
            self.store.failure(
                source,
                f"incomplete incremental page walk for {market_id}; cursor retained",
            )
        self.store.success(source)

    def _run_poll(self, source: str, function: Any, client: FindataClient) -> None:
        try:
            function(client)
        except Exception as exc:
            self.store.failure(source, f"{type(exc).__name__}: {exc}")
            log.exception("%s poll failed", source)

    def run(self, *, smoke_seconds: float | None = None) -> None:
        smoke_end = time.monotonic() + smoke_seconds if smoke_seconds else None
        signal.signal(signal.SIGTERM, self.request_stop)
        signal.signal(signal.SIGINT, self.request_stop)
        if self.enable_pm_sse:
            self.sse_thread.start()
        if self.enable_news_websocket:
            self.news_thread.start()
        next_poll = 0.0
        try:
            with FindataClient(rpm=60, timeout=60.0) as client:
                while not self.stop_event.is_set() and utc_now() < self.stop_at:
                    if smoke_end is not None and time.monotonic() >= smoke_end:
                        break
                    now_monotonic = time.monotonic()
                    if now_monotonic >= next_poll:
                        self._run_poll("news_latest", self._poll_news, client)
                        self._run_poll("kol_tweets", self._poll_kols, client)
                        next_poll = time.monotonic() + self.poll_seconds
                    if (
                        self.last_metadata_poll == 0.0
                        or now_monotonic - self.last_metadata_poll >= self.metadata_seconds
                    ):
                        self._run_poll("market_events", self._poll_market_events, client)
                        self.last_metadata_poll = time.monotonic()
                    if self.trade_candidates:
                        next_venue = self.trade_candidates[
                            self.trade_index % len(self.trade_candidates)
                        ][0]
                        self._run_poll(
                            f"trades_{next_venue}",
                            self._poll_one_candidate_trade_history,
                            client,
                        )
                    if time.monotonic() - self.last_health_write >= 10:
                        self._write_health()
                        self.last_health_write = time.monotonic()
                    self.stop_event.wait(0.05)
        finally:
            self.stop_event.set()
            if self.enable_pm_sse:
                self.sse_thread.join(timeout=10)
            if self.enable_news_websocket:
                self.news_thread.join(timeout=10)
            self._write_health()
            self.store.close()


def acquire_process_lock(root: Path) -> Any:
    root.mkdir(parents=True, exist_ok=True)
    handle = (root / "collector.lock").open("w")
    try:
        fcntl.flock(handle, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except BlockingIOError as exc:
        handle.close()
        raise SystemExit(f"collector already running for {root}") from exc
    handle.write(str(__import__("os").getpid()) + "\n")
    handle.flush()
    return handle


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--protocol", type=Path, default=DEFAULT_PROTOCOL)
    parser.add_argument("--root", type=Path, default=DEFAULT_ROOT)
    parser.add_argument("--market-roster", type=Path, default=DEFAULT_MARKET_ROSTER)
    parser.add_argument("--poll-seconds", type=float, default=60.0)
    parser.add_argument("--metadata-seconds", type=float, default=6 * 60 * 60)
    parser.add_argument(
        "--smoke-seconds",
        type=float,
        help="Stop after this many seconds; intended for temporary-root validation",
    )
    parser.add_argument(
        "--enable-news-websocket",
        action="store_true",
        help="Enable the optional news WebSocket; disabled while the proxy rejects upgrades",
    )
    parser.add_argument(
        "--enable-pm-sse",
        action="store_true",
        help="Enable the optional PM SSE; disabled while the proxy does not complete handshakes",
    )
    args = parser.parse_args()

    protocol = load_object(args.protocol)
    if protocol.get("status") != "preregistered_labels_uninspected":
        raise SystemExit("active protocol is not label-uninspected")
    if protocol.get("historical_reuse", {}).get("archive_replaces_prospective_windows") is not False:
        raise SystemExit("protocol does not preserve prospective collection")
    stop_at = parse_utc(protocol["windows"]["holdout"]["end_exclusive"])
    assert stop_at is not None
    if utc_now() >= stop_at:
        raise SystemExit(f"collection window already closed at {rfc3339(stop_at)}")
    if args.poll_seconds <= 0 or args.metadata_seconds <= 0:
        raise SystemExit("poll intervals must be positive")

    process_lock = acquire_process_lock(args.root)
    try:
        collector = ProspectiveCollector(
            protocol=protocol,
            root=args.root,
            market_roster=args.market_roster,
            poll_seconds=args.poll_seconds,
            metadata_seconds=args.metadata_seconds,
            stop_at=stop_at,
            enable_news_websocket=args.enable_news_websocket,
            enable_pm_sse=args.enable_pm_sse,
        )
        collector.run(smoke_seconds=args.smoke_seconds)
    finally:
        process_lock.close()


if __name__ == "__main__":
    main()
