"""Run leakage-safe historical feasibility for the EventX v5 residual design.

This is an exploratory development task. It reads only the previously opened v4
discovery interval, never the protected v4 future confirmation. Base probabilities
are generated out of fold; residual models train only on earlier OOF folds.
"""

from __future__ import annotations

import csv
from datetime import datetime, timezone
import json
import os
from pathlib import Path
from typing import Any, Iterator

import numpy as np
from sklearn.linear_model import SGDClassifier
from sklearn.metrics import average_precision_score, roc_auc_score
from sklearn.preprocessing import SplineTransformer, StandardScaler

from eventx.features.v4_news import MINUTE_US
from eventx.features.v5_residual import (
    gated_residual_probability,
    logit,
    online_story_stages,
)
from eventx.settings import REPO_ROOT
from eventx.tasks.build_v4_discovery_examples import EXAMPLE_DTYPE
from eventx.tasks.evaluate_v4_confirmatory import two_level_bootstrap
from eventx.tasks.prepare_v3_1_historical_development_arrays import sha256_file
from eventx.tasks.prepare_v4_discovery_news_quality import (
    EVENT_DTYPE,
    load_documents,
)
from eventx.tasks.run_v4_discovery_models import FOLDS, OOF_DTYPE
from eventx.tasks.run_v4_exploratory_novelty_diffusion import reconstruct_oof_indices


EXAMPLES = REPO_ROOT / "data/v4/discovery/examples/examples.bin"
EXAMPLES_MANIFEST = REPO_ROOT / "data/v4/discovery/examples/manifest.json"
OOF = REPO_ROOT / "data/v4/discovery/models/oof_predictions.bin"
OOF_MANIFEST = REPO_ROOT / "data/v4/discovery/models/manifest.json"
EVENTS = REPO_ROOT / "data/v4/discovery/prepared/news_quality_events.bin"
EVENT_MANIFEST = REPO_ROOT / "data/v4/discovery/prepared/manifest.json"
MARKETS = REPO_ROOT / "data/v3_1_historical/primary/development/prepared/market_index.jsonl"
FUTURE = REPO_ROOT / "data/v4/confirmatory"
OUTPUT = REPO_ROOT / "data/v5/development/residual_feasibility"
PREDICTIONS = OUTPUT / "predictions.bin"
REPORT = OUTPUT / "report.json"
CALIBRATION = OUTPUT / "correction_calibration.csv"
SUBGROUPS = OUTPUT / "subgroups.csv"
SUMMARY = OUTPUT / "SUMMARY.md"
MANIFEST = OUTPUT / "manifest.json"
START = datetime(2026, 5, 17, tzinfo=timezone.utc)
START_US = int(START.timestamp() * 1_000_000)
BATCH_ROWS = 65_536
BASE_EPOCHS = 8
BASE_SEED = 73
RESIDUAL_SEED = 173
SHRINKAGE_GRID = (0.0, 0.1, 0.25, 0.5, 0.75, 1.0)
LINEAR_CONFIGS = (
    (1e-5, 0.9),
    (1e-4, 0.5),
    (1e-4, 0.9),
    (1e-3, 0.9),
)
SPLINE_CONFIGS = ((1e-4, 0.9), (1e-3, 0.9))
V4_LOG_COLUMNS = (6, 7, 8, 9)
SPLINE_COLUMNS = np.asarray(
    [16, 21, 22, 23, 24, 25, 26, 27, 28, 29, 38, 39, 40, 41,
     42, 43, 44, 45, 50, 51, 52],
    dtype=np.int64,
)
PREDICTION_DTYPE = np.dtype(
    [
        ("market", "<u4"),
        ("minute", "<i4"),
        ("venue", "u1"),
        ("fold", "u1"),
        ("label", "u1"),
        ("exposed", "u1"),
        ("b0_v4", "<f4"),
        ("b0_v5", "<f4"),
        ("v5_a", "<f4"),
        ("v5_b", "<f4"),
    ],
    align=False,
)


def relative(path: Path) -> str:
    return str(path.relative_to(REPO_ROOT))


def read_jsonl(path: Path) -> Iterator[dict[str, Any]]:
    with path.open(encoding="utf-8") as handle:
        for line in handle:
            if line.strip():
                yield json.loads(line)


def atomic_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n")
    os.replace(temporary, path)


def atomic_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    if not rows:
        raise ValueError(f"empty CSV: {path}")
    fields = list(dict.fromkeys(key for row in rows for key in row))
    temporary = path.with_suffix(path.suffix + ".tmp")
    with temporary.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)
    os.replace(temporary, path)


def verify_manifest(path: Path) -> None:
    manifest = json.loads(path.read_text(encoding="utf-8"))
    for artifact in manifest.get("artifacts", []):
        target = REPO_ROOT / str(artifact["path"])
        if not target.is_file() or sha256_file(target) != str(artifact["sha256"]):
            raise RuntimeError(f"hash-lock failure: {target}")


def parse_utc(value: str) -> datetime:
    return datetime.fromisoformat(str(value).replace("Z", "+00:00")).astimezone(
        timezone.utc
    )


def terminal_metadata(markets: list[dict[str, Any]]) -> tuple[np.ndarray, np.ndarray]:
    terminal_minutes = np.zeros(len(markets), dtype=np.float64)
    known = np.zeros(len(markets), dtype=bool)
    for index, market in enumerate(markets):
        if int(market["market_index"]) != index:
            raise RuntimeError("market index is not deterministic")
        terminal = market.get("terminal_time")
        if not terminal:
            continue
        terminal_time = parse_utc(str(terminal))
        if terminal_time < parse_utc(str(market["first_trade_ts"])):
            continue
        terminal_minutes[index] = (terminal_time - START).total_seconds() / 60.0
        known[index] = True
    return terminal_minutes, known


def base_values(
    examples: np.ndarray,
    indices: np.ndarray,
    terminal_minutes: np.ndarray,
    terminal_known: np.ndarray,
) -> np.ndarray:
    values = np.asarray(examples["features"][indices, :12], dtype=np.float64).copy()
    for column in V4_LOG_COLUMNS:
        values[:, column] = np.log1p(np.maximum(values[:, column], 0.0))
    market = np.asarray(examples["market"][indices], dtype=np.int64)
    known = terminal_known[market]
    remaining = np.maximum(
        terminal_minutes[market] - np.asarray(examples["minute"][indices]), 0.0
    )
    remaining[~known] = 0.0
    return np.column_stack((values, np.log1p(remaining), (~known).astype(np.float64)))


def base_scaler(
    examples: np.ndarray,
    indices: np.ndarray,
    terminal_minutes: np.ndarray,
    terminal_known: np.ndarray,
) -> tuple[np.ndarray, np.ndarray]:
    total = np.zeros(14, dtype=np.float64)
    total_sq = np.zeros(14, dtype=np.float64)
    rows = 0
    for start in range(0, len(indices), BATCH_ROWS):
        values = base_values(
            examples,
            indices[start : start + BATCH_ROWS],
            terminal_minutes,
            terminal_known,
        )
        total += values.sum(axis=0, dtype=np.float64)
        total_sq += np.square(values).sum(axis=0, dtype=np.float64)
        rows += len(values)
    means = total / rows
    scales = np.sqrt(np.maximum(0.0, total_sq / rows - means * means))
    scales[scales == 0.0] = 1.0
    return means, scales


def fit_base(
    examples: np.ndarray,
    train: np.ndarray,
    validation: np.ndarray,
    terminal_minutes: np.ndarray,
    terminal_known: np.ndarray,
    fold: int,
) -> tuple[np.ndarray, dict[str, Any]]:
    means, scales = base_scaler(
        examples, train, terminal_minutes, terminal_known
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
            values = (
                base_values(examples, chosen, terminal_minutes, terminal_known) - means
            ) / scales
            model.partial_fit(
                values,
                np.asarray(examples["label"][chosen], dtype=np.uint8),
                classes=np.asarray([0, 1], dtype=np.uint8) if first else None,
            )
            first = False
        print(f"v5 base fold {fold}: epoch {epoch + 1}/{BASE_EPOCHS}", flush=True)
    predictions = np.empty(len(validation), dtype=np.float64)
    for start in range(0, len(validation), BATCH_ROWS):
        chosen = validation[start : start + BATCH_ROWS]
        values = (
            base_values(examples, chosen, terminal_minutes, terminal_known) - means
        ) / scales
        predictions[start : start + len(chosen)] = model.predict_proba(values)[:, 1]
    return predictions, {
        "train_rows": len(train),
        "validation_rows": len(validation),
        "epochs": BASE_EPOCHS,
        "seed": BASE_SEED,
        "coefficient_l2_norm": float(np.linalg.norm(model.coef_)),
    }


def build_rich_news_features(
    oof: np.ndarray,
    v4_features: np.ndarray,
    events: np.ndarray,
    document_stages: np.ndarray,
) -> tuple[np.ndarray, np.ndarray, list[str]]:
    names = [f"log1p_v4_news_{index}" for index in range(16)]
    names.extend(
        [
            "log1p_latest_age",
            "age_0_30m",
            "age_30_120m",
            "age_120_360m",
            "age_360_1440m",
            "latest_relevance",
            "latest_novelty",
            "latest_relevance_novelty",
            "max_relevance_60m",
            "max_relevance_360m",
            "max_relevance_1440m",
            "max_relevance_novelty_60m",
            "max_relevance_novelty_360m",
            "max_relevance_novelty_1440m",
            "latest_stage_new",
            "latest_stage_preconfirmation_repeat",
            "latest_stage_first_cross_publisher",
            "latest_stage_postconfirmation_repeat",
            "log1p_new_story_count_1440m",
            "log1p_preconfirmation_repeat_count_1440m",
            "log1p_first_cross_publisher_count_1440m",
            "log1p_postconfirmation_repeat_count_1440m",
            "decay_relevance_half_life_30m",
            "decay_relevance_half_life_120m",
            "decay_relevance_novelty_half_life_30m",
            "decay_relevance_novelty_half_life_120m",
        ]
    )
    output = np.zeros((len(oof), len(names)), dtype=np.float32)
    output[:, :16] = np.log1p(np.maximum(v4_features[:, 12:28], 0.0))
    exposed = np.asarray(v4_features[:, 14] > 0, dtype=bool)
    order = np.argsort(oof["market"], kind="stable")
    ordered_market = np.asarray(oof["market"][order], dtype=np.uint32)
    boundaries = np.concatenate(
        ([0], np.flatnonzero(np.diff(ordered_market)) + 1, [len(order)])
    )
    maximum_market = int(max(oof["market"].max(), events["market"].max()))
    event_offsets = np.searchsorted(
        events["market"], np.arange(maximum_market + 2, dtype=np.uint32), side="left"
    )
    for number, (left, right) in enumerate(zip(boundaries[:-1], boundaries[1:]), 1):
        rows = order[left:right]
        market = int(ordered_market[left])
        grid = START_US + np.asarray(oof["minute"][rows], dtype=np.int64) * MINUTE_US
        market_events = events[event_offsets[market] : event_offsets[market + 1]]
        if not len(market_events):
            continue
        times = np.asarray(market_events["timestamp_us"], dtype=np.int64)
        relevance = np.asarray(market_events["relevance"], dtype=np.float64)
        novelty = np.asarray(market_events["novelty"], dtype=np.float64)
        product = relevance * novelty
        stages = document_stages[np.asarray(market_events["document"], dtype=np.int64)]
        rights = np.searchsorted(times, grid, side="right")
        lefts_1440 = np.searchsorted(times, grid - 1440 * MINUTE_US, side="right")
        for local, row in enumerate(rows):
            stop = int(rights[local])
            start_1440 = int(lefts_1440[local])
            if stop <= start_1440:
                continue
            latest = stop - 1
            age = (int(grid[local]) - int(times[latest])) / MINUTE_US
            output[row, 16] = np.log1p(max(age, 0.0))
            output[row, 17:21] = (
                age <= 30,
                30 < age <= 120,
                120 < age <= 360,
                360 < age < 1440,
            )
            output[row, 21:24] = (
                relevance[latest],
                novelty[latest],
                product[latest],
            )
            for window_number, window in enumerate((60, 360, 1440)):
                start = int(
                    np.searchsorted(
                        times,
                        int(grid[local]) - window * MINUTE_US,
                        side="right",
                    )
                )
                if stop > start:
                    output[row, 24 + window_number] = float(
                        np.max(relevance[start:stop])
                    )
                    output[row, 27 + window_number] = float(
                        np.max(product[start:stop])
                    )
            stage = int(stages[latest])
            if 1 <= stage <= 4:
                output[row, 30 + stage - 1] = 1.0
            window_stages = stages[start_1440:stop]
            for stage_value in range(1, 5):
                output[row, 34 + stage_value - 1] = np.log1p(
                    np.sum(window_stages == stage_value)
                )
            ages = (int(grid[local]) - times[start_1440:stop]) / MINUTE_US
            for offset, half_life in enumerate((30.0, 120.0)):
                weights = np.exp(-np.log(2.0) * ages / half_life)
                output[row, 38 + offset] = float(
                    np.sum(weights * relevance[start_1440:stop])
                )
                output[row, 40 + offset] = float(
                    np.sum(weights * product[start_1440:stop])
                )
        if number % 300 == 0:
            print(
                f"v5 rich features: {number}/{len(boundaries) - 1} markets",
                flush=True,
            )
    if not np.array_equal(exposed, output[:, 0 + 2] > 0):
        # V4 column 14 is the 1,440-minute article count, which maps to local index 2.
        raise RuntimeError("v5 exposure gate differs from v4 point-in-time count")
    if not np.all(np.isfinite(output)):
        raise RuntimeError("nonfinite v5 rich feature")
    return output, exposed, names


def residual_matrix(
    rich: np.ndarray,
    oof_features: np.ndarray,
    oof_indices: np.ndarray,
    examples: np.ndarray,
    p0: np.ndarray,
    terminal_minutes: np.ndarray,
    terminal_known: np.ndarray,
) -> tuple[np.ndarray, list[str]]:
    market = np.asarray(examples["market"][oof_indices], dtype=np.int64)
    known = terminal_known[market]
    remaining = np.maximum(
        terminal_minutes[market] - np.asarray(examples["minute"][oof_indices]), 0.0
    )
    remaining[~known] = 0.0
    context = np.column_stack(
        (
            logit(p0),
            p0,
            oof_features[:, 4],
            oof_features[:, 5],
            np.log1p(np.maximum(oof_features[:, 6], 0.0)),
            np.log1p(np.maximum(oof_features[:, 7], 0.0)),
            np.log1p(np.maximum(oof_features[:, 8], 0.0)),
            np.log1p(np.maximum(oof_features[:, 9], 0.0)),
            np.log1p(np.maximum(oof_features[:, 10], 0.0)),
            np.asarray(examples["price_age"][oof_indices], dtype=np.float64),
            np.log1p(remaining),
            (~known).astype(np.float64),
        )
    ).astype(np.float32)
    names = [
        "b0_v5_logit",
        "b0_v5_probability",
        "realized_vol_30m",
        "realized_vol_240m",
        "log1p_trade_count_60m",
        "log1p_trade_count_240m",
        "log1p_notional_60m",
        "log1p_notional_240m",
        "log1p_minutes_since_trade",
        "price_age_minutes",
        "log1p_minutes_to_terminal",
        "terminal_unknown",
    ]
    return np.column_stack((rich, context)).astype(np.float32), names


def candidate_values(
    train: np.ndarray,
    other: np.ndarray,
    spline: bool,
) -> tuple[np.ndarray, np.ndarray, dict[str, Any]]:
    if not spline:
        return train, other, {"transform": "linear"}
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
        {
            "transform": "quadratic_spline",
            "spline_input_columns": SPLINE_COLUMNS.tolist(),
            "output_width": int(train_spline.shape[1] + keep.sum()),
        },
    )


def fit_residual(
    train: np.ndarray,
    labels: np.ndarray,
    other: np.ndarray,
    alpha: float,
    l1_ratio: float,
) -> tuple[np.ndarray, dict[str, Any]]:
    scaler = StandardScaler()
    train_scaled = scaler.fit_transform(train)
    other_scaled = scaler.transform(other)
    model = SGDClassifier(
        loss="log_loss",
        penalty="elasticnet",
        alpha=float(alpha),
        l1_ratio=float(l1_ratio),
        fit_intercept=True,
        max_iter=40,
        tol=1e-4,
        n_iter_no_change=5,
        shuffle=True,
        learning_rate="optimal",
        average=True,
        random_state=RESIDUAL_SEED,
    )
    model.fit(train_scaled, labels)
    decision = np.asarray(model.decision_function(other_scaled), dtype=np.float64)
    return decision, {
        "alpha": float(alpha),
        "l1_ratio": float(l1_ratio),
        "iterations": int(model.n_iter_),
        "nonzero_coefficients": int(np.sum(np.abs(model.coef_) > 1e-12)),
        "coefficient_l2_norm": float(np.linalg.norm(model.coef_)),
    }


def point_loss(labels: np.ndarray, scores: np.ndarray) -> np.ndarray:
    values = np.clip(np.asarray(scores, dtype=np.float64), 1e-7, 1 - 1e-7)
    targets = np.asarray(labels, dtype=np.float64)
    return -targets * np.log(values) - (1 - targets) * np.log(1 - values)


def metric(labels: np.ndarray, scores: np.ndarray) -> dict[str, Any]:
    labels = np.asarray(labels, dtype=np.uint8)
    scores = np.clip(np.asarray(scores, dtype=np.float64), 1e-7, 1 - 1e-7)
    positives = int(labels.sum())
    return {
        "rows": len(labels),
        "positives": positives,
        "prevalence": float(labels.mean()),
        "mean_prediction": float(scores.mean()),
        "log_loss": float(point_loss(labels, scores).mean()),
        "brier": float(np.mean(np.square(labels - scores))),
        "average_precision": (
            float(average_precision_score(labels, scores)) if positives else None
        ),
        "roc_auc": (
            float(roc_auc_score(labels, scores))
            if len(np.unique(labels)) == 2
            else None
        ),
    }


def compare(
    labels: np.ndarray, baseline: np.ndarray, candidate: np.ndarray
) -> dict[str, Any]:
    left = metric(labels, baseline)
    right = metric(labels, candidate)
    return {
        "log_loss_improvement": float(left["log_loss"] - right["log_loss"]),
        "brier_improvement": float(left["brier"] - right["brier"]),
        "delta_average_precision": (
            float(right["average_precision"] - left["average_precision"])
            if left["average_precision"] is not None
            and right["average_precision"] is not None
            else None
        ),
    }


def select_candidate(
    matrix: np.ndarray,
    labels: np.ndarray,
    p0: np.ndarray,
    exposed: np.ndarray,
    train_mask: np.ndarray,
    tune_mask: np.ndarray,
    configs: tuple[tuple[float, float], ...],
    spline: bool,
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    train = train_mask & exposed
    tune = tune_mask & exposed
    train_values, tune_values, transform = candidate_values(
        matrix[train], matrix[tune], spline
    )
    trials = []
    for alpha, l1_ratio in configs:
        decision, model_info = fit_residual(
            train_values, labels[train], tune_values, alpha, l1_ratio
        )
        raw_correction = decision - logit(p0[tune])
        for shrinkage in SHRINKAGE_GRID:
            predictions = gated_residual_probability(
                p0[tune], np.ones(int(tune.sum()), dtype=bool), raw_correction, shrinkage
            )
            trials.append(
                {
                    **model_info,
                    **transform,
                    "shrinkage": shrinkage,
                    "tuning_rows": int(tune.sum()),
                    "tuning_log_loss": metric(labels[tune], predictions)["log_loss"],
                    "tuning_improvement": compare(
                        labels[tune], p0[tune], predictions
                    )["log_loss_improvement"],
                }
            )
    trials.sort(
        key=lambda row: (
            float(row["tuning_log_loss"]),
            float(row["shrinkage"]),
            float(row["alpha"]),
            float(row["l1_ratio"]),
        )
    )
    return trials[0], trials


def refit_candidate(
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
    decision, model_info = fit_residual(
        train_values,
        labels[train],
        validation_values,
        float(selected["alpha"]),
        float(selected["l1_ratio"]),
    )
    corrections = np.zeros(int(validation_mask.sum()), dtype=np.float64)
    local_exposure = exposed[validation_mask]
    corrections[local_exposure] = decision - logit(p0[validation])
    predictions = gated_residual_probability(
        p0[validation_mask],
        local_exposure,
        corrections,
        float(selected["shrinkage"]),
    )
    return predictions, {
        **model_info,
        **transform,
        "shrinkage": float(selected["shrinkage"]),
        "train_exposed_rows": int(train.sum()),
        "validation_exposed_rows": int(validation.sum()),
    }


def market_balanced(
    rows: np.ndarray, baseline: np.ndarray, candidate: np.ndarray
) -> dict[str, Any]:
    labels = np.asarray(rows["label"], dtype=np.uint8)
    improvement = point_loss(labels, baseline) - point_loss(labels, candidate)
    values = []
    for market in np.unique(rows["market"]):
        values.append(float(np.mean(improvement[rows["market"] == market])))
    return {
        "markets": len(values),
        "mean_market_log_loss_improvement": float(np.mean(values)),
        "median_market_log_loss_improvement": float(np.median(values)),
        "markets_positive": int(np.sum(np.asarray(values) > 0)),
    }


def correction_calibration(rows: np.ndarray, name: str) -> list[dict[str, Any]]:
    exposed = rows["exposed"] == 1
    base = np.asarray(rows["b0_v5"][exposed], dtype=np.float64)
    candidate = np.asarray(rows[name][exposed], dtype=np.float64)
    labels = np.asarray(rows["label"][exposed], dtype=np.uint8)
    correction = logit(candidate) - logit(base)
    edges = np.quantile(correction, np.linspace(0, 1, 11))
    output = []
    for index in range(10):
        mask = (correction >= edges[index]) & (
            correction <= edges[index + 1]
            if index == 9
            else correction < edges[index + 1]
        )
        if not np.any(mask):
            continue
        output.append(
            {
                "candidate": name,
                "decile": index + 1,
                "lower": float(edges[index]),
                "upper": float(edges[index + 1]),
                "rows": int(mask.sum()),
                "markets": int(len(np.unique(rows["market"][exposed][mask]))),
                "mean_correction": float(correction[mask].mean()),
                "mean_b0_v5": float(base[mask].mean()),
                "mean_candidate": float(candidate[mask].mean()),
                "observed_rate": float(labels[mask].mean()),
                "log_loss_improvement": compare(
                    labels[mask], base[mask], candidate[mask]
                )["log_loss_improvement"],
            }
        )
    return output


def main() -> None:
    outputs = (PREDICTIONS, REPORT, CALIBRATION, SUBGROUPS, SUMMARY, MANIFEST)
    if any(path.exists() for path in outputs):
        raise SystemExit("v5 residual-feasibility artifact already exists")
    forbidden = (
        FUTURE / "consumption_receipt.json",
        FUTURE / "examples/examples.bin",
        FUTURE / "evaluation/result.json",
    )
    if any(path.exists() for path in forbidden):
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

    base_predictions = np.empty(len(oof), dtype=np.float64)
    base_folds = []
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
        expected = np.flatnonzero(oof["fold"] == fold)
        if not np.array_equal(validation, oof_indices[expected]):
            raise RuntimeError(f"base fold {fold} OOF alignment failure")
        predicted, info = fit_base(
            examples,
            train,
            validation,
            terminal_minutes,
            terminal_known,
            fold,
        )
        base_predictions[expected] = predicted
        base_folds.append({"fold": fold, **info})

    documents, _document_stats = load_documents()
    document_times = np.asarray(
        [int(row["available_at"].timestamp() * 1_000_000) for row in documents],
        dtype=np.int64,
    )
    stages = online_story_stages(
        document_times,
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
        base_predictions,
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
            fold_predictions: dict[str, np.ndarray] = {}
            selected_models = {}
            trial_counts = {}
            for name, configs, spline in (
                ("v5_a", LINEAR_CONFIGS, False),
                ("v5_b", SPLINE_CONFIGS, True),
            ):
                selected, trials = select_candidate(
                    matrix,
                    labels,
                    base_predictions,
                    exposed,
                    inner_train,
                    inner_tune,
                    configs,
                    spline,
                )
                predicted, refit = refit_candidate(
                    matrix,
                    labels,
                    base_predictions,
                    exposed,
                    outer_train,
                    outer_validation,
                    selected,
                    spline,
                )
                fold_predictions[name] = predicted
                selected_models[name] = {"selected": selected, "refit": refit}
                trial_counts[name] = len(trials)

            selected_rows = np.flatnonzero(outer_validation)
            rows = np.empty(len(selected_rows), dtype=PREDICTION_DTYPE)
            for field in ("market", "minute", "venue", "fold", "label"):
                rows[field] = oof[field][selected_rows]
            rows["exposed"] = exposed[selected_rows]
            rows["b0_v4"] = oof["b0"][selected_rows]
            rows["b0_v5"] = base_predictions[selected_rows]
            rows["v5_a"] = fold_predictions["v5_a"]
            rows["v5_b"] = fold_predictions["v5_b"]
            for name in ("v5_a", "v5_b"):
                if not np.array_equal(
                    rows[name][rows["exposed"] == 0],
                    rows["b0_v5"][rows["exposed"] == 0],
                ):
                    raise RuntimeError(f"{name} no-news equality invariant failed")
            rows.tofile(handle)
            fold_reports.append(
                {
                    "fold": fold,
                    "meta_train_folds": list(range(1, fold)),
                    "inner_tuning_fold": fold - 1,
                    "validation_rows": len(rows),
                    "validation_exposed_rows": int(rows["exposed"].sum()),
                    "selected_models": selected_models,
                    "trial_counts": trial_counts,
                    "b0_v5": metric(rows["label"], rows["b0_v5"]),
                    "v5_a": metric(rows["label"], rows["v5_a"]),
                    "v5_b": metric(rows["label"], rows["v5_b"]),
                    "v5_a_vs_b0_v5": compare(
                        rows["label"], rows["b0_v5"], rows["v5_a"]
                    ),
                    "v5_b_vs_b0_v5": compare(
                        rows["label"], rows["b0_v5"], rows["v5_b"]
                    ),
                }
            )
            print(f"v5 residual fold {fold}/5 complete", flush=True)
    os.replace(temporary, PREDICTIONS)

    row_count = PREDICTIONS.stat().st_size // PREDICTION_DTYPE.itemsize
    rows = np.memmap(
        PREDICTIONS, mode="r", dtype=PREDICTION_DTYPE, shape=(row_count,)
    )
    aggregate = {
        "b0_v4": metric(rows["label"], rows["b0_v4"]),
        "b0_v5": metric(rows["label"], rows["b0_v5"]),
        "b0_v5_vs_b0_v4": compare(
            rows["label"], rows["b0_v4"], rows["b0_v5"]
        ),
    }
    bootstraps = {}
    market_results = {}
    for offset, name in enumerate(("v5_a", "v5_b")):
        aggregate[name] = metric(rows["label"], rows[name])
        aggregate[f"{name}_vs_b0_v5"] = compare(
            rows["label"], rows["b0_v5"], rows[name]
        )
        exposed_rows = rows["exposed"] == 1
        aggregate[f"{name}_vs_b0_v5_exposed"] = compare(
            rows["label"][exposed_rows],
            rows["b0_v5"][exposed_rows],
            rows[name][exposed_rows],
        )
        difference = point_loss(rows["label"], rows["b0_v5"]) - point_loss(
            rows["label"], rows[name]
        )
        bootstraps[name] = two_level_bootstrap(
            np.asarray(rows["market"]),
            np.asarray(rows["minute"]),
            difference,
            samples=2000,
            seed=931 + offset,
        )
        bootstraps[name]["estimand"] = f"B0-v5 minus {name} log loss"
        market_results[name] = market_balanced(
            rows, rows["b0_v5"], rows[name]
        )

    categories = np.asarray(
        [str(markets[int(index)]["category"]) for index in rows["market"]],
        dtype=object,
    )
    venues = np.asarray(
        [str(markets[int(index)]["venue"]) for index in rows["market"]],
        dtype=object,
    )
    subgroup_rows = []
    for dimension, values in (("category", categories), ("venue", venues)):
        for value in sorted(set(values.tolist())):
            mask = values == value
            market_count = len(np.unique(rows["market"][mask]))
            if market_count < 30:
                continue
            for name in ("v5_a", "v5_b"):
                subgroup_rows.append(
                    {
                        "dimension": dimension,
                        "value": value,
                        "candidate": name,
                        "rows": int(mask.sum()),
                        "markets": int(market_count),
                        **compare(
                            rows["label"][mask],
                            rows["b0_v5"][mask],
                            rows[name][mask],
                        ),
                    }
                )
    calibration_rows = []
    for name in ("v5_a", "v5_b"):
        calibration_rows.extend(correction_calibration(rows, name))
    atomic_csv(CALIBRATION, calibration_rows)
    atomic_csv(SUBGROUPS, subgroup_rows)

    unexposed = rows["exposed"] == 0
    invariants = {
        "v5_a_no_news_max_absolute_difference": float(
            np.max(np.abs(rows["v5_a"][unexposed] - rows["b0_v5"][unexposed]))
        ),
        "v5_b_no_news_max_absolute_difference": float(
            np.max(np.abs(rows["v5_b"][unexposed] - rows["b0_v5"][unexposed]))
        ),
        "sequential_meta_training": True,
        "base_probabilities_out_of_fold": True,
        "future_v4_data_read": False,
    }
    report = {
        "experiment_id": "eventx-v5-residual-historical-feasibility-20260903",
        "created_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "status": "complete",
        "role": "opened historical development feasibility; not v5 confirmation",
        "future_v4_data_read": False,
        "frozen_v4_changed": False,
        "evaluated_folds": [3, 4, 5],
        "excluded_from_residual_evaluation": (
            "folds 1-2 supply strictly earlier cross-fitted meta-training/tuning data"
        ),
        "rows": len(rows),
        "markets": int(len(np.unique(rows["market"]))),
        "news_exposed_rows": int(rows["exposed"].sum()),
        "news_exposed_markets": int(
            len(np.unique(rows["market"][rows["exposed"] == 1]))
        ),
        "base_model": {
            "features": [
                "v4 B0 features",
                "log1p_minutes_to_scheduled_terminal",
                "terminal_unknown",
            ],
            "learner": "averaged optimal-learning-rate logistic SGD",
            "alpha": 1e-4,
            "folds": base_folds,
        },
        "residual_features": rich_names + context_names,
        "candidate_definitions": {
            "v5_a": "gated linear elastic-net residual with nested shrinkage",
            "v5_b": "gated quadratic-spline elastic-net residual with nested shrinkage",
        },
        "folds": fold_reports,
        "aggregate": aggregate,
        "paired_bootstraps": bootstraps,
        "market_balanced": market_results,
        "invariants": invariants,
        "subgroup_policy": (
            "descriptive only; emitted for groups with at least 30 independent markets"
        ),
        "limitations": [
            "feature and model choices were motivated by opened historical outcomes",
            "only folds 3-5 support strictly earlier residual meta-training and evaluation",
            "one base and residual seed; not a frozen deployment bundle",
            "exact-headline cross-publisher states do not establish editorial independence",
            "a new untouched interval is required for any confirmatory v5 claim",
        ],
    }
    atomic_json(REPORT, report)
    SUMMARY.write_text(
        "# EventX v5 gated residual historical feasibility\n\n"
        "Opened historical development analysis only; v4 future data were not read.\n\n"
        f"- Evaluation rows (folds 3–5): {len(rows):,}; news-exposed: "
        f"{int(rows['exposed'].sum()):,}.\n"
        f"- B0-v5 versus B0-v4 log-loss improvement: "
        f"`{aggregate['b0_v5_vs_b0_v4']['log_loss_improvement']:.6f}`.\n"
        f"- V5-A versus B0-v5 log-loss improvement: "
        f"`{aggregate['v5_a_vs_b0_v5']['log_loss_improvement']:.6f}`.\n"
        f"- V5-B versus B0-v5 log-loss improvement: "
        f"`{aggregate['v5_b_vs_b0_v5']['log_loss_improvement']:.6f}`.\n"
        f"- V5-A bootstrap interval: "
        f"`[{bootstraps['v5_a']['ci_95_lower']:.6f}, {bootstraps['v5_a']['ci_95_upper']:.6f}]`.\n"
        f"- V5-B bootstrap interval: "
        f"`[{bootstraps['v5_b']['ci_95_lower']:.6f}, {bootstraps['v5_b']['ci_95_upper']:.6f}]`.\n\n"
        "No-news predictions equal B0-v5 exactly. These results may guide a separate "
        "v5 protocol but cannot confirm it.\n",
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
                    CALIBRATION,
                    SUBGROUPS,
                    SUMMARY,
                    Path(__file__).resolve(),
                    REPO_ROOT / "eventx/features/v5_residual.py",
                    REPO_ROOT / "eventx/tasks/test_v5_residual_architecture.py",
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
                "rows": report["rows"],
                "news_exposed_rows": report["news_exposed_rows"],
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
