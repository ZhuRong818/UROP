"""Build a reproducible, pre-test semantic audit sample for KOL associations."""

from __future__ import annotations

import argparse
import hashlib
import json
import random
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Iterator

from eventx.features.kol_association import (
    CASHTAG_RE,
    content_hash,
    entities_for,
    parse_ts,
    tokens,
)
from eventx.settings import REPO_ROOT


def read_jsonl(path: Path) -> Iterator[dict[str, Any]]:
    with path.open() as handle:
        for line in handle:
            if line.strip():
                yield json.loads(line)


def write_jsonl_atomic(path: Path, rows: list[dict[str, Any]]) -> None:
    temporary = path.with_suffix(path.suffix + ".tmp")
    with temporary.open("w") as handle:
        for row in rows:
            handle.write(json.dumps(row, sort_keys=True, ensure_ascii=False) + "\n")
    temporary.replace(path)


def reservoir_add(
    rows: list[dict[str, Any]],
    row: dict[str, Any],
    seen: int,
    limit: int,
    rng: random.Random,
) -> None:
    if len(rows) < limit:
        rows.append(row)
        return
    index = rng.randrange(seen)
    if index < limit:
        rows[index] = row


def round_robin_sample(
    groups: dict[str, list[dict[str, Any]]],
    target: int,
    per_group_cap: int,
    rng: random.Random,
) -> list[dict[str, Any]]:
    for rows in groups.values():
        rng.shuffle(rows)
    chosen: list[dict[str, Any]] = []
    depth = 0
    keys = sorted(groups)
    while len(chosen) < target:
        added = False
        for key in keys:
            if depth < min(len(groups[key]), per_group_cap):
                chosen.append(groups[key][depth])
                added = True
                if len(chosen) == target:
                    break
        if not added:
            break
        depth += 1
    if len(chosen) < target:
        leftovers = [
            row
            for key in keys
            for row in groups[key][per_group_cap:]
        ]
        rng.shuffle(leftovers)
        chosen.extend(leftovers[: target - len(chosen)])
    return chosen


def audit_id(row: dict[str, Any]) -> str:
    payload = "|".join(
        [
            row["sample_type"],
            row["market_id"],
            row["doc_id"],
            ",".join(row.get("match_reason") or []),
        ]
    )
    return hashlib.sha256(payload.encode()).hexdigest()[:16]


def main() -> None:
    parser = argparse.ArgumentParser(description="Build a pre-test KOL association audit sample")
    parser.add_argument("--matched", type=int, default=200)
    parser.add_argument("--unmatched", type=int, default=100)
    parser.add_argument("--seed", type=int, default=20260729)
    parser.add_argument("--out-dir", type=Path, default=REPO_ROOT / "data" / "v1" / "audit")
    parser.add_argument(
        "--exclude-audit",
        action="append",
        default=[],
        type=Path,
        help="Prior audit JSONL whose market/tweet and market/content pairs must be excluded",
    )
    parser.add_argument(
        "--blind",
        action="store_true",
        help="Write a shuffled reviewer file without predictions plus a separate internal key",
    )
    args = parser.parse_args()
    out_dir = (
        args.out_dir
        if args.out_dir.is_absolute()
        else REPO_ROOT / args.out_dir
    )

    root = REPO_ROOT / "data" / "v1"
    markets = list(read_jsonl(root / "toy" / "selected_markets.jsonl"))
    frozen = json.loads((root / "toy" / "frozen_manifest.json").read_text())
    start = parse_ts(frozen["window"]["start"])
    cutoff = parse_ts(frozen["split_boundaries"]["test_start"])
    if start is None or cutoff is None:
        raise SystemExit("Frozen manifest has no valid audit window.")
    market_by_id = {str(row["market_id"]): row for row in markets}

    excluded_pairs: set[tuple[str, str]] = set()
    excluded_content: set[tuple[str, str]] = set()
    excluded_rows = 0
    for exclusion_path in args.exclude_audit:
        for row in read_jsonl(exclusion_path):
            excluded_rows += 1
            market_id = str(row.get("market_id") or "")
            doc_id = str(row.get("doc_id") or "")
            if market_id and doc_id:
                excluded_pairs.add((market_id, doc_id))
            digest = row.get("content_hash")
            if not digest and row.get("text"):
                digest = content_hash(str(row["text"]))
            if market_id and digest:
                excluded_content.add((market_id, str(digest)))

    all_pretest_associations = [
        row
        for row in read_jsonl(root / "curated" / "kol_market_assoc.jsonl")
        if (parse_ts(row.get("ts")) or cutoff) < cutoff
        and str(row["market_id"]) in market_by_id
    ]
    pretest_associations = [
        row
        for row in all_pretest_associations
        if (str(row["market_id"]), str(row["doc_id"])) not in excluded_pairs
        and (
            str(row["market_id"]),
            str(row.get("content_hash") or ""),
        )
        not in excluded_content
    ]
    association_pairs = {
        (str(row["market_id"]), str(row["doc_id"])) for row in pretest_associations
    }
    association_content = {
        (str(row["market_id"]), str(row["content_hash"]))
        for row in pretest_associations
        if row.get("content_hash")
    }
    matched_groups: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in pretest_associations:
        reason = "+".join(sorted(row.get("match_reason") or ["unknown"]))
        matched_groups[f"{row['market_id']}|{reason}"].append(dict(row))
    rng = random.Random(args.seed)
    matched = round_robin_sample(matched_groups, args.matched, 10, rng)
    matched_ids = {str(row["doc_id"]) for row in matched}

    specs: dict[str, dict[str, Any]] = {}
    token_index: dict[str, set[str]] = defaultdict(set)
    for market_id, market in market_by_id.items():
        extracted = entities_for(str(market["question"]))
        specs[market_id] = extracted
        values = [
            *extracted["entity_phrase"],
            *extracted["anchor"],
            *extracted["keyword"],
        ]
        for value in values:
            for token in tokens(value):
                token_index[token].add(market_id)

    tweet_text: dict[str, dict[str, Any]] = {}
    hard_groups: dict[str, list[dict[str, Any]]] = defaultdict(list)
    hard_seen: Counter[str] = Counter()
    hard_seen_content: set[tuple[str, str]] = set()
    for tweet in read_jsonl(root / "raw" / "kol_tweets.jsonl"):
        ts = parse_ts(tweet.get("created_at") or tweet.get("ts"))
        if ts is None or not start <= ts < cutoff:
            continue
        doc_id = str(tweet.get("tweet_id") or tweet.get("id") or "")
        if doc_id in matched_ids:
            tweet_text[doc_id] = tweet
        text = str(tweet.get("text") or "")
        digest = content_hash(text)
        text_lower = text.lower()
        tweet_tokens = tokens(text)
        candidates: set[str] = set()
        for token in tweet_tokens:
            candidates.update(token_index.get(token, ()))
        tweet_cashtags = {
            value.upper() for value in CASHTAG_RE.findall(text)
        }
        for market_id in candidates:
            if (market_id, doc_id) in excluded_pairs:
                continue
            if (market_id, digest) in excluded_content:
                continue
            if (market_id, doc_id) in association_pairs:
                continue
            if (market_id, digest) in association_content:
                continue
            if (market_id, digest) in hard_seen_content:
                continue
            extracted = specs[market_id]
            exact_phrases = [
                phrase for phrase in extracted["entity_phrase"] if phrase.lower() in text_lower
            ]
            overlap = sorted(
                tweet_tokens.intersection(
                    set(extracted["anchor"]) | set(extracted["keyword"])
                )
            )
            exact_cashtags = sorted(tweet_cashtags.intersection(extracted["cashtag"]))
            if not exact_phrases and not exact_cashtags and len(overlap) < 2:
                continue
            hard_seen_content.add((market_id, digest))
            hard_seen[market_id] += 1
            reservoir_add(
                hard_groups[market_id],
                {
                    "kind": "kol_tweet",
                    "doc_id": doc_id,
                    "handle": tweet.get("kol_username")
                    or tweet.get("author_username")
                    or tweet.get("_kol_handle"),
                    "ts": tweet.get("created_at") or tweet.get("ts"),
                    "venue": market_by_id[market_id]["venue"],
                    "market_id": market_id,
                    "outcome_id": market_by_id[market_id]["outcome_id"],
                    "match_reason": [],
                    "matched_terms": sorted(set(exact_phrases + exact_cashtags + overlap)),
                    "content_hash": digest,
                    "text": text,
                },
                hard_seen[market_id],
                50,
                rng,
            )

    unmatched = round_robin_sample(hard_groups, args.unmatched, 5, rng)
    for row in matched:
        tweet = tweet_text.get(str(row["doc_id"]), {})
        row["text"] = tweet.get("text")
        row["sample_type"] = "matched"
    for row in unmatched:
        row["sample_type"] = "hard_unmatched"

    sample = []
    for row in [*matched, *unmatched]:
        market = market_by_id[str(row["market_id"])]
        reviewed = {
            **row,
            "audit_id": audit_id(row),
            "question": market["question"],
            "review_label": None,
            "review_rationale": None,
            "reviewer": None,
            "audit_cutoff_exclusive": cutoff.isoformat().replace("+00:00", "Z"),
            "audit_start_inclusive": start.isoformat().replace("+00:00", "Z"),
            "dataset_id": frozen["dataset_id"],
        }
        sample.append(reviewed)
    sample.sort(key=lambda row: (row["sample_type"], row["market_id"], row["audit_id"]))
    out_dir.mkdir(parents=True, exist_ok=True)
    if args.blind:
        reviewer_rows = [
            {
                "audit_id": row["audit_id"],
                "dataset_id": row["dataset_id"],
                "question": row["question"],
                "tweet_ts": row["ts"],
                "tweet_handle": row["handle"],
                "tweet_text": row["text"],
                "review_label": None,
                "review_confidence": None,
                "review_rationale": None,
                "reviewer": None,
            }
            for row in sample
        ]
        random.Random(args.seed + 1).shuffle(reviewer_rows)
        internal_rows = [
            {
                "audit_id": row["audit_id"],
                "sample_type": row["sample_type"],
                "market_id": row["market_id"],
                "outcome_id": row["outcome_id"],
                "doc_id": row["doc_id"],
                "content_hash": row.get("content_hash"),
                "association_rule": row.get("association_rule"),
                "match_reason": row.get("match_reason") or [],
                "matched_terms": row.get("matched_terms") or [],
            }
            for row in sample
        ]
        reviewer_path = out_dir / "kol_association_blind_review.jsonl"
        internal_path = out_dir / "kol_association_blind_key.jsonl"
        write_jsonl_atomic(reviewer_path, reviewer_rows)
        write_jsonl_atomic(internal_path, internal_rows)
        output_files = {
            "reviewer_sample": str(reviewer_path.relative_to(REPO_ROOT)),
            "internal_key": str(internal_path.relative_to(REPO_ROOT)),
        }
    else:
        sample_path = out_dir / "kol_association_audit_sample.jsonl"
        write_jsonl_atomic(sample_path, sample)
        output_files = {"audit_sample": str(sample_path.relative_to(REPO_ROOT))}
    output_sha256 = {
        label: hashlib.sha256((REPO_ROOT / path).read_bytes()).hexdigest()
        for label, path in output_files.items()
    }
    report = {
        "dataset_id": frozen["dataset_id"],
        "start_inclusive": start.isoformat().replace("+00:00", "Z"),
        "cutoff_exclusive": cutoff.isoformat().replace("+00:00", "Z"),
        "seed": args.seed,
        "requested": {"matched": args.matched, "unmatched": args.unmatched},
        "sampled": dict(Counter(row["sample_type"] for row in sample)),
        "markets_sampled": {
            sample_type: len(
                {row["market_id"] for row in sample if row["sample_type"] == sample_type}
            )
            for sample_type in ("matched", "hard_unmatched")
        },
        "blind": args.blind,
        "excluded_prior_audit_rows": excluded_rows,
        "excluded_market_doc_pairs": len(excluded_pairs),
        "excluded_market_content_pairs": len(excluded_content),
        "eligible_pretest_associations_before_exclusions": len(
            all_pretest_associations
        ),
        "pretest_associations": len(pretest_associations),
        "output_files": output_files,
        "output_sha256": output_sha256,
        "review_guide": (
            "eventx/features/KOL_BLIND_REVIEW_GUIDE.md" if args.blind else None
        ),
        "status": "awaiting_blind_review" if args.blind else "awaiting_review",
    }
    (out_dir / "kol_association_audit_report.json").write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n"
    )
    print(json.dumps(report, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
