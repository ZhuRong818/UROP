"""Create a reproducible pre-test blind audit for EventX news associations."""

from __future__ import annotations

import argparse
import hashlib
import json
import random
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Iterator

from eventx.features.kol_association import content_hash, parse_ts
from eventx.features.news_association import article_id, article_text
from eventx.settings import REPO_ROOT


def read_jsonl(path: Path) -> Iterator[dict[str, Any]]:
    with path.open() as handle:
        for line in handle:
            if line.strip():
                yield json.loads(line)


def write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w") as handle:
        for row in rows:
            handle.write(json.dumps(row, sort_keys=True) + "\n")


def round_robin_sample(
    rows: list[dict[str, Any]],
    limit: int,
    seed: int,
) -> list[dict[str, Any]]:
    rng = random.Random(seed)
    groups: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        groups[str(row["market_id"])].append(row)
    for values in groups.values():
        rng.shuffle(values)
    selected = []
    market_ids = sorted(groups)
    while len(selected) < limit and any(groups.values()):
        for market_id in market_ids:
            if groups[market_id] and len(selected) < limit:
                selected.append(groups[market_id].pop())
    return selected


def main() -> None:
    parser = argparse.ArgumentParser(description="Build blind EventX news audit")
    parser.add_argument("--version", default="v1")
    parser.add_argument("--matched", type=int, default=70)
    parser.add_argument("--unmatched", type=int, default=30)
    parser.add_argument("--out-dir", type=Path)
    args = parser.parse_args()

    root = REPO_ROOT / "data" / args.version
    out_dir = args.out_dir or root / "audit_news_v1"
    toy_freeze = json.loads((root / "toy" / "frozen_manifest.json").read_text())
    cutoff = parse_ts(toy_freeze["split_boundaries"]["test_start"])
    assert cutoff is not None
    markets = {
        str(row["market_id"]): row
        for row in read_jsonl(root / "toy" / "selected_markets.jsonl")
    }
    associations = [
        row
        for row in read_jsonl(root / "curated" / "news_market_assoc.jsonl")
        if (parse_ts(row.get("ts")) or cutoff) < cutoff
    ]
    association_pairs = {
        (str(row["market_id"]), str(row["doc_id"])) for row in associations
    }
    articles: dict[tuple[str, str], dict[str, Any]] = {}
    for row in read_jsonl(root / "raw" / "news_toy_search.jsonl"):
        market_id = str(row.get("_search_market_id") or "")
        if market_id not in markets:
            continue
        ts = parse_ts(row.get("published_at"))
        if ts is None or ts >= cutoff:
            continue
        doc_id = article_id(row)
        key = (market_id, doc_id)
        articles.setdefault(key, row)

    matched_rows = []
    for association in associations:
        key = (str(association["market_id"]), str(association["doc_id"]))
        article = articles.get(key)
        if article is None:
            continue
        matched_rows.append(
            {
                "market_id": key[0],
                "doc_id": key[1],
                "prediction": "matched",
                "match_reason": association.get("match_reason"),
                "article": article,
            }
        )
    unmatched_rows = []
    seen_unmatched_content: set[tuple[str, str]] = set()
    for (market_id, doc_id), article in articles.items():
        if (market_id, doc_id) in association_pairs:
            continue
        digest = content_hash(article_text(article))
        if (market_id, digest) in seen_unmatched_content:
            continue
        seen_unmatched_content.add((market_id, digest))
        unmatched_rows.append(
            {
                "market_id": market_id,
                "doc_id": doc_id,
                "prediction": "unmatched",
                "match_reason": [],
                "article": article,
            }
        )

    sampled = round_robin_sample(matched_rows, args.matched, 41)
    sampled.extend(round_robin_sample(unmatched_rows, args.unmatched, 43))
    random.Random(47).shuffle(sampled)
    blind_rows = []
    key_rows = []
    for row in sampled:
        market = markets[row["market_id"]]
        article = row["article"]
        audit_id = hashlib.sha256(
            f"{row['market_id']}:{row['doc_id']}:{row['prediction']}".encode()
        ).hexdigest()[:16]
        blind_rows.append(
            {
                "audit_id": audit_id,
                "market_id": row["market_id"],
                "market_question": market["question"],
                "article_ts": article.get("published_at"),
                "article_publisher": article.get("publisher"),
                "article_headline": article.get("headline"),
                "article_summary": article.get("summary"),
                "review_label": "",
                "review_confidence": "",
                "review_rationale": "",
                "reviewer": "",
            }
        )
        key_rows.append(
            {
                "audit_id": audit_id,
                "rule_prediction": row["prediction"],
                "match_reason": row["match_reason"],
                "market_id": row["market_id"],
                "doc_id": row["doc_id"],
            }
        )
    write_jsonl(out_dir / "news_association_blind_review.jsonl", blind_rows)
    write_jsonl(out_dir / "news_association_blind_key.jsonl", key_rows)
    report = {
        "dataset_id": toy_freeze["dataset_id"],
        "test_cutoff_exclusive": toy_freeze["split_boundaries"]["test_start"],
        "predictions_hidden": True,
        "eligible_pretest_matched": len(matched_rows),
        "eligible_pretest_hard_unmatched": len(unmatched_rows),
        "sample_rows": len(blind_rows),
        "sample_composition": dict(Counter(row["prediction"] for row in sampled)),
        "markets_in_sample": len({row["market_id"] for row in sampled}),
        "review_file": str(
            (out_dir / "news_association_blind_review.jsonl")
            .resolve()
            .relative_to(REPO_ROOT)
        ),
        "key_file": str(
            (out_dir / "news_association_blind_key.jsonl")
            .resolve()
            .relative_to(REPO_ROOT)
        ),
    }
    (out_dir / "news_association_audit_report.json").write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n"
    )
    print(json.dumps(report, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
