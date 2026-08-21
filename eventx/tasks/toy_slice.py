"""Build the retained-trade EventX toy slice from frozen JSONL extracts.

This intentionally small, dependency-free runner verifies the benchmark contract before
the full feature stack exists: canonical binary outcomes, point-in-time 1-minute bars,
30-minute labels, and purged train/validation/test splits.

Example (after the trade backfill has produced enough rows):
    python -m eventx.tasks.toy_slice --venue polymarket --max-markets 20
"""

from __future__ import annotations

import argparse
import json
import math
from collections import Counter, deque
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any, Iterator

import yaml

from eventx.settings import REPO_ROOT

CONFIG_PATH = REPO_ROOT / "eventx" / "config" / "eventx.yaml"


def parse_ts(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00")).astimezone(UTC)


def as_rfc3339(value: datetime) -> str:
    return value.astimezone(UTC).isoformat().replace("+00:00", "Z")


def split_boundaries(
    start: datetime,
    end: datetime,
    validation_frac: float,
    holdout_frac: float,
) -> tuple[datetime, datetime]:
    if validation_frac <= 0 or holdout_frac <= 0 or validation_frac + holdout_frac >= 1:
        raise ValueError("validation_frac and holdout_frac must be positive and sum to less than 1")
    span = end - start
    validation_start = start + span * (1 - validation_frac - holdout_frac)
    test_start = start + span * (1 - holdout_frac)
    return validation_start, test_start


def read_jsonl(path: Path) -> Iterator[dict[str, Any]]:
    with path.open() as handle:
        for line in handle:
            if line.strip():
                yield json.loads(line)


def load_canonical_outcomes(path: Path, venue: str) -> dict[tuple[str, str], bool]:
    """Map (market_id, outcome_id) to whether it is the canonical YES side."""
    canonical: dict[tuple[str, str], bool] = {}
    for row in read_jsonl(path):
        if row.get("venue") != venue or row.get("outcome_id") is None:
            continue
        canonical[(str(row["market_id"]), str(row["outcome_id"]))] = bool(
            row.get("canonical_side")
        )
    return canonical


def trade_fields(row: dict[str, Any], venue: str) -> tuple[datetime, float, float, str] | None:
    """Return timestamp, probability, size, and outcome ID for one retained trade."""
    try:
        if venue == "polymarket":
            return parse_ts(row["ts"]), float(row["price"]), float(row.get("size") or 0), str(row["token_id"])
        price = float(row["yes_price"])
        if price > 1:
            price /= 100
        return parse_ts(row["created_time"]), price, float(row.get("count") or 0), "YES"
    except (KeyError, TypeError, ValueError):
        return None


def count_eligible_trades(
    trades_path: Path,
    venue: str,
    start: datetime,
    end: datetime,
    canonical: dict[tuple[str, str], bool],
) -> Counter[tuple[str, str]]:
    counts: Counter[tuple[str, str]] = Counter()
    for row in read_jsonl(trades_path):
        fields = trade_fields(row, venue)
        if fields is None:
            continue
        ts, _price, _size, outcome_id = fields
        market_id = str(row.get("market_id") or row.get("condition_id") or row.get("ticker") or "")
        if not market_id or not start <= ts <= end:
            continue
        if venue == "polymarket" and not canonical.get((market_id, outcome_id), False):
            continue
        counts[(market_id, outcome_id)] += 1
    return counts


def collect_trades(
    trades_path: Path,
    venue: str,
    start: datetime,
    end: datetime,
    canonical: dict[tuple[str, str], bool],
    selected: set[tuple[str, str]],
) -> dict[tuple[str, str], list[tuple[datetime, float, float]]]:
    grouped: dict[tuple[str, str], list[tuple[datetime, float, float]]] = {
        key: [] for key in selected
    }
    for row in read_jsonl(trades_path):
        fields = trade_fields(row, venue)
        if fields is None:
            continue
        ts, price, size, outcome_id = fields
        market_id = str(row.get("market_id") or row.get("condition_id") or row.get("ticker") or "")
        key = (market_id, outcome_id)
        if key not in selected or not start <= ts <= end:
            continue
        grouped[key].append((ts, price, size))
    return grouped


def minute_bars(
    venue: str, market_id: str, outcome_id: str, trades: list[tuple[datetime, float, float]]
) -> list[dict[str, Any]]:
    """Resample one canonical-outcome trade stream into forward-filled minute bars."""
    if not trades:
        return []
    by_minute: dict[datetime, list[tuple[float, float]]] = {}
    for ts, price, size in sorted(trades):
        bucket = ts.replace(second=0, microsecond=0)
        by_minute.setdefault(bucket, []).append((price, size))
    first, last = min(by_minute), max(by_minute)
    bars: list[dict[str, Any]] = []
    last_price: float | None = None
    ts = first
    while ts <= last:
        rows = by_minute.get(ts, [])
        if rows:
            last_price = rows[-1][0]
        if last_price is not None:
            clipped = min(max(last_price, 1.0e-4), 1 - 1.0e-4)
            bars.append(
                {
                    "venue": venue,
                    "market_id": market_id,
                    "outcome_id": outcome_id,
                    "ts": as_rfc3339(ts),
                    "price": last_price,
                    "price_logodds": math.log(clipped / (1 - clipped)),
                    "price_source": "last_trade" if rows else "forward_filled_last_trade",
                    "n_trades": len(rows),
                    "notional": sum(price * size for price, size in rows),
                }
            )
        ts += timedelta(minutes=1)
    return bars


def label_bars(
    bars: list[dict[str, Any]], horizon_min: int, k_sigma: float, vol_window: int,
    min_trades: int, min_notional: float, market: dict[str, Any],
    validation_boundary: datetime, test_boundary: datetime,
) -> list[dict[str, Any]]:
    """Apply point-in-time features, eligibility, labels, and a purged split."""
    if len(bars) <= horizon_min:
        return []
    diffs_30: deque[float] = deque()
    diffs_long: deque[float] = deque()
    trades_60: deque[int] = deque()
    trades_long: deque[int] = deque()
    notional_60: deque[float] = deque()
    notional_long: deque[float] = deque()
    diff_30_sum = diff_30_sq = diff_long_sum = diff_long_sq = 0.0
    trades_60_sum = trades_long_sum = 0
    notional_60_sum = notional_long_sum = 0.0
    labels: list[dict[str, Any]] = []
    previous: float | None = None
    minutes_since_trade = 0
    close_ts = parse_ts(market["scheduled_close_ts"]) if market.get("scheduled_close_ts") else None
    resolution_ts = parse_ts(market["resolution_ts"]) if market.get("resolution_ts") else None
    validation_purge_start = validation_boundary - timedelta(minutes=horizon_min)
    test_purge_start = test_boundary - timedelta(minutes=horizon_min)
    for i, bar in enumerate(bars):
        value = float(bar["price_logodds"])
        if previous is not None:
            change = value - previous
            diffs_30.append(change)
            diff_30_sum += change
            diff_30_sq += change * change
            if len(diffs_30) > 30:
                old = diffs_30.popleft()
                diff_30_sum -= old
                diff_30_sq -= old * old
            diffs_long.append(change)
            diff_long_sum += change
            diff_long_sq += change * change
            if len(diffs_long) > vol_window:
                old = diffs_long.popleft()
                diff_long_sum -= old
                diff_long_sq -= old * old
        previous = value
        n_trades = int(bar["n_trades"])
        notional = float(bar["notional"])
        minutes_since_trade = 0 if n_trades else minutes_since_trade + 1
        trades_60.append(n_trades)
        trades_60_sum += n_trades
        notional_60.append(notional)
        notional_60_sum += notional
        if len(trades_60) > 60:
            trades_60_sum -= trades_60.popleft()
            notional_60_sum -= notional_60.popleft()
        trades_long.append(n_trades)
        trades_long_sum += n_trades
        notional_long.append(notional)
        notional_long_sum += notional
        if len(trades_long) > vol_window:
            trades_long_sum -= trades_long.popleft()
            notional_long_sum -= notional_long.popleft()
        if i + horizon_min >= len(bars) or len(diffs_long) < 30:
            continue
        mean = diff_long_sum / len(diffs_long)
        variance = max(0.0, diff_long_sq / len(diffs_long) - mean * mean)
        sigma = math.sqrt(variance)
        mean_30 = diff_30_sum / len(diffs_30)
        variance_30 = max(0.0, diff_30_sq / len(diffs_30) - mean_30 * mean_30)
        vol_30 = math.sqrt(variance_30)
        future = float(bars[i + horizon_min]["price_logodds"])
        fwd_dy = future - value
        ts = parse_ts(bar["ts"])
        boundary_price = float(bar["price"]) >= 0.98 or float(bar["price"]) <= 0.02
        near_scheduled_close = bool(close_ts and ts >= close_ts - timedelta(minutes=horizon_min))
        # Current status is not point-in-time metadata and must not be projected
        # backward. A resolution timestamp can only affect rows at or after it.
        outcome_known = bool(resolution_ts and ts >= resolution_ts)
        near_terminal = boundary_price and (near_scheduled_close or outcome_known)
        eligible = (
            trades_long_sum >= min_trades
            and notional_long_sum >= min_notional
            and not near_terminal
        )
        if ts < validation_purge_start:
            split = "train"
        elif ts < validation_boundary:
            split = "purged_train_validation"
        elif ts < test_purge_start:
            split = "validation"
        elif ts < test_boundary:
            split = "purged_validation_test"
        else:
            split = "test"
        labels.append(
            {
                **bar,
                "horizon_min": horizon_min,
                "eligible": int(eligible),
                "label_valid": 1,
                "fwd_dy": fwd_dy,
                "rolling_sigma": sigma,
                "y_jump": int(abs(fwd_dy) >= k_sigma * sigma) if sigma else 0,
                "near_terminal": int(near_terminal),
                "split": split,
                "momentum_5m": value - float(bars[max(0, i - 5)]["price_logodds"]),
                "momentum_30m": value - float(bars[max(0, i - 30)]["price_logodds"]),
                "momentum_120m": value - float(bars[max(0, i - 120)]["price_logodds"]),
                "realized_vol_30m": vol_30,
                "realized_vol_240m": sigma,
                "trade_count_60m": trades_60_sum,
                "trade_count_240m": trades_long_sum,
                "notional_60m": notional_60_sum,
                "notional_240m": notional_long_sum,
                "minutes_since_trade": min(minutes_since_trade, 1440),
            }
        )
    return labels


def write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    with path.open("w") as handle:
        for row in rows:
            handle.write(json.dumps(row, sort_keys=True) + "\n")


def prevalence_baseline(path: Path) -> dict[str, Any]:
    """A model-free metric sanity check for the first toy run.

    b0/b1/b2/b3 require the feature extractors and are deliberately not fabricated here.
    This baseline verifies that label eligibility, split assignment, and Brier scoring are
    wired correctly once the selected markets have sufficient trade activity.
    """
    train_rows = train_jumps = 0
    evaluation_labels: dict[str, list[int]] = {"validation": [], "test": []}
    for row in read_jsonl(path):
        if not row["eligible"]:
            continue
        if row.get("split") == "train":
            train_rows += 1
            train_jumps += int(row["y_jump"])
        elif row.get("split") in evaluation_labels:
            evaluation_labels[row["split"]].append(int(row["y_jump"]))
    if not train_rows or any(not rows for rows in evaluation_labels.values()):
        return {
            "name": "train_prevalence_sanity",
            "status": "insufficient_eligible_rows",
            "train_rows": train_rows,
            "validation_rows": len(evaluation_labels["validation"]),
            "test_rows": len(evaluation_labels["test"]),
        }
    probability = train_jumps / train_rows
    evaluations = {}
    for split, labels in evaluation_labels.items():
        evaluations[split] = {
            "rows": len(labels),
            "jump_rate": sum(labels) / len(labels),
            "brier": sum((label - probability) ** 2 for label in labels) / len(labels),
        }
    return {
        "name": "train_prevalence_sanity",
        "status": "ok",
        "train_rows": train_rows,
        "train_jump_rate": probability,
        "evaluation": evaluations,
    }


def main() -> None:
    ap = argparse.ArgumentParser(description="Build EventX's retained-trade toy slice")
    ap.add_argument("--venue", choices=["polymarket", "kalshi"], default="polymarket")
    ap.add_argument("--max-markets", type=int, default=20)
    ap.add_argument("--horizon-min", type=int, default=30)
    ap.add_argument("--trades", type=Path)
    ap.add_argument("--markets", type=Path)
    ap.add_argument("--out-dir", type=Path)
    args = ap.parse_args()

    cfg = yaml.safe_load(CONFIG_PATH.read_text())
    version = cfg["extract"]["version"]
    window = cfg["window"]
    start, end = parse_ts(window["start"]), parse_ts(window["end"])
    raw_dir = REPO_ROOT / "data" / version / "raw"
    trades_path = args.trades or raw_dir / f"trades_{args.venue}.jsonl"
    outcome_path = raw_dir / f"market_outcomes_{args.venue}.jsonl"
    out_dir = args.out_dir or REPO_ROOT / "data" / version / "toy"
    out_dir.mkdir(parents=True, exist_ok=True)
    if not trades_path.exists() or not outcome_path.exists():
        raise SystemExit("Toy slice awaits trade and market-outcome extracts; rerun after those jobs have produced files.")

    canonical = load_canonical_outcomes(outcome_path, args.venue)
    selection_path = args.markets or REPO_ROOT / "data" / version / "toy" / "selected_markets.jsonl"
    selected_rows = [
        row for row in (read_jsonl(selection_path) if selection_path.exists() else [])
        if row.get("venue") == args.venue
    ][: args.max_markets]
    if not selected_rows:
        raise SystemExit("No frozen cohort found; run eventx.tasks.select_toy_markets first.")
    if any(row.get("selection_basis") != "training_period_only" for row in selected_rows):
        raise SystemExit("Refusing a cohort that was not selected from training-period information only.")
    selected_keys = [
        (str(row["market_id"]), str(row["outcome_id"])) for row in selected_rows
    ]
    selection_source = str(selection_path)
    selected = set(selected_keys)
    metadata = {
        (str(row["market_id"]), str(row["outcome_id"])): row for row in selected_rows
    }
    grouped = collect_trades(trades_path, args.venue, start, end, canonical, selected)
    validation_boundary, test_boundary = split_boundaries(
        start,
        end,
        float(cfg["splits"]["validation_frac"]),
        float(cfg["splits"]["holdout_frac"]),
    )
    bars_path = out_dir / "bars.jsonl"
    labels_path = out_dir / f"labels_{args.horizon_min}m.jsonl"
    splits_path = out_dir / f"splits_{args.horizon_min}m.jsonl"
    bars_tmp = bars_path.with_suffix(".jsonl.tmp")
    labels_tmp = labels_path.with_suffix(".jsonl.tmp")
    splits_tmp = splits_path.with_suffix(".jsonl.tmp")
    n_bars = n_labels = n_eligible = 0
    split_counts: Counter[str] = Counter()
    eligible_split_counts: Counter[str] = Counter()
    markets_by_split: dict[str, set[str]] = {}
    eligible_markets_by_split: dict[str, set[str]] = {}
    with bars_tmp.open("w") as bars_handle, labels_tmp.open("w") as labels_handle, splits_tmp.open("w") as splits_handle:
        for key in selected_keys:
            market_bars = minute_bars(args.venue, key[0], key[1], grouped.get(key, []))
            market_labels = label_bars(
                market_bars,
                args.horizon_min,
                float(cfg["labels"]["k_sigma"]),
                int(cfg["labels"]["vol_window_bars"]),
                int(cfg["labels"]["min_trades"]),
                float(cfg["labels"]["min_notional"]),
                metadata.get(key, {}),
                validation_boundary,
                test_boundary,
            )
            for bar in market_bars:
                bars_handle.write(json.dumps(bar, sort_keys=True) + "\n")
            for row in market_labels:
                labels_handle.write(json.dumps(row, sort_keys=True) + "\n")
                splits_handle.write(
                    json.dumps(
                        {
                            "venue": row["venue"],
                            "market_id": row["market_id"],
                            "outcome_id": row["outcome_id"],
                            "ts": row["ts"],
                            "split": row["split"],
                        },
                        sort_keys=True,
                    )
                    + "\n"
                )
            n_bars += len(market_bars)
            n_labels += len(market_labels)
            n_eligible += sum(row["eligible"] for row in market_labels)
            split_counts.update(row["split"] for row in market_labels)
            for row in market_labels:
                split = row["split"]
                markets_by_split.setdefault(split, set()).add(key[0])
                if row["eligible"]:
                    eligible_split_counts[split] += 1
                    eligible_markets_by_split.setdefault(split, set()).add(key[0])
    bars_tmp.replace(bars_path)
    labels_tmp.replace(labels_path)
    splits_tmp.replace(splits_path)
    baseline = prevalence_baseline(labels_path)
    (out_dir / "baseline_sanity.json").write_text(json.dumps(baseline, indent=2, sort_keys=True) + "\n")
    manifest = {
        "extract_version": version,
        "window": window,
        "venue": args.venue,
        "horizon_min": args.horizon_min,
        "selected_outcomes": len(selected_keys),
        "selection_source": selection_source,
        "selection_basis": "training_period_only",
        "split_boundaries": {
            "validation_start": as_rfc3339(validation_boundary),
            "test_start": as_rfc3339(test_boundary),
            "purge_min": args.horizon_min,
        },
        "split_fractions": {
            "validation": float(cfg["splits"]["validation_frac"]),
            "test": float(cfg["splits"]["holdout_frac"]),
        },
        "bars": n_bars,
        "labels": n_labels,
        "eligible_labels": n_eligible,
        "split_counts": dict(split_counts),
        "eligible_split_counts": dict(eligible_split_counts),
        "markets_by_split": {
            split: len(markets) for split, markets in sorted(markets_by_split.items())
        },
        "eligible_markets_by_split": {
            split: len(markets)
            for split, markets in sorted(eligible_markets_by_split.items())
        },
        "baseline_status": baseline["status"],
    }
    (out_dir / "manifest.json").write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n")
    print(json.dumps(manifest, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
