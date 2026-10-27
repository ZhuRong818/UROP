"""Publish an exclusion overlay; never replace or certify the reserved audit."""
import hashlib
import json
from pathlib import Path
import tempfile

def main():
    root=Path("data/v6")
    audit=root/"boundary_audit_20260916"
    reserved=root/"hybrid_audit_20260916/reserved_review_packet.jsonl"
    out=root/"boundary_quarantine_20260916"
    if out.exists():raise FileExistsError(out)
    sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
    m=json.loads((audit/"manifest.json").read_text())
    assert all(sha(audit/n)==h for n,h in m["outputs"].items())
    r=json.loads((audit/"report.json").read_text())
    groups=set(r["conservative_bridge_reserved_groups"])
    packet=[json.loads(x) for x in reserved.open()]
    excluded=[p for p in packet if p["contract"]["provisional_split_group"] in groups]
    remaining=[p for p in packet if p["contract"]["provisional_split_group"] not in groups]
    assert len(excluded)+len(remaining)==len(packet)
    stage=Path(tempfile.mkdtemp(prefix=".quarantine-",dir=root))
    def write(name,rr):
        with (stage/name).open("w") as f:
            for x in rr:f.write(json.dumps(x,sort_keys=True)+"\n")
    write("quarantined_pair_ids.jsonl",[{"pair_id":p["pair_id"],"group":p["contract"]["provisional_split_group"],
        "reason":"unresolved_or_unadopted_cross_split_boundary"} for p in excluded])
    write("remaining_preview_NOT_CERTIFIED.jsonl",remaining)
    report={"original_pairs":len(packet),"quarantined_pairs":len(excluded),"remaining_preview_pairs":len(remaining),
        "remaining_groups":len({p["contract"]["provisional_split_group"] for p in remaining}),
        "remaining_articles":len({p["article"]["article_id"] for p in remaining}),
        "gate":"FAIL_PENDING_BOUNDARY_REVIEW","remaining_certified":False,"original_modified":False,
        "automatic_refill":False,"sampling_design_requires_new_freeze":True}
    (stage/"report.json").write_text(json.dumps(report,indent=2)+"\n")
    (stage/"manifest.json").write_text(json.dumps({"inputs":{str(reserved):sha(reserved),str(audit/"manifest.json"):sha(audit/"manifest.json")},
        "code_sha256":sha(Path(__file__)),"outputs":{p.name:sha(p) for p in stage.iterdir()}},indent=2)+"\n")
    stage.rename(out)
    print(json.dumps(report,indent=2))

if __name__=="__main__":main()
