"""Run offline synthetic checks for the frozen EventX v2.3 news contract."""

from __future__ import annotations

from datetime import datetime, timezone
import json
from pathlib import Path
import tempfile
from typing import Any

from eventx.settings import REPO_ROOT
from eventx.tasks.collect_v2_3_news import (
    NewsStore,
    availability_time,
    load_object,
    parse_utc,
    poll_once,
    validate_contract,
)


CONTRACT_PATH = (
    REPO_ROOT / "eventx" / "release" / "v2_3" / "news_collection_contract.json"
)


class FakeClient:
    def __init__(self, response: Any) -> None:
        self.response = response
        self.calls: list[tuple[str, dict[str, Any]]] = []

    def get(self, endpoint: str, **params: Any) -> Any:
        self.calls.append((endpoint, params))
        return self.response


class FrozenClock:
    def __init__(self, *values: datetime) -> None:
        self.values = iter(values)

    def __call__(self) -> datetime:
        return next(self.values)


def dt(value: str) -> datetime:
    parsed = parse_utc(value)
    assert parsed is not None
    return parsed


def capped_fixture(contract: dict[str, Any], root: Path) -> dict[str, Any]:
    store = NewsStore(root, contract)
    try:
        initial = "2026-08-17T10:00:00Z"
        store.set_state("news_since", initial, at=dt(initial))
        rows = [
            {
                "headline": f"Synthetic article {index}",
                "id": f"cap-{index}",
                "published_at": "2026-08-17T10:00:00Z",
                "publisher": "synthetic",
                "url": f"https://invalid.example/cap-{index}",
            }
            for index in range(200)
        ]
        client = FakeClient(rows)
        result = poll_once(
            client,
            store,
            contract,
            clock=FrozenClock(
                dt("2026-08-17T10:17:00Z"),
                dt("2026-08-17T10:17:01Z"),
            ),
        )
        health = store.health(at=dt("2026-08-17T10:17:02Z"))
        first = store.connection.execute(
            "SELECT published_at, first_seen_at, available_at FROM news_seen ORDER BY record_key LIMIT 1"
        ).fetchone()
        failures: list[str] = []
        if result.get("cap_alarm") is not True:
            failures.append("200-row response did not raise cap alarm")
        if result.get("checkpoint_advanced") is not False:
            failures.append("checkpoint advanced on a cap alarm")
        if store.get_state("news_since") != initial:
            failures.append("capped response changed news_since")
        if len(health["unresolved_censoring_intervals"]) != 1:
            failures.append("capped response did not open one unresolved interval")
        if first is None or first[2] != "2026-08-17T10:17:01Z":
            failures.append("primary availability was backdated before first_seen_at")
        if client.calls != [
            (
                "/news/latest",
                {"limit": 200, "since": "2026-08-17T10:00:00Z"},
            )
        ]:
            failures.append("collector request does not match frozen endpoint/parameters")
        return {
            "failures": failures,
            "result": result,
            "unresolved_intervals": len(health["unresolved_censoring_intervals"]),
        }
    finally:
        store.close()


def uncapped_gap_fixture(contract: dict[str, Any], root: Path) -> dict[str, Any]:
    store = NewsStore(root, contract)
    try:
        initial = "2026-08-17T10:00:00Z"
        store.set_state("news_since", initial, at=dt(initial))
        store.set_state(
            "last_success_at",
            "2026-08-17T10:00:00Z",
            at=dt("2026-08-17T10:00:00Z"),
        )
        client = FakeClient(
            [
                {
                    "headline": "Synthetic future-publication article",
                    "id": "uncapped-1",
                    "published_at": "2026-08-17T10:20:00Z",
                    "publisher": "synthetic",
                    "url": "https://invalid.example/uncapped-1",
                }
            ]
        )
        result = poll_once(
            client,
            store,
            contract,
            clock=FrozenClock(
                dt("2026-08-17T10:16:00Z"),
                dt("2026-08-17T10:17:00Z"),
            ),
        )
        first = store.connection.execute(
            "SELECT published_at, first_seen_at, available_at FROM news_seen LIMIT 1"
        ).fetchone()
        failures: list[str] = []
        if result.get("cap_alarm") is not False:
            failures.append("uncapped response raised cap alarm")
        if result.get("gap_alarm") is not True:
            failures.append("greater-than-five-minute success gap did not alarm")
        if result.get("gap_recovered_by_uncapped_response") is not True:
            failures.append("uncapped contiguous response did not record gap recovery")
        if result.get("checkpoint_advanced") is not True:
            failures.append("uncapped response did not advance checkpoint")
        if first is None or first[2] != "2026-08-17T10:20:00Z":
            failures.append("availability did not wait for a later publication time")
        if store.health(at=dt("2026-08-17T10:17:01Z"))[
            "unresolved_censoring_intervals"
        ]:
            failures.append("uncapped response opened an unresolved censoring interval")
        return {"failures": failures, "result": result}
    finally:
        store.close()


def main() -> None:
    contract = load_object(CONTRACT_PATH)
    failures: list[str] = []
    try:
        validate_contract(contract)
    except ValueError as exc:
        failures.append(str(exc))

    if availability_time(
        dt("2026-08-17T10:00:00Z"),
        dt("2026-08-17T10:17:00Z"),
    ) != dt("2026-08-17T10:17:00Z"):
        failures.append("availability_time permits retrospective backdating")

    with tempfile.TemporaryDirectory(prefix="eventx-v2-3-news-contract-") as temporary:
        temporary_root = Path(temporary)
        capped = capped_fixture(contract, temporary_root / "capped")
        uncapped = uncapped_gap_fixture(contract, temporary_root / "uncapped")
    failures.extend(capped["failures"])
    failures.extend(uncapped["failures"])

    output = {
        "capped_fixture": {
            "cap_alarm": capped["result"].get("cap_alarm"),
            "checkpoint_advanced": capped["result"].get("checkpoint_advanced"),
            "unresolved_intervals": capped["unresolved_intervals"],
        },
        "contract_id": contract.get("contract_id"),
        "failures": failures,
        "label_blind": True,
        "labels_read": [],
        "status": "ok" if not failures else "failed",
        "uncapped_gap_fixture": {
            "cap_alarm": uncapped["result"].get("cap_alarm"),
            "checkpoint_advanced": uncapped["result"].get("checkpoint_advanced"),
            "gap_alarm": uncapped["result"].get("gap_alarm"),
            "gap_recovered": uncapped["result"].get(
                "gap_recovered_by_uncapped_response"
            ),
        },
    }
    print(json.dumps(output, indent=2, sort_keys=True))
    if failures:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
