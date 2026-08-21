"""Nested walk-forward evaluation of recent-activity-gated EventX KOL features."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

from eventx.features.build_kol_features import hash_file, parse_ts
from eventx.settings import REPO_ROOT
from eventx.tasks.run_b1 import (
    KOL_FEATURES,
    MARKET_FEATURES,
    Example,
    metrics,
    model_result,
)
from eventx.tasks.run_b1_walk_forward import (
    fold_boundaries,
    load_pretest_examples,
    sign_test_p_value,
    summary,
)
from eventx.tasks.validate_b1_robustness import block_bootstrap

GATE_WINDOWS_MIN = (120, 360, 1440)
GATE_FEATURE_INDEX = {
    120: KOL_FEATURES.index("kol_tweet_count_120m"),
    360: KOL_FEATURES.index("kol_tweet_count_360m"),
    1440: KOL_FEATURES.index("kol_tweet_count_1440m"),
}


def is_active(example: Example, gate_min: int) -> bool:
    if gate_min == 0:
        return False
    return example.kol[GATE_FEATURE_INDEX[gate_min]] > 0


def paired_result(
    labels: list[int],
    b0_scores: list[float],
    candidate_scores: list[float],
) -> dict[str, Any]:
    b0 = metrics(labels, b0_scores)
    candidate = metrics(labels, candidate_scores)
    b0_ap = b0["average_precision"]
    candidate_ap = candidate["average_precision"]
    return {
        "b0_market_only": b0,
        "candidate": candidate,
        "incremental_over_b0": {
            "delta_average_precision": (
                float(candidate_ap) - float(b0_ap)
                if b0_ap is not None and candidate_ap is not None
                else None
            ),
            "brier_improvement": float(b0["brier"]) - float(candidate["brier"]),
        },
    }


def fit_b0(
    train: list[Example],
    validation: list[Example],
    epochs: int,
) -> tuple[dict[str, Any], list[float]]:
    return model_result(
        [example.market for example in train],
        [example.label for example in train],
        [example.market for example in validation],
        [example.label for example in validation],
        MARKET_FEATURES,
        epochs=epochs,
    )


def fit_ungated_b1(
    train: list[Example],
    validation: list[Example],
    epochs: int,
) -> tuple[dict[str, Any], list[float]]:
    return model_result(
        [example.market + example.kol for example in train],
        [example.label for example in train],
        [example.market + example.kol for example in validation],
        [example.label for example in validation],
        MARKET_FEATURES + KOL_FEATURES,
        epochs=epochs,
    )


def gated_scores(
    train: list[Example],
    validation: list[Example],
    b0_scores: list[float],
    gate_min: int,
    epochs: int,
) -> tuple[list[float], dict[str, Any]]:
    if gate_min == 0:
        return b0_scores.copy(), {
            "gate_min": 0,
            "active_train_rows": 0,
            "active_train_positives": 0,
            "active_validation_rows": 0,
            "fallback_to_b0": True,
            "model": None,
        }
    active_train = [example for example in train if is_active(example, gate_min)]
    active_validation_indices = [
        index for index, example in enumerate(validation) if is_active(example, gate_min)
    ]
    if not active_train:
        return b0_scores.copy(), {
            "gate_min": gate_min,
            "active_train_rows": 0,
            "active_train_positives": 0,
            "active_validation_rows": len(active_validation_indices),
            "fallback_to_b0": True,
            "model": None,
        }
    active_model, active_scores = fit_ungated_b1(active_train, validation, epochs)
    result = b0_scores.copy()
    for index in active_validation_indices:
        result[index] = active_scores[index]
    return result, {
        "gate_min": gate_min,
        "active_train_rows": len(active_train),
        "active_train_positives": sum(example.label for example in active_train),
        "active_validation_rows": len(active_validation_indices),
        "fallback_to_b0": False,
        "model": active_model,
    }


def select_gate_nested(
    outer_train: list[Example],
    start: datetime,
    outer_training_end: datetime,
    purge: timedelta,
    inner_splits: int,
    epochs: int,
) -> tuple[int, dict[str, Any]]:
    candidate_windows = (0, *GATE_WINDOWS_MIN)
    candidate_labels: dict[int, list[int]] = {window: [] for window in candidate_windows}
    candidate_b0_scores: dict[int, list[float]] = {
        window: [] for window in candidate_windows
    }
    candidate_scores: dict[int, list[float]] = {window: [] for window in candidate_windows}
    candidate_fold_details: dict[int, list[dict[str, Any]]] = {
        window: [] for window in candidate_windows
    }
    inner_boundaries = fold_boundaries(start, outer_training_end, inner_splits)
    used_inner_folds = 0
    for inner_fold, (validation_start, validation_end) in enumerate(
        inner_boundaries,
        start=1,
    ):
        training_end = validation_start - purge
        train = [example for example in outer_train if example.ts < training_end]
        validation = [
            example
            for example in outer_train
            if validation_start <= example.ts < validation_end
        ]
        if (
            not train
            or not validation
            or len({example.label for example in train}) < 2
        ):
            continue
        used_inner_folds += 1
        _b0_model, b0_scores = fit_b0(train, validation, epochs)
        labels = [example.label for example in validation]
        for window in candidate_windows:
            scores, gate_details = gated_scores(
                train,
                validation,
                b0_scores,
                window,
                epochs,
            )
            candidate_labels[window].extend(labels)
            candidate_b0_scores[window].extend(b0_scores)
            candidate_scores[window].extend(scores)
            candidate_fold_details[window].append(
                {
                    "inner_fold": inner_fold,
                    "train_rows": len(train),
                    "validation_rows": len(validation),
                    "validation_positives": sum(labels),
                    "gate_fit": {
                        key: value
                        for key, value in gate_details.items()
                        if key != "model"
                    },
                }
            )
    if used_inner_folds == 0:
        raise SystemExit("No usable inner folds for nested gate selection.")

    candidates: list[dict[str, Any]] = []
    for window in candidate_windows:
        comparison = paired_result(
            candidate_labels[window],
            candidate_b0_scores[window],
            candidate_scores[window],
        )
        candidates.append(
            {
                "gate": "off" if window == 0 else f"{window}m",
                "gate_min": window,
                "inner_oof_rows": len(candidate_labels[window]),
                "inner_oof_positives": sum(candidate_labels[window]),
                **comparison,
                "inner_folds": candidate_fold_details[window],
            }
        )
    selected = min(
        candidates,
        key=lambda candidate: (
            float(candidate["candidate"]["brier"]),
            candidate["gate_min"],
        ),
    )
    return int(selected["gate_min"]), {
        "inner_splits_requested": inner_splits,
        "inner_splits_used": used_inner_folds,
        "selection_metric": "lowest aggregate inner out-of-fold Brier score",
        "tie_break": "shorter gate, with off first",
        "candidates": candidates,
        "selected_gate": selected["gate"],
        "selected_gate_min": selected["gate_min"],
    }


def regime_diagnostics(
    examples: list[Example],
    labels: list[int],
    b0_scores: list[float],
    b1_scores: list[float],
) -> dict[str, Any]:
    diagnostics: dict[str, Any] = {}
    for window in GATE_WINDOWS_MIN:
        active = [
            index for index, example in enumerate(examples) if is_active(example, window)
        ]
        inactive = [
            index for index, example in enumerate(examples) if not is_active(example, window)
        ]

        def subset(indices: list[int]) -> dict[str, Any]:
            return paired_result(
                [labels[index] for index in indices],
                [b0_scores[index] for index in indices],
                [b1_scores[index] for index in indices],
            )

        diagnostics[f"{window}m"] = {
            "active": {"rows": len(active), **subset(active)},
            "inactive": {"rows": len(inactive), **subset(inactive)},
        }
    return diagnostics


def main() -> None:
    parser = argparse.ArgumentParser(description="Run nested gated EventX B1 validation")
    parser.add_argument("--labels", type=Path)
    parser.add_argument("--features", type=Path)
    parser.add_argument("--feature-report", type=Path)
    parser.add_argument("--toy-freeze", type=Path)
    parser.add_argument("--out", type=Path)
    parser.add_argument("--outer-splits", type=int, default=5)
    parser.add_argument("--inner-splits", type=int, default=3)
    parser.add_argument("--purge-min", type=int, default=30)
    parser.add_argument("--epochs", type=int, default=8)
    parser.add_argument("--bootstrap-samples", type=int, default=2000)
    parser.add_argument("--block-minutes", type=int, default=360)
    args = parser.parse_args()
    if min(
        args.outer_splits,
        args.inner_splits,
        args.purge_min,
        args.epochs,
        args.bootstrap_samples,
        args.block_minutes,
    ) <= 0:
        raise SystemExit("Split, duration, epoch, and sample parameters must be positive.")

    root = REPO_ROOT / "data" / "v1" / "toy"
    labels_path = args.labels or root / "labels_30m.jsonl"
    features_path = args.features or root / "kol_features_5m.jsonl"
    feature_report_path = args.feature_report or root / "kol_features_5m_report.json"
    toy_freeze_path = args.toy_freeze or root / "frozen_manifest.json"
    out_path = args.out or root / "b1_gated_nested_cv_5m.json"
    feature_report = json.loads(feature_report_path.read_text())
    toy_freeze = json.loads(toy_freeze_path.read_text())
    if feature_report["dataset_id"] != toy_freeze["dataset_id"]:
        raise SystemExit("Feature and frozen toy dataset IDs do not match.")
    if hash_file(features_path)["sha256"] != feature_report["artifact"]["sha256"]:
        raise SystemExit("KOL feature artifact hash does not match its report.")

    test_start = parse_ts(toy_freeze["split_boundaries"]["test_start"])
    pretest_start = parse_ts(toy_freeze["window"]["start"])
    pretest_end = test_start - timedelta(minutes=args.purge_min)
    cadence_min = int(feature_report["cadence_min"])
    examples, load_stats = load_pretest_examples(
        labels_path,
        features_path,
        cadence_min,
        pretest_end,
    )
    purge = timedelta(minutes=args.purge_min)
    outer_boundaries = fold_boundaries(pretest_start, pretest_end, args.outer_splits)
    folds: list[dict[str, Any]] = []
    oof_examples: list[Example] = []
    oof_fold_numbers: list[int] = []
    oof_labels: list[int] = []
    oof_b0_scores: list[float] = []
    oof_ungated_scores: list[float] = []
    oof_gated_scores: list[float] = []
    for fold_number, (validation_start, validation_end) in enumerate(
        outer_boundaries,
        start=1,
    ):
        training_end = validation_start - purge
        train = [example for example in examples if example.ts < training_end]
        validation = [
            example
            for example in examples
            if validation_start <= example.ts < validation_end
        ]
        if (
            not train
            or not validation
            or len({example.label for example in train}) < 2
        ):
            raise SystemExit(f"Outer fold {fold_number} lacks usable class coverage.")
        selected_gate, nested = select_gate_nested(
            train,
            pretest_start,
            training_end,
            purge,
            args.inner_splits,
            args.epochs,
        )
        b0_model, b0_scores = fit_b0(train, validation, args.epochs)
        ungated_model, ungated_scores = fit_ungated_b1(train, validation, args.epochs)
        gated, outer_gate_fit = gated_scores(
            train,
            validation,
            b0_scores,
            selected_gate,
            args.epochs,
        )
        labels = [example.label for example in validation]
        ungated_comparison = paired_result(labels, b0_scores, ungated_scores)
        gated_comparison = paired_result(labels, b0_scores, gated)
        model_payload = json.dumps(
            {
                "b0": b0_model,
                "ungated_b1": ungated_model,
                "selected_gate_min": selected_gate,
                "active_model": outer_gate_fit["model"],
            },
            sort_keys=True,
            separators=(",", ":"),
        )
        folds.append(
            {
                "fold": fold_number,
                "training_end_exclusive": training_end.isoformat().replace(
                    "+00:00", "Z"
                ),
                "validation_start": validation_start.isoformat().replace("+00:00", "Z"),
                "validation_end_exclusive": validation_end.isoformat().replace(
                    "+00:00", "Z"
                ),
                "train_rows": len(train),
                "train_positives": sum(example.label for example in train),
                "validation_rows": len(validation),
                "validation_positives": sum(labels),
                "nested_gate_selection": nested,
                "selected_gate": "off"
                if selected_gate == 0
                else f"{selected_gate}m",
                "outer_gate_fit": {
                    key: value for key, value in outer_gate_fit.items() if key != "model"
                },
                "ungated_b1": ungated_comparison,
                "nested_gated_b1": gated_comparison,
                "model_sha256": hashlib.sha256(model_payload.encode()).hexdigest(),
            }
        )
        oof_examples.extend(validation)
        oof_fold_numbers.extend([fold_number] * len(validation))
        oof_labels.extend(labels)
        oof_b0_scores.extend(b0_scores)
        oof_ungated_scores.extend(ungated_scores)
        oof_gated_scores.extend(gated)

    ungated_oof = paired_result(oof_labels, oof_b0_scores, oof_ungated_scores)
    gated_oof = paired_result(oof_labels, oof_b0_scores, oof_gated_scores)
    fold_gated_delta_ap = [
        float(fold["nested_gated_b1"]["incremental_over_b0"]["delta_average_precision"])
        for fold in folds
    ]
    fold_gated_brier = [
        float(fold["nested_gated_b1"]["incremental_over_b0"]["brier_improvement"])
        for fold in folds
    ]
    positive_ap_folds = sum(value > 0 for value in fold_gated_delta_ap)
    positive_brier_folds = sum(value > 0 for value in fold_gated_brier)
    bootstrap_groups: dict[str, list[int]] = {}
    for index, (fold_number, example) in enumerate(
        zip(oof_fold_numbers, oof_examples)
    ):
        bootstrap_groups.setdefault(f"{fold_number}:{example.market_id}", []).append(index)
    for indices in bootstrap_groups.values():
        indices.sort(key=lambda index: oof_examples[index].ts)
    block_rows = math.ceil(args.block_minutes / cadence_min)
    bootstrap = block_bootstrap(
        oof_labels,
        oof_b0_scores,
        oof_gated_scores,
        bootstrap_groups,
        block_rows=block_rows,
        cadence_min=cadence_min,
        samples=args.bootstrap_samples,
        seed=37,
    )
    gated_delta_ap = float(
        gated_oof["incremental_over_b0"]["delta_average_precision"]
    )
    gated_brier = float(gated_oof["incremental_over_b0"]["brier_improvement"])
    stability_gate = {
        "aggregate_delta_average_precision_positive": gated_delta_ap > 0,
        "aggregate_brier_improvement_positive": gated_brier > 0,
        "average_precision_positive_in_at_least_4_of_5_folds": positive_ap_folds
        >= math.ceil(args.outer_splits * 0.8),
        "brier_positive_in_at_least_4_of_5_folds": positive_brier_folds
        >= math.ceil(args.outer_splits * 0.8),
        "bootstrap_brier_ci_lower_above_zero": float(
            bootstrap["brier_improvement"]["ci_95_lower"]
        )
        > 0,
    }
    stability_gate["passed"] = all(stability_gate.values())
    result = {
        "status": (
            "ready_to_freeze" if stability_gate["passed"] else "do_not_freeze"
        ),
        "dataset_id": feature_report["dataset_id"],
        "kol_rule_id": feature_report["kol_rule_id"],
        "protocol": {
            "outer": "5-fold purged expanding-window evaluation",
            "inner": "3-fold purged expanding-window gate selection",
            "gate_candidates_min": [0, *GATE_WINDOWS_MIN],
            "gate_zero_meaning": "disable KOL correction and use B0",
            "selection_metric": "inner out-of-fold Brier",
            "purge_min": args.purge_min,
            "cadence_min": cadence_min,
            "test_start": test_start.isoformat().replace("+00:00", "Z"),
            "pretest_label_end_exclusive": pretest_end.isoformat().replace(
                "+00:00", "Z"
            ),
        },
        "load_validation": load_stats,
        "folds": folds,
        "selected_gates": [fold["selected_gate"] for fold in folds],
        "out_of_fold": {
            "rows": len(oof_labels),
            "positives": sum(oof_labels),
            "ungated_b1": ungated_oof,
            "nested_gated_b1": gated_oof,
        },
        "regime_diagnostics_on_ungated_b1": regime_diagnostics(
            oof_examples,
            oof_labels,
            oof_b0_scores,
            oof_ungated_scores,
        ),
        "nested_gated_fold_stability": {
            "delta_average_precision": {
                **summary(fold_gated_delta_ap),
                "positive_folds": positive_ap_folds,
                "one_sided_sign_test_p_value": sign_test_p_value(
                    positive_ap_folds,
                    args.outer_splits,
                ),
            },
            "brier_improvement": {
                **summary(fold_gated_brier),
                "positive_folds": positive_brier_folds,
                "one_sided_sign_test_p_value": sign_test_p_value(
                    positive_brier_folds,
                    args.outer_splits,
                ),
            },
        },
        "paired_block_bootstrap": bootstrap,
        "freeze_gate": stability_gate,
        "test_policy": (
            "Outer validation folds are untouched by their inner gate selection. Only "
            "pre-test labels ending before the frozen test boundary are accessed; no "
            "test metric is computed."
        ),
        "inputs": {
            "labels": str(labels_path.resolve().relative_to(REPO_ROOT)),
            "features": str(features_path.resolve().relative_to(REPO_ROOT)),
            "feature_report": str(feature_report_path.resolve().relative_to(REPO_ROOT)),
            "toy_freeze": str(toy_freeze_path.resolve().relative_to(REPO_ROOT)),
        },
    }
    out_path.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
    print(
        json.dumps(
            {
                "status": result["status"],
                "selected_gates": result["selected_gates"],
                "out_of_fold": result["out_of_fold"],
                "regime_diagnostics": result["regime_diagnostics_on_ungated_b1"],
                "fold_stability": result["nested_gated_fold_stability"],
                "bootstrap": {
                    "delta_average_precision": bootstrap[
                        "delta_average_precision"
                    ],
                    "brier_improvement": bootstrap["brier_improvement"],
                },
                "freeze_gate": result["freeze_gate"],
                "output": str(out_path),
            },
            indent=2,
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
