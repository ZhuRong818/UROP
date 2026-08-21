"""Deterministic association of targeted news candidates to EventX toy markets."""

from __future__ import annotations

import argparse
import hashlib
import json
from collections import Counter
from pathlib import Path
from typing import Any, Iterator

import yaml

from eventx.features.kol_association import (
    content_hash,
    entities_for,
    match_market_v3,
    parse_ts,
)
from eventx.settings import REPO_ROOT

CONFIG_PATH = REPO_ROOT / "eventx" / "config" / "eventx.yaml"
ASSOCIATION_RULE = "news_rule_v1_semantic_v3"


def read_jsonl(path: Path) -> Iterator[dict[str, Any]]:
    with path.open() as handle:
        for line in handle:
            if not line.strip():
                continue
            try:
                yield json.loads(line)
            except json.JSONDecodeError:
                continue


def write_jsonl_atomic(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    with temporary.open("w") as handle:
        for row in rows:
            handle.write(json.dumps(row, sort_keys=True) + "\n")
    temporary.replace(path)


def article_text(row: dict[str, Any]) -> str:
    return " ".join(
        str(value).strip()
        for value in (
            row.get("headline") or row.get("title"),
            row.get("summary") or row.get("body"),
        )
        if value
    )


def article_id(row: dict[str, Any]) -> str:
    value = str(row.get("article_id") or row.get("id") or row.get("url") or "")
    return hashlib.sha256(value.encode()).hexdigest()[:24]


def main() -> None:
    parser = argparse.ArgumentParser(description="Associate EventX news to selected markets")
    parser.add_argument("--version")
    parser.add_argument("--markets", type=Path)
    parser.add_argument("--news", type=Path)
    parser.add_argument("--out-dir", type=Path)
    args = parser.parse_args()

    config = yaml.safe_load(CONFIG_PATH.read_text())
    version = args.version or config["extract"]["version"]
    root = REPO_ROOT / "data" / version
    markets_path = args.markets or root / "toy" / "selected_markets.jsonl"
    news_path = args.news or root / "raw" / "news_toy_search.jsonl"
    out_dir = args.out_dir or root / "curated"
    lo = parse_ts(config["window"]["start"])
    hi = parse_ts(config["window"]["end"])
    assert lo is not None and hi is not None

    markets = {str(row["market_id"]): row for row in read_jsonl(markets_path)}
    if not markets:
        raise SystemExit("No selected toy markets found.")
    entities = {
        market_id: entities_for(str(market["question"]))
        for market_id, market in markets.items()
    }
    associations: list[dict[str, Any]] = []
    seen_market_content: set[tuple[str, str, str]] = set()
    retrieval_rows = invalid_timestamps = outside_window = empty_text = 0
    duplicate_market_content = 0
    unique_articles_in_window: set[str] = set()
    matched_articles: set[str] = set()
    reasons: Counter[str] = Counter()
    matches_by_market: Counter[str] = Counter()
    retrieved_by_market: Counter[str] = Counter()
    for row in read_jsonl(news_path):
        retrieval_rows += 1
        market_id = str(row.get("_search_market_id") or "")
        market = markets.get(market_id)
        if market is None:
            continue
        retrieved_by_market[market_id] += 1
        ts = parse_ts(row.get("published_at") or row.get("ts"))
        if ts is None:
            invalid_timestamps += 1
            continue
        if not lo <= ts <= hi:
            outside_window += 1
            continue
        text = article_text(row)
        if not text:
            empty_text += 1
            continue
        url = str(row.get("url") or "")
        doc_id = article_id(row)
        unique_articles_in_window.add(doc_id)
        match_reasons, terms = match_market_v3(
            str(market["question"]),
            entities[market_id],
            text,
            set(),
        )
        if not match_reasons:
            continue
        digest = content_hash(text)
        dedupe_key = (market_id, str(market["outcome_id"]), digest)
        if dedupe_key in seen_market_content:
            duplicate_market_content += 1
            continue
        seen_market_content.add(dedupe_key)
        association = {
            "kind": "news_article",
            "doc_id": doc_id,
            "url": url,
            "publisher": row.get("publisher"),
            "category": row.get("category"),
            "article_symbol": row.get("symbol"),
            "news_symbol_mapped": False,
            "ts": row.get("published_at") or row.get("ts"),
            "venue": market["venue"],
            "market_id": market_id,
            "outcome_id": market["outcome_id"],
            "match_reason": match_reasons,
            "matched_terms": sorted(set(terms)),
            "content_hash": digest,
            "retrieval_query": row.get("_search_query"),
            "association_rule": ASSOCIATION_RULE,
            "semantic_rule_source": "eventx.features.kol_association.match_market_v3",
            "extract_version": version,
        }
        associations.append(association)
        matched_articles.add(doc_id)
        matches_by_market[market_id] += 1
        reasons.update(match_reasons)

    associations.sort(
        key=lambda row: (
            str(row["market_id"]),
            str(row["ts"]),
            str(row["doc_id"]),
        )
    )
    write_jsonl_atomic(out_dir / "news_market_assoc.jsonl", associations)
    report = {
        "version": version,
        "association_rule": ASSOCIATION_RULE,
        "semantic_rule_source": "rule_v3",
        "window": config["window"],
        "selected_markets": len(markets),
        "retrieval_rows": retrieval_rows,
        "unique_articles_in_window": len(unique_articles_in_window),
        "invalid_timestamps": invalid_timestamps,
        "outside_window": outside_window,
        "empty_text": empty_text,
        "matched_articles": len(matched_articles),
        "associations": len(associations),
        "duplicate_market_content_removed": duplicate_market_content,
        "markets_with_retrieval": sum(value > 0 for value in retrieved_by_market.values()),
        "markets_with_matches": sum(value > 0 for value in matches_by_market.values()),
        "retrieved_by_market": dict(sorted(retrieved_by_market.items())),
        "matches_by_market": dict(sorted(matches_by_market.items())),
        "matches_by_reason": dict(sorted(reasons.items())),
        "symbol_mapping": {
            "mapped_markets": 0,
            "note": (
                "The toy cohort contains event markets without canonical financial ticker "
                "mappings. Provider article symbols are not treated as market mappings."
            ),
        },
    }
    (out_dir / "news_association_report.json").write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n"
    )
    print(json.dumps(report, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
