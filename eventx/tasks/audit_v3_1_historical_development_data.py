"""Freeze the corrected EventX v3.1 development data gate.

The v3 gate already performed the full 21.7-million-row byte and receipt audit.
This task verifies that immutable gate, proves that v3.1 is exactly its valid
positive-notional subset, and rechecks the frozen news-support evidence without
reading labels, outcomes, or historical-holdout data.
"""

from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
from typing import Any, Iterator

from eventx.settings import REPO_ROOT


PROTOCOL = REPO_ROOT / "eventx/release/v3_1_historical_primary/protocol.json"
PREREG = (
    REPO_ROOT / "eventx/release/v3_1_historical_primary/preregistration_manifest.json"
)
POWER = REPO_ROOT / "data/v3_1_historical/primary/power/manifest.json"
OLD_GATE = REPO_ROOT / "data/v3_historical/primary/development/data_gate"
NEW_INPUT = REPO_ROOT / "data/v3_1_historical/primary/label_blind_inputs"
OUTPUT = REPO_ROOT / "data/v3_1_historical/primary/development/data_gate"
PROHIBITED = (
    REPO_ROOT / "data/v3_1_historical/primary/development/labels.jsonl",
    REPO_ROOT / "data/v3_1_historical/primary/development/results.json",
    REPO_ROOT / "data/v3_1_historical/primary/holdout",
)


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def relative(path: Path) -> str:
    return str(path.relative_to(REPO_ROOT))


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


def verify_manifest(path: Path) -> int:
    manifest = json.loads(path.read_text(encoding="utf-8"))
    checked = 0
    for artifact in manifest.get("artifacts", []):
        artifact_path = REPO_ROOT / str(artifact["path"])
        if not artifact_path.is_file() or sha256_file(artifact_path) != str(
            artifact["sha256"]
        ):
            raise RuntimeError(f"hash-lock failure: {artifact_path}")
        checked += 1
    return checked


def main() -> None:
    if any(path.exists() for path in PROHIBITED):
        raise SystemExit("outcome-bearing or holdout artifact exists; gate refused")
    locked_artifacts = sum(verify_manifest(path) for path in (PREREG, POWER, OLD_GATE / "manifest.json"))
    protocol = json.loads(PROTOCOL.read_text())
    cohort = {
        (str(row["venue"]), str(row["market_id"])): row
        for row in read_jsonl(NEW_INPUT / "cohort.jsonl")
    }
    old_stats = {
        (str(row["venue"]), str(row["market_id"])): row
        for row in read_jsonl(OLD_GATE / "market_stats.jsonl")
    }
    expected = {
        key
        for key, row in old_stats.items()
        if int(row["unique_executions"]) >= 100 and int(row["active_utc_days"]) >= 10
    }
    count_matches = all(
        int(row["trades"]) == int(old_stats[key]["unique_executions"])
        and int(row["active_days"]) == int(old_stats[key]["active_utc_days"])
        for key, row in cohort.items()
    )
    old_report = json.loads((OLD_GATE / "report.json").read_text())
    source_checks: dict[str, bool] = {}
    for venue, report in old_report["venue_reports"].items():
        for name, value in report["checks"].items():
            if name in {
                "all_frozen_markets_retain_100_execution_gate",
                "all_frozen_markets_retain_10_active_day_gate",
                "observed_counts_not_below_frozen_selection_counts",
                "observed_days_not_below_frozen_selection_days",
            }:
                continue
            source_checks[f"{venue}:{name}"] = bool(value)
    new_input_report = json.loads((NEW_INPUT / "report.json").read_text())
    checks = {
        "protocol_hash_and_pre_outcome_seal_pass": protocol.get("status")
        == "re_preregistered_after_label_blind_trade_gate_before_labels_or_outcomes",
        "predecessor_full_source_checks_pass_except_activity_thresholds": all(
            source_checks.values()
        ),
        "predecessor_zero_notional_policy_applied": old_report["venue_reports"][
            "kalshi"
        ]["zero_notional_rows_excluded"]
        == 204069,
        "corrected_cohort_is_exact_valid_subset": set(cohort) == expected,
        "corrected_cohort_count_is_frozen": len(cohort)
        == int(protocol["cohort"]["markets"])
        == 4651,
        "corrected_activity_counts_match_full_rescan": count_matches,
        "all_corrected_markets_meet_activity_gate": all(
            int(row["trades"]) >= 100 and int(row["active_days"]) >= 10
            for row in cohort.values()
        ),
        "corrected_news_support_gate_passed": new_input_report.get("integrity_pass")
        is True,
        "labels_or_outcomes_read": False,
        "holdout_prices_read": False,
    }
    passed = all(
        value is True
        for name, value in checks.items()
        if name not in {"labels_or_outcomes_read", "holdout_prices_read"}
    ) and checks["labels_or_outcomes_read"] is False and checks[
        "holdout_prices_read"
    ] is False
    report_path = OUTPUT / "report.json"
    report = {
        "protocol_id": protocol["protocol_id"],
        "created_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "status": "passed_and_frozen" if passed else "failed",
        "integrity_pass": passed,
        "label_blind": True,
        "labels_or_outcomes_read": False,
        "holdout_prices_read": False,
        "locked_artifacts_checked": locked_artifacts,
        "cohort_markets": len(cohort),
        "by_venue": {
            venue: sum(key[0] == venue for key in cohort)
            for venue in ("kalshi", "polymarket")
        },
        "source_rows": {
            venue: old_report["venue_reports"][venue]["raw_rows"]
            for venue in ("kalshi", "polymarket")
        },
        "positive_notional_executions": {
            venue: old_report["venue_reports"][venue]["unique_executions"]
            for venue in ("kalshi", "polymarket")
        },
        "zero_notional_rows_excluded": 204069,
        "exact_duplicate_rows_collapsed": sum(
            old_report["venue_reports"][venue]["exact_duplicate_rows_collapsed"]
            for venue in ("kalshi", "polymarket")
        ),
        "news_documents": new_input_report["news"]["development_documents"],
        "news_associations": new_input_report["development_associations"]["total"],
        "source_checks_reused_from_full_rescan": source_checks,
        "checks": checks,
    }
    atomic_json(report_path, report)
    manifest_path = OUTPUT / "manifest.json"
    artifacts = (
        PROTOCOL,
        PREREG,
        POWER,
        OLD_GATE / "manifest.json",
        OLD_GATE / "report.json",
        OLD_GATE / "market_stats.jsonl",
        NEW_INPUT / "cohort.jsonl",
        NEW_INPUT / "development_association_counts.jsonl",
        NEW_INPUT / "report.json",
        Path(__file__).resolve(),
        report_path,
    )
    atomic_json(
        manifest_path,
        {
            "protocol_id": protocol["protocol_id"],
            "status": "frozen_pre_outcome_development_data_gate",
            "labels_or_outcomes_read": False,
            "holdout_prices_read": False,
            "artifacts": [
                {"path": relative(path), "sha256": sha256_file(path)}
                for path in artifacts
            ],
        },
    )
    print(json.dumps(report, indent=2, sort_keys=True))
    if not passed:
        raise SystemExit(2)


if __name__ == "__main__":
    main()
