"""Record current submission format and user-attested independence without adoption."""
import hashlib
import json
from pathlib import Path
from collections import Counter
from eventx.tasks.validate_v6_boundary_submissions import validate

def main():
    base=Path("data/v6/boundary_audit_20260916")
    out=Path("data/v6/boundary_format_recheck_20260916")
    if out.exists():raise FileExistsError(out)
    read=lambda p:[json.loads(x) for x in p.open()]
    sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
    old=json.loads(Path("data/v6/boundary_submission_validation_20260916/manifest.json").read_text())
    frozen=json.loads((base/"manifest.json").read_text())
    report={"user_attestation":"User states both files are independent reviewer reviews; accepted as user attestation, not independently verified",
        "second_review_per_pair_established":False,"certification":False,"files":{}}
    for kind in ("family","story"):
        p=base/f"{kind}_review_packet.jsonl"
        q=base/f"{kind}_review_packet_reviewed_20260916.jsonl"
        original=read(p)
        assert sha(p)==frozen["outputs"][p.name]
        rr=read(q) if q.exists() else []
        report["files"][kind]={"template_path":str(p),"template_rows":len(original),
            "template_blank_rows":sum(r["decision"] is None and r["reviewer"] is None for r in original),
            "submission_path":str(q),"submission_exists":q.exists(),
            "prior_submission_sha256":old["inputs"].get(str(q)),
            "current_submission_sha256":sha(q) if q.exists() else None,
            "reviewers":dict(Counter(r.get("reviewer") for r in rr)),
            "decisions":dict(Counter(r.get("decision") for r in rr)),
            "validation_errors":validate(original,rr,kind) if q.exists() else ["missing_submission"]}
    out.mkdir()
    story=base/"story_review_packet_reviewed_20260916.jsonl"
    (out/"story_submission_snapshot.jsonl").write_bytes(story.read_bytes())
    (out/"report.json").write_text(json.dumps(report,indent=2)+"\n")
    (out/"manifest.json").write_text(json.dumps({"code_sha256":sha(Path(__file__)),
        "outputs":{p.name:sha(p) for p in out.iterdir()}},indent=2)+"\n")
    print(json.dumps(report,indent=2))

if __name__=="__main__":main()
