"""Receipt targeted confirmation submissions without changing graph or splits."""
from collections import Counter
import json
from pathlib import Path
import tempfile

from eventx.tasks.validate_v6_boundary_submissions import read, sha, validate, write


def main():
    base = Path("data/v6/boundary_confirmation_20260916")
    first = Path("data/v6/boundary_restored_submission_20260916")
    out = Path("data/v6/confirmation_validation_20260916")
    if out.exists():
        raise FileExistsError(out)
    for directory in (base, first):
        manifest = json.loads((directory / "manifest.json").read_text())
        assert all(sha(directory / n) == h for n, h in manifest["outputs"].items())
    inputs = {}
    results = {}
    snapshots = {}
    comparisons = []
    for kind, name in (("family", "boundary_reviews_independent.jsonl"),
                       ("story", "story_reviews_independent.jsonl")):
        template = base / f"{kind}_confirmation_packet.jsonl"
        submission = base / name
        previous = first / f"{kind}_submission_snapshot.jsonl"
        for path in (template, submission, previous):
            inputs[str(path)] = sha(path)
        original, rows = read(template), read(submission)
        errors = validate(original, rows, kind)
        snapshots[kind] = submission.read_bytes()
        old = {r["review_id"]: r for r in read(previous)}
        results[kind] = {"rows": len(rows), "errors": errors,
                         "structural_validation_pass": not errors,
                         "decisions": dict(Counter(r.get("decision") for r in rows)),
                         "reviewers": dict(Counter(r.get("reviewer") for r in rows))}
        if errors:
            continue
        for row in rows:
            earlier = old[row["review_id"]]
            a, b = earlier["decision"], row["decision"]
            isolation_agreement = (a == b == "must_link" if kind == "family" else
                                   a in {"same_story", "related_update"} and
                                   b in {"same_story", "related_update"})
            comparisons.append({"kind": kind, "review_id": row["review_id"],
                                "first_decision": a, "second_decision": b,
                                "exact_agreement": a == b,
                                "shared_isolation_agreement": isolation_agreement,
                                "first_rationale": earlier["rationale"],
                                "second_rationale": row["rationale"],
                                "adopted": False})
    report = {"validation": results,
              "exact_agreements": sum(r["exact_agreement"] for r in comparisons),
              "split_isolation_agreements": sum(r["shared_isolation_agreement"] for r in comparisons),
              "comparison_rows": len(comparisons),
              "subtype_disagreements": [r["review_id"] for r in comparisons if not r["exact_agreement"]],
              "review_provenance": "submitted_as_independent; identity_and_blinding_not_independently_verified",
              "whole_boundary_certification": False,
              "graph_or_split_modified": False, "outcomes_accessed": False,
              "scope": "targeted_positive_confirmation_not_representative_accuracy_estimate"}
    stage = Path(tempfile.mkdtemp(prefix=".confirmation-validation-", dir=out.parent))
    for kind, payload in snapshots.items():
        (stage / f"{kind}_submission_snapshot.jsonl").write_bytes(payload)
    write(stage / "comparisons.jsonl", comparisons)
    write(stage / "subtype_disagreements.jsonl", [r for r in comparisons if not r["exact_agreement"]])
    (stage / "report.json").write_text(json.dumps(report, indent=2) + "\n")
    (stage / "manifest.json").write_text(json.dumps({
        "inputs": inputs, "code_sha256": sha(Path(__file__)),
        "outputs": {p.name: sha(p) for p in stage.iterdir()},
    }, indent=2) + "\n")
    stage.rename(out)
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
