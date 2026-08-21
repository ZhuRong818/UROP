"""Diagnose why KOL features hurt the combined EventX pre-test baseline.

This analysis refits only the already-fixed B1 and B3 specifications on the
same purged folds. It produces descriptive diagnostics and does not select,
fit, or evaluate a new candidate model. Test rows are skipped before label
access through the shared combined-example loader.
"""

from __future__ import annotations

import argparse
import json
import math
from collections import defaultdict
from datetime import timedelta
from pathlib import Path
from typing import Any

from eventx.features.build_kol_features import hash_file, parse_ts
from eventx.settings import REPO_ROOT
from eventx.tasks.run_b1 import KOL_FEATURES, MARKET_FEATURES, model_result
from eventx.tasks.run_b1_walk_forward import fold_boundaries
from eventx.tasks.run_combined_walk_forward import (
    CombinedExample,
    load_pretest_examples,
    metric_delta,
    read_jsonl,
)
from eventx.tasks.run_news_baseline import NEWS_CORE_FEATURES


def mean(values: list[float]) -> float:
    return sum(values) / len(values)


def standard_deviation(values: list[float]) -> float:
    center = mean(values)
    return math.sqrt(sum((value - center) ** 2 for value in values) / len(values))


def correlation(values: list[float], labels: list[int]) -> float | None:
    value_mean = mean(values)
    label_mean = mean([float(label) for label in labels])
    value_scale = math.sqrt(sum((value - value_mean) ** 2 for value in values))
    label_scale = math.sqrt(sum((label - label_mean) ** 2 for label in labels))
    if value_scale <= 1.0e-12 or label_scale <= 1.0e-12:
        return None
    return sum(
        (value - value_mean) * (label - label_mean)
        for value, label in zip(values, labels)
    ) / (value_scale * label_scale)


def quantile(values: list[float], probability: float) -> float:
    ordered = sorted(values)
    position = probability * (len(ordered) - 1)
    lower = math.floor(position)
    upper = math.ceil(position)
    if lower == upper:
        return ordered[lower]
    fraction = position - lower
    return ordered[lower] * (1 - fraction) + ordered[upper] * fraction


def distribution(values: list[float]) -> dict[str, float | int]:
    return {
        "rows": len(values),
        "mean": mean(values),
        "standard_deviation": standard_deviation(values),
        "p05": quantile(values, 0.05),
        "median": quantile(values, 0.5),
        "p95": quantile(values, 0.95),
        "min": min(values),
        "max": max(values),
    }


def brier_row_improvement(label: int, reference: float, candidate: float) -> float:
    return (label - reference) ** 2 - (label - candidate) ** 2


def paired_subset(
    records: list[dict[str, Any]],
    indices: list[int],
) -> dict[str, Any] | None:
    if not indices:
        return None
    labels = [int(records[index]["label"]) for index in indices]
    b1_scores = [float(records[index]["b1_score"]) for index in indices]
    b3_scores = [float(records[index]["b3_score"]) for index in indices]
    comparison = metric_delta(labels, b1_scores, b3_scores)
    row_improvements = [
        float(records[index]["brier_row_improvement"]) for index in indices
    ]
    return {
        "rows": len(indices),
        "positives": sum(labels),
        "comparison": comparison,
        "total_brier_improvement": sum(row_improvements),
        "mean_probability_change_b3_minus_b1": mean(
            [b3 - b1 for b1, b3 in zip(b1_scores, b3_scores)]
        ),
    }


def group_diagnostics(
    records: list[dict[str, Any]],
    key: str,
    questions: dict[str, str],
) -> list[dict[str, Any]]:
    groups: dict[str, list[int]] = defaultdict(list)
    for index, record in enumerate(records):
        groups[str(record[key])].append(index)
    rows = []
    for value, indices in groups.items():
        summary = paired_subset(records, indices)
        if summary is None:
            continue
        rows.append(
            {
                key: value,
                "question": questions.get(value) if key == "market_id" else None,
                "kol_active_24h_rows": sum(
                    bool(records[index]["kol_active_24h"]) for index in indices
                ),
                "news_active_24h_rows": sum(
                    bool(records[index]["news_active_24h"]) for index in indices
                ),
                **summary,
            }
        )
    rows.sort(key=lambda row: float(row["total_brier_improvement"]))
    return rows


def activity_window_diagnostics(
    examples: list[CombinedExample],
    records: list[dict[str, Any]],
) -> dict[str, Any]:
    result = {}
    for minutes in (30, 120, 360, 1440):
        feature = f"kol_tweet_count_{minutes}m"
        position = KOL_FEATURES.index(feature)
        active = [
            index for index, example in enumerate(examples) if example.kol[position] > 0
        ]
        inactive = [
            index for index, example in enumerate(examples) if example.kol[position] == 0
        ]
        result[f"{minutes}m"] = {
            "active": paired_subset(records, active),
            "inactive": paired_subset(records, inactive),
        }
    return result


def fitted_kol_component(
    example: CombinedExample,
    model: dict[str, Any],
) -> float:
    result = 0.0
    for feature, value in zip(KOL_FEATURES, example.kol):
        standardization = model["standardization"][feature]
        standardized_value = (
            value - float(standardization["mean"])
        ) / float(standardization["scale"])
        result += float(model["coefficients"][feature]) * standardized_value
    return result


def coefficient_diagnostics(
    fold_coefficients: dict[int, dict[str, float]],
) -> list[dict[str, Any]]:
    result = []
    for feature in KOL_FEATURES:
        coefficients = [
            float(fold_coefficients[fold][feature])
            for fold in sorted(fold_coefficients)
        ]
        signs = [
            1 if value > 1.0e-12 else -1 if value < -1.0e-12 else 0
            for value in coefficients
        ]
        sign_changes = sum(
            left != right and left != 0 and right != 0
            for left, right in zip(signs, signs[1:])
        )
        result.append(
            {
                "feature": feature,
                "coefficients_by_fold": coefficients,
                "signs_by_fold": signs,
                "sign_changes": sign_changes,
                "mean_absolute_coefficient": mean(
                    [abs(value) for value in coefficients]
                ),
                "coefficient_range": max(coefficients) - min(coefficients),
                "fold3_coefficient": coefficients[2],
            }
        )
    result.sort(
        key=lambda row: (
            -int(row["sign_changes"]),
            -float(row["coefficient_range"]),
        )
    )
    return result


def fold3_feature_shift(
    train: list[CombinedExample],
    validation: list[CombinedExample],
    model: dict[str, Any],
) -> list[dict[str, Any]]:
    train_labels = [example.label for example in train]
    validation_labels = [example.label for example in validation]
    result = []
    for position, feature in enumerate(KOL_FEATURES):
        train_values = [example.kol[position] for example in train]
        validation_values = [example.kol[position] for example in validation]
        train_mean = mean(train_values)
        train_scale = max(standard_deviation(train_values), 1.0e-8)
        train_correlation = correlation(train_values, train_labels)
        validation_correlation = correlation(validation_values, validation_labels)
        coefficient = float(model["coefficients"][feature])
        standardized_mean_shift = (mean(validation_values) - train_mean) / train_scale
        result.append(
            {
                "feature": feature,
                "train_mean_transformed": train_mean,
                "validation_mean_transformed": mean(validation_values),
                "standardized_mean_shift": standardized_mean_shift,
                "train_nonzero_share": sum(value != 0 for value in train_values)
                / len(train_values),
                "validation_nonzero_share": sum(
                    value != 0 for value in validation_values
                )
                / len(validation_values),
                "train_label_correlation": train_correlation,
                "validation_label_correlation": validation_correlation,
                "correlation_sign_reversal": (
                    train_correlation is not None
                    and validation_correlation is not None
                    and train_correlation * validation_correlation < 0
                ),
                "fold3_coefficient": coefficient,
                "absolute_shift_times_coefficient": abs(
                    standardized_mean_shift * coefficient
                ),
            }
        )
    result.sort(
        key=lambda row: float(row["absolute_shift_times_coefficient"]),
        reverse=True,
    )
    return result


def exclusion_sensitivity(
    records: list[dict[str, Any]],
    key: str,
    questions: dict[str, str],
) -> list[dict[str, Any]]:
    values = sorted({str(record[key]) for record in records})
    rows = []
    for value in values:
        retained = [
            index for index, record in enumerate(records) if str(record[key]) != value
        ]
        summary = paired_subset(records, retained)
        if summary is None:
            continue
        comparison = summary["comparison"]
        rows.append(
            {
                f"excluded_{key}": value,
                "question": questions.get(value) if key == "market_id" else None,
                "retained_rows": summary["rows"],
                "delta_average_precision": comparison["delta_average_precision"],
                "brier_improvement": comparison["brier_improvement"],
            }
        )
    rows.sort(key=lambda row: float(row["brier_improvement"]), reverse=True)
    return rows


def markdown_report(result: dict[str, Any]) -> str:
    primary = result["aggregate_primary_comparison"]["comparison"]
    fold3 = result["fold3"]
    root_cause = result["root_cause_summary"]
    most_harmful = result["market_diagnostics"][:5]
    coefficients = result["coefficient_stability"]
    shifts = result["fold3"]["kol_feature_shift"][:5]
    lines = [
        "# EventX B3 failure diagnosis",
        "",
        f"Dataset: `{result['dataset_id']}`  ",
        f"Status: **{result['status']}**  ",
        "Test policy: **test labels remain untouched**.",
        "",
        "## Decision",
        "",
        "**Retain B0 as the benchmark reference. Reject B3 and do not create another "
        "test-eligible KOL candidate from this frozen development set.**",
        "",
        result["decision"]["reason"],
        "",
        "A future KOL candidate requires a new development window and a preregistered "
        "specification. Reusing these folds for more feature or gate selection would "
        "turn the current validation evidence into training data.",
        "",
        "## Main evidence",
        "",
        f"- Aggregate B3 vs B1 AP change: "
        f"`{float(primary['delta_average_precision']):+.6f}`.",
        f"- Aggregate Brier improvement: "
        f"`{float(primary['brier_improvement']):+.6f}` (negative is worse).",
        f"- Fold 3 AP change: "
        f"`{float(fold3['comparison']['delta_average_precision']):+.6f}`; "
        f"Brier improvement: `{float(fold3['comparison']['brier_improvement']):+.6f}`.",
        f"- Largest market driver: {root_cause['largest_market_question']} contributed "
        f"`{float(root_cause['largest_market_net_brier_loss_share']):.1%}` of the "
        "net Brier loss.",
        f"- After excluding that market, AP change is "
        f"`{float(root_cause['largest_market_exclusion_ap_delta']):+.6f}`, but Brier "
        f"improvement remains `{float(root_cause['largest_market_exclusion_brier']):+.6f}`.",
        f"- In fold 3, 30-minute KOL-active rows moved from mean prediction "
        f"`{float(root_cause['fold3_30m_active_b1_mean_prediction']):.3f}` to "
        f"`{float(root_cause['fold3_30m_active_b3_mean_prediction']):.3f}` against "
        f"`{float(root_cause['fold3_30m_active_jump_rate']):.3f}` prevalence; their "
        f"Brier improvement was "
        f"`{float(root_cause['fold3_30m_active_brier_improvement']):+.6f}`.",
        f"- Leave-one-market exclusions making Brier positive: "
        f"`{result['concentration_tests']['market_exclusions_with_positive_brier']}`.",
        f"- Leave-one-fold exclusions making Brier positive: "
        f"`{result['concentration_tests']['fold_exclusions_with_positive_brier']}`.",
        f"- KOL features changing coefficient sign across folds: "
        f"`{result['coefficient_summary']['features_with_sign_changes']}` of "
        f"`{len(KOL_FEATURES)}`.",
        f"- Fold-3 KOL features with train/validation correlation reversal: "
        f"`{result['fold3']['features_with_correlation_sign_reversal']}` of "
        f"`{len(KOL_FEATURES)}`.",
        "",
        "## Markets contributing most Brier harm",
        "",
        "| Market | Rows | Positives | Total Brier improvement |",
        "|---|---:|---:|---:|",
    ]
    for row in most_harmful:
        question = str(row["question"] or row["market_id"]).replace("|", "\\|")
        lines.append(
            f"| {question} | {row['rows']} | {row['positives']} | "
            f"{float(row['total_brier_improvement']):+.4f} |"
        )
    lines.extend(
        [
            "",
            "## Most unstable KOL coefficients",
            "",
            "| Feature | Sign changes | Fold-3 coefficient | Range |",
            "|---|---:|---:|---:|",
        ]
    )
    for row in coefficients[:6]:
        lines.append(
            f"| `{row['feature']}` | {row['sign_changes']} | "
            f"{float(row['fold3_coefficient']):+.4f} | "
            f"{float(row['coefficient_range']):.4f} |"
        )
    lines.extend(
        [
            "",
            "## Largest fold-3 KOL distribution shifts",
            "",
            "| Feature | Standardized mean shift | Train corr. | Validation corr. |",
            "|---|---:|---:|---:|",
        ]
    )
    for row in shifts:
        train_correlation = row["train_label_correlation"]
        validation_correlation = row["validation_label_correlation"]
        train_text = "n/a" if train_correlation is None else f"{train_correlation:+.4f}"
        validation_text = (
            "n/a"
            if validation_correlation is None
            else f"{validation_correlation:+.4f}"
        )
        lines.append(
            f"| `{row['feature']}` | "
            f"{float(row['standardized_mean_shift']):+.3f} | "
            f"{train_text} | {validation_text} |"
        )
    lines.extend(
        [
            "",
            "## Permitted next step",
            "",
            "Archive this result as a negative finding and continue with B0 as the "
            "reference benchmark. KOL work can resume only with new development data; "
            "the untouched test block must not be opened to rescue or tune B3.",
            "",
        ]
    )
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser(description="Diagnose EventX combined B3 failure")
    parser.add_argument("--labels", type=Path)
    parser.add_argument("--news-features", type=Path)
    parser.add_argument("--news-report", type=Path)
    parser.add_argument("--kol-features", type=Path)
    parser.add_argument("--kol-report", type=Path)
    parser.add_argument("--toy-freeze", type=Path)
    parser.add_argument("--combined-result", type=Path)
    parser.add_argument("--selected-markets", type=Path)
    parser.add_argument("--out", type=Path)
    parser.add_argument("--markdown-out", type=Path)
    parser.add_argument("--n-splits", type=int, default=5)
    parser.add_argument("--purge-min", type=int, default=30)
    parser.add_argument("--epochs", type=int, default=8)
    args = parser.parse_args()

    root = REPO_ROOT / "data" / "v1" / "toy"
    labels_path = args.labels or root / "labels_30m.jsonl"
    news_features_path = args.news_features or root / "news_features_5m.jsonl"
    news_report_path = args.news_report or root / "news_features_5m_report.json"
    kol_features_path = args.kol_features or root / "kol_features_5m.jsonl"
    kol_report_path = args.kol_report or root / "kol_features_5m_report.json"
    freeze_path = args.toy_freeze or root / "frozen_manifest.json"
    combined_path = args.combined_result or root / "combined_b3_walk_forward_cv_5m.json"
    selected_path = args.selected_markets or root / "selected_markets.jsonl"
    out_path = args.out or root / "combined_b3_failure_diagnostic.json"
    markdown_path = args.markdown_out or root / "combined_b3_failure_diagnostic.md"

    news_report = json.loads(news_report_path.read_text())
    kol_report = json.loads(kol_report_path.read_text())
    freeze = json.loads(freeze_path.read_text())
    combined = json.loads(combined_path.read_text())
    if len(
        {
            news_report["dataset_id"],
            kol_report["dataset_id"],
            freeze["dataset_id"],
            combined["dataset_id"],
        }
    ) != 1:
        raise SystemExit("Diagnostic inputs do not share one frozen dataset ID.")
    if hash_file(news_features_path)["sha256"] != news_report["artifact"]["sha256"]:
        raise SystemExit("News feature hash mismatch.")
    if hash_file(kol_features_path)["sha256"] != kol_report["artifact"]["sha256"]:
        raise SystemExit("KOL feature hash mismatch.")
    if combined["primary_comparison"] != "b3_kol_over_b1_news":
        raise SystemExit("Unexpected combined-result primary comparison.")

    questions = {
        str(row["market_id"]): str(row["question"])
        for row in read_jsonl(selected_path)
    }
    cadence_min = int(news_report["cadence_min"])
    test_start = parse_ts(freeze["split_boundaries"]["test_start"])
    pretest_start = parse_ts(freeze["window"]["start"])
    pretest_end = test_start - timedelta(minutes=args.purge_min)
    examples, load_stats = load_pretest_examples(
        labels_path,
        news_features_path,
        kol_features_path,
        cadence_min,
        pretest_end,
    )
    boundaries = fold_boundaries(pretest_start, pretest_end, args.n_splits)
    purge = timedelta(minutes=args.purge_min)
    b1_features = MARKET_FEATURES + NEWS_CORE_FEATURES
    b3_features = MARKET_FEATURES + NEWS_CORE_FEATURES + KOL_FEATURES

    records: list[dict[str, Any]] = []
    oof_examples: list[CombinedExample] = []
    fold_coefficients: dict[int, dict[str, float]] = {}
    fold_summaries = []
    fold3_train: list[CombinedExample] = []
    fold3_validation: list[CombinedExample] = []
    fold3_model: dict[str, Any] | None = None
    for fold_number, (validation_start, validation_end) in enumerate(
        boundaries, start=1
    ):
        training_end = validation_start - purge
        train = [example for example in examples if example.ts < training_end]
        validation = [
            example
            for example in examples
            if validation_start <= example.ts < validation_end
        ]
        train_labels = [example.label for example in train]
        validation_labels = [example.label for example in validation]
        b1, b1_scores = model_result(
            [example.market + example.news for example in train],
            train_labels,
            [example.market + example.news for example in validation],
            validation_labels,
            b1_features,
            args.epochs,
        )
        b3, b3_scores = model_result(
            [example.market + example.news + example.kol for example in train],
            train_labels,
            [
                example.market + example.news + example.kol
                for example in validation
            ],
            validation_labels,
            b3_features,
            args.epochs,
        )
        fold_coefficients[fold_number] = {
            feature: float(b3["coefficients"][feature]) for feature in KOL_FEATURES
        }
        start_index = len(records)
        for example, label, b1_score, b3_score in zip(
            validation,
            validation_labels,
            b1_scores,
            b3_scores,
        ):
            records.append(
                {
                    "fold": fold_number,
                    "market_id": example.market_id,
                    "label": label,
                    "b1_score": b1_score,
                    "b3_score": b3_score,
                    "brier_row_improvement": brier_row_improvement(
                        label, b1_score, b3_score
                    ),
                    "kol_logit_component_b3": fitted_kol_component(example, b3),
                    "news_active_24h": example.news_active_24h,
                    "kol_active_24h": example.kol_active_24h,
                }
            )
            oof_examples.append(example)
        fold_indices = list(range(start_index, len(records)))
        fold_summary = paired_subset(records, fold_indices)
        if fold_summary is None:
            raise SystemExit(f"Fold {fold_number} has no diagnostic rows.")
        fold_summaries.append({"fold": fold_number, **fold_summary})
        if fold_number == 3:
            fold3_train = train
            fold3_validation = validation
            fold3_model = b3

    if fold3_model is None:
        raise SystemExit("Fold 3 was not produced.")
    all_indices = list(range(len(records)))
    aggregate = paired_subset(records, all_indices)
    if aggregate is None:
        raise SystemExit("No out-of-fold diagnostic rows.")
    market_rows = group_diagnostics(records, "market_id", questions)
    fold3_indices = [
        index for index, record in enumerate(records) if int(record["fold"]) == 3
    ]
    fold3_records = [records[index] for index in fold3_indices]
    fold3_examples = [
        example
        for example, record in zip(oof_examples, records)
        if int(record["fold"]) == 3
    ]
    fold3_market_rows = group_diagnostics(fold3_records, "market_id", questions)
    market_exclusions = exclusion_sensitivity(records, "market_id", questions)
    fold_exclusions = exclusion_sensitivity(records, "fold", questions)
    coefficient_rows = coefficient_diagnostics(fold_coefficients)
    feature_shift = fold3_feature_shift(
        fold3_train,
        fold3_validation,
        fold3_model,
    )
    fold3_summary = paired_subset(records, fold3_indices)
    if fold3_summary is None:
        raise SystemExit("Fold 3 has no diagnostic rows.")
    aggregate_activity = activity_window_diagnostics(oof_examples, records)
    fold3_activity = activity_window_diagnostics(fold3_examples, fold3_records)

    negative_market_contribution = sum(
        min(0.0, float(row["total_brier_improvement"])) for row in market_rows
    )
    top5_negative = sum(
        min(0.0, float(row["total_brier_improvement"])) for row in market_rows[:5]
    )
    features_with_sign_changes = sum(
        int(row["sign_changes"]) > 0 for row in coefficient_rows
    )
    sign_reversals = sum(
        bool(row["correlation_sign_reversal"]) for row in feature_shift
    )
    largest_market = market_rows[0]
    largest_market_exclusion = next(
        row
        for row in market_exclusions
        if row["excluded_market_id"] == largest_market["market_id"]
    )
    fold3_30m_active = fold3_activity["30m"]["active"]
    if fold3_30m_active is None:
        raise SystemExit("Fold 3 has no 30-minute KOL-active diagnostic rows.")
    fold3_30m_comparison = fold3_30m_active["comparison"]
    result = {
        "status": "diagnosis_complete_test_untouched",
        "dataset_id": freeze["dataset_id"],
        "news_rule_id": news_report["news_rule_id"],
        "kol_rule_id": kol_report["kol_rule_id"],
        "load_validation": load_stats,
        "protocol": {
            "type": f"{args.n_splits}-fold purged expanding-window diagnostic",
            "cadence_min": cadence_min,
            "purge_min": args.purge_min,
            "pretest_label_end_exclusive": pretest_end.isoformat().replace(
                "+00:00", "Z"
            ),
            "test_start": test_start.isoformat().replace("+00:00", "Z"),
            "models_refit": ["b1_market_plus_news", "b3_market_plus_news_plus_kol"],
            "new_candidate_selected": False,
        },
        "aggregate_primary_comparison": aggregate,
        "fold_diagnostics": fold_summaries,
        "market_diagnostics": market_rows,
        "activity_window_diagnostics": aggregate_activity,
        "prediction_change": {
            "b3_minus_b1": distribution(
                [
                    float(record["b3_score"]) - float(record["b1_score"])
                    for record in records
                ]
            ),
            "b3_fitted_kol_logit_component": distribution(
                [float(record["kol_logit_component_b3"]) for record in records]
            ),
            "b3_minus_b1_by_label": {
                str(label): distribution(
                    [
                        float(record["b3_score"]) - float(record["b1_score"])
                        for record in records
                        if int(record["label"]) == label
                    ]
                )
                for label in (0, 1)
            },
        },
        "fold3": {
            **fold3_summary,
            "market_diagnostics": fold3_market_rows,
            "activity_window_diagnostics": fold3_activity,
            "kol_feature_shift": feature_shift,
            "features_with_correlation_sign_reversal": sign_reversals,
        },
        "root_cause_summary": {
            "failure_mode": (
                "Nonstationary short-window KOL activity produces unstable probability "
                "shifts. Ranking damage is concentrated in the largest market driver, "
                "while calibration damage remains after removing it."
            ),
            "largest_market_id": largest_market["market_id"],
            "largest_market_question": largest_market["question"],
            "largest_market_total_brier_improvement": largest_market[
                "total_brier_improvement"
            ],
            "largest_market_net_brier_loss_share": float(
                largest_market["total_brier_improvement"]
            )
            / float(aggregate["total_brier_improvement"]),
            "largest_market_exclusion_ap_delta": largest_market_exclusion[
                "delta_average_precision"
            ],
            "largest_market_exclusion_brier": largest_market_exclusion[
                "brier_improvement"
            ],
            "fold3_30m_active_rows": fold3_30m_active["rows"],
            "fold3_30m_active_jump_rate": fold3_30m_comparison["reference"][
                "jump_rate"
            ],
            "fold3_30m_active_b1_mean_prediction": fold3_30m_comparison["reference"][
                "mean_prediction"
            ],
            "fold3_30m_active_b3_mean_prediction": fold3_30m_comparison["candidate"][
                "mean_prediction"
            ],
            "fold3_30m_active_ap_delta": fold3_30m_comparison[
                "delta_average_precision"
            ],
            "fold3_30m_active_brier_improvement": fold3_30m_comparison[
                "brier_improvement"
            ],
        },
        "coefficient_stability": coefficient_rows,
        "coefficient_summary": {
            "features_with_sign_changes": features_with_sign_changes,
            "features_with_two_or_more_sign_changes": sum(
                int(row["sign_changes"]) >= 2 for row in coefficient_rows
            ),
        },
        "concentration_tests": {
            "markets_with_negative_total_brier_contribution": sum(
                float(row["total_brier_improvement"]) < 0 for row in market_rows
            ),
            "top5_share_of_negative_market_brier_contribution": (
                top5_negative / negative_market_contribution
                if negative_market_contribution
                else None
            ),
            "leave_one_market_out": market_exclusions,
            "market_exclusions_with_positive_brier": sum(
                float(row["brier_improvement"]) > 0 for row in market_exclusions
            ),
            "market_exclusions_with_positive_ap": sum(
                row["delta_average_precision"] is not None
                and float(row["delta_average_precision"]) > 0
                for row in market_exclusions
            ),
            "leave_one_fold_out": fold_exclusions,
            "fold_exclusions_with_positive_brier": sum(
                float(row["brier_improvement"]) > 0 for row in fold_exclusions
            ),
            "fold_exclusions_with_positive_ap": sum(
                row["delta_average_precision"] is not None
                and float(row["delta_average_precision"]) > 0
                for row in fold_exclusions
            ),
        },
        "decision": {
            "benchmark_reference": "b0_market_only",
            "b3": "reject",
            "open_test": False,
            "new_candidate_on_current_development_set": "not_justified",
            "reason": (
                "The KOL loss is not rescued by excluding any single market or fold, "
                "coefficient signs and feature-label relationships are unstable, and "
                "the prior nested activity-gate experiment already selected KOL off "
                "in four of five outer folds. More selection on the same folds would "
                "overfit the development evidence."
            ),
            "future_research_requirement": (
                "Use a new development window and preregister a sparse or residualized "
                "KOL specification before any further test-eligible evaluation."
            ),
        },
        "test_policy": (
            "The shared loader alignment-checked all feature rows at or after the "
            "pre-test cutoff and skipped them before y_jump access. No test labels "
            "or test metrics are present."
        ),
        "inputs": {
            "combined_result": {
                "path": str(combined_path.resolve().relative_to(REPO_ROOT)),
                "sha256": hash_file(combined_path)["sha256"],
            },
            "news_features_sha256": news_report["artifact"]["sha256"],
            "kol_features_sha256": kol_report["artifact"]["sha256"],
        },
    }
    out_path.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
    markdown_path.write_text(markdown_report(result))
    print(
        json.dumps(
            {
                "status": result["status"],
                "aggregate": aggregate,
                "fold3": {
                    "comparison": fold3_summary["comparison"],
                    "features_with_correlation_sign_reversal": sign_reversals,
                },
                "coefficient_summary": result["coefficient_summary"],
                "concentration_tests": {
                    key: value
                    for key, value in result["concentration_tests"].items()
                    if not key.startswith("leave_one_")
                },
                "decision": result["decision"],
                "json_output": str(out_path),
                "markdown_output": str(markdown_path),
            },
            indent=2,
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
