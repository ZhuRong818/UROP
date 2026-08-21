"""Run the fixed EventX market/news/KOL baseline ladder on pre-test folds.

The primary comparison is B3 (market + core news + KOL) versus B1
(market + core news), which isolates the incremental value of KOL features
after accounting for structured news. Test rows are alignment-checked, but
their labels are never accessed.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
from collections import defaultdict
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Iterator, NamedTuple

from eventx.features.build_kol_features import hash_file, parse_ts
from eventx.settings import REPO_ROOT
from eventx.tasks.run_b1 import (
    KOL_FEATURES,
    MARKET_FEATURES,
    metrics,
    model_result,
    transform,
)
from eventx.tasks.run_b1_walk_forward import fold_boundaries, sign_test_p_value, summary
from eventx.tasks.run_news_baseline import NEWS_CORE_FEATURES, news_transform
from eventx.tasks.validate_b1_robustness import block_bootstrap


class CombinedExample(NamedTuple):
    market: list[float]
    news: list[float]
    kol: list[float]
    label: int
    news_active_24h: bool
    kol_active_24h: bool
    market_id: str
    ts: datetime


def read_jsonl(path: Path) -> Iterator[dict[str, Any]]:
    with path.open() as handle:
        for line in handle:
            if line.strip():
                yield json.loads(line)


def row_key(row: dict[str, Any]) -> tuple[str, str, str, str]:
    return (
        str(row["venue"]),
        str(row["market_id"]),
        str(row["outcome_id"]),
        str(row["ts"]),
    )


def load_pretest_examples(
    labels_path: Path,
    news_features_path: Path,
    kol_features_path: Path,
    cadence_min: int,
    pretest_end_exclusive: datetime,
) -> tuple[list[CombinedExample], dict[str, Any]]:
    news_rows = iter(read_jsonl(news_features_path))
    kol_rows = iter(read_jsonl(kol_features_path))
    news_row = next(news_rows, None)
    kol_row = next(kol_rows, None)
    examples: list[CombinedExample] = []
    stats = {
        "cadence_rows_matched": 0,
        "ineligible_pretest_rows": 0,
        "post_pretest_rows_skipped_without_accessing_y_jump": 0,
    }
    for label_row in read_jsonl(labels_path):
        timestamp = str(label_row["ts"])
        minute = int(timestamp[11:13]) * 60 + int(timestamp[14:16])
        if timestamp[17:19] != "00" or minute % cadence_min:
            continue
        if news_row is None or kol_row is None:
            raise SystemExit("A feature artifact ended before the cadence-filtered labels.")
        key = row_key(label_row)
        if key != row_key(news_row) or key != row_key(kol_row):
            raise SystemExit(
                "Label/news/KOL artifacts are not aligned: "
                f"label={key} news={row_key(news_row)} kol={row_key(kol_row)}"
            )
        stats["cadence_rows_matched"] += 1
        timestamp_dt = parse_ts(timestamp)
        if timestamp_dt >= pretest_end_exclusive:
            stats["post_pretest_rows_skipped_without_accessing_y_jump"] += 1
        elif not int(label_row["eligible"]):
            stats["ineligible_pretest_rows"] += 1
        else:
            examples.append(
                CombinedExample(
                    market=[
                        transform(name, label_row[name]) for name in MARKET_FEATURES
                    ],
                    news=[
                        news_transform(name, news_row[name])
                        for name in NEWS_CORE_FEATURES
                    ],
                    kol=[transform(name, kol_row[name]) for name in KOL_FEATURES],
                    label=int(label_row["y_jump"]),
                    news_active_24h=int(news_row["news_article_count_1440m"]) > 0,
                    kol_active_24h=int(kol_row["kol_tweet_count_1440m"]) > 0,
                    market_id=str(label_row["market_id"]),
                    ts=timestamp_dt,
                )
            )
        news_row = next(news_rows, None)
        kol_row = next(kol_rows, None)
    if (
        news_row is not None
        or next(news_rows, None) is not None
        or kol_row is not None
        or next(kol_rows, None) is not None
    ):
        raise SystemExit("A feature artifact has unmatched trailing rows.")
    examples.sort(key=lambda example: (example.ts, example.market_id))
    stats["eligible_pretest_examples"] = len(examples)
    stats["eligible_pretest_positives"] = sum(example.label for example in examples)
    stats["activity_24h"] = {
        "news_active_rows": sum(example.news_active_24h for example in examples),
        "kol_active_rows": sum(example.kol_active_24h for example in examples),
        "both_active_rows": sum(
            example.news_active_24h and example.kol_active_24h for example in examples
        ),
    }
    return examples, stats


def metric_delta(
    labels: list[int],
    reference_scores: list[float],
    candidate_scores: list[float],
) -> dict[str, Any]:
    reference = metrics(labels, reference_scores)
    candidate = metrics(labels, candidate_scores)
    reference_ap = reference["average_precision"]
    candidate_ap = candidate["average_precision"]
    return {
        "reference": reference,
        "candidate": candidate,
        "delta_average_precision": (
            float(candidate_ap) - float(reference_ap)
            if reference_ap is not None and candidate_ap is not None
            else None
        ),
        "brier_improvement": float(reference["brier"]) - float(candidate["brier"]),
    }


def model_vectors(
    examples: list[CombinedExample],
) -> dict[str, list[list[float]]]:
    return {
        "b0_market_only": [example.market for example in examples],
        "b1_market_plus_news": [
            example.market + example.news for example in examples
        ],
        "b2_market_plus_kol": [example.market + example.kol for example in examples],
        "b3_market_plus_news_plus_kol": [
            example.market + example.news + example.kol for example in examples
        ],
    }


def comparison_set(
    labels: list[int],
    scores: dict[str, list[float]],
) -> dict[str, dict[str, Any]]:
    pairs = {
        "b1_news_over_b0": ("b0_market_only", "b1_market_plus_news"),
        "b2_kol_over_b0": ("b0_market_only", "b2_market_plus_kol"),
        "b3_over_b0": ("b0_market_only", "b3_market_plus_news_plus_kol"),
        "b3_kol_over_b1_news": (
            "b1_market_plus_news",
            "b3_market_plus_news_plus_kol",
        ),
        "b3_news_over_b2_kol": (
            "b2_market_plus_kol",
            "b3_market_plus_news_plus_kol",
        ),
    }
    return {
        name: {
            "reference_model": reference,
            "candidate_model": candidate,
            **metric_delta(labels, scores[reference], scores[candidate]),
        }
        for name, (reference, candidate) in pairs.items()
    }


def activity_strata(
    examples: list[CombinedExample],
    labels: list[int],
    b1_scores: list[float],
    b3_scores: list[float],
) -> dict[str, Any]:
    predicates = {
        "both_active": lambda row: row.news_active_24h and row.kol_active_24h,
        "kol_only": lambda row: row.kol_active_24h and not row.news_active_24h,
        "news_only": lambda row: row.news_active_24h and not row.kol_active_24h,
        "neither_active": lambda row: not row.news_active_24h
        and not row.kol_active_24h,
    }
    result = {}
    for name, predicate in predicates.items():
        indices = [index for index, example in enumerate(examples) if predicate(example)]
        selected_labels = [labels[index] for index in indices]
        if not indices:
            result[name] = {"rows": 0, "positives": 0, "comparison": None}
            continue
        result[name] = {
            "rows": len(indices),
            "positives": sum(selected_labels),
            "comparison": metric_delta(
                selected_labels,
                [b1_scores[index] for index in indices],
                [b3_scores[index] for index in indices],
            ),
        }
    return result


def relative_input(path: Path) -> str:
    return str(path.resolve().relative_to(REPO_ROOT))


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Run the fixed EventX B0/B1/B2/B3 walk-forward ladder"
    )
    parser.add_argument("--labels", type=Path)
    parser.add_argument("--news-features", type=Path)
    parser.add_argument("--news-report", type=Path)
    parser.add_argument("--kol-features", type=Path)
    parser.add_argument("--kol-report", type=Path)
    parser.add_argument("--toy-freeze", type=Path)
    parser.add_argument("--out", type=Path)
    parser.add_argument("--n-splits", type=int, default=5)
    parser.add_argument("--purge-min", type=int, default=30)
    parser.add_argument("--epochs", type=int, default=8)
    parser.add_argument("--bootstrap-samples", type=int, default=2000)
    parser.add_argument("--block-minutes", type=int, default=360)
    args = parser.parse_args()
    if (
        args.n_splits <= 0
        or args.purge_min <= 0
        or args.epochs <= 0
        or args.bootstrap_samples <= 0
        or args.block_minutes <= 0
    ):
        raise SystemExit("Fold, purge, epoch, bootstrap, and block settings must be positive.")

    root = REPO_ROOT / "data" / "v1" / "toy"
    labels_path = args.labels or root / "labels_30m.jsonl"
    news_features_path = args.news_features or root / "news_features_5m.jsonl"
    news_report_path = args.news_report or root / "news_features_5m_report.json"
    kol_features_path = args.kol_features or root / "kol_features_5m.jsonl"
    kol_report_path = args.kol_report or root / "kol_features_5m_report.json"
    freeze_path = args.toy_freeze or root / "frozen_manifest.json"
    out_path = args.out or root / "combined_b3_walk_forward_cv_5m.json"

    news_report = json.loads(news_report_path.read_text())
    kol_report = json.loads(kol_report_path.read_text())
    freeze = json.loads(freeze_path.read_text())
    dataset_ids = {
        news_report["dataset_id"],
        kol_report["dataset_id"],
        freeze["dataset_id"],
    }
    if len(dataset_ids) != 1:
        raise SystemExit("News, KOL, and frozen-toy dataset IDs do not match.")
    if int(news_report["cadence_min"]) != int(kol_report["cadence_min"]):
        raise SystemExit("News and KOL feature cadences do not match.")
    if hash_file(news_features_path)["sha256"] != news_report["artifact"]["sha256"]:
        raise SystemExit("News feature artifact hash does not match its report.")
    if hash_file(kol_features_path)["sha256"] != kol_report["artifact"]["sha256"]:
        raise SystemExit("KOL feature artifact hash does not match its report.")
    if not news_report["point_in_time_validation"]["passed"]:
        raise SystemExit("News feature artifact failed point-in-time validation.")
    if not kol_report["point_in_time_validation"]["passed"]:
        raise SystemExit("KOL feature artifact failed point-in-time validation.")

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
    feature_names = {
        "b0_market_only": MARKET_FEATURES,
        "b1_market_plus_news": MARKET_FEATURES + NEWS_CORE_FEATURES,
        "b2_market_plus_kol": MARKET_FEATURES + KOL_FEATURES,
        "b3_market_plus_news_plus_kol": (
            MARKET_FEATURES + NEWS_CORE_FEATURES + KOL_FEATURES
        ),
    }

    folds = []
    oof_examples: list[CombinedExample] = []
    oof_fold_numbers: list[int] = []
    oof_labels: list[int] = []
    oof_scores: dict[str, list[float]] = {name: [] for name in feature_names}
    seen_oof_keys: set[tuple[str, datetime]] = set()
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
        if (
            not train
            or not validation
            or len(set(train_labels)) < 2
            or len(set(validation_labels)) < 2
        ):
            raise SystemExit(f"Fold {fold_number} lacks usable binary class coverage.")

        train_vectors = model_vectors(train)
        validation_vectors = model_vectors(validation)
        fold_models = {}
        fold_scores = {}
        for model_name, names in feature_names.items():
            model, scores = model_result(
                train_vectors[model_name],
                train_labels,
                validation_vectors[model_name],
                validation_labels,
                names,
                args.epochs,
            )
            fold_models[model_name] = model
            fold_scores[model_name] = scores
        model_hash = hashlib.sha256(
            json.dumps(fold_models, sort_keys=True, separators=(",", ":")).encode()
        ).hexdigest()
        comparisons = comparison_set(validation_labels, fold_scores)
        folds.append(
            {
                "fold": fold_number,
                "training": {
                    "start": min(example.ts for example in train)
                    .isoformat()
                    .replace("+00:00", "Z"),
                    "end_exclusive": training_end.isoformat().replace("+00:00", "Z"),
                    "rows": len(train),
                    "positives": sum(train_labels),
                    "markets": len({example.market_id for example in train}),
                },
                "purge": {
                    "start": training_end.isoformat().replace("+00:00", "Z"),
                    "end": validation_start.isoformat().replace("+00:00", "Z"),
                    "minutes": args.purge_min,
                },
                "validation": {
                    "start": validation_start.isoformat().replace("+00:00", "Z"),
                    "end_exclusive": validation_end.isoformat().replace(
                        "+00:00", "Z"
                    ),
                    "rows": len(validation),
                    "positives": sum(validation_labels),
                    "markets": len({example.market_id for example in validation}),
                    "news_active_24h_rows": sum(
                        example.news_active_24h for example in validation
                    ),
                    "kol_active_24h_rows": sum(
                        example.kol_active_24h for example in validation
                    ),
                    "model_metrics": {
                        name: model["validation"]
                        for name, model in fold_models.items()
                    },
                    "comparisons": comparisons,
                },
                "model_sha256": model_hash,
                "model_coefficients": {
                    name: model["coefficients"] for name, model in fold_models.items()
                },
            }
        )
        for index, example in enumerate(validation):
            key = (example.market_id, example.ts)
            if key in seen_oof_keys:
                raise SystemExit(f"Duplicate out-of-fold prediction key: {key}")
            seen_oof_keys.add(key)
            oof_examples.append(example)
            oof_fold_numbers.append(fold_number)
            oof_labels.append(validation_labels[index])
            for model_name in feature_names:
                oof_scores[model_name].append(fold_scores[model_name][index])

    oof_metrics = {
        name: metrics(oof_labels, scores) for name, scores in oof_scores.items()
    }
    oof_comparisons = comparison_set(oof_labels, oof_scores)
    primary_fold_ap = [
        float(
            fold["validation"]["comparisons"]["b3_kol_over_b1_news"][
                "delta_average_precision"
            ]
        )
        for fold in folds
    ]
    primary_fold_brier = [
        float(
            fold["validation"]["comparisons"]["b3_kol_over_b1_news"][
                "brier_improvement"
            ]
        )
        for fold in folds
    ]
    positive_ap = sum(value > 0 for value in primary_fold_ap)
    positive_brier = sum(value > 0 for value in primary_fold_brier)

    groups: dict[str, list[int]] = defaultdict(list)
    for index, (fold_number, example) in enumerate(
        zip(oof_fold_numbers, oof_examples)
    ):
        groups[f"{fold_number}:{example.market_id}"].append(index)
    for indices in groups.values():
        indices.sort(key=lambda index: oof_examples[index].ts)
    bootstrap = block_bootstrap(
        oof_labels,
        oof_scores["b1_market_plus_news"],
        oof_scores["b3_market_plus_news_plus_kol"],
        dict(groups),
        block_rows=math.ceil(args.block_minutes / cadence_min),
        cadence_min=cadence_min,
        samples=args.bootstrap_samples,
        seed=61,
    )

    primary = oof_comparisons["b3_kol_over_b1_news"]
    freeze_gate = {
        "aggregate_delta_average_precision_positive": float(
            primary["delta_average_precision"]
        )
        > 0,
        "aggregate_brier_improvement_positive": float(primary["brier_improvement"])
        > 0,
        "average_precision_positive_in_at_least_4_of_5_folds": positive_ap
        >= math.ceil(args.n_splits * 0.8),
        "brier_positive_in_at_least_4_of_5_folds": positive_brier
        >= math.ceil(args.n_splits * 0.8),
        "bootstrap_brier_ci_lower_above_zero": float(
            bootstrap["brier_improvement"]["ci_95_lower"]
        )
        > 0,
    }
    freeze_gate["passed"] = all(freeze_gate.values())
    result = {
        "status": "ready_to_freeze" if freeze_gate["passed"] else "do_not_freeze",
        "dataset_id": freeze["dataset_id"],
        "news_rule_id": news_report["news_rule_id"],
        "kol_rule_id": kol_report["kol_rule_id"],
        "primary_comparison": "b3_kol_over_b1_news",
        "model": "standardized_logistic_sgd",
        "fixed_hyperparameters": {
            "epochs": args.epochs,
            "learning_rate": 0.02,
            "l2": 1.0e-4,
            "shuffle_seed": 11,
        },
        "features": feature_names,
        "protocol": {
            "type": f"{args.n_splits}-fold purged expanding-window",
            "cadence_min": cadence_min,
            "purge_min": args.purge_min,
            "pretest_label_end_exclusive": pretest_end.isoformat().replace(
                "+00:00", "Z"
            ),
            "test_start": test_start.isoformat().replace("+00:00", "Z"),
        },
        "load_validation": load_stats,
        "folds": folds,
        "out_of_fold": {
            "rows": len(oof_labels),
            "positives": sum(oof_labels),
            "model_metrics": oof_metrics,
            "comparisons": oof_comparisons,
        },
        "primary_fold_stability": {
            "delta_average_precision": {
                **summary(primary_fold_ap),
                "positive_folds": positive_ap,
                "one_sided_sign_test_p_value": sign_test_p_value(
                    positive_ap, args.n_splits
                ),
            },
            "brier_improvement": {
                **summary(primary_fold_brier),
                "positive_folds": positive_brier,
                "one_sided_sign_test_p_value": sign_test_p_value(
                    positive_brier, args.n_splits
                ),
            },
        },
        "primary_paired_block_bootstrap": bootstrap,
        "primary_activity_strata": activity_strata(
            oof_examples,
            oof_labels,
            oof_scores["b1_market_plus_news"],
            oof_scores["b3_market_plus_news_plus_kol"],
        ),
        "freeze_gate": freeze_gate,
        "test_policy": (
            "Rows at or after the pre-test label cutoff were alignment-checked and "
            "skipped before y_jump access. No test label or test metric is present."
        ),
        "inputs": {
            "labels": relative_input(labels_path),
            "news_features": {
                "path": relative_input(news_features_path),
                "sha256": news_report["artifact"]["sha256"],
            },
            "news_report": relative_input(news_report_path),
            "kol_features": {
                "path": relative_input(kol_features_path),
                "sha256": kol_report["artifact"]["sha256"],
            },
            "kol_report": relative_input(kol_report_path),
            "toy_freeze": relative_input(freeze_path),
        },
    }
    out_path.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
    print(
        json.dumps(
            {
                "status": result["status"],
                "primary_comparison": result["primary_comparison"],
                "out_of_fold_model_metrics": oof_metrics,
                "out_of_fold_comparisons": oof_comparisons,
                "primary_fold_stability": result["primary_fold_stability"],
                "primary_paired_block_bootstrap": bootstrap,
                "primary_activity_strata": result["primary_activity_strata"],
                "freeze_gate": freeze_gate,
                "output": str(out_path),
            },
            indent=2,
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
