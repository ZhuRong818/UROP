"""Aggregate label-blind v2 selection-window market activity from retained trades."""

from __future__ import annotations

import argparse
from collections import defaultdict
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
from typing import Any, Iterator

from eventx.settings import REPO_ROOT


DEFAULT_PROTOCOL = REPO_ROOT / "eventx" / "release" / "v2_1" / "protocol.json"
DEFAULT_MARKETS = REPO_ROOT / "data" / "v2_1" / "taxonomy" / "market_categories.jsonl"
DEFAULT_RAW_DIR = REPO_ROOT / "data" / "v2_1" / "selection" / "reconciled"
DEFAULT_OUTPUT_DIR = REPO_ROOT / "data" / "v2_1" / "selection"
PROHIBITED_MARKET_FIELDS = {
    "label",
    "target",
    "y",
    "y_jump",
    "forward_return",
    "forward_logodds",
    "prediction",
    "probability_prediction",
    "metric",
}


def read_jsonl(path: Path) -> Iterator[dict[str, Any]]:
    with path.open() as handle:
        for line_number, line in enumerate(handle, start=1):
            if not line.strip():
                continue
            value = json.loads(line)
            if not isinstance(value, dict):
                raise ValueError(f"{path}:{line_number} must be a JSON object")
            yield value


def load_object(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text())
    if not isinstance(value, dict):
        raise ValueError(f"{path} must contain a JSON object")
    return value


def parse_utc(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00")).astimezone(timezone.utc)


def rfc3339(value: datetime) -> str:
    return value.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def relative(path: Path) -> str:
    return str(path.resolve().relative_to(REPO_ROOT.resolve()))


def ensure_label_blind_market_row(row: dict[str, Any], path: Path) -> None:
    found = sorted(PROHIBITED_MARKET_FIELDS & {key.lower() for key in row})
    if found:
        raise ValueError(f"{path} contains prohibited post-selection fields: {found}")


def load_markets(path: Path, allowed_categories: set[str]) -> dict[tuple[str, str], dict[str, Any]]:
    markets: dict[tuple[str, str], dict[str, Any]] = {}
    for row in read_jsonl(path):
        ensure_label_blind_market_row(row, path)
        venue = str(row.get("venue") or "")
        market_id = str(row.get("market_id") or "")
        category = str(row.get("category") or "")
        if not venue or not market_id:
            raise ValueError(f"{path} has a row without venue/market_id")
        if category not in allowed_categories:
            raise ValueError(f"{path} has invalid category {category!r}")
        if row.get("is_binary") is not True or row.get("canonical_side") is not True:
            continue
        key = (venue, market_id)
        if key in markets:
            raise ValueError(f"{path} contains duplicate canonical market {key}")
        markets[key] = row
    return markets


def normalized_trade(
    row: dict[str, Any],
    venue: str,
) -> tuple[datetime, str, float, str] | None:
    try:
        if venue == "polymarket":
            timestamp = parse_utc(str(row["ts"]))
            outcome_id = str(row["token_id"])
            price = float(row["price"])
            size = float(row.get("size") or 0)
        else:
            timestamp = parse_utc(str(row["created_time"]))
            outcome_id = "YES"
            price = float(row["yes_price"])
            if price > 1:
                price /= 100
            size = float(row.get("count") or 0)
        market_id = str(
            row.get("market_id")
            or row.get("condition_id")
            or row.get("market_ticker")
            or row.get("ticker")
            or ""
        )
        if not market_id or price < 0 or size < 0:
            return None
        return timestamp, outcome_id, price * size, market_id
    except (KeyError, TypeError, ValueError):
        return None


def trade_identity(row: dict[str, Any], venue: str) -> str:
    material = [
        venue,
        row.get("trade_id") or row.get("id") or row.get("transaction_hash"),
        row.get("market_id") or row.get("condition_id") or row.get("market_ticker"),
        row.get("token_id"),
        row.get("ts") or row.get("created_time"),
        row.get("price") or row.get("yes_price"),
        row.get("size") or row.get("count"),
        row.get("side") or row.get("taker_side"),
    ]
    encoded = json.dumps(material, separators=(",", ":")).encode()
    return f"{venue}:{hashlib.sha256(encoded).hexdigest()}"


def atomic_write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    with temporary.open("w") as handle:
        for row in rows:
            handle.write(json.dumps(row, sort_keys=True) + "\n")
    temporary.replace(path)


def atomic_write_json(path: Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n")
    temporary.replace(path)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--protocol", type=Path, default=DEFAULT_PROTOCOL)
    parser.add_argument("--markets", type=Path, default=DEFAULT_MARKETS)
    parser.add_argument("--raw-dir", type=Path, default=DEFAULT_RAW_DIR)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--as-of", help="UTC RFC3339 time; used only for deterministic replay")
    args = parser.parse_args()

    protocol = load_object(args.protocol)
    start = parse_utc(protocol["windows"]["selection"]["start"])
    end = parse_utc(protocol["windows"]["selection"]["end_exclusive"])
    now = parse_utc(args.as_of) if args.as_of else datetime.now(timezone.utc)
    if now < end:
        raise SystemExit(
            f"temporal seal: selection window closes at {rfc3339(end)}; "
            f"activity cannot be finalized at {rfc3339(now)}"
        )

    allowed_categories = set(protocol["cohort"]["categories"])
    markets = load_markets(args.markets, allowed_categories)
    by_market: dict[tuple[str, str], dict[str, Any]] = defaultdict(
        lambda: {
            "active_days": set(),
            "active_hours": set(),
            "last_trade_ts": None,
            "notional": 0.0,
            "trades": 0,
        }
    )
    source_rows: dict[str, int] = {}
    retained_rows: dict[str, int] = {}
    duplicate_rows: dict[str, int] = {}

    for venue in protocol["cohort"]["venues"]:
        trades_path = args.raw_dir / f"trades_{venue}.jsonl"
        if not trades_path.is_file():
            raise FileNotFoundError(trades_path)
        seen: set[str] = set()
        source_rows[venue] = 0
        retained_rows[venue] = 0
        duplicate_rows[venue] = 0
        for row in read_jsonl(trades_path):
            source_rows[venue] += 1
            fields = normalized_trade(row, venue)
            if fields is None:
                continue
            timestamp, outcome_id, notional, market_id = fields
            if not start <= timestamp < end:
                continue
            market = markets.get((venue, market_id))
            if market is None:
                continue
            if str(market.get("outcome_id")) != outcome_id:
                continue
            identity = trade_identity(row, venue)
            if identity in seen:
                duplicate_rows[venue] += 1
                continue
            seen.add(identity)
            retained_rows[venue] += 1
            state = by_market[(venue, market_id)]
            state["trades"] += 1
            state["notional"] += notional
            state["active_days"].add(timestamp.date().isoformat())
            state["active_hours"].add(timestamp.strftime("%Y-%m-%dT%H:00:00Z"))
            previous = state["last_trade_ts"]
            if previous is None or timestamp > previous:
                state["last_trade_ts"] = timestamp

    rows: list[dict[str, Any]] = []
    for (venue, market_id), state in sorted(by_market.items()):
        market = markets[(venue, market_id)]
        rows.append(
            {
                "active_days": len(state["active_days"]),
                "active_hours": len(state["active_hours"]),
                "category": market["category"],
                "last_trade_ts": rfc3339(state["last_trade_ts"]),
                "market_id": market_id,
                "notional": state["notional"],
                "selection_end_exclusive": rfc3339(end),
                "selection_start": rfc3339(start),
                "trades": state["trades"],
                "venue": venue,
            }
        )

    output_path = args.output_dir / "market_activity.jsonl"
    atomic_write_jsonl(output_path, rows)
    report = {
        "activity_rows": len(rows),
        "duplicate_rows_removed": duplicate_rows,
        "generated_at": rfc3339(now),
        "input_hashes": {
            relative(args.markets): sha256_file(args.markets),
            relative(args.protocol): sha256_file(args.protocol),
            **{
                relative(args.raw_dir / f"trades_{venue}.jsonl"): sha256_file(
                    args.raw_dir / f"trades_{venue}.jsonl"
                )
                for venue in protocol["cohort"]["venues"]
            },
        },
        "label_blind": True,
        "labels_read": [],
        "output": {
            "path": relative(output_path),
            "sha256": sha256_file(output_path),
        },
        "protocol_id": protocol["protocol_id"],
        "retained_selection_rows": retained_rows,
        "selection_end_exclusive": rfc3339(end),
        "selection_start": rfc3339(start),
        "source_rows_scanned": source_rows,
    }
    atomic_write_json(args.output_dir / "activity_report.json", report)
    print(json.dumps({key: report[key] for key in ("activity_rows", "label_blind")}, indent=2))


if __name__ == "__main__":
    main()
