"""Run synthetic checks for the EventX v2.3 news implementation revision."""

from __future__ import annotations

from datetime import datetime
import json
from pathlib import Path
import tempfile
from typing import Any

from eventx.tasks.collect_v2_3_news import parse_utc, poll_once
from eventx.tasks.collect_v2_3_news_v2 import (
    DEFAULT_CONTRACT,
    NewsStore,
    load_object,
    normalize_url,
    stable_news_identity,
    validate_contract,
)


def dt(value: str) -> datetime:
    parsed = parse_utc(value)
    assert parsed is not None
    return parsed


class FakeClient:
    def __init__(self, response: Any) -> None:
        self.response = response

    def get(self, _endpoint: str, **_params: Any) -> Any:
        return self.response


class FrozenClock:
    def __init__(self, *values: datetime) -> None:
        self.values = iter(values)

    def __call__(self) -> datetime:
        return next(self.values)


def verify_store(root: Path, contract: dict[str, Any]) -> list[str]:
    failures: list[str] = []
    store = NewsStore(root, contract)
    try:
        first = {
            "id": "article-1",
            "headline": "Initial headline",
            "published_at": "2026-08-27T04:00:00Z",
            "url": "https://Example.com/story/?utm_source=test",
        }
        revised = {**first, "headline": "Revised headline"}
        key_first = stable_news_identity(first)[0]
        key_revised = stable_news_identity(revised)[0]
        store.append_news(first, retrieved_at=dt("2026-08-27T04:02:00Z"))
        store.append_news(revised, retrieved_at=dt("2026-08-27T04:03:00Z"))
        entity = store.connection.execute(
            "SELECT first_seen_at, available_at FROM news_seen WHERE record_key = ?",
            (key_first,),
        ).fetchone()
        versions = store.connection.execute(
            "SELECT COUNT(*) FROM news_versions WHERE record_key = ?", (key_first,)
        ).fetchone()[0]
        if key_first != key_revised:
            failures.append("content revision changed the stable entity key")
        if versions != 2:
            failures.append("content revision was not stored as a second version")
        if entity != ("2026-08-27T04:02:00Z", "2026-08-27T04:02:00Z"):
            failures.append("revision changed first_seen_at or backdated availability")

        url_first = {
            "headline": "URL-only article",
            "published_at": "2026-08-27T04:05:00Z",
            "url": "https://News.Example/path/?utm_campaign=x&a=1#part",
        }
        url_conflict = {
            **url_first,
            "headline": "URL-only article revised",
            "published_at": "2026-08-27T03:55:00Z",
            "url": "https://news.example/path?a=1",
        }
        url_key = stable_news_identity(url_first)[0]
        if url_key != stable_news_identity(url_conflict)[0]:
            failures.append("URL normalization did not preserve stable identity")
        store.append_news(url_first, retrieved_at=dt("2026-08-27T04:06:00Z"))
        store.append_news(url_conflict, retrieved_at=dt("2026-08-27T04:07:00Z"))
        quarantined = store.connection.execute(
            "SELECT quarantined FROM news_seen WHERE record_key = ?", (url_key,)
        ).fetchone()[0]
        conflicts = store.connection.execute(
            "SELECT COUNT(*) FROM timestamp_conflicts WHERE record_key = ?", (url_key,)
        ).fetchone()[0]
        if quarantined != 1 or conflicts != 1:
            failures.append("publication timestamp conflict did not quarantine once")
        store.append_news(url_conflict, retrieved_at=dt("2026-08-27T04:08:00Z"))
        conflicts_after_duplicate = store.connection.execute(
            "SELECT COUNT(*) FROM timestamp_conflicts WHERE record_key = ?", (url_key,)
        ).fetchone()[0]
        if conflicts_after_duplicate != 1:
            failures.append("repeated conflicting version duplicated conflict evidence")

        fallback = stable_news_identity({"headline": "No id or URL"})
        if fallback[1] != "fallback_content":
            failures.append("missing identity was not explicitly flagged as fallback")
    finally:
        store.close()
    return failures


def verify_cap(root: Path, contract: dict[str, Any]) -> list[str]:
    failures: list[str] = []
    store = NewsStore(root, contract)
    try:
        initial = "2026-08-27T04:00:00Z"
        store.set_state("news_since", initial, at=dt(initial))
        rows = [
            {
                "id": f"cap-{index}",
                "headline": f"Article {index}",
                "published_at": "2026-08-27T04:00:00Z",
                "url": f"https://invalid.example/{index}",
            }
            for index in range(200)
        ]
        result = poll_once(
            FakeClient(rows),
            store,
            contract,
            clock=FrozenClock(
                dt("2026-08-27T04:01:00Z"),
                dt("2026-08-27T04:01:01Z"),
            ),
        )
        if result.get("cap_alarm") is not True:
            failures.append("200 rows did not raise the frozen cap alarm")
        if result.get("checkpoint_advanced") is not False:
            failures.append("checkpoint advanced on a capped response")
        if store.get_state("news_since") != initial:
            failures.append("capped response changed news_since")
    finally:
        store.close()
    return failures


def main() -> None:
    contract = load_object(DEFAULT_CONTRACT)
    failures: list[str] = []
    try:
        validate_contract(contract)
    except ValueError as exc:
        failures.append(str(exc))
    normalized = normalize_url(
        "HTTPS://Example.COM:443/story/?utm_source=x&b=2&a=1#fragment"
    )
    if normalized != "https://example.com/story?a=1&b=2":
        failures.append(f"unexpected URL normalization: {normalized}")
    with tempfile.TemporaryDirectory(prefix="eventx-v2-3-news-v2-") as temporary:
        root = Path(temporary)
        failures.extend(verify_store(root / "store", contract))
        failures.extend(verify_cap(root / "cap", contract))
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
