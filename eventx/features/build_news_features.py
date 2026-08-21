"""Build leakage-safe structured-news features for the frozen EventX toy cohort."""

from __future__ import annotations

import argparse
import bisect
import json
import math
from collections import Counter
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Iterator, NamedTuple

from eventx.features.build_kol_features import (
    RECENCY_CAP_MIN,
    cadence_match,
    hash_file,
    parse_ts,
)
from eventx.settings import REPO_ROOT

WINDOWS_MIN = (60, 360, 1440)


class NewsEvent(NamedTuple):
    ts: datetime
    publisher: str
    category: str
    content_hash: str


def read_jsonl(path: Path) -> Iterator[dict[str, Any]]:
    with path.open() as handle:
        for line in handle:
            if line.strip():
                yield json.loads(line)


def relative(path: Path) -> str:
    return str(path.resolve().relative_to(REPO_ROOT.resolve()))


def verify_frozen_files(manifest: dict[str, Any]) -> None:
    failures = []
    for name, expected in manifest["files"].items():
        path = REPO_ROOT / name
        if not path.exists():
            failures.append(f"{name}:missing")
        elif hash_file(path)["sha256"] != expected["sha256"]:
            failures.append(f"{name}:sha256_mismatch")
    if failures:
        raise SystemExit("Frozen news-rule verification failed: " + ", ".join(failures))


def load_events(
    path: Path,
) -> tuple[dict[tuple[str, str, str], list[NewsEvent]], dict[str, int]]:
    grouped: dict[tuple[str, str, str], list[NewsEvent]] = {}
    seen: set[tuple[str, str, str, str]] = set()
    stats = {
        "association_rows": 0,
        "duplicate_market_content": 0,
        "invalid_timestamp": 0,
    }
    for row in read_jsonl(path):
        stats["association_rows"] += 1
        if row.get("association_rule") != "news_rule_v1_semantic_v3":
            raise SystemExit("News association file contains an unexpected rule.")
        key = (str(row["venue"]), str(row["market_id"]), str(row["outcome_id"]))
        content_key = (*key, str(row["content_hash"]))
        if content_key in seen:
            stats["duplicate_market_content"] += 1
            continue
        seen.add(content_key)
        try:
            ts = parse_ts(row["ts"])
        except (KeyError, TypeError, ValueError):
            stats["invalid_timestamp"] += 1
            continue
        grouped.setdefault(key, []).append(
            NewsEvent(
                ts=ts,
                publisher=str(row.get("publisher") or "__missing__").strip().lower(),
                category=str(row.get("category") or "__missing__").strip().lower(),
                content_hash=str(row["content_hash"]),
            )
        )
    for events in grouped.values():
        events.sort(key=lambda event: (event.ts, event.content_hash))
    return grouped, stats


def diversity(values: list[str]) -> tuple[int, float, float]:
    if not values:
        return 0, 0.0, 0.0
    counts = Counter(values)
    total = len(values)
    entropy = -sum((count / total) * math.log(count / total) for count in counts.values())
    normalized = entropy / math.log(len(counts)) if len(counts) > 1 else 0.0
    return len(counts), normalized, max(counts.values()) / total


def point_in_time_features(
    events: list[NewsEvent],
    times: list[datetime],
    ts: datetime,
) -> tuple[dict[str, int | float], datetime | None]:
    right = bisect.bisect_right(times, ts)
    features: dict[str, int | float] = {"news_symbol_mapped": 0}
    slices: dict[int, list[NewsEvent]] = {}
    for minutes in WINDOWS_MIN:
        left = bisect.bisect_right(times, ts - timedelta(minutes=minutes), hi=right)
        rows = events[left:right]
        slices[minutes] = rows
        suffix = f"{minutes}m"
        features[f"news_article_count_{suffix}"] = len(rows)
        features[f"news_unique_publishers_{suffix}"] = len(
            {event.publisher for event in rows}
        )
        features[f"news_unique_categories_{suffix}"] = len(
            {event.category for event in rows}
        )
    _publisher_count, publisher_entropy, top_share = diversity(
        [event.publisher for event in slices[1440]]
    )
    features["news_publisher_entropy_24h"] = publisher_entropy
    features["news_top_publisher_share_24h"] = top_share
    latest = events[right - 1].ts if right else None
    features["news_has_history"] = int(latest is not None)
    features["news_minutes_since_latest"] = (
        min((ts - latest).total_seconds() / 60, RECENCY_CAP_MIN)
        if latest is not None
        else float(RECENCY_CAP_MIN)
    )
    recent_6h = len(slices[360])
    prior_end = bisect.bisect_right(times, ts - timedelta(minutes=360), hi=right)
    prior_start = bisect.bisect_right(
        times,
        ts - timedelta(minutes=1800),
        hi=prior_end,
    )
    prior_24h = prior_end - prior_start
    features["news_prior_24h_count_excluding_6h"] = prior_24h
    features["news_activity_burst_log_6h_vs_prior_24h"] = math.log(
        (recent_6h + 1) / (prior_24h / 4 + 1)
    )
    return features, latest


def main() -> None:
    parser = argparse.ArgumentParser(description="Build EventX structured-news features")
    parser.add_argument("--version", default="v1")
    parser.add_argument("--labels", type=Path)
    parser.add_argument("--associations", type=Path)
    parser.add_argument("--rule-freeze", type=Path)
    parser.add_argument("--out", type=Path)
    parser.add_argument("--report", type=Path)
    parser.add_argument("--cadence-min", type=int, default=5)
    args = parser.parse_args()

    root = REPO_ROOT / "data" / args.version
    labels_path = args.labels or root / "toy" / "labels_30m.jsonl"
    associations_path = args.associations or root / "curated" / "news_market_assoc.jsonl"
    freeze_path = args.rule_freeze or root / "curated" / "news_rule_v1_frozen_manifest.json"
    out_path = args.out or root / "toy" / "news_features_5m.jsonl"
    report_path = args.report or root / "toy" / "news_features_5m_report.json"
    freeze = json.loads(freeze_path.read_text())
    if freeze.get("locked") is not True:
        raise SystemExit("News association rule must be frozen before feature construction.")
    verify_frozen_files(freeze)
    grouped, association_stats = load_events(associations_path)
    event_times = {key: [event.ts for event in events] for key, events in grouped.items()}

    rows_written = input_rows = future_violations = duplicate_keys = 0
    split_counts: Counter[str] = Counter()
    eligible_counts: Counter[str] = Counter()
    eligible_active_24h: Counter[str] = Counter()
    output_keys: set[tuple[str, str, str, str]] = set()
    markets_written: set[tuple[str, str, str]] = set()
    out_path.parent.mkdir(parents=True, exist_ok=True)
    temporary = out_path.with_suffix(out_path.suffix + ".tmp")
    with temporary.open("w") as output:
        for row in read_jsonl(labels_path):
            input_rows += 1
            ts = parse_ts(row["ts"])
            if not cadence_match(ts, args.cadence_min):
                continue
            key = (str(row["venue"]), str(row["market_id"]), str(row["outcome_id"]))
            features, latest = point_in_time_features(
                grouped.get(key, []),
                event_times.get(key, []),
                ts,
            )
            if latest is not None and latest > ts:
                future_violations += 1
            output_key = (*key, str(row["ts"]))
            if output_key in output_keys:
                duplicate_keys += 1
            output_keys.add(output_key)
            split = str(row["split"])
            output_row = {
                "venue": key[0],
                "market_id": key[1],
                "outcome_id": key[2],
                "ts": row["ts"],
                "split": split,
                "eligible": int(row["eligible"]),
                "feature_cadence_min": args.cadence_min,
                "association_rule": freeze["association_rule"],
                "news_rule_id": freeze["news_rule_id"],
                **features,
            }
            output.write(json.dumps(output_row, sort_keys=True) + "\n")
            rows_written += 1
            markets_written.add(key)
            split_counts[split] += 1
            if int(row["eligible"]):
                eligible_counts[split] += 1
                if int(features["news_article_count_1440m"]) > 0:
                    eligible_active_24h[split] += 1
    temporary.replace(out_path)
    if future_violations or duplicate_keys:
        raise SystemExit(
            f"Feature validation failed: future={future_violations}, duplicates={duplicate_keys}"
        )
    artifact = hash_file(out_path)
    feature_names = [
        *(f"news_article_count_{minutes}m" for minutes in WINDOWS_MIN),
        *(f"news_unique_publishers_{minutes}m" for minutes in WINDOWS_MIN),
        *(f"news_unique_categories_{minutes}m" for minutes in WINDOWS_MIN),
        "news_publisher_entropy_24h",
        "news_top_publisher_share_24h",
        "news_has_history",
        "news_minutes_since_latest",
        "news_prior_24h_count_excluding_6h",
        "news_activity_burst_log_6h_vs_prior_24h",
        "news_symbol_mapped",
    ]
    report = {
        "status": "ok",
        "feature_schema": 1,
        "dataset_id": freeze["dataset_id"],
        "news_rule_id": freeze["news_rule_id"],
        "association_rule": freeze["association_rule"],
        "cadence_min": args.cadence_min,
        "window_semantics": "(feature_ts - window, feature_ts]",
        "input_label_rows_scanned": input_rows,
        "rows_written": rows_written,
        "split_counts": dict(sorted(split_counts.items())),
        "eligible_split_counts": dict(sorted(eligible_counts.items())),
        "eligible_active_24h_rows_by_split": dict(sorted(eligible_active_24h.items())),
        "markets_written": len(markets_written),
        "markets_with_news_associations": len(grouped),
        "association_input_validation": association_stats,
        "point_in_time_validation": {
            "future_event_violations": future_violations,
            "duplicate_output_keys": duplicate_keys,
            "passed": not future_violations and not duplicate_keys,
        },
        "features": feature_names,
        "sentiment_availability": {
            "news_symbol_mapped_markets": 0,
            "structured_sentiment_included": False,
            "reason": "No toy event market has a canonical financial ticker mapping.",
        },
        "test_policy": (
            "Features use only associated articles with published_at <= feature_ts. "
            "No outcome label fields are copied into the artifact."
        ),
        "inputs": {
            "labels": relative(labels_path),
            "associations": relative(associations_path),
            "rule_freeze": relative(freeze_path),
        },
        "artifact": {"path": relative(out_path), **artifact},
    }
    report_path.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")
    print(json.dumps(report, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
