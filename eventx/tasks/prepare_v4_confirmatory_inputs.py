"""Prepare point-in-time EventX v4 confirmatory trades and news events once."""

from __future__ import annotations

from collections import Counter
from datetime import datetime, timedelta, timezone
import json
import os
from pathlib import Path
from typing import Any, Iterator

import joblib
import numpy as np
from sklearn.preprocessing import normalize

from eventx.features.v2_1_association import associate, market_spec, normalized_tokens
from eventx.features.v4_news import (
    market_relative_novelty,
    normalized_publisher,
    story_diffusion_counts,
)
from eventx.settings import REPO_ROOT
from eventx.tasks.collect_v2_3_news_v2 import normalize_url
from eventx.tasks.export_v3_historical_feasibility import parse_utc, rfc3339
from eventx.tasks.prepare_v3_1_historical_development_arrays import TRADE_DTYPE, sha256_file
from eventx.tasks.prepare_v4_discovery_news_quality import EVENT_DTYPE


PROTOCOL_ID = "eventx-v4-confirmatory-polymarket-20260902"
ROOT = REPO_ROOT / "data/v4/confirmatory/sealed_inputs"
COHORT = REPO_ROOT / "data/v4/confirmatory/cohort_gate/cohort.jsonl"
COLLECTION_GATE = REPO_ROOT / "data/v4/confirmatory/collection_gate/manifest.json"
COLLECTION_REPORT = REPO_ROOT / "data/v4/confirmatory/collection_gate/report.json"
CONSUMPTION_RECEIPT = REPO_ROOT / "data/v4/confirmatory/consumption_receipt.json"
SEMANTIC_MODEL = REPO_ROOT / "data/v4/discovery/prepared/semantic_model.joblib"
OUTPUT = REPO_ROOT / "data/v4/confirmatory/prepared"
MARKETS = OUTPUT / "market_index.jsonl"
TRADES = OUTPUT / "trades.bin"
EVENTS = OUTPUT / "news_quality_events.bin"
PUBLISHERS = OUTPUT / "publishers.json"
REPORT = OUTPUT / "report.json"
MANIFEST = OUTPUT / "manifest.json"
NEWS_START = parse_utc("2026-08-30T00:00:00Z")
TRADE_START = parse_utc("2026-09-06T00:00:00Z")
END = parse_utc("2026-10-30T00:00:00Z")


def relative(path: Path) -> str:
    return str(path.relative_to(REPO_ROOT))


def read_jsonl(path: Path) -> Iterator[dict[str, Any]]:
    with path.open(encoding="utf-8") as handle:
        for line in handle:
            if line.strip():
                yield json.loads(line)


def atomic_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n")
    os.replace(temporary, path)


def atomic_jsonl(path: Path, values: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    with temporary.open("w", encoding="utf-8") as handle:
        for value in values:
            handle.write(json.dumps(value, sort_keys=True, separators=(",", ":")) + "\n")
    os.replace(temporary, path)


def verify_manifest(path: Path) -> None:
    manifest = json.loads(path.read_text(encoding="utf-8"))
    if manifest.get("status") != "passed":
        raise RuntimeError(f"required gate did not pass: {path}")
    for artifact in manifest.get("artifacts", []):
        target = REPO_ROOT / str(artifact["path"])
        if not target.is_file() or sha256_file(target) != str(artifact["sha256"]):
            raise RuntimeError(f"hash-lock failure: {target}")


def verify_consumption_receipt(receipt: dict[str, Any]) -> None:
    if receipt.get("protocol_id") != PROTOCOL_ID or receipt.get("status") != (
        "future_holdout_irreversibly_consumed_before_label_summary"
    ):
        raise RuntimeError("wrong or incomplete consumption receipt")
    for artifact in receipt.get("inputs", []):
        target = REPO_ROOT / str(artifact["path"])
        if not target.is_file() or sha256_file(target) != str(artifact["sha256"]):
            raise RuntimeError(f"consumption-receipt hash failure: {target}")


def timestamp_us(value: datetime) -> int:
    return int(round(value.timestamp() * 1_000_000))


def load_markets() -> tuple[list[dict[str, Any]], dict[tuple[str, str], int]]:
    rows = sorted(read_jsonl(COHORT), key=lambda row: str(row["market_id"]))
    indexed = [{**row, "market_index": index} for index, row in enumerate(rows)]
    lookup = {
        (str(row["market_id"]), str(row["canonical_yes_asset_id"])): index
        for index, row in enumerate(rows)
    }
    if len(rows) != 470 or len(lookup) != len(rows):
        raise RuntimeError("unexpected or duplicate frozen cohort")
    return indexed, lookup


def prepare_trades(lookup: dict[tuple[str, str], int]) -> dict[str, int]:
    maximum_rows = int(
        json.loads(COLLECTION_REPORT.read_text(encoding="utf-8"))["counts"]["trade_rows"]
    )
    temporary = TRADES.with_suffix(TRADES.suffix + ".tmp")
    values = np.memmap(temporary, mode="w+", dtype=TRADE_DTYPE, shape=(maximum_rows,))
    counters: Counter[str] = Counter()
    written = 0
    ordinal = 0
    day = TRADE_START
    while day < END:
        root = ROOT / "trades" / day.date().isoformat()
        for path in sorted(root.glob("batch_*.jsonl")):
            previous_identity: tuple[str, str, str, str] | None = None
            previous_payload: tuple[float, float] | None = None
            for row in read_jsonl(path):
                counters["raw_rows"] += 1
                ordinal += 1
                condition = str(row["condition_id"])
                asset = str(row.get("asset_id") or "")
                market = lookup.get((condition, asset))
                if market is None:
                    raise RuntimeError(f"execution outside frozen YES cohort: {condition}:{asset}")
                stamp = rfc3339(parse_utc(str(row["ts"])))
                identity = (condition, asset, str(row["trade_id"]), stamp)
                payload = (float(row["price"]), float(row["size"]))
                if identity == previous_identity:
                    if previous_payload != payload:
                        raise RuntimeError(f"conflicting trade identity: {identity}")
                    counters["exact_duplicates_collapsed"] += 1
                    continue
                previous_identity, previous_payload = identity, payload
                price, notional = payload
                if not np.isfinite(price) or not 0.0 <= price <= 1.0:
                    raise RuntimeError("invalid trade price")
                if not np.isfinite(notional) or notional <= 0.0:
                    raise RuntimeError("invalid positive trade notional")
                if written >= maximum_rows:
                    raise RuntimeError("trade allocation exceeded collection-gate row count")
                values[written] = (
                    market,
                    timestamp_us(parse_utc(stamp)),
                    price,
                    notional,
                    ordinal,
                )
                written += 1
        day += timedelta(days=1)
    values.flush()
    del values
    os.truncate(temporary, written * TRADE_DTYPE.itemsize)
    array = np.memmap(temporary, mode="r+", dtype=TRADE_DTYPE, shape=(written,))
    array.sort(order=("market", "timestamp_us", "ordinal"), kind="quicksort")
    array.flush()
    del array
    os.replace(temporary, TRADES)
    counters["normalized_rows"] = written
    return dict(counters)


def load_documents() -> tuple[list[dict[str, Any]], dict[str, int]]:
    identities: dict[str, dict[str, Any]] = {}
    counters: Counter[str] = Counter()
    day = NEWS_START
    while day < END:
        path = ROOT / "news" / day.date().isoformat() / "articles.jsonl"
        for row in read_jsonl(path):
            counters["raw_rows"] += 1
            published = parse_utc(str(row["published_at"]))
            ingest = parse_utc(str(row["ingest_ts"]))
            started = parse_utc(str(row["run_started_at"]))
            ended = parse_utc(str(row["run_ended_at"])) if row.get("run_ended_at") else ingest
            available = max(published, ingest, started, ended)
            if available > published + timedelta(hours=24):
                counters["availability_lag_over_24h_excluded"] += 1
                continue
            if not NEWS_START <= available < END:
                counters["outside_feature_clock"] += 1
                continue
            headline = str(row.get("headline") or "").strip()
            summary = str(row.get("summary") or "").strip()
            text = " ".join(value for value in (headline, summary) if value)
            if not text:
                counters["empty_text"] += 1
                continue
            url = str(row.get("url") or "").strip()
            try:
                canonical = normalize_url(url) if url else ""
            except ValueError:
                canonical = ""
            identity = f"url:{canonical}" if canonical else f"id:{row['id']}"
            candidate = {
                "available_at": available,
                "doc_id": str(row["id"]),
                "headline": headline,
                "publisher": normalized_publisher(str(row.get("publisher") or "unknown")),
                "published_at": published,
                "text": text,
                "tokens": normalized_tokens(text),
            }
            current = identities.get(identity)
            if current is None:
                identities[identity] = {"document": candidate, "published": {rfc3339(published)}}
            else:
                counters["duplicate_identity_rows"] += 1
                current["published"].add(rfc3339(published))
                old = current["document"]
                if (available, candidate["doc_id"]) < (old["available_at"], old["doc_id"]):
                    current["document"] = candidate
        day += timedelta(days=1)
    documents = []
    for identity, value in identities.items():
        if identity.startswith("url:") and len(value["published"]) > 1:
            counters["timestamp_conflict_identities_excluded"] += 1
            continue
        documents.append(value["document"])
    documents.sort(key=lambda row: (row["available_at"], row["doc_id"]))
    counters["documents"] = len(documents)
    return documents, dict(counters)


def prepare_events(documents: list[dict[str, Any]], markets: list[dict[str, Any]]) -> tuple[dict[str, Any], list[str]]:
    payload = joblib.load(SEMANTIC_MODEL)
    vectorizer = payload["vectorizer"]
    decomposition = payload["decomposition"]
    document_vectors = normalize(
        decomposition.transform(vectorizer.transform(row["text"] for row in documents)),
        norm="l2",
        copy=False,
    ).astype(np.float32)
    market_vectors = normalize(
        decomposition.transform(vectorizer.transform(row["question"] for row in markets)),
        norm="l2",
        copy=False,
    ).astype(np.float32)
    token_index: dict[str, set[int]] = {}
    for document, row in enumerate(documents):
        for token in row["tokens"]:
            token_index.setdefault(token, set()).add(document)
    publishers = sorted({str(row["publisher"]) for row in documents})
    publisher_index = {value: index for index, value in enumerate(publishers)}
    if len(publishers) >= np.iinfo(np.uint16).max:
        raise RuntimeError("publisher dictionary exceeds uint16")
    times = np.asarray([timestamp_us(row["available_at"]) for row in documents], dtype=np.int64)
    _reports, diffusion_publishers = story_diffusion_counts(
        times,
        [str(row["headline"]) for row in documents],
        [str(row["publisher"]) for row in documents],
    )
    raw_events: list[tuple[int, int, int, int, float, float, int]] = []
    markets_with_events = 0
    for market_index, market in enumerate(markets):
        spec = market_spec(str(market["question"]), str(market["category"]))
        seeds = set(spec.anchors) | set(spec.event_terms) | set(spec.keywords)
        for phrase in spec.phrases:
            seeds.update(normalized_tokens(phrase))
        candidates: set[int] = set()
        for token in seeds:
            candidates.update(token_index.get(token, set()))
        matched = []
        for document in sorted(candidates):
            reasons, _terms = associate(spec, str(documents[document]["text"]))
            if reasons:
                matched.append(document)
        markets_with_events += int(bool(matched))
        for document in matched:
            relevance = float(np.clip(market_vectors[market_index] @ document_vectors[document], 0.0, 1.0))
            raw_events.append((
                market_index,
                int(times[document]),
                document,
                publisher_index[str(documents[document]["publisher"])],
                relevance,
                1.0,
                int(diffusion_publishers[document]),
            ))
    events = np.asarray(raw_events, dtype=EVENT_DTYPE)
    if len(events):
        events.sort(order=("market", "timestamp_us", "document"), kind="quicksort")
        boundaries = np.concatenate(([0], np.flatnonzero(np.diff(events["market"])) + 1, [len(events)]))
        for left, right in zip(boundaries[:-1], boundaries[1:]):
            indices = np.asarray(events["document"][left:right], dtype=np.int64)
            events["novelty"][left:right] = market_relative_novelty(
                np.asarray(events["timestamp_us"][left:right], dtype=np.int64),
                document_vectors[indices],
                prior_documents=20,
                window_minutes=7 * 1440,
            )
    temporary = EVENTS.with_suffix(EVENTS.suffix + ".tmp")
    events.tofile(temporary)
    os.replace(temporary, EVENTS)
    return {
        "events": len(events),
        "markets_with_events": markets_with_events,
        "cross_publisher_events": int(np.sum(events["diffusion_publishers"] >= 2)),
    }, publishers


def main() -> None:
    if any(path.exists() for path in (MARKETS, TRADES, EVENTS, PUBLISHERS, REPORT, MANIFEST)):
        raise SystemExit("v4 confirmatory prepared artifact already exists; rerun prohibited")
    if not CONSUMPTION_RECEIPT.is_file():
        raise SystemExit("holdout consumption receipt must exist first")
    receipt = json.loads(CONSUMPTION_RECEIPT.read_text(encoding="utf-8"))
    verify_consumption_receipt(receipt)
    verify_manifest(COLLECTION_GATE)
    OUTPUT.mkdir(parents=True, exist_ok=True)
    markets, lookup = load_markets()
    atomic_jsonl(MARKETS, markets)
    trade_stats = prepare_trades(lookup)
    documents, document_stats = load_documents()
    event_stats, publishers = prepare_events(documents, markets)
    atomic_json(PUBLISHERS, publishers)
    report = {
        "protocol_id": PROTOCOL_ID,
        "created_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "status": "confirmatory_inputs_prepared_after_consumption_receipt",
        "models_or_metrics_computed": False,
        "label_summary_disclosed": False,
        "markets": len(markets),
        "trades": trade_stats,
        "documents": document_stats,
        "news_events": event_stats,
        "artifacts": [
            {"path": relative(path), "sha256": sha256_file(path)}
            for path in (MARKETS, TRADES, EVENTS, PUBLISHERS)
        ],
    }
    atomic_json(REPORT, report)
    atomic_json(MANIFEST, {
        "protocol_id": PROTOCOL_ID,
        "status": "prepared",
        "artifacts": [
            {"path": relative(path), "sha256": sha256_file(path)}
            for path in (MARKETS, TRADES, EVENTS, PUBLISHERS, REPORT, Path(__file__).resolve())
        ],
        "inputs": [
            {"path": relative(path), "sha256": sha256_file(path)}
            for path in (COLLECTION_GATE, CONSUMPTION_RECEIPT, COHORT, SEMANTIC_MODEL)
        ],
    })
    print(json.dumps({"status": report["status"], "markets": len(markets), "trades": trade_stats["normalized_rows"], "documents": document_stats["documents"], "news_events": event_stats["events"]}, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
