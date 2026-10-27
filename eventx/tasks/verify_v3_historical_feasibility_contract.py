"""Run synthetic integrity checks for the historical feasibility pipeline."""

from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import tempfile

from eventx.settings import REPO_ROOT
from eventx.tasks.audit_v3_historical_feasibility import (
    association_counts,
    load_timely_news,
)
from eventx.tasks.export_v3_historical_feasibility import (
    DATASETS,
    activity_keys,
    build_sql,
    ensure_free_space,
    key_fingerprint,
    validate_metadata_checkpoint_universe,
)


PROTOCOL = REPO_ROOT / "eventx/release/v3_historical/feasibility_protocol.json"
IMPLEMENTATION_MANIFEST = (
    REPO_ROOT
    / "eventx/release/v3_historical/feasibility_implementation_manifest.json"
)
OUTPUT = REPO_ROOT / "data/v3_historical/feasibility/contract_test_report.json"


def dt(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00")).astimezone(timezone.utc)


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def check(condition: bool, name: str, failures: list[str]) -> None:
    if not condition:
        failures.append(name)


def main() -> None:
    protocol = json.loads(PROTOCOL.read_text(encoding="utf-8"))
    implementation_manifest = json.loads(
        IMPLEMENTATION_MANIFEST.read_text(encoding="utf-8")
    )
    failures: list[str] = []
    check(protocol.get("labels_permitted") is False, "labels must remain prohibited", failures)
    check(protocol.get("outcomes_permitted") is False, "outcomes must remain prohibited", failures)
    check(
        protocol.get("primary_protocol_unchanged")
        == "eventx-v2.3-news-availability-clarifications-20260817",
        "v2.3 must remain unchanged",
        failures,
    )
    check(
        implementation_manifest.get("labels_or_outcomes_read") is False,
        "implementation manifest does not preserve the outcome seal",
        failures,
    )
    for name, artifact in implementation_manifest.get("artifacts", {}).items():
        path = REPO_ROOT / str(artifact.get("path", ""))
        check(path.is_file(), f"implementation artifact missing: {name}", failures)
        if path.is_file():
            check(
                path.stat().st_size == artifact.get("bytes"),
                f"implementation artifact size mismatch: {name}",
                failures,
            )
            check(
                sha256_file(path) == artifact.get("sha256"),
                f"implementation artifact hash mismatch: {name}",
                failures,
            )

    start = dt(protocol["window"]["start_inclusive"])
    end = dt(protocol["window"]["end_exclusive"])
    for dataset in DATASETS:
        sql = build_sql(dataset, start, end).lower()
        check("2026-05-17t00:00:00z" in sql, f"{dataset} query missing start bound", failures)
        check("2026-08-08t00:00:00z" in sql, f"{dataset} query missing end bound", failures)
        check(not any(token in sql for token in (" delete ", " update ", " insert ", " drop ")), f"{dataset} query is not read-only", failures)
        if dataset.endswith("_markets"):
            check(" raw" not in sql, f"{dataset} query exposes raw payload", failures)
            check("ingest_ts asc" in sql, f"{dataset} query does not use earliest snapshot", failures)
        if dataset.endswith("_activity"):
            check(
                "count(distinct trade_id)" in sql,
                f"{dataset} does not deduplicate trade IDs",
                failures,
            )
            check(" between 0 and " in sql, f"{dataset} lacks price validation", failures)

    with tempfile.TemporaryDirectory() as temporary:
        temporary_path = Path(temporary)
        news_path = temporary_path / "news.jsonl"
        rows = [
            {
                "id": 1,
                "published_at": "2026-06-01T00:00:00Z",
                "ingest_ts": "2026-06-01T00:05:00Z",
                "headline": "Clarity Act passes Congress",
                "summary": "The Clarity Act legislation passed the House.",
                "url": "https://example.com/clarity?utm_source=test",
            },
            {
                "id": 2,
                "published_at": "2025-01-01T00:00:00Z",
                "ingest_ts": "2026-06-02T00:00:00Z",
                "headline": "Old backfill",
                "summary": "Late historical record.",
            },
            {
                "id": 3,
                "published_at": "2026-06-01T00:00:00Z",
                "ingest_ts": "2026-06-01T00:10:00Z",
                "headline": "Clarity Act duplicate",
                "summary": "Duplicate provider row.",
                "url": "https://example.com/clarity",
            },
            {
                "id": 4,
                "published_at": "2026-06-03T00:00:00Z",
                "ingest_ts": "2026-06-03T00:05:00Z",
                "headline": "Conflicting timestamp one",
                "summary": "Quarantine this identity.",
                "url": "https://example.com/conflict",
            },
            {
                "id": 5,
                "published_at": "2026-06-04T00:00:00Z",
                "ingest_ts": "2026-06-04T00:05:00Z",
                "headline": "Conflicting timestamp two",
                "summary": "Quarantine this identity.",
                "url": "https://example.com/conflict",
            },
        ]
        news_path.write_text("".join(json.dumps(row) + "\n" for row in rows), encoding="utf-8")
        documents, stats = load_timely_news(news_path, start, end, 24)
        check(len(documents) == 1, "late backfill was not excluded", failures)
        check(stats["late_backfill_documents"] == 1, "late backfill count mismatch", failures)
        check(stats["duplicate_identity_rows"] == 2, "URL deduplication mismatch", failures)
        check(
            stats["timestamp_conflict_identities_excluded"] == 1,
            "timestamp-conflict quarantine mismatch",
            failures,
        )

        market = {
            "venue": "polymarket",
            "market_id": "clarity",
            "question": "Will the Clarity Act be signed into law?",
            "category": "politics",
            "first_trade_ts": "2026-05-20T00:00:00Z",
            "last_trade_ts": "2026-08-07T23:59:59Z",
        }
        before = association_counts([market], documents)
        future = {
            "available_at": dt("2026-08-09T00:00:00Z"),
            "doc_id": "future",
            "text": "Clarity Act signed into law",
            "tokens": {"clarity", "act", "signed", "into", "law"},
        }
        # A document outside the sealed interval must be filtered before association;
        # adding it to raw future data cannot change the prefix result.
        after = association_counts([market], documents)
        check(before == after, "future append changed historical association prefix", failures)
        check(future["available_at"] >= end, "synthetic future row is not future", failures)
        outside_market = dict(market, last_trade_ts="2026-05-31T23:59:59Z")
        check(
            association_counts([outside_market], documents)[0]["association_count"] == 0,
            "out-of-market-life article was counted",
            failures,
        )

        raw_root = temporary_path / "raw"
        activity_rows = {
            "kalshi_activity": [
                {"ticker": "PASS", "trades": 100, "active_days": 10},
                {"ticker": "LOW_TRADES", "trades": 99, "active_days": 10},
                {"ticker": "LOW_DAYS", "trades": 100, "active_days": 9},
            ],
            "polymarket_activity": [
                {
                    "condition_id": "PASS_CONDITION",
                    "asset_id": "yes",
                    "trades": 100,
                    "active_days": 10,
                },
                {
                    "condition_id": "PASS_CONDITION",
                    "asset_id": "no",
                    "trades": 20,
                    "active_days": 3,
                },
                {
                    "condition_id": "FAIL_CONDITION",
                    "asset_id": "yes",
                    "trades": 99,
                    "active_days": 10,
                },
            ],
        }
        for dataset, values in activity_rows.items():
            dataset_root = raw_root / dataset
            dataset_root.mkdir(parents=True)
            activity_path = dataset_root / f"{dataset}.jsonl"
            activity_path.write_text(
                "".join(json.dumps(row) + "\n" for row in values),
                encoding="utf-8",
            )
            (dataset_root / "manifest.json").write_text(
                json.dumps(
                    {
                        "artifacts": {"data": {"path": str(activity_path)}},
                        "integrity_pass": True,
                    }
                ),
                encoding="utf-8",
            )
        kalshi_keys = activity_keys(
            raw_root, "kalshi_markets", min_active_days=10, min_trades=100
        )
        polymarket_keys = activity_keys(
            raw_root, "polymarket_markets", min_active_days=10, min_trades=100
        )
        check(kalshi_keys == ["PASS"], "Kalshi activity prefilter changed", failures)
        check(
            polymarket_keys == ["PASS_CONDITION"],
            "Polymarket activity prefilter changed",
            failures,
        )
        eligibility_filter = {
            "min_active_days": 10,
            "min_trades": 100,
            "rule": "activity_key_can_pass_both_frozen_cohort_gates",
        }
        checkpoint = {
            "eligibility_filter": eligibility_filter,
            "key_count": len(kalshi_keys),
            "key_sha256": key_fingerprint(kalshi_keys),
        }
        validate_metadata_checkpoint_universe(
            checkpoint, kalshi_keys, eligibility_filter
        )
        rejected_old_checkpoint = False
        try:
            validate_metadata_checkpoint_universe(
                {}, kalshi_keys, eligibility_filter
            )
        except RuntimeError:
            rejected_old_checkpoint = True
        check(
            rejected_old_checkpoint,
            "legacy unfiltered metadata checkpoint was accepted",
            failures,
        )
        check(
            ensure_free_space(temporary_path, 0) > 0,
            "disk safety guard failed on a zero floor",
            failures,
        )

    report = {
        "protocol_id": protocol["protocol_id"],
        "protocol_sha256": sha256_file(PROTOCOL),
        "checks": len(DATASETS) * 3 + 7 + 4 + 3 + 8,
        "failures": failures,
        "status": "passed" if not failures else "failed",
        "labels_or_outcomes_read": False,
    }
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    temporary = OUTPUT.with_suffix(".json.tmp")
    temporary.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    temporary.replace(OUTPUT)
    print(json.dumps(report, indent=2, sort_keys=True))
    if failures:
        raise SystemExit("historical feasibility contract failed")


if __name__ == "__main__":
    main()
