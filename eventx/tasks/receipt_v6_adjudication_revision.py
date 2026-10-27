"""Record citation revision and decision changes without adopting a second round."""
import json
from pathlib import Path
from eventx.tasks.validate_v6_boundary_submissions import read, sha


def main():
    source = Path("data/v6/bounded_submission_validation_20260917/adjudication_packet_completed_with_evidence_refs.jsonl")
    prior = Path("data/v6/bounded_adjudication_receipt_20260917/submission_snapshot.jsonl")
    out = Path("data/v6/bounded_adjudication_revision_20260917")
    if out.exists():
        raise FileExistsError(out)
    old = {r["review_id"]: r for r in read(prior)}
    rows = read(source)
    assert len(rows) == 8 and {r["review_id"] for r in rows} == set(old)
    changes, checks = [], []
    for r in rows:
        o = old[r["review_id"]]
        assert all(r[k] == o[k] for k in ("kind", "first_review", "second_review"))
        assert r["evidence_refs"]
        if r["adjudication_decision"] != o["adjudication_decision"]:
            changes.append({"review_id": r["review_id"], "before": o["adjudication_decision"],
                            "after": r["adjudication_decision"]})
        embedded = json.dumps([r["first_review"], r["second_review"]])
        for ref in r["evidence_refs"]:
            if "#L" in ref:
                name, line = ref.rsplit("#L", 1)
                path = Path(name)
                n = int(line)
                # Existence only; do not read unrelated source values or outcomes.
                count = sum(1 for _ in path.open()) if path.is_file() else 0
                ok = 1 <= n <= count
                scope = "file_and_line_exist_not_semantic_verification"
            elif ref.startswith("content_sha256:"):
                ok = ref.split(":", 1)[1] in embedded
                scope = "hash_matches_embedded_evidence"
            elif ref.startswith("article:"):
                identity, line = ref[len("article:"):].split("#source_line=")
                ok = any(v.get("article_id") == identity and str(v.get("source_line")) == line
                         for review in (r["first_review"], r["second_review"])
                         for v in (review.get("development_article", {}), review.get("reserved_article", {})))
                scope = "article_id_and_line_match_embedded_evidence"
            else:
                ok = ref in embedded
                scope = "identifier_present_in_embedded_evidence"
            checks.append({"review_id": r["review_id"], "reference": ref, "pass": ok, "scope": scope})
    report = {"rows": len(rows), "ids_and_embedded_evidence_unchanged": True,
              "decision_changes": changes, "reference_checks": checks,
              "status": "NOT_ADOPTED_PROTOCOL_CLARIFICATION_REQUIRED",
              "semantic_support_certified": False, "first_adjudication_preserved": True,
              "formal_audit_evaluated": False, "graph_changed": False}
    out.mkdir()
    (out / "submission_snapshot.jsonl").write_bytes(source.read_bytes())
    (out / "report.json").write_text(json.dumps(report, indent=2) + "\n")
    (out / "manifest.json").write_text(json.dumps({"inputs": {str(source): sha(source), str(prior): sha(prior)},
        "code_sha256": sha(Path(__file__)), "outputs": {p.name: sha(p) for p in out.iterdir()}}, indent=2) + "\n")
    print(json.dumps({"rows":len(rows), "changed_decisions": len(changes),
        "references": len(checks), "failed_reference_checks": sum(not c["pass"] for c in checks),
        "adopted": False}))


if __name__ == "__main__":
    main()
