"""Verify the EventX v2.3 implementation-v3 operational safeguards."""

from __future__ import annotations

from datetime import datetime
import hashlib
import json
from pathlib import Path
import tempfile
from typing import Any

from eventx.tasks.collect_v2_3_news import load_object, parse_utc
from eventx.tasks.collect_v2_3_news_v3 import (
    DEFAULT_CONTRACT,
    NewsStore,
    safe_sleep_seconds,
    stable_news_identity,
    validate_contract,
)


PREDECESSOR = Path("eventx/release/v2_3_1/news_collection_contract.json")
MANIFEST = Path("eventx/release/v2_3_2/implementation_manifest.json")
SCIENTIFIC_SECTIONS = ("availability", "censoring", "collection", "data_gate", "openapi")


def dt(value: str) -> datetime:
    parsed = parse_utc(value)
    assert parsed is not None
    return parsed


def check(condition: bool, name: str, failures: list[str]) -> None:
    if not condition:
        failures.append(name)


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def verify_future_quarantine(root: Path, contract: dict[str, Any]) -> list[str]:
    failures: list[str] = []
    store = NewsStore(root, contract)
    try:
        future = {
            "id": "future-article",
            "headline": "URL-derived future date",
            "published_at": "2030-04-07T12:00:00Z",
            "url": "https://example.invalid/2030/04/07/story",
        }
        retrieved = dt("2026-09-01T14:00:00Z")
        written, _, _ = store.append_news(future, retrieved_at=retrieved)
        store.append_news(
            {**future, "headline": "Changing vendor payload"},
            retrieved_at=dt("2026-09-01T14:01:00Z"),
        )
        check(not written, "future timestamp entered primary write path", failures)
        check(
            store.connection.execute("SELECT COUNT(*) FROM news_seen").fetchone()[0] == 0,
            "future timestamp entered primary entity table",
            failures,
        )
        check(
            store.connection.execute(
                "SELECT COUNT(*) FROM invalid_timestamp_rows"
            ).fetchone()[0]
            == 1,
            "future timestamp quarantine is not deduplicated",
            failures,
        )
        check(
            not (root / "raw" / "news.jsonl").exists(),
            "future timestamp entered primary news stream",
            failures,
        )
        check(
            (root / "raw" / "invalid_timestamp_rows.jsonl").is_file(),
            "future timestamp quarantine ledger is missing",
            failures,
        )
        prior = {
            **future,
            "id": "preexisting-article",
            "published_at": "2026-09-01T13:50:00Z",
        }
        store.append_news(prior, retrieved_at=retrieved)
        future_revision = {
            **future,
            "id": "preexisting-article",
        }
        store.append_news(future_revision, retrieved_at=retrieved)
        preexisting_key = stable_news_identity(prior)[0]
        check(
            store.connection.execute(
                "SELECT quarantined FROM news_seen WHERE record_key = ?",
                (preexisting_key,),
            ).fetchone()
            == (1,),
            "predecessor primary entity was not quarantined",
            failures,
        )
    finally:
        store.close()
    return failures


def main() -> None:
    contract = load_object(DEFAULT_CONTRACT)
    predecessor = load_object(PREDECESSOR)
    manifest = load_object(MANIFEST)
    failures: list[str] = []
    try:
        validate_contract(contract)
    except ValueError as exc:
        failures.append(str(exc))
    for section in SCIENTIFIC_SECTIONS:
        check(
            contract.get(section) == predecessor.get(section),
            f"scientific contract section changed: {section}",
            failures,
        )
    check(
        manifest.get("implementation_id")
        == "eventx-v2.3-news-implementation-v3-20260901",
        "implementation manifest ID mismatch",
        failures,
    )
    for name, artifact in manifest.get("artifacts", {}).items():
        path = Path(str(artifact.get("path", "")))
        check(path.is_file(), f"manifest artifact missing: {name}", failures)
        if path.is_file():
            check(
                path.stat().st_size == artifact.get("bytes"),
                f"manifest artifact size mismatch: {name}",
                failures,
            )
            check(
                sha256_file(path) == artifact.get("sha256"),
                f"manifest artifact hash mismatch: {name}",
                failures,
            )
    check(safe_sleep_seconds(10.0, 10.1) == 0.0, "negative sleep not clamped", failures)
    check(safe_sleep_seconds(10.0, 9.9) > 0.0, "positive sleep removed", failures)
    check(safe_sleep_seconds(10.0, 0.0) == 0.25, "sleep ceiling changed", failures)
    with tempfile.TemporaryDirectory(prefix="eventx-v2-3-news-v3-") as temporary:
        failures.extend(verify_future_quarantine(Path(temporary), contract))
    output = {
        "contract_id": contract.get("contract_id"),
        "failures": failures,
        "label_blind": True,
        "labels_read": [],
        "status": "ok" if not failures else "failed",
    }
    print(json.dumps(output, indent=2, sort_keys=True))
    if failures:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
