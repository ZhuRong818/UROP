"""Build the frozen, label-blind EventX v2.1 news/KOL association audit."""

from __future__ import annotations

import argparse
from collections import Counter, defaultdict
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import random
from typing import Any, Iterator

from eventx.features.v2_1_association import (
    RULE_VERSION,
    associate,
    candidate_evidence,
    is_retrieval_candidate,
    market_spec,
)
from eventx.settings import REPO_ROOT


DEFAULT_PROTOCOL = REPO_ROOT / "eventx" / "release" / "v2_1" / "protocol.json"
DEFAULT_COHORT = REPO_ROOT / "data" / "v2_1" / "cohort" / "selected_markets.jsonl"
DEFAULT_COHORT_MANIFEST = (
    REPO_ROOT / "data" / "v2_1" / "cohort" / "cohort_freeze_manifest.json"
)
DEFAULT_NEWS = REPO_ROOT / "data" / "v2_1" / "prospective" / "raw" / "news_latest.jsonl"
DEFAULT_KOL = REPO_ROOT / "data" / "v2_1" / "prospective" / "raw" / "kol_tweets.jsonl"
DEFAULT_TARGETED_NEWS = (
    REPO_ROOT / "data" / "v2_1" / "association" / "candidate_retrieval"
    / "news_targeted.jsonl"
)
DEFAULT_TARGETED_KOL = (
    REPO_ROOT / "data" / "v2_1" / "association" / "candidate_retrieval"
    / "kol_targeted.jsonl"
)
DEFAULT_OUTPUT = REPO_ROOT / "data" / "v2_1" / "association" / "v1_audit"
RULE_SOURCE = REPO_ROOT / "eventx" / "features" / "v2_1_association.py"
SAMPLE_SEED = 83
TARGET_PER_CELL = 75
PROHIBITED_FIELDS = {
    "forward_logodds",
    "forward_return",
    "label",
    "metric",
    "prediction",
    "probability_prediction",
    "target",
    "y",
    "y_jump",
}


def parse_utc(value: str) -> datetime:
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def read_jsonl(path: Path) -> Iterator[dict[str, Any]]:
    with path.open() as handle:
        for line_number, line in enumerate(handle, start=1):
            if not line.strip():
                continue
            value = json.loads(line)
            if not isinstance(value, dict):
                raise ValueError(f"{path}:{line_number} must be a JSON object")
            yield value


def load_object(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text())
    if not isinstance(value, dict):
        raise ValueError(f"{path} must contain a JSON object")
    return value


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def content_hash(text: str) -> str:
    normalized = " ".join(text.lower().split())
    return hashlib.sha256(normalized.encode()).hexdigest()


def stable_hash(value: str) -> str:
    return hashlib.sha256(value.encode()).hexdigest()


def relative(path: Path) -> str:
    return str(path.resolve().relative_to(REPO_ROOT.resolve()))


def atomic_json(path: Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n")
    temporary.replace(path)


def atomic_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    with temporary.open("w") as handle:
        for row in rows:
            handle.write(json.dumps(row, sort_keys=True) + "\n")
    temporary.replace(path)


def document_text(source: str, record: dict[str, Any]) -> str:
    if source == "news":
        return " ".join(
            str(record.get(field) or "").strip()
            for field in ("headline", "summary")
            if str(record.get(field) or "").strip()
        )
    return str(record.get("text") or "").strip()


def load_documents(
    path: Path,
    *,
    source: str,
    protocol_id: str,
    cutoff: datetime,
) -> tuple[list[dict[str, Any]], dict[str, int]]:
    documents: dict[str, dict[str, Any]] = {}
    seen_content: set[str] = set()
    stats: Counter[str] = Counter()
    for envelope in read_jsonl(path):
        stats["rows_scanned"] += 1
        if envelope.get("_protocol_id") != protocol_id:
            raise ValueError(f"{path} contains a different protocol ID")
        record = envelope.get("record")
        if not isinstance(record, dict):
            stats["invalid_envelopes"] += 1
            continue
        event_value = envelope.get("_event_ts")
        if not event_value:
            stats["missing_event_ts"] += 1
            continue
        try:
            event_ts = parse_utc(str(event_value))
        except ValueError:
            stats["invalid_event_ts"] += 1
            continue
        if event_ts >= cutoff:
            stats["at_or_after_cutoff"] += 1
            continue
        text = document_text(source, record)
        if not text:
            stats["empty_text"] += 1
            continue
        digest = content_hash(text)
        doc_id = str(envelope.get("_record_key") or digest)
        if doc_id in documents:
            stats["duplicate_doc_id"] += 1
            continue
        if digest in seen_content:
            stats["duplicate_content"] += 1
            continue
        seen_content.add(digest)
        documents[doc_id] = {
            "content_hash": digest,
            "doc_id": doc_id,
            "event_ts": event_ts.isoformat().replace("+00:00", "Z"),
            "metadata": {
                "display_name": record.get("display_name"),
                "handle": record.get("handle"),
                "headline": record.get("headline"),
                "publisher": record.get("publisher"),
                "summary": record.get("summary"),
                "url": record.get("url"),
            },
            "retrieved_at": envelope.get("_retrieved_at"),
            "source": source,
            "text": text,
        }
    stats["eligible_unique_documents"] = len(documents)
    return sorted(documents.values(), key=lambda row: row["doc_id"]), dict(stats)


def round_robin_sample(
    rows: list[dict[str, Any]],
    *,
    limit: int,
    seed: int,
) -> list[dict[str, Any]]:
    rng = random.Random(seed)
    groups: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        groups[(str(row["category"]), str(row["market_id"]))].append(row)
    for values in groups.values():
        rng.shuffle(values)
    order = sorted(groups)
    rng.shuffle(order)
    selected: list[dict[str, Any]] = []
    while len(selected) < limit and any(groups.values()):
        for key in order:
            if groups[key] and len(selected) < limit:
                selected.append(groups[key].pop())
    return selected


def merge_documents(
    batches: list[list[dict[str, Any]]],
) -> tuple[list[dict[str, Any]], int]:
    merged: dict[str, dict[str, Any]] = {}
    content_seen: set[str] = set()
    duplicates = 0
    for rows in batches:
        for row in rows:
            if row["doc_id"] in merged or row["content_hash"] in content_seen:
                duplicates += 1
                continue
            merged[row["doc_id"]] = row
            content_seen.add(row["content_hash"])
    return sorted(merged.values(), key=lambda row: row["doc_id"]), duplicates


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--protocol", type=Path, default=DEFAULT_PROTOCOL)
    parser.add_argument("--cohort", type=Path, default=DEFAULT_COHORT)
    parser.add_argument("--cohort-manifest", type=Path, default=DEFAULT_COHORT_MANIFEST)
    parser.add_argument("--news", type=Path, default=DEFAULT_NEWS)
    parser.add_argument("--kol", type=Path, default=DEFAULT_KOL)
    parser.add_argument("--targeted-news", type=Path, default=DEFAULT_TARGETED_NEWS)
    parser.add_argument("--targeted-kol", type=Path, default=DEFAULT_TARGETED_KOL)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--target-per-cell", type=int, default=TARGET_PER_CELL)
    args = parser.parse_args()

    protocol = load_object(args.protocol)
    cohort_manifest = load_object(args.cohort_manifest)
    if cohort_manifest.get("status") != "frozen":
        raise SystemExit("cohort is not frozen")
    if cohort_manifest.get("label_blind") is not True or cohort_manifest.get("labels_read") != []:
        raise SystemExit("cohort label-blind seal is invalid")
    if sha256_file(args.cohort) != cohort_manifest.get("output", {}).get("sha256"):
        raise SystemExit("selected cohort hash does not match its freeze manifest")
    cutoff = parse_utc(protocol["windows"]["development"]["start"])
    markets = list(read_jsonl(args.cohort))
    if len(markets) != int(cohort_manifest.get("selected_markets", -1)):
        raise SystemExit("selected cohort row count mismatch")
    for row in markets:
        prohibited = PROHIBITED_FIELDS.intersection(key.lower() for key in row)
        if prohibited:
            raise SystemExit(f"cohort contains prohibited fields: {sorted(prohibited)}")

    source_paths = {
        "news": [args.news, *([args.targeted_news] if args.targeted_news.is_file() else [])],
        "kol": [args.kol, *([args.targeted_kol] if args.targeted_kol.is_file() else [])],
    }
    documents_by_source: dict[str, list[dict[str, Any]]] = {}
    document_stats: dict[str, dict[str, Any]] = {}
    for source, paths in source_paths.items():
        batches: list[list[dict[str, Any]]] = []
        file_stats: dict[str, dict[str, int]] = {}
        for path in paths:
            documents, stats = load_documents(
                path,
                source=source,
                protocol_id=str(protocol["protocol_id"]),
                cutoff=cutoff,
            )
            batches.append(documents)
            file_stats[relative(path)] = stats
        merged, cross_file_duplicates = merge_documents(batches)
        documents_by_source[source] = merged
        document_stats[source] = {
            "cross_file_duplicates": cross_file_duplicates,
            "eligible_unique_documents": len(merged),
            "files": file_stats,
        }

    specs = []
    candidates: list[dict[str, Any]] = []
    associations: dict[str, list[dict[str, Any]]] = {"news": [], "kol": []}
    for market in markets:
        spec = market_spec(str(market.get("question") or ""), str(market["category"]))
        specs.append(
            {
                "market_id": market["market_id"],
                "outcome_id": market["outcome_id"],
                "rule_version": RULE_VERSION,
                "spec": spec.to_dict(),
                "venue": market["venue"],
            }
        )
        for source, documents in documents_by_source.items():
            for document in documents:
                evidence = candidate_evidence(spec, document["text"])
                if not is_retrieval_candidate(evidence):
                    continue
                reasons, terms = associate(spec, document["text"])
                prediction = "matched" if reasons else "hard_unmatched"
                pair_id = stable_hash(
                    f"{market['venue']}:{market['market_id']}:{source}:{document['doc_id']}"
                )
                pair = {
                    "association_rule": RULE_VERSION,
                    "category": market["category"],
                    "content_hash": document["content_hash"],
                    "doc_id": document["doc_id"],
                    "event_ts": document["event_ts"],
                    "evidence": evidence,
                    "market_id": market["market_id"],
                    "market_question": market["question"],
                    "match_reasons": reasons,
                    "match_terms": terms,
                    "outcome_id": market["outcome_id"],
                    "pair_id": pair_id,
                    "prediction": prediction,
                    "retrieved_at": document["retrieved_at"],
                    "source": source,
                    "venue": market["venue"],
                }
                candidates.append(pair)
                if reasons:
                    associations[source].append(pair)

    candidates.sort(key=lambda row: row["pair_id"])
    specs.sort(key=lambda row: (row["venue"], row["market_id"]))
    for values in associations.values():
        values.sort(key=lambda row: row["pair_id"])

    sampled: list[dict[str, Any]] = []
    realized_cells: dict[str, int] = {}
    for cell_index, (source, prediction) in enumerate(
        (
            ("news", "matched"),
            ("news", "hard_unmatched"),
            ("kol", "matched"),
            ("kol", "hard_unmatched"),
        )
    ):
        eligible = [
            row
            for row in candidates
            if row["source"] == source and row["prediction"] == prediction
        ]
        values = round_robin_sample(
            eligible,
            limit=args.target_per_cell,
            seed=SAMPLE_SEED + cell_index,
        )
        sampled.extend(values)
        realized_cells[f"{source}:{prediction}"] = len(values)
    random.Random(SAMPLE_SEED + 101).shuffle(sampled)

    blind_rows: list[dict[str, Any]] = []
    key_rows: list[dict[str, Any]] = []
    document_lookup = {
        (document["source"], document["doc_id"]): document
        for documents in documents_by_source.values()
        for document in documents
    }
    for pair in sampled:
        audit_id = stable_hash(f"v2.1-association-audit:{pair['pair_id']}")[:16]
        document = document_lookup[(pair["source"], pair["doc_id"])]
        blind_rows.append(
            {
                "audit_id": audit_id,
                "category": pair["category"],
                "document_event_ts": pair["event_ts"],
                "document_metadata": document["metadata"],
                "document_source": pair["source"],
                "document_text": document["text"],
                "market_question": pair["market_question"],
                "review_confidence": "",
                "review_label": "",
                "review_rationale": "",
                "reviewer": "",
                "venue": pair["venue"],
            }
        )
        key_rows.append(
            {
                "audit_id": audit_id,
                "category": pair["category"],
                "content_hash": pair["content_hash"],
                "doc_id": pair["doc_id"],
                "evidence": pair["evidence"],
                "market_id": pair["market_id"],
                "match_reasons": pair["match_reasons"],
                "match_terms": pair["match_terms"],
                "pair_id": pair["pair_id"],
                "rule_prediction": pair["prediction"],
                "source": pair["source"],
                "venue": pair["venue"],
            }
        )

    output_paths = {
        "candidate_pool": args.output / "association_candidate_pool.jsonl",
        "news_documents": args.output / "news_documents_predevelopment.jsonl",
        "kol_documents": args.output / "kol_documents_predevelopment.jsonl",
        "market_specs": args.output / "market_specs.jsonl",
        "news_associations": args.output / "news_market_assoc_predevelopment.jsonl",
        "kol_associations": args.output / "kol_market_assoc_predevelopment.jsonl",
        "blind_review": args.output / "association_blind_review.jsonl",
        "blind_key": args.output / "association_blind_key.jsonl",
    }
    atomic_jsonl(output_paths["candidate_pool"], candidates)
    atomic_jsonl(output_paths["news_documents"], documents_by_source["news"])
    atomic_jsonl(output_paths["kol_documents"], documents_by_source["kol"])
    atomic_jsonl(output_paths["market_specs"], specs)
    atomic_jsonl(output_paths["news_associations"], associations["news"])
    atomic_jsonl(output_paths["kol_associations"], associations["kol"])
    atomic_jsonl(output_paths["blind_review"], blind_rows)
    atomic_jsonl(output_paths["blind_key"], key_rows)
    report = {
        "association_rule": RULE_VERSION,
        "audit_cutoff_exclusive": cutoff.isoformat().replace("+00:00", "Z"),
        "candidate_pairs": len(candidates),
        "candidate_pairs_by_source_prediction": dict(
            sorted(Counter(f"{row['source']}:{row['prediction']}" for row in candidates).items())
        ),
        "cohort_markets": len(markets),
        "document_stats": document_stats,
        "input_hashes": {
            relative(args.cohort): sha256_file(args.cohort),
            relative(args.cohort_manifest): sha256_file(args.cohort_manifest),
            relative(args.protocol): sha256_file(args.protocol),
            relative(RULE_SOURCE): sha256_file(RULE_SOURCE),
            **{
                relative(path): sha256_file(path)
                for paths in source_paths.values()
                for path in paths
                if path not in {args.news, args.kol}
            },
        },
        "label_blind": True,
        "labels_read": [],
        "outputs": {
            name: {
                "path": relative(path),
                "sha256": sha256_file(path),
            }
            for name, path in output_paths.items()
        },
        "predictions_hidden": True,
        "protocol_id": protocol["protocol_id"],
        "realized_sample_cells": realized_cells,
        "sample_categories": dict(sorted(Counter(row["category"] for row in sampled).items())),
        "sample_rows": len(sampled),
        "sample_seed": SAMPLE_SEED,
        "source_files": {
            source: [relative(path) for path in paths]
            for source, paths in source_paths.items()
        },
        "status": "awaiting_independent_blind_review",
        "target_per_cell": args.target_per_cell,
    }
    atomic_json(args.output / "association_audit_preparation_report.json", report)
    print(json.dumps(report, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
