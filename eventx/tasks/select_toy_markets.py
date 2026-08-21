"""Select a dense toy cohort using training-period information only."""

from __future__ import annotations

import argparse
import json
import math
from collections import defaultdict
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any, Iterator

import yaml

from eventx.settings import REPO_ROOT

CONFIG_PATH = REPO_ROOT / "eventx" / "config" / "eventx.yaml"


def read_jsonl(path: Path) -> Iterator[dict[str, Any]]:
    if not path.exists():
        return
    with path.open() as handle:
        for line in handle:
            if not line.strip():
                continue
            try:
                yield json.loads(line)
            except json.JSONDecodeError:
                continue


def parse_ts(value: Any) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(str(value).replace("Z", "+00:00")).astimezone(UTC)
    except ValueError:
        return None


def trade_values(row: dict[str, Any], venue: str) -> tuple[datetime, str, float] | None:
    try:
        if venue == "polymarket":
            ts = parse_ts(row["ts"])
            if ts is None:
                return None
            return ts, str(row["token_id"]), float(row["price"]) * float(row.get("size") or 0)
        ts = parse_ts(row["created_time"])
        if ts is None:
            return None
        price = float(row["yes_price"])
        if price > 1:
            price /= 100
        return ts, "YES", price * float(row.get("count") or 0)
    except (KeyError, TypeError, ValueError):
        return None


def write_jsonl_atomic(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    with temporary.open("w") as handle:
        for row in rows:
            handle.write(json.dumps(row, sort_keys=True) + "\n")
    temporary.replace(path)


def main() -> None:
    parser = argparse.ArgumentParser(description="Select dense markets for the EventX toy slice")
    parser.add_argument("--version")
    parser.add_argument("--max-markets", type=int, default=20)
    parser.add_argument("--min-active-days", type=int, default=3)
    parser.add_argument("--min-notional", type=float, default=1_000)
    parser.add_argument("--min-train-trades", type=int, default=100)
    parser.add_argument("--max-train-staleness-hours", type=float, default=72)
    parser.add_argument(
        "--purge-min",
        type=int,
        default=30,
        help="Exclude this many minutes immediately before validation begins",
    )
    parser.add_argument("--out-dir", type=Path)
    args = parser.parse_args()

    config = yaml.safe_load(CONFIG_PATH.read_text())
    version = args.version or config["extract"]["version"]
    root = REPO_ROOT / "data" / version
    curated_path = root / "curated" / "markets.jsonl"
    out_dir = args.out_dir or root / "toy"
    lo = parse_ts(config["window"]["start"])
    hi = parse_ts(config["window"]["end"])
    assert lo is not None and hi is not None
    validation_frac = float(config["splits"]["validation_frac"])
    holdout_frac = float(config["splits"]["holdout_frac"])
    if validation_frac <= 0 or holdout_frac <= 0 or validation_frac + holdout_frac >= 1:
        raise SystemExit("validation_frac and holdout_frac must be positive and sum to less than 1")
    validation_boundary = lo + (hi - lo) * (1 - validation_frac - holdout_frac)
    selection_end = validation_boundary - timedelta(minutes=args.purge_min)

    markets: dict[tuple[str, str], dict[str, Any]] = {}
    canonical: dict[tuple[str, str], str] = {}
    for row in read_jsonl(curated_path):
        if not row.get("window_overlap"):
            continue
        key = (str(row["venue"]), str(row["market_id"]))
        markets[key] = row
        canonical[key] = str(row["outcome_id"])

    counts: dict[tuple[str, str], int] = defaultdict(int)
    notionals: dict[tuple[str, str], float] = defaultdict(float)
    days: dict[tuple[str, str], set[str]] = defaultdict(set)
    hours: dict[tuple[str, str], set[str]] = defaultdict(set)
    first: dict[tuple[str, str], datetime] = {}
    last: dict[tuple[str, str], datetime] = {}
    for venue in config["venues"]:
        path = root / "raw" / f"trades_{venue}.jsonl"
        for row in read_jsonl(path):
            market_id = str(row.get("market_id") or row.get("condition_id") or row.get("ticker") or "")
            key = (venue, market_id)
            if key not in markets:
                continue
            values = trade_values(row, venue)
            if values is None:
                continue
            ts, outcome_id, notional = values
            if not lo <= ts < selection_end or outcome_id != canonical[key]:
                continue
            counts[key] += 1
            notionals[key] += notional
            days[key].add(ts.date().isoformat())
            hours[key].add(ts.strftime("%Y-%m-%dT%H"))
            first[key] = min(first.get(key, ts), ts)
            last[key] = max(last.get(key, ts), ts)

    ranked: list[dict[str, Any]] = []
    for key, n_trades in counts.items():
        market = markets[key]
        scheduled_close = parse_ts(market.get("scheduled_close_ts"))
        contract_spans_window = bool(scheduled_close and scheduled_close >= hi)
        active_days = len(days[key])
        active_hours = len(hours[key])
        notional = notionals[key]
        train_staleness_hours = (selection_end - last[key]).total_seconds() / 3600
        passes = (
            n_trades >= args.min_train_trades
            and active_days >= args.min_active_days
            and notional >= args.min_notional
            and contract_spans_window
            and train_staleness_hours <= args.max_train_staleness_hours
        )
        score = math.log1p(n_trades) + math.log1p(notional) + 0.1 * active_hours
        ranked.append(
            {
                "venue": key[0],
                "market_id": key[1],
                "outcome_id": canonical[key],
                "question": market["question"],
                "category": market["category"],
                "scheduled_close_ts": market.get("scheduled_close_ts"),
                "resolution_ts": market.get("resolution_ts"),
                "status": market.get("status"),
                "n_trades": n_trades,
                "train_trades": n_trades,
                "train_notional": round(notional, 6),
                "train_active_days": active_days,
                "train_active_hours": active_hours,
                "train_staleness_hours": round(train_staleness_hours, 6),
                "first_trade_ts": first[key].isoformat().replace("+00:00", "Z"),
                "last_trade_ts": last[key].isoformat().replace("+00:00", "Z"),
                "density_score": score,
                "passes_thresholds": passes,
                "selection_basis": "training_period_only",
                "contract_spans_window": contract_spans_window,
            }
        )
    ranked.sort(key=lambda row: (-row["passes_thresholds"], -row["density_score"], row["market_id"]))
    selected = [row for row in ranked if row["passes_thresholds"]][: args.max_markets]
    out_dir.mkdir(parents=True, exist_ok=True)
    write_jsonl_atomic(out_dir / "selected_markets.jsonl", selected)
    report = {
        "version": version,
        "window": config["window"],
        "selection_basis": "training_period_only",
        "contract_eligibility": "scheduled_close_at_or_after_window_end",
        "selection_window": {
            "start": lo.isoformat().replace("+00:00", "Z"),
            "end_exclusive": selection_end.isoformat().replace("+00:00", "Z"),
            "validation_boundary": validation_boundary.isoformat().replace("+00:00", "Z"),
            "purge_min": args.purge_min,
        },
        "thresholds": {
            "min_active_days": args.min_active_days,
            "min_notional": args.min_notional,
            "min_train_trades": args.min_train_trades,
            "max_train_staleness_hours": args.max_train_staleness_hours,
        },
        "curated_window_markets": len(markets),
        "markets_with_canonical_trades": len(ranked),
        "markets_passing": sum(row["passes_thresholds"] for row in ranked),
        "selected": len(selected),
        "top_ranked": ranked[:50],
    }
    (out_dir / "market_selection_report.json").write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n"
    )
    print(json.dumps(report, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
