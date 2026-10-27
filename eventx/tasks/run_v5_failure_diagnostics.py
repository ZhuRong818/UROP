"""Diagnose the historical v4 news-correction failure before specifying v5.

Only previously opened discovery inputs are used. Future v4 inputs are forbidden.
"""

from __future__ import annotations

from collections import Counter, deque
import csv
from datetime import datetime, timezone
import json
import os
from pathlib import Path
from typing import Any, Iterator

import numpy as np

from eventx.features.v4_news import MINUTE_US, normalized_headline
from eventx.settings import REPO_ROOT
from eventx.tasks.build_v4_discovery_examples import EXAMPLE_DTYPE
from eventx.tasks.prepare_v3_1_historical_development_arrays import TRADE_DTYPE, sha256_file
from eventx.tasks.prepare_v4_discovery_news_quality import EVENT_DTYPE, load_documents
from eventx.tasks.run_v4_discovery_models import OOF_DTYPE
from eventx.tasks.run_v4_exploratory_novelty_diffusion import (
    comparison,
    loss,
    reconstruct_oof_indices,
)


EXAMPLES = REPO_ROOT / "data/v4/discovery/examples/examples.bin"
EXAMPLES_MANIFEST = REPO_ROOT / "data/v4/discovery/examples/manifest.json"
OOF = REPO_ROOT / "data/v4/discovery/models/oof_predictions.bin"
MODEL_MANIFEST = REPO_ROOT / "data/v4/discovery/models/manifest.json"
EVENTS = REPO_ROOT / "data/v4/discovery/prepared/news_quality_events.bin"
TRADES = REPO_ROOT / "data/v3_1_historical/primary/development/prepared/trades.bin"
MARKETS = REPO_ROOT / "data/v3_1_historical/primary/development/prepared/market_index.jsonl"
FUTURE = REPO_ROOT / "data/v4/confirmatory"
OUTPUT = REPO_ROOT / "data/v5/design_diagnostics/failure_modes"
REPORT = OUTPUT / "report.json"
AGE_CSV = OUTPUT / "news_age.csv"
LIFECYCLE_CSV = OUTPUT / "story_lifecycle.csv"
CORRECTION_CSV = OUTPUT / "correction_calibration.csv"
CONTEXT_CSV = OUTPUT / "context_results.csv"
TRADE_CSV = OUTPUT / "trade_arrival.csv"
SUMMARY = OUTPUT / "SUMMARY.md"
MANIFEST = OUTPUT / "manifest.json"
DEVELOPMENT_START_US = int(datetime(2026, 5, 17, tzinfo=timezone.utc).timestamp() * 1_000_000)
HORIZON_US = 30 * MINUTE_US
WINDOW_US = 1440 * MINUTE_US
STAGE_NAMES = {
    0: "no_news",
    1: "new_story_first_report",
    2: "repeat_before_cross_publisher_confirmation",
    3: "first_cross_publisher_confirmation",
    4: "post_confirmation_repetition",
}


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
        raise ValueError(f"empty output table: {path}")
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


def story_stages(documents: list[dict[str, Any]]) -> tuple[np.ndarray, dict[str, Any]]:
    stages = np.zeros(len(documents), dtype=np.uint8)
    histories: dict[str, deque[tuple[int, str]]] = {}
    publisher_counts: dict[str, Counter[str]] = {}
    story_keys: set[str] = set()
    counts = {name: 0 for name in STAGE_NAMES.values() if name != "no_news"}
    for index, document in enumerate(documents):
        key = normalized_headline(str(document["headline"]))
        if len(key) < 20:
            key = f"short:{index}"
        story_keys.add(key)
        publisher = str(document["publisher"])
        timestamp = int(document["available_at"].timestamp() * 1_000_000)
        history = histories.setdefault(key, deque())
        publishers = publisher_counts.setdefault(key, Counter())
        cutoff = timestamp - WINDOW_US
        while history and history[0][0] <= cutoff:
            _expired_time, expired_publisher = history.popleft()
            publishers[expired_publisher] -= 1
            if publishers[expired_publisher] <= 0:
                del publishers[expired_publisher]
        before = len(publishers)
        if not history:
            stage = 1
        elif before < 2 and publisher in publishers:
            stage = 2
        elif before == 1 and publisher not in publishers:
            stage = 3
        else:
            stage = 4
        history.append((timestamp, publisher))
        publishers[publisher] += 1
        stages[index] = stage
        counts[STAGE_NAMES[stage]] += 1
    return stages, {
        "documents": len(documents),
        "exact_headline_story_keys": len(story_keys),
        "lifecycle_window_minutes": 1440,
        "document_stage_counts": counts,
        "publisher_independence_claimed": False,
        "note": "Cross-publisher means distinct normalized publisher labels; syndication independence is unavailable.",
    }


def align_dynamic_states(
    oof: np.ndarray,
    events: np.ndarray,
    trades: np.ndarray,
    document_stages: np.ndarray,
) -> dict[str, np.ndarray]:
    count = len(oof)
    latest_age = np.full(count, np.nan, dtype=np.float32)
    latest_stage = np.zeros(count, dtype=np.uint8)
    new_story_count = np.zeros(count, dtype=np.uint16)
    confirmation_count = np.zeros(count, dtype=np.uint16)
    post_confirmation_count = np.zeros(count, dtype=np.uint16)
    trade_arrival = np.zeros(count, dtype=np.uint8)
    order = np.argsort(oof["market"], kind="stable")
    ordered_markets = np.asarray(oof["market"][order], dtype=np.uint32)
    boundaries = np.concatenate(([0], np.flatnonzero(np.diff(ordered_markets)) + 1, [count]))
    event_market_offsets = np.searchsorted(events["market"], np.arange(int(oof["market"].max()) + 2, dtype=np.uint32), side="left")
    trade_market_offsets = np.searchsorted(trades["market"], np.arange(int(oof["market"].max()) + 2, dtype=np.uint32), side="left")
    for left, right in zip(boundaries[:-1], boundaries[1:]):
        row_indices = order[left:right]
        market = int(ordered_markets[left])
        grid = DEVELOPMENT_START_US + np.asarray(oof["minute"][row_indices], dtype=np.int64) * MINUTE_US
        market_events = events[event_market_offsets[market]:event_market_offsets[market + 1]]
        if len(market_events):
            times = np.asarray(market_events["timestamp_us"], dtype=np.int64)
            stages = document_stages[np.asarray(market_events["document"], dtype=np.int64)]
            event_right = np.searchsorted(times, grid, side="right")
            event_left = np.searchsorted(times, grid - WINDOW_US, side="right")
            present = event_right > event_left
            latest = event_right[present] - 1
            latest_age[row_indices[present]] = ((grid[present] - times[latest]) / MINUTE_US).astype(np.float32)
            latest_stage[row_indices[present]] = stages[latest]
            for target, stage in (
                (new_story_count, 1),
                (confirmation_count, 3),
                (post_confirmation_count, 4),
            ):
                prefix = np.concatenate(([0], np.cumsum(stages == stage, dtype=np.int64)))
                target[row_indices] = np.minimum(prefix[event_right] - prefix[event_left], np.iinfo(np.uint16).max)
        market_trades = trades[trade_market_offsets[market]:trade_market_offsets[market + 1]]
        trade_times = np.asarray(market_trades["timestamp_us"], dtype=np.int64)
        visible = np.searchsorted(trade_times, grid, side="right")
        future = np.searchsorted(trade_times, grid + HORIZON_US, side="right")
        trade_arrival[row_indices] = (future > visible).astype(np.uint8)
    return {
        "latest_news_age_minutes": latest_age,
        "latest_story_stage": latest_stage,
        "new_story_count_1440m": new_story_count,
        "first_confirmation_count_1440m": confirmation_count,
        "post_confirmation_count_1440m": post_confirmation_count,
        "trade_arrival_30m": trade_arrival,
    }


def diagnostic_row(name: str, mask: np.ndarray, labels: np.ndarray, oof: np.ndarray) -> dict[str, Any]:
    if not np.any(mask):
        return {"group": name, "rows": 0}
    output = {
        "group": name,
        "rows": int(mask.sum()),
        "markets": int(len(np.unique(oof["market"][mask]))),
        "positives": int(labels[mask].sum()),
        "prevalence": float(labels[mask].mean()),
        "mean_b0": float(np.mean(oof["b0"][mask])),
        "mean_b1": float(np.mean(oof["b1"][mask])),
        "mean_b2": float(np.mean(oof["b2"][mask])),
        "mean_b3": float(np.mean(oof["b3"][mask])),
    }
    for title, baseline, candidate in (
        ("b1_vs_b0", "b0", "b1"),
        ("b2_vs_b1", "b1", "b2"),
        ("b3_vs_b2", "b2", "b3"),
        ("b3_vs_b0", "b0", "b3"),
    ):
        result = comparison(labels[mask], oof[baseline][mask], oof[candidate][mask])
        output[f"{title}_log_loss_improvement"] = result["log_loss_improvement"]
        output[f"{title}_brier_improvement"] = result["brier_improvement"]
    return output


def correction_rows(labels: np.ndarray, oof: np.ndarray) -> list[dict[str, Any]]:
    p0 = np.clip(np.asarray(oof["b0"], dtype=np.float64), 1e-7, 1 - 1e-7)
    p3 = np.clip(np.asarray(oof["b3"], dtype=np.float64), 1e-7, 1 - 1e-7)
    corrections = np.log(p3 / (1 - p3)) - np.log(p0 / (1 - p0))
    edges = np.asarray([-np.inf, -1.0, -0.5, -0.2, -0.05, 0.05, 0.2, 0.5, 1.0, np.inf])
    output = []
    for index in range(len(edges) - 1):
        mask = (corrections > edges[index]) & (corrections <= edges[index + 1])
        if not np.any(mask):
            continue
        output.append({
            "bucket": index + 1,
            "lower": None if not np.isfinite(edges[index]) else float(edges[index]),
            "upper": None if not np.isfinite(edges[index + 1]) else float(edges[index + 1]),
            "rows": int(mask.sum()),
            "markets": int(len(np.unique(oof["market"][mask]))),
            "mean_logit_correction": float(corrections[mask].mean()),
            "mean_probability_correction": float((p3[mask] - p0[mask]).mean()),
            "mean_b0": float(p0[mask].mean()),
            "mean_b3": float(p3[mask].mean()),
            "observed_rate": float(labels[mask].mean()),
            "observed_minus_b0": float((labels[mask] - p0[mask]).mean()),
            "b3_vs_b0_log_loss_improvement": float(np.mean(loss(labels[mask], p0[mask]) - loss(labels[mask], p3[mask]))),
        })
    return output


def quantile_groups(name: str, values: np.ndarray, valid: np.ndarray, labels: np.ndarray, oof: np.ndarray) -> list[dict[str, Any]]:
    selected = values[valid]
    if not len(selected):
        return []
    edges = np.quantile(selected, (0, 0.25, 0.5, 0.75, 1))
    bins = np.searchsorted(edges[1:-1], values, side="right")
    output = []
    for number in range(4):
        mask = valid & (bins == number)
        row = diagnostic_row(f"{name}_q{number + 1}", mask, labels, oof)
        row["dimension"] = name
        row["lower"] = float(edges[number])
        row["upper"] = float(edges[number + 1])
        output.append(row)
    return output


def main() -> None:
    outputs = (REPORT, AGE_CSV, LIFECYCLE_CSV, CORRECTION_CSV, CONTEXT_CSV, TRADE_CSV, SUMMARY, MANIFEST)
    if any(path.exists() for path in outputs):
        raise SystemExit("v5 failure-diagnostic artifacts already exist")
    forbidden = (FUTURE / "consumption_receipt.json", FUTURE / "examples/examples.bin", FUTURE / "evaluation/result.json")
    if any(path.exists() for path in forbidden):
        raise SystemExit("historical diagnosis refused after v4 future consumption")
    verify_manifest(EXAMPLES_MANIFEST)
    verify_manifest(MODEL_MANIFEST)
    example_count = EXAMPLES.stat().st_size // EXAMPLE_DTYPE.itemsize
    oof_count = OOF.stat().st_size // OOF_DTYPE.itemsize
    event_count = EVENTS.stat().st_size // EVENT_DTYPE.itemsize
    trade_count = TRADES.stat().st_size // TRADE_DTYPE.itemsize
    examples = np.memmap(EXAMPLES, mode="r", dtype=EXAMPLE_DTYPE, shape=(example_count,))
    oof = np.memmap(OOF, mode="r", dtype=OOF_DTYPE, shape=(oof_count,))
    events = np.memmap(EVENTS, mode="r", dtype=EVENT_DTYPE, shape=(event_count,))
    trades = np.memmap(TRADES, mode="r", dtype=TRADE_DTYPE, shape=(trade_count,))
    indices = reconstruct_oof_indices(examples, oof)
    features = np.asarray(examples["features"][indices], dtype=np.float32)
    labels = np.asarray(oof["label"], dtype=np.uint8)
    documents, document_stats = load_documents()
    stages, story_summary = story_stages(documents)
    dynamic = align_dynamic_states(oof, events, trades, stages)
    if np.any(labels > dynamic["trade_arrival_30m"]):
        raise RuntimeError("jump found without a future execution")

    age = dynamic["latest_news_age_minutes"]
    age_specs = (
        ("no_news_1440m", ~np.isfinite(age)),
        ("age_0_30m", (age >= 0) & (age <= 30)),
        ("age_30_120m", (age > 30) & (age <= 120)),
        ("age_120_360m", (age > 120) & (age <= 360)),
        ("age_360_1440m", (age > 360) & (age < 1440)),
    )
    age_rows = [diagnostic_row(name, mask, labels, oof) for name, mask in age_specs]
    lifecycle_rows = [
        diagnostic_row(STAGE_NAMES[stage], dynamic["latest_story_stage"] == stage, labels, oof)
        for stage in STAGE_NAMES
    ]
    lifecycle_rows.extend([
        diagnostic_row("any_new_story_in_1440m", dynamic["new_story_count_1440m"] > 0, labels, oof),
        diagnostic_row("any_first_cross_publisher_confirmation_in_1440m", dynamic["first_confirmation_count_1440m"] > 0, labels, oof),
        diagnostic_row("any_post_confirmation_repetition_in_1440m", dynamic["post_confirmation_count_1440m"] > 0, labels, oof),
    ])
    corrections = correction_rows(labels, oof)

    market_rows = list(read_jsonl(MARKETS))
    categories = np.asarray([str(row["category"]) for row in market_rows], dtype=object)
    venues = np.asarray([str(row["venue"]) for row in market_rows], dtype=object)
    market_index = np.asarray(oof["market"], dtype=np.int64)
    context_rows = []
    for dimension, row_values in (("category", categories[market_index]), ("venue", venues[market_index])):
        for value in sorted(set(row_values.tolist())):
            row = diagnostic_row(f"{dimension}:{value}", row_values == value, labels, oof)
            row["dimension"] = dimension
            row["value"] = value
            context_rows.append(row)
    context_rows.extend(quantile_groups("liquidity_notional_240m", np.asarray(features[:, 9], dtype=np.float64), np.ones(len(oof), dtype=bool), labels, oof))
    terminal_us = np.full(len(market_rows), np.nan, dtype=np.float64)
    for index, market in enumerate(market_rows):
        if market.get("terminal_time"):
            terminal_us[index] = datetime.fromisoformat(str(market["terminal_time"]).replace("Z", "+00:00")).timestamp() * 1_000_000
    grid_us = DEVELOPMENT_START_US + np.asarray(oof["minute"], dtype=np.int64) * MINUTE_US
    time_to_terminal = (terminal_us[market_index] - grid_us) / MINUTE_US
    context_rows.extend(quantile_groups("minutes_to_scheduled_terminal", time_to_terminal, np.isfinite(time_to_terminal) & (time_to_terminal >= 0), labels, oof))

    arrival = dynamic["trade_arrival_30m"].astype(bool)
    trade_rows = [
        diagnostic_row("future_execution", arrival, labels, oof),
        diagnostic_row("no_future_execution", ~arrival, labels, oof),
        diagnostic_row("future_execution_with_news", arrival & np.isfinite(age), labels, oof),
        diagnostic_row("future_execution_without_news", arrival & ~np.isfinite(age), labels, oof),
    ]
    for row, mask in zip(trade_rows, (arrival, ~arrival, arrival & np.isfinite(age), arrival & ~np.isfinite(age))):
        row["trade_arrival_rate"] = float(arrival[mask].mean()) if np.any(mask) else None
    decomposition = {
        "rows": len(oof),
        "trade_arrivals": int(arrival.sum()),
        "trade_arrival_rate": float(arrival.mean()),
        "jumps": int(labels.sum()),
        "jump_rate": float(labels.mean()),
        "jump_rate_conditional_on_trade": float(labels[arrival].mean()),
        "jump_without_trade": int(np.sum(labels & ~arrival)),
        "trade_arrival_rate_news_exposed": float(arrival[np.isfinite(age)].mean()),
        "trade_arrival_rate_no_news": float(arrival[~np.isfinite(age)].mean()),
    }

    OUTPUT.mkdir(parents=True, exist_ok=True)
    atomic_csv(AGE_CSV, age_rows)
    atomic_csv(LIFECYCLE_CSV, lifecycle_rows)
    atomic_csv(CORRECTION_CSV, corrections)
    atomic_csv(CONTEXT_CSV, context_rows)
    atomic_csv(TRADE_CSV, trade_rows)
    report = {
        "diagnostic_id": "eventx-v5-pre-design-failure-diagnostics-20260903",
        "created_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "status": "complete",
        "role": "historical post-v4-freeze exploratory diagnosis for a separate v5 design",
        "future_v4_data_read": False,
        "frozen_v4_changed": False,
        "oof_rows": len(oof),
        "oof_markets": int(len(np.unique(oof["market"]))),
        "document_reconstruction": document_stats,
        "story_lifecycle": story_summary,
        "news_age_results": age_rows,
        "story_lifecycle_results": lifecycle_rows,
        "correction_calibration": corrections,
        "context_results": context_rows,
        "trade_arrival_results": trade_rows,
        "trade_arrival_decomposition": decomposition,
        "definitions": {
            "story": "token-normalized exact headline; short headlines remain unique",
            "cross_publisher": "distinct normalized publisher labels, not proven editorial independence",
            "latest_stage": "lifecycle state of the latest associated report in (t-1440m,t]",
            "correction": "logit(B3 OOF probability) minus logit(B0 OOF probability)",
        },
    }
    atomic_json(REPORT, report)
    key_age = {row["group"]: row for row in age_rows}
    key_stage = {row["group"]: row for row in lifecycle_rows}
    SUMMARY.write_text(
        "# EventX v5 pre-design failure diagnostics\n\n"
        "This exploratory analysis used only previously opened historical discovery "
        "data. It did not read the v4 future holdout or alter frozen v4.\n\n"
        "## Key outputs\n\n"
        f"- OOF rows: {len(oof):,}; markets: {len(np.unique(oof['market'])):,}.\n"
        f"- B3-vs-B0 log-loss improvement with no recent news: "
        f"`{key_age['no_news_1440m']['b3_vs_b0_log_loss_improvement']:.6f}`.\n"
        f"- B3-vs-B0 improvement for news aged 0–30 minutes: "
        f"`{key_age['age_0_30m']['b3_vs_b0_log_loss_improvement']:.6f}`.\n"
        f"- B3-vs-B0 improvement when the latest report is the first cross-publisher "
        f"confirmation: `{key_stage['first_cross_publisher_confirmation']['b3_vs_b0_log_loss_improvement']:.6f}`.\n"
        f"- Trade-arrival rate: {decomposition['trade_arrival_rate']:.3%}; jump rate "
        f"conditional on a trade: {decomposition['jump_rate_conditional_on_trade']:.3%}.\n"
        f"- Jump observations without a future execution: {decomposition['jump_without_trade']}.\n\n"
        "The detailed JSON and CSV tables should be used to finalize—not retroactively "
        "confirm—the separate v5 feature and model specification.\n",
        encoding="utf-8",
    )
    atomic_json(MANIFEST, {
        "diagnostic_id": report["diagnostic_id"],
        "status": report["status"],
        "artifacts": [{"path": relative(path), "sha256": sha256_file(path)} for path in (*outputs[:-1], Path(__file__).resolve())],
        "inputs": [{"path": relative(path), "sha256": sha256_file(path)} for path in (EXAMPLES, EXAMPLES_MANIFEST, OOF, MODEL_MANIFEST, EVENTS, TRADES, MARKETS)],
    })
    print(json.dumps({
        "status": report["status"],
        "future_v4_data_read": False,
        "news_age_results": age_rows,
        "trade_arrival_decomposition": decomposition,
    }, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
