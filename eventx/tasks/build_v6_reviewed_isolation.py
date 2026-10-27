"""Version reviewed isolation graph and exclusion preview, without certifying it."""
import hashlib
import json
from pathlib import Path
import tempfile
from eventx.tasks.certify_v5_family_graph import components, validate_split_certificate
from eventx.tasks.validate_v6_boundary_submissions import read, sha, write


def main():
    out = Path("data/v6/reviewed_isolation_20260916")
    if out.exists():
        raise FileExistsError(out)
    base = Path("data/v5/reviewed_pair_graph_20260915")
    confirmation = Path("data/v6/confirmation_validation_20260916")
    user = Path("data/v6/boundary_confirmation_20260916")
    inputs = {}
    for directory in (base, confirmation, user):
        mp = directory / "manifest.json"
        m = json.loads(mp.read_text())
        assert all(sha(directory / n) == h for n, h in m["outputs"].items())
        inputs[str(mp)] = sha(mp)
    report = json.loads((confirmation / "report.json").read_text())
    assert all(r["structural_validation_pass"] for r in report["validation"].values())
    def load(path):
        inputs[str(path)] = sha(path)
        return read(path)
    old = json.loads((base / "candidate_components.json").read_text())
    fid = lambda c: "family-" + hashlib.sha256("|".join(sorted(c)).encode()).hexdigest()[:16]
    groups = {fid(c): c for c in old}
    reviewed = load(confirmation / "family_submission_snapshot.jsonl")
    adjudications = load(user / "user_adjudications.jsonl")
    evidence = [{"review_id": r["review_id"], "left": r["development_group"],
                 "right": r["reserved_group"], "basis": "two_submitted_agreeing_reviews"}
                for r in reviewed if r["decision"] == "must_link"]
    evidence += [{"review_id": r["review_id"], "left": r["development_group"],
                  "right": r["reserved_group"], "basis": "user_evidence_visible_adjudication"}
                 for r in adjudications if r["adjudication_decision"] == "must_link"]
    assert len(evidence) == 51
    edges = [(r["left"], r["right"]) for r in evidence]
    grouped = components(groups, edges)
    graph = sorted(sorted(n for g in block for n in groups[g]) for block in grouped)
    node_map = {n: fid(c) for c in graph for n in c}
    crosswalk = {g: node_map[c[0]] for g, c in groups.items()}
    assert all(len({node_map[n] for n in c}) == 1 for c in old)
    validate_split_certificate(groups, edges, crosswalk, {g: False for g in groups})
    for a, b in edges:
        bad = dict(crosswalk)
        bad[b] = "deliberately-separated"
        try:
            validate_split_certificate(groups, edges, bad, {g: False for g in groups})
        except ValueError:
            pass
        else:
            raise AssertionError("Known link split accepted")
    markets = load(base / "market_family_mapping.jsonl")
    mapped = [dict(r, family_id=node_map[r["event_id"]], family_certified=False) for r in markets]
    stories = load(confirmation / "story_submission_snapshot.jsonl")
    comparisons = {r["review_id"]: r for r in load(confirmation / "comparisons.jsonl")}
    story_edges = [{"review_id": r["review_id"],
                    "development_article_id": r["development_article"]["article_id"],
                    "reserved_article_id": r["reserved_article"]["article_id"],
                    "split_constraint": "must_coisolate",
                    "subtype_labels": [comparisons[r["review_id"]]["first_decision"], r["decision"]],
                    "subtype_adjudicated": comparisons[r["review_id"]]["exact_agreement"]}
                   for r in stories]
    development = load(Path("data/v6/hybrid_development_reviews_20260916/packet.jsonl"))
    reserved = load(Path("data/v6/hybrid_audit_20260916/reserved_review_packet.jsonl"))
    dev_groups = {crosswalk[r["contract"]["provisional_split_group"]] for r in development}
    prior = {r["pair_id"] for r in load(user / "risk_preview_NOT_ADMITTED.jsonl")}
    story_risks = {r["reserved_article_id"] for r in story_edges}
    series = next(r for r in adjudications if r["review_id"] == "boundary-42902e38c11c50ae")
    constraints = [{"review_id": series["review_id"], "left": series["development_group"],
                    "right": series["reserved_group"], "constraint": "retain_cross_split_quarantine",
                    "semantic_merge": False, "cohort_wide_series_policy_frozen": False}]
    excluded, remaining = [], []
    for row in reserved:
        new_group = crosswalk[row["contract"]["provisional_split_group"]]
        reasons = []
        if row["pair_id"] in prior:
            reasons.append("prior_risk_retained")
        if new_group in dev_groups:
            reasons.append("reviewed_transitive_family_overlap")
        if row["article"]["article_id"] in story_risks:
            reasons.append("confirmed_story_overlap")
        if reasons:
            excluded.append({"pair_id": row["pair_id"], "new_family_id": new_group, "reasons": reasons})
        else:
            remaining.append({"pair_id": row["pair_id"], "new_family_id": new_group,
                              "admitted": False, "certified": False})
    assert prior <= {r["pair_id"] for r in excluded}
    assert not ({r["new_family_id"] for r in remaining} & dev_groups)
    summary = {"prior_components": len(old), "new_provisional_components": len(graph),
               "reviewed_edges": len(evidence), "two_review_edges": 40, "user_adjudicated_edges": 11,
               "split_rejection_tests_passed": len(edges), "markets_mapped": len(mapped),
               "story_isolation_edges": len(story_edges), "original_reserved_pairs": len(reserved),
               "excluded_preview_pairs": len(excluded), "remaining_NOT_ADMITTED": len(remaining),
               "additional_exclusions": len(excluded) - len(prior),
               "remaining_known_family_overlap": 0, "prior_components_preserved": True,
               "final_certification": False, "original_sampling_modified": False,
               "series_policy_frozen": False, "outcomes_accessed": False}
    stage = Path(tempfile.mkdtemp(prefix=".reviewed-isolation-", dir=out.parent))
    for name, obj in (("candidate_components.json", graph), ("old_to_new_family_ids.json", crosswalk),
                      ("report.json", summary)):
        (stage / name).write_text(json.dumps(obj, indent=2) + "\n")
    for name, rows in (("market_family_mapping", mapped), ("reviewed_edges", evidence),
                       ("story_isolation", story_edges), ("series_restrictions", constraints),
                       ("exclusion_overlay", excluded), ("remaining_NOT_ADMITTED", remaining),
                       ("unresolved_boundaries", [r for r in adjudications if r["adjudication_decision"] == "unresolved"])):
        write(stage / (name + ".jsonl"), rows)
    (stage / "manifest.json").write_text(json.dumps({"inputs": inputs,
        "code_sha256": sha(Path(__file__)), "outputs": {p.name: sha(p) for p in stage.iterdir()}}, indent=2) + "\n")
    stage.rename(out)
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
