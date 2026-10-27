"""Audit that known Lumid defects are fail-closed for EventX v2.3.

This audit is label-blind. It reports operational protection and never authorizes B1
while source-censoring intervals remain unresolved.
"""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import sqlite3
from typing import Any

from eventx.settings import REPO_ROOT


PROTOCOL = REPO_ROOT / "eventx/release/v2_3/protocol.json"
CONTRACT = REPO_ROOT / "eventx/release/v2_3_2/news_collection_contract.json"
IMPLEMENTATION_MANIFEST = (
    REPO_ROOT / "eventx/release/v2_3_2/implementation_manifest.json"
)
NEWS_ROOT = REPO_ROOT / "data/v2_3_1/prospective_news"
HISTORICAL_ROOT = REPO_ROOT / "data/v3_historical/feasibility/raw"
OUTPUT = REPO_ROOT / "data/v2_3_2/source_safety_20260901/report.json"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Audit EventX v2.3 source safeguards without reading labels."
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=OUTPUT,
        help="report path (relative paths are resolved from the repository root)",
    )
    return parser.parse_args()


def load(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise RuntimeError(f"expected object: {path}")
    return value


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def result(name: str, passed: bool, evidence: Any) -> dict[str, Any]:
    return {"check": name, "evidence": evidence, "passed": passed}


def atomic_json(path: Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(".json.tmp")
    temporary.write_text(
        json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    temporary.replace(path)


def main() -> None:
    args = parse_args()
    output = args.output if args.output.is_absolute() else REPO_ROOT / args.output
    protocol = load(PROTOCOL)
    contract = load(CONTRACT)
    manifest = load(IMPLEMENTATION_MANIFEST)
    health = load(NEWS_ROOT / "health.json")
    receipts = sorted((NEWS_ROOT / "restart_receipts").glob("*.json"))
    if not receipts:
        raise RuntimeError("no implementation-v3 restart receipt")
    restart = load(receipts[-1])
    checks: list[dict[str, Any]] = []

    price = protocol["price"]
    checks.append(
        result(
            "broken Kalshi candles cannot enter the primary price series",
            price["primary"]
            == "latest_canonical_yes_trade_at_or_before_t_carried_forward"
            and price["candle_role"] == "separate_fallback_diagnostic_only",
            price,
        )
    )
    censoring = contract["censoring"]
    checks.append(
        result(
            "capped news fails closed without checkpoint advancement",
            censoring["cap_alarm_comparison"]
            == "returned_rows >= response_cap_rows"
            and censoring["checkpoint_advances_on_cap_alarm"] is False
            and contract["data_gate"]["b1_may_run_with_unresolved_censored_intervals"]
            is False,
            {
                "cap_alarms": health["counters"]["cap_alarms"],
                "news_since": health["news_since"],
                "unresolved_intervals": len(
                    health.get("unresolved_censoring_intervals", [])
                ),
            },
        )
    )

    database = NEWS_ROOT / "state/news_collector.sqlite3"
    with sqlite3.connect(database) as connection:
        invalid_rows, invalid_entities = connection.execute(
            "SELECT COUNT(*), COUNT(DISTINCT record_key) "
            "FROM invalid_timestamp_rows"
        ).fetchone()
        later_timely_entities = connection.execute(
            """
            SELECT COUNT(*)
            FROM (
                SELECT DISTINCT i.record_key
                FROM invalid_timestamp_rows i
                JOIN news_seen n USING(record_key)
                WHERE n.quarantined = 0
                  AND julianday(n.first_seen_at)
                      >= julianday(n.published_at) - (300.0 / 86400.0)
                  AND julianday(n.available_at) >= julianday(n.published_at)
            )
            """
        ).fetchone()[0]
        unsafe_unquarantined_entities = connection.execute(
            """
            SELECT COUNT(*)
            FROM (
                SELECT DISTINCT i.record_key
                FROM invalid_timestamp_rows i
                JOIN news_seen n USING(record_key)
                WHERE n.quarantined = 0
                  AND (
                      n.published_at IS NULL
                      OR n.available_at IS NULL
                      OR julianday(n.first_seen_at)
                         < julianday(n.published_at) - (300.0 / 86400.0)
                      OR julianday(n.available_at) < julianday(n.published_at)
                  )
            )
            """
        ).fetchone()[0]
    checks.append(
        result(
            "future-dated news identities are excluded from B1 primary",
            invalid_entities > 0 and unsafe_unquarantined_entities == 0,
            {
                "append_only_evidence_rows": invalid_rows,
                "distinct_invalid_entities": invalid_entities,
                "eventually_reobserved_with_timely_availability": later_timely_entities,
                "unsafe_unquarantined_invalid_entities": (
                    unsafe_unquarantined_entities
                ),
                "rule": (
                    "an early invalid observation never enters the primary stream; "
                    "a later observation may enter only within the frozen 300-second "
                    "tolerance and with available_at >= published_at"
                ),
            },
        )
    )

    collector_artifact = manifest["artifacts"]["news_collector_program"]
    collector_path = REPO_ROOT / collector_artifact["path"]
    checks.append(
        result(
            "runtime collector matches the frozen implementation manifest",
            restart["collector_sha256"] == collector_artifact["sha256"]
            == sha256_file(collector_path)
            and restart["implementation_manifest_sha256"]
            == sha256_file(IMPLEMENTATION_MANIFEST),
            {
                "collector_sha256": restart["collector_sha256"],
                "restart_receipt": str(receipts[-1].relative_to(REPO_ROOT)),
            },
        )
    )

    valid_historical: dict[str, bool] = {}
    for dataset in ("news", "kalshi_activity", "polymarket_activity"):
        dataset_manifest = load(HISTORICAL_ROOT / dataset / "manifest.json")
        valid_historical[dataset] = dataset_manifest.get("integrity_pass") is True
    checks.append(
        result(
            "historical recovery relies on hashed runtime receipts rather than OpenAPI response examples",
            all(valid_historical.values()),
            valid_historical,
        )
    )

    local_lineage = (
        restart.get("contract_sha256") == sha256_file(CONTRACT)
        and bool(restart.get("protocol_id"))
    )
    checks.append(
        result(
            "empty remote lineage listing is replaced by local code/contract/source receipts",
            local_lineage,
            {
                "contract_sha256": restart.get("contract_sha256"),
                "protocol_id": restart.get("protocol_id"),
            },
        )
    )

    failures = [value["check"] for value in checks if not value["passed"]]
    unresolved = len(health.get("unresolved_censoring_intervals", []))
    report = {
        "audited_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "b1_execution_authorized": not failures and unresolved == 0,
        "checks": checks,
        "failures": failures,
        "known_source_bugs_guarded": not failures,
        "labels_or_outcomes_read": False,
        "protocol_id": protocol["protocol_id"],
        "status": (
            "passed_ready_for_data_gate"
            if not failures and unresolved == 0
            else "guarded_pending_source_reconciliation"
            if not failures
            else "failed"
        ),
        "unresolved_censoring_intervals": unresolved,
    }
    atomic_json(output, report)
    print(json.dumps(report, indent=2, sort_keys=True))
    if failures:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
