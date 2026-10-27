"""Audit EventXBench linkage supervision without reading external holdout labels.

The audit reads full rows only from T2 train and T3 gold. T2 validation and test are
restricted to identifier/schema fields needed for leakage checks; their label fields
are never accessed or emitted.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import statistics
from collections import Counter
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Iterable


CONDITION_RE = re.compile(r"^0x[0-9a-fA-F]{64}$")
TWITTER_EPOCH_MS = 1_288_834_974_657


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--root", type=Path, default=Path("data/external/eventxbench")
    )
    parser.add_argument(
        "--kol-tweets",
        type=Path,
        default=Path("data/v1/raw/kol_tweets.jsonl"),
    )
    parser.add_argument(
        "--opened-exclusions",
        type=Path,
        default=Path(
            "data/v2_1/association/kol_v2_audit/"
            "opened_pair_content_exclusions_through_kol_v2.jsonl"
        ),
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("data/external/eventxbench/AUDIT_REPORT.json"),
    )
    return parser.parse_args()


def rows(path: Path) -> Iterable[dict[str, Any]]:
    with path.open(encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, start=1):
            if not line.strip():
                continue
            value = json.loads(line)
            if not isinstance(value, dict):
                raise ValueError(f"{path}:{line_number} is not a JSON object")
            yield value


def normalized_id(value: Any) -> str:
    return "" if value is None else str(value).strip()


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def parse_timestamp(value: Any) -> datetime | None:
    if not isinstance(value, str) or not value.strip():
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00")).astimezone(UTC)
    except ValueError:
        return None


def snowflake_timestamp(tweet_id: str) -> datetime | None:
    try:
        value = int(tweet_id)
    except (TypeError, ValueError):
        return None
    milliseconds = (value >> 22) + TWITTER_EPOCH_MS
    try:
        return datetime.fromtimestamp(milliseconds / 1000, tz=UTC)
    except (OverflowError, OSError, ValueError):
        return None


def timestamp_range(values: list[datetime]) -> dict[str, str | None]:
    return {
        "earliest": min(values).isoformat().replace("+00:00", "Z") if values else None,
        "latest": max(values).isoformat().replace("+00:00", "Z") if values else None,
    }


def numeric_summary(values: list[float]) -> dict[str, float | int | None]:
    if not values:
        return {"count": 0, "min": None, "median": None, "max": None}
    return {
        "count": len(values),
        "min": min(values),
        "median": statistics.median(values),
        "max": max(values),
    }


def counter(counter: Counter[Any]) -> dict[str, int]:
    return {str(key): value for key, value in sorted(counter.items(), key=str)}


def audit_t2_train(
    path: Path,
) -> tuple[dict[str, Any], set[str], set[tuple[str, str]], set[str]]:
    count = 0
    tweet_ids: list[str] = []
    gold_conditions: list[str] = []
    pairs: list[tuple[str, str]] = []
    instance_ids: list[str] = []
    candidate_counts: list[float] = []
    cosine_scores: list[float] = []
    explicit_times: list[datetime] = []
    derived_times: list[datetime] = []
    timestamp_delta_seconds: list[float] = []
    post_before_market = 0
    post_at_or_after_market = 0
    candidate_markets_created_after_post = 0
    rows_with_any_candidate_created_after_post = 0
    missing_or_invalid_post_time = 0
    invalid_link_condition_ids = 0
    invalid_candidate_condition_ids = 0
    link_rows_missing_gold = 0
    link_gold_missing_from_candidates = 0
    none_rows_with_nonnull_gold = 0
    label_semantics_mismatch = 0
    unknown_binary_label_rows = 0
    text_missing = 0
    all_candidate_conditions: set[str] = set()
    source_counts: Counter[Any] = Counter()
    tier_counts: Counter[Any] = Counter()
    binary_counts: Counter[Any] = Counter()
    setting_counts: Counter[Any] = Counter()
    version_counts: Counter[Any] = Counter()
    split_counts: Counter[Any] = Counter()
    provenance_versions: dict[str, Counter[Any]] = {}

    for row in rows(path):
        count += 1
        tweet_id = normalized_id(row.get("tweet_id"))
        gold = normalized_id(row.get("gold_condition_id"))
        pair = (tweet_id, gold)
        tweet_ids.append(tweet_id)
        if gold:
            gold_conditions.append(gold)
        instance_ids.append(normalized_id(row.get("instance_id")))
        binary_label = normalized_id(row.get("binary_label")).upper()
        label = normalized_id(row.get("label"))
        if binary_label == "LINK":
            pairs.append(pair)
            if not gold:
                link_rows_missing_gold += 1
            elif not CONDITION_RE.fullmatch(gold):
                invalid_link_condition_ids += 1
            if label != gold:
                label_semantics_mismatch += 1
        elif binary_label == "NONE":
            if gold:
                none_rows_with_nonnull_gold += 1
            if label != "NONE":
                label_semantics_mismatch += 1
        else:
            unknown_binary_label_rows += 1
            label_semantics_mismatch += 1
        if not isinstance(row.get("post_text"), str) or not row["post_text"].strip():
            text_missing += 1

        source_counts[row.get("label_source")] += 1
        tier_counts[row.get("label_tier")] += 1
        binary_counts[row.get("binary_label")] += 1
        setting_counts[row.get("candidate_setting")] += 1
        version_counts[row.get("dataset_version")] += 1
        split_counts[row.get("split")] += 1

        provenance = row.get("provenance")
        if isinstance(provenance, dict):
            for key in (
                "contract_recall_version",
                "physical_recall_version",
                "policy_version",
                "storage_backend",
                "db_pair_judgment_used",
            ):
                provenance_versions.setdefault(key, Counter())[provenance.get(key)] += 1

        candidates = row.get("candidates")
        if not isinstance(candidates, list):
            candidates = []
        candidate_counts.append(float(len(candidates)))
        candidate_ids: set[str] = set()
        candidate_market_times: list[datetime] = []
        gold_market_time: datetime | None = None
        for candidate in candidates:
            if not isinstance(candidate, dict):
                continue
            condition_id = normalized_id(candidate.get("condition_id"))
            candidate_ids.add(condition_id)
            if condition_id:
                all_candidate_conditions.add(condition_id)
            if not CONDITION_RE.fullmatch(condition_id):
                invalid_candidate_condition_ids += 1
            score = candidate.get("cosine_score")
            if isinstance(score, (int, float)):
                cosine_scores.append(float(score))
            if condition_id == gold:
                gold_market_time = parse_timestamp(candidate.get("market_created_at"))
            candidate_market_time = parse_timestamp(candidate.get("market_created_at"))
            if candidate_market_time is not None:
                candidate_market_times.append(candidate_market_time)
        if binary_label == "LINK" and gold not in candidate_ids:
            link_gold_missing_from_candidates += 1

        explicit_time = parse_timestamp(row.get("post_created_at"))
        derived_time = snowflake_timestamp(tweet_id)
        if explicit_time is None:
            missing_or_invalid_post_time += 1
        else:
            explicit_times.append(explicit_time)
        if derived_time is not None:
            derived_times.append(derived_time)
        if explicit_time is not None and derived_time is not None:
            timestamp_delta_seconds.append(abs((explicit_time - derived_time).total_seconds()))
        if explicit_time is not None:
            future_candidate_count = sum(
                market_time > explicit_time for market_time in candidate_market_times
            )
            candidate_markets_created_after_post += future_candidate_count
            if future_candidate_count:
                rows_with_any_candidate_created_after_post += 1
        if explicit_time is not None and gold_market_time is not None:
            if explicit_time < gold_market_time:
                post_before_market += 1
            else:
                post_at_or_after_market += 1

    unique_tweets = set(tweet_ids)
    unique_pairs = set(pairs)
    report = {
        "path": str(path),
        "sha256": sha256(path),
        "rows": count,
        "unique_tweets": len(unique_tweets),
        "unique_gold_conditions": len(set(gold_conditions)),
        "unique_tweet_market_pairs": len(unique_pairs),
        "duplicate_tweet_rows": count - len(unique_tweets),
        "duplicate_link_pair_rows": len(pairs) - len(unique_pairs),
        "duplicate_instance_ids": count - len(set(instance_ids)),
        "dataset_versions": counter(version_counts),
        "splits": counter(split_counts),
        "candidate_settings": counter(setting_counts),
        "binary_labels": counter(binary_counts),
        "label_sources": counter(source_counts),
        "label_tiers": counter(tier_counts),
        "provenance": {key: counter(value) for key, value in provenance_versions.items()},
        "candidate_count": numeric_summary(candidate_counts),
        "candidate_cosine_score": numeric_summary(cosine_scores),
        "link_rows": binary_counts.get("LINK", 0),
        "none_rows": binary_counts.get("NONE", 0),
        "unknown_binary_label_rows": unknown_binary_label_rows,
        "link_rows_missing_gold": link_rows_missing_gold,
        "link_gold_missing_from_candidates": link_gold_missing_from_candidates,
        "none_rows_with_nonnull_gold": none_rows_with_nonnull_gold,
        "label_semantics_mismatch": label_semantics_mismatch,
        "invalid_link_condition_ids": invalid_link_condition_ids,
        "invalid_candidate_condition_ids": invalid_candidate_condition_ids,
        "missing_post_text": text_missing,
        "missing_or_invalid_post_created_at": missing_or_invalid_post_time,
        "post_created_at_range": timestamp_range(explicit_times),
        "snowflake_timestamp_range": timestamp_range(derived_times),
        "snowflake_vs_explicit_abs_seconds": numeric_summary(timestamp_delta_seconds),
        "post_before_gold_market_creation": post_before_market,
        "post_at_or_after_gold_market_creation": post_at_or_after_market,
        "candidate_markets_created_after_post": candidate_markets_created_after_post,
        "rows_with_any_candidate_created_after_post": (
            rows_with_any_candidate_created_after_post
        ),
    }
    return report, unique_tweets, unique_pairs, all_candidate_conditions


def audit_t3_gold(path: Path) -> tuple[dict[str, Any], set[str], set[tuple[str, str]]]:
    count = 0
    tweet_ids: list[str] = []
    conditions: list[str] = []
    pairs: list[tuple[str, str]] = []
    derived_times: list[datetime] = []
    grades: Counter[Any] = Counter()
    requires_official: Counter[Any] = Counter()
    invalid_conditions = 0
    text_missing = 0
    all_three_exact = 0
    gold_equals_median = 0
    annotation_spreads: list[float] = []
    missing_annotator_grade = 0
    invalid_gold_grades = 0

    for row in rows(path):
        count += 1
        tweet_id = normalized_id(row.get("tweet_id"))
        condition = normalized_id(row.get("condition_id"))
        tweet_ids.append(tweet_id)
        conditions.append(condition)
        pairs.append((tweet_id, condition))
        if not CONDITION_RE.fullmatch(condition):
            invalid_conditions += 1
        if not isinstance(row.get("tweet"), str) or not row["tweet"].strip():
            text_missing += 1
        gold_grade = row.get("gold_grade")
        grades[gold_grade] += 1
        if not isinstance(gold_grade, (int, float)) or not 0 <= float(gold_grade) <= 5:
            invalid_gold_grades += 1
        requires_official[row.get("requires_official")] += 1
        derived = snowflake_timestamp(tweet_id)
        if derived is not None:
            derived_times.append(derived)

        annotator_values = [row.get(f"A{index}_grade") for index in range(1, 4)]
        if not all(isinstance(value, (int, float)) for value in annotator_values):
            missing_annotator_grade += 1
            continue
        numeric = [float(value) for value in annotator_values]
        if len(set(numeric)) == 1:
            all_three_exact += 1
        median = statistics.median(numeric)
        if isinstance(row.get("gold_grade"), (int, float)) and float(row["gold_grade"]) == median:
            gold_equals_median += 1
        annotation_spreads.append(max(numeric) - min(numeric))

    unique_tweets = set(tweet_ids)
    unique_pairs = set(pairs)
    report = {
        "path": str(path),
        "sha256": sha256(path),
        "rows": count,
        "unique_tweets": len(unique_tweets),
        "unique_conditions": len(set(conditions)),
        "unique_tweet_market_pairs": len(unique_pairs),
        "duplicate_tweet_rows": count - len(unique_tweets),
        "duplicate_pair_rows": count - len(unique_pairs),
        "invalid_condition_ids": invalid_conditions,
        "missing_tweet_text": text_missing,
        "gold_grade_distribution": counter(grades),
        "invalid_gold_grades": invalid_gold_grades,
        "requires_official_distribution": counter(requires_official),
        "snowflake_timestamp_range": timestamp_range(derived_times),
        "rows_missing_any_annotator_grade": missing_annotator_grade,
        "rows_with_all_three_annotator_grades": len(annotation_spreads),
        "all_three_annotators_exact": all_three_exact,
        "gold_equals_annotator_median": gold_equals_median,
        "annotator_grade_spread": numeric_summary(annotation_spreads),
        "annotator_grade_spread_at_least_2": sum(
            value >= 2 for value in annotation_spreads
        ),
        "annotator_grade_spread_at_least_3": sum(
            value >= 3 for value in annotation_spreads
        ),
    }
    return report, unique_tweets, unique_pairs


def safe_split_identifiers(path: Path) -> dict[str, Any]:
    """Read no label or gold-condition field from an external evaluation split."""
    count = 0
    tweet_ids: set[str] = set()
    instance_ids: set[str] = set()
    candidate_conditions: set[str] = set()
    candidate_counts: list[float] = []
    has_post_created_at = 0
    derived_times: list[datetime] = []
    missing_or_invalid_snowflake_time = 0
    candidate_markets_created_after_post = 0
    rows_with_any_candidate_created_after_post = 0
    for row in rows(path):
        count += 1
        tweet_id = normalized_id(row.get("tweet_id"))
        tweet_ids.add(tweet_id)
        instance_ids.add(normalized_id(row.get("instance_id")))
        post_time = snowflake_timestamp(tweet_id)
        if post_time is None:
            missing_or_invalid_snowflake_time += 1
        else:
            derived_times.append(post_time)
        candidates = row.get("candidates")
        if not isinstance(candidates, list):
            candidates = []
        candidate_counts.append(float(len(candidates)))
        future_candidate_count = 0
        for candidate in candidates:
            if isinstance(candidate, dict):
                candidate_conditions.add(normalized_id(candidate.get("condition_id")))
                market_time = parse_timestamp(candidate.get("market_created_at"))
                if (
                    post_time is not None
                    and market_time is not None
                    and market_time > post_time
                ):
                    future_candidate_count += 1
        candidate_markets_created_after_post += future_candidate_count
        if future_candidate_count:
            rows_with_any_candidate_created_after_post += 1
        if "post_created_at" in row and row.get("post_created_at") is not None:
            has_post_created_at += 1
    return {
        "path": str(path),
        "sha256": sha256(path),
        "rows": count,
        "tweet_ids": tweet_ids,
        "instance_ids": instance_ids,
        "candidate_conditions": candidate_conditions,
        "candidate_count": numeric_summary(candidate_counts),
        "rows_with_post_created_at": has_post_created_at,
        "snowflake_timestamp_range": timestamp_range(derived_times),
        "missing_or_invalid_snowflake_timestamp": missing_or_invalid_snowflake_time,
        "candidate_markets_created_after_post": candidate_markets_created_after_post,
        "rows_with_any_candidate_created_after_post": (
            rows_with_any_candidate_created_after_post
        ),
        "label_fields_accessed": False,
    }


def audit_local_kol_overlap(path: Path, target_tweets: set[str]) -> dict[str, Any]:
    matched_tweets: set[str] = set()
    matched_handles: set[str] = set()
    scanned = 0
    for row in rows(path):
        scanned += 1
        tweet_id = normalized_id(row.get("tweet_id"))
        if tweet_id not in target_tweets:
            continue
        matched_tweets.add(tweet_id)
        handle = normalized_id(
            row.get("_kol_handle")
            or row.get("kol_username")
            or row.get("author_username")
        ).lower()
        if handle:
            matched_handles.add(handle)
    return {
        "path": str(path),
        "rows_scanned": scanned,
        "target_tweets": len(target_tweets),
        "matched_tweets": len(matched_tweets),
        "matched_fraction": len(matched_tweets) / len(target_tweets) if target_tweets else None,
        "matched_unique_handles": len(matched_handles),
    }


def audit_opened_pair_overlap(
    path: Path, external_pairs: set[tuple[str, str]]
) -> dict[str, Any]:
    opened_pairs: set[tuple[str, str]] = set()
    scanned = 0
    for row in rows(path):
        scanned += 1
        if normalized_id(row.get("source")).lower() != "kol":
            continue
        opened_pairs.add(
            (normalized_id(row.get("doc_id")), normalized_id(row.get("market_id")))
        )
    overlap = external_pairs & opened_pairs
    return {
        "path": str(path),
        "rows_scanned": scanned,
        "opened_kol_pairs": len(opened_pairs),
        "external_pairs": len(external_pairs),
        "overlapping_pairs": len(overlap),
    }


def public_split_summary(value: dict[str, Any]) -> dict[str, Any]:
    return {
        key: item
        for key, item in value.items()
        if key not in {"tweet_ids", "instance_ids", "candidate_conditions"}
    }


def main() -> int:
    args = parse_args()
    t2_train_path = args.root / "data/t2/t2_train.jsonl"
    t2_val_path = args.root / "data/t2/t2_val.jsonl"
    t2_test_path = args.root / "data/t2/t2_test.jsonl"
    t3_gold_path = args.root / "data/t3/gold.jsonl"

    t2, t2_tweets, t2_pairs, t2_candidate_conditions = audit_t2_train(
        t2_train_path
    )
    t3, t3_tweets, t3_pairs = audit_t3_gold(t3_gold_path)
    val = safe_split_identifiers(t2_val_path)
    test = safe_split_identifiers(t2_test_path)

    target_tweets = t2_tweets | t3_tweets
    external_pairs = t2_pairs | t3_pairs
    report = {
        "audit_version": "eventxbench-source-audit-v1",
        "generated_at": datetime.now(UTC).isoformat().replace("+00:00", "Z"),
        "scope": {
            "development_content_read": [str(t2_train_path), str(t3_gold_path)],
            "evaluation_split_use": "identifier/schema overlap only; labels not accessed",
            "external_test_labels_inspected": False,
        },
        "t2_train": t2,
        "t3_gold": t3,
        "safe_evaluation_split_schema": {
            "validation": public_split_summary(val),
            "test": public_split_summary(test),
        },
        "split_identifier_overlap": {
            "train_vs_validation_tweet_ids": len(t2_tweets & val["tweet_ids"]),
            "train_vs_test_tweet_ids": len(t2_tweets & test["tweet_ids"]),
            "train_vs_validation_candidate_conditions": len(
                t2_candidate_conditions & val["candidate_conditions"]
            ),
            "train_vs_test_candidate_conditions": len(
                t2_candidate_conditions & test["candidate_conditions"]
            ),
            "validation_vs_test_tweet_ids": len(val["tweet_ids"] & test["tweet_ids"]),
            "validation_vs_test_instance_ids": len(
                val["instance_ids"] & test["instance_ids"]
            ),
            "validation_vs_test_candidate_conditions": len(
                val["candidate_conditions"] & test["candidate_conditions"]
            ),
        },
        "t2_t3_overlap": {
            "tweet_ids": len(t2_tweets & t3_tweets),
            "tweet_market_pairs": len(t2_pairs & t3_pairs),
        },
        "local_kol_overlap": audit_local_kol_overlap(args.kol_tweets, target_tweets),
        "opened_pair_overlap": audit_opened_pair_overlap(
            args.opened_exclusions, external_pairs
        ),
        "decision": "conditional auxiliary source; not ready for confirmatory EventX use",
    }

    args.output.parent.mkdir(parents=True, exist_ok=True)
    temporary = args.output.with_suffix(args.output.suffix + ".tmp")
    temporary.write_text(
        json.dumps(report, indent=2, sort_keys=True, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    temporary.replace(args.output)
    print(json.dumps(report, indent=2, sort_keys=True, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
