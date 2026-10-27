"""Receipt boundary reviews and incomplete relevance templates; no final evaluation."""
import json
from collections import Counter
from pathlib import Path
from eventx.tasks.validate_v6_boundary_submissions import read, sha, validate, write


def main():
    base = Path("data/v6/bounded_audit_20260917")
    out = Path("data/v6/bounded_submission_validation_20260917")
    if out.exists():
        raise FileExistsError(out)
    manifest = json.loads((base / "manifest.json").read_text())
    assert all(sha(base / n) == h for n, h in manifest["outputs"].items())
    inputs = {str(base / "manifest.json"): sha(base / "manifest.json")}
    snapshots, reports, tasks = {}, {}, []
    for kind in ("family", "story"):
        packet = base / f"{kind}_review_packet.jsonl"
        submitted = base / f"{kind}_review_packet_independent_reviewer_1.jsonl"
        prior = Path("data/v6/boundary_restored_submission_20260916") / f"{kind}_submission_snapshot.jsonl"
        for p in (packet, submitted, prior):
            inputs[str(p)] = sha(p)
        rows = read(submitted)
        errors = validate(read(packet), rows, kind)
        old = {r["review_id"]: r for r in read(prior)}
        reports[kind] = {"rows": len(rows), "structural_errors": errors,
                         "decisions": dict(Counter(r["decision"] for r in rows))}
        snapshots[f"{kind}_submission_snapshot.jsonl"] = submitted.read_bytes()
        if not errors:
            for row in rows:
                first = old[row["review_id"]]
                if first["decision"] != row["decision"]:
                    tasks.append({"kind": kind, "review_id": row["review_id"],
                        "first_review": first, "second_review": row,
                        "adjudicator": None, "adjudication_decision": None,
                        "rationale": None, "evidence_refs": [],
                        "adjudication_attempts_used": 0, "max_attempts": 1})
    for label in ("A", "B"):
        path = base / f"relevance_reviewer_{label}_responses.jsonl"
        inputs[str(path)] = sha(path)
        rows = read(path)
        reports[f"relevance_{label}"] = {"rows": len(rows),
            "blank_reviewer_ids": sum(r.get("reviewer_id") is None for r in rows),
            "blank_relevance_labels": sum(r.get("labels", {}).get("relevance") is None for r in rows),
            "status": "INCOMPLETE"}
        snapshots[f"relevance_{label}_submission_snapshot.jsonl"] = path.read_bytes()
    report = {"validation": reports, "adjudication_cases": len(tasks),
              "adjudication_by_kind": dict(Counter(r["kind"] for r in tasks)),
              "status": "awaiting_adjudication_and_relevance_reviews",
              "formal_audit_evaluated": False, "resampled": False,
              "reviewer_independence": "submitted_as_independent_not_independently_verified",
              "outcomes_accessed": False}
    out.mkdir()
    for name, content in snapshots.items():
        (out / name).write_bytes(content)
    write(out / "adjudication_packet.jsonl", tasks)
    (out / "report.json").write_text(json.dumps(report, indent=2) + "\n")
    (out / "manifest.json").write_text(json.dumps({"inputs": inputs,
        "code_sha256": sha(Path(__file__)), "outputs": {p.name: sha(p) for p in out.iterdir()}}, indent=2) + "\n")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
