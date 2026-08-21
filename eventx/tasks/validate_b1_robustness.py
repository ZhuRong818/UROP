"""Validation-only robustness checks for the incremental KOL feature model."""

from __future__ import annotations

import argparse
import json
import math
import random
from collections import defaultdict
from pathlib import Path
from typing import Any

from eventx.features.build_kol_features import hash_file
from eventx.settings import REPO_ROOT
from eventx.tasks.run_b1 import (
    KOL_FEATURES,
    MARKET_FEATURES,
    Example,
    load_train_validation,
    metrics,
    model_result,
    sigmoid,
    standardized,
)


def percentile(values: list[float], probability: float) -> float:
    ordered = sorted(values)
    if not ordered:
        raise ValueError("Cannot calculate a percentile from an empty list.")
    position = probability * (len(ordered) - 1)
    lower = math.floor(position)
    upper = math.ceil(position)
    if lower == upper:
        return ordered[lower]
    fraction = position - lower
    return ordered[lower] * (1 - fraction) + ordered[upper] * fraction


def distribution_summary(values: list[float]) -> dict[str, float | int]:
    return {
        "samples": len(values),
        "mean": sum(values) / len(values),
        "median": percentile(values, 0.5),
        "ci_95_lower": percentile(values, 0.025),
        "ci_95_upper": percentile(values, 0.975),
        "probability_positive": sum(value > 0 for value in values) / len(values),
    }


def grouped_indices(examples: list[Example]) -> dict[str, list[int]]:
    groups: dict[str, list[int]] = defaultdict(list)
    for index, example in enumerate(examples):
        groups[example.market_id].append(index)
    for indices in groups.values():
        indices.sort(key=lambda index: examples[index].ts)
    return dict(sorted(groups.items()))


def circular_block_sample(
    groups: dict[str, list[int]],
    block_rows: int,
    rng: random.Random,
) -> list[int]:
    sampled: list[int] = []
    for indices in groups.values():
        size = len(indices)
        selected: list[int] = []
        while len(selected) < size:
            start = rng.randrange(size)
            selected.extend(indices[(start + offset) % size] for offset in range(block_rows))
        sampled.extend(selected[:size])
    return sampled


def paired_metrics(
    labels: list[int],
    b0_scores: list[float],
    b1_scores: list[float],
    indices: list[int],
) -> tuple[float | None, float]:
    selected_labels = [labels[index] for index in indices]
    selected_b0 = [b0_scores[index] for index in indices]
    selected_b1 = [b1_scores[index] for index in indices]
    b0 = metrics(selected_labels, selected_b0)
    b1 = metrics(selected_labels, selected_b1)
    b0_ap = b0["average_precision"]
    b1_ap = b1["average_precision"]
    delta_ap = (
        float(b1_ap) - float(b0_ap)
        if b0_ap is not None and b1_ap is not None
        else None
    )
    brier_improvement = float(b0["brier"]) - float(b1["brier"])
    return delta_ap, brier_improvement


def block_bootstrap(
    labels: list[int],
    b0_scores: list[float],
    b1_scores: list[float],
    groups: dict[str, list[int]],
    block_rows: int,
    cadence_min: int,
    samples: int,
    seed: int,
) -> dict[str, Any]:
    rng = random.Random(seed)
    delta_ap: list[float] = []
    brier_improvement: list[float] = []
    invalid_ap_samples = 0
    for _ in range(samples):
        indices = circular_block_sample(groups, block_rows, rng)
        sample_delta_ap, sample_brier = paired_metrics(
            labels,
            b0_scores,
            b1_scores,
            indices,
        )
        if sample_delta_ap is None:
            invalid_ap_samples += 1
        else:
            delta_ap.append(sample_delta_ap)
        brier_improvement.append(sample_brier)
    return {
        "method": "paired circular moving-block bootstrap, stratified by market",
        "block_rows": block_rows,
        "block_minutes": block_rows * cadence_min,
        "requested_samples": samples,
        "invalid_average_precision_samples": invalid_ap_samples,
        "seed": seed,
        "delta_average_precision": distribution_summary(delta_ap),
        "brier_improvement": distribution_summary(brier_improvement),
    }


def shifted_contributions(
    contributions: list[float],
    groups: dict[str, list[int]],
    block_rows: int,
    rng: random.Random,
) -> list[float]:
    shifted = contributions.copy()
    for indices in groups.values():
        size = len(indices)
        if size <= 1:
            continue
        block_shifts = list(range(block_rows, size, block_rows))
        shift = rng.choice(block_shifts) if block_shifts else rng.randrange(1, size)
        for position, target_index in enumerate(indices):
            source_index = indices[(position + shift) % size]
            shifted[target_index] = contributions[source_index]
    return shifted


def time_shift_permutation(
    labels: list[int],
    b0_scores: list[float],
    base_logits: list[float],
    kol_contributions: list[float],
    groups: dict[str, list[int]],
    observed_delta_ap: float,
    observed_brier_improvement: float,
    block_rows: int,
    cadence_min: int,
    samples: int,
    seed: int,
) -> dict[str, Any]:
    rng = random.Random(seed)
    null_delta_ap: list[float] = []
    null_brier_improvement: list[float] = []
    all_indices = list(range(len(labels)))
    for _ in range(samples):
        permuted = shifted_contributions(kol_contributions, groups, block_rows, rng)
        scores = [
            sigmoid(base_logit + contribution)
            for base_logit, contribution in zip(base_logits, permuted)
        ]
        delta_ap, brier = paired_metrics(labels, b0_scores, scores, all_indices)
        if delta_ap is not None:
            null_delta_ap.append(delta_ap)
        null_brier_improvement.append(brier)
    ap_exceedances = sum(value >= observed_delta_ap for value in null_delta_ap)
    brier_exceedances = sum(
        value >= observed_brier_improvement for value in null_brier_improvement
    )
    return {
        "method": (
            "within-market circular time shifts of the fitted KOL logit contribution; "
            "market-feature logit and KOL autocorrelation are preserved"
        ),
        "block_rows": block_rows,
        "block_minutes": block_rows * cadence_min,
        "samples": samples,
        "seed": seed,
        "delta_average_precision": {
            "observed": observed_delta_ap,
            "null": distribution_summary(null_delta_ap),
            "one_sided_p_value": (ap_exceedances + 1) / (len(null_delta_ap) + 1),
        },
        "brier_improvement": {
            "observed": observed_brier_improvement,
            "null": distribution_summary(null_brier_improvement),
            "one_sided_p_value": (brier_exceedances + 1)
            / (len(null_brier_improvement) + 1),
        },
    }


def leave_one_market_out(
    examples: list[Example],
    labels: list[int],
    b0_scores: list[float],
    b1_scores: list[float],
    groups: dict[str, list[int]],
) -> dict[str, Any]:
    all_indices = set(range(len(examples)))
    rows = []
    for market_id, market_indices in groups.items():
        retained = sorted(all_indices.difference(market_indices))
        delta_ap, brier = paired_metrics(labels, b0_scores, b1_scores, retained)
        rows.append(
            {
                "excluded_market_id": market_id,
                "excluded_rows": len(market_indices),
                "excluded_positives": sum(labels[index] for index in market_indices),
                "retained_rows": len(retained),
                "delta_average_precision": delta_ap,
                "brier_improvement": brier,
            }
        )
    ap_values = [
        float(row["delta_average_precision"])
        for row in rows
        if row["delta_average_precision"] is not None
    ]
    brier_values = [float(row["brier_improvement"]) for row in rows]
    return {
        "method": "fixed-model delete-one-market validation sensitivity",
        "markets": len(rows),
        "all_delta_average_precision_positive": all(value > 0 for value in ap_values),
        "all_brier_improvements_positive": all(value > 0 for value in brier_values),
        "delta_average_precision_range": {
            "min": min(ap_values),
            "max": max(ap_values),
        },
        "brier_improvement_range": {
            "min": min(brier_values),
            "max": max(brier_values),
        },
        "exclusions": rows,
    }


def b1_logit_components(
    examples: list[Example],
    model: dict[str, Any],
) -> tuple[list[float], list[float]]:
    feature_names = MARKET_FEATURES + KOL_FEATURES
    vectors = [example.market + example.kol for example in examples]
    means = [float(model["standardization"][name]["mean"]) for name in feature_names]
    scales = [float(model["standardization"][name]["scale"]) for name in feature_names]
    weights = [float(model["coefficients"][name]) for name in feature_names]
    transformed = standardized(vectors, means, scales)
    split_at = len(MARKET_FEATURES)
    base_logits = []
    kol_contributions = []
    for vector in transformed:
        base_logits.append(
            float(model["intercept"])
            + sum(
                weight * value
                for weight, value in zip(weights[:split_at], vector[:split_at])
            )
        )
        kol_contributions.append(
            sum(
                weight * value
                for weight, value in zip(weights[split_at:], vector[split_at:])
            )
        )
    return base_logits, kol_contributions


def main() -> None:
    parser = argparse.ArgumentParser(description="Validate EventX B1 robustness")
    parser.add_argument("--labels", type=Path)
    parser.add_argument("--features", type=Path)
    parser.add_argument("--feature-report", type=Path)
    parser.add_argument("--b1-result", type=Path)
    parser.add_argument("--out", type=Path)
    parser.add_argument("--bootstrap-samples", type=int, default=2000)
    parser.add_argument("--permutation-samples", type=int, default=2000)
    parser.add_argument("--block-minutes", type=int, default=360)
    parser.add_argument("--block-rows", type=int)
    args = parser.parse_args()
    if (
        args.bootstrap_samples <= 0
        or args.permutation_samples <= 0
        or args.block_minutes <= 0
        or (args.block_rows is not None and args.block_rows <= 0)
    ):
        raise SystemExit("Sample counts and block duration must be positive.")

    root = REPO_ROOT / "data" / "v1" / "toy"
    labels_path = args.labels or root / "labels_30m.jsonl"
    features_path = args.features or root / "kol_features_30m.jsonl"
    feature_report_path = args.feature_report or root / "kol_features_30m_report.json"
    b1_result_path = args.b1_result or root / "b1_validation_results.json"
    out_path = args.out or root / "b1_robustness_results.json"
    feature_report = json.loads(feature_report_path.read_text())
    prior_result = json.loads(b1_result_path.read_text())
    if prior_result.get("status") != "validation_complete_test_untouched":
        raise SystemExit("B1 validation result is not in the expected test-untouched state.")
    if hash_file(features_path)["sha256"] != feature_report["artifact"]["sha256"]:
        raise SystemExit("KOL feature artifact hash does not match its report.")

    cadence_min = int(feature_report["cadence_min"])
    block_rows = args.block_rows or math.ceil(args.block_minutes / cadence_min)
    datasets, load_stats = load_train_validation(
        labels_path,
        features_path,
        cadence_min,
    )
    train = datasets["train"]
    validation = datasets["validation"]
    train_labels = [example.label for example in train]
    validation_labels = [example.label for example in validation]
    b0, b0_scores = model_result(
        [example.market for example in train],
        train_labels,
        [example.market for example in validation],
        validation_labels,
        MARKET_FEATURES,
        epochs=8,
    )
    b1, b1_scores = model_result(
        [example.market + example.kol for example in train],
        train_labels,
        [example.market + example.kol for example in validation],
        validation_labels,
        MARKET_FEATURES + KOL_FEATURES,
        epochs=8,
    )
    all_indices = list(range(len(validation)))
    observed_delta_ap, observed_brier = paired_metrics(
        validation_labels,
        b0_scores,
        b1_scores,
        all_indices,
    )
    if observed_delta_ap is None:
        raise SystemExit("Validation has no positive examples for average precision.")
    expected = prior_result["validation"]["incremental_b1_over_b0"]
    if (
        abs(observed_delta_ap - float(expected["delta_average_precision"])) > 1.0e-12
        or abs(observed_brier - float(expected["brier_improvement"])) > 1.0e-12
    ):
        raise SystemExit("Reproduced model metrics do not match the locked validation result.")

    groups = grouped_indices(validation)
    bootstrap = block_bootstrap(
        validation_labels,
        b0_scores,
        b1_scores,
        groups,
        block_rows=block_rows,
        cadence_min=cadence_min,
        samples=args.bootstrap_samples,
        seed=23,
    )
    base_logits, kol_contributions = b1_logit_components(validation, b1)
    permutation = time_shift_permutation(
        validation_labels,
        b0_scores,
        base_logits,
        kol_contributions,
        groups,
        observed_delta_ap,
        observed_brier,
        block_rows=block_rows,
        cadence_min=cadence_min,
        samples=args.permutation_samples,
        seed=29,
    )
    lomo = leave_one_market_out(
        validation,
        validation_labels,
        b0_scores,
        b1_scores,
        groups,
    )
    brier_bootstrap_pass = (
        float(bootstrap["brier_improvement"]["ci_95_lower"]) > 0
    )
    brier_permutation_pass = (
        float(permutation["brier_improvement"]["one_sided_p_value"]) <= 0.05
    )
    brier_lomo_pass = bool(lomo["all_brier_improvements_positive"])
    ready = brier_bootstrap_pass and brier_permutation_pass and brier_lomo_pass
    result = {
        "status": "ready_to_freeze" if ready else "more_validation_needed",
        "dataset_id": feature_report["dataset_id"],
        "kol_rule_id": feature_report["kol_rule_id"],
        "primary_metric": "brier_improvement",
        "observed": {
            "delta_average_precision": observed_delta_ap,
            "brier_improvement": observed_brier,
            "validation_rows": len(validation),
            "validation_positives": sum(validation_labels),
            "validation_markets": len(groups),
        },
        "paired_block_bootstrap": bootstrap,
        "time_shift_permutation": permutation,
        "leave_one_market_out": lomo,
        "freeze_gate": {
            "bootstrap_brier_ci_lower_above_zero": brier_bootstrap_pass,
            "permutation_brier_p_at_most_0_05": brier_permutation_pass,
            "brier_positive_after_every_market_exclusion": brier_lomo_pass,
            "passed": ready,
        },
        "model_reproduction": {
            "matched_prior_result": True,
            "b0_validation": b0["validation"],
            "b1_validation": b1["validation"],
        },
        "load_validation": load_stats,
        "test_policy": (
            "All checks use train and validation examples only. Test feature rows are "
            "alignment-checked and skipped before y_jump access; no test metric is computed."
        ),
        "inputs": {
            "labels": str(labels_path.resolve().relative_to(REPO_ROOT)),
            "features": str(features_path.resolve().relative_to(REPO_ROOT)),
            "feature_report": str(feature_report_path.resolve().relative_to(REPO_ROOT)),
            "b1_validation_result": str(b1_result_path.resolve().relative_to(REPO_ROOT)),
        },
    }
    out_path.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
    summary = {
        "status": result["status"],
        "observed": result["observed"],
        "freeze_gate": result["freeze_gate"],
        "bootstrap": {
            "delta_average_precision": bootstrap["delta_average_precision"],
            "brier_improvement": bootstrap["brier_improvement"],
        },
        "permutation": {
            "delta_average_precision": permutation["delta_average_precision"],
            "brier_improvement": permutation["brier_improvement"],
        },
        "leave_one_market_out": {
            key: value for key, value in lomo.items() if key != "exclusions"
        },
        "output": str(out_path),
    }
    print(json.dumps(summary, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
