"""Preserve submitted adjudications without fabricating evidence or final evaluation."""
import json
from collections import Counter
from pathlib import Path
from eventx.tasks.validate_v6_boundary_submissions import read, sha


def main():
    base = Path("data/v6/bounded_submission_validation_20260917")
    source = base / "adjudication_packet_completed_no_unresolved.jsonl"
    out = Path("data/v6/bounded_adjudication_receipt_20260917")
    if out.exists():
        raise FileExistsError(out)
    m = json.loads((base / "manifest.json").read_text())
    assert all(sha(base / n) == h for n, h in m["outputs"].items())
    original = {r["review_id"]: r for r in read(base / "adjudication_packet.jsonl")}
    rows = read(source)
    errors = []
    if len(rows) != len(original) or {r.get("review_id") for r in rows} != set(original):
        errors.append("ID count/set mismatch")
    allowed = {"family": {"must_link", "no_direct_link_established", "unresolved"},
               "story": {"same_story", "related_update", "distinct_story", "unresolved"}}
    for r in rows:
        key = r.get("review_id")
        if key not in original:
            continue
        old = original[key]
        for field in ("kind", "first_review", "second_review", "max_attempts"):
            if r.get(field) != old[field]:
                errors.append(f"{key}: changed {field}")
        for field in ("adjudicator", "rationale"):
            if not isinstance(r.get(field), str) or not r[field].strip():
                errors.append(f"{key}: missing {field}")
        if r.get("adjudication_decision") not in allowed[old["kind"]]:
            errors.append(f"{key}: invalid decision")
    counts = {kind: dict(Counter(r.get("adjudication_decision") for r in rows if r.get("kind") == kind))
              for kind in allowed}
    report = {"rows": len(rows), "structural_errors": errors,
        "submitted_decisions": counts,
        "empty_evidence_refs": [r["review_id"] for r in rows if not r.get("evidence_refs")],
        "evidence_sufficiency_certified": False,
        "specific_evidence_concern": "boundary-881c4d6f8e86e1ba requires an explicit settlement-rule link; broad major-policy relevance alone does not prove a leg dependency",
        "status": "submission_recorded_not_final_audit", "adjudication_rounds_received": 1,
        "formal_audit_evaluated": False, "graph_changed": False, "resampled": False,
        "outcomes_accessed": False}
    out.mkdir()
    (out / "submission_snapshot.jsonl").write_bytes(source.read_bytes())
    (out / "report.json").write_text(json.dumps(report, indent=2) + "\n")
    (out / "manifest.json").write_text(json.dumps({"inputs": {
        str(source): sha(source), str(base / "manifest.json"): sha(base / "manifest.json")},
        "code_sha256": sha(Path(__file__)), "outputs": {p.name: sha(p) for p in out.iterdir()}}, indent=2) + "\n")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
