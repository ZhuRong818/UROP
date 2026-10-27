"""Validate submitted boundary reviews; preview risks without adopting decisions."""
from collections import Counter
import hashlib
import json
from pathlib import Path
import tempfile

BASE=Path("data/v6/boundary_audit_20260916")
OUT=Path("data/v6/boundary_submission_validation_20260916")
ALLOWED={"family":{"must_link","no_direct_link_established","unresolved"},
         "story":{"same_story","related_update","distinct_story","unresolved"}}

def read(p):return [json.loads(x) for x in p.open()]
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def write(p,rows):
    with p.open("w") as f:
        for r in rows:f.write(json.dumps(r,sort_keys=True)+"\n")

def validate(original,submitted,kind):
    index={r["review_id"]:r for r in original}
    ids=[r.get("review_id") for r in submitted]
    errors=[]
    if len(set(ids))!=len(ids):errors.append({"error":"duplicate_ids"})
    if set(ids)!=set(index):errors.append({"error":"id_set_mismatch"})
    for r in submitted:
        key=r.get("review_id")
        if key not in index:continue
        if r.get("decision") not in ALLOWED[kind]:errors.append({"review_id":key,"error":"decision"})
        for k in ("reviewer","rationale"):
            if not isinstance(r.get(k),str) or not r[k].strip():errors.append({"review_id":key,"error":k})
        changed=[k for k,v in index[key].items() if k not in {"decision","reviewer","rationale"} and r.get(k)!=v]
        if changed:errors.append({"review_id":key,"error":"evidence_changed","fields":changed})
    return errors

def main():
    if OUT.exists():raise FileExistsError(OUT)
    frozen=json.loads((BASE/"manifest.json").read_text())
    assert all(sha(BASE/n)==h for n,h in frozen["outputs"].items())
    inputs={};results={};submitted={};originals={}
    for kind in ALLOWED:
        p=BASE/f"{kind}_review_packet.jsonl"
        q=BASE/f"{kind}_review_packet_reviewed_20260916.jsonl"
        original,rr=read(p),read(q)
        inputs.update({str(p):sha(p),str(q):sha(q)})
        errors=validate(original,rr,kind)
        results[kind]={"rows":len(rr),"errors":errors,"structural_validation_pass":not errors,
                       "decisions":dict(Counter(r.get("decision") for r in rr)),
                       "reviewers":dict(Counter(r.get("reviewer") for r in rr))}
        submitted[kind]=rr;originals[kind]=original
    preview=[]
    if all(v["structural_validation_pass"] for v in results.values()):
        risks={r["reserved_group"] for r in submitted["family"] if r["decision"] in {"must_link","unresolved"}}
        story_risks={r["reserved_article"]["article_id"] for r in submitted["story"] if r["decision"]!="distinct_story"}
        prior_path=Path("data/v6/boundary_quarantine_20260916/quarantined_pair_ids.jsonl")
        reserved_path=Path("data/v6/hybrid_audit_20260916/reserved_review_packet.jsonl")
        inputs.update({str(prior_path):sha(prior_path),str(reserved_path):sha(reserved_path)})
        prior={r["pair_id"] for r in read(prior_path)}
        for r in read(reserved_path):
            reasons=[]
            if r["pair_id"] in prior:reasons.append("existing_quarantine")
            if r["contract"]["provisional_split_group"] in risks:reasons.append("submitted_family_risk_unadopted")
            if r["article"]["article_id"] in story_risks:reasons.append("submitted_story_risk_unadopted")
            if reasons:preview.append({"pair_id":r["pair_id"],"reasons":reasons})
        impact={"prior_quarantined_pairs":len(prior),"preview_flagged_pairs":len(preview),
                "additional_flagged_pairs":len({r["pair_id"] for r in preview}-prior),
                "remaining_preview_pairs":600-len(preview),"reserved_family_groups_flagged":len(risks),
                "reserved_articles_flagged":len(story_risks),"adopted":False}
    else:impact={"not_computed":"invalid_submission"}
    report={"status":"first_submission_validated_not_certified","validation":results,"impact":impact,
            "independent_second_reviews_present":False,"reviewer_human_provenance":"not_confirmed",
            "certified":False,"frozen_graph_or_split_modified":False}
    stage=Path(tempfile.mkdtemp(prefix=".submission-validation-",dir=OUT.parent))
    write(stage/"risk_preview.jsonl",preview)
    for kind in ALLOWED:
        write(stage/f"{kind}_second_review_packet.jsonl",originals[kind])
        write(stage/f"{kind}_decisions_requiring_resolution.jsonl",[r for r in submitted[kind]
              if r["decision"] not in {"distinct_story","no_direct_link_established"}])
    (stage/"report.json").write_text(json.dumps(report,indent=2)+"\n")
    (stage/"manifest.json").write_text(json.dumps({"inputs":inputs,"code_sha256":sha(Path(__file__)),
        "outputs":{p.name:sha(p) for p in stage.iterdir()}},indent=2)+"\n")
    stage.rename(OUT)
    print(json.dumps(report,indent=2))

if __name__=="__main__":main()
