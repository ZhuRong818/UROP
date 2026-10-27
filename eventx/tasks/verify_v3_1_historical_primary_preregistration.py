"""Verify the hash-locked EventX v3.1 historical preregistration."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

from eventx.settings import REPO_ROOT


MANIFEST = (
    REPO_ROOT / "eventx/release/v3_1_historical_primary/preregistration_manifest.json"
)
CONSUMED_V1 = (
    REPO_ROOT / "data/v1_oot_20260723_20260730/holdout_consumption_receipt.json"
)
PROHIBITED = (
    REPO_ROOT / "data/v3_1_historical/primary/development/labels.jsonl",
    REPO_ROOT / "data/v3_1_historical/primary/development/results.json",
    REPO_ROOT / "data/v3_1_historical/primary/holdout",
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
    protocol_id = "eventx-v3.1-historical-primary-20260902"
    if manifest.get("protocol_id") != protocol_id:
        failures.append("manifest protocol id changed")
    for flag in (
        "labels_or_outcomes_inspected",
        "historical_holdout_covariates_used",
        "trade_price_values_used_for_revision",
    ):
        if manifest.get(flag) is not False:
            failures.append(f"pre-outcome seal not preserved: {flag}")
    for artifact in manifest.get("artifacts", []):
        path = REPO_ROOT / str(artifact["path"])
        if not path.is_file():
            failures.append(f"missing artifact: {artifact['path']}")
        elif digest(path) != str(artifact["sha256"]):
            failures.append(f"hash mismatch: {artifact['path']}")

    protocol = load(
        REPO_ROOT / "eventx/release/v3_1_historical_primary/protocol.json"
    )
    if protocol.get("protocol_id") != protocol_id:
        failures.append("protocol id changed")
    if protocol.get("status") != (
        "re_preregistered_after_label_blind_trade_gate_before_labels_or_outcomes"
    ):
        failures.append("protocol does not retain its pre-outcome revision status")
    if protocol.get("cohort", {}).get("markets") != 4651:
        failures.append("corrected cohort size changed")
    if protocol.get("cohort", {}).get("by_venue") != {
        "kalshi": 3832,
        "polymarket": 819,
    }:
        failures.append("corrected venue counts changed")
    if protocol.get("revision", {}).get("change") != (
        "remove exactly 19 markets failing the original activity minimum after positive-notional normalization"
    ):
        failures.append("bounded revision changed")
    if protocol.get("integrity", {}).get("trade_price_values_used_for_revision") is not False:
        failures.append("price values affected revision")
    if protocol.get("integrity", {}).get("historical_holdout_covariates_used_for_selection") is not False:
        failures.append("historical holdout affected revision")
    if len(protocol.get("development_validation", {}).get("folds", [])) != 5:
        failures.append("five validation folds are not frozen")
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
        failures.append("promotion gate changed")

    input_report = load(
        REPO_ROOT / "data/v3_1_historical/primary/label_blind_inputs/report.json"
    )
    if input_report.get("integrity_pass") is not True:
        failures.append("corrected label-blind input gate failed")
    if input_report.get("revision", {}).get("removed_markets") != 19:
        failures.append("incorrect number of activity-invalid removals")
    consumed = load(CONSUMED_V1)
    if consumed.get("status") != "consumed":
        failures.append("prior v1 holdout receipt is not consumed")
    for path in PROHIBITED:
        if path.exists():
            failures.append(f"unexpected outcome-bearing artifact exists: {path}")

    report = {
        "protocol_id": protocol_id,
        "artifacts_checked": len(manifest.get("artifacts", [])),
        "failures": failures,
        "passed": not failures,
        "labels_or_outcomes_read": False,
        "historical_holdout_read": False,
        "prior_consumed_holdout_verified": True,
    }
    print(json.dumps(report, indent=2, sort_keys=True))
    if failures:
        raise SystemExit("v3.1 preregistration verification failed")


if __name__ == "__main__":
    main()
