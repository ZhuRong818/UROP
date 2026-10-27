"""Prepare frozen semantic and diffusion news events for EventX v4 discovery."""

from __future__ import annotations

from collections import Counter
from datetime import datetime, timezone
import json
import os
from pathlib import Path
from typing import Any, Iterator

import joblib
import numpy as np
from sklearn.decomposition import TruncatedSVD
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.preprocessing import normalize

from eventx.features.v2_1_association import (
    associate,
    market_spec,
    normalized_tokens,
)
from eventx.features.v4_news import (
    market_relative_novelty,
    normalized_publisher,
    story_diffusion_counts,
)
from eventx.settings import REPO_ROOT
from eventx.tasks.collect_v2_3_news_v2 import normalize_url
from eventx.tasks.export_v3_historical_feasibility import parse_utc, rfc3339
from eventx.tasks.prepare_v3_1_historical_development_arrays import (
    NEWS_DTYPE,
    sha256_file,
)


NEWS = REPO_ROOT / "data/v3_historical/primary/label_blind_inputs/news.jsonl"
MARKETS = REPO_ROOT / "data/v3_1_historical/primary/development/prepared/market_index.jsonl"
REFERENCE_ASSOCIATIONS = (
    REPO_ROOT / "data/v3_1_historical/primary/development/prepared/news_associations.bin"
)
OUTPUT = REPO_ROOT / "data/v4/discovery/prepared"
MODEL = OUTPUT / "semantic_model.joblib"
EVENTS = OUTPUT / "news_quality_events.bin"
PUBLISHERS = OUTPUT / "publishers.json"
REPORT = OUTPUT / "report.json"
MANIFEST = OUTPUT / "manifest.json"
DEVELOPMENT_END = parse_utc("2026-07-22T00:00:00Z")
COMPONENTS = 64
MAX_FEATURES = 50_000
EVENT_DTYPE = np.dtype(
    [
        ("market", "<u4"),
        ("timestamp_us", "<i8"),
        ("document", "<u4"),
        ("publisher", "<u2"),
        ("relevance", "<f4"),
        ("novelty", "<f4"),
        ("diffusion_publishers", "<u2"),
    ],
    align=False,
)


def relative(path: Path) -> str:
    return str(path.relative_to(REPO_ROOT))


def atomic_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n")
    os.replace(temporary, path)


def read_jsonl(path: Path) -> Iterator[dict[str, Any]]:
    with path.open(encoding="utf-8") as handle:
        for line in handle:
            if line.strip():
                yield json.loads(line)


def timestamp_us(value: datetime) -> int:
    return int(round(value.timestamp() * 1_000_000))


def load_documents() -> tuple[list[dict[str, Any]], dict[str, int]]:
    """Mirror the v3.1 identity/clock policy while retaining v4 text metadata."""

    identities: dict[str, dict[str, Any]] = {}
    counters: Counter[str] = Counter()
    for row in read_jsonl(NEWS):
        available = parse_utc(str(row["available_at"]))
        if available >= DEVELOPMENT_END:
            continue
        published = parse_utc(str(row["published_at"]))
        headline = str(row.get("headline") or "").strip()
        summary = str(row.get("summary") or "").strip()
        text = " ".join(value for value in (headline, summary) if value)
        if not text:
            counters["empty_text"] += 1
            continue
        url = str(row.get("url") or "").strip()
        try:
            normalized = normalize_url(url) if url else ""
        except ValueError:
            normalized = ""
        identity = f"url:{normalized}" if normalized else f"id:{row['id']}"
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
            identities[identity] = {
                "document": candidate,
                "published_values": {rfc3339(published)},
            }
            continue
        counters["duplicate_identity_rows"] += 1
        current["published_values"].add(rfc3339(published))
        existing = current["document"]
        if (candidate["available_at"], candidate["doc_id"]) < (
            existing["available_at"], existing["doc_id"]
        ):
            current["document"] = candidate
    documents = []
    for identity, value in identities.items():
        if identity.startswith("url:") and len(value["published_values"]) > 1:
            counters["timestamp_conflict_identities_excluded"] += 1
            continue
        documents.append(value["document"])
    documents.sort(key=lambda row: (row["available_at"], row["doc_id"]))
    counters["documents"] = len(documents)
    return documents, dict(counters)


def fit_semantic_model(
    documents: list[dict[str, Any]], markets: list[dict[str, Any]]
) -> tuple[np.ndarray, np.ndarray, dict[str, Any]]:
    vectorizer = TfidfVectorizer(
        lowercase=True,
        strip_accents="unicode",
        ngram_range=(1, 2),
        min_df=3,
        max_df=0.995,
        max_features=MAX_FEATURES,
        sublinear_tf=True,
        norm="l2",
        dtype=np.float32,
    )
    document_tfidf = vectorizer.fit_transform(row["text"] for row in documents)
    decomposition = TruncatedSVD(
        n_components=COMPONENTS,
        algorithm="randomized",
        n_iter=5,
        random_state=73,
    )
    document_vectors = normalize(
        decomposition.fit_transform(document_tfidf), norm="l2", copy=False
    ).astype(np.float32)
    market_vectors = normalize(
        decomposition.transform(vectorizer.transform(row["question"] for row in markets)),
        norm="l2",
        copy=False,
    ).astype(np.float32)
    payload = {
        "protocol": "eventx-v4-semantic-lsa-v1",
        "vectorizer": vectorizer,
        "decomposition": decomposition,
        "normalization": "row_l2_after_truncated_svd",
        "relevance": "clip(cosine_lsa(question, headline_plus_summary), 0, 1)",
    }
    temporary = MODEL.with_suffix(MODEL.suffix + ".tmp")
    joblib.dump(payload, temporary, compress=3)
    os.replace(temporary, MODEL)
    return document_vectors, market_vectors, {
        "components": COMPONENTS,
        "maximum_vocabulary": MAX_FEATURES,
        "fitted_vocabulary": len(vectorizer.vocabulary_),
        "document_tfidf_shape": list(document_tfidf.shape),
        "explained_variance_ratio_sum": float(
            decomposition.explained_variance_ratio_.sum()
        ),
        "random_state": 73,
    }


def build_events(
    documents: list[dict[str, Any]],
    markets: list[dict[str, Any]],
    document_vectors: np.ndarray,
    market_vectors: np.ndarray,
) -> tuple[np.ndarray, dict[str, Any], list[str]]:
    token_index: dict[str, set[int]] = {}
    for document_index, document in enumerate(documents):
        for token in document["tokens"]:
            token_index.setdefault(token, set()).add(document_index)
    publisher_values = sorted({str(row["publisher"]) for row in documents})
    if len(publisher_values) >= np.iinfo(np.uint16).max:
        raise RuntimeError("publisher index exceeds uint16")
    publisher_lookup = {value: index for index, value in enumerate(publisher_values)}
    doc_times = np.asarray(
        [timestamp_us(row["available_at"]) for row in documents], dtype=np.int64
    )
    _story_reports, story_publishers = story_diffusion_counts(
        doc_times,
        [str(row["headline"]) for row in documents],
        [str(row["publisher"]) for row in documents],
    )
    expected = REFERENCE_ASSOCIATIONS.stat().st_size // NEWS_DTYPE.itemsize
    events = np.empty(expected, dtype=EVENT_DTYPE)
    written = 0
    markets_with_events = 0
    for market_index, market in enumerate(markets):
        if int(market["market_index"]) != market_index:
            raise RuntimeError("market index is not deterministic")
        spec = market_spec(str(market["question"]), str(market["category"]))
        seeds = set(spec.anchors) | set(spec.event_terms) | set(spec.keywords)
        for phrase in spec.phrases:
            seeds.update(normalized_tokens(phrase))
        candidates: set[int] = set()
        for token in seeds:
            candidates.update(token_index.get(token, set()))
        matched = []
        for document_index in sorted(candidates):
            reasons, _terms = associate(spec, str(documents[document_index]["text"]))
            if reasons:
                matched.append(document_index)
        if matched:
            markets_with_events += 1
        for document_index in matched:
            if written >= len(events):
                raise RuntimeError("v4 association count exceeds frozen v3.1 count")
            relevance = float(
                np.clip(
                    market_vectors[market_index] @ document_vectors[document_index],
                    0.0,
                    1.0,
                )
            )
            events[written] = (
                market_index,
                doc_times[document_index],
                document_index,
                publisher_lookup[str(documents[document_index]["publisher"])],
                relevance,
                1.0,
                story_publishers[document_index],
            )
            written += 1
        if (market_index + 1) % 500 == 0:
            print(
                f"v4 associated {market_index + 1}/{len(markets)} markets; "
                f"events={written}",
                flush=True,
            )
    if written != expected:
        raise RuntimeError(f"v4 association count {written} != frozen reference {expected}")
    events.sort(order=("market", "timestamp_us", "document"), kind="quicksort")
    reference = np.memmap(
        REFERENCE_ASSOCIATIONS, mode="r", dtype=NEWS_DTYPE, shape=(expected,)
    )
    if not np.array_equal(events["market"], reference["market"]) or not np.array_equal(
        events["timestamp_us"], reference["timestamp_us"]
    ):
        raise RuntimeError("v4 associations differ from frozen v3.1 membership/clock")
    boundaries = np.concatenate(
        (
            [0],
            np.flatnonzero(np.diff(events["market"])) + 1,
            [len(events)],
        )
    )
    for number, (left, right) in enumerate(zip(boundaries[:-1], boundaries[1:]), start=1):
        document_indices = np.asarray(events["document"][left:right], dtype=np.int64)
        events["novelty"][left:right] = market_relative_novelty(
            np.asarray(events["timestamp_us"][left:right], dtype=np.int64),
            document_vectors[document_indices],
            prior_documents=20,
            window_minutes=7 * 1440,
        )
        if number % 500 == 0:
            print(f"v4 novelty {number}/{len(boundaries) - 1} markets", flush=True)
    return events, {
        "events": len(events),
        "markets_with_events": markets_with_events,
        "relevance_mean": float(events["relevance"].mean()),
        "relevance_p90": float(np.quantile(events["relevance"], 0.90)),
        "novelty_mean": float(events["novelty"].mean()),
        "novelty_p10": float(np.quantile(events["novelty"], 0.10)),
        "cross_publisher_events": int(np.sum(events["diffusion_publishers"] >= 2)),
        "association_membership_and_clock_equal_v3_1": True,
    }, publisher_values


def main() -> None:
    if any(path.exists() for path in (MODEL, EVENTS, PUBLISHERS, REPORT, MANIFEST)):
        raise SystemExit("v4 discovery news-quality artifact already exists")
    OUTPUT.mkdir(parents=True, exist_ok=True)
    documents, document_stats = load_documents()
    markets = list(read_jsonl(MARKETS))
    document_vectors, market_vectors, semantic = fit_semantic_model(documents, markets)
    events, event_stats, publishers = build_events(
        documents, markets, document_vectors, market_vectors
    )
    events.tofile(EVENTS)
    atomic_json(PUBLISHERS, publishers)
    report = {
        "protocol_id": "eventx-v4-confirmatory-20260902",
        "created_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "status": "prepared_discovery_news_quality",
        "label_blind_feature_construction": True,
        "historical_interval_outcomes_previously_opened": True,
        "documents": document_stats,
        "semantic_model": semantic,
        "events": event_stats,
        "feature_semantics": {
            "text": "headline plus summary",
            "relevance": "clipped LSA cosine between market question and article text",
            "novelty": "one minus maximum clipped LSA cosine to 20 prior associated market articles within seven days",
            "diffusion": "at least two normalized publishers reported the same normalized exact headline within the prior 24 hours as of article availability",
            "virality": "not measured",
        },
        "artifacts": [
            {"path": relative(path), "sha256": sha256_file(path)}
            for path in (MODEL, EVENTS, PUBLISHERS)
        ],
        "inputs": [
            {"path": relative(path), "sha256": sha256_file(path)}
            for path in (NEWS, MARKETS, REFERENCE_ASSOCIATIONS)
        ],
    }
    atomic_json(REPORT, report)
    atomic_json(
        MANIFEST,
        {
            "protocol_id": report["protocol_id"],
            "status": report["status"],
            "artifacts": [
                {"path": relative(path), "sha256": sha256_file(path)}
                for path in (MODEL, EVENTS, PUBLISHERS, REPORT, Path(__file__).resolve())
            ],
            "inputs": report["inputs"],
        },
    )
    print(json.dumps({
        "status": report["status"],
        "documents": document_stats,
        "semantic_model": semantic,
        "events": event_stats,
    }, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
