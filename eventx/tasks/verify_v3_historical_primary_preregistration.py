"""Verify the hash-locked EventX v3 historical primary preregistration."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

from eventx.settings import REPO_ROOT


MANIFEST = (
    REPO_ROOT
    / "eventx/release/v3_historical_primary/preregistration_manifest.json"
)
CONSUMED_V1 = (
    REPO_ROOT
    / "data/v1_oot_20260723_20260730/holdout_consumption_receipt.json"
)
PROHIBITED_PRE_SELECTION = (
    REPO_ROOT / "data/v3_historical/primary/development/labels.jsonl",
    REPO_ROOT / "data/v3_historical/primary/development/results.json",
    REPO_ROOT / "data/v3_historical/primary/holdout/consumption_receipt.json",
    REPO_ROOT / "data/v3_historical/primary/holdout/results.json",
)


def digest(path: Path) -> str:
    value = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            value.update(chunk)
    return value.hexdigest()


def load(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def main() -> None:
    failures: list[str] = []
    manifest = load(MANIFEST)
    if manifest.get("protocol_id") != "eventx-v3-historical-primary-20260902":
        failures.append("manifest protocol id changed")
    if manifest.get("labels_or_outcomes_inspected") is not False:
        failures.append("manifest does not preserve the pre-label seal")
    for artifact in manifest.get("artifacts", []):
        path = REPO_ROOT / str(artifact["path"])
        if not path.is_file():
            failures.append(f"missing artifact: {artifact['path']}")
        elif digest(path) != artifact["sha256"]:
            failures.append(f"hash mismatch: {artifact['path']}")

    protocol_path = REPO_ROOT / "eventx/release/v3_historical_primary/protocol.json"
    protocol = load(protocol_path)
    if protocol.get("status") != "preregistered_before_prices_labels_or_outcomes":
        failures.append("protocol no longer has its pre-label status")
    if protocol.get("cohort", {}).get("markets") != 4670:
        failures.append("frozen cohort size changed")
    if protocol.get("cohort", {}).get("reselection_after_labels") is not False:
        failures.append("cohort reselection is not prohibited")
    if protocol.get("one_shot_holdout", {}).get("reruns_permitted") is not False:
        failures.append("historical holdout reruns are not prohibited")
    if len(protocol.get("development_validation", {}).get("folds", [])) != 5:
        failures.append("five development folds are not frozen")
    if set(protocol.get("promotion_gate", {})) != {
        "all_required",
        "fallback",
        "h1",
        "h2",
        "h3",
        "h4",
        "h5",
        "undefined_required_metric",
    }:
        failures.append("promotion gate fields changed")

    input_report = load(
        REPO_ROOT / "data/v3_historical/primary/label_blind_inputs/report.json"
    )
    provenance = load(
        REPO_ROOT / "data/v3_historical/provenance_audit_v2/report.json"
    )
    if input_report.get("integrity_pass") is not True:
        failures.append("label-blind input gate did not pass")
    if input_report.get("holdout_covariates_used_for_selection") is not False:
        failures.append("holdout covariates affected cohort selection")
    if provenance.get("integrity_pass") is not True:
        failures.append("news provenance gate did not pass")

    consumed = load(CONSUMED_V1)
    if consumed.get("status") != "consumed":
        failures.append("prior v1 holdout receipt is missing its consumed status")
    for path in PROHIBITED_PRE_SELECTION:
        if path.exists():
            failures.append(f"unexpected pre-selection artifact exists: {path}")

    report = {
        "protocol_id": protocol.get("protocol_id"),
        "artifacts_checked": len(manifest.get("artifacts", [])),
        "failures": failures,
        "passed": not failures,
        "labels_or_outcomes_read": False,
        "prior_consumed_holdout_verified": True,
    }
    print(json.dumps(report, indent=2, sort_keys=True))
    if failures:
        raise SystemExit("historical primary preregistration verification failed")


if __name__ == "__main__":
    main()
