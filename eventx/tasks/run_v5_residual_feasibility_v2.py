"""Matched-base and converged-solver follow-up for EventX v5 feasibility.

This version preserves every tuning trial and separates the optimizer change from
the time-to-terminal feature. It uses only opened historical discovery data.
"""

from __future__ import annotations

from datetime import datetime, timezone
import json
import os
from pathlib import Path
import warnings
from typing import Any

import numpy as np
from sklearn.exceptions import ConvergenceWarning
from sklearn.linear_model import LogisticRegression, SGDClassifier
from sklearn.preprocessing import StandardScaler

from eventx.features.v5_residual import gated_residual_probability, logit, online_story_stages
from eventx.settings import REPO_ROOT
from eventx.tasks.build_v4_discovery_examples import EXAMPLE_DTYPE
from eventx.tasks.evaluate_v4_confirmatory import two_level_bootstrap
from eventx.tasks.prepare_v3_1_historical_development_arrays import sha256_file
from eventx.tasks.prepare_v4_discovery_news_quality import EVENT_DTYPE, load_documents
from eventx.tasks.run_v4_discovery_models import FOLDS, OOF_DTYPE
from eventx.tasks.run_v4_exploratory_novelty_diffusion import reconstruct_oof_indices
from eventx.tasks.run_v5_residual_feasibility import (
    BASE_EPOCHS,
    BASE_SEED,
    BATCH_ROWS,
    EVENT_MANIFEST,
    EVENTS,
    EXAMPLES,
    EXAMPLES_MANIFEST,
    FUTURE,
    MARKETS,
    OOF,
    OOF_MANIFEST,
    SHRINKAGE_GRID,
    SPLINE_CONFIGS,
    base_values,
    build_rich_news_features,
    candidate_values,
    compare,
    market_balanced,
    metric,
    parse_utc,
    point_loss,
    read_jsonl,
    relative,
    residual_matrix,
    terminal_metadata,
    verify_manifest,
)


OUTPUT = REPO_ROOT / "data/v5/development/residual_feasibility_v2"
PREDICTIONS = OUTPUT / "predictions.bin"
REPORT = OUTPUT / "report.json"
SUMMARY = OUTPUT / "SUMMARY.md"
MANIFEST = OUTPUT / "manifest.json"
LINEAR_C_VALUES = (0.01, 0.1, 1.0)
SPLINE_C_VALUES = (0.01, 0.1)
PREDICTION_DTYPE = np.dtype(
    [
        ("market", "<u4"),
        ("minute", "<i4"),
        ("fold", "u1"),
        ("label", "u1"),
        ("exposed", "u1"),
        ("b0_v4", "<f4"),
        ("b0_matched", "<f4"),
        ("b0_v5", "<f4"),
        ("v5_a", "<f4"),
        ("v5_b", "<f4"),
    ],
    align=False,
)


def atomic_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n")
    os.replace(temporary, path)


def matched_base_scaler(
    examples: np.ndarray,
    indices: np.ndarray,
    terminal_minutes: np.ndarray,
    terminal_known: np.ndarray,
    width: int,
) -> tuple[np.ndarray, np.ndarray]:
    total = np.zeros(width, dtype=np.float64)
    total_sq = np.zeros(width, dtype=np.float64)
    count = 0
    for start in range(0, len(indices), BATCH_ROWS):
        values = base_values(
            examples,
            indices[start : start + BATCH_ROWS],
            terminal_minutes,
            terminal_known,
        )[:, :width]
        total += values.sum(axis=0, dtype=np.float64)
        total_sq += np.square(values).sum(axis=0, dtype=np.float64)
        count += len(values)
    means = total / count
    scales = np.sqrt(np.maximum(0.0, total_sq / count - means * means))
    scales[scales == 0.0] = 1.0
    return means, scales


def fit_matched_base(
    examples: np.ndarray,
    train: np.ndarray,
    validation: np.ndarray,
    terminal_minutes: np.ndarray,
    terminal_known: np.ndarray,
    fold: int,
    width: int,
) -> tuple[np.ndarray, dict[str, Any]]:
    means, scales = matched_base_scaler(
        examples, train, terminal_minutes, terminal_known, width
    )
    model = SGDClassifier(
        loss="log_loss",
        penalty="l2",
        alpha=1e-4,
        fit_intercept=True,
        max_iter=1,
        tol=None,
        shuffle=False,
        learning_rate="optimal",
        average=True,
        random_state=BASE_SEED,
    )
    rng = np.random.default_rng(BASE_SEED + fold)
    first = True
    for epoch in range(BASE_EPOCHS):
        order = rng.permutation(train)
        for start in range(0, len(order), BATCH_ROWS):
            chosen = order[start : start + BATCH_ROWS]
            values = base_values(
                examples, chosen, terminal_minutes, terminal_known
            )[:, :width]
            model.partial_fit(
                (values - means) / scales,
                np.asarray(examples["label"][chosen], dtype=np.uint8),
                classes=np.asarray([0, 1], dtype=np.uint8) if first else None,
            )
            first = False
        print(
            f"v5-v2 base width {width} fold {fold}: epoch {epoch + 1}/{BASE_EPOCHS}",
            flush=True,
        )
    output = np.empty(len(validation), dtype=np.float64)
    for start in range(0, len(validation), BATCH_ROWS):
        chosen = validation[start : start + BATCH_ROWS]
        values = base_values(
            examples, chosen, terminal_minutes, terminal_known
        )[:, :width]
        output[start : start + len(chosen)] = model.predict_proba(
            (values - means) / scales
        )[:, 1]
    return output, {
        "width": width,
        "fold": fold,
        "train_rows": len(train),
        "validation_rows": len(validation),
        "coefficient_l2_norm": float(np.linalg.norm(model.coef_)),
    }


def fit_converged(
    train: np.ndarray,
    labels: np.ndarray,
    other: np.ndarray,
    c_value: float,
) -> tuple[np.ndarray, dict[str, Any]]:
    scaler = StandardScaler()
    train_scaled = scaler.fit_transform(train)
    other_scaled = scaler.transform(other)
    model = LogisticRegression(
        C=float(c_value),
        penalty="l2",
        solver="lbfgs",
        max_iter=500,
        tol=1e-7,
        fit_intercept=True,
        random_state=271,
    )
    with warnings.catch_warnings(record=True) as captured:
        warnings.simplefilter("always", ConvergenceWarning)
        model.fit(train_scaled, labels)
    convergence_messages = [
        str(item.message)
        for item in captured
        if issubclass(item.category, ConvergenceWarning)
    ]
    return np.asarray(model.decision_function(other_scaled), dtype=np.float64), {
        "c": float(c_value),
        "iterations": int(model.n_iter_[0]),
        "converged": not convergence_messages,
        "convergence_messages": convergence_messages,
        "coefficient_l2_norm": float(np.linalg.norm(model.coef_)),
    }


def tune(
    matrix: np.ndarray,
    labels: np.ndarray,
    p0: np.ndarray,
    exposed: np.ndarray,
    train_mask: np.ndarray,
    tune_mask: np.ndarray,
    c_values: tuple[float, ...],
    spline: bool,
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    train = train_mask & exposed
    validation = tune_mask & exposed
    train_values, validation_values, transform = candidate_values(
        matrix[train], matrix[validation], spline
    )
    trials = []
    for c_value in c_values:
        decision, fit = fit_converged(
            train_values, labels[train], validation_values, c_value
        )
        raw_correction = decision - logit(p0[validation])
        for shrinkage in SHRINKAGE_GRID:
            predictions = gated_residual_probability(
                p0[validation],
                np.ones(int(validation.sum()), dtype=bool),
                raw_correction,
                shrinkage,
            )
            trials.append(
                {
                    **fit,
                    **transform,
                    "shrinkage": float(shrinkage),
                    "train_rows": int(train.sum()),
                    "tuning_rows": int(validation.sum()),
                    "tuning_log_loss": metric(labels[validation], predictions)[
                        "log_loss"
                    ],
                    "tuning_log_loss_improvement": compare(
                        labels[validation], p0[validation], predictions
                    )["log_loss_improvement"],
                }
            )
    trials.sort(
        key=lambda row: (
            float(row["tuning_log_loss"]),
            float(row["shrinkage"]),
            float(row["c"]),
        )
    )
    return trials[0], trials


def refit(
    matrix: np.ndarray,
    labels: np.ndarray,
    p0: np.ndarray,
    exposed: np.ndarray,
    train_mask: np.ndarray,
    validation_mask: np.ndarray,
    selected: dict[str, Any],
    spline: bool,
) -> tuple[np.ndarray, dict[str, Any]]:
    train = train_mask & exposed
    validation = validation_mask & exposed
    train_values, validation_values, transform = candidate_values(
        matrix[train], matrix[validation], spline
    )
    decision, fit = fit_converged(
        train_values, labels[train], validation_values, float(selected["c"])
    )
    local_exposed = exposed[validation_mask]
    correction = np.zeros(int(validation_mask.sum()), dtype=np.float64)
    correction[local_exposed] = decision - logit(p0[validation])
    prediction = gated_residual_probability(
        p0[validation_mask],
        local_exposed,
        correction,
        float(selected["shrinkage"]),
    )
    return prediction, {
        **fit,
        **transform,
        "shrinkage": float(selected["shrinkage"]),
        "train_rows": int(train.sum()),
        "validation_rows": int(validation.sum()),
    }


def main() -> None:
    if any(path.exists() for path in (PREDICTIONS, REPORT, SUMMARY, MANIFEST)):
        raise SystemExit("v5 residual feasibility v2 already exists")
    if any(
        path.exists()
        for path in (
            FUTURE / "consumption_receipt.json",
            FUTURE / "examples/examples.bin",
            FUTURE / "evaluation/result.json",
        )
    ):
        raise SystemExit("v5 historical feasibility refused after v4 consumption")
    for manifest in (EXAMPLES_MANIFEST, OOF_MANIFEST, EVENT_MANIFEST):
        verify_manifest(manifest)

    example_count = EXAMPLES.stat().st_size // EXAMPLE_DTYPE.itemsize
    oof_count = OOF.stat().st_size // OOF_DTYPE.itemsize
    event_count = EVENTS.stat().st_size // EVENT_DTYPE.itemsize
    examples = np.memmap(
        EXAMPLES, mode="r", dtype=EXAMPLE_DTYPE, shape=(example_count,)
    )
    oof = np.memmap(OOF, mode="r", dtype=OOF_DTYPE, shape=(oof_count,))
    events = np.memmap(EVENTS, mode="r", dtype=EVENT_DTYPE, shape=(event_count,))
    markets = list(read_jsonl(MARKETS))
    terminal_minutes, terminal_known = terminal_metadata(markets)
    oof_indices = reconstruct_oof_indices(examples, oof)

    base_matched = np.empty(len(oof), dtype=np.float64)
    base_v5 = np.empty(len(oof), dtype=np.float64)
    base_fits = []
    for fold, held_group, validation_start, validation_end in FOLDS:
        train = np.flatnonzero(
            (examples["minute"] < validation_start - 30)
            & (examples["group"] != held_group)
        )
        validation = np.flatnonzero(
            (examples["minute"] >= validation_start)
            & (examples["minute"] < validation_end)
            & (examples["group"] == held_group)
        )
        target = np.flatnonzero(oof["fold"] == fold)
        if not np.array_equal(validation, oof_indices[target]):
            raise RuntimeError(f"fold {fold} alignment failure")
        for width, destination, name in (
            (12, base_matched, "b0_matched"),
            (14, base_v5, "b0_v5"),
        ):
            prediction, fit = fit_matched_base(
                examples,
                train,
                validation,
                terminal_minutes,
                terminal_known,
                fold,
                width,
            )
            destination[target] = prediction
            base_fits.append({"model": name, **fit})

    documents, _stats = load_documents()
    stages = online_story_stages(
        np.asarray(
            [int(row["available_at"].timestamp() * 1_000_000) for row in documents],
            dtype=np.int64,
        ),
        [str(row["headline"]) for row in documents],
        [str(row["publisher"]) for row in documents],
    )
    oof_features = np.asarray(examples["features"][oof_indices], dtype=np.float32)
    rich, exposed, rich_names = build_rich_news_features(
        oof, oof_features, events, stages
    )
    matrix, context_names = residual_matrix(
        rich,
        oof_features,
        oof_indices,
        examples,
        base_v5,
        terminal_minutes,
        terminal_known,
    )
    labels = np.asarray(oof["label"], dtype=np.uint8)

    OUTPUT.mkdir(parents=True, exist_ok=True)
    temporary = PREDICTIONS.with_suffix(PREDICTIONS.suffix + ".tmp")
    fold_reports = []
    with temporary.open("wb") as handle:
        for fold in (3, 4, 5):
            inner_train = oof["fold"] < fold - 1
            inner_tune = oof["fold"] == fold - 1
            outer_train = oof["fold"] < fold
            outer_validation = oof["fold"] == fold
            predictions = {}
            candidate_reports = {}
            for name, c_values, spline in (
                ("v5_a", LINEAR_C_VALUES, False),
                ("v5_b", SPLINE_C_VALUES, True),
            ):
                selected, trials = tune(
                    matrix,
                    labels,
                    base_v5,
                    exposed,
                    inner_train,
                    inner_tune,
                    c_values,
                    spline,
                )
                prediction, final_fit = refit(
                    matrix,
                    labels,
                    base_v5,
                    exposed,
                    outer_train,
                    outer_validation,
                    selected,
                    spline,
                )
                predictions[name] = prediction
                candidate_reports[name] = {
                    "selected": selected,
                    "final_fit": final_fit,
                    "tuning_trials": trials,
                }
            indices = np.flatnonzero(outer_validation)
            rows = np.empty(len(indices), dtype=PREDICTION_DTYPE)
            for field in ("market", "minute", "fold", "label"):
                rows[field] = oof[field][indices]
            rows["exposed"] = exposed[indices]
            rows["b0_v4"] = oof["b0"][indices]
            rows["b0_matched"] = base_matched[indices]
            rows["b0_v5"] = base_v5[indices]
            rows["v5_a"] = predictions["v5_a"]
            rows["v5_b"] = predictions["v5_b"]
            for name in ("v5_a", "v5_b"):
                no_news = rows["exposed"] == 0
                if not np.array_equal(rows[name][no_news], rows["b0_v5"][no_news]):
                    raise RuntimeError(f"{name} no-news equality failure")
            rows.tofile(handle)
            fold_reports.append(
                {
                    "fold": fold,
                    "validation_rows": len(rows),
                    "validation_exposed_rows": int(rows["exposed"].sum()),
                    "candidates": candidate_reports,
                    "b0_matched_vs_b0_v4": compare(
                        rows["label"], rows["b0_v4"], rows["b0_matched"]
                    ),
                    "terminal_addition_b0_v5_vs_b0_matched": compare(
                        rows["label"], rows["b0_matched"], rows["b0_v5"]
                    ),
                    "v5_a_vs_b0_v5": compare(
                        rows["label"], rows["b0_v5"], rows["v5_a"]
                    ),
                    "v5_b_vs_b0_v5": compare(
                        rows["label"], rows["b0_v5"], rows["v5_b"]
                    ),
                }
            )
            print(f"v5-v2 residual fold {fold}/5 complete", flush=True)
    os.replace(temporary, PREDICTIONS)

    count = PREDICTIONS.stat().st_size // PREDICTION_DTYPE.itemsize
    rows = np.memmap(PREDICTIONS, mode="r", dtype=PREDICTION_DTYPE, shape=(count,))
    aggregate = {
        name: metric(rows["label"], rows[name])
        for name in ("b0_v4", "b0_matched", "b0_v5", "v5_a", "v5_b")
    }
    aggregate["b0_matched_vs_b0_v4"] = compare(
        rows["label"], rows["b0_v4"], rows["b0_matched"]
    )
    aggregate["terminal_addition_b0_v5_vs_b0_matched"] = compare(
        rows["label"], rows["b0_matched"], rows["b0_v5"]
    )
    bootstraps = {}
    balanced = {}
    exposed_rows = rows["exposed"] == 1
    for offset, name in enumerate(("v5_a", "v5_b")):
        aggregate[f"{name}_vs_b0_v5"] = compare(
            rows["label"], rows["b0_v5"], rows[name]
        )
        aggregate[f"{name}_vs_b0_v5_exposed"] = compare(
            rows["label"][exposed_rows],
            rows["b0_v5"][exposed_rows],
            rows[name][exposed_rows],
        )
        improvement = point_loss(rows["label"], rows["b0_v5"]) - point_loss(
            rows["label"], rows[name]
        )
        bootstraps[name] = two_level_bootstrap(
            np.asarray(rows["market"]),
            np.asarray(rows["minute"]),
            improvement,
            samples=2000,
            seed=1031 + offset,
        )
        bootstraps[name]["estimand"] = f"B0-v5 minus {name} log loss"
        balanced[name] = market_balanced(rows, rows["b0_v5"], rows[name])

    invariants = {
        "future_v4_data_read": False,
        "base_probabilities_out_of_fold": True,
        "residual_training_uses_only_earlier_oof_folds": True,
        "v5_a_no_news_max_absolute_difference": float(
            np.max(np.abs(rows["v5_a"][~exposed_rows] - rows["b0_v5"][~exposed_rows]))
        ),
        "v5_b_no_news_max_absolute_difference": float(
            np.max(np.abs(rows["v5_b"][~exposed_rows] - rows["b0_v5"][~exposed_rows]))
        ),
        "all_final_residual_fits_converged": bool(
            all(
                candidate["final_fit"]["converged"]
                for fold in fold_reports
                for candidate in fold["candidates"].values()
            )
        ),
    }
    report = {
        "experiment_id": "eventx-v5-residual-historical-feasibility-v2-20260903",
        "created_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "status": "complete",
        "role": "opened historical development feasibility; not confirmation",
        "future_v4_data_read": False,
        "frozen_v4_changed": False,
        "evaluated_folds": [3, 4, 5],
        "rows": len(rows),
        "markets": int(len(np.unique(rows["market"]))),
        "news_exposed_rows": int(exposed_rows.sum()),
        "base_fits": base_fits,
        "residual_features": rich_names + context_names,
        "folds": fold_reports,
        "aggregate": aggregate,
        "paired_bootstraps": bootstraps,
        "market_balanced": balanced,
        "invariants": invariants,
        "limitations": [
            "feature/model choices use opened historical outcomes",
            "folds 1-2 are consumed as sequential meta-training/tuning support",
            "one deterministic base fit per fold",
            "L2 rather than elastic-net residual is used to secure convergence",
            "new untouched confirmation is required for any v5 claim",
        ],
    }
    atomic_json(REPORT, report)
    SUMMARY.write_text(
        "# EventX v5 matched-base and converged residual feasibility\n\n"
        "Opened historical development only; protected v4 future data were not read.\n\n"
        f"- Matched optimizer B0 versus v4 B0 improvement: "
        f"`{aggregate['b0_matched_vs_b0_v4']['log_loss_improvement']:.6f}`.\n"
        f"- Time-to-terminal addition versus matched B0 improvement: "
        f"`{aggregate['terminal_addition_b0_v5_vs_b0_matched']['log_loss_improvement']:.6f}`.\n"
        f"- Converged V5-A versus B0-v5 improvement: "
        f"`{aggregate['v5_a_vs_b0_v5']['log_loss_improvement']:.6f}`.\n"
        f"- Converged V5-B versus B0-v5 improvement: "
        f"`{aggregate['v5_b_vs_b0_v5']['log_loss_improvement']:.6f}`.\n"
        f"- All final residual fits converged: "
        f"`{invariants['all_final_residual_fits_converged']}`.\n\n"
        "Every tuning trial is preserved in report.json. No-news predictions equal "
        "B0-v5 exactly. This run cannot confirm v5.\n",
        encoding="utf-8",
    )
    atomic_json(
        MANIFEST,
        {
            "experiment_id": report["experiment_id"],
            "status": report["status"],
            "artifacts": [
                {"path": relative(path), "sha256": sha256_file(path)}
                for path in (
                    PREDICTIONS,
                    REPORT,
                    SUMMARY,
                    Path(__file__).resolve(),
                )
            ],
            "inputs": [
                {"path": relative(path), "sha256": sha256_file(path)}
                for path in (EXAMPLES, OOF, EVENTS, MARKETS)
            ],
        },
    )
    print(
        json.dumps(
            {
                "status": report["status"],
                "aggregate": aggregate,
                "paired_bootstraps": bootstraps,
                "invariants": invariants,
            },
            indent=2,
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
