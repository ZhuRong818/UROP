"""Versioned convergence repair for the selected direct B0-v5N architecture.

The original architecture-selection artifact is preserved. Only its non-converged
fold-4 final fit is repeated with the same selected hyperparameter and a larger fixed
iteration budget; the resulting full prediction artifact is separately versioned.
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
from sklearn.linear_model import LogisticRegression
from sklearn.preprocessing import StandardScaler

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
from eventx.tasks.run_v5_market_baseline_selection import (
    PREDICTION_DTYPE,
    compare,
    market_balanced,
    metric,
    point_loss,
)
from eventx.tasks.run_v5_residual_feasibility import (
    EXAMPLES,
    EXAMPLES_MANIFEST,
    FUTURE,
    MARKETS,
    OOF,
    OOF_MANIFEST,
    read_jsonl,
    relative,
    terminal_metadata,
    verify_manifest,
)


SOURCE_DIR = REPO_ROOT / "data/v5/development/market_baseline_selection"
SOURCE_PREDICTIONS = SOURCE_DIR / "predictions.bin"
SOURCE_REPORT = SOURCE_DIR / "report.json"
SOURCE_MANIFEST = SOURCE_DIR / "manifest.json"
OUTPUT = REPO_ROOT / "data/v5/development/market_baseline_selection_v2"
PREDICTIONS = OUTPUT / "predictions.bin"
REPORT = OUTPUT / "report.json"
MODEL_SPEC = OUTPUT / "model_spec.json"
SUMMARY = OUTPUT / "SUMMARY.md"
MANIFEST = OUTPUT / "manifest.json"
REPAIRED_FOLD = 4
MAX_ITER = 2000
TOLERANCE = 1e-7


def atomic_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n")
    os.replace(temporary, path)


def converged_fit(
    training: np.ndarray,
    labels: np.ndarray,
    validation: np.ndarray,
    c_value: float,
) -> tuple[np.ndarray, dict[str, Any]]:
    scaler = StandardScaler()
    training_scaled = scaler.fit_transform(training)
    validation_scaled = scaler.transform(validation)
    model = LogisticRegression(
        C=float(c_value),
        penalty="l2",
        solver="lbfgs",
        max_iter=MAX_ITER,
        tol=TOLERANCE,
        fit_intercept=True,
        random_state=271,
    )
    with warnings.catch_warnings(record=True) as captured:
        warnings.simplefilter("always", ConvergenceWarning)
        model.fit(training_scaled, labels)
    messages = [
        str(item.message)
        for item in captured
        if issubclass(item.category, ConvergenceWarning)
    ]
    return sigmoid(model.decision_function(validation_scaled)), {
        "c": float(c_value),
        "solver": "lbfgs",
        "max_iter": MAX_ITER,
        "tolerance": TOLERANCE,
        "iterations": int(model.n_iter_[0]),
        "converged": not messages,
        "convergence_messages": messages,
        "coefficient_l2_norm": float(np.linalg.norm(model.coef_)),
        "train_rows": int(len(training)),
        "validation_rows": int(len(validation)),
        "output_width": int(training.shape[1]),
    }


def main() -> None:
    if any(path.exists() for path in (PREDICTIONS, REPORT, MODEL_SPEC, SUMMARY, MANIFEST)):
        raise SystemExit("v5 market convergence-check artifacts already exist")
    if any(
        path.exists()
        for path in (
            FUTURE / "consumption_receipt.json",
            FUTURE / "examples/examples.bin",
            FUTURE / "evaluation/result.json",
        )
    ):
        raise SystemExit("B0-v5N convergence repair refused after v4 future consumption")
    for manifest in (EXAMPLES_MANIFEST, OOF_MANIFEST, SOURCE_MANIFEST):
        verify_manifest(manifest)

    source_report = json.loads(SOURCE_REPORT.read_text(encoding="utf-8"))
    selected = next(
        fold["selected"]
        for fold in source_report["folds"]
        if int(fold["fold"]) == REPAIRED_FOLD
    )
    source_count = SOURCE_PREDICTIONS.stat().st_size // PREDICTION_DTYPE.itemsize
    source = np.memmap(
        SOURCE_PREDICTIONS,
        mode="r",
        dtype=PREDICTION_DTYPE,
        shape=(source_count,),
    )
    example_count = EXAMPLES.stat().st_size // EXAMPLE_DTYPE.itemsize
    oof_count = OOF.stat().st_size // OOF_DTYPE.itemsize
    examples = np.memmap(
        EXAMPLES, mode="r", dtype=EXAMPLE_DTYPE, shape=(example_count,)
    )
    oof = np.memmap(OOF, mode="r", dtype=OOF_DTYPE, shape=(oof_count,))
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
    train_mask = oof["fold"] < REPAIRED_FOLD
    validation_mask = oof["fold"] == REPAIRED_FOLD
    basis, training = fit_market_spline_basis(matrix[train_mask])
    validation = basis.transform(matrix[validation_mask])
    repaired, fit = converged_fit(
        training,
        labels[train_mask],
        validation,
        float(selected["c"]),
    )
    if not fit["converged"]:
        raise RuntimeError("fold-4 direct B0-v5N still did not converge")

    source_fold_mask = source["fold"] == REPAIRED_FOLD
    if int(source_fold_mask.sum()) != int(validation_mask.sum()):
        raise RuntimeError("repair fold row-count mismatch")
    for field in ("market", "minute", "fold", "label"):
        if not np.array_equal(source[field][source_fold_mask], oof[field][validation_mask]):
            raise RuntimeError(f"repair fold {field} alignment failure")

    OUTPUT.mkdir(parents=True, exist_ok=True)
    temporary = PREDICTIONS.with_suffix(PREDICTIONS.suffix + ".tmp")
    repaired_rows = np.asarray(source).copy()
    previous = np.asarray(repaired_rows["direct_nonlinear"][source_fold_mask], dtype=np.float64)
    repaired_rows["direct_nonlinear"][source_fold_mask] = repaired
    repaired_rows.tofile(temporary)
    os.replace(temporary, PREDICTIONS)
    rows = np.memmap(PREDICTIONS, mode="r", dtype=PREDICTION_DTYPE, shape=(source_count,))

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
            seed=1701 + offset,
        )
        bootstraps[name]["estimand"] = f"{baseline} minus {candidate} log loss"

    all_prior_other_folds_converged = all(
        fold["final_fit"]["converged"]
        for fold in source_report["folds"]
        if int(fold["fold"]) != REPAIRED_FOLD
    )
    selected_architecture = min(
        ("direct_nonlinear", "stacked_nonlinear"),
        key=lambda name: (aggregate[name]["log_loss"], name),
    )
    report = {
        "experiment_id": "eventx-v5-market-baseline-selection-v2-20260903",
        "created_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "status": "complete",
        "role": "opened historical B0-v5N convergence repair; not confirmation",
        "rows": len(rows),
        "markets": int(len(np.unique(rows["market"]))),
        "selected_opened_development_architecture": selected_architecture,
        "repaired_fold": REPAIRED_FOLD,
        "repaired_fit": fit,
        "prediction_change": {
            "maximum_absolute": float(np.max(np.abs(previous - repaired))),
            "mean_absolute": float(np.mean(np.abs(previous - repaired))),
        },
        "aggregate": aggregate,
        "comparisons": comparisons,
        "paired_bootstraps": bootstraps,
        "market_balanced": {
            name: market_balanced(rows, rows[baseline], rows[candidate])
            for name, (baseline, candidate) in contrast_fields.items()
        },
        "invariants": {
            "future_v4_data_read": False,
            "news_features_used": False,
            "spline_basis_fit_on_training_rows_only": True,
            "selection_uses_opened_development_only": True,
            "all_final_fits_converged": bool(
                fit["converged"] and all_prior_other_folds_converged
            ),
            "source_architecture_run_preserved": True,
        },
        "limitations": [
            "selection uses opened historical outcomes and is not confirmation",
            "only the previously non-converged final fit was repeated",
            "a new label-blind source/cohort/power audit is required before freezing",
        ],
    }
    spec = {
        "design_id": "eventx-b0-v5n-development-candidate-v2-20260903",
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
        "solver": {
            "type": "L2 logistic regression",
            "implementation": "sklearn LogisticRegression lbfgs",
            "max_iter": MAX_ITER,
            "tolerance": TOLERANCE,
            "random_state": 271,
        },
        "regularization_grid": [0.001, 0.01, 0.1],
        "selection_metric": "inner-fold log loss",
        "outer_evaluation_folds": [3, 4, 5],
        "confirmation_status": "requires new untouched interval",
    }
    atomic_json(REPORT, report)
    atomic_json(MODEL_SPEC, spec)
    contrast = comparisons["direct_vs_stacked"]["log_loss_improvement"]
    interval = bootstraps["direct_vs_stacked"]
    SUMMARY.write_text(
        "# EventX B0-v5N convergence-checked architecture\n\n"
        "Opened historical development only; protected v4 future data were not read.\n\n"
        f"- Selected development architecture: `{selected_architecture}`.\n"
        f"- Repaired fold converged in `{fit['iterations']}` iterations.\n"
        f"- Direct versus stacked log-loss improvement: `{contrast:.6f}`.\n"
        f"- Paired interval: `[{interval['ci_95_lower']:.6f}, "
        f"{interval['ci_95_upper']:.6f}]`.\n"
        f"- Maximum repaired prediction change: "
        f"`{report['prediction_change']['maximum_absolute']:.8f}`.\n\n"
        "The direct nonlinear market-only implementation is the B0-v5N development "
        "candidate. It is not yet frozen or confirmed.\n",
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
                )
            ],
            "inputs": [
                {"path": relative(path), "sha256": sha256_file(path)}
                for path in (SOURCE_PREDICTIONS, SOURCE_REPORT, EXAMPLES, OOF, MARKETS)
            ],
        },
    )
    print(
        json.dumps(
            {
                "status": report["status"],
                "selected": selected_architecture,
                "repaired_fit": fit,
                "prediction_change": report["prediction_change"],
                "aggregate": aggregate,
                "comparisons": comparisons,
                "paired_bootstraps": bootstraps,
                "invariants": report["invariants"],
            },
            indent=2,
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
