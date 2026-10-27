"""Run the frozen, outcome-blind EventX v4 collection completeness gate."""

from __future__ import annotations

from collections import Counter
from datetime import datetime, timedelta, timezone
import json
import os
from pathlib import Path
from typing import Any, Iterator

from eventx.settings import REPO_ROOT
from eventx.tasks.audit_v3_historical_feasibility import parse_utc
from eventx.tasks.prepare_v3_1_historical_development_arrays import sha256_file


ROOT = REPO_ROOT / "data/v4/confirmatory/sealed_inputs"
COHORT = REPO_ROOT / "data/v4/confirmatory/cohort_gate/cohort.jsonl"
STATE = ROOT / "collector_state.json"
REPORT = REPO_ROOT / "data/v4/confirmatory/collection_gate/report.json"
MANIFEST = REPO_ROOT / "data/v4/confirmatory/collection_gate/manifest.json"
NEWS_START = parse_utc("2026-08-30T00:00:00Z")
TRADE_START = parse_utc("2026-09-06T00:00:00Z")
END = parse_utc("2026-10-30T00:00:00Z")
BATCH_SIZE = 50


def read_jsonl(path: Path) -> Iterator[dict[str, Any]]:
    with path.open(encoding="utf-8") as handle:
        for line in handle:
            if line.strip():
                yield json.loads(line)


def atomic_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n")
    os.replace(temporary, path)


def days(start: datetime, end: datetime) -> Iterator[datetime]:
    value = start
    while value < end:
        yield value
        value += timedelta(days=1)


def validate_artifact(data: Path, sql: Path, receipt_path: Path) -> tuple[int, dict[str, Any]]:
    if not data.is_file() or not sql.is_file() or not receipt_path.is_file():
        raise RuntimeError(f"missing sealed partition: {data}")
    receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
    if sha256_file(data) != receipt["data_sha256"]:
        raise RuntimeError(f"data hash mismatch: {data}")
    if sha256_file(sql) != receipt["sql_sha256"]:
        raise RuntimeError(f"SQL hash mismatch: {sql}")
    rowcount = sum(1 for _ in read_jsonl(data))
    if rowcount != int(receipt["receipt"]["rowcount"]):
        raise RuntimeError(f"receipt row count mismatch: {data}")
    return rowcount, receipt


def main() -> None:
    if REPORT.exists() or MANIFEST.exists():
        raise SystemExit("v4 collection gate already exists")
    state = json.loads(STATE.read_text(encoding="utf-8"))
    cohort = list(read_jsonl(COHORT))
    pairs = [
        (str(row["market_id"]), str(row["canonical_yes_asset_id"]))
        for row in cohort
    ]
    counters: Counter[str] = Counter()
    input_artifacts: list[dict[str, str]] = []
    news_ids: set[str] = set()
    for day in days(NEWS_START, END):
        root = ROOT / "news" / day.date().isoformat()
        data = root / "articles.jsonl"
        sql = root / "articles.sql"
        receipt_path = root / "articles_receipt.json"
        rowcount, _receipt = validate_artifact(data, sql, receipt_path)
        counters["news_days"] += 1
        counters["news_rows"] += rowcount
        for row in read_jsonl(data):
            ingest = parse_utc(str(row["ingest_ts"]))
            published = parse_utc(str(row["published_at"]))
            run_start = parse_utc(str(row["run_started_at"]))
            run_end = parse_utc(str(row["run_ended_at"])) if row.get("run_ended_at") else ingest
            if not day <= ingest < day + timedelta(days=1):
                raise RuntimeError(f"news outside ingest partition: {data}")
            if not published <= ingest <= published + timedelta(hours=24):
                raise RuntimeError(f"invalid news publication/ingest lag: {data}")
            if ingest < run_start or run_end < run_start:
                raise RuntimeError(f"invalid news provenance clock: {data}")
            if str(row.get("run_status")) != "ok":
                raise RuntimeError(f"non-ok news provenance run: {data}")
            identity = str(row["id"])
            if identity in news_ids:
                raise RuntimeError(f"duplicate article id across partitions: {identity}")
            news_ids.add(identity)
        input_artifacts.extend(
            {"path": str(path.relative_to(REPO_ROOT)), "sha256": sha256_file(path)}
            for path in (data, sql, receipt_path)
        )

    expected_batches = [pairs[start : start + BATCH_SIZE] for start in range(0, len(pairs), BATCH_SIZE)]
    for day in days(TRADE_START, END):
        root = ROOT / "trades" / day.date().isoformat()
        for number, group in enumerate(expected_batches, start=1):
            name = f"batch_{number:03d}"
            data = root / f"{name}.jsonl"
            sql = root / f"{name}.sql"
            receipt_path = root / f"{name}_receipt.json"
            rowcount, _receipt = validate_artifact(data, sql, receipt_path)
            allowed = set(group)
            previous: tuple[str, str, str, str] | None = None
            previous_payload: tuple[float, float] | None = None
            for row in read_jsonl(data):
                timestamp = parse_utc(str(row["ts"]))
                pair = (str(row["condition_id"]), str(row.get("asset_id") or ""))
                if pair not in allowed:
                    raise RuntimeError(f"trade outside frozen batch: {data}")
                if not day <= timestamp < day + timedelta(days=1):
                    raise RuntimeError(f"trade outside time partition: {data}")
                price = float(row["price"])
                size = float(row["size"])
                if not 0.0 <= price <= 1.0 or not size > 0.0:
                    raise RuntimeError(f"invalid positive-notional YES trade: {data}")
                key = (pair[0], pair[1], str(row["trade_id"]), str(row["ts"]))
                payload = (price, size)
                if key == previous:
                    if payload != previous_payload:
                        raise RuntimeError(f"conflicting adjacent trade duplicate: {data}")
                    counters["exact_trade_duplicates"] += 1
                previous, previous_payload = key, payload
            counters["trade_partitions"] += 1
            counters["trade_rows"] += rowcount
            input_artifacts.extend(
                {"path": str(path.relative_to(REPO_ROOT)), "sha256": sha256_file(path)}
                for path in (data, sql, receipt_path)
            )
        counters["trade_days"] += 1

    checks = {
        "collector_complete": state.get("status") == "sealed_collection_complete_pending_data_gate",
        "expected_news_days": counters["news_days"] == (END - NEWS_START).days,
        "expected_trade_days": counters["trade_days"] == (END - TRADE_START).days,
        "expected_trade_partitions": counters["trade_partitions"]
        == (END - TRADE_START).days * len(expected_batches),
        "news_rows_nonempty": counters["news_rows"] > 0,
        "trade_rows_nonempty": counters["trade_rows"] > 0,
        "labels_predictions_prevalence_or_metrics_read": False,
    }
    passed = all(
        value is True
        for name, value in checks.items()
        if name != "labels_predictions_prevalence_or_metrics_read"
    ) and checks["labels_predictions_prevalence_or_metrics_read"] is False
    report = {
        "protocol_id": "eventx-v4-confirmatory-polymarket-20260902",
        "created_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "status": "passed" if passed else "failed",
        "integrity_pass": passed,
        "outcome_blind": True,
        "counts": dict(counters),
        "checks": checks,
        "input_artifacts": input_artifacts,
    }
    atomic_json(REPORT, report)
    atomic_json(MANIFEST, {
        "protocol_id": report["protocol_id"],
        "status": report["status"],
        "artifacts": [
            {"path": str(path.relative_to(REPO_ROOT)), "sha256": sha256_file(path)}
            for path in (REPORT, COHORT, STATE, Path(__file__).resolve())
        ],
        "input_artifacts": input_artifacts,
    })
    print(json.dumps({
        "status": report["status"],
        "counts": report["counts"],
        "checks": report["checks"],
    }, indent=2, sort_keys=True))
    if not passed:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
