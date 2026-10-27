"""Review cached contract identities only; never read prices, outcomes or labels.

Produces structural triage plus explicitly scoped semantic merge recommendations.
Neither venue-event IDs nor this review certify final independent event families.
"""

import collections
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
QUEUE = ROOT / "data/v5/source_readiness_20260908/family_review_queue.jsonl"
METADATA = ROOT / "data/v3_historical/feasibility/raw/kalshi_markets/kalshi_markets.jsonl"
OUTPUT = ROOT / "data/v5/family_review_20260909"


def review_group(key, members, metadata):
    flags = ["cross_event_and_cross_venue_review_required"]
    if len({r["question"] for r in members}) < len(members):
        flags.append("repeated_question_requires_contract_subtitle")
    if key.startswith("kalshi:event:KXMVE"):
        flags.append("multi_leg_contract_requires_verified_component_graph")
    if key.startswith("kalshi:event:KXWC"):
        flags.append("world_cup_fixture_and_tournament_dependency_review")
    if key.startswith("kalshi:event:KXPGA"):
        flags.append("golf_tournament_and_season_dependency_review")
    identities = []
    for row in members:
        meta = metadata.get(row["market_id"], {})
        identities.append({"market_id": row["market_id"], "question": row["question"],
                           "yes_sub_title": meta.get("yes_sub_title"),
                           "no_sub_title": meta.get("no_sub_title")})
    return {"candidate_family_id": key, "member_count": len(members),
            "review_type": "all_queue_structural_triage_not_full_semantic_approval",
            "flags": flags, "identities": identities,
            "family_verified": False, "approved_family_id": None}


def main():
    if OUTPUT.exists():
        raise SystemExit("Review output already exists; use a new version, never overwrite")
    rows = [json.loads(line) for line in QUEUE.open()]
    # Cached schema contains contract identities, not market outcomes/prices.
    metadata = {r["ticker"]: {k: r.get(k) for k in
                ("yes_sub_title", "no_sub_title", "event_ticker")}
                for line in METADATA.open() if (r := json.loads(line))}
    groups, unresolved = collections.defaultdict(list), []
    for row in rows:
        if row["candidate_family_id"]:
            groups[row["candidate_family_id"]].append(row)
        else:
            unresolved.append({"market_id": row["market_id"], "venue": row["venue"],
                               "reason": "missing_event_membership", "family_verified": False})
    reviewed = [review_group(key, members, metadata) for key, members in sorted(groups.items())]
    # These two tournament scopes were reviewed from titles and event tickers.
    # They are lower-bound must-link recommendations, NOT exhaustive components.
    merges = []
    for suffix, title in [("THOC26", "The Open Championship"), ("USO26", "U.S. Open")]:
        keys = [k for k in sorted(groups) if k.startswith("kalshi:event:KXPGA")
                and k.endswith("-" + suffix)]
        members = [r for key in keys for r in groups[key]]
        if not members or not all(title in r["question"] for r in members):
            raise ValueError("Tournament title evidence no longer matches reviewed scope")
        merges.append({"scope": f"golf:{suffix}", "candidate_family_ids": keys,
                       "market_ids": [r["market_id"] for r in members],
                       "reason": "Same named tournament: winner, placements, rounds/cut or holes-in-one",
                       "decision": "must_link_for_split_isolation_within_reviewed_scope",
                       "not_a_logical_equivalence_claim": True,
                       "final_family_approved": False,
                       "remaining": "Check season-major and multi-leg bridges and cross-venue equivalents"})
    flags = collections.Counter(flag for group in reviewed for flag in group["flags"])
    report = {"status": "reviewed_not_admitted", "input_markets": len(rows),
              "candidate_groups_reviewed_structurally": len(reviewed),
              "markets_missing_event_membership": len(unresolved),
              "flagged_group_counts": dict(flags), "scoped_merge_recommendations": len(merges),
              "merge_covered_markets": sum(len(m["market_ids"]) for m in merges),
              "approved_families": 0, "new_labels_or_market_outcomes_read": False}
    OUTPUT.mkdir(parents=True)
    for name, records in [("group_triage.jsonl", reviewed), ("missing_membership.jsonl", unresolved)]:
        (OUTPUT / name).write_text("".join(json.dumps(r, sort_keys=True) + "\n" for r in records))
    for name, value in [("scoped_merges.json", merges), ("report.json", report)]:
        (OUTPUT / name).write_text(json.dumps(value, indent=2, sort_keys=True) + "\n")
    paths = [QUEUE, METADATA, Path(__file__), *sorted(OUTPUT.iterdir())]
    manifest = {"status": "label_blind_review_evidence_not_cohort_freeze", "artifacts": [
        {"path": str(p.relative_to(ROOT)), "sha256": hashlib.sha256(p.read_bytes()).hexdigest()}
        for p in paths]}
    (OUTPUT / "manifest.json").write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n")
    print(json.dumps(report, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
