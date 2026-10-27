"""Preserve and validate restored submissions; do not alter prior review history."""
from collections import Counter
import hashlib
import json
from pathlib import Path
from eventx.tasks.validate_v6_boundary_submissions import validate

def main():
    base=Path("data/v6/boundary_audit_20260916")
    prior=Path("data/v6/boundary_submission_validation_20260916")
    out=Path("data/v6/boundary_restored_submission_20260916")
    if out.exists():raise FileExistsError(out)
    read=lambda p:[json.loads(x) for x in p.open()]
    sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
    manifest=json.loads((prior/"manifest.json").read_text())
    report={"reviewer_independence":"user_attested_previously",
            "second_review_per_pair_established":False,"certified":False,"files":{}}
    snapshots={}
    for kind in ("family","story"):
        original=prior/f"{kind}_second_review_packet.jsonl"
        assert sha(original)==manifest["outputs"][original.name]
        p=base/f"{kind}_review_packet_reviewed_20260916.jsonl"
        rows=read(p)
        errors=validate(read(original),rows,kind)
        report["files"][kind]={"path":str(p),"sha256":sha(p),"rows":len(rows),
            "decisions":dict(Counter(r["decision"] for r in rows)),
            "reviewers":dict(Counter(r["reviewer"] for r in rows)),"errors":errors,
            "matches_first_submission_hash":sha(p)==manifest["inputs"].get(str(p))}
        snapshots[kind]=p.read_bytes()
    out.mkdir()
    for kind,raw in snapshots.items():(out/f"{kind}_submission_snapshot.jsonl").write_bytes(raw)
    (out/"report.json").write_text(json.dumps(report,indent=2)+"\n")
    (out/"manifest.json").write_text(json.dumps({"code_sha256":sha(Path(__file__)),
        "outputs":{p.name:sha(p) for p in out.iterdir()}},indent=2)+"\n")
    print(json.dumps(report,indent=2))

if __name__=="__main__":main()
