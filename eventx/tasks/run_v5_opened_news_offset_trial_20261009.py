"""Exploratory news-exposed offset comparison on opened V5 development rows.

Run: .venv/bin/python -m eventx.tasks.run_v5_opened_news_offset_trial_20261009
This is a new diagnostic, not V5-R promotion or a protected evaluation.
"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
from scipy.optimize import minimize
from scipy.special import expit, logit

from eventx.tasks.audit_v5_algorithms import block_interval, recent_news
from eventx.tasks.prepare_v4_discovery_news_quality import EVENT_DTYPE
from eventx.tasks.run_v4_discovery_models import OOF_DTYPE
from eventx.tasks.run_v5_residual_feasibility import (
    EVENT_MANIFEST,
    EVENTS,
    FUTURE,
    OOF,
    OOF_MANIFEST,
    REPO_ROOT,
    metric,
    point_loss,
    sha256_file,
    verify_manifest,
)

PARENT = REPO_ROOT / "data/v5/algorithm_audit_20260907"
OUT = REPO_ROOT / "data/v5/opened_news_offset_trial_20261009"
PENALTY = 0.01
ARMS = {"context": (0,), "timing": (0, 1, 2), "semantic": (0, 1, 2, 3, 4)}
INPUTS = (PARENT / "predictions.npz", PARENT / "report.json", OOF, EVENTS)


def write_json(path: Path, value: dict) -> None:
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(value, indent=2, sort_keys=True, allow_nan=False) + "\n")
    temporary.replace(path)


def fit_offset(x: np.ndarray, y: np.ndarray, baseline: np.ndarray) -> tuple[np.ndarray, dict]:
    """Fit an unpenalized correction intercept and L2-penalized coefficients."""
    if len(np.unique(y)) != 2:
        raise RuntimeError("Exposed training data have only one label class")
    mean = x.mean(axis=0)
    scale = x.std(axis=0)
    scale[scale < 1e-12] = 1.0
    standardized = (x - mean) / scale
    design = np.column_stack((np.ones(len(x)), standardized))
    offset = logit(np.clip(baseline, 1e-7, 1 - 1e-7))

    def objective(beta: np.ndarray) -> tuple[float, np.ndarray]:
        z = offset + design @ beta
        value = np.mean(np.logaddexp(0.0, z) - y * z)
        value += 0.5 * PENALTY * np.dot(beta[1:], beta[1:])
        gradient = design.T @ (expit(z) - y) / len(y)
        gradient[1:] += PENALTY * beta[1:]
        return float(value), gradient

    result = minimize(
        objective,
        np.zeros(design.shape[1]),
        method="L-BFGS-B",
        jac=True,
        options={"maxiter": 2000, "gtol": 1e-7, "ftol": 1e-12},
    )
    if not result.success or not np.all(np.isfinite(result.x)):
        raise RuntimeError(f"Offset fit failed: {result.message}")
    return result.x, {
        "mean": mean.tolist(),
        "scale": scale.tolist(),
        "iterations": int(result.nit),
        "gradient_max_abs": float(np.max(np.abs(result.jac))),
        "training_objective": float(result.fun),
    }


def predict_offset(
    x: np.ndarray, baseline: np.ndarray, beta: np.ndarray, fit: dict
) -> np.ndarray:
    standardized = (x - np.asarray(fit["mean"])) / np.asarray(fit["scale"])
    correction = beta[0] + standardized @ beta[1:]
    return expit(logit(np.clip(baseline, 1e-7, 1 - 1e-7)) + correction)


def main() -> None:
    if OUT.exists():
        raise SystemExit("Preserve existing trial output; create another version")
    for path in (
        FUTURE / "consumption_receipt.json",
        FUTURE / "examples/examples.bin",
        FUTURE / "evaluation/result.json",
    ):
        if path.exists():
            raise SystemExit("Protected V4 artifacts exist; refusing this trial")
    verify_manifest(OOF_MANIFEST)
    verify_manifest(EVENT_MANIFEST)
    verify_manifest(PARENT / "manifest.json")
    OUT.mkdir(parents=True)
    contract = {
        "role": "opened-development exploratory observed-news comparison",
        "not_v5_r_promotion": True,
        "prediction_source": "frozen tree_no_terminal OOF predictions from V5 algorithm audit",
        "source_policy": "Only rows with at least one observed event in (t-30m,t]; no claim that absent events mean zero news",
        "outer_evaluation_folds": [4, 5],
        "training_folds": {"4": [3], "5": [3, 4]},
        "label_horizon_purge_minutes": 30,
        "arms": {key: list(columns) for key, columns in ARMS.items()},
        "columns": ["baseline_logit", "log1p_count", "latest_age_over_30", "max_relevance_novelty", "latest_relevance_novelty"],
        "fit": "fixed-baseline logistic offset on exposed training rows; correction intercept unpenalized, standardized coefficients L2 penalized",
        "l2_penalty": PENALTY,
        "baseline_and_comparisons": ["tree_no_terminal", "context", "timing", "semantic"],
        "interval": "1000 market-cluster resamples, seed 907, descriptive only",
        "known_limits": [
            "Opened outcomes and post-selection diagnostic, not independent confirmation",
            "Full-discovery semantic TF-IDF/SVD used later historical text",
            "Historical news feed completeness and article/market versions uncertified",
            "Market groups do not certify event-family independence",
            "Market-only baseline eligibility may inherit snapshot metadata",
        ],
        "inputs": [{"path": str(p.relative_to(REPO_ROOT)), "sha256": sha256_file(p)} for p in INPUTS],
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    write_json(OUT / "contract.json", contract)

    oof = np.memmap(OOF, mode="r", dtype=OOF_DTYPE)
    events = np.memmap(EVENTS, mode="r", dtype=EVENT_DTYPE)
    selected = np.flatnonzero(oof["fold"] >= 3)
    with np.load(PARENT / "predictions.npz", allow_pickle=False) as frozen:
        rows = {key: frozen[key].copy() for key in ("market", "minute", "fold", "label", "tree_no_terminal")}
    for key in ("market", "minute", "fold", "label"):
        if not np.array_equal(rows[key], oof[key][selected]):
            raise RuntimeError(f"Frozen baseline and OOF row mismatch: {key}")
    news = recent_news(oof, events)[selected]
    exposed = news[:, 0] > 0
    p0 = rows["tree_no_terminal"]
    if not np.all(np.isfinite(p0)) or not np.all((p0 > 0) & (p0 < 1)):
        raise RuntimeError("Invalid baseline probabilities")
    x = np.column_stack((
        logit(p0), np.log1p(news[:, 1]), news[:, 2] / 30.0,
        news[:, 3], news[:, 4],
    ))
    eval_indices = []
    predictions = {"tree_no_terminal": []}
    predictions.update({name: [] for name in ARMS})
    fits = []
    for fold in (4, 5):
        eval_mask = (rows["fold"] == fold) & exposed
        if not np.any(eval_mask):
            raise RuntimeError(f"No exposed evaluation rows in fold {fold}")
        eval_start = int(rows["minute"][eval_mask].min())
        train_mask = (
            (rows["fold"] >= 3) & (rows["fold"] < fold) & exposed
            & (rows["minute"] + 30 < eval_start)
        )
        train = np.flatnonzero(train_mask)
        validation = np.flatnonzero(eval_mask)
        if not len(train) or np.intersect1d(rows["market"][train], rows["market"][validation]).size:
            raise RuntimeError(f"Training/evaluation group gate failed in fold {fold}")
        if rows["minute"][train].max() + 30 >= eval_start:
            raise RuntimeError(f"Label-horizon purge failed in fold {fold}")
        eval_indices.append(validation)
        predictions["tree_no_terminal"].append(p0[validation])
        entry = {
            "fold": fold,
            "training_exposed_rows": len(train),
            "validation_exposed_rows": len(validation),
            "validation_markets": int(np.unique(rows["market"][validation]).size),
            "label_purge_gap_minutes": int(eval_start - rows["minute"][train].max()),
            "arms": {},
        }
        for name, columns in ARMS.items():
            beta, fit = fit_offset(x[train][:, columns], rows["label"][train], p0[train])
            score = predict_offset(x[validation][:, columns], p0[validation], beta, fit)
            if not np.all(np.isfinite(score)):
                raise RuntimeError(f"Nonfinite score: {name}, fold {fold}")
            predictions[name].append(score)
            entry["arms"][name] = {
                "coefficients": beta.tolist(),
                "fit": fit,
                "metrics": metric(rows["label"][validation], score),
            }
        fits.append(entry)
        write_json(OUT / "checkpoint.json", {"completed_folds": fits})
        print(f"Fold {fold} complete: {len(validation)} observed-news rows", flush=True)

    eval_indices = np.concatenate(eval_indices)
    scores = {name: np.concatenate(chunks) for name, chunks in predictions.items()}
    labels = rows["label"][eval_indices]
    metrics = {name: metric(labels, score) for name, score in scores.items()}
    pairs = (
        ("tree_no_terminal", "context"),
        ("context", "timing"),
        ("timing", "semantic"),
        ("tree_no_terminal", "semantic"),
    )
    comparisons = {}
    for baseline, candidate in pairs:
        difference = point_loss(labels, scores[baseline]) - point_loss(labels, scores[candidate])
        comparisons[f"{candidate}_vs_{baseline}"] = {
            "log_loss": block_interval({"market": rows["market"][eval_indices]}, difference),
            "fold_log_loss_improvement": {
                str(fold): float(difference[rows["fold"][eval_indices] == fold].mean())
                for fold in (4, 5)
            },
            "brier_improvement": float(metrics[baseline]["brier"] - metrics[candidate]["brier"]),
            "average_precision_gain": float(metrics[candidate]["average_precision"] - metrics[baseline]["average_precision"]),
        }
    np.savez_compressed(
        OUT / "predictions.npz",
        market=rows["market"][eval_indices], minute=rows["minute"][eval_indices],
        fold=rows["fold"][eval_indices], label=labels, **scores,
    )
    report = {
        "status": "complete",
        "scope": contract["role"],
        "validation_rows_all": int(np.sum(rows["fold"] >= 4)),
        "validation_rows_observed_news": len(eval_indices),
        "validation_markets_observed_news": int(np.unique(rows["market"][eval_indices]).size),
        "metrics": metrics,
        "comparisons": comparisons,
        "folds": fits,
        "protected_outcomes_read": False,
        "source_certification_claim": False,
        "candidate_promotion": False,
    }
    write_json(OUT / "report.json", report)
    artifacts = [OUT / "contract.json", OUT / "report.json", OUT / "predictions.npz", Path(__file__)]
    write_json(OUT / "manifest.json", {"artifacts": [
        {"path": str(p.relative_to(REPO_ROOT)), "sha256": sha256_file(p)} for p in artifacts
    ]})
    print(json.dumps({
        "status": "complete",
        "observed_news_rows": len(eval_indices),
        "metrics": {name: {"log_loss": value["log_loss"], "brier": value["brier"], "average_precision": value["average_precision"]} for name, value in metrics.items()},
        "comparisons": {name: value["log_loss"]["mean"] for name, value in comparisons.items()},
    }, indent=2))


if __name__ == "__main__":
    main()
