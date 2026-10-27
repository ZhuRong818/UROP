"""Build retrospective cards and an UNLABELLED development-only retrieval pilot.

Only metadata and allowlisted opened-discovery news are read. No price/label inputs.
This is not the proposed event/story-disjoint held-out association audit.
"""
from collections import Counter
from datetime import datetime, timezone
import argparse
import hashlib
import json
from pathlib import Path
import random
import tempfile

from eventx.v6.contracts import canonical_id, review_text, utc
from eventx.v6.retrieval import BM25

ROOT = Path(__file__).resolve().parents[2]
PATHS = {
    "metadata": "data/v5/source_readiness_20260908/metadata_staging.jsonl",
    "topics": "data/v5/topic_coverage_triage_20260914/topic_review_queue.jsonl",
    "memberships": "data/v5/embedded_membership_recovery_20260910/candidate_memberships.jsonl",
    "families": "data/v5/reviewed_pair_graph_20260915/market_family_mapping.jsonl",
    "parents": "data/v5/rich_leg_recovery_20260915/parent_metadata.jsonl",
    "legs": "data/v5/rich_leg_recovery_20260915/leg_references.jsonl",
    "rules": "data/v5/provenance_recovery_20260908/reassessment_20260915_recovered_rule_text.jsonl",
    "news_index": "data/v5/source_readiness_20260908/news_provenance_staging.jsonl",
    "news": "data/v3_historical/primary/label_blind_inputs/news.jsonl",
}
SEED = 20260916


def digest(path):
    with path.open("rb") as f:
        return hashlib.file_digest(f, "sha256").hexdigest()


def rows(name):
    with (ROOT / PATHS[name]).open() as f:
        for line, text in enumerate(f, 1):
            yield line, json.loads(text)


def write_json(path, value):
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n")


def write_rows(path, values):
    with path.open("w") as f:
        for value in values:
            f.write(json.dumps(value, sort_keys=True) + "\n")


def build(output):
    if output.exists():
        raise FileExistsError("Use a new version; never overwrite a release")
    # Verify the proposal, recovered rules and frozen reassessment before reuse.
    old_manifest = ROOT / "data/v5/design_reassessment_20260915/manifest.json"
    old = json.loads(old_manifest.read_text())
    for section in ("inputs", "outputs"):
        for path, expected in old[section].items():
            if digest(ROOT / path) != expected:
                raise ValueError(f"Prior artifact changed: {path}")
    inputs = {path: digest(ROOT / path) for path in PATHS.values()}
    topics = {(r["venue"], r["market_id"]): (line, r) for line, r in rows("topics")}
    memberships = {r["condition_id"]: (line, r) for line, r in rows("memberships")}
    families = {r["market_id"]: r for _, r in rows("families")}
    parents = {r["ticker"] for _, r in rows("parents")}
    rules = {r["ticker"]: (line, r) for line, r in rows("rules")}
    cards = []
    for line, meta in rows("metadata"):
        venue, market = meta["venue"], meta["market_id"]
        topic_line, topic = topics[(venue, market)]
        events, titles, subtitles, evidence = [], [], [], []
        source_event = meta["candidate_family"].get("source_event_id")
        if source_event:
            events.append(canonical_id(venue, "event", source_event))
        if topic.get("yes_sub_title"):
            subtitles.append(topic["yes_sub_title"])
        if venue == "polymarket" and market in memberships:
            member_line, member = memberships[market]
            events += [canonical_id(venue, "event", x) for x in member["candidate_event_ids"]]
            for e in member["evidence"]:
                titles += [e["event_title"]] if e.get("event_title") else []
                subtitles += [e["contract_subtitle"]] if e.get("contract_subtitle") else []
            evidence.append({"path": PATHS["memberships"], "line": member_line})
        rule_evidence = []
        if venue == "kalshi" and market in rules:
            rule_line, rule = rules[market]
            for field in ("rules_primary", "rules_secondary"):
                if rule.get(field):
                    rule_evidence.append({"text": rule[field], "field": field,
                        "source_ingest_ts": rule["ingest_ts"],
                        "historical_availability_verified": False,
                        "path": PATHS["rules"], "line": rule_line})
        unique_subtitles = sorted(set(subtitles))
        cards.append({"schema_version": "v6-contract-card-0.1",
            "contract_id": canonical_id(venue, "contract", market), "venue": venue,
            "market_id": market, "question": meta["question"],
            "yes_subtitle": unique_subtitles[0] if len(unique_subtitles) == 1 else None,
            "subtitle_candidates": unique_subtitles,
            "subtitle_conflict": len(unique_subtitles) > 1,
            "event_ids": sorted(set(events)), "event_titles": sorted(set(titles)),
            "provisional_split_group": families[market]["family_id"],
            "family_certified": False,
            "scope": "combo_extension" if venue == "kalshi" and market in parents
                     else "single_event_candidate_unverified",
            "rule_evidence": rule_evidence, "terminal_fields": meta["terminal_fields"],
            "semantic_fields": {k: None for k in ("entities", "event_type", "location",
                "event_date", "stage", "metric", "comparator", "threshold", "unit", "resolution_source")},
            "token_mapping": None, "pit_certificate": None, "training_admissible": False,
            "topic": topic.get("suggested_topic"), "topic_certified": False,
            "source_ingest_ts": meta["source_ingest_ts"],
            "evidence": [{"path": PATHS["metadata"], "line": line},
                         {"path": PATHS["topics"], "line": topic_line}, *evidence]})
    cards.sort(key=lambda c: c["contract_id"])
    if len({c["contract_id"] for c in cards}) != len(cards):
        raise ValueError("Duplicate contract cards; explicit version reconciliation required")
    edges = []
    for line, leg in rows("legs"):
        edges.append({"type": "explicit_parent_leg", "direction": "parent_to_leg",
            "parent_event_id": canonical_id("kalshi", "event", leg["parent_event_id"]),
            "leg_event_id": canonical_id("kalshi", "event", leg["event_ticker"]),
            "parent_contract_id": canonical_id("kalshi", "contract", leg["parent_market_id"]),
            "leg_contract_id": canonical_id("kalshi", "contract", leg["market_ticker"]),
            "side": leg["side"], "leg_index": leg["leg_index"],
            "historical_semantics_certified": False,
            "evidence": {"path": PATHS["legs"], "line": line}})
    index = [r for _, r in rows("news_index") if r["clock_consistent"]]
    if len({r["article_id"] for r in index}) != len(index):
        raise ValueError("Duplicate article IDs need version resolution")
    rng = random.Random(SEED)
    chosen = rng.sample(sorted(index, key=lambda r: r["article_id"]), 200)
    selected = {r["source_line"]: r for r in chosen}
    articles = []
    # Read only selected lines into JSON/text; index was restricted to opened history.
    with (ROOT / PATHS["news"]).open() as f:
        for line, text in enumerate(f, 1):
            if line not in selected:
                continue
            row, proof = json.loads(text), selected[line]
            if str(row["id"]) != proof["article_id"]:
                raise ValueError("Article identity/line mismatch")
            content = {k: row.get(k) for k in ("headline", "summary")}
            actual = hashlib.sha256(json.dumps(content, sort_keys=True).encode()).hexdigest()
            if actual != proof["content_sha256"]:
                raise ValueError("Article text hash changed")
            clock = utc(proof["source_clock_available_at"])
            if not utc("2026-05-17T00:00:00Z") <= clock < utc("2026-07-22T00:00:00Z"):
                raise ValueError("Article outside opened discovery")
            articles.append({"article_id": proof["article_id"], **content,
                "published_at": row["published_at"], "source_clock_available_at": clock.isoformat(),
                "publisher": row.get("publisher"), "source_run_id": row.get("source_run_id"),
                "content_sha256": actual, "source_line": line,
                "historical_admission": "pending_revision_field_and_export_reconciliation"})
    if len(articles) != len(chosen):
        raise ValueError("Missing selected article")
    candidates = [c for c in cards if c["scope"] == "single_event_candidate_unverified"]
    engine = BM25([review_text(c) for c in candidates])
    pool, ledger, packet = [], [], []
    article_probability = len(chosen) / len(index)
    for article in sorted(articles, key=lambda a: a["article_id"]):
        text = "\n".join(article[k] or "" for k in ("headline", "summary"))
        hits = engine.search(text, 50)
        for rank, (i, score) in enumerate(hits, 1):
            pool.append({"article_id": article["article_id"],
                "contract_id": candidates[i]["contract_id"], "rank": rank, "bm25": score})
        retrieved = {i for i, _ in hits}
        outside = [i for i in range(len(candidates)) if i not in retrieved]
        selections = [(i, "top5", 1.0) for i, _ in hits[:5]]
        if outside:
            selections.append((rng.choice(outside), "uniform_outside_top50", 1 / len(outside)))
        for i, stratum, conditional_probability in selections:
            card = candidates[i]
            pair_id = hashlib.sha256((article["article_id"] + "|" + card["contract_id"]).encode()).hexdigest()[:24]
            ledger.append({"pair_id": pair_id, "stratum": stratum,
                "article_selection_probability": article_probability,
                "conditional_pair_probability": conditional_probability,
                "pair_inclusion_probability": article_probability * conditional_probability,
                "outside_pool_size": len(outside), "split": "development_pilot_only"})
            packet.append({"pair_id": pair_id, "article": article, "contract": card,
                "labels": {"relevance": None, "outcome_applicability": None,
                    "evidence_spans": [], "identity_problem": None}, "reviewer_id": None})
    # Hide retrieval order/channel from reviewer packet, retain auditable selection ledger.
    rng.shuffle(packet)
    output.parent.mkdir(parents=True, exist_ok=True)
    stage = Path(tempfile.mkdtemp(prefix=".v6-stage-", dir=output.parent))
    for name, records in (("contract_cards", cards), ("explicit_dependency_edges", edges),
                          ("articles", articles), ("retrieval_pool", pool),
                          ("selection_ledger", ledger), ("development_review_packet", packet)):
        write_rows(stage / f"{name}.jsonl", records)
    report = {"status": "development_annotation_pilot_not_predictive_or_heldout",
        "contract_cards": len(cards), "scope_counts": dict(Counter(c["scope"] for c in cards)),
        "cards_with_rule_text": sum(bool(c["rule_evidence"]) for c in cards),
        "cards_with_named_subtitle": sum(bool(c["yes_subtitle"]) for c in cards),
        "subtitle_conflicts": sum(c["subtitle_conflict"] for c in cards),
        "explicit_leg_edges": len(edges), "article_population": len(index),
        "articles_sampled": len(articles), "top50_pool_pairs": len(pool),
        "review_pairs": len(packet), "human_labels": 0, "admitted_predictive_contracts": 0,
        "forecast_fits": 0, "protected_outcomes_accessed": False,
        "dense_encoder_implemented": False, "crossencoder_implemented": False,
        "heldout_audit_prepared": False, "seed": SEED,
        "limits": ["No active-status filter: contract validity not certified; review-only corpus",
            "Review uses retrospective rule evidence, never admitted historical features",
            "Development-only: event/story disjoint heldout audit still required",
            "Sampling probabilities do not make this enriched sample population precision",
            "No family graph merges or semantic auto-certification"]}
    write_json(stage / "report.json", report)
    manifest = {"created_at": datetime.now(timezone.utc).isoformat(), "inputs": inputs,
        "prior_manifest_sha256": digest(old_manifest),
        "code": {str(p.relative_to(ROOT)): digest(p) for p in
                 [Path(__file__).resolve(), *sorted((ROOT / "eventx/v6").glob("*.py"))]},
        "outputs": {p.name: digest(p) for p in sorted(stage.iterdir())},
        "research_freeze": False}
    write_json(stage / "manifest.json", manifest)
    stage.rename(output)
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=ROOT / "data/v6/contract_link_pilot_20260916")
    build(parser.parse_args().output.resolve())
