"""Freeze the prospective EventX v2 cohort after the sealed selection window."""

from __future__ import annotations

import argparse
from collections import Counter, defaultdict
from datetime import datetime, timezone
import hashlib
import json
import math
from pathlib import Path
from typing import Any, Iterator

from eventx.settings import REPO_ROOT


DEFAULT_PROTOCOL = REPO_ROOT / "eventx" / "release" / "v2_1" / "protocol.json"
DEFAULT_TAXONOMY_GUIDE = REPO_ROOT / "eventx" / "release" / "v2" / "TAXONOMY_GUIDE.md"
DEFAULT_MARKETS = REPO_ROOT / "data" / "v2_1" / "taxonomy" / "market_categories.jsonl"
DEFAULT_AUDIT = REPO_ROOT / "data" / "v2_1" / "taxonomy" / "audit_report.json"
DEFAULT_ACTIVITY = REPO_ROOT / "data" / "v2_1" / "selection" / "market_activity.jsonl"
DEFAULT_OUTPUT_DIR = REPO_ROOT / "data" / "v2_1" / "cohort"
TERMINAL_STATUSES = {"closed", "determined", "finalized", "resolved", "settled"}
PROHIBITED_FIELDS = {
    "label",
    "target",
    "y",
    "y_jump",
    "forward_return",
    "forward_logodds",
    "prediction",
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


def parse_utc(value: str | None) -> datetime | None:
    if not value:
        return None
    return datetime.fromisoformat(str(value).replace("Z", "+00:00")).astimezone(timezone.utc)


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


def ensure_label_blind(row: dict[str, Any], path: Path) -> None:
    found = sorted(PROHIBITED_FIELDS & {key.lower() for key in row})
    if found:
        raise ValueError(f"{path} contains prohibited post-selection fields: {found}")


def verify_taxonomy_audit(audit: dict[str, Any]) -> None:
    failures: list[str] = []
    if audit.get("status") != "accepted":
        failures.append("status is not accepted")
    if int(audit.get("review_rows", 0)) < 200:
        failures.append("fewer than 200 reviewed rows")
    overall = audit.get("overall", {})
    if float(overall.get("precision", 0)) < 0.90:
        failures.append("overall precision below 0.90")
    if float(overall.get("recall", 0)) < 0.90:
        failures.append("overall recall below 0.90")
    for category, values in audit.get("by_category", {}).items():
        if int(values.get("review_rows", 0)) >= 20 and float(values.get("precision", 0)) < 0.80:
            failures.append(f"{category} precision below 0.80")
    if failures:
        raise ValueError("taxonomy audit failed: " + "; ".join(failures))


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
    parser.add_argument("--taxonomy-guide", type=Path, default=DEFAULT_TAXONOMY_GUIDE)
    parser.add_argument("--markets", type=Path, default=DEFAULT_MARKETS)
    parser.add_argument("--taxonomy-audit", type=Path, default=DEFAULT_AUDIT)
    parser.add_argument("--activity", type=Path, default=DEFAULT_ACTIVITY)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--as-of", help="UTC RFC3339 time; used only for deterministic replay")
    args = parser.parse_args()

    protocol = load_object(args.protocol)
    selection_end = parse_utc(protocol["windows"]["selection"]["end_exclusive"])
    assert selection_end is not None
    now = parse_utc(args.as_of) if args.as_of else datetime.now(timezone.utc)
    assert now is not None
    if now < selection_end:
        raise SystemExit(
            f"temporal seal: cohort cannot be frozen before {rfc3339(selection_end)}; "
            f"current time is {rfc3339(now)}"
        )

    audit = load_object(args.taxonomy_audit)
    verify_taxonomy_audit(audit)
    allowed_categories = set(protocol["cohort"]["categories"])
    markets: dict[tuple[str, str], dict[str, Any]] = {}
    for row in read_jsonl(args.markets):
        ensure_label_blind(row, args.markets)
        venue = str(row.get("venue") or "")
        market_id = str(row.get("market_id") or "")
        category = str(row.get("category") or "")
        if category not in allowed_categories:
            raise ValueError(f"invalid corrected category {category!r}")
        if row.get("is_binary") is not True or row.get("canonical_side") is not True:
            continue
        key = (venue, market_id)
        if not venue or not market_id or key in markets:
            raise ValueError(f"invalid or duplicate canonical market {key}")
        markets[key] = row

    activity: dict[tuple[str, str], dict[str, Any]] = {}
    for row in read_jsonl(args.activity):
        ensure_label_blind(row, args.activity)
        key = (str(row.get("venue") or ""), str(row.get("market_id") or ""))
        if not all(key) or key in activity:
            raise ValueError(f"invalid or duplicate activity row {key}")
        activity[key] = row

    thresholds = protocol["cohort"]["thresholds"]
    required_close = parse_utc(thresholds["scheduled_close_at_or_after"])
    assert required_close is not None
    staleness_hours_max = float(thresholds["last_trade_staleness_hours_max"])
    eligible: list[dict[str, Any]] = []
    drops: Counter[str] = Counter()
    for key, market in markets.items():
        state = activity.get(key)
        if state is None:
            drops["no_selection_activity"] += 1
            continue
        close = parse_utc(market.get("scheduled_close_ts"))
        resolution = parse_utc(market.get("resolution_ts"))
        status = str(market.get("status") or "").lower()
        last_trade = parse_utc(state.get("last_trade_ts"))
        if close is None or close < required_close:
            drops["scheduled_close_too_early_or_missing"] += 1
            continue
        if resolution is not None and resolution <= selection_end:
            drops["resolved_by_selection_end"] += 1
            continue
        if status in TERMINAL_STATUSES:
            drops["terminal_status"] += 1
            continue
        if int(state.get("trades", 0)) < int(thresholds["min_trades"]):
            drops["below_min_trades"] += 1
            continue
        if float(state.get("notional", 0)) < float(thresholds["min_notional"]):
            drops["below_min_notional"] += 1
            continue
        if int(state.get("active_days", 0)) < int(thresholds["min_active_days"]):
            drops["below_min_active_days"] += 1
            continue
        if last_trade is None:
            drops["missing_last_trade"] += 1
            continue
        staleness_hours = (selection_end - last_trade).total_seconds() / 3600
        if staleness_hours < 0 or staleness_hours > staleness_hours_max:
            drops["last_trade_stale_or_after_window"] += 1
            continue
        score = (
            math.log1p(int(state["trades"]))
            + math.log1p(float(state["notional"]))
            + 0.1 * int(state.get("active_hours", 0))
        )
        eligible.append(
            {
                "active_days": int(state["active_days"]),
                "active_hours": int(state.get("active_hours", 0)),
                "canonical_side": True,
                "category": market["category"],
                "cohort_score": score,
                "last_trade_ts": state["last_trade_ts"],
                "market_id": key[1],
                "notional": float(state["notional"]),
                "outcome_id": str(market["outcome_id"]),
                "question": market.get("question"),
                "scheduled_close_ts": market["scheduled_close_ts"],
                "taxonomy_version": market.get("taxonomy_version"),
                "trades": int(state["trades"]),
                "venue": key[0],
            }
        )

    grouped: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)
    for row in eligible:
        grouped[(row["venue"], row["category"])].append(row)
    selected: list[dict[str, Any]] = []
    max_per_group = int(protocol["cohort"]["max_per_venue_category"])
    group_counts: dict[str, int] = {}
    for key in sorted(grouped):
        ranked = sorted(
            grouped[key],
            key=lambda row: (-row["cohort_score"], row["market_id"]),
        )
        retained = ranked[:max_per_group]
        selected.extend(retained)
        group_counts[f"{key[0]}:{key[1]}"] = len(retained)
    selected.sort(key=lambda row: (row["venue"], row["category"], -row["cohort_score"], row["market_id"]))

    maximum_total = (
        len(protocol["cohort"]["venues"])
        * len(protocol["cohort"]["categories"])
        * max_per_group
    )
    if len(selected) > maximum_total:
        raise AssertionError("selected cohort exceeds preregistered maximum")

    selected_path = args.output_dir / "selected_markets.jsonl"
    atomic_write_jsonl(selected_path, selected)
    report = {
        "drop_reasons": dict(sorted(drops.items())),
        "eligible_before_caps": len(eligible),
        "frozen_at": rfc3339(now),
        "group_counts": group_counts,
        "input_hashes": {
            relative(args.activity): sha256_file(args.activity),
            relative(args.markets): sha256_file(args.markets),
            relative(args.protocol): sha256_file(args.protocol),
            relative(args.taxonomy_audit): sha256_file(args.taxonomy_audit),
            relative(args.taxonomy_guide): sha256_file(args.taxonomy_guide),
        },
        "label_blind": True,
        "labels_read": [],
        "output": {
            "bytes": selected_path.stat().st_size,
            "path": relative(selected_path),
            "sha256": sha256_file(selected_path),
        },
        "protocol_id": protocol["protocol_id"],
        "selected_markets": len(selected),
        "selection_end_exclusive": rfc3339(selection_end),
        "status": "frozen",
        "taxonomy_version": audit.get("taxonomy_version"),
    }
    atomic_write_json(args.output_dir / "cohort_freeze_manifest.json", report)
    print(
        json.dumps(
            {
                "eligible_before_caps": len(eligible),
                "label_blind": True,
                "selected_markets": len(selected),
                "status": "frozen",
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
