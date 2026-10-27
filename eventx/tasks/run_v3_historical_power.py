"""Run the frozen label-blind cluster-power sensitivity for EventX v3 history."""

from __future__ import annotations

from collections import Counter
from datetime import datetime, timezone
import hashlib
import json
import math
import os
from pathlib import Path
import random
from typing import Any, Iterator

from eventx.settings import REPO_ROOT


PROTOCOL_PATH = (
    REPO_ROOT / "eventx/release/v3_historical_primary/protocol.json"
)
COHORT_PATH = (
    REPO_ROOT / "data/v3_historical/primary/label_blind_inputs/cohort.jsonl"
)
OUTPUT = REPO_ROOT / "data/v3_historical/primary/power"
SCRIPT_PATH = REPO_ROOT / "eventx/tasks/run_v3_historical_power.py"
SEED = 20260902
SIMULATIONS = 10000
SCENARIOS = (
    {"name": "null", "delta_ap": 0.0, "brier_improvement": 0.0},
    {"name": "very_small", "delta_ap": 0.0005, "brier_improvement": 0.0001},
    {"name": "small", "delta_ap": 0.001, "brier_improvement": 0.00025},
    {"name": "moderate", "delta_ap": 0.0025, "brier_improvement": 0.0005},
    {"name": "clear", "delta_ap": 0.005, "brier_improvement": 0.001},
)


def sha256_file(path: Path) -> str:
    value = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            value.update(chunk)
    return value.hexdigest()


def atomic_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n")
    os.replace(temporary, path)


def read_jsonl(path: Path) -> Iterator[dict[str, Any]]:
    with path.open(encoding="utf-8") as handle:
        for line in handle:
            if line.strip():
                yield json.loads(line)


def market_group(venue: str, market_id: str) -> int:
    payload = f"{venue}:{market_id}".encode()
    return int(hashlib.sha256(payload).hexdigest(), 16) % 5


def weighted(values: dict[tuple[str, int], float], counts: Counter[Any]) -> float:
    total = sum(counts.values())
    return sum(values[key] * count for key, count in counts.items()) / total


def simulate_scenario(
    rng: random.Random,
    counts: Counter[tuple[str, int]],
    delta_ap: float,
    brier_improvement: float,
    ap_cluster_sd: float,
    brier_cluster_sd: float,
) -> dict[str, float]:
    passed = Counter()
    n_total = sum(counts.values())
    brier_standard_error = brier_cluster_sd / math.sqrt(n_total)
    for _ in range(SIMULATIONS):
        ap_cells: dict[tuple[str, int], float] = {}
        brier_cells: dict[tuple[str, int], float] = {}
        for key, count in counts.items():
            shared = rng.gauss(0.0, 1.0)
            independent = rng.gauss(0.0, 1.0)
            ap_cells[key] = delta_ap + ap_cluster_sd / math.sqrt(count) * shared
            brier_cells[key] = brier_improvement + brier_cluster_sd / math.sqrt(
                count
            ) * (0.5 * shared + math.sqrt(0.75) * independent)
        overall_ap = weighted(ap_cells, counts)
        overall_brier = weighted(brier_cells, counts)
        fold_passes = 0
        for group in range(5):
            fold_counts = Counter(
                {key: count for key, count in counts.items() if key[1] == group}
            )
            if weighted(ap_cells, fold_counts) > 0 and weighted(
                brier_cells, fold_counts
            ) > 0:
                fold_passes += 1
        venue_brier = {}
        for venue in ("kalshi", "polymarket"):
            venue_counts = Counter(
                {key: count for key, count in counts.items() if key[0] == venue}
            )
            venue_brier[venue] = weighted(brier_cells, venue_counts)
        h1 = overall_ap > 0
        h2 = overall_brier > 0
        h3 = fold_passes >= 4
        h4 = overall_brier - 1.959963984540054 * brier_standard_error > 0
        h5 = all(value >= 0 for value in venue_brier.values())
        for name, value in (("h1", h1), ("h2", h2), ("h3", h3), ("h4", h4), ("h5", h5)):
            passed[name] += int(value)
        passed["all_h1_h5"] += int(h1 and h2 and h3 and h4 and h5)
    return {name: value / SIMULATIONS for name, value in sorted(passed.items())}


def main() -> None:
    protocol = json.loads(PROTOCOL_PATH.read_text(encoding="utf-8"))
    if protocol.get("status") != "preregistered_before_prices_labels_or_outcomes":
        raise SystemExit("historical protocol is not in its pre-label state")
    if sha256_file(COHORT_PATH) != protocol["cohort"]["sha256"]:
        raise SystemExit("historical cohort hash mismatch")
    prohibited = (
        REPO_ROOT / "data/v3_historical/primary/development/labels.jsonl",
        REPO_ROOT / "data/v3_historical/primary/development/results.json",
        REPO_ROOT / "data/v3_historical/primary/holdout/results.json",
    )
    if any(path.exists() for path in prohibited):
        raise SystemExit("outcome-bearing artifacts already exist; power seal failed")

    counts: Counter[tuple[str, int]] = Counter()
    for row in read_jsonl(COHORT_PATH):
        venue = str(row["venue"])
        counts[(venue, market_group(venue, str(row["market_id"])))] += 1
    if sum(counts.values()) != int(protocol["cohort"]["markets"]):
        raise SystemExit("cohort count changed")

    config = {
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
    manifest = {
        "protocol_id": protocol["protocol_id"],
        "manifest_id": "eventx-v3-historical-power-20260902",
        "labels_or_outcomes_read": False,
        "artifacts": [
            {"path": str(PROTOCOL_PATH.relative_to(REPO_ROOT)), "sha256": sha256_file(PROTOCOL_PATH)},
            {"path": str(COHORT_PATH.relative_to(REPO_ROOT)), "sha256": sha256_file(COHORT_PATH)},
            {"path": str(SCRIPT_PATH.relative_to(REPO_ROOT)), "sha256": sha256_file(SCRIPT_PATH)},
            {"path": str(config_path.relative_to(REPO_ROOT)), "sha256": sha256_file(config_path)},
            {"path": str(report_path.relative_to(REPO_ROOT)), "sha256": sha256_file(report_path)},
        ],
    }
    atomic_json(manifest_path, manifest)
    print(json.dumps(report, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
