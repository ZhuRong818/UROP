"""Label-blind feasibility audit for EventX v4 news-quality features."""

from __future__ import annotations

from collections import Counter, defaultdict
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import re
from typing import Any, Iterator

import numpy as np

from eventx.settings import REPO_ROOT
from eventx.tasks.prepare_v3_1_historical_development_arrays import (
    NEWS_DTYPE,
    sha256_file,
)


NEWS = REPO_ROOT / "data/v3_historical/primary/label_blind_inputs/news.jsonl"
COHORT = REPO_ROOT / "data/v3_1_historical/primary/label_blind_inputs/cohort.jsonl"
ASSOCIATIONS = (
    REPO_ROOT
    / "data/v3_1_historical/primary/development/prepared/news_associations.bin"
)
KALSHI_METADATA = (
    REPO_ROOT
    / "data/v3_historical/feasibility/raw/kalshi_markets/kalshi_markets.jsonl"
)
POLY_METADATA = (
    REPO_ROOT
    / "data/v3_historical/feasibility/raw/polymarket_markets/polymarket_markets.jsonl"
)
OUTPUT = REPO_ROOT / "data/v4/discovery/feature_feasibility"
REPORT = OUTPUT / "report.json"
MANIFEST = OUTPUT / "manifest.json"
TOKEN = re.compile(r"[a-z0-9]+", re.IGNORECASE)


def read_jsonl(path: Path) -> Iterator[dict[str, Any]]:
    with path.open(encoding="utf-8") as handle:
        for line in handle:
            if line.strip():
                yield json.loads(line)


def relative(path: Path) -> str:
    return str(path.relative_to(REPO_ROOT))


def atomic_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n")
    os.replace(temporary, path)


def normalized_headline(value: str) -> str:
    return " ".join(TOKEN.findall(value.lower()))


def main() -> None:
    if REPORT.exists() or MANIFEST.exists():
        raise SystemExit("v4 feature feasibility artifact already exists")
    counters: Counter[str] = Counter()
    publishers: Counter[str] = Counter()
    sources: Counter[str] = Counter()
    categories: Counter[str] = Counter()
    days: Counter[str] = Counter()
    text_lengths: list[int] = []
    story_publishers: dict[str, set[str]] = defaultdict(set)
    story_rows: Counter[str] = Counter()
    for row in read_jsonl(NEWS):
        counters["rows"] += 1
        headline = str(row.get("headline") or "").strip()
        summary = str(row.get("summary") or "").strip()
        publisher = str(row.get("publisher") or "").strip()
        source = str(row.get("source_endpoint") or row.get("source") or "").strip()
        category = str(row.get("category") or "").strip()
        available = str(row.get("available_at") or "")
        counters["headline_nonempty"] += int(bool(headline))
        counters["summary_nonempty"] += int(bool(summary))
        counters["headline_or_summary_nonempty"] += int(bool(headline or summary))
        counters["publisher_nonempty"] += int(bool(publisher))
        counters["source_nonempty"] += int(bool(source))
        counters["symbol_nonempty"] += int(bool(row.get("symbol")))
        counters["related_symbols_nonempty"] += int(bool(row.get("related_symbols")))
        counters["body_present_in_export"] += int("body" in row and bool(row.get("body")))
        counters["engagement_field_present"] += int(
            any(key in row for key in ("likes", "shares", "reposts", "views", "comments"))
        )
        if publisher:
            publishers[publisher] += 1
        if source:
            sources[source] += 1
        if category:
            categories[category] += 1
        if available:
            days[available[:10]] += 1
        text_lengths.append(len((headline + " " + summary).strip()))
        fingerprint = normalized_headline(headline)
        if len(fingerprint) >= 20:
            story_rows[fingerprint] += 1
            if publisher:
                story_publishers[fingerprint].add(publisher.lower())

    association_count = ASSOCIATIONS.stat().st_size // NEWS_DTYPE.itemsize
    associations = np.memmap(
        ASSOCIATIONS, mode="r", dtype=NEWS_DTYPE, shape=(association_count,)
    )
    associated_markets = int(len(np.unique(associations["market"])))
    multi_publisher = {
        key: values for key, values in story_publishers.items() if len(values) >= 2
    }
    multi_publisher_rows = sum(story_rows[key] for key in multi_publisher)

    cohort = list(read_jsonl(COHORT))
    kalshi_metadata = {
        str(row["ticker"]): row for row in read_jsonl(KALSHI_METADATA)
    }
    poly_metadata = {
        str(row["condition_id"]): row for row in read_jsonl(POLY_METADATA)
    }
    event_keys: Counter[str] = Counter()
    event_key_sources: Counter[str] = Counter()
    terminal_known = 0
    for market in cohort:
        venue = str(market["venue"])
        market_id = str(market["market_id"])
        metadata = (
            kalshi_metadata.get(market_id)
            if venue == "kalshi"
            else poly_metadata.get(market_id)
        )
        if metadata is None:
            continue
        if venue == "kalshi" and metadata.get("event_ticker"):
            key = "kalshi:" + str(metadata["event_ticker"])
            event_key_sources["native_event_ticker"] += 1
        else:
            # Conservative fallback: each condition is its own cluster. A future
            # native event identifier may merge clusters, never split them post hoc.
            key = venue + ":condition:" + market_id
            event_key_sources["condition_fallback"] += 1
        event_keys[key] += 1
        terminal_known += int(
            bool(
                metadata.get("close_time")
                or metadata.get("expiration_time")
                or metadata.get("end_date")
            )
        )

    lengths = np.asarray(text_lengths, dtype=np.int64)
    rows = counters["rows"]
    field_rates = {
        key: counters[key] / rows
        for key in (
            "headline_nonempty",
            "summary_nonempty",
            "headline_or_summary_nonempty",
            "publisher_nonempty",
            "source_nonempty",
            "symbol_nonempty",
            "related_symbols_nonempty",
            "body_present_in_export",
            "engagement_field_present",
        )
    }
    capabilities = {
        "point_in_time_availability": True,
        "headline_summary_semantic_input": field_rates["headline_or_summary_nonempty"] >= 0.99,
        "publisher_diversity": field_rates["publisher_nonempty"] >= 0.90,
        "cross_publisher_diffusion_proxy": len(multi_publisher) >= 100,
        "historical_market_relative_novelty": len(days) >= 56 and association_count >= 200,
        "native_event_cluster_for_every_market": event_key_sources["condition_fallback"] == 0,
        "full_article_body": field_rates["body_present_in_export"] >= 0.90,
        "true_social_virality": field_rates["engagement_field_present"] >= 0.90,
    }
    required = (
        "point_in_time_availability",
        "headline_summary_semantic_input",
        "publisher_diversity",
        "cross_publisher_diffusion_proxy",
        "historical_market_relative_novelty",
    )
    passed = all(capabilities[key] for key in required)
    report = {
        "audit_id": "eventx-v4-feature-feasibility-20260902",
        "created_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "status": "passed_for_quality_and_diffusion_proxy" if passed else "failed",
        "label_blind": True,
        "labels_predictions_or_outcomes_read": False,
        "integrity_pass": passed,
        "news": {
            "rows": rows,
            "calendar_days": len(days),
            "field_rates": field_rates,
            "text_length_characters": {
                "median": float(np.median(lengths)),
                "p10": float(np.quantile(lengths, 0.10)),
                "p90": float(np.quantile(lengths, 0.90)),
            },
            "unique_publishers": len(publishers),
            "unique_source_endpoints": len(sources),
            "top_publishers": publishers.most_common(20),
            "source_endpoints": dict(sources),
            "categories": dict(categories),
            "exact_headline_story_clusters": len(story_publishers),
            "cross_publisher_story_clusters": len(multi_publisher),
            "rows_in_cross_publisher_story_clusters": multi_publisher_rows,
        },
        "associations": {
            "events": association_count,
            "markets_with_events": associated_markets,
        },
        "market_structure": {
            "cohort_markets": len(cohort),
            "event_clusters": len(event_keys),
            "markets_in_multi_contract_event_clusters": sum(
                count for count in event_keys.values() if count > 1
            ),
            "largest_event_cluster": max(event_keys.values(), default=0),
            "event_key_sources": dict(event_key_sources),
            "terminal_time_known": terminal_known,
        },
        "capabilities": capabilities,
        "required_capabilities": list(required),
        "decisions": {
            "primary_text": "headline plus summary",
            "novelty": "supported as a derived point-in-time feature",
            "relevance": "supported with a frozen local vectorizer",
            "diffusion": "supported only as cross-publisher story diffusion",
            "virality": "not supported; no engagement/repost fields",
            "body_features": "not supported by the saved source-valid export",
            "event_clustering": (
                "native Kalshi event ticker; conservative condition-level fallback "
                "where Lumid supplies no native event identifier"
            ),
        },
        "inputs": [
            {"path": relative(path), "sha256": sha256_file(path)}
            for path in (NEWS, COHORT, ASSOCIATIONS, KALSHI_METADATA, POLY_METADATA)
        ],
    }
    atomic_json(REPORT, report)
    atomic_json(
        MANIFEST,
        {
            "audit_id": report["audit_id"],
            "status": report["status"],
            "artifacts": [
                {"path": relative(path), "sha256": sha256_file(path)}
                for path in (REPORT, Path(__file__).resolve())
            ],
            "inputs": report["inputs"],
        },
    )
    print(json.dumps({
        "status": report["status"],
        "integrity_pass": passed,
        "news_rows": rows,
        "field_rates": field_rates,
        "cross_publisher_story_clusters": len(multi_publisher),
        "association_events": association_count,
        "associated_markets": associated_markets,
        "capabilities": capabilities,
    }, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
