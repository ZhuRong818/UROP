"""Run the hardened, label-blind EventX v2.3 news collector.

Implementation v3 preserves the frozen collection semantics, fixes the cadence race,
and quarantines implausible future publication timestamps before the primary stream.
"""

from __future__ import annotations

import argparse
from datetime import datetime, timedelta
import hashlib
import json
import os
from pathlib import Path
import signal
import time
from typing import Any

from eventx.ingest.client import FindataClient
from eventx.settings import REPO_ROOT
from eventx.tasks.collect_v2_3_news import (
    acquire_lock,
    canonical_json,
    load_object,
    parse_utc,
    poll_once,
    published_at,
    rfc3339,
    sha256_json,
    utc_now,
)
from eventx.tasks.collect_v2_3_news_v2 import (
    DEFAULT_ROOT,
    DEFAULT_STOP_AT,
    NewsStore as V2NewsStore,
    file_sha256,
    stable_news_identity,
    validate_contract as validate_v2_contract,
)


DEFAULT_CONTRACT = (
    REPO_ROOT / "eventx" / "release" / "v2_3_2" / "news_collection_contract.json"
)
DEFAULT_IMPLEMENTATION_MANIFEST = (
    REPO_ROOT / "eventx" / "release" / "v2_3_2" / "implementation_manifest.json"
)


def validate_contract(contract: dict[str, Any]) -> None:
    validate_v2_contract(contract)
    implementation = contract.get("implementation", {})
    if implementation.get("future_publication_tolerance_seconds") != 300:
        raise ValueError("future-publication tolerance must be 300 seconds")
    if implementation.get("cadence_sleep_floor_seconds") != 0:
        raise ValueError("cadence sleep floor must be zero")
    if implementation.get("restart_receipts") != "append_only":
        raise ValueError("restart receipts must be append-only")


def safe_sleep_seconds(deadline: float, now: float) -> float:
    """Return the race-safe bounded delay for the cadence loop."""

    return max(0.0, min(0.25, deadline - now))


class NewsStore(V2NewsStore):
    """Implementation-v3 state with pre-primary future-time quarantine."""

    def __init__(self, root: Path, contract: dict[str, Any]) -> None:
        super().__init__(root, contract)
        self.future_tolerance = timedelta(
            seconds=float(
                contract["implementation"]["future_publication_tolerance_seconds"]
            )
        )
        self.connection.executescript(
            """
            CREATE TABLE IF NOT EXISTS invalid_timestamp_rows (
                invalid_key TEXT PRIMARY KEY,
                record_key TEXT NOT NULL,
                content_sha256 TEXT NOT NULL,
                published_at TEXT NOT NULL,
                retrieved_at TEXT NOT NULL,
                reason TEXT NOT NULL,
                raw_json TEXT NOT NULL
            );
            """
        )
        for name in ("future_timestamp_quarantined", "future_timestamp_duplicates"):
            self.connection.execute(
                "INSERT OR IGNORE INTO counters(name, value) VALUES (?, 0)", (name,)
            )
        self.connection.execute(
            """
            UPDATE news_seen
            SET quarantined = 1
            WHERE record_key IN (
                SELECT DISTINCT record_key FROM invalid_timestamp_rows
            )
            """
        )
        self.connection.commit()

    def append_news(
        self,
        row: dict[str, Any],
        *,
        retrieved_at: datetime,
    ) -> tuple[bool, datetime | None, datetime | None]:
        publication_time = published_at(row)
        if (
            publication_time is None
            or publication_time <= retrieved_at + self.future_tolerance
        ):
            return super().append_news(row, retrieved_at=retrieved_at)

        record_key, identity_kind, identity_value = stable_news_identity(row)
        content_sha = sha256_json(row)
        quarantine_identity = {
            "published_at": rfc3339(publication_time),
            "record_key": record_key,
            "reason": "published_at_more_than_300_seconds_after_retrieval",
        }
        invalid_material = {
            **quarantine_identity,
            "retrieved_at": rfc3339(retrieved_at),
        }
        invalid_key = hashlib.sha256(
            canonical_json(quarantine_identity).encode("utf-8")
        ).hexdigest()
        existing = self.connection.execute(
            """
            SELECT 1
            FROM invalid_timestamp_rows
            WHERE record_key = ?
              AND published_at = ?
              AND reason = ?
            LIMIT 1
            """,
            (
                record_key,
                rfc3339(publication_time),
                "published_at_more_than_300_seconds_after_retrieval",
            ),
        ).fetchone()
        if existing is None:
            self.connection.execute(
                """
                INSERT INTO invalid_timestamp_rows(
                    invalid_key, record_key, content_sha256, published_at,
                    retrieved_at, reason, raw_json
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    invalid_key,
                    record_key,
                    content_sha,
                    rfc3339(publication_time),
                    rfc3339(retrieved_at),
                    "published_at_more_than_300_seconds_after_retrieval",
                    canonical_json(row),
                ),
            )
            self._append_jsonl(
                self.raw_dir / "invalid_timestamp_rows.jsonl",
                {
                    **invalid_material,
                    "_contract_id": self.contract_id,
                    "_identity_kind": identity_kind,
                    "_identity_value": identity_value,
                    "_protocol_id": self.protocol_id,
                    "_quarantined": True,
                    "_reason": "published_at_more_than_300_seconds_after_retrieval",
                    "_usable_for_b1_primary": False,
                    "record": row,
                },
            )
            self.increment("future_timestamp_quarantined")
        else:
            self.increment("future_timestamp_duplicates")
        self.connection.execute(
            "UPDATE news_seen SET quarantined = 1 WHERE record_key = ?",
            (record_key,),
        )
        self.connection.commit()
        return False, publication_time, retrieved_at

    def health(self, *, at: datetime) -> dict[str, Any]:
        result = super().health(at=at)
        result["implementation_version"] = "v3"
        result["invalid_future_timestamp_rows"] = int(
            self.connection.execute(
                "SELECT COUNT(*) FROM invalid_timestamp_rows"
            ).fetchone()[0]
        )
        return result


def previous_pid(root: Path) -> int | None:
    path = root / "collector.lock"
    try:
        return int(path.read_text(encoding="utf-8").strip())
    except (FileNotFoundError, OSError, ValueError):
        return None


def write_start_receipt(
    root: Path,
    contract_path: Path,
    manifest_path: Path,
    contract: dict[str, Any],
    store: NewsStore,
    *,
    started_at: datetime,
    predecessor_pid: int | None,
) -> Path:
    receipt = {
        "collector_program": str(Path(__file__).resolve().relative_to(REPO_ROOT)),
        "collector_sha256": file_sha256(Path(__file__)),
        "contract_id": contract["contract_id"],
        "contract_path": str(contract_path.resolve().relative_to(REPO_ROOT)),
        "contract_sha256": file_sha256(contract_path),
        "implementation_manifest_path": str(
            manifest_path.resolve().relative_to(REPO_ROOT)
        ),
        "implementation_manifest_sha256": file_sha256(manifest_path),
        "label_blind": True,
        "labels_read": [],
        "news_since_at_start": store.get_state("news_since"),
        "pid": os.getpid(),
        "predecessor_last_success_at": store.get_state("last_success_at"),
        "predecessor_pid": predecessor_pid,
        "protocol_id": contract["protocol_id"],
        "reuses_predecessor_append_only_state": True,
        "started_at": rfc3339(started_at),
    }
    receipts = root / "restart_receipts"
    receipts.mkdir(parents=True, exist_ok=True)
    timestamp = started_at.strftime("%Y%m%dT%H%M%SZ")
    path = receipts / f"{timestamp}_{os.getpid()}.json"
    temporary = path.with_suffix(".json.tmp")
    temporary.write_text(
        json.dumps(receipt, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    os.replace(temporary, path)
    return path


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--contract", type=Path, default=DEFAULT_CONTRACT)
    parser.add_argument(
        "--implementation-manifest",
        type=Path,
        default=DEFAULT_IMPLEMENTATION_MANIFEST,
    )
    parser.add_argument("--root", type=Path, default=DEFAULT_ROOT)
    parser.add_argument("--since")
    parser.add_argument("--poll-seconds", type=float)
    parser.add_argument("--stop-at", default=DEFAULT_STOP_AT)
    parser.add_argument("--once", action="store_true")
    args = parser.parse_args()

    contract = load_object(args.contract)
    validate_contract(contract)
    if not args.implementation_manifest.is_file():
        raise SystemExit("implementation manifest is missing")
    fixed_poll = float(contract["collection"]["poll_seconds"])
    poll_seconds = fixed_poll if args.poll_seconds is None else args.poll_seconds
    if poll_seconds != fixed_poll:
        raise SystemExit(f"poll frequency is frozen at {fixed_poll:g} seconds")
    stop_at = parse_utc(args.stop_at)
    if stop_at is None:
        raise SystemExit("--stop-at must be an RFC3339 timestamp")

    predecessor_pid = previous_pid(args.root)
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
        elif args.since is not None:
            parsed_since = parse_utc(args.since)
            if parsed_since is None or rfc3339(parsed_since) != existing_since:
                raise SystemExit("--since cannot overwrite an existing checkpoint")

        started_at = utc_now()
        write_start_receipt(
            args.root,
            args.contract,
            args.implementation_manifest,
            contract,
            store,
            started_at=started_at,
            predecessor_pid=predecessor_pid,
        )
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
                    delay = safe_sleep_seconds(deadline, time.monotonic())
                    if delay <= 0:
                        break
                    time.sleep(delay)
    finally:
        store.write_health(at=utc_now())
        store.close()
        process_lock.close()


if __name__ == "__main__":
    main()
