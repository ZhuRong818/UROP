"""Build the fresh, KOL-only blind audit for the frozen EventX v2.1 v2 candidate."""

from __future__ import annotations

from collections import Counter, defaultdict
import hashlib
import json
from pathlib import Path
import random
from typing import Any, Iterable

from eventx.features.v2_1_kol_association_v2 import (
    LEXICAL_SPEC,
    RULE_VERSION,
    is_retrieval_candidate,
    prediction,
)
from eventx.settings import REPO_ROOT


V1_ROOT = REPO_ROOT / "data" / "v2_1" / "association" / "v1_audit"
CANDIDATE_ROOT = REPO_ROOT / "data" / "v2_1" / "association" / "kol_v2_candidate"
OUTPUT_ROOT = REPO_ROOT / "data" / "v2_1" / "association" / "kol_v2_audit"
RULE_SOURCE = REPO_ROOT / "eventx" / "features" / "v2_1_kol_association_v2.py"
CANDIDATE_FREEZE = CANDIDATE_ROOT / "candidate_freeze_manifest.json"
V1_FREEZE = V1_ROOT / "audit_freeze_manifest.json"
DOCUMENTS = V1_ROOT / "kol_documents_predevelopment.jsonl"
MARKETS = V1_ROOT / "market_specs.jsonl"
EXCLUSIONS = V1_ROOT / "opened_pair_content_exclusions.jsonl"
BLIND_RELEASE = REPO_ROOT / "eventx" / "release" / "v2_1" / "eventx_v2_1_kol_v2_blind_review.jsonl"
SAMPLE_SEED = 211
TARGET_PER_CELL = 75


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    rows = []
    with path.open() as handle:
        for line_number, line in enumerate(handle, start=1):
            if not line.strip():
                continue
            value = json.loads(line)
            if not isinstance(value, dict):
                raise ValueError(f"{path}:{line_number} must be an object")
            rows.append(value)
    return rows


def load(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text())
    if not isinstance(value, dict):
        raise ValueError(f"{path} must contain an object")
    return value


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def stable_hash(value: str) -> str:
    return hashlib.sha256(value.encode()).hexdigest()


def relative(path: Path) -> str:
    return str(path.resolve().relative_to(REPO_ROOT.resolve()))


def jsonl_bytes(rows: Iterable[dict[str, Any]]) -> bytes:
    return "".join(json.dumps(row, sort_keys=True) + "\n" for row in rows).encode()


def write_once(path: Path, payload: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        if path.read_bytes() != payload:
            raise SystemExit(f"refusing to overwrite frozen audit artifact: {path}")
        return
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_bytes(payload)
    temporary.replace(path)


def round_robin_sample(
    rows: list[dict[str, Any]], *, limit: int, seed: int
) -> list[dict[str, Any]]:
    rng = random.Random(seed)
    groups: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        groups[(str(row["category"]), str(row["market_id"]))].append(row)
    for values in groups.values():
        rng.shuffle(values)
    order = sorted(groups)
    rng.shuffle(order)
    selected = []
    while len(selected) < limit and any(groups.values()):
        for key in order:
            if groups[key] and len(selected) < limit:
                selected.append(groups[key].pop())
    return selected


def main() -> None:
    candidate_freeze = load(CANDIDATE_FREEZE)
    v1_freeze = load(V1_FREEZE)
    if candidate_freeze.get("candidate_rule") != RULE_VERSION:
        raise SystemExit("candidate freeze does not match imported KOL-v2 rule")
    if candidate_freeze.get("status") != "frozen_candidate_awaiting_fresh_blind_audit":
        raise SystemExit("KOL-v2 candidate is not frozen for blind audit")
    for path in (RULE_SOURCE, LEXICAL_SPEC):
        expected = candidate_freeze["frozen_files"][relative(path)]["sha256"]
        if sha256_file(path) != expected:
            raise SystemExit(f"frozen KOL-v2 source changed: {path}")
    for path in (DOCUMENTS, MARKETS, EXCLUSIONS):
        expected = v1_freeze["frozen_files"][relative(path)]["sha256"]
        if sha256_file(path) != expected:
            raise SystemExit(f"frozen v1/opened artifact changed: {path}")

    documents = read_jsonl(DOCUMENTS)
    markets = read_jsonl(MARKETS)
    exclusions = read_jsonl(EXCLUSIONS)
    if len(documents) != 2779 or len(markets) != 14 or len(exclusions) != 300:
        raise SystemExit("unexpected frozen source row counts")
    excluded_pairs = {(row["market_id"], row["content_hash"]) for row in exclusions}
    excluded_pair_ids = {row["pair_id"] for row in exclusions}
    opened_kol = [row for row in exclusions if row["source"] == "kol"]
    if len(opened_kol) != 150:
        raise SystemExit("expected exactly 150 opened KOL pairs")

    candidates = []
    all_pair_exclusions_seen = 0
    candidate_exclusions_seen = 0
    for market_row in markets:
        market_id = str(market_row["market_id"])
        venue = str(market_row["venue"])
        market_spec = market_row["spec"]
        category = str(market_spec["category"])
        question = str(market_spec["question"])
        for document in documents:
            pair_id = stable_hash(f"{venue}:{market_id}:kol:{document['doc_id']}")
            excluded = (
                (market_id, document["content_hash"]) in excluded_pairs
                or pair_id in excluded_pair_ids
            )
            if excluded:
                all_pair_exclusions_seen += 1
            retrieval_candidate = is_retrieval_candidate(market_id, document["text"])
            if not retrieval_candidate:
                continue
            if excluded:
                candidate_exclusions_seen += 1
                continue
            rule_prediction, reasons, terms, evidence = prediction(market_id, document["text"])
            candidates.append(
                {
                    "association_rule": RULE_VERSION,
                    "category": category,
                    "content_hash": document["content_hash"],
                    "doc_id": document["doc_id"],
                    "event_ts": document["event_ts"],
                    "evidence": evidence,
                    "market_id": market_id,
                    "market_question": question,
                    "match_reasons": reasons,
                    "match_terms": terms,
                    "outcome_id": market_row["outcome_id"],
                    "pair_id": pair_id,
                    "prediction": rule_prediction,
                    "retrieved_at": document["retrieved_at"],
                    "source": "kol",
                    "venue": venue,
                }
            )
    if all_pair_exclusions_seen != 150:
        raise SystemExit(
            f"opened-pair universe guard found {all_pair_exclusions_seen} KOL pairs, expected 150"
        )
    candidates.sort(key=lambda row: row["pair_id"])

    sample = []
    realized = {}
    for cell_index, rule_prediction in enumerate(("matched", "hard_unmatched")):
        eligible = [row for row in candidates if row["prediction"] == rule_prediction]
        selected = round_robin_sample(
            eligible,
            limit=TARGET_PER_CELL,
            seed=SAMPLE_SEED + cell_index,
        )
        sample.extend(selected)
        realized[rule_prediction] = len(selected)
    if realized != {"matched": TARGET_PER_CELL, "hard_unmatched": TARGET_PER_CELL}:
        raise SystemExit(f"fresh KOL audit cell shortfall: {realized}")
    random.Random(SAMPLE_SEED + 101).shuffle(sample)

    document_lookup = {row["doc_id"]: row for row in documents}
    blind = []
    key = []
    for pair in sample:
        if (
            (pair["market_id"], pair["content_hash"]) in excluded_pairs
            or pair["pair_id"] in excluded_pair_ids
        ):
            raise SystemExit("opened pair leaked into fresh blind sample")
        audit_id = stable_hash(f"v2.1-kol-v2-blind-audit:{pair['pair_id']}")[:16]
        document = document_lookup[pair["doc_id"]]
        blind.append(
            {
                "audit_id": audit_id,
                "category": pair["category"],
                "document_event_ts": pair["event_ts"],
                "document_metadata": document["metadata"],
                "document_source": "kol",
                "document_text": document["text"],
                "market_question": pair["market_question"],
                "review_confidence": "",
                "review_label": "",
                "review_rationale": "",
                "reviewer": "",
                "venue": pair["venue"],
            }
        )
        key.append(
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
                "source": "kol",
                "venue": pair["venue"],
            }
        )

    paths = {
        "candidate_pool": OUTPUT_ROOT / "kol_v2_candidate_pool.jsonl",
        "blind_key": OUTPUT_ROOT / "kol_v2_blind_key.jsonl",
        "blind_review": BLIND_RELEASE,
    }
    write_once(paths["candidate_pool"], jsonl_bytes(candidates))
    write_once(paths["blind_key"], jsonl_bytes(key))
    write_once(paths["blind_review"], jsonl_bytes(blind))

    report = {
        "association_rule": RULE_VERSION,
        "candidate_pairs": len(candidates),
        "candidate_pairs_by_prediction": dict(
            sorted(Counter(row["prediction"] for row in candidates).items())
        ),
        "exclusion_policy": ["market_id+content_hash", "pair_id"],
        "fresh_unopened_pairs": True,
        "input_hashes": {
            relative(path): sha256_file(path)
            for path in (CANDIDATE_FREEZE, V1_FREEZE, RULE_SOURCE, LEXICAL_SPEC, DOCUMENTS, MARKETS, EXCLUSIONS)
        },
        "label_blind": True,
        "labels_read": [],
        "opened_candidate_pairs_excluded": candidate_exclusions_seen,
        "opened_kol_pairs_in_universe": all_pair_exclusions_seen,
        "outputs": {
            name: {"path": relative(path), "sha256": sha256_file(path)}
            for name, path in paths.items()
        },
        "predictions_hidden": True,
        "protocol_id": candidate_freeze["protocol_id"],
        "realized_sample_cells": realized,
        "sample_categories": dict(sorted(Counter(row["category"] for row in sample).items())),
        "sample_markets": dict(sorted(Counter(row["market_id"] for row in sample).items())),
        "sample_rows": len(sample),
        "sample_seed": SAMPLE_SEED,
        "source_documents": len(documents),
        "status": "awaiting_independent_blind_review",
        "target_per_cell": TARGET_PER_CELL,
    }
    report_path = OUTPUT_ROOT / "kol_v2_audit_preparation_report.json"
    write_once(report_path, (json.dumps(report, indent=2, sort_keys=True) + "\n").encode())
    print(json.dumps(report, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
