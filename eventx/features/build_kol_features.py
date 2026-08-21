"""Build leakage-safe, point-in-time KOL features for the frozen EventX toy cohort."""

from __future__ import annotations

import argparse
import bisect
import hashlib
import json
import math
from collections import Counter
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any, Iterator, NamedTuple

from eventx.settings import REPO_ROOT

WINDOWS_MIN = (30, 120, 360, 1440)
RECENCY_CAP_MIN = 10_080


class Event(NamedTuple):
    ts: datetime
    handle: str
    content_hash: str


def parse_ts(value: Any) -> datetime:
    return datetime.fromisoformat(str(value).replace("Z", "+00:00")).astimezone(UTC)


def read_jsonl(path: Path) -> Iterator[dict[str, Any]]:
    with path.open() as handle:
        for line in handle:
            if line.strip():
                yield json.loads(line)


def hash_file(path: Path) -> dict[str, Any]:
    digest = hashlib.sha256()
    size = 0
    lines = 0
    with path.open("rb") as handle:
        while chunk := handle.read(8 * 1024 * 1024):
            digest.update(chunk)
            size += len(chunk)
            lines += chunk.count(b"\n")
    result: dict[str, Any] = {"sha256": digest.hexdigest(), "bytes": size}
    if path.suffix == ".jsonl":
        result["rows"] = lines
    return result


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
        raise SystemExit("Frozen KOL rule verification failed: " + ", ".join(failures))


def load_events(
    path: Path,
) -> tuple[
    dict[tuple[str, str, str], list[Event]],
    dict[str, int],
]:
    grouped: dict[tuple[str, str, str], list[Event]] = {}
    seen_market_content: set[tuple[str, str, str, str]] = set()
    seen_market_doc: set[tuple[str, str, str, str]] = set()
    stats = {
        "association_rows": 0,
        "duplicate_market_content": 0,
        "duplicate_market_doc": 0,
        "invalid_timestamp": 0,
        "missing_handle": 0,
    }
    for row in read_jsonl(path):
        stats["association_rows"] += 1
        if row.get("association_rule") != "rule_v3":
            raise SystemExit("Association file contains a non-rule_v3 row.")
        key = (str(row["venue"]), str(row["market_id"]), str(row["outcome_id"]))
        content_key = (*key, str(row.get("content_hash") or ""))
        doc_key = (*key, str(row.get("doc_id") or ""))
        if content_key in seen_market_content:
            stats["duplicate_market_content"] += 1
            continue
        if doc_key in seen_market_doc:
            stats["duplicate_market_doc"] += 1
            continue
        seen_market_content.add(content_key)
        seen_market_doc.add(doc_key)
        try:
            ts = parse_ts(row["ts"])
        except (KeyError, TypeError, ValueError):
            stats["invalid_timestamp"] += 1
            continue
        handle = str(row.get("handle") or "").strip().lower()
        if not handle:
            stats["missing_handle"] += 1
            handle = "__missing__"
        grouped.setdefault(key, []).append(
            Event(ts=ts, handle=handle, content_hash=str(row.get("content_hash") or ""))
        )
    for events in grouped.values():
        events.sort(key=lambda event: (event.ts, event.content_hash, event.handle))
    return grouped, stats


def window_events(
    events: list[Event],
    times: list[datetime],
    ts: datetime,
    minutes: int,
    right: int,
) -> list[Event]:
    left = bisect.bisect_right(times, ts - timedelta(minutes=minutes), hi=right)
    return events[left:right]


def handle_diversity(events: list[Event]) -> tuple[int, float, float]:
    if not events:
        return 0, 0.0, 0.0
    counts = Counter(event.handle for event in events)
    total = len(events)
    entropy = -sum((count / total) * math.log(count / total) for count in counts.values())
    normalized_entropy = entropy / math.log(len(counts)) if len(counts) > 1 else 0.0
    top_share = max(counts.values()) / total
    return len(counts), normalized_entropy, top_share


def point_in_time_features(
    events: list[Event],
    times: list[datetime],
    ts: datetime,
) -> tuple[dict[str, int | float], datetime | None]:
    right = bisect.bisect_right(times, ts)
    features: dict[str, int | float] = {}
    slices: dict[int, list[Event]] = {}
    for minutes in WINDOWS_MIN:
        rows = window_events(events, times, ts, minutes, right)
        slices[minutes] = rows
        unique_handles, entropy, top_share = handle_diversity(rows)
        suffix = f"{minutes}m"
        features[f"kol_tweet_count_{suffix}"] = len(rows)
        features[f"kol_novel_count_{suffix}"] = len({event.content_hash for event in rows})
        features[f"kol_unique_handles_{suffix}"] = unique_handles
        if minutes == 1440:
            features["kol_handle_entropy_24h"] = entropy
            features["kol_top_handle_share_24h"] = top_share

    latest = events[right - 1].ts if right else None
    features["kol_has_history"] = int(latest is not None)
    features["kol_minutes_since_latest"] = (
        min((ts - latest).total_seconds() / 60, RECENCY_CAP_MIN)
        if latest is not None
        else float(RECENCY_CAP_MIN)
    )
    recent_2h = len(slices[120])
    prior_end = bisect.bisect_right(times, ts - timedelta(minutes=120), hi=right)
    prior_start = bisect.bisect_right(
        times,
        ts - timedelta(minutes=1560),
        hi=prior_end,
    )
    prior_24h = prior_end - prior_start
    expected_2h = prior_24h / 12
    features["kol_prior_24h_count_excluding_2h"] = prior_24h
    features["kol_activity_burst_log_2h_vs_prior_24h"] = math.log(
        (recent_2h + 1) / (expected_2h + 1)
    )
    return features, latest


def cadence_match(ts: datetime, cadence_min: int) -> bool:
    minutes = ts.hour * 60 + ts.minute
    return ts.second == 0 and ts.microsecond == 0 and minutes % cadence_min == 0


def main() -> None:
    parser = argparse.ArgumentParser(description="Build leakage-safe EventX KOL features")
    parser.add_argument("--version", default="v1")
    parser.add_argument("--labels", type=Path)
    parser.add_argument("--associations", type=Path)
    parser.add_argument("--rule-freeze", type=Path)
    parser.add_argument("--out", type=Path)
    parser.add_argument("--report", type=Path)
    parser.add_argument("--cadence-min", type=int, default=30)
    parser.add_argument(
        "--skip-freeze-verification",
        action="store_true",
        help="Only for local debugging; production builds must verify hashes.",
    )
    args = parser.parse_args()
    if args.cadence_min <= 0 or 1440 % args.cadence_min:
        raise SystemExit("--cadence-min must be a positive divisor of 1440")

    root = REPO_ROOT / "data" / args.version
    labels_path = args.labels or root / "toy" / "labels_30m.jsonl"
    associations_path = args.associations or root / "curated" / "kol_market_assoc.jsonl"
    freeze_path = args.rule_freeze or root / "curated" / "kol_rule_v3_frozen_manifest.json"
    out_path = args.out or root / "toy" / "kol_features_30m.jsonl"
    report_path = args.report or root / "toy" / "kol_features_30m_report.json"
    for path in (labels_path, associations_path, freeze_path):
        if not path.exists():
            raise SystemExit(f"Missing required input: {path}")

    freeze = json.loads(freeze_path.read_text())
    if freeze.get("locked") is not True or freeze.get("association_rule") != "rule_v3":
        raise SystemExit("KOL rule v3 must be accepted and frozen before building features.")
    if not args.skip_freeze_verification:
        verify_frozen_files(freeze)

    grouped, association_stats = load_events(associations_path)
    event_times = {key: [event.ts for event in events] for key, events in grouped.items()}
    rows_written = 0
    input_rows = 0
    split_counts: Counter[str] = Counter()
    eligible_split_counts: Counter[str] = Counter()
    nonzero_24h_by_split: Counter[str] = Counter()
    eligible_nonzero_24h_by_split: Counter[str] = Counter()
    markets_written: set[tuple[str, str, str]] = set()
    markets_with_associations: set[tuple[str, str, str]] = set(grouped)
    output_keys: set[tuple[str, str, str, str]] = set()
    duplicate_output_keys = 0
    monotonic_window_violations = 0
    handle_count_violations = 0
    novelty_count_violations = 0
    future_event_violations = 0
    max_latest_event_ts: datetime | None = None
    min_feature_ts: datetime | None = None
    max_feature_ts: datetime | None = None

    out_path.parent.mkdir(parents=True, exist_ok=True)
    temporary = out_path.with_suffix(out_path.suffix + ".tmp")
    with temporary.open("w") as output:
        for row in read_jsonl(labels_path):
            input_rows += 1
            ts = parse_ts(row["ts"])
            if not cadence_match(ts, args.cadence_min):
                continue
            key = (str(row["venue"]), str(row["market_id"]), str(row["outcome_id"]))
            events = grouped.get(key, [])
            features, latest = point_in_time_features(
                events,
                event_times.get(key, []),
                ts,
            )
            if latest is not None:
                if latest > ts:
                    future_event_violations += 1
                max_latest_event_ts = max(max_latest_event_ts, latest) if max_latest_event_ts else latest
            split = str(row["split"])
            output_row = {
                "venue": key[0],
                "market_id": key[1],
                "outcome_id": key[2],
                "ts": row["ts"],
                "split": split,
                "eligible": int(row["eligible"]),
                "feature_cadence_min": args.cadence_min,
                "association_rule": "rule_v3",
                "kol_rule_id": freeze["kol_rule_id"],
                **features,
            }
            output_key = (*key, str(row["ts"]))
            if output_key in output_keys:
                duplicate_output_keys += 1
            output_keys.add(output_key)
            tweet_counts = [
                int(features[f"kol_tweet_count_{minutes}m"]) for minutes in WINDOWS_MIN
            ]
            unique_handles = [
                int(features[f"kol_unique_handles_{minutes}m"]) for minutes in WINDOWS_MIN
            ]
            novel_counts = [
                int(features[f"kol_novel_count_{minutes}m"]) for minutes in WINDOWS_MIN
            ]
            if tweet_counts != sorted(tweet_counts):
                monotonic_window_violations += 1
            if any(handles > count for handles, count in zip(unique_handles, tweet_counts)):
                handle_count_violations += 1
            if novel_counts != tweet_counts:
                novelty_count_violations += 1
            output.write(json.dumps(output_row, sort_keys=True) + "\n")
            rows_written += 1
            markets_written.add(key)
            split_counts[split] += 1
            if int(row["eligible"]):
                eligible_split_counts[split] += 1
            if int(features["kol_tweet_count_1440m"]) > 0:
                nonzero_24h_by_split[split] += 1
                if int(row["eligible"]):
                    eligible_nonzero_24h_by_split[split] += 1
            min_feature_ts = min(min_feature_ts, ts) if min_feature_ts else ts
            max_feature_ts = max(max_feature_ts, ts) if max_feature_ts else ts
    temporary.replace(out_path)

    if future_event_violations:
        raise SystemExit(f"Point-in-time validation failed: {future_event_violations} future events")
    artifact = hash_file(out_path)
    report = {
        "status": "ok",
        "feature_schema": 1,
        "dataset_id": freeze["dataset_id"],
        "association_rule": "rule_v3",
        "kol_rule_id": freeze["kol_rule_id"],
        "cadence_min": args.cadence_min,
        "window_semantics": "(feature_ts - window, feature_ts]",
        "recency_cap_min": RECENCY_CAP_MIN,
        "input_label_rows_scanned": input_rows,
        "rows_written": rows_written,
        "split_counts": dict(sorted(split_counts.items())),
        "eligible_split_counts": dict(sorted(eligible_split_counts.items())),
        "nonzero_24h_rows_by_split": dict(sorted(nonzero_24h_by_split.items())),
        "eligible_nonzero_24h_rows_by_split": dict(
            sorted(eligible_nonzero_24h_by_split.items())
        ),
        "markets_written": len(markets_written),
        "markets_with_associations": len(markets_with_associations),
        "feature_time_range": {
            "min": min_feature_ts.isoformat().replace("+00:00", "Z")
            if min_feature_ts
            else None,
            "max": max_feature_ts.isoformat().replace("+00:00", "Z")
            if max_feature_ts
            else None,
        },
        "max_latest_event_ts_used": (
            max_latest_event_ts.isoformat().replace("+00:00", "Z")
            if max_latest_event_ts
            else None
        ),
        "point_in_time_validation": {
            "future_event_violations": future_event_violations,
            "passed": future_event_violations == 0,
        },
        "feature_invariants": {
            "duplicate_output_keys": duplicate_output_keys,
            "monotonic_window_violations": monotonic_window_violations,
            "unique_handles_exceeding_tweets": handle_count_violations,
            "novel_count_not_equal_to_tweet_count": novelty_count_violations,
            "passed": not any(
                (
                    duplicate_output_keys,
                    monotonic_window_violations,
                    handle_count_violations,
                    novelty_count_violations,
                )
            ),
        },
        "association_input_validation": association_stats,
        "features": [
            *(f"kol_tweet_count_{minutes}m" for minutes in WINDOWS_MIN),
            *(f"kol_novel_count_{minutes}m" for minutes in WINDOWS_MIN),
            *(f"kol_unique_handles_{minutes}m" for minutes in WINDOWS_MIN),
            "kol_handle_entropy_24h",
            "kol_top_handle_share_24h",
            "kol_has_history",
            "kol_minutes_since_latest",
            "kol_prior_24h_count_excluding_2h",
            "kol_activity_burst_log_2h_vs_prior_24h",
        ],
        "recommended_b1_model_features": [
            *(f"kol_tweet_count_{minutes}m" for minutes in WINDOWS_MIN),
            *(f"kol_unique_handles_{minutes}m" for minutes in WINDOWS_MIN),
            "kol_handle_entropy_24h",
            "kol_top_handle_share_24h",
            "kol_has_history",
            "kol_minutes_since_latest",
            "kol_prior_24h_count_excluding_2h",
            "kol_activity_burst_log_2h_vs_prior_24h",
        ],
        "redundancy_note": (
            "The frozen association input is already content-deduplicated, so each "
            "kol_novel_count_* column equals its kol_tweet_count_* counterpart. Keep "
            "novel counts for auditability, but use only the tweet-count family in B1."
        ),
        "excluded_unsafe_or_unavailable_features": {
            "engagement": (
                "Raw counts are extraction-time snapshots without point-in-time histories; "
                "using them would leak post-tweet engagement."
            ),
            "author_followers": (
                "Follower counts are extraction-time snapshots without observation timestamps."
            ),
            "sentiment": "No frozen, independently validated point-in-time sentiment field exists.",
        },
        "test_policy": (
            "Features are generated mechanically for all splits using only associations "
            "with tweet_ts <= feature_ts. No test labels are copied into this artifact."
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
