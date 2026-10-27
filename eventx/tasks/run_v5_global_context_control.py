"""Test a global nonlinear market-only control against gated v5 recalibration."""

from __future__ import annotations

from datetime import datetime, timezone
import json
import os
from pathlib import Path
from typing import Any

import numpy as np
from sklearn.preprocessing import SplineTransformer

from eventx.features.v5_residual import gated_residual_probability, logit
from eventx.settings import REPO_ROOT
from eventx.tasks.build_v4_discovery_examples import EXAMPLE_DTYPE
from eventx.tasks.evaluate_v4_confirmatory import two_level_bootstrap
from eventx.tasks.prepare_v3_1_historical_development_arrays import sha256_file
from eventx.tasks.run_v4_discovery_models import FOLDS, OOF_DTYPE
from eventx.tasks.run_v4_exploratory_novelty_diffusion import reconstruct_oof_indices
from eventx.tasks.run_v5_mechanism_ablation import PREDICTION_DTYPE as MECHANISM_DTYPE
from eventx.tasks.run_v5_residual_feasibility import (
    EXAMPLES,
    EXAMPLES_MANIFEST,
    FUTURE,
    MARKETS,
    OOF,
    OOF_MANIFEST,
    SHRINKAGE_GRID,
    compare,
    market_balanced,
    metric,
    point_loss,
    read_jsonl,
    relative,
    terminal_metadata,
    verify_manifest,
)
from eventx.tasks.run_v5_residual_feasibility_v2 import fit_converged, fit_matched_base


MECHANISM_PREDICTIONS = (
    REPO_ROOT / "data/v5/development/mechanism_ablation/predictions.bin"
)
MECHANISM_MANIFEST = REPO_ROOT / "data/v5/development/mechanism_ablation/manifest.json"
OUTPUT = REPO_ROOT / "data/v5/development/global_context_control"
PREDICTIONS = OUTPUT / "predictions.bin"
REPORT = OUTPUT / "report.json"
SUMMARY = OUTPUT / "SUMMARY.md"
MANIFEST = OUTPUT / "manifest.json"
C_VALUES = (0.01, 0.1)
SPLINE_COLUMNS = np.asarray([0, 1, 2, 3, 8, 9, 10], dtype=np.int64)
PREDICTION_DTYPE = np.dtype(
    [
        ("market", "<u4"),
        ("minute", "<i4"),
        ("fold", "u1"),
        ("label", "u1"),
        ("b0_v5", "<f4"),
        ("global_context", "<f4"),
        ("gated_context", "<f4"),
        ("gated_full", "<f4"),
    ],
    align=False,
)


def atomic_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n")
    os.replace(temporary, path)


def context_matrix(
    examples: np.ndarray,
    oof_indices: np.ndarray,
    p0: np.ndarray,
    terminal_minutes: np.ndarray,
    terminal_known: np.ndarray,
) -> np.ndarray:
    features = np.asarray(examples["features"][oof_indices], dtype=np.float64)
    market = np.asarray(examples["market"][oof_indices], dtype=np.int64)
    known = terminal_known[market]
    remaining = np.maximum(
        terminal_minutes[market] - np.asarray(examples["minute"][oof_indices]), 0.0
    )
    remaining[~known] = 0.0
    return np.column_stack(
        (
            logit(p0),
            p0,
            features[:, 4],
            features[:, 5],
            np.log1p(np.maximum(features[:, 6], 0.0)),
            np.log1p(np.maximum(features[:, 7], 0.0)),
            np.log1p(np.maximum(features[:, 8], 0.0)),
            np.log1p(np.maximum(features[:, 9], 0.0)),
            np.log1p(np.maximum(features[:, 10], 0.0)),
            np.asarray(examples["price_age"][oof_indices], dtype=np.float64),
            np.log1p(remaining),
            (~known).astype(np.float64),
        )
    ).astype(np.float32)


def spline_values(
    train: np.ndarray, other: np.ndarray
) -> tuple[np.ndarray, np.ndarray, dict[str, Any]]:
    transformer = SplineTransformer(
        n_knots=4,
        degree=2,
        knots="quantile",
        extrapolation="linear",
        include_bias=False,
    )
    train_spline = transformer.fit_transform(train[:, SPLINE_COLUMNS])
    other_spline = transformer.transform(other[:, SPLINE_COLUMNS])
    keep = np.ones(train.shape[1], dtype=bool)
    keep[SPLINE_COLUMNS] = False
    return (
        np.column_stack((train[:, keep], train_spline)),
        np.column_stack((other[:, keep], other_spline)),
        {"output_width": int(keep.sum() + train_spline.shape[1])},
    )


def tune(
    matrix: np.ndarray,
    labels: np.ndarray,
    p0: np.ndarray,
    train_mask: np.ndarray,
    tune_mask: np.ndarray,
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    train_values, tune_values, transform = spline_values(
        matrix[train_mask], matrix[tune_mask]
    )
    trials = []
    for c_value in C_VALUES:
        decision, fit = fit_converged(
            train_values, labels[train_mask], tune_values, c_value
        )
        correction = decision - logit(p0[tune_mask])
        for shrinkage in SHRINKAGE_GRID:
            prediction = gated_residual_probability(
                p0[tune_mask],
                np.ones(int(tune_mask.sum()), dtype=bool),
                correction,
                shrinkage,
            )
            trials.append(
                {
                    **fit,
                    **transform,
                    "shrinkage": float(shrinkage),
                    "train_rows": int(train_mask.sum()),
                    "tuning_rows": int(tune_mask.sum()),
                    "log_loss": metric(labels[tune_mask], prediction)["log_loss"],
                    "log_loss_improvement": compare(
                        labels[tune_mask], p0[tune_mask], prediction
                    )["log_loss_improvement"],
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


def refit(
    matrix: np.ndarray,
    labels: np.ndarray,
    p0: np.ndarray,
    train_mask: np.ndarray,
    validation_mask: np.ndarray,
    selected: dict[str, Any],
) -> tuple[np.ndarray, dict[str, Any]]:
    train_values, validation_values, transform = spline_values(
        matrix[train_mask], matrix[validation_mask]
    )
    decision, fit = fit_converged(
        train_values,
        labels[train_mask],
        validation_values,
        float(selected["c"]),
    )
    correction = decision - logit(p0[validation_mask])
    prediction = gated_residual_probability(
        p0[validation_mask],
        np.ones(int(validation_mask.sum()), dtype=bool),
        correction,
        float(selected["shrinkage"]),
    )
    return prediction, {
        **fit,
        **transform,
        "shrinkage": float(selected["shrinkage"]),
        "train_rows": int(train_mask.sum()),
        "validation_rows": int(validation_mask.sum()),
    }


def main() -> None:
    if any(path.exists() for path in (PREDICTIONS, REPORT, SUMMARY, MANIFEST)):
        raise SystemExit("v5 global context control already exists")
    if any(
        path.exists()
        for path in (
            FUTURE / "consumption_receipt.json",
            FUTURE / "examples/examples.bin",
            FUTURE / "evaluation/result.json",
        )
    ):
        raise SystemExit("global context control refused after v4 future consumption")
    for manifest in (EXAMPLES_MANIFEST, OOF_MANIFEST):
        verify_manifest(manifest)
    mechanism_manifest = json.loads(MECHANISM_MANIFEST.read_text(encoding="utf-8"))
    expected = next(
        row["sha256"]
        for row in mechanism_manifest["artifacts"]
        if row["path"] == relative(MECHANISM_PREDICTIONS)
    )
    if sha256_file(MECHANISM_PREDICTIONS) != expected:
        raise RuntimeError("mechanism prediction hash mismatch")

    example_count = EXAMPLES.stat().st_size // EXAMPLE_DTYPE.itemsize
    oof_count = OOF.stat().st_size // OOF_DTYPE.itemsize
    examples = np.memmap(
        EXAMPLES, mode="r", dtype=EXAMPLE_DTYPE, shape=(example_count,)
    )
    oof = np.memmap(OOF, mode="r", dtype=OOF_DTYPE, shape=(oof_count,))
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
            raise RuntimeError(f"global context fold {fold} alignment failure")
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
    matrix = context_matrix(
        examples, oof_indices, p0, terminal_minutes, terminal_known
    )
    labels = np.asarray(oof["label"], dtype=np.uint8)

    mechanism_count = MECHANISM_PREDICTIONS.stat().st_size // MECHANISM_DTYPE.itemsize
    mechanism = np.memmap(
        MECHANISM_PREDICTIONS,
        mode="r",
        dtype=MECHANISM_DTYPE,
        shape=(mechanism_count,),
    )
    OUTPUT.mkdir(parents=True, exist_ok=True)
    temporary = PREDICTIONS.with_suffix(PREDICTIONS.suffix + ".tmp")
    fold_reports = []
    with temporary.open("wb") as handle:
        cursor = 0
        for fold in (3, 4, 5):
            inner_train = oof["fold"] < fold - 1
            inner_tune = oof["fold"] == fold - 1
            outer_train = oof["fold"] < fold
            outer_validation = oof["fold"] == fold
            selected, trials = tune(
                matrix, labels, p0, inner_train, inner_tune
            )
            prediction, final_fit = refit(
                matrix,
                labels,
                p0,
                outer_train,
                outer_validation,
                selected,
            )
            indices = np.flatnonzero(outer_validation)
            count = len(indices)
            control = mechanism[cursor : cursor + count]
            if not np.array_equal(control["fold"], oof["fold"][indices]):
                raise RuntimeError(f"mechanism fold {fold} alignment failure")
            if not np.array_equal(control["market"], oof["market"][indices]):
                raise RuntimeError(f"mechanism market {fold} alignment failure")
            rows = np.empty(count, dtype=PREDICTION_DTYPE)
            for field in ("market", "minute", "fold", "label"):
                rows[field] = oof[field][indices]
            rows["b0_v5"] = p0[indices]
            rows["global_context"] = prediction
            rows["gated_context"] = control["context_only"]
            rows["gated_full"] = control["full"]
            rows.tofile(handle)
            fold_reports.append(
                {
                    "fold": fold,
                    "validation_rows": count,
                    "selected": selected,
                    "final_fit": final_fit,
                    "tuning_trials": trials,
                    "global_vs_b0_v5": compare(
                        rows["label"], rows["b0_v5"], rows["global_context"]
                    ),
                    "gated_context_vs_global": compare(
                        rows["label"], rows["global_context"], rows["gated_context"]
                    ),
                    "gated_full_vs_global": compare(
                        rows["label"], rows["global_context"], rows["gated_full"]
                    ),
                }
            )
            cursor += count
            print(f"v5 global context fold {fold}/5 complete", flush=True)
    if cursor != len(mechanism):
        raise RuntimeError("mechanism row count not fully consumed")
    os.replace(temporary, PREDICTIONS)

    count = PREDICTIONS.stat().st_size // PREDICTION_DTYPE.itemsize
    rows = np.memmap(PREDICTIONS, mode="r", dtype=PREDICTION_DTYPE, shape=(count,))
    aggregate = {
        name: metric(rows["label"], rows[name])
        for name in ("b0_v5", "global_context", "gated_context", "gated_full")
    }
    contrasts = {
        "global_vs_b0_v5": ("b0_v5", "global_context"),
        "gated_context_vs_global": ("global_context", "gated_context"),
        "gated_full_vs_global": ("global_context", "gated_full"),
    }
    bootstraps = {}
    for offset, (name, (baseline, candidate)) in enumerate(contrasts.items()):
        aggregate[name] = compare(rows["label"], rows[baseline], rows[candidate])
        improvement = point_loss(rows["label"], rows[baseline]) - point_loss(
            rows["label"], rows[candidate]
        )
        bootstraps[name] = two_level_bootstrap(
            np.asarray(rows["market"]),
            np.asarray(rows["minute"]),
            improvement,
            samples=2000,
            seed=1501 + offset,
        )
        bootstraps[name]["estimand"] = f"{baseline} minus {candidate} log loss"

    invariants = {
        "future_v4_data_read": False,
        "market_only_control_uses_no_news_feature_or_exposure_gate": True,
        "base_probabilities_out_of_fold": True,
        "meta_training_uses_only_earlier_oof_folds": True,
        "all_fits_converged": bool(
            all(fold["final_fit"]["converged"] for fold in fold_reports)
        ),
    }
    report = {
        "experiment_id": "eventx-v5-global-nonlinear-context-control-20260903",
        "created_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "status": "complete",
        "role": "opened historical market-only control; not confirmation",
        "future_v4_data_read": False,
        "rows": len(rows),
        "markets": int(len(np.unique(rows["market"]))),
        "base_fits": base_fits,
        "folds": fold_reports,
        "aggregate": aggregate,
        "paired_bootstraps": bootstraps,
        "market_balanced": {
            name: market_balanced(rows, rows[baseline], rows[candidate])
            for name, (baseline, candidate) in contrasts.items()
        },
        "invariants": invariants,
        "limitations": [
            "model choices use opened historical outcomes",
            "this is a stacked nonlinear calibration control, not a final B0 architecture",
            "folds 1-2 provide sequential meta-training/tuning support",
            "new untouched confirmation is required",
        ],
    }
    atomic_json(REPORT, report)
    SUMMARY.write_text(
        "# EventX v5 global nonlinear market-context control\n\n"
        "Opened historical development only; protected v4 future data were not read.\n\n"
        f"- Global nonlinear market-only control versus B0-v5: "
        f"`{aggregate['global_vs_b0_v5']['log_loss_improvement']:.6f}`.\n"
        f"- News-gated context model versus global control: "
        f"`{aggregate['gated_context_vs_global']['log_loss_improvement']:.6f}`.\n"
        f"- News-gated full model versus global control: "
        f"`{aggregate['gated_full_vs_global']['log_loss_improvement']:.6f}`.\n\n"
        "This control tests whether the apparent v5 gain is nonlinear market "
        "calibration rather than news information.\n",
        encoding="utf-8",
    )
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
                for path in (EXAMPLES, OOF, MARKETS, MECHANISM_PREDICTIONS)
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
