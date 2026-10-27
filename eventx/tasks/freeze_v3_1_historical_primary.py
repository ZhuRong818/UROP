"""Create the pre-outcome EventX v3.1 corrected-cohort preregistration."""

from __future__ import annotations

from copy import deepcopy
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
from typing import Any, Iterator

from eventx.settings import REPO_ROOT


OLD_RELEASE = REPO_ROOT / "eventx/release/v3_historical_primary"
NEW_RELEASE = REPO_ROOT / "eventx/release/v3_1_historical_primary"
OLD_INPUT = REPO_ROOT / "data/v3_historical/primary/label_blind_inputs"
OLD_GATE = REPO_ROOT / "data/v3_historical/primary/development/data_gate"
NEW_INPUT = REPO_ROOT / "data/v3_1_historical/primary/label_blind_inputs"
NEW_DEVELOPMENT = REPO_ROOT / "data/v3_1_historical/primary/development"
NEW_HOLDOUT = REPO_ROOT / "data/v3_1_historical/primary/holdout"
PROTOCOL_ID = "eventx-v3.1-historical-primary-20260902"


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def relative(path: Path) -> str:
    return str(path.relative_to(REPO_ROOT))


def atomic_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n")
    os.replace(temporary, path)


def atomic_jsonl(path: Path, values: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    with temporary.open("w", encoding="utf-8") as handle:
        for value in values:
            handle.write(json.dumps(value, sort_keys=True, separators=(",", ":")) + "\n")
    os.replace(temporary, path)


def read_jsonl(path: Path) -> Iterator[dict[str, Any]]:
    with path.open(encoding="utf-8") as handle:
        for line in handle:
            if line.strip():
                value = json.loads(line)
                if not isinstance(value, dict):
                    raise RuntimeError(f"non-object JSONL row in {path}")
                yield value


def verify_manifest(path: Path) -> None:
    manifest = json.loads(path.read_text(encoding="utf-8"))
    for artifact in manifest.get("artifacts", []):
        artifact_path = REPO_ROOT / str(artifact["path"])
        if not artifact_path.is_file() or sha256_file(artifact_path) != str(
            artifact["sha256"]
        ):
            raise RuntimeError(f"hash-lock failure: {artifact_path}")


def main() -> None:
    prohibited = (
        OLD_INPUT.parent / "development/labels.jsonl",
        OLD_INPUT.parent / "holdout",
        NEW_DEVELOPMENT / "labels.jsonl",
        NEW_HOLDOUT,
    )
    if any(path.exists() for path in prohibited):
        raise SystemExit("labels or historical holdout material exist; revision prohibited")
    verify_manifest(OLD_RELEASE / "preregistration_manifest.json")
    verify_manifest(REPO_ROOT / "data/v3_historical/primary/power/manifest.json")
    verify_manifest(OLD_GATE / "manifest.json")
    old_gate_report = json.loads((OLD_GATE / "report.json").read_text())
    if old_gate_report.get("integrity_pass") is not False:
        raise SystemExit("expected the preserved v3 data-gate failure")
    if old_gate_report.get("labels_or_outcomes_read") is not False:
        raise SystemExit("v3 gate is not label blind")
    if old_gate_report.get("holdout_prices_read") is not False:
        raise SystemExit("v3 gate read historical holdout prices")

    old_cohort = {
        (str(row["venue"]), str(row["market_id"])): row
        for row in read_jsonl(OLD_INPUT / "cohort.jsonl")
    }
    stats = {
        (str(row["venue"]), str(row["market_id"])): row
        for row in read_jsonl(OLD_GATE / "market_stats.jsonl")
    }
    if set(old_cohort) != set(stats):
        raise SystemExit("v3 gate statistics do not exactly cover the frozen cohort")

    kept: list[dict[str, Any]] = []
    removed: list[dict[str, Any]] = []
    for key in sorted(old_cohort):
        source = old_cohort[key]
        observed = stats[key]
        valid_trades = int(observed["unique_executions"])
        valid_days = int(observed["active_utc_days"])
        if valid_trades < 100 or valid_days < 10:
            removed.append(
                {
                    "venue": key[0],
                    "market_id": key[1],
                    "valid_executions": valid_trades,
                    "valid_active_utc_days": valid_days,
                    "reason": [
                        reason
                        for condition, reason in (
                            (valid_trades < 100, "fewer_than_100_valid_executions"),
                            (valid_days < 10, "fewer_than_10_valid_active_utc_days"),
                        )
                        if condition
                    ],
                }
            )
            continue
        row = dict(source)
        row["trades"] = valid_trades
        row["active_days"] = valid_days
        row["selection_normalization"] = "positive_notional_composite_execution_key"
        kept.append(row)
    if len(kept) != 4651 or len(removed) != 19:
        raise SystemExit(f"unexpected corrected cohort: kept={len(kept)} removed={len(removed)}")

    cohort_path = NEW_INPUT / "cohort.jsonl"
    removed_path = NEW_INPUT / "removed_markets.jsonl"
    atomic_jsonl(cohort_path, kept)
    atomic_jsonl(removed_path, removed)
    kept_keys = {(str(row["venue"]), str(row["market_id"])) for row in kept}
    association_rows = [
        row
        for row in read_jsonl(OLD_INPUT / "development_association_counts.jsonl")
        if (str(row["venue"]), str(row["market_id"])) in kept_keys
    ]
    if len(association_rows) != len(kept):
        raise SystemExit("corrected association rows do not exactly cover cohort")
    associations_path = NEW_INPUT / "development_association_counts.jsonl"
    atomic_jsonl(associations_path, association_rows)
    association_total = sum(int(row["association_count"]) for row in association_rows)
    association_max = max(int(row["association_count"]) for row in association_rows)
    association_markets_five = sum(
        int(row["association_count"]) >= 5 for row in association_rows
    )
    by_venue = {
        venue: sum(str(row["venue"]) == venue for row in kept)
        for venue in ("kalshi", "polymarket")
    }
    old_input_report = json.loads((OLD_INPUT / "report.json").read_text())
    gates = {
        "corrected_cohort_markets_at_least_30": len(kept) >= 30,
        "corrected_cohort_each_venue_at_least_5": all(
            value >= 5 for value in by_venue.values()
        ),
        "all_markets_at_least_100_valid_executions": all(
            int(row["trades"]) >= 100 for row in kept
        ),
        "all_markets_at_least_10_valid_active_days": all(
            int(row["active_days"]) >= 10 for row in kept
        ),
        "development_news_calendar_days_at_least_56": old_input_report["news"][
            "usable_calendar_days"
        ]
        >= 56,
        "development_associations_at_least_200": association_total >= 200,
        "development_markets_with_five_associations_at_least_20": association_markets_five
        >= 20,
        "maximum_single_market_share_at_most_half": association_max
        / association_total
        <= 0.5,
    }
    if not all(gates.values()):
        raise SystemExit(f"corrected label-blind support gate failed: {gates}")
    input_report_path = NEW_INPUT / "report.json"
    input_report = {
        "protocol_id": PROTOCOL_ID,
        "created_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "status": "passed_pre_outcome_corrected_cohort_gate",
        "label_blind": True,
        "labels_or_outcomes_read": False,
        "trade_price_values_used_for_revision": False,
        "historical_holdout_covariates_used": False,
        "holdout_prices_read": False,
        "predecessor": {
            "protocol_id": old_gate_report["protocol_id"],
            "data_gate_status": old_gate_report["status"],
            "report_path": relative(OLD_GATE / "report.json"),
            "report_sha256": sha256_file(OLD_GATE / "report.json"),
        },
        "revision": {
            "rule": "retain exactly markets with >=100 positive-notional composite-key executions on >=10 development UTC days",
            "original_markets": len(old_cohort),
            "removed_markets": len(removed),
            "retained_markets": len(kept),
            "zero_notional_rows_excluded": old_gate_report["venue_reports"]["kalshi"][
                "zero_notional_rows_excluded"
            ],
            "removed_path": relative(removed_path),
            "removed_sha256": sha256_file(removed_path),
        },
        "cohort": {
            "markets": len(kept),
            "by_venue": by_venue,
            "path": relative(cohort_path),
            "sha256": sha256_file(cohort_path),
        },
        "news": old_input_report["news"],
        "development_associations": {
            "total": association_total,
            "markets_with_at_least_five": association_markets_five,
            "maximum_for_one_market": association_max,
            "maximum_market_share": association_max / association_total,
            "path": relative(associations_path),
            "sha256": sha256_file(associations_path),
        },
        "gates": gates,
        "integrity_pass": True,
    }
    atomic_json(input_report_path, input_report)

    old_protocol = json.loads((OLD_RELEASE / "protocol.json").read_text())
    protocol = deepcopy(old_protocol)
    protocol["protocol_id"] = PROTOCOL_ID
    protocol["created_at"] = datetime.now(timezone.utc).isoformat().replace(
        "+00:00", "Z"
    )
    protocol["status"] = (
        "re_preregistered_after_label_blind_trade_gate_before_labels_or_outcomes"
    )
    protocol["authorization"]["scope"] = (
        "minimal pre-outcome correction after the v3 trade gate found zero-notional "
        "warehouse rows; all confirmatory analysis rules remain unchanged"
    )
    protocol["integrity"].update(
        {
            "labels_inspected_before_revision": False,
            "outcomes_inspected_before_revision": False,
            "predecessor_trade_prices_retrieved_before_freeze": False,
            "trade_prices_retrieved_before_freeze": True,
            "trade_prices_retrieved_before_revision": True,
            "trade_price_values_used_for_revision": False,
            "revision_inputs": "development execution identity, positive notional and active UTC day only",
        }
    )
    protocol["cohort"].update(
        {
            "selection_rule": "include every market with earliest Lumid metadata available before development close, a unique canonical YES outcome, at least 100 positive-notional canonical-YES development executions under the composite key, and at least 10 development active UTC days",
            "markets": len(kept),
            "by_venue": by_venue,
            "path": relative(cohort_path),
            "sha256": sha256_file(cohort_path),
            "predecessor_markets_removed_by_label_blind_data_gate": len(removed),
            "reselection_after_labels": False,
        }
    )
    protocol["news_association"].update(
        {
            "development_associations": association_total,
            "development_markets_with_at_least_five": association_markets_five,
            "maximum_single_market_share": association_max / association_total,
        }
    )
    protocol["revision"] = {
        "predecessor_protocol_id": old_protocol["protocol_id"],
        "predecessor_result": "failed_label_blind_development_trade_gate",
        "observed_source_issue": "204069 Kalshi rows with count=0",
        "change": "remove exactly 19 markets failing the original activity minimum after positive-notional normalization",
        "unchanged": [
            "research_question",
            "source_policy",
            "windows",
            "news_availability",
            "news_association_rule",
            "price",
            "eligibility",
            "labels",
            "features",
            "learner",
            "development_validation",
            "metrics",
            "uncertainty",
            "promotion_gate",
            "one_shot_holdout",
        ],
    }
    protocol["execution_order"] = [
        "preserve failed v3 label-blind data gate and its immutable artifacts",
        "freeze corrected positive-notional cohort before labels or outcomes",
        "rerun and freeze synthetic market-cluster power sensitivity",
        "pass and freeze corrected development data and feature gate",
        *old_protocol["execution_order"][5:],
    ]
    protocol["frozen_evidence"]["label_blind_input_report"] = {
        "path": relative(input_report_path),
        "sha256": sha256_file(input_report_path),
    }
    protocol["frozen_evidence"]["predecessor_failed_data_gate"] = {
        "path": relative(OLD_GATE / "report.json"),
        "sha256": sha256_file(OLD_GATE / "report.json"),
    }
    protocol_path = NEW_RELEASE / "protocol.json"
    atomic_json(protocol_path, protocol)

    preregistration_path = NEW_RELEASE / "PREREGISTRATION.md"
    artifacts = [
        protocol_path,
        preregistration_path,
        cohort_path,
        removed_path,
        associations_path,
        input_report_path,
        OLD_RELEASE / "protocol.json",
        OLD_GATE / "manifest.json",
        OLD_GATE / "report.json",
        OLD_RELEASE / "IMPLEMENTATION_AMENDMENT_1.md",
        OLD_RELEASE / "IMPLEMENTATION_AMENDMENT_2.md",
        OLD_RELEASE / "IMPLEMENTATION_AMENDMENT_3.md",
        REPO_ROOT / "data/v3_historical/provenance_audit_v2/report.json",
        REPO_ROOT / "eventx/features/v2_1_association.py",
        REPO_ROOT / "eventx/tasks/build_v2_1_taxonomy.py",
        REPO_ROOT / "eventx/release/v2_3/protocol.json",
        Path(__file__).resolve(),
    ]
    manifest = {
        "protocol_id": PROTOCOL_ID,
        "manifest_id": "eventx-v3.1-historical-primary-preregistration-20260902",
        "labels_or_outcomes_inspected": False,
        "historical_holdout_covariates_used": False,
        "trade_price_values_used_for_revision": False,
        "artifacts": [
            {"path": relative(path), "sha256": sha256_file(path)}
            for path in artifacts
        ],
    }
    manifest_path = NEW_RELEASE / "preregistration_manifest.json"
    atomic_json(manifest_path, manifest)
    print(json.dumps(input_report, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
