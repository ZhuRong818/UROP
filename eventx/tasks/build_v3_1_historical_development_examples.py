"""Build the frozen EventX v3.1 development feature/label matrix."""

from __future__ import annotations

from collections import Counter
from datetime import datetime, timezone
import hashlib
import json
import math
import os
from pathlib import Path
from typing import Any, Iterator

import numpy as np

from eventx.settings import REPO_ROOT
from eventx.tasks.prepare_v3_1_historical_development_arrays import (
    NEWS_DTYPE,
    TRADE_DTYPE,
    parse_utc,
    sha256_file,
)


PROTOCOL = REPO_ROOT / "eventx/release/v3_1_historical_primary/protocol.json"
PREPARED = REPO_ROOT / "data/v3_1_historical/primary/development/prepared"
IMPLEMENTATION_MANIFEST = (
    REPO_ROOT / "eventx/release/v3_1_historical_primary/implementation_manifest.json"
)
OUTPUT = REPO_ROOT / "data/v3_1_historical/primary/development"
EXAMPLES = OUTPUT / "examples.bin"
REPORT = OUTPUT / "examples_report.json"
MANIFEST = OUTPUT / "examples_manifest.json"
HOLDOUT = REPO_ROOT / "data/v3_1_historical/primary/holdout"
DEVELOPMENT_START = parse_utc("2026-05-17T00:00:00Z")
DEVELOPMENT_END = parse_utc("2026-07-22T00:00:00Z")
MINUTE_US = 60 * 1_000_000
HORIZON_MINUTES = 30
FEATURE_NAMES = (
    "price_logodds",
    "momentum_5m",
    "momentum_30m",
    "momentum_120m",
    "realized_vol_30m",
    "realized_vol_240m",
    "trade_count_60m",
    "trade_count_240m",
    "notional_60m",
    "notional_240m",
    "minutes_since_trade",
    "venue_indicator",
    "news_article_count_60m",
    "news_article_count_360m",
    "news_article_count_1440m",
    "news_symbol_mapped",
)
EXAMPLE_DTYPE = np.dtype(
    [
        ("market", "<u4"),
        ("minute", "<i4"),
        ("venue", "u1"),
        ("group", "u1"),
        ("label", "u1"),
        ("price_age", "<f4"),
        ("features", "<f4", (len(FEATURE_NAMES),)),
    ],
    align=False,
)


def relative(path: Path) -> str:
    return str(path.relative_to(REPO_ROOT))


def atomic_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n")
    os.replace(temporary, path)


def read_jsonl(path: Path) -> Iterator[dict[str, Any]]:
    with path.open(encoding="utf-8") as handle:
        for line in handle:
            if line.strip():
                yield json.loads(line)


def verify_manifest(path: Path) -> None:
    manifest = json.loads(path.read_text(encoding="utf-8"))
    for artifact in manifest.get("artifacts", []):
        artifact_path = REPO_ROOT / str(artifact["path"])
        if not artifact_path.is_file() or sha256_file(artifact_path) != str(
            artifact["sha256"]
        ):
            raise RuntimeError(f"hash-lock failure: {artifact_path}")


def ceil_div(left: int, right: int) -> int:
    return -(-left // right)


def rolling_population_std(values: np.ndarray, windows: tuple[int, ...]) -> dict[int, np.ndarray]:
    differences = np.diff(values)
    cumulative = np.concatenate(([0.0], np.cumsum(differences, dtype=np.float64)))
    cumulative_sq = np.concatenate(
        ([0.0], np.cumsum(differences * differences, dtype=np.float64))
    )
    positions = np.arange(len(values), dtype=np.int64)
    output: dict[int, np.ndarray] = {}
    for window in windows:
        left = np.maximum(0, positions - window)
        count = positions - left
        total = cumulative[positions] - cumulative[left]
        total_sq = cumulative_sq[positions] - cumulative_sq[left]
        denominator = np.maximum(count, 1)
        mean = total / denominator
        variance = np.maximum(0.0, total_sq / denominator - mean * mean)
        result = np.sqrt(variance)
        result[count == 0] = np.nan
        output[window] = result
    return output


def trailing_counts_and_sums(
    timestamps: np.ndarray,
    notionals: np.ndarray,
    grid_us: np.ndarray,
    window_minutes: int,
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    right = np.searchsorted(timestamps, grid_us, side="right")
    left = np.searchsorted(
        timestamps, grid_us - window_minutes * MINUTE_US, side="right"
    )
    cumulative = np.concatenate(([0.0], np.cumsum(notionals, dtype=np.float64)))
    return right - left, cumulative[right] - cumulative[left], right


def market_examples(
    market: dict[str, Any],
    trades: np.ndarray,
    news_timestamps: np.ndarray,
) -> np.ndarray:
    if not len(trades):
        return np.empty(0, dtype=EXAMPLE_DTYPE)
    timestamps = np.asarray(trades["timestamp_us"], dtype=np.int64)
    prices = np.asarray(trades["price"], dtype=np.float64)
    notionals = np.asarray(trades["notional"], dtype=np.float64)
    start_us = int(round(DEVELOPMENT_START.timestamp() * 1_000_000))
    end_us = int(round(DEVELOPMENT_END.timestamp() * 1_000_000))
    first_minute = ceil_div(int(timestamps[0] - start_us), MINUTE_US)
    last_minute_exclusive = (end_us - start_us) // MINUTE_US - HORIZON_MINUTES
    terminal_text = market.get("terminal_time")
    terminal_usable = False
    if terminal_text:
        terminal_us = int(round(parse_utc(str(terminal_text)).timestamp() * 1_000_000))
        terminal_usable = terminal_us >= int(timestamps[0])
        if terminal_usable:
            last_minute_exclusive = min(
                last_minute_exclusive,
                (terminal_us - start_us) // MINUTE_US - HORIZON_MINUTES + 1,
            )
    first_grid = ceil_div(first_minute, 5) * 5
    if last_minute_exclusive <= first_grid:
        return np.empty(0, dtype=EXAMPLE_DTYPE)
    minute_positions = np.arange(
        first_minute,
        last_minute_exclusive + HORIZON_MINUTES,
        dtype=np.int64,
    )
    minute_times_us = start_us + minute_positions * MINUTE_US
    price_indices = np.searchsorted(timestamps, minute_times_us, side="right") - 1
    if np.any(price_indices < 0):
        raise RuntimeError("minute grid precedes first visible execution")
    clipped = np.clip(prices[price_indices], 0.0001, 0.9999)
    logodds = np.log(clipped / (1.0 - clipped))
    volatility = rolling_population_std(logodds, (30, 240))
    grid_minutes = np.arange(first_grid, last_minute_exclusive, 5, dtype=np.int64)
    indices = grid_minutes - first_minute
    grid_us = start_us + grid_minutes * MINUTE_US
    future_indices = indices + HORIZON_MINUTES

    count_60, notional_60, right = trailing_counts_and_sums(
        timestamps, notionals, grid_us, 60
    )
    count_240, notional_240, right_240 = trailing_counts_and_sums(
        timestamps, notionals, grid_us, 240
    )
    if not np.array_equal(right, right_240):
        raise RuntimeError("trailing-window right endpoints differ")
    visible_trade_index = right - 1
    price_age = (grid_us - timestamps[visible_trade_index]) / MINUTE_US
    sigma = volatility[240][indices]
    valid = (
        (indices >= 30)
        & np.isfinite(sigma)
        & (count_240 >= 3)
        & (notional_240 >= 100.0)
        & (right > 0)
    )
    if terminal_usable:
        valid &= grid_us + HORIZON_MINUTES * MINUTE_US <= terminal_us
    indices = indices[valid]
    future_indices = future_indices[valid]
    grid_minutes = grid_minutes[valid]
    grid_us = grid_us[valid]
    visible_trade_index = visible_trade_index[valid]
    price_age = price_age[valid]
    count_60 = count_60[valid]
    count_240 = count_240[valid]
    notional_60 = notional_60[valid]
    notional_240 = notional_240[valid]
    sigma = sigma[valid]
    if not len(indices):
        return np.empty(0, dtype=EXAMPLE_DTYPE)

    current = logodds[indices]
    forward_change = logodds[future_indices] - current
    labels = np.where(sigma > 0.0, np.abs(forward_change) >= 4.0 * sigma, False)
    feature_matrix = np.empty((len(indices), len(FEATURE_NAMES)), dtype=np.float32)
    feature_matrix[:, 0] = current
    for column, lag in ((1, 5), (2, 30), (3, 120)):
        feature_matrix[:, column] = current - logodds[np.maximum(0, indices - lag)]
    feature_matrix[:, 4] = volatility[30][indices]
    feature_matrix[:, 5] = sigma
    feature_matrix[:, 6] = count_60
    feature_matrix[:, 7] = count_240
    feature_matrix[:, 8] = notional_60
    feature_matrix[:, 9] = notional_240
    feature_matrix[:, 10] = price_age
    venue_indicator = 0 if str(market["venue"]) == "kalshi" else 1
    feature_matrix[:, 11] = venue_indicator
    news_right = np.searchsorted(news_timestamps, grid_us, side="right")
    for column, window in ((12, 60), (13, 360), (14, 1440)):
        news_left = np.searchsorted(
            news_timestamps, grid_us - window * MINUTE_US, side="right"
        )
        feature_matrix[:, column] = news_right - news_left
    feature_matrix[:, 15] = 0.0
    if not np.all(np.isfinite(feature_matrix)):
        raise RuntimeError(f"nonfinite feature for market {market['market_index']}")

    output = np.empty(len(indices), dtype=EXAMPLE_DTYPE)
    output["market"] = int(market["market_index"])
    output["minute"] = grid_minutes
    output["venue"] = venue_indicator
    output["group"] = int(market["market_group"])
    output["label"] = labels.astype(np.uint8)
    output["price_age"] = price_age.astype(np.float32)
    output["features"] = feature_matrix
    return output


def offsets(values: np.ndarray, markets: int) -> np.ndarray:
    return np.searchsorted(
        values["market"], np.arange(markets + 1, dtype=np.uint32), side="left"
    )


def main() -> None:
    if EXAMPLES.exists() or REPORT.exists() or MANIFEST.exists():
        raise SystemExit("development example artifact already exists; rerun prohibited")
    if HOLDOUT.exists():
        raise SystemExit("historical holdout exists before candidate freeze")
    verify_manifest(IMPLEMENTATION_MANIFEST)
    verify_manifest(PREPARED / "manifest.json")
    protocol = json.loads(PROTOCOL.read_text())
    markets = list(read_jsonl(PREPARED / "market_index.jsonl"))
    trade_count = (PREPARED / "trades.bin").stat().st_size // TRADE_DTYPE.itemsize
    news_count = (PREPARED / "news_associations.bin").stat().st_size // NEWS_DTYPE.itemsize
    trades = np.memmap(
        PREPARED / "trades.bin", mode="r", dtype=TRADE_DTYPE, shape=(trade_count,)
    )
    news = np.memmap(
        PREPARED / "news_associations.bin", mode="r", dtype=NEWS_DTYPE, shape=(news_count,)
    )
    trade_offsets = offsets(trades, len(markets))
    news_offsets = offsets(news, len(markets))
    counters: Counter[str] = Counter()
    by_venue: Counter[str] = Counter()
    by_group: Counter[int] = Counter()
    positives_by_group: Counter[int] = Counter()
    temporary = EXAMPLES.with_suffix(EXAMPLES.suffix + ".tmp")
    with temporary.open("wb") as handle:
        for index, market in enumerate(markets):
            rows = market_examples(
                market,
                trades[trade_offsets[index] : trade_offsets[index + 1]],
                np.asarray(
                    news["timestamp_us"][news_offsets[index] : news_offsets[index + 1]],
                    dtype=np.int64,
                ),
            )
            rows.tofile(handle)
            counters["rows"] += len(rows)
            counters["positives"] += int(rows["label"].sum())
            counters["markets_with_rows"] += int(len(rows) > 0)
            counters["fresh_30m_rows"] += int(np.sum(rows["price_age"] <= 30.0))
            counters["fresh_60m_rows"] += int(np.sum(rows["price_age"] <= 60.0))
            venue = str(market["venue"])
            by_venue[venue] += len(rows)
            group = int(market["market_group"])
            by_group[group] += len(rows)
            positives_by_group[group] += int(rows["label"].sum())
            if (index + 1) % 250 == 0:
                print(
                    f"built examples for {index + 1}/{len(markets)} markets; "
                    f"rows={counters['rows']} positives={counters['positives']}",
                    flush=True,
                )
    os.replace(temporary, EXAMPLES)
    expected_bytes = counters["rows"] * EXAMPLE_DTYPE.itemsize
    if EXAMPLES.stat().st_size != expected_bytes:
        raise RuntimeError("development example byte count mismatch")
    report = {
        "protocol_id": protocol["protocol_id"],
        "created_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "status": "development_examples_frozen",
        "labels_or_outcomes_produced": True,
        "historical_holdout_read": False,
        "rows": counters["rows"],
        "positives": counters["positives"],
        "prevalence": counters["positives"] / counters["rows"],
        "markets_with_rows": counters["markets_with_rows"],
        "rows_by_venue": dict(sorted(by_venue.items())),
        "rows_by_market_group": {
            str(key): by_group[key] for key in range(5)
        },
        "positives_by_market_group": {
            str(key): positives_by_group[key] for key in range(5)
        },
        "price_freshness": {
            "le_30_minutes": counters["fresh_30m_rows"],
            "le_60_minutes": counters["fresh_60m_rows"],
        },
        "feature_names": list(FEATURE_NAMES),
        "dtype": EXAMPLE_DTYPE.descr,
        "artifact": {
            "path": relative(EXAMPLES),
            "bytes": EXAMPLES.stat().st_size,
            "sha256": sha256_file(EXAMPLES),
        },
        "checks": {
            "rows_nonempty": counters["rows"] > 0,
            "binary_class_coverage": 0 < counters["positives"] < counters["rows"],
            "all_market_groups_nonempty": all(by_group[key] > 0 for key in range(5)),
            "holdout_read": False,
        },
    }
    atomic_json(REPORT, report)
    atomic_json(
        MANIFEST,
        {
            "protocol_id": protocol["protocol_id"],
            "status": "frozen_development_examples",
            "historical_holdout_read": False,
            "artifacts": [
                {"path": relative(path), "sha256": sha256_file(path)}
                for path in (
                    PROTOCOL,
                    IMPLEMENTATION_MANIFEST,
                    PREPARED / "manifest.json",
                    Path(__file__).resolve(),
                    EXAMPLES,
                    REPORT,
                )
            ],
        },
    )
    print(json.dumps(report, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
