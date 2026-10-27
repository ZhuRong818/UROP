"""Package pending reviews and user decisions; never adopt or certify splits."""
from collections import Counter
import hashlib
import json
from pathlib import Path
import tempfile


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read(path):
    return [json.loads(line) for line in path.read_text().splitlines()]


def main():
    root = Path("data/v6")
    out = root / "boundary_confirmation_20260916"
    if out.exists():
        raise FileExistsError(out)
    enriched = root / "boundary_adjudication_enriched_20260916"
    manifest = json.loads((enriched / "manifest.json").read_text())
    for name, digest in manifest["outputs"].items():
        assert sha(enriched / name) == digest, name
    packet_path = enriched / "adjudication_packet.jsonl"
    receipt = Path("eventx/release/v6/USER_BOUNDARY_ADJUDICATION_20260916.md")
    tasks = read(packet_path)
    decisions = {}
    for line in receipt.read_text().splitlines():
        if line.startswith("| boundary-"):
            _, key, decision, rationale, _ = line.split("|")
            assert key.strip() not in decisions
            decisions[key.strip()] = (decision.strip(), rationale.strip())
    expected = {t["review_id"] for t in tasks
                if t["kind"] == "family" and t["submitted_review"]["decision"] == "unresolved"}
    assert set(decisions) == expected and len(expected) == 15
    assert Counter(d[0] for d in decisions.values()) == {
        "must_link": 11, "no_direct_link_established": 2, "unresolved": 2}
    original_dir = root / "boundary_audit_20260916"
    originals = {}
    original_manifest = json.loads((original_dir / "manifest.json").read_text())
    inputs = {str(packet_path): sha(packet_path), str(receipt): sha(receipt)}
    for kind in ("family", "story"):
        path = original_dir / f"{kind}_review_packet.jsonl"
        assert sha(path) == original_manifest["outputs"][path.name]
        originals[kind] = {r["review_id"]: r for r in read(path)}
        inputs[str(path)] = sha(path)
    pending = {"family": [], "story": []}
    recorded = []
    for task in tasks:
        key = task["review_id"]
        if key not in decisions:
            row = originals[task["kind"]][key]
            assert all(row.get(k) is None for k in ("decision", "reviewer", "rationale"))
            pending[task["kind"]].append(row)
        else:
            decision, rationale = decisions[key]
            recorded.append({
                "review_id": key, "adjudicator": "user_conversation_20260916",
                "adjudication_decision": decision, "rationale": rationale,
                "rationale_is_summary": True, "not_blind_second_review": True,
                "evidence_refs": [f"{packet_path}#{key}", str(receipt)],
                "development_group": task["submitted_review"]["development_group"],
                "reserved_group": task["submitted_review"]["reserved_group"],
                "adopted": False, "certified": False,
            })
    assert len(pending["family"]) == 40 and len(pending["story"]) == 2
    # Retain all earlier conservative flags; negative adjudications cannot release rows.
    risk_path = root / "boundary_submission_validation_20260916/risk_preview.jsonl"
    reserved_path = root / "hybrid_audit_20260916/reserved_review_packet.jsonl"
    inputs.update({str(p): sha(p) for p in (risk_path, reserved_path)})
    reserved = read(reserved_path)
    prior_risks = {r["pair_id"] for r in read(risk_path)}
    assert prior_risks <= {r["pair_id"] for r in reserved}
    linked_groups = {r["reserved_group"] for r in recorded if r["adjudication_decision"] == "must_link"}
    unresolved_groups = {r["reserved_group"] for r in recorded if r["adjudication_decision"] == "unresolved"}
    series = next(r for r in recorded if r["review_id"] == "boundary-42902e38c11c50ae")
    risk_rows = []
    for row in reserved:
        reasons = []
        group = row["contract"]["provisional_split_group"]
        if row["pair_id"] in prior_risks:
            reasons.append("prior_conservative_risk_retained")
        if group in linked_groups:
            reasons.append("user_must_link_to_development_pending_adoption")
        if group in unresolved_groups:
            reasons.append("unresolved_rule_boundary")
        if group == series["reserved_group"]:
            reasons.append("adjacent_series_split_policy_pending")
        if reasons:
            risk_rows.append({"pair_id": row["pair_id"], "reasons": reasons})
    assert prior_risks <= {r["pair_id"] for r in risk_rows}
    report = {
        "user_decisions": dict(Counter(r["adjudication_decision"] for r in recorded)),
        "pending_family_confirmations": len(pending["family"]),
        "pending_story_confirmations": len(pending["story"]),
        "original_reserved_pairs": len(reserved), "risk_preview_pairs": len(risk_rows),
        "unflagged_preview_pairs_NOT_ADMITTED": len(reserved) - len(risk_rows),
        "user_must_link_reserved_groups": len(linked_groups),
        "pairs_in_user_must_link_groups": sum(r["contract"]["provisional_split_group"] in linked_groups for r in reserved),
        "quarantined_rows_released": 0, "graph_changed": False,
        "certified": False, "independent_reviews_generated": False,
        "outcomes_accessed": False,
    }
    stage = Path(tempfile.mkdtemp(prefix=".boundary-confirmation-", dir=root))
    def write(name, rows):
        (stage / name).write_text("".join(json.dumps(r, sort_keys=True) + "\n" for r in rows))
    for kind, rows in pending.items():
        write(f"{kind}_confirmation_packet.jsonl", rows)
    write("user_adjudications.jsonl", recorded)
    write("risk_preview_NOT_ADMITTED.jsonl", risk_rows)
    (stage / "report.json").write_text(json.dumps(report, indent=2) + "\n")
    (stage / "manifest.json").write_text(json.dumps({
        "inputs": inputs, "code_sha256": sha(Path(__file__)),
        "outputs": {p.name: sha(p) for p in stage.iterdir()},
    }, indent=2) + "\n")
    stage.rename(out)
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
