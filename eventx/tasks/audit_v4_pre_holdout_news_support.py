"""Audit label-blind v4 news exposure before the future holdout begins."""

from __future__ import annotations

from collections import Counter
from datetime import datetime, timezone
import json
import os
from pathlib import Path
from typing import Any, Iterator

from eventx.features.v2_1_association import associate, market_spec, normalized_tokens
from eventx.settings import REPO_ROOT
from eventx.tasks.audit_v3_historical_feasibility import parse_utc


NEWS_ROOT = REPO_ROOT / "data/v4/confirmatory/sealed_inputs/news"
COHORT = REPO_ROOT / "data/v4/confirmatory/cohort_gate/cohort.jsonl"
OUTPUT = REPO_ROOT / "data/v4/confirmatory/pre_holdout_news_support.json"


def read_jsonl(path: Path) -> Iterator[dict[str, Any]]:
    with path.open(encoding="utf-8") as handle:
        for line in handle:
            if line.strip():
                yield json.loads(line)


def atomic_json(path: Path, value: Any) -> None:
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n")
    os.replace(temporary, path)


def main() -> None:
    if OUTPUT.exists():
        raise SystemExit("v4 pre-holdout news-support audit already exists")
    documents: dict[str, dict[str, Any]] = {}
    source_files = sorted(NEWS_ROOT.glob("*/articles.jsonl"))
    for path in source_files:
        for row in read_jsonl(path):
            identity = str(row["id"])
            timestamps = [
                parse_utc(str(row[field]))
                for field in ("published_at", "ingest_ts", "run_started_at")
                if row.get(field)
            ]
            if row.get("run_ended_at"):
                timestamps.append(parse_utc(str(row["run_ended_at"])))
            available = max(timestamps)
            text = " ".join(
                str(row.get(field) or "").strip()
                for field in ("headline", "summary")
                if str(row.get(field) or "").strip()
            )
            if text and identity not in documents:
                documents[identity] = {
                    "available_at": available,
                    "text": text,
                    "tokens": normalized_tokens(text),
                }
    values = list(documents.values())
    token_index: dict[str, set[int]] = {}
    for index, document in enumerate(values):
        for token in document["tokens"]:
            token_index.setdefault(token, set()).add(index)
    cohort = list(read_jsonl(COHORT))
    events = 0
    markets_with_events = 0
    by_category_events: Counter[str] = Counter()
    by_category_markets: Counter[str] = Counter()
    maximum = 0
    for market in cohort:
        spec = market_spec(str(market["question"]), str(market["category"]))
        seeds = set(spec.anchors) | set(spec.event_terms) | set(spec.keywords)
        for phrase in spec.phrases:
            seeds.update(normalized_tokens(phrase))
        candidates: set[int] = set()
        for token in seeds:
            candidates.update(token_index.get(token, set()))
        matched = sum(
            bool(associate(spec, str(values[index]["text"]))[0])
            for index in candidates
        )
        if matched:
            markets_with_events += 1
            by_category_markets[str(market["category"])] += 1
        events += matched
        by_category_events[str(market["category"])] += matched
        maximum = max(maximum, matched)
    report = {
        "protocol_id": "eventx-v4-confirmatory-polymarket-20260902",
        "created_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "status": "label_blind_diagnostic_complete",
        "future_prices_labels_predictions_or_metrics_read": False,
        "source_files": [str(path.relative_to(REPO_ROOT)) for path in source_files],
        "documents": len(values),
        "cohort_markets": len(cohort),
        "association_events": events,
        "markets_with_events": markets_with_events,
        "market_coverage": markets_with_events / len(cohort),
        "maximum_events_one_market": maximum,
        "events_by_category": dict(by_category_events),
        "markets_with_events_by_category": dict(by_category_markets),
        "interpretation": "pre-holdout exposure diagnostic only; it cannot modify the frozen cohort, feature definitions, models or decision rule",
    }
    atomic_json(OUTPUT, report)
    print(json.dumps(report, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
