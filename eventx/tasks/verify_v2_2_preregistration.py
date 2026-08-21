"""Verify the EventX v2.2 Option-A October pilot preregistration and lineage."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from eventx.settings import REPO_ROOT
from eventx.tasks.verify_v2_preregistration import (
    V1_RECEIPT,
    load_json,
    repo_path,
    sha256_file,
)


DEFAULT_MANIFEST = (
    REPO_ROOT / "eventx" / "release" / "v2_2" / "preregistration_manifest.json"
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
    if windows.get("development", {}).get("end_exclusive") != "2026-09-28T00:00:00Z":
        failures.append("Option-A development cutoff mismatch")
    if windows.get("reconciliation_freeze") != {
        "start": "2026-09-28T00:00:00Z",
        "end_exclusive": "2026-10-01T00:00:00Z",
    }:
        failures.append("72-hour reconciliation/freeze window mismatch")
    if windows.get("holdout") != {
        "start": "2026-10-01T00:00:00Z",
        "end_exclusive": "2026-10-22T00:00:00Z",
    }:
        failures.append("October holdout window mismatch")
    if protocol.get("deadline", {}).get("candidate_freeze_no_later_than") != "2026-10-01T00:00:00Z":
        failures.append("candidate freeze deadline mismatch")
    if protocol.get("deadline", {}).get("completion_at") != "2026-10-31T23:59:59Z":
        failures.append("October completion deadline mismatch")

    comparison = protocol.get("confirmatory_comparison", {})
    if comparison.get("candidate") != "b1_market_core_news":
        failures.append("B1 is not the confirmatory candidate")
    if comparison.get("reference") != "b0_market_only":
        failures.append("B0 is not the confirmatory reference")
    if comparison.get("tests_kol_incremental_information") is not False:
        failures.append("v2.2 must not claim to test KOL incremental information")

    price = protocol.get("price", {})
    if price.get("primary") != "latest_canonical_yes_trade_at_or_before_t_carried_forward":
        failures.append("uniform last-trade primary price mismatch")
    if price.get("primary_source_switching_permitted") is not False:
        failures.append("primary price-source switching must be prohibited")
    if price.get("record_price_age_minutes") is not True:
        failures.append("price age must be recorded")

    labels = protocol.get("labels", {})
    if labels.get("threshold") != "4 * trailing_sigma_1m_240 * sqrt(horizon_min / 30)":
        failures.append("label threshold formula mismatch")
    if labels.get("threshold_is_four_horizon_sigmas") is not False:
        failures.append("threshold semantics must reject four-horizon-sigma interpretation")
    if labels.get("threshold_anchor_scale_in_one_minute_sigma_units") != 4.0:
        failures.append("threshold anchor scale mismatch")

    if protocol.get("eligibility", {}).get("price_age_robustness_minutes") != [30, 60]:
        failures.append("price freshness robustness thresholds mismatch")
    if protocol.get("economic_significance", {}).get("directional_pnl_permitted") is not False:
        failures.append("directional P&L must be disabled for the absolute-jump target")
    if protocol.get("t5", {}).get("runs_in_v2_2") is not False:
        failures.append("T5 must be disabled after the KOL gate failure")

    prior = protocol.get("prior_protocol", {})
    prior_path = repo_path(prior.get("path", ""))
    prior_manifest_path = repo_path(prior.get("manifest_path", ""))
    if prior.get("status") != "superseded_before_development_and_holdout_labels":
        failures.append("prior protocol supersession state is invalid")
    if not prior_path.is_file() or sha256_file(prior_path) != prior.get("sha256"):
        failures.append("v2.1 protocol lineage hash mismatch")
    if (
        not prior_manifest_path.is_file()
        or sha256_file(prior_manifest_path) != prior.get("manifest_sha256")
    ):
        failures.append("v2.1 manifest lineage hash mismatch")

    cohort = protocol.get("cohort", {})
    cohort_path = repo_path(cohort.get("selected_markets_path", ""))
    if not cohort_path.is_file() or sha256_file(cohort_path) != cohort.get("selected_markets_sha256"):
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

    output = {
        "checked_artifacts": len(manifest.get("artifacts", {})),
        "candidate_freeze_deadline": protocol.get("deadline", {}).get(
            "candidate_freeze_no_later_than"
        ),
        "confirmatory_comparison": comparison,
        "failures": failures,
        "labels_inspected": False,
        "prior_protocol": prior.get("protocol_id"),
        "protocol_id": protocol.get("protocol_id"),
        "status": "ok" if not failures else "failed",
        "v1_holdout_state": "consumed",
        "v2_2_holdout_state": "future_reserved_uninspected",
    }
    print(json.dumps(output, indent=2, sort_keys=True))
    if failures:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
