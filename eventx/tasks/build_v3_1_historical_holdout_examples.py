"""Normalize holdout trades and build the sealed v3.1 B0 example matrix."""

from __future__ import annotations

from collections import Counter
from datetime import datetime, timezone
import json
import os
from pathlib import Path
from typing import Any, Iterator

import numpy as np

from eventx.settings import REPO_ROOT
from eventx.tasks.build_v3_1_historical_development_examples import (
    EXAMPLE_DTYPE,
    FEATURE_NAMES,
    ceil_div,
    rolling_population_std,
    trailing_counts_and_sums,
)
from eventx.tasks.export_v3_historical_feasibility import parse_utc, rfc3339
from eventx.tasks.prepare_v3_1_historical_development_arrays import (
    TRADE_DTYPE,
    sha256_file,
    timestamp_us,
)


RELEASE = REPO_ROOT / "eventx/release/v3_1_historical_primary"
PROTOCOL = RELEASE / "protocol.json"
CANDIDATE = RELEASE / "candidate.json"
CANDIDATE_MANIFEST = RELEASE / "candidate_manifest.json"
HOLDOUT_IMPLEMENTATION_MANIFEST = RELEASE / "holdout_implementation_manifest.json"
DEVELOPMENT_PREPARED = REPO_ROOT / "data/v3_1_historical/primary/development/prepared"
HOLDOUT = REPO_ROOT / "data/v3_1_historical/primary/holdout"
RAW_TRADES = HOLDOUT / "trades"
NORMALIZED_TRADES = HOLDOUT / "trades.bin"
EXAMPLES = HOLDOUT / "examples.bin"
REPORT = HOLDOUT / "examples_report.json"
MANIFEST = HOLDOUT / "examples_manifest.json"
RECEIPT = HOLDOUT / "holdout_consumption_receipt.json"
RESULT = HOLDOUT / "evaluation_result.json"
HOLDOUT_START = parse_utc("2026-07-22T00:00:00Z")
HOLDOUT_END = parse_utc("2026-08-08T00:00:00Z")
MINUTE_US = 60 * 1_000_000
HORIZON_MINUTES = 30
WARMUP_MINUTES = 240


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
    value = json.loads(path.read_text(encoding="utf-8"))
    for artifact in value.get("artifacts", []):
        artifact_path = REPO_ROOT / str(artifact["path"])
        if not artifact_path.is_file() or sha256_file(artifact_path) != str(
            artifact["sha256"]
        ):
            raise RuntimeError(f"hash-lock failure: {artifact_path}")


def offsets(values: np.ndarray, markets: int) -> np.ndarray:
    return np.searchsorted(
        values["market"], np.arange(markets + 1, dtype=np.uint32), side="left"
    )


def normalize_holdout_trades(
    markets: list[dict[str, Any]], lookup: dict[tuple[str, str], int]
) -> tuple[dict[str, int], list[dict[str, Any]]]:
    manifests = {
        venue: json.loads((RAW_TRADES / venue / "manifest.json").read_text())
        for venue in ("kalshi", "polymarket")
    }
    if not all(value.get("integrity_pass") is True for value in manifests.values()):
        raise RuntimeError("holdout trade retrieval did not pass integrity")
    maximum_rows = sum(int(value["rows"]) for value in manifests.values())
    array = np.memmap(
        NORMALIZED_TRADES, mode="w+", dtype=TRADE_DTYPE, shape=(maximum_rows,)
    )
    counters: Counter[str] = Counter()
    written = 0
    ordinal = 1 << 62
    raw_artifacts: list[dict[str, Any]] = []
    for venue in ("kalshi", "polymarket"):
        for artifact in manifests[venue]["artifacts"]:
            page_path = REPO_ROOT / str(artifact["data_path"])
            if sha256_file(page_path) != str(artifact["data_sha256"]):
                raise RuntimeError(f"holdout raw page hash mismatch: {page_path}")
            raw_artifacts.append(
                {"path": relative(page_path), "sha256": sha256_file(page_path)}
            )
            previous_key: tuple[str, str] | None = None
            previous_signature: tuple[Any, ...] | None = None
            for row in read_jsonl(page_path):
                counters["raw_rows"] += 1
                ordinal += 1
                trade_id = str(row["trade_id"])
                if venue == "kalshi":
                    key = (venue, str(row["ticker"]))
                    timestamp_text = str(row["created_time"])
                    price = float(row["yes_price"]) / 100.0
                    notional = float(row["count"])
                    signature = (key, row["count"], row["yes_price"])
                else:
                    key = (venue, str(row["condition_id"]))
                    timestamp_text = str(row["ts"])
                    price = float(row["price"])
                    notional = float(row["size"])
                    signature = (key, str(row["asset_id"]), row["size"], row["price"])
                execution_key = (trade_id, rfc3339(parse_utc(timestamp_text)))
                if execution_key == previous_key:
                    if signature != previous_signature:
                        raise RuntimeError(f"conflicting adjacent duplicate in {page_path}")
                    counters["exact_duplicates_collapsed"] += 1
                    continue
                previous_key = execution_key
                previous_signature = signature
                market_index = lookup.get(key)
                if market_index is None:
                    raise RuntimeError(f"out-of-cohort holdout execution: {key}")
                if notional == 0.0:
                    counters["zero_notional_excluded"] += 1
                    continue
                if notional < 0.0 or not np.isfinite(notional):
                    raise RuntimeError(f"invalid holdout notional in {page_path}")
                if not 0.0 <= price <= 1.0 or not np.isfinite(price):
                    raise RuntimeError(f"invalid holdout price in {page_path}")
                array[written] = (
                    market_index,
                    timestamp_us(timestamp_text),
                    price,
                    notional,
                    ordinal,
                )
                written += 1
    array.flush()
    del array
    os.truncate(NORMALIZED_TRADES, written * TRADE_DTYPE.itemsize)
    array = np.memmap(
        NORMALIZED_TRADES, mode="r+", dtype=TRADE_DTYPE, shape=(written,)
    )
    array.sort(order=("market", "timestamp_us", "ordinal"), kind="quicksort")
    array.flush()
    del array
    counters["normalized_rows"] = written
    if counters["raw_rows"] != maximum_rows:
        raise RuntimeError("holdout raw row accounting mismatch")
    return dict(counters), raw_artifacts


def combined_market_trades(
    development: np.ndarray, holdout: np.ndarray
) -> np.ndarray:
    start_us = int(round(HOLDOUT_START.timestamp() * 1_000_000))
    warmup_us = start_us - WARMUP_MINUTES * MINUTE_US
    if len(development):
        timestamps = np.asarray(development["timestamp_us"], dtype=np.int64)
        left = int(np.searchsorted(timestamps, warmup_us, side="left"))
        left = max(0, left - 1)
        development = development[left:]
    if len(development) and len(holdout):
        values = np.concatenate((development, holdout))
    elif len(development):
        values = np.array(development, dtype=TRADE_DTYPE, copy=True)
    else:
        values = np.array(holdout, dtype=TRADE_DTYPE, copy=True)
    if len(values) > 1:
        values.sort(order=("timestamp_us", "ordinal"), kind="quicksort")
    return values


def holdout_market_examples(market: dict[str, Any], trades: np.ndarray) -> np.ndarray:
    if not len(trades):
        return np.empty(0, dtype=EXAMPLE_DTYPE)
    timestamps = np.asarray(trades["timestamp_us"], dtype=np.int64)
    prices = np.asarray(trades["price"], dtype=np.float64)
    notionals = np.asarray(trades["notional"], dtype=np.float64)
    start_us = int(round(HOLDOUT_START.timestamp() * 1_000_000))
    end_us = int(round(HOLDOUT_END.timestamp() * 1_000_000))
    first_minute = max(
        -WARMUP_MINUTES,
        ceil_div(int(timestamps[0] - start_us), MINUTE_US),
    )
    last_minute_exclusive = (end_us - start_us) // MINUTE_US - HORIZON_MINUTES
    terminal_text = market.get("terminal_time")
    terminal_usable = False
    if terminal_text:
        terminal_us = timestamp_us(str(terminal_text))
        frozen_first_trade_us = timestamp_us(str(market["first_trade_ts"]))
        terminal_usable = terminal_us >= frozen_first_trade_us
        if terminal_usable:
            last_minute_exclusive = min(
                last_minute_exclusive,
                (terminal_us - start_us) // MINUTE_US - HORIZON_MINUTES + 1,
            )
    first_grid = max(0, ceil_div(first_minute, 5) * 5)
    if last_minute_exclusive <= first_grid:
        return np.empty(0, dtype=EXAMPLE_DTYPE)

    minute_positions = np.arange(
        first_minute,
        last_minute_exclusive + HORIZON_MINUTES,
        dtype=np.int64,
    )
    minute_times_us = start_us + minute_positions * MINUTE_US
    price_indices = np.searchsorted(timestamps, minute_times_us, side="right") - 1
    visible = price_indices >= 0
    if not np.any(visible):
        return np.empty(0, dtype=EXAMPLE_DTYPE)
    # Minutes before the first visible execution cannot be used; keep a safe index
    # only so vectorized construction remains defined before the eligibility mask.
    safe_price_indices = np.maximum(price_indices, 0)
    clipped = np.clip(prices[safe_price_indices], 0.0001, 0.9999)
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
        raise RuntimeError("holdout trailing-window right endpoints differ")
    visible_trade_index = np.maximum(right - 1, 0)
    price_age = (grid_us - timestamps[visible_trade_index]) / MINUTE_US
    sigma = volatility[240][indices]
    valid = (
        (indices >= 30)
        & visible[indices]
        & visible[future_indices]
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
    feature_matrix = np.zeros((len(indices), len(FEATURE_NAMES)), dtype=np.float32)
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
    if not np.all(np.isfinite(feature_matrix[:, :12])):
        raise RuntimeError(f"nonfinite B0 holdout feature for {market['market_index']}")

    output = np.empty(len(indices), dtype=EXAMPLE_DTYPE)
    output["market"] = int(market["market_index"])
    output["minute"] = grid_minutes
    output["venue"] = venue_indicator
    output["group"] = int(market["market_group"])
    output["label"] = labels.astype(np.uint8)
    output["price_age"] = price_age.astype(np.float32)
    output["features"] = feature_matrix
    return output


def main() -> None:
    if any(path.exists() for path in (NORMALIZED_TRADES, EXAMPLES, REPORT, MANIFEST)):
        raise SystemExit("holdout example artifact exists; rerun prohibited")
    if RECEIPT.exists() or RESULT.exists():
        raise SystemExit("holdout has already been consumed")
    verify_manifest(CANDIDATE_MANIFEST)
    verify_manifest(HOLDOUT_IMPLEMENTATION_MANIFEST)
    verify_manifest(DEVELOPMENT_PREPARED / "manifest.json")
    candidate = json.loads(CANDIDATE.read_text(encoding="utf-8"))
    if candidate.get("candidate") != "b0":
        raise SystemExit("this frozen holdout builder is for the selected B0 candidate")
    markets = list(read_jsonl(DEVELOPMENT_PREPARED / "market_index.jsonl"))
    lookup = {
        (str(row["venue"]), str(row["market_id"])): int(row["market_index"])
        for row in markets
    }
    trade_stats, raw_artifacts = normalize_holdout_trades(markets, lookup)

    development_count = (
        (DEVELOPMENT_PREPARED / "trades.bin").stat().st_size // TRADE_DTYPE.itemsize
    )
    holdout_count = NORMALIZED_TRADES.stat().st_size // TRADE_DTYPE.itemsize
    development = np.memmap(
        DEVELOPMENT_PREPARED / "trades.bin",
        mode="r",
        dtype=TRADE_DTYPE,
        shape=(development_count,),
    )
    holdout = np.memmap(
        NORMALIZED_TRADES, mode="r", dtype=TRADE_DTYPE, shape=(holdout_count,)
    )
    development_offsets = offsets(development, len(markets))
    holdout_offsets = offsets(holdout, len(markets))
    counters: Counter[str] = Counter()
    by_venue: Counter[str] = Counter()
    temporary = EXAMPLES.with_suffix(EXAMPLES.suffix + ".tmp")
    with temporary.open("wb") as handle:
        for index, market in enumerate(markets):
            combined = combined_market_trades(
                development[development_offsets[index] : development_offsets[index + 1]],
                holdout[holdout_offsets[index] : holdout_offsets[index + 1]],
            )
            rows = holdout_market_examples(market, combined)
            rows.tofile(handle)
            counters["rows"] += len(rows)
            counters["positives"] += int(rows["label"].sum())
            counters["markets_with_rows"] += int(len(rows) > 0)
            counters["fresh_30m_rows"] += int(np.sum(rows["price_age"] <= 30.0))
            counters["fresh_60m_rows"] += int(np.sum(rows["price_age"] <= 60.0))
            by_venue[str(market["venue"])] += len(rows)
            if (index + 1) % 250 == 0:
                print(
                    f"built holdout examples for {index + 1}/{len(markets)} markets; "
                    f"rows={counters['rows']}",
                    flush=True,
                )
    os.replace(temporary, EXAMPLES)
    if EXAMPLES.stat().st_size != counters["rows"] * EXAMPLE_DTYPE.itemsize:
        raise RuntimeError("holdout example byte count mismatch")
    report = {
        "protocol_id": candidate["protocol_id"],
        "created_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "status": "sealed_holdout_examples_built_metrics_unread",
        "candidate": "b0",
        "window": {
            "start": rfc3339(HOLDOUT_START),
            "end_exclusive": rfc3339(HOLDOUT_END),
        },
        "holdout_prices_read": True,
        "holdout_metrics_read": False,
        "news_features_constructed": False,
        "news_features_reason": "B0 was frozen; B1 must not be evaluated on holdout",
        "rows": counters["rows"],
        "positives": counters["positives"],
        "prevalence": counters["positives"] / counters["rows"],
        "markets_with_rows": counters["markets_with_rows"],
        "rows_by_venue": dict(sorted(by_venue.items())),
        "price_freshness": {
            "le_30_minutes": counters["fresh_30m_rows"],
            "le_60_minutes": counters["fresh_60m_rows"],
        },
        "trade_normalization": trade_stats,
        "feature_names_materialized": list(FEATURE_NAMES[:12]),
        "artifact": {
            "path": relative(EXAMPLES),
            "bytes": EXAMPLES.stat().st_size,
            "sha256": sha256_file(EXAMPLES),
            "dtype": EXAMPLE_DTYPE.descr,
        },
    }
    atomic_json(REPORT, report)
    artifacts = [
        PROTOCOL,
        CANDIDATE,
        CANDIDATE_MANIFEST,
        HOLDOUT_IMPLEMENTATION_MANIFEST,
        DEVELOPMENT_PREPARED / "manifest.json",
        RAW_TRADES / "kalshi/manifest.json",
        RAW_TRADES / "polymarket/manifest.json",
        NORMALIZED_TRADES,
        EXAMPLES,
        REPORT,
        Path(__file__).resolve(),
    ]
    atomic_json(
        MANIFEST,
        {
            "protocol_id": candidate["protocol_id"],
            "status": "sealed_holdout_examples_hash_locked_before_metrics",
            "holdout_metrics_read": False,
            "artifacts": [
                {"path": relative(path), "sha256": sha256_file(path)}
                for path in artifacts
            ],
            "raw_page_artifacts": raw_artifacts,
        },
    )
    print(json.dumps(report, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
