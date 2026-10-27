"""Run the frozen label-blind cluster-power sensitivity for EventX v3.1."""

from __future__ import annotations

from collections import Counter
from datetime import datetime, timezone
import json
from pathlib import Path
import random
from typing import Any

from eventx.settings import REPO_ROOT
from eventx.tasks.run_v3_historical_power import (
    SCENARIOS,
    SEED,
    SIMULATIONS,
    atomic_json,
    market_group,
    read_jsonl,
    sha256_file,
    simulate_scenario,
)


PROTOCOL_PATH = REPO_ROOT / "eventx/release/v3_1_historical_primary/protocol.json"
PREREG_MANIFEST = (
    REPO_ROOT / "eventx/release/v3_1_historical_primary/preregistration_manifest.json"
)
COHORT_PATH = REPO_ROOT / "data/v3_1_historical/primary/label_blind_inputs/cohort.jsonl"
OUTPUT = REPO_ROOT / "data/v3_1_historical/primary/power"
SCRIPT_PATH = Path(__file__).resolve()


def verify_manifest(path: Path) -> None:
    manifest = json.loads(path.read_text(encoding="utf-8"))
    for artifact in manifest.get("artifacts", []):
        artifact_path = REPO_ROOT / str(artifact["path"])
        if not artifact_path.is_file() or sha256_file(artifact_path) != str(
            artifact["sha256"]
        ):
            raise RuntimeError(f"hash-lock failure: {artifact_path}")


def main() -> None:
    verify_manifest(PREREG_MANIFEST)
    protocol = json.loads(PROTOCOL_PATH.read_text(encoding="utf-8"))
    if protocol.get("status") != (
        "re_preregistered_after_label_blind_trade_gate_before_labels_or_outcomes"
    ):
        raise SystemExit("v3.1 protocol is not in its pre-outcome state")
    if sha256_file(COHORT_PATH) != str(protocol["cohort"]["sha256"]):
        raise SystemExit("v3.1 cohort hash mismatch")
    prohibited = (
        REPO_ROOT / "data/v3_1_historical/primary/development/labels.jsonl",
        REPO_ROOT / "data/v3_1_historical/primary/development/results.json",
        REPO_ROOT / "data/v3_1_historical/primary/holdout",
    )
    if any(path.exists() for path in prohibited):
        raise SystemExit("outcome-bearing artifact exists; power seal failed")

    counts: Counter[tuple[str, int]] = Counter()
    for row in read_jsonl(COHORT_PATH):
        venue = str(row["venue"])
        counts[(venue, market_group(venue, str(row["market_id"])))] += 1
    if sum(counts.values()) != int(protocol["cohort"]["markets"]):
        raise SystemExit("cohort count changed")

    config: dict[str, Any] = {
        "protocol_id": protocol["protocol_id"],
        "label_blind": True,
        "empirical_labels_or_prevalence_used": False,
        "simulations": SIMULATIONS,
        "seed": SEED,
        "cluster_unit": "market",
        "market_counts_by_venue_and_group": {
            f"{venue}:{group}": count
            for (venue, group), count in sorted(counts.items())
        },
        "assumptions": {
            "ap_market_cluster_sd": 0.02,
            "brier_improvement_market_cluster_sd": 0.01,
            "ap_brier_cell_correlation": 0.5,
            "h4_approximation": "normal lower bound over independent market clusters",
            "temporal_rows_do_not_increase_cluster_count": True,
            "interpretation": "design sensitivity, not an empirical power estimate",
        },
        "scenarios": list(SCENARIOS),
        "protocol_may_change_from_output": False,
    }
    OUTPUT.mkdir(parents=True, exist_ok=True)
    config_path = OUTPUT / "config.json"
    report_path = OUTPUT / "report.json"
    manifest_path = OUTPUT / "manifest.json"
    atomic_json(config_path, config)

    rng = random.Random(SEED)
    results = []
    for scenario in SCENARIOS:
        results.append(
            {
                **scenario,
                "promotion_probability": simulate_scenario(
                    rng,
                    counts,
                    float(scenario["delta_ap"]),
                    float(scenario["brier_improvement"]),
                    0.02,
                    0.01,
                ),
            }
        )
    report = {
        "protocol_id": protocol["protocol_id"],
        "completed_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "status": "completed_and_frozen_before_labels",
        "label_blind": True,
        "labels_or_outcomes_read": False,
        "market_clusters": sum(counts.values()),
        "results": results,
        "decision_effect": "none; the preregistered protocol cannot change from this sensitivity",
    }
    atomic_json(report_path, report)
    atomic_json(
        manifest_path,
        {
            "protocol_id": protocol["protocol_id"],
            "manifest_id": "eventx-v3.1-historical-power-20260902",
            "labels_or_outcomes_read": False,
            "artifacts": [
                {
                    "path": str(path.relative_to(REPO_ROOT)),
                    "sha256": sha256_file(path),
                }
                for path in (
                    PROTOCOL_PATH,
                    PREREG_MANIFEST,
                    COHORT_PATH,
                    SCRIPT_PATH,
                    config_path,
                    report_path,
                )
            ],
        },
    )
    print(json.dumps(report, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
