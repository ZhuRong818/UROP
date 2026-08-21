"""Verify the EventX v2.3 label-blind clarification preregistration and lineage."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
from typing import Any

from eventx.settings import REPO_ROOT
from eventx.tasks.collect_v2_3_news import availability_time, is_cap_alarm, validate_contract
from eventx.tasks.verify_v2_preregistration import (
    V1_RECEIPT,
    load_json,
    repo_path,
    sha256_file,
)


DEFAULT_MANIFEST = (
    REPO_ROOT / "eventx" / "release" / "v2_3" / "preregistration_manifest.json"
)


def verify_artifact(
    name: str,
    specification: dict[str, Any],
    failures: list[str],
) -> None:
    try:
        path = repo_path(specification["path"])
    except (KeyError, TypeError, ValueError) as exc:
        failures.append(f"{name}: invalid path: {exc}")
        return
    if not path.is_file():
        failures.append(f"{name}: missing {specification.get('path')}")
        return
    if path.stat().st_size != specification.get("bytes"):
        failures.append(f"{name}: byte count mismatch")
    if sha256_file(path) != specification.get("sha256"):
        failures.append(f"{name}: SHA-256 mismatch")


def utc(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00")).astimezone(timezone.utc)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST)
    args = parser.parse_args()
    manifest_path = args.manifest
    if not manifest_path.is_absolute():
        manifest_path = (Path.cwd() / manifest_path).resolve()
    manifest = load_json(manifest_path)

    failures: list[str] = []
    if manifest.get("preregistration_schema") != 1:
        failures.append("unsupported preregistration manifest schema")
    if manifest.get("locked") is not True:
        failures.append("preregistration manifest is not locked")
    if manifest.get("status") != "preregistered_labels_uninspected":
        failures.append("unexpected manifest status")
    for name, specification in manifest.get("artifacts", {}).items():
        verify_artifact(name, specification, failures)

    protocol_path = repo_path(manifest["protocol"]["path"])
    protocol = load_json(protocol_path)
    if sha256_file(protocol_path) != manifest["protocol"].get("sha256"):
        failures.append("protocol SHA-256 mismatch")
    if protocol.get("protocol_id") != manifest.get("protocol_id"):
        failures.append("protocol ID mismatch")
    if protocol.get("status") != "preregistered_labels_uninspected":
        failures.append("protocol is not label-uninspected")

    windows = protocol.get("windows", {})
    if windows.get("development") != {
        "start": "2026-08-08T00:00:00Z",
        "end_exclusive": "2026-09-28T00:00:00Z",
    }:
        failures.append("development window changed from v2.2")
    if windows.get("reconciliation_freeze") != {
        "start": "2026-09-28T00:00:00Z",
        "end_exclusive": "2026-10-01T00:00:00Z",
    }:
        failures.append("72-hour reconciliation/freeze window mismatch")
    if windows.get("holdout") != {
        "start": "2026-10-01T00:00:00Z",
        "end_exclusive": "2026-10-22T00:00:00Z",
    }:
        failures.append("October holdout changed from v2.2")

    comparison = protocol.get("confirmatory_comparison", {})
    if comparison.get("candidate") != "b1_market_core_news":
        failures.append("B1 is not the confirmatory candidate")
    if comparison.get("reference") != "b0_market_only":
        failures.append("B0 is not the confirmatory reference")
    if comparison.get("tests_kol_incremental_information") is not False:
        failures.append("v2.3 must not claim to test KOL incremental information")

    expected_hypotheses = {
        "h1": "AP(B1) - AP(B0) > 0",
        "h2": "Brier(B0) - Brier(B1) > 0",
        "h3": "both_h1_and_h2_improvements_positive_in_at_least_4_of_5_outer_folds",
        "h4": "paired_moving_block_bootstrap_95pct_lower_bound_for_Brier(B0)-Brier(B1) > 0",
        "h5": "Brier(B0)-Brier(B1) >= 0_in_each_of_polymarket_and_kalshi",
    }
    hypotheses = protocol.get("confirmatory_hypotheses", {})
    for key, expected in expected_hypotheses.items():
        if hypotheses.get(key) != expected:
            failures.append(f"explicit {key} mismatch")
    if hypotheses.get("required_for_b1_promotion") != ["h1", "h2", "h3", "h4", "h5"]:
        failures.append("all five explicit hypotheses must be required for B1 promotion")
    if hypotheses.get("historical_kol_h1_h6_run") is not False:
        failures.append("historical KOL hypotheses must not run")

    promotion = protocol.get("promotion_gate", {})
    if promotion.get("undefined_fold_metric") != "fold_does_not_count_as_positive":
        failures.append("undefined-fold disposition mismatch")
    if promotion.get("undefined_aggregate_required_metric") != "corresponding_condition_unsatisfied":
        failures.append("undefined aggregate-metric disposition mismatch")
    if promotion.get("undefined_venue_required_metric") != "venue_condition_unsatisfied":
        failures.append("undefined venue-metric disposition mismatch")
    if promotion.get("undefined_metrics_may_be_dropped_imputed_or_zero_filled") is not False:
        failures.append("undefined confirmatory metrics may not be manipulated")

    contract_path = repo_path(protocol.get("news_collection", {}).get("contract_path", ""))
    if not contract_path.is_file():
        failures.append("news collection contract is missing")
        contract: dict[str, Any] = {}
    else:
        contract = load_json(contract_path)
        if sha256_file(contract_path) != protocol["news_collection"].get("contract_sha256"):
            failures.append("news collection contract SHA-256 mismatch")
        try:
            validate_contract(contract)
        except ValueError as exc:
            failures.append(f"invalid news collection contract: {exc}")

    news = protocol.get("news_collection", {})
    if news.get("poll_seconds") != 60 or news.get("request_limit") != 200:
        failures.append("frozen news polling frequency or response cap mismatch")
    if news.get("max_success_gap_seconds") != 300:
        failures.append("maximum tolerated news gap mismatch")
    if news.get("cap_alarm_comparison") != "returned_rows >= 200":
        failures.append("200-row censoring alarm mismatch")
    if news.get("checkpoint_advances_on_cap_or_failure") is not False:
        failures.append("news checkpoint may not advance on cap/failure")
    if news.get("unrecoverable_interval_disposition") != "b1_incomplete_never_zero_news":
        failures.append("unrecoverable interval disposition mismatch")
    if news.get("holdout_policy_identical") is not True:
        failures.append("holdout must use the same news-censoring policy")
    if news.get("active_legacy_collector_compliant") is not False:
        failures.append("legacy collector must not be represented as v2.3-compliant")

    availability = protocol.get("news_availability", {})
    if availability.get("primary_feature_time") != "max(published_at, first_seen_at)":
        failures.append("primary point-in-time news availability mismatch")
    if availability.get("historical_backfill_may_backdate_primary_features") is not False:
        failures.append("historical news backfill may not backdate primary features")
    if availability.get("invalid_or_missing_published_at") != "exclude_from_b1_primary":
        failures.append("invalid publication-time disposition mismatch")
    if availability.get("published_at_only_role") != "separate_oracle_sensitivity_only_cannot_rescue_primary":
        failures.append("published-at-only sensitivity role mismatch")
    if availability_time(utc("2026-08-17T10:00:00Z"), utc("2026-08-17T10:17:00Z")) != utc(
        "2026-08-17T10:17:00Z"
    ):
        failures.append("availability helper permits retrospective backdating")
    if not is_cap_alarm(200, contract) or is_cap_alarm(199, contract):
        failures.append("collector cap-alarm helper violates the frozen 200-row rule")

    expected_order = [
        "close_and_reconcile_exact_development_sources",
        "pass_and_freeze_label_blind_data_sufficiency_gate",
        "run_label_blind_synthetic_14_market_cluster_power_simulation",
        "freeze_power_simulation_configuration_seed_and_output",
        "construct_price_grid_eligibility_and_labels",
        "run_frozen_b0_b1_development_comparison_once",
    ]
    if protocol.get("execution_order") != expected_order:
        failures.append("data-gate/power/label execution order mismatch")
    power = protocol.get("power_analysis", {})
    if power.get("execution_position") != "after_frozen_data_gate_before_any_label_construction":
        failures.append("power simulation position mismatch")
    if power.get("empirical_labels_prevalence_or_outcome_paths_permitted") is not False:
        failures.append("power simulation must remain label/outcome blind")
    if power.get("output_freeze_required") is not True:
        failures.append("power simulation output must freeze before labels")

    labels = protocol.get("labels", {})
    expected_paper_language = (
        "The threshold is a preregistered heuristic event definition inherited from "
        "the pilot protocol and should not be interpreted as a Gaussian "
        "four-standard-deviation event."
    )
    if labels.get("paper_language") != expected_paper_language:
        failures.append("required threshold paper language mismatch")
    if labels.get("threshold") != "4 * trailing_sigma_1m_240 * sqrt(horizon_min / 30)":
        failures.append("inherited label threshold changed")

    positioning = protocol.get("paper_positioning", {})
    if positioning.get("study_title") != (
        "A prospective protocol-validation study of incremental news information in "
        "prediction-market repricing"
    ):
        failures.append("October study positioning mismatch")
    if "does not create hundreds of thousands" not in positioning.get(
        "required_sample_size_disclosure", ""
    ):
        failures.append("14-market effective-sample disclosure missing")

    prior = protocol.get("prior_protocol", {})
    prior_path = repo_path(prior.get("path", ""))
    prior_manifest_path = repo_path(prior.get("manifest_path", ""))
    if prior.get("status") != "superseded_before_development_and_holdout_labels":
        failures.append("v2.2 supersession state is invalid")
    if not prior_path.is_file() or sha256_file(prior_path) != prior.get("sha256"):
        failures.append("v2.2 protocol lineage hash mismatch")
    if not prior_manifest_path.is_file() or sha256_file(prior_manifest_path) != prior.get(
        "manifest_sha256"
    ):
        failures.append("v2.2 manifest lineage hash mismatch")

    cohort = protocol.get("cohort", {})
    cohort_path = repo_path(cohort.get("selected_markets_path", ""))
    if not cohort_path.is_file() or sha256_file(cohort_path) != cohort.get(
        "selected_markets_sha256"
    ):
        failures.append("frozen cohort lineage hash mismatch")
    if cohort.get("frozen_market_count") != 14 or cohort.get("reselection_permitted") is not False:
        failures.append("frozen 14-market cohort contract mismatch")

    label_seal = manifest.get("label_seal", {})
    for key in (
        "development_labels_created",
        "development_labels_inspected",
        "holdout_labels_created",
        "holdout_labels_inspected",
    ):
        if label_seal.get(key) is not False:
            failures.append(f"{key} must be false")

    receipt = load_json(V1_RECEIPT)
    if receipt.get("status") != "consumed" or receipt.get("rerun_permitted") is not False:
        failures.append("v1 holdout state is not consumed/no-rerun")
    if receipt.get("dataset_id") != protocol.get("prior_v1_holdout", {}).get("dataset_id"):
        failures.append("v1 holdout dataset ID mismatch")

    audit_manifest_path = repo_path(
        manifest.get("prior_incomplete_news_audit", {}).get("path", "")
    )
    if not audit_manifest_path.is_file():
        failures.append("prior incomplete Lumid audit manifest missing")
    else:
        audit_manifest = load_json(audit_manifest_path)
        if sha256_file(audit_manifest_path) != manifest["prior_incomplete_news_audit"].get(
            "sha256"
        ):
            failures.append("prior incomplete Lumid audit manifest hash mismatch")
        if audit_manifest.get("status") != "incomplete_news_latest_truncation_risk":
            failures.append("prior news truncation result was not preserved as incomplete")
        if audit_manifest.get("label_seal", {}).get("labels_read") != []:
            failures.append("prior Lumid audit label seal is not clean")

    output = {
        "checked_artifacts": len(manifest.get("artifacts", {})),
        "confirmatory_hypotheses": {
            key: hypotheses.get(key) for key in ("h1", "h2", "h3", "h4", "h5")
        },
        "failures": failures,
        "labels_inspected": False,
        "news_contract": contract.get("contract_id"),
        "prior_news_audit_state": "incomplete_news_latest_truncation_risk",
        "prior_protocol": prior.get("protocol_id"),
        "protocol_id": protocol.get("protocol_id"),
        "status": "ok" if not failures else "failed",
        "v1_holdout_state": "consumed",
        "v2_3_holdout_state": "future_reserved_uninspected",
    }
    print(json.dumps(output, indent=2, sort_keys=True))
    if failures:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
