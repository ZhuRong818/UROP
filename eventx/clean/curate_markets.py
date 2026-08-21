"""Curate raw market details into EventX's canonical binary-outcome contract."""

from __future__ import annotations

import argparse
import json
import re
from collections import Counter
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Iterator

import yaml

from eventx.settings import REPO_ROOT

CONFIG_PATH = REPO_ROOT / "eventx" / "config" / "eventx.yaml"

CATEGORY_TERMS = {
    "sports": {
        "afl", "baseball", "basketball", "cricket", "f1", "football", "game", "goal",
        "golf", "grand prix", "match", "mlb", "nba", "nfl", "nhl", "olympic", "race",
        "soccer", "tennis", "tournament", "ufc", "wimbledon", "win the",
    },
    "politics": {
        "ballot", "cabinet", "congress", "democrat", "election", "electoral", "governor",
        "minister", "parliament", "president", "prime minister", "republican", "senate", "vote",
    },
    "crypto": {
        "bitcoin", "btc", "crypto", "defi", "dogecoin", "ethereum", "eth", "solana", "token",
    },
    "macro": {
        "central bank", "cpi", "fed", "federal reserve", "gdp", "inflation", "interest rate",
        "recession", "treasury", "unemployment",
    },
}


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
                # A concurrently appended final line can be retried on the next run.
                continue


def parse_ts(value: Any) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(str(value).replace("Z", "+00:00")).astimezone(UTC)
    except ValueError:
        return None


def category_for(question: str) -> tuple[str, list[str]]:
    text = re.sub(r"\s+", " ", question.lower())
    scores = {
        category: sorted(term for term in terms if term in text)
        for category, terms in CATEGORY_TERMS.items()
    }
    scores = {category: terms for category, terms in scores.items() if terms}
    if not scores:
        return "other", []
    category = max(scores, key=lambda name: (len(scores[name]), -list(CATEGORY_TERMS).index(name)))
    return category, scores[category]


def overlaps(start: datetime | None, end: datetime | None, lo: datetime, hi: datetime) -> bool:
    return (start is None or start <= hi) and (end is None or end >= lo)


def write_jsonl_atomic(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    with temporary.open("w") as handle:
        for row in rows:
            handle.write(json.dumps(row, sort_keys=True) + "\n")
    temporary.replace(path)


def curate_venue(raw_dir: Path, venue: str, window_lo: datetime, window_hi: datetime) -> tuple[list[dict[str, Any]], Counter[str]]:
    detail_path = raw_dir / f"market_details_{venue}.jsonl"
    outcome_path = raw_dir / f"market_outcomes_{venue}.jsonl"
    details: dict[str, dict[str, Any]] = {}
    for row in read_jsonl(detail_path):
        market_id = str(row.get("market_id") or row.get("condition_id") or row.get("ticker") or "")
        if market_id:
            details[market_id] = row

    outcome_groups: dict[str, list[dict[str, Any]]] = {}
    for row in read_jsonl(outcome_path):
        market_id = str(row.get("market_id") or "")
        if market_id:
            outcome_groups.setdefault(market_id, []).append(row)

    report: Counter[str] = Counter(raw_detail_markets=len(details))
    curated: list[dict[str, Any]] = []
    for market_id, detail in details.items():
        rows = outcome_groups.get(market_id, [])
        canonical = [row for row in rows if row.get("is_binary") and row.get("canonical_side")]
        if len(canonical) != 1:
            report["dropped_no_unique_canonical_yes"] += 1
            continue
        outcome = canonical[0]
        outcome_id = outcome.get("outcome_id") or ("YES" if venue == "kalshi" else None)
        if not outcome_id:
            report["dropped_missing_outcome_id"] += 1
            continue
        question = str(outcome.get("question") or detail.get("question") or detail.get("title") or "")
        category, category_matches = category_for(question)
        start_raw = detail.get("start_date") or detail.get("open_time") or detail.get("created_time")
        end_raw = outcome.get("scheduled_close_ts") or detail.get("end_date") or detail.get("close_time")
        start_ts, end_ts = parse_ts(start_raw), parse_ts(end_raw)
        in_window = overlaps(start_ts, end_ts, window_lo, window_hi)
        curated.append(
            {
                "venue": venue,
                "market_id": market_id,
                "outcome_id": str(outcome_id),
                "outcome_name": str(outcome.get("outcome_name") or "YES"),
                "canonical_side": True,
                "is_binary": True,
                "question": question,
                "description": detail.get("description"),
                "category": category,
                "category_match_terms": category_matches,
                "start_ts": start_raw,
                "scheduled_close_ts": end_raw,
                "resolution_ts": outcome.get("resolution_ts") or detail.get("closed_time"),
                "status": outcome.get("status") or detail.get("status"),
                "active": detail.get("active"),
                "archived": detail.get("archived"),
                "enable_order_book": detail.get("enable_order_book"),
                "window_overlap": in_window,
                "extract_version": detail.get("_extract_version"),
            }
        )
        report["curated_binary_yes"] += 1
        report[f"category_{category}"] += 1
        report["window_overlap"] += int(in_window)
    return curated, report


def main() -> None:
    parser = argparse.ArgumentParser(description="Curate EventX binary market outcomes")
    parser.add_argument("--version")
    parser.add_argument("--out-dir", type=Path)
    args = parser.parse_args()

    config = yaml.safe_load(CONFIG_PATH.read_text())
    version = args.version or config["extract"]["version"]
    raw_dir = REPO_ROOT / "data" / version / "raw"
    out_dir = args.out_dir or REPO_ROOT / "data" / version / "curated"
    window_lo = parse_ts(config["window"]["start"])
    window_hi = parse_ts(config["window"]["end"])
    assert window_lo is not None and window_hi is not None

    all_rows: list[dict[str, Any]] = []
    combined: Counter[str] = Counter()
    by_venue: dict[str, dict[str, int]] = {}
    for venue in config["venues"]:
        rows, report = curate_venue(raw_dir, venue, window_lo, window_hi)
        all_rows.extend(rows)
        combined.update(report)
        by_venue[venue] = dict(sorted(report.items()))
    all_rows.sort(key=lambda row: (row["venue"], row["market_id"]))
    write_jsonl_atomic(out_dir / "markets.jsonl", all_rows)
    summary = {
        "version": version,
        "window": config["window"],
        "rows": len(all_rows),
        "by_venue": by_venue,
        "combined": dict(sorted(combined.items())),
    }
    (out_dir / "market_curation_report.json").write_text(
        json.dumps(summary, indent=2, sort_keys=True) + "\n"
    )
    print(json.dumps(summary, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
