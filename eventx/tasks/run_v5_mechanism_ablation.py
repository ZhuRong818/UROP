"""Decompose the promising v5 spline residual into prespecified mechanisms.

All inputs are previously opened historical discovery data. This task does not read
the protected v4 future confirmation and cannot produce a confirmatory v5 claim.
"""

from __future__ import annotations

from datetime import datetime, timezone
import json
import os
from pathlib import Path
from typing import Any

import numpy as np
from sklearn.preprocessing import SplineTransformer

from eventx.features.v5_residual import gated_residual_probability, logit, online_story_stages
from eventx.settings import REPO_ROOT
from eventx.tasks.build_v4_discovery_examples import EXAMPLE_DTYPE
from eventx.tasks.evaluate_v4_confirmatory import two_level_bootstrap
from eventx.tasks.prepare_v3_1_historical_development_arrays import sha256_file
from eventx.tasks.prepare_v4_discovery_news_quality import EVENT_DTYPE, load_documents
from eventx.tasks.run_v4_discovery_models import FOLDS, OOF_DTYPE
from eventx.tasks.run_v4_exploratory_novelty_diffusion import reconstruct_oof_indices
from eventx.tasks.run_v5_residual_feasibility import (
    EVENT_MANIFEST,
    EVENTS,
    EXAMPLES,
    EXAMPLES_MANIFEST,
    FUTURE,
    MARKETS,
    OOF,
    OOF_MANIFEST,
    SHRINKAGE_GRID,
    build_rich_news_features,
    compare,
    market_balanced,
    metric,
    point_loss,
    read_jsonl,
    relative,
    residual_matrix,
    terminal_metadata,
    verify_manifest,
)
from eventx.tasks.run_v5_residual_feasibility_v2 import (
    fit_converged,
    fit_matched_base,
)


OUTPUT = REPO_ROOT / "data/v5/development/mechanism_ablation"
PREDICTIONS = OUTPUT / "predictions.bin"
REPORT = OUTPUT / "report.json"
SUMMARY = OUTPUT / "SUMMARY.md"
MANIFEST = OUTPUT / "manifest.json"
C_VALUES = (0.01, 0.1)
GLOBAL_SPLINE_COLUMNS = {
    16,
    21,
    22,
    23,
    24,
    25,
    26,
    27,
    28,
    29,
    38,
    39,
    40,
    41,
    42,
    43,
    44,
    45,
    50,
    51,
    52,
}
SUBSETS = {
    "context_only": tuple(range(42, 54)),
    "volume_age": (0, 1, 2, *range(16, 21), *range(42, 54)),
    "quality_age": (
        0,
        1,
        2,
        *range(16, 30),
        *range(38, 42),
        *range(42, 54),
    ),
    "lifecycle_age": (
        0,
        1,
        2,
        *range(16, 21),
        *range(30, 38),
        *range(42, 54),
    ),
    "full": tuple(range(54)),
}
PREDICTION_DTYPE = np.dtype(
    [
        ("market", "<u4"),
        ("minute", "<i4"),
        ("fold", "u1"),
        ("label", "u1"),
        ("exposed", "u1"),
        ("b0_v5", "<f4"),
        *[(name, "<f4") for name in SUBSETS],
    ],
    align=False,
)


def atomic_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n")
    os.replace(temporary, path)


def spline_values(
    train: np.ndarray,
    other: np.ndarray,
    global_columns: tuple[int, ...],
) -> tuple[np.ndarray, np.ndarray, dict[str, Any]]:
    local_spline = np.asarray(
        [
            local
            for local, global_column in enumerate(global_columns)
            if global_column in GLOBAL_SPLINE_COLUMNS
        ],
        dtype=np.int64,
    )
    if not len(local_spline):
        return train, other, {"spline_input_columns": [], "output_width": train.shape[1]}
    transformer = SplineTransformer(
        n_knots=4,
        degree=2,
        knots="quantile",
        extrapolation="linear",
        include_bias=False,
    )
    train_spline = transformer.fit_transform(train[:, local_spline])
    other_spline = transformer.transform(other[:, local_spline])
    keep = np.ones(train.shape[1], dtype=bool)
    keep[local_spline] = False
    return (
        np.column_stack((train[:, keep], train_spline)),
        np.column_stack((other[:, keep], other_spline)),
        {
            "spline_input_columns": [
                int(global_columns[index]) for index in local_spline
            ],
            "output_width": int(keep.sum() + train_spline.shape[1]),
        },
    )


def tune_subset(
    matrix: np.ndarray,
    columns: tuple[int, ...],
    labels: np.ndarray,
    p0: np.ndarray,
    exposed: np.ndarray,
    train_mask: np.ndarray,
    tune_mask: np.ndarray,
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    train = train_mask & exposed
    validation = tune_mask & exposed
    train_values, validation_values, transform = spline_values(
        matrix[train][:, columns], matrix[validation][:, columns], columns
    )
    trials = []
    for c_value in C_VALUES:
        decision, fit = fit_converged(
            train_values, labels[train], validation_values, c_value
        )
        correction = decision - logit(p0[validation])
        for shrinkage in SHRINKAGE_GRID:
            prediction = gated_residual_probability(
                p0[validation],
                np.ones(int(validation.sum()), dtype=bool),
                correction,
                shrinkage,
            )
            trials.append(
                {
                    **fit,
                    **transform,
                    "shrinkage": float(shrinkage),
                    "train_rows": int(train.sum()),
                    "tuning_rows": int(validation.sum()),
                    "log_loss_improvement": compare(
                        labels[validation], p0[validation], prediction
                    )["log_loss_improvement"],
                    "log_loss": metric(labels[validation], prediction)["log_loss"],
                }
            )
    trials.sort(
        key=lambda row: (
            float(row["log_loss"]),
            float(row["shrinkage"]),
            float(row["c"]),
        )
    )
    return trials[0], trials


def refit_subset(
    matrix: np.ndarray,
    columns: tuple[int, ...],
    labels: np.ndarray,
    p0: np.ndarray,
    exposed: np.ndarray,
    train_mask: np.ndarray,
    validation_mask: np.ndarray,
    selected: dict[str, Any],
) -> tuple[np.ndarray, dict[str, Any]]:
    train = train_mask & exposed
    validation = validation_mask & exposed
    train_values, validation_values, transform = spline_values(
        matrix[train][:, columns], matrix[validation][:, columns], columns
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
        raise SystemExit("v5 mechanism ablation already exists")
    if any(
        path.exists()
        for path in (
            FUTURE / "consumption_receipt.json",
            FUTURE / "examples/examples.bin",
            FUTURE / "evaluation/result.json",
        )
    ):
        raise SystemExit("mechanism ablation refused after v4 future consumption")
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

    p0 = np.empty(len(oof), dtype=np.float64)
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
            raise RuntimeError(f"mechanism fold {fold} alignment failure")
        prediction, fit = fit_matched_base(
            examples,
            train,
            validation,
            terminal_minutes,
            terminal_known,
            fold,
            14,
        )
        p0[target] = prediction
        base_fits.append(fit)

    documents, _document_stats = load_documents()
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
        p0,
        terminal_minutes,
        terminal_known,
    )
    if matrix.shape[1] != 54:
        raise RuntimeError(f"unexpected mechanism matrix width: {matrix.shape[1]}")
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
            candidate_predictions = {}
            candidate_reports = {}
            for name, columns in SUBSETS.items():
                selected, trials = tune_subset(
                    matrix,
                    columns,
                    labels,
                    p0,
                    exposed,
                    inner_train,
                    inner_tune,
                )
                prediction, fit = refit_subset(
                    matrix,
                    columns,
                    labels,
                    p0,
                    exposed,
                    outer_train,
                    outer_validation,
                    selected,
                )
                candidate_predictions[name] = prediction
                candidate_reports[name] = {
                    "global_columns": list(columns),
                    "selected": selected,
                    "final_fit": fit,
                    "tuning_trials": trials,
                }
            indices = np.flatnonzero(outer_validation)
            rows = np.empty(len(indices), dtype=PREDICTION_DTYPE)
            for field in ("market", "minute", "fold", "label"):
                rows[field] = oof[field][indices]
            rows["exposed"] = exposed[indices]
            rows["b0_v5"] = p0[indices]
            for name in SUBSETS:
                rows[name] = candidate_predictions[name]
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
                    "comparisons": {
                        name: compare(rows["label"], rows["b0_v5"], rows[name])
                        for name in SUBSETS
                    },
                }
            )
            print(f"v5 mechanism fold {fold}/5 complete", flush=True)
    os.replace(temporary, PREDICTIONS)

    count = PREDICTIONS.stat().st_size // PREDICTION_DTYPE.itemsize
    rows = np.memmap(PREDICTIONS, mode="r", dtype=PREDICTION_DTYPE, shape=(count,))
    exposed_rows = rows["exposed"] == 1
    aggregate = {"b0_v5": metric(rows["label"], rows["b0_v5"])}
    bootstraps = {}
    balanced = {}
    for offset, name in enumerate(SUBSETS):
        aggregate[name] = metric(rows["label"], rows[name])
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
            seed=1201 + offset,
        )
        bootstraps[name]["estimand"] = f"B0-v5 minus {name} log loss"
        balanced[name] = market_balanced(rows, rows["b0_v5"], rows[name])

    invariants = {
        "future_v4_data_read": False,
        "base_probabilities_out_of_fold": True,
        "residual_training_uses_only_earlier_oof_folds": True,
        "all_final_fits_converged": bool(
            all(
                value["final_fit"]["converged"]
                for fold in fold_reports
                for value in fold["candidates"].values()
            )
        ),
        "no_news_max_absolute_difference": {
            name: float(
                np.max(
                    np.abs(rows[name][~exposed_rows] - rows["b0_v5"][~exposed_rows])
                )
            )
            for name in SUBSETS
        },
    }
    report = {
        "experiment_id": "eventx-v5-mechanism-ablation-20260903",
        "created_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "status": "complete",
        "role": "opened historical mechanism ablation; not confirmation",
        "future_v4_data_read": False,
        "frozen_v4_changed": False,
        "evaluated_folds": [3, 4, 5],
        "rows": len(rows),
        "markets": int(len(np.unique(rows["market"]))),
        "news_exposed_rows": int(exposed_rows.sum()),
        "feature_names": rich_names + context_names,
        "subsets": {name: list(columns) for name, columns in SUBSETS.items()},
        "base_fits": base_fits,
        "folds": fold_reports,
        "aggregate": aggregate,
        "paired_bootstraps": bootstraps,
        "market_balanced": balanced,
        "invariants": invariants,
        "limitations": [
            "all mechanisms and models were developed after historical outcomes opened",
            "news exposure itself can act as a regime indicator",
            "subsets share correlated features and are descriptive, not causal decompositions",
            "folds 1-2 provide sequential meta-training and tuning support",
            "new untouched confirmation is required",
        ],
    }
    atomic_json(REPORT, report)
    lines = [
        "# EventX v5 mechanism ablation",
        "",
        "Opened historical development only; protected v4 future data were not read.",
        "",
    ]
    for name in SUBSETS:
        value = aggregate[f"{name}_vs_b0_v5"]["log_loss_improvement"]
        interval = bootstraps[name]
        lines.append(
            f"- {name}: improvement `{value:.6f}`, interval "
            f"`[{interval['ci_95_lower']:.6f}, {interval['ci_95_upper']:.6f}]`."
        )
    lines.extend(
        [
            "",
            "These nested results distinguish exposure-conditioned recalibration from "
            "incremental volume, quality and lifecycle representations. They are not "
            "confirmatory evidence.",
        ]
    )
    SUMMARY.write_text("\n".join(lines) + "\n", encoding="utf-8")
    atomic_json(
        MANIFEST,
        {
            "experiment_id": report["experiment_id"],
            "status": report["status"],
            "artifacts": [
                {"path": relative(path), "sha256": sha256_file(path)}
                for path in (PREDICTIONS, REPORT, SUMMARY, Path(__file__).resolve())
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
                "market_balanced": balanced,
                "invariants": invariants,
            },
            indent=2,
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
