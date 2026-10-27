"""Select a direct or stacked nonlinear B0-v5N on opened development data.

This task is design-stage evidence only. It refuses to run after consumption of the
protected v4 future interval and never reads news features or future outcomes.
"""

from __future__ import annotations

from datetime import datetime, timezone
import json
import os
from pathlib import Path
from typing import Any

import numpy as np

from eventx.features.v5_market import (
    MARKET_FEATURE_NAMES,
    NONLINEAR_COLUMNS,
    fit_market_spline_basis,
    market_values,
)
from eventx.features.v5_residual import sigmoid
from eventx.settings import REPO_ROOT
from eventx.tasks.build_v4_discovery_examples import EXAMPLE_DTYPE
from eventx.tasks.evaluate_v4_confirmatory import two_level_bootstrap
from eventx.tasks.prepare_v3_1_historical_development_arrays import sha256_file
from eventx.tasks.run_v4_discovery_models import OOF_DTYPE
from eventx.tasks.run_v4_exploratory_novelty_diffusion import reconstruct_oof_indices
from eventx.tasks.run_v5_global_context_control import (
    PREDICTION_DTYPE as GLOBAL_DTYPE,
)
from eventx.tasks.run_v5_residual_feasibility import (
    EXAMPLES,
    EXAMPLES_MANIFEST,
    FUTURE,
    MARKETS,
    OOF,
    OOF_MANIFEST,
    compare,
    market_balanced,
    metric,
    point_loss,
    read_jsonl,
    relative,
    terminal_metadata,
    verify_manifest,
)
from eventx.tasks.run_v5_residual_feasibility_v2 import fit_converged


GLOBAL = REPO_ROOT / "data/v5/development/global_context_control/predictions.bin"
GLOBAL_MANIFEST = REPO_ROOT / "data/v5/development/global_context_control/manifest.json"
OUTPUT = REPO_ROOT / "data/v5/development/market_baseline_selection"
PREDICTIONS = OUTPUT / "predictions.bin"
REPORT = OUTPUT / "report.json"
MODEL_SPEC = OUTPUT / "model_spec.json"
SUMMARY = OUTPUT / "SUMMARY.md"
MANIFEST = OUTPUT / "manifest.json"
C_VALUES = (0.001, 0.01, 0.1)
PREDICTION_DTYPE = np.dtype(
    [
        ("market", "<u4"),
        ("minute", "<i4"),
        ("fold", "u1"),
        ("label", "u1"),
        ("b0_v5_linear", "<f4"),
        ("direct_nonlinear", "<f4"),
        ("stacked_nonlinear", "<f4"),
    ],
    align=False,
)


def atomic_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n")
    os.replace(temporary, path)


def tune_direct(
    matrix: np.ndarray,
    labels: np.ndarray,
    train_mask: np.ndarray,
    tune_mask: np.ndarray,
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    basis, training = fit_market_spline_basis(matrix[train_mask])
    tuning = basis.transform(matrix[tune_mask])
    trials = []
    for c_value in C_VALUES:
        decision, fit = fit_converged(
            training, labels[train_mask], tuning, c_value
        )
        prediction = sigmoid(decision)
        trials.append(
            {
                **fit,
                "train_rows": int(train_mask.sum()),
                "tuning_rows": int(tune_mask.sum()),
                "output_width": int(training.shape[1]),
                "tuning_log_loss": metric(labels[tune_mask], prediction)["log_loss"],
            }
        )
    trials.sort(key=lambda row: (float(row["tuning_log_loss"]), float(row["c"])))
    return trials[0], trials


def refit_direct(
    matrix: np.ndarray,
    labels: np.ndarray,
    train_mask: np.ndarray,
    validation_mask: np.ndarray,
    c_value: float,
) -> tuple[np.ndarray, dict[str, Any]]:
    basis, training = fit_market_spline_basis(matrix[train_mask])
    validation = basis.transform(matrix[validation_mask])
    decision, fit = fit_converged(
        training, labels[train_mask], validation, c_value
    )
    return sigmoid(decision), {
        **fit,
        "train_rows": int(train_mask.sum()),
        "validation_rows": int(validation_mask.sum()),
        "output_width": int(training.shape[1]),
    }


def main() -> None:
    if any(path.exists() for path in (PREDICTIONS, REPORT, MODEL_SPEC, SUMMARY, MANIFEST)):
        raise SystemExit("v5 market baseline selection already exists")
    if any(
        path.exists()
        for path in (
            FUTURE / "consumption_receipt.json",
            FUTURE / "examples/examples.bin",
            FUTURE / "evaluation/result.json",
        )
    ):
        raise SystemExit("B0-v5N selection refused after v4 future consumption")
    for manifest in (EXAMPLES_MANIFEST, OOF_MANIFEST, GLOBAL_MANIFEST):
        verify_manifest(manifest)

    example_count = EXAMPLES.stat().st_size // EXAMPLE_DTYPE.itemsize
    oof_count = OOF.stat().st_size // OOF_DTYPE.itemsize
    global_count = GLOBAL.stat().st_size // GLOBAL_DTYPE.itemsize
    examples = np.memmap(
        EXAMPLES, mode="r", dtype=EXAMPLE_DTYPE, shape=(example_count,)
    )
    oof = np.memmap(OOF, mode="r", dtype=OOF_DTYPE, shape=(oof_count,))
    global_rows = np.memmap(
        GLOBAL, mode="r", dtype=GLOBAL_DTYPE, shape=(global_count,)
    )
    markets = list(read_jsonl(MARKETS))
    terminal_minutes, terminal_known = terminal_metadata(markets)
    oof_indices = reconstruct_oof_indices(examples, oof)
    matrix = market_values(
        examples["features"][oof_indices, :12],
        examples["market"][oof_indices],
        examples["minute"][oof_indices],
        examples["price_age"][oof_indices],
        terminal_minutes,
        terminal_known,
    )
    labels = np.asarray(oof["label"], dtype=np.uint8)

    OUTPUT.mkdir(parents=True, exist_ok=True)
    temporary = PREDICTIONS.with_suffix(PREDICTIONS.suffix + ".tmp")
    fold_reports = []
    cursor = 0
    with temporary.open("wb") as handle:
        for fold in (3, 4, 5):
            inner_train = oof["fold"] < fold - 1
            inner_tune = oof["fold"] == fold - 1
            outer_train = oof["fold"] < fold
            outer_validation = oof["fold"] == fold
            selected, trials = tune_direct(
                matrix, labels, inner_train, inner_tune
            )
            direct, final_fit = refit_direct(
                matrix,
                labels,
                outer_train,
                outer_validation,
                float(selected["c"]),
            )
            indices = np.flatnonzero(outer_validation)
            count = len(indices)
            stacked = global_rows[cursor : cursor + count]
            for field in ("market", "minute", "fold", "label"):
                if not np.array_equal(stacked[field], oof[field][indices]):
                    raise RuntimeError(f"stacked baseline {field} fold {fold} misalignment")
            rows = np.empty(count, dtype=PREDICTION_DTYPE)
            for field in ("market", "minute", "fold", "label"):
                rows[field] = oof[field][indices]
            rows["b0_v5_linear"] = stacked["b0_v5"]
            rows["direct_nonlinear"] = direct
            rows["stacked_nonlinear"] = stacked["global_context"]
            rows.tofile(handle)
            fold_reports.append(
                {
                    "fold": fold,
                    "validation_rows": count,
                    "selected": selected,
                    "tuning_trials": trials,
                    "final_fit": final_fit,
                    "direct_vs_linear": compare(
                        rows["label"], rows["b0_v5_linear"], rows["direct_nonlinear"]
                    ),
                    "stacked_vs_linear": compare(
                        rows["label"], rows["b0_v5_linear"], rows["stacked_nonlinear"]
                    ),
                    "direct_vs_stacked": compare(
                        rows["label"], rows["stacked_nonlinear"], rows["direct_nonlinear"]
                    ),
                }
            )
            cursor += count
            print(f"B0-v5N direct comparison fold {fold}/5 complete", flush=True)
    if cursor != len(global_rows):
        raise RuntimeError("stacked prediction rows were not fully consumed")
    os.replace(temporary, PREDICTIONS)

    row_count = PREDICTIONS.stat().st_size // PREDICTION_DTYPE.itemsize
    rows = np.memmap(PREDICTIONS, mode="r", dtype=PREDICTION_DTYPE, shape=(row_count,))
    models = ("b0_v5_linear", "direct_nonlinear", "stacked_nonlinear")
    aggregate = {name: metric(rows["label"], rows[name]) for name in models}
    contrast_fields = {
        "direct_vs_linear": ("b0_v5_linear", "direct_nonlinear"),
        "stacked_vs_linear": ("b0_v5_linear", "stacked_nonlinear"),
        "direct_vs_stacked": ("stacked_nonlinear", "direct_nonlinear"),
    }
    comparisons = {}
    bootstraps = {}
    for offset, (name, (baseline, candidate)) in enumerate(contrast_fields.items()):
        comparisons[name] = compare(rows["label"], rows[baseline], rows[candidate])
        improvement = point_loss(rows["label"], rows[baseline]) - point_loss(
            rows["label"], rows[candidate]
        )
        bootstraps[name] = two_level_bootstrap(
            np.asarray(rows["market"]),
            np.asarray(rows["minute"]),
            improvement,
            samples=2000,
            seed=1601 + offset,
        )
        bootstraps[name]["estimand"] = f"{baseline} minus {candidate} log loss"

    selected_architecture = min(
        ("direct_nonlinear", "stacked_nonlinear"),
        key=lambda name: (aggregate[name]["log_loss"], name),
    )
    invariants = {
        "future_v4_data_read": False,
        "news_features_used": False,
        "spline_basis_fit_on_training_rows_only": True,
        "direct_meta_or_base_probability_used": False,
        "stacked_base_probabilities_out_of_fold": True,
        "selection_uses_opened_development_only": True,
        "all_direct_fits_converged": bool(
            all(
                fold["selected"]["converged"] and fold["final_fit"]["converged"]
                for fold in fold_reports
            )
        ),
    }
    report = {
        "experiment_id": "eventx-v5-market-baseline-selection-20260903",
        "created_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "status": "complete",
        "role": "opened historical B0-v5N architecture selection; not confirmation",
        "rows": len(rows),
        "markets": int(len(np.unique(rows["market"]))),
        "selected_opened_development_architecture": selected_architecture,
        "aggregate": aggregate,
        "comparisons": comparisons,
        "paired_bootstraps": bootstraps,
        "market_balanced": {
            name: market_balanced(rows, rows[baseline], rows[candidate])
            for name, (baseline, candidate) in contrast_fields.items()
        },
        "folds": fold_reports,
        "invariants": invariants,
        "limitations": [
            "selection uses opened historical outcomes and is not confirmation",
            "folds 1-2 provide sequential training and tuning support",
            "the stacked comparator is the completed global market-only control",
            "a new label-blind source/cohort/power audit is required before freezing",
        ],
    }
    spec = {
        "design_id": "eventx-b0-v5n-development-candidate-20260903",
        "status": "development_selected_not_frozen",
        "architecture": selected_architecture,
        "feature_names": list(MARKET_FEATURE_NAMES),
        "nonlinear_columns": [MARKET_FEATURE_NAMES[i] for i in NONLINEAR_COLUMNS],
        "spline": {
            "n_knots": 4,
            "degree": 2,
            "knots": "quantile",
            "extrapolation": "linear",
            "include_bias": False,
            "fit_scope": "training partition only",
        },
        "regularization_grid": list(C_VALUES),
        "selection_metric": "inner-fold log loss",
        "outer_evaluation_folds": [3, 4, 5],
        "confirmation_status": "requires new untouched interval",
    }
    atomic_json(REPORT, report)
    atomic_json(MODEL_SPEC, spec)
    direct_delta = comparisons["direct_vs_stacked"]["log_loss_improvement"]
    direct_ci = bootstraps["direct_vs_stacked"]
    SUMMARY.write_text(
        "# EventX B0-v5N architecture selection\n\n"
        "Opened historical development only; protected v4 future data were not read.\n\n"
        f"- Selected development architecture: `{selected_architecture}`.\n"
        f"- Direct minus stacked comparison (positive favours direct): "
        f"`{direct_delta:.6f}`.\n"
        f"- Paired interval: `[{direct_ci['ci_95_lower']:.6f}, "
        f"{direct_ci['ci_95_upper']:.6f}]`.\n"
        f"- Direct versus linear B0-v5: "
        f"`{comparisons['direct_vs_linear']['log_loss_improvement']:.6f}`.\n"
        f"- Stacked versus linear B0-v5: "
        f"`{comparisons['stacked_vs_linear']['log_loss_improvement']:.6f}`.\n\n"
        "This result selects a market-only development architecture; it does not "
        "confirm performance on a new interval.\n",
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
                    MODEL_SPEC,
                    SUMMARY,
                    Path(__file__).resolve(),
                    REPO_ROOT / "eventx/features/v5_market.py",
                )
            ],
            "inputs": [
                {"path": relative(path), "sha256": sha256_file(path)}
                for path in (EXAMPLES, OOF, MARKETS, GLOBAL)
            ],
        },
    )
    print(
        json.dumps(
            {
                "status": report["status"],
                "selected": selected_architecture,
                "aggregate": aggregate,
                "comparisons": comparisons,
                "paired_bootstraps": bootstraps,
                "invariants": invariants,
            },
            indent=2,
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
