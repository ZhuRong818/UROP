"""Collect Lumid news under the frozen EventX v2.3 censoring contract.

This collector is label-blind and append-only. It records every retrieval attempt,
refuses to advance the news checkpoint on a response-cap alarm, and derives the
primary feature availability time as max(published_at, first_seen_at).

It is intentionally separate from the running legacy v2.1 collector. Launching or
replacing a daemon is an explicit operational action; importing or verifying this
module never changes the live collector.
"""

from __future__ import annotations

import argparse
from datetime import datetime, timedelta, timezone
import fcntl
import hashlib
import json
from pathlib import Path
import signal
import sqlite3
import time
from typing import Any, Callable

from eventx.ingest.client import FindataClient
from eventx.settings import REPO_ROOT


DEFAULT_CONTRACT = (
    REPO_ROOT / "eventx" / "release" / "v2_3" / "news_collection_contract.json"
)
DEFAULT_ROOT = REPO_ROOT / "data" / "v2_3" / "prospective_news"
DEFAULT_STOP_AT = "2026-10-22T00:00:00Z"
ROW_KEYS = ("data", "articles", "results", "items")
IDENTIFIER_KEYS = ("article_id", "id", "uuid", "url")
PUBLISHED_KEYS = (
    "published_at",
    "publishedAt",
    "published_date",
    "publishedDate",
)


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def rfc3339(value: datetime) -> str:
    return value.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


def parse_utc(value: Any) -> datetime | None:
    if value in (None, ""):
        return None
    try:
        parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except (TypeError, ValueError):
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def canonical_json(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), default=str)


def sha256_json(value: Any) -> str:
    return hashlib.sha256(canonical_json(value).encode()).hexdigest()


def load_object(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text())
    if not isinstance(value, dict):
        raise ValueError(f"{path} must contain a JSON object")
    return value


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


def first_value(row: dict[str, Any], keys: tuple[str, ...]) -> str | None:
    for key in keys:
        value = row.get(key)
        if value not in (None, ""):
            return str(value)
    return None


def published_at(row: dict[str, Any]) -> datetime | None:
    return parse_utc(first_value(row, PUBLISHED_KEYS))


def news_record_key(row: dict[str, Any]) -> str:
    identifier = first_value(row, IDENTIFIER_KEYS)
    material = {
        "content_sha256": sha256_json(row),
        "identifier": identifier,
    }
    return hashlib.sha256(f"lumid_news:{canonical_json(material)}".encode()).hexdigest()


def availability_time(
    publication_time: datetime | None,
    first_seen_at: datetime,
) -> datetime | None:
    """Return the frozen primary availability time without retrospective backdating."""

    if publication_time is None:
        return None
    return max(publication_time, first_seen_at)


def is_cap_alarm(row_count: int, contract: dict[str, Any]) -> bool:
    cap = int(contract["collection"]["response_cap_rows"])
    return row_count >= cap


def validate_contract(contract: dict[str, Any]) -> None:
    collection = contract.get("collection", {})
    censoring = contract.get("censoring", {})
    availability = contract.get("availability", {})
    if collection.get("endpoint") != "/news/latest":
        raise ValueError("v2.3 contract must use /news/latest")
    if collection.get("poll_seconds") != 60:
        raise ValueError("v2.3 news polling must be fixed at 60 seconds")
    if collection.get("response_cap_rows") != 200:
        raise ValueError("v2.3 response-cap alarm must be fixed at 200 rows")
    if collection.get("max_success_gap_seconds") != 300:
        raise ValueError("v2.3 maximum successful-request gap must be 300 seconds")
    if censoring.get("checkpoint_advances_on_cap_alarm") is not False:
        raise ValueError("checkpoint advancement on capped responses is prohibited")
    if availability.get("primary_feature_time") != "max(published_at, first_seen_at)":
        raise ValueError("point-in-time news availability rule mismatch")


class NewsStore:
    """Append-only news/request files plus a restart-safe SQLite state registry."""

    def __init__(self, root: Path, contract: dict[str, Any]) -> None:
        self.root = root
        self.raw_dir = root / "raw"
        self.state_dir = root / "state"
        self.raw_dir.mkdir(parents=True, exist_ok=True)
        self.state_dir.mkdir(parents=True, exist_ok=True)
        self.contract = contract
        self.contract_id = str(contract["contract_id"])
        self.protocol_id = str(contract["protocol_id"])
        self.connection = sqlite3.connect(self.state_dir / "news_collector.sqlite3")
        self.connection.execute("PRAGMA journal_mode=WAL")
        self.connection.execute("PRAGMA synchronous=FULL")
        self.connection.executescript(
            """
            CREATE TABLE IF NOT EXISTS state (
                name TEXT PRIMARY KEY,
                value TEXT NOT NULL,
                updated_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS news_seen (
                record_key TEXT PRIMARY KEY,
                first_seen_at TEXT NOT NULL,
                published_at TEXT,
                available_at TEXT,
                content_sha256 TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS timestamp_conflicts (
                record_key TEXT NOT NULL,
                prior_published_at TEXT,
                observed_published_at TEXT,
                observed_at TEXT NOT NULL,
                content_sha256 TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS censoring_intervals (
                interval_id TEXT PRIMARY KEY,
                start_at TEXT NOT NULL,
                end_at TEXT NOT NULL,
                reason TEXT NOT NULL,
                opened_at TEXT NOT NULL,
                status TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS counters (
                name TEXT PRIMARY KEY,
                value INTEGER NOT NULL
            );
            """
        )
        for name in (
            "requests",
            "request_errors",
            "cap_alarms",
            "gap_alarms",
            "records_written",
            "duplicates",
            "timestamp_conflicts",
            "missing_published_at",
        ):
            self.connection.execute(
                "INSERT OR IGNORE INTO counters(name, value) VALUES (?, 0)",
                (name,),
            )
        self.connection.commit()

    def close(self) -> None:
        self.connection.commit()
        self.connection.close()

    def get_state(self, name: str) -> str | None:
        row = self.connection.execute(
            "SELECT value FROM state WHERE name = ?",
            (name,),
        ).fetchone()
        return str(row[0]) if row else None

    def set_state(self, name: str, value: str, *, at: datetime) -> None:
        self.connection.execute(
            """
            INSERT INTO state(name, value, updated_at)
            VALUES (?, ?, ?)
            ON CONFLICT(name) DO UPDATE SET
                value = excluded.value,
                updated_at = excluded.updated_at
            """,
            (name, value, rfc3339(at)),
        )
        self.connection.commit()

    def increment(self, name: str, amount: int = 1) -> None:
        self.connection.execute(
            "UPDATE counters SET value = value + ? WHERE name = ?",
            (amount, name),
        )

    def _append_jsonl(self, path: Path, value: dict[str, Any]) -> None:
        with path.open("a") as handle:
            handle.write(json.dumps(value, sort_keys=True, default=str) + "\n")
            handle.flush()

    def append_request(self, value: dict[str, Any]) -> None:
        self._append_jsonl(self.raw_dir / "news_requests.jsonl", value)
        self.increment("requests")
        if value.get("status") != "success":
            self.increment("request_errors")
        if value.get("cap_alarm") is True:
            self.increment("cap_alarms")
        if value.get("gap_alarm") is True:
            self.increment("gap_alarms")
        self.connection.commit()

    def append_news(
        self,
        row: dict[str, Any],
        *,
        retrieved_at: datetime,
    ) -> tuple[bool, datetime | None, datetime | None]:
        key = news_record_key(row)
        content_sha = sha256_json(row)
        publication_time = published_at(row)
        publication_text = rfc3339(publication_time) if publication_time else None
        existing = self.connection.execute(
            "SELECT first_seen_at, published_at FROM news_seen WHERE record_key = ?",
            (key,),
        ).fetchone()
        if existing:
            prior_publication = str(existing[1]) if existing[1] is not None else None
            if prior_publication != publication_text:
                self.connection.execute(
                    """
                    INSERT INTO timestamp_conflicts(
                        record_key, prior_published_at, observed_published_at,
                        observed_at, content_sha256
                    ) VALUES (?, ?, ?, ?, ?)
                    """,
                    (
                        key,
                        prior_publication,
                        publication_text,
                        rfc3339(retrieved_at),
                        content_sha,
                    ),
                )
                self.increment("timestamp_conflicts")
            self.increment("duplicates")
            self.connection.commit()
            return False, publication_time, parse_utc(existing[0])

        available = availability_time(publication_time, retrieved_at)
        available_text = rfc3339(available) if available else None
        self.connection.execute(
            """
            INSERT INTO news_seen(
                record_key, first_seen_at, published_at, available_at, content_sha256
            ) VALUES (?, ?, ?, ?, ?)
            """,
            (
                key,
                rfc3339(retrieved_at),
                publication_text,
                available_text,
                content_sha,
            ),
        )
        if publication_time is None:
            self.increment("missing_published_at")
        envelope = {
            "_availability_rule": "max(published_at, first_seen_at)",
            "_available_at": available_text,
            "_contract_id": self.contract_id,
            "_first_seen_at": rfc3339(retrieved_at),
            "_protocol_id": self.protocol_id,
            "_published_at": publication_text,
            "_record_key": key,
            "_retrieved_at": rfc3339(retrieved_at),
            "_source_endpoint": self.contract["collection"]["endpoint"],
            "_usable_for_b1_primary": available is not None,
            "record": row,
        }
        self._append_jsonl(self.raw_dir / "news.jsonl", envelope)
        self.increment("records_written")
        self.connection.commit()
        return True, publication_time, retrieved_at

    def open_censoring_interval(
        self,
        *,
        start_at: datetime,
        end_at: datetime,
        reason: str,
    ) -> str:
        material = {
            "end_at": rfc3339(end_at),
            "reason": reason,
            "start_at": rfc3339(start_at),
        }
        interval_id = hashlib.sha256(canonical_json(material).encode()).hexdigest()
        self.connection.execute(
            """
            INSERT OR IGNORE INTO censoring_intervals(
                interval_id, start_at, end_at, reason, opened_at, status
            ) VALUES (?, ?, ?, ?, ?, 'unresolved')
            """,
            (
                interval_id,
                material["start_at"],
                material["end_at"],
                reason,
                rfc3339(end_at),
            ),
        )
        self.connection.commit()
        return interval_id

    def health(self, *, at: datetime) -> dict[str, Any]:
        counters = dict(self.connection.execute("SELECT name, value FROM counters"))
        unresolved = self.connection.execute(
            """
            SELECT interval_id, start_at, end_at, reason
            FROM censoring_intervals
            WHERE status = 'unresolved'
            ORDER BY start_at
            """
        ).fetchall()
        return {
            "contract_id": self.contract_id,
            "counters": counters,
            "generated_at": rfc3339(at),
            "label_blind": True,
            "labels_read": [],
            "last_attempt_at": self.get_state("last_attempt_at"),
            "last_success_at": self.get_state("last_success_at"),
            "news_since": self.get_state("news_since"),
            "protocol_id": self.protocol_id,
            "unresolved_censoring_intervals": [
                {
                    "interval_id": row[0],
                    "start_at": row[1],
                    "end_at": row[2],
                    "reason": row[3],
                }
                for row in unresolved
            ],
        }

    def write_health(self, *, at: datetime) -> None:
        path = self.root / "health.json"
        temporary = path.with_suffix(".json.tmp")
        temporary.write_text(json.dumps(self.health(at=at), indent=2, sort_keys=True) + "\n")
        temporary.replace(path)


def poll_once(
    client: Any,
    store: NewsStore,
    contract: dict[str, Any],
    *,
    clock: Callable[[], datetime] = utc_now,
) -> dict[str, Any]:
    collection = contract["collection"]
    since_text = store.get_state("news_since")
    since = parse_utc(since_text)
    if since is None:
        raise RuntimeError("news_since is not initialized; provide --since on first launch")

    started = clock()
    store.set_state("last_attempt_at", rfc3339(started), at=started)
    params = {
        "limit": int(collection["response_cap_rows"]),
        "since": rfc3339(since),
    }
    prior_success = parse_utc(store.get_state("last_success_at"))
    try:
        response = client.get(str(collection["endpoint"]), **params)
    except Exception as exc:
        completed = clock()
        request = {
            "cap_alarm": False,
            "completed_at": rfc3339(completed),
            "contract_id": contract["contract_id"],
            "endpoint": collection["endpoint"],
            "error": f"{type(exc).__name__}: {str(exc)[:300]}",
            "gap_alarm": (
                prior_success is not None
                and (completed - prior_success).total_seconds()
                > float(collection["max_success_gap_seconds"])
            ),
            "params": params,
            "protocol_id": contract["protocol_id"],
            "response_rows": null_value(),
            "started_at": rfc3339(started),
            "status": "error",
        }
        store.append_request(request)
        store.write_health(at=completed)
        raise

    completed = clock()
    rows = extract_rows(response)
    cap_alarm = is_cap_alarm(len(rows), contract)
    gap_seconds = (
        (completed - prior_success).total_seconds() if prior_success is not None else None
    )
    gap_alarm = (
        gap_seconds is not None
        and gap_seconds > float(collection["max_success_gap_seconds"])
    )
    valid_publication_times: list[datetime] = []
    missing_published = 0
    after_completion = 0
    records_written = 0
    for row in rows:
        written, publication_time, _first_seen = store.append_news(
            row,
            retrieved_at=completed,
        )
        records_written += int(written)
        if publication_time is None:
            missing_published += 1
            continue
        if publication_time > completed:
            after_completion += 1
        if publication_time <= completed + timedelta(minutes=5):
            valid_publication_times.append(publication_time)

    interval_id: str | None = None
    checkpoint_advanced = False
    if cap_alarm:
        interval_id = store.open_censoring_interval(
            start_at=since,
            end_at=completed,
            reason="response_cap_rows_reached",
        )
    else:
        overlap = timedelta(seconds=float(collection["overlap_seconds"]))
        proposed = (
            max(valid_publication_times) - overlap
            if valid_publication_times
            else completed - overlap
        )
        new_since = max(since, proposed)
        store.set_state("news_since", rfc3339(new_since), at=completed)
        checkpoint_advanced = new_since > since

    store.set_state("last_success_at", rfc3339(completed), at=completed)
    request = {
        "cap_alarm": cap_alarm,
        "censoring_interval_id": interval_id,
        "checkpoint_advanced": checkpoint_advanced,
        "completed_at": rfc3339(completed),
        "contract_id": contract["contract_id"],
        "endpoint": collection["endpoint"],
        "gap_alarm": gap_alarm,
        "gap_recovered_by_uncapped_response": bool(gap_alarm and not cap_alarm),
        "gap_seconds": gap_seconds,
        "params": params,
        "post_retrieval_publication_rows": after_completion,
        "protocol_id": contract["protocol_id"],
        "records_written": records_written,
        "response_rows": len(rows),
        "response_sha256": sha256_json(response),
        "rows_missing_published_at": missing_published,
        "started_at": rfc3339(started),
        "status": "success",
    }
    store.append_request(request)
    store.write_health(at=completed)
    return request


def null_value() -> None:
    """Make the explicit JSON-null intent readable in request construction."""

    return None


def acquire_lock(root: Path) -> Any:
    root.mkdir(parents=True, exist_ok=True)
    handle = (root / "collector.lock").open("w")
    try:
        fcntl.flock(handle, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except BlockingIOError as exc:
        handle.close()
        raise SystemExit(f"v2.3 news collector already running for {root}") from exc
    handle.write(str(__import__("os").getpid()) + "\n")
    handle.flush()
    return handle


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--contract", type=Path, default=DEFAULT_CONTRACT)
    parser.add_argument("--root", type=Path, default=DEFAULT_ROOT)
    parser.add_argument(
        "--since",
        help="Required RFC3339 checkpoint on first launch; never inferred silently",
    )
    parser.add_argument("--poll-seconds", type=float)
    parser.add_argument("--stop-at", default=DEFAULT_STOP_AT)
    parser.add_argument("--once", action="store_true")
    args = parser.parse_args()

    contract = load_object(args.contract)
    validate_contract(contract)
    fixed_poll = float(contract["collection"]["poll_seconds"])
    poll_seconds = fixed_poll if args.poll_seconds is None else args.poll_seconds
    if poll_seconds != fixed_poll:
        raise SystemExit(f"poll frequency is frozen at {fixed_poll:g} seconds")
    stop_at = parse_utc(args.stop_at)
    if stop_at is None:
        raise SystemExit("--stop-at must be an RFC3339 timestamp")

    process_lock = acquire_lock(args.root)
    store = NewsStore(args.root, contract)
    stop = False

    def request_stop(*_args: object) -> None:
        nonlocal stop
        stop = True

    signal.signal(signal.SIGTERM, request_stop)
    signal.signal(signal.SIGINT, request_stop)
    try:
        existing_since = store.get_state("news_since")
        if existing_since is None:
            initial_since = parse_utc(args.since)
            if initial_since is None:
                raise SystemExit("first launch requires an explicit valid --since value")
            store.set_state("news_since", rfc3339(initial_since), at=utc_now())
        elif args.since is not None and rfc3339(parse_utc(args.since) or utc_now()) != existing_since:
            raise SystemExit("--since cannot overwrite an existing checkpoint")

        with FindataClient(rpm=60, timeout=60.0) as client:
            while not stop and utc_now() < stop_at:
                cycle_started = time.monotonic()
                try:
                    result = poll_once(client, store, contract)
                    print(json.dumps(result, sort_keys=True), flush=True)
                except Exception as exc:
                    print(
                        json.dumps(
                            {"status": "error", "error": f"{type(exc).__name__}: {exc}"},
                            sort_keys=True,
                        ),
                        flush=True,
                    )
                if args.once:
                    break
                remaining = max(0.0, poll_seconds - (time.monotonic() - cycle_started))
                end_wait = time.monotonic() + remaining
                while not stop and time.monotonic() < end_wait:
                    time.sleep(min(0.25, end_wait - time.monotonic()))
    finally:
        store.write_health(at=utc_now())
        store.close()
        process_lock.close()


if __name__ == "__main__":
    main()
