"""Build sealed EventX v4 confirmatory features and labels after consumption."""

from __future__ import annotations

from collections import Counter
from datetime import datetime, timezone
import json
import os
from pathlib import Path
from typing import Any, Iterator

import numpy as np

from eventx.features.v4_news import MINUTE_US, trailing_event_features
from eventx.settings import REPO_ROOT
from eventx.tasks.build_v3_1_historical_development_examples import (
    FEATURE_NAMES as V3_FEATURE_NAMES,
    ceil_div,
    rolling_population_std,
    trailing_counts_and_sums,
)
from eventx.tasks.build_v4_discovery_examples import FEATURE_NAMES, reordered_quality
from eventx.tasks.export_v3_historical_feasibility import parse_utc
from eventx.tasks.prepare_v3_1_historical_development_arrays import TRADE_DTYPE, sha256_file
from eventx.tasks.prepare_v4_discovery_news_quality import EVENT_DTYPE


PROTOCOL_ID = "eventx-v4-confirmatory-polymarket-20260902"
PREPARED = REPO_ROOT / "data/v4/confirmatory/prepared"
PREPARED_MANIFEST = PREPARED / "manifest.json"
RECEIPT = REPO_ROOT / "data/v4/confirmatory/consumption_receipt.json"
OUTPUT = REPO_ROOT / "data/v4/confirmatory/examples"
EXAMPLES = OUTPUT / "examples.bin"
REPORT = OUTPUT / "report.json"
MANIFEST = OUTPUT / "manifest.json"
START = parse_utc("2026-09-06T00:00:00Z")
END = parse_utc("2026-10-30T00:00:00Z")
HORIZON_MINUTES = 30
WINDOWS = (60, 360, 1440)
EXAMPLE_DTYPE = np.dtype([
    ("market", "<u4"),
    ("minute", "<i4"),
    ("venue", "u1"),
    ("group", "u1"),
    ("label", "u1"),
    ("trade_arrival", "u1"),
    ("price_age", "<f4"),
    ("features", "<f4", (len(FEATURE_NAMES),)),
], align=False)


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


def verify_manifest(path: Path) -> None:
    manifest = json.loads(path.read_text(encoding="utf-8"))
    for artifact in manifest.get("artifacts", []):
        target = REPO_ROOT / str(artifact["path"])
        if not target.is_file() or sha256_file(target) != str(artifact["sha256"]):
            raise RuntimeError(f"hash-lock failure: {target}")


def verify_consumption_receipt() -> None:
    receipt = json.loads(RECEIPT.read_text(encoding="utf-8"))
    if receipt.get("protocol_id") != PROTOCOL_ID or receipt.get("status") != (
        "future_holdout_irreversibly_consumed_before_label_summary"
    ):
        raise RuntimeError("wrong or incomplete consumption receipt")
    for artifact in receipt.get("inputs", []):
        target = REPO_ROOT / str(artifact["path"])
        if not target.is_file() or sha256_file(target) != str(artifact["sha256"]):
            raise RuntimeError(f"consumption-receipt hash failure: {target}")


def offsets(values: np.ndarray, count: int) -> np.ndarray:
    return np.searchsorted(values["market"], np.arange(count + 1, dtype=np.uint32), side="left")


def market_examples(
    market: dict[str, Any], trades: np.ndarray, events: np.ndarray,
    start: datetime = START, end: datetime = END,
) -> np.ndarray:
    if not len(trades):
        return np.empty(0, dtype=EXAMPLE_DTYPE)
    timestamps = np.asarray(trades["timestamp_us"], dtype=np.int64)
    prices = np.asarray(trades["price"], dtype=np.float64)
    notionals = np.asarray(trades["notional"], dtype=np.float64)
    start_us = int(round(start.timestamp() * 1_000_000))
    end_us = int(round(end.timestamp() * 1_000_000))
    first_minute = ceil_div(int(timestamps[0] - start_us), MINUTE_US)
    last_exclusive = (end_us - start_us) // MINUTE_US - HORIZON_MINUTES
    terminal = market.get("terminal_time")
    terminal_us = int(round(parse_utc(str(terminal)).timestamp() * 1_000_000)) if terminal else None
    if terminal_us is not None:
        last_exclusive = min(last_exclusive, (terminal_us - start_us) // MINUTE_US - HORIZON_MINUTES + 1)
    first_grid = ceil_div(first_minute, 5) * 5
    if last_exclusive <= first_grid:
        return np.empty(0, dtype=EXAMPLE_DTYPE)
    minute_positions = np.arange(first_minute, last_exclusive + HORIZON_MINUTES, dtype=np.int64)
    minute_times = start_us + minute_positions * MINUTE_US
    price_indices = np.searchsorted(timestamps, minute_times, side="right") - 1
    if np.any(price_indices < 0):
        raise RuntimeError("grid precedes first execution")
    clipped = np.clip(prices[price_indices], 0.0001, 0.9999)
    logodds = np.log(clipped / (1.0 - clipped))
    volatility = rolling_population_std(logodds, (30, 240))
    grid_minutes = np.arange(first_grid, last_exclusive, 5, dtype=np.int64)
    indices = grid_minutes - first_minute
    grid_us = start_us + grid_minutes * MINUTE_US
    future_indices = indices + HORIZON_MINUTES
    count60, notional60, right = trailing_counts_and_sums(timestamps, notionals, grid_us, 60)
    count240, notional240, right240 = trailing_counts_and_sums(timestamps, notionals, grid_us, 240)
    if not np.array_equal(right, right240):
        raise RuntimeError("trailing endpoints differ")
    visible = right - 1
    age = (grid_us - timestamps[visible]) / MINUTE_US
    sigma = volatility[240][indices]
    valid = (indices >= 30) & np.isfinite(sigma) & (count240 >= 3) & (notional240 >= 100.0) & (right > 0) & (age <= 60.0)
    if terminal_us is not None:
        valid &= grid_us + HORIZON_MINUTES * MINUTE_US <= terminal_us
    indices, future_indices, grid_minutes, grid_us = indices[valid], future_indices[valid], grid_minutes[valid], grid_us[valid]
    visible, age, sigma = visible[valid], age[valid], sigma[valid]
    count60, count240 = count60[valid], count240[valid]
    notional60, notional240 = notional60[valid], notional240[valid]
    if not len(indices):
        return np.empty(0, dtype=EXAMPLE_DTYPE)
    current = logodds[indices]
    labels = np.where(sigma > 0.0, np.abs(logodds[future_indices] - current) >= 4.0 * sigma, False)
    future_trade_right = np.searchsorted(timestamps, grid_us + HORIZON_MINUTES * MINUTE_US, side="right")
    trade_arrival = future_trade_right > right[valid]
    features = np.empty((len(indices), len(FEATURE_NAMES)), dtype=np.float32)
    features[:, 0] = current
    for column, lag in ((1, 5), (2, 30), (3, 120)):
        features[:, column] = current - logodds[np.maximum(0, indices - lag)]
    features[:, 4] = volatility[30][indices]
    features[:, 5] = sigma
    features[:, 6:12] = np.column_stack((count60, count240, notional60, notional240, age, np.ones(len(indices))))
    event_times = np.asarray(events["timestamp_us"], dtype=np.int64)
    news_right = np.searchsorted(event_times, grid_us, side="right")
    for column, window in ((12, 60), (13, 360), (14, 1440)):
        news_left = np.searchsorted(event_times, grid_us - window * MINUTE_US, side="right")
        features[:, column] = news_right - news_left
    features[:, 15] = 0.0
    quality = trailing_event_features(
        event_times,
        np.asarray(events["relevance"], dtype=np.float32),
        np.asarray(events["novelty"], dtype=np.float32),
        np.asarray(events["publisher"], dtype=np.uint16),
        np.asarray(events["diffusion_publishers"] >= 2, dtype=np.uint8),
        grid_us,
        WINDOWS,
    )
    features[:, len(V3_FEATURE_NAMES):] = reordered_quality(quality)
    if not np.all(np.isfinite(features)):
        raise RuntimeError(f"nonfinite confirmatory feature: {market['market_index']}")
    output = np.empty(len(indices), dtype=EXAMPLE_DTYPE)
    output["market"] = int(market["market_index"])
    output["minute"] = grid_minutes
    output["venue"] = 1
    output["group"] = int(market["market_group"])
    output["label"] = labels.astype(np.uint8)
    output["trade_arrival"] = trade_arrival.astype(np.uint8)
    output["price_age"] = age.astype(np.float32)
    output["features"] = features
    return output


def main() -> None:
    if any(path.exists() for path in (EXAMPLES, REPORT, MANIFEST)):
        raise SystemExit("confirmatory examples already exist; rerun prohibited")
    if not RECEIPT.is_file():
        raise SystemExit("consumption receipt required before labels")
    verify_consumption_receipt()
    verify_manifest(PREPARED_MANIFEST)
    markets = list(read_jsonl(PREPARED / "market_index.jsonl"))
    trade_count = (PREPARED / "trades.bin").stat().st_size // TRADE_DTYPE.itemsize
    event_count = (PREPARED / "news_quality_events.bin").stat().st_size // EVENT_DTYPE.itemsize
    trades = np.memmap(PREPARED / "trades.bin", mode="r", dtype=TRADE_DTYPE, shape=(trade_count,))
    events = np.memmap(PREPARED / "news_quality_events.bin", mode="r", dtype=EVENT_DTYPE, shape=(event_count,))
    trade_offsets, event_offsets = offsets(trades, len(markets)), offsets(events, len(markets))
    counters: Counter[str] = Counter()
    OUTPUT.mkdir(parents=True, exist_ok=True)
    temporary = EXAMPLES.with_suffix(EXAMPLES.suffix + ".tmp")
    with temporary.open("wb") as handle:
        for index, market in enumerate(markets):
            rows = market_examples(market, trades[trade_offsets[index]:trade_offsets[index + 1]], events[event_offsets[index]:event_offsets[index + 1]])
            rows.tofile(handle)
            counters["rows_price_age_le_60"] += len(rows)
            counters["rows_price_age_le_30"] += int(np.sum(rows["price_age"] <= 30.0))
            counters["markets_with_rows"] += int(len(rows) > 0)
    os.replace(temporary, EXAMPLES)
    report = {
        "protocol_id": PROTOCOL_ID,
        "created_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "status": "confirmatory_examples_sealed_pending_one_shot_evaluation",
        "labels_constructed_after_consumption_receipt": True,
        "label_prevalence_or_values_disclosed": False,
        "prediction_or_metric_computed": False,
        "rows_price_age_le_60": counters["rows_price_age_le_60"],
        "rows_price_age_le_30": counters["rows_price_age_le_30"],
        "markets_with_rows": counters["markets_with_rows"],
        "feature_names": list(FEATURE_NAMES),
        "dtype": EXAMPLE_DTYPE.descr,
        "artifact": {"path": relative(EXAMPLES), "sha256": sha256_file(EXAMPLES), "bytes": EXAMPLES.stat().st_size},
    }
    atomic_json(REPORT, report)
    atomic_json(MANIFEST, {
        "protocol_id": PROTOCOL_ID,
        "status": "examples_sealed",
        "artifacts": [
            {"path": relative(path), "sha256": sha256_file(path)}
            for path in (EXAMPLES, REPORT, Path(__file__).resolve())
        ],
        "inputs": [{"path": relative(PREPARED_MANIFEST), "sha256": sha256_file(PREPARED_MANIFEST)}, {"path": relative(RECEIPT), "sha256": sha256_file(RECEIPT)}],
    })
    print(json.dumps({"status": report["status"], "rows_price_age_le_60": report["rows_price_age_le_60"], "rows_price_age_le_30": report["rows_price_age_le_30"], "label_summary_disclosed": False}, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
