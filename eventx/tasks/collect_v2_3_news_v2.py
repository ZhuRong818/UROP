"""Collect Lumid news with stable entity keys and append-only content versions.

This is the label-blind implementation revision of the frozen EventX v2.3 news
collection design.  It preserves the endpoint, polling, censoring, and availability
rules while separating article identity from mutable article content.
"""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import signal
import time
from typing import Any, Callable
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

from eventx.ingest.client import FindataClient
from eventx.settings import REPO_ROOT
from eventx.tasks.collect_v2_3_news import (
    NewsStore as V23NewsStore,
    acquire_lock,
    availability_time,
    canonical_json,
    first_value,
    load_object,
    parse_utc,
    poll_once,
    published_at,
    rfc3339,
    sha256_json,
    utc_now,
    validate_contract as validate_v23_contract,
)


DEFAULT_CONTRACT = (
    REPO_ROOT / "eventx" / "release" / "v2_3_1" / "news_collection_contract.json"
)
DEFAULT_ROOT = REPO_ROOT / "data" / "v2_3_1" / "prospective_news"
DEFAULT_STOP_AT = "2026-10-22T00:00:00Z"
PROVIDER_ID_KEYS = ("article_id", "id", "uuid")
TRACKING_QUERY_KEYS = {
    "fbclid",
    "gclid",
    "mc_cid",
    "mc_eid",
    "ref",
}


def normalize_url(value: str) -> str:
    """Return a conservative identity URL with fragments/tracking removed."""

    parsed = urlsplit(value.strip())
    scheme = parsed.scheme.lower()
    hostname = (parsed.hostname or "").lower()
    port = parsed.port
    if port is not None and not (
        (scheme == "http" and port == 80) or (scheme == "https" and port == 443)
    ):
        hostname = f"{hostname}:{port}"
    path = parsed.path or "/"
    if path != "/":
        path = path.rstrip("/")
    query = [
        (key, item)
        for key, item in parse_qsl(parsed.query, keep_blank_values=True)
        if not key.lower().startswith("utm_") and key.lower() not in TRACKING_QUERY_KEYS
    ]
    return urlunsplit((scheme, hostname, path, urlencode(sorted(query)), ""))


def stable_news_identity(row: dict[str, Any]) -> tuple[str, str, str]:
    """Return stable key, identity kind, and normalized identity value."""

    for key in PROVIDER_ID_KEYS:
        value = first_value(row, (key,))
        if value is not None:
            identity_value = value.strip()
            material = f"lumid_news:{key}:{identity_value}"
            return hashlib.sha256(material.encode()).hexdigest(), key, identity_value
    url = first_value(row, ("url",))
    if url is not None:
        normalized = normalize_url(url)
        if normalized:
            material = f"lumid_news:normalized_url:{normalized}"
            return hashlib.sha256(material.encode()).hexdigest(), "normalized_url", normalized
    content_sha = sha256_json(row)
    material = f"lumid_news:fallback_content:{content_sha}"
    return hashlib.sha256(material.encode()).hexdigest(), "fallback_content", content_sha


def validate_contract(contract: dict[str, Any]) -> None:
    validate_v23_contract(contract)
    expected = "provider_id_else_normalized_url_with_content_versions_separate"
    if contract.get("collection", {}).get("stable_record_key") != expected:
        raise ValueError("v2.3 implementation-v2 stable record key mismatch")
    if contract.get("implementation", {}).get("content_versions") != "append_only":
        raise ValueError("content revisions must be append-only")


class NewsStore(V23NewsStore):
    """Restart-safe v2 store with stable entities and append-only revisions."""

    def __init__(self, root: Path, contract: dict[str, Any]) -> None:
        super().__init__(root, contract)
        columns = {
            str(row[1])
            for row in self.connection.execute("PRAGMA table_info(news_seen)").fetchall()
        }
        additions = {
            "identity_kind": "TEXT",
            "identity_value": "TEXT",
            "quarantined": "INTEGER NOT NULL DEFAULT 0",
        }
        for name, declaration in additions.items():
            if name not in columns:
                self.connection.execute(
                    f"ALTER TABLE news_seen ADD COLUMN {name} {declaration}"
                )
        self.connection.executescript(
            """
            CREATE TABLE IF NOT EXISTS news_versions (
                record_key TEXT NOT NULL,
                content_sha256 TEXT NOT NULL,
                first_observed_at TEXT NOT NULL,
                published_at TEXT,
                raw_json TEXT NOT NULL,
                PRIMARY KEY(record_key, content_sha256)
            );
            CREATE TABLE IF NOT EXISTS conflict_dedup (
                conflict_key TEXT PRIMARY KEY,
                record_key TEXT NOT NULL,
                prior_published_at TEXT,
                observed_published_at TEXT,
                observed_at TEXT NOT NULL,
                content_sha256 TEXT NOT NULL
            );
            """
        )
        for name in ("content_revisions", "identity_fallbacks", "quarantined_records"):
            self.connection.execute(
                "INSERT OR IGNORE INTO counters(name, value) VALUES (?, 0)", (name,)
            )
        self.connection.commit()

    def _append_version(
        self,
        row: dict[str, Any],
        *,
        record_key: str,
        identity_kind: str,
        identity_value: str,
        content_sha: str,
        publication_time: datetime | None,
        first_seen_at: datetime,
        observed_at: datetime,
        entity_available_at: datetime | None,
        revision: bool,
        quarantined: bool,
    ) -> None:
        publication_text = rfc3339(publication_time) if publication_time else None
        version_available = availability_time(publication_time, observed_at)
        envelope = {
            "_availability_rule": "max(published_at, first_seen_at)",
            "_available_at": rfc3339(version_available) if version_available else None,
            "_content_sha256": content_sha,
            "_contract_id": self.contract_id,
            "_entity_available_at": (
                rfc3339(entity_available_at) if entity_available_at else None
            ),
            "_first_seen_at": rfc3339(first_seen_at),
            "_identity_kind": identity_kind,
            "_identity_value": identity_value,
            "_is_content_revision": revision,
            "_protocol_id": self.protocol_id,
            "_published_at": publication_text,
            "_quarantined": quarantined,
            "_record_key": record_key,
            "_retrieved_at": rfc3339(observed_at),
            "_source_endpoint": self.contract["collection"]["endpoint"],
            "_usable_for_b1_primary": version_available is not None and not quarantined,
            "record": row,
        }
        self._append_jsonl(self.raw_dir / "news.jsonl", envelope)

    def append_news(
        self,
        row: dict[str, Any],
        *,
        retrieved_at: datetime,
    ) -> tuple[bool, datetime | None, datetime | None]:
        record_key, identity_kind, identity_value = stable_news_identity(row)
        content_sha = sha256_json(row)
        publication_time = published_at(row)
        publication_text = rfc3339(publication_time) if publication_time else None
        existing = self.connection.execute(
            """
            SELECT first_seen_at, published_at, available_at, content_sha256,
                   COALESCE(quarantined, 0)
            FROM news_seen WHERE record_key = ?
            """,
            (record_key,),
        ).fetchone()

        if existing is None:
            first_seen_at = retrieved_at
            entity_available = availability_time(publication_time, first_seen_at)
            self.connection.execute(
                """
                INSERT INTO news_seen(
                    record_key, first_seen_at, published_at, available_at,
                    content_sha256, identity_kind, identity_value, quarantined
                ) VALUES (?, ?, ?, ?, ?, ?, ?, 0)
                """,
                (
                    record_key,
                    rfc3339(first_seen_at),
                    publication_text,
                    rfc3339(entity_available) if entity_available else None,
                    content_sha,
                    identity_kind,
                    identity_value,
                ),
            )
            if identity_kind == "fallback_content":
                self.increment("identity_fallbacks")
            if publication_time is None:
                self.increment("missing_published_at")
            self.connection.execute(
                """
                INSERT INTO news_versions(
                    record_key, content_sha256, first_observed_at, published_at, raw_json
                ) VALUES (?, ?, ?, ?, ?)
                """,
                (
                    record_key,
                    content_sha,
                    rfc3339(retrieved_at),
                    publication_text,
                    canonical_json(row),
                ),
            )
            self._append_version(
                row,
                record_key=record_key,
                identity_kind=identity_kind,
                identity_value=identity_value,
                content_sha=content_sha,
                publication_time=publication_time,
                first_seen_at=first_seen_at,
                observed_at=retrieved_at,
                entity_available_at=entity_available,
                revision=False,
                quarantined=False,
            )
            self.increment("records_written")
            self.connection.commit()
            return True, publication_time, first_seen_at

        first_seen_at = parse_utc(existing[0])
        assert first_seen_at is not None
        prior_publication = str(existing[1]) if existing[1] is not None else None
        entity_available = parse_utc(existing[2])
        prior_content_sha = str(existing[3])
        quarantined = bool(existing[4])

        if prior_publication != publication_text:
            conflict_material = {
                "content_sha256": content_sha,
                "observed_published_at": publication_text,
                "prior_published_at": prior_publication,
                "record_key": record_key,
            }
            conflict_key = hashlib.sha256(canonical_json(conflict_material).encode()).hexdigest()
            inserted = self.connection.execute(
                """
                INSERT OR IGNORE INTO conflict_dedup(
                    conflict_key, record_key, prior_published_at,
                    observed_published_at, observed_at, content_sha256
                ) VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    conflict_key,
                    record_key,
                    prior_publication,
                    publication_text,
                    rfc3339(retrieved_at),
                    content_sha,
                ),
            ).rowcount
            if inserted:
                self.connection.execute(
                    """
                    INSERT INTO timestamp_conflicts(
                        record_key, prior_published_at, observed_published_at,
                        observed_at, content_sha256
                    ) VALUES (?, ?, ?, ?, ?)
                    """,
                    (
                        record_key,
                        prior_publication,
                        publication_text,
                        rfc3339(retrieved_at),
                        content_sha,
                    ),
                )
                self.increment("timestamp_conflicts")
                if not quarantined:
                    self.increment("quarantined_records")
                self._append_jsonl(
                    self.raw_dir / "timestamp_conflicts.jsonl",
                    {**conflict_material, "observed_at": rfc3339(retrieved_at)},
                )
            quarantined = True
            self.connection.execute(
                "UPDATE news_seen SET quarantined = 1 WHERE record_key = ?",
                (record_key,),
            )

        if prior_content_sha == content_sha:
            self.increment("duplicates")
            self.connection.commit()
            return False, publication_time, first_seen_at

        inserted_version = self.connection.execute(
            """
            INSERT OR IGNORE INTO news_versions(
                record_key, content_sha256, first_observed_at, published_at, raw_json
            ) VALUES (?, ?, ?, ?, ?)
            """,
            (
                record_key,
                content_sha,
                rfc3339(retrieved_at),
                publication_text,
                canonical_json(row),
            ),
        ).rowcount
        if not inserted_version:
            self.increment("duplicates")
            self.connection.commit()
            return False, publication_time, first_seen_at

        self.connection.execute(
            "UPDATE news_seen SET content_sha256 = ? WHERE record_key = ?",
            (content_sha, record_key),
        )
        self._append_version(
            row,
            record_key=record_key,
            identity_kind=identity_kind,
            identity_value=identity_value,
            content_sha=content_sha,
            publication_time=publication_time,
            first_seen_at=first_seen_at,
            observed_at=retrieved_at,
            entity_available_at=entity_available,
            revision=True,
            quarantined=quarantined,
        )
        self.increment("content_revisions")
        self.increment("records_written")
        self.connection.commit()
        return True, publication_time, first_seen_at

    def health(self, *, at: datetime) -> dict[str, Any]:
        result = super().health(at=at)
        result["implementation_version"] = "v2"
        result["stable_entities"] = int(
            self.connection.execute("SELECT COUNT(*) FROM news_seen").fetchone()[0]
        )
        result["content_versions"] = int(
            self.connection.execute("SELECT COUNT(*) FROM news_versions").fetchone()[0]
        )
        result["quarantined_entities"] = int(
            self.connection.execute(
                "SELECT COUNT(*) FROM news_seen WHERE quarantined = 1"
            ).fetchone()[0]
        )
        return result


def file_sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write_initial_receipt(
    root: Path,
    contract_path: Path,
    contract: dict[str, Any],
    *,
    started_at: datetime,
    initial_since: datetime,
    unresolved_start: datetime | None,
    interval_id: str | None,
    legacy_pid: int | None,
) -> None:
    receipt = {
        "collector_program": str(Path(__file__).resolve().relative_to(REPO_ROOT)),
        "collector_sha256": file_sha256(Path(__file__)),
        "contract_id": contract["contract_id"],
        "contract_path": str(contract_path.resolve().relative_to(REPO_ROOT)),
        "contract_sha256": file_sha256(contract_path),
        "initial_checkpoint": rfc3339(initial_since),
        "label_blind": True,
        "labels_read": [],
        "legacy_collector_pid_preserved": legacy_pid,
        "output_root": str(root.resolve().relative_to(REPO_ROOT)),
        "pid": os.getpid(),
        "protocol_id": contract["protocol_id"],
        "started_at": rfc3339(started_at),
        "unresolved_prelaunch_interval": (
            {
                "end_at": rfc3339(initial_since),
                "interval_id": interval_id,
                "start_at": rfc3339(unresolved_start),
            }
            if unresolved_start is not None
            else None
        ),
    }
    path = root / "launch_receipt.json"
    temporary = path.with_suffix(".json.tmp")
    temporary.write_text(json.dumps(receipt, indent=2, sort_keys=True) + "\n")
    temporary.replace(path)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--contract", type=Path, default=DEFAULT_CONTRACT)
    parser.add_argument("--root", type=Path, default=DEFAULT_ROOT)
    parser.add_argument("--since")
    parser.add_argument("--unresolved-start")
    parser.add_argument("--legacy-pid", type=int)
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
            started_at = utc_now()
            store.set_state("news_since", rfc3339(initial_since), at=started_at)
            unresolved_start = parse_utc(args.unresolved_start)
            interval_id = None
            if unresolved_start is not None:
                if unresolved_start >= initial_since:
                    raise SystemExit("--unresolved-start must precede --since")
                interval_id = store.open_censoring_interval(
                    start_at=unresolved_start,
                    end_at=initial_since,
                    reason="prelaunch_interval_requires_lumid_reconciliation",
                )
            write_initial_receipt(
                args.root,
                args.contract,
                contract,
                started_at=started_at,
                initial_since=initial_since,
                unresolved_start=unresolved_start,
                interval_id=interval_id,
                legacy_pid=args.legacy_pid,
            )
        elif args.since is not None:
            parsed_since = parse_utc(args.since)
            if parsed_since is None or rfc3339(parsed_since) != existing_since:
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
                deadline = time.monotonic() + remaining
                while not stop and time.monotonic() < deadline:
                    time.sleep(min(0.25, deadline - time.monotonic()))
    finally:
        store.write_health(at=utc_now())
        store.close()
        process_lock.close()


if __name__ == "__main__":
    main()
