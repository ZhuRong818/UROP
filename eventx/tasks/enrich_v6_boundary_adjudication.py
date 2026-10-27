"""Attach recovered descriptive rules to unresolved reviews; never auto-adjudicate."""
import hashlib
import json
from pathlib import Path
from datetime import datetime

def main():
    base=Path("data/v6/boundary_adjudication_20260916")
    raw=Path("data/v5/provenance_recovery_20260908")
    out=Path("data/v6/boundary_adjudication_enriched_20260916")
    if out.exists():raise FileExistsError(out)
    sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
    read=lambda p:[json.loads(x) for x in p.open()]
    m=json.loads((base/"manifest.json").read_text())
    assert all(sha(base/n)==v for n,v in m["outputs"].items())
    selection=json.loads((base/"selection.json").read_text())
    evidence={};counts={};inputs={str(base/"manifest.json"):sha(base/"manifest.json")}
    for venue in ("kalshi","polymarket"):
        p=raw/f"v6_adjudication_{venue}_20260916.jsonl"
        receipt=raw/f"v6_adjudication_{venue}_20260916.json"
        r=json.loads(receipt.read_text());rr=read(p)
        assert r["status"]=="complete" and r["data_sha256"]==sha(p) and r["rows"]==len(rr)
        key="ticker" if venue=="kalshi" else "condition_id"
        assert set(x[key] for x in rr)==set(selection[venue]) and len(rr)==len(selection[venue])
        for line,x in enumerate(rr,1):
            evidence[f"{venue}:contract:{x[key]}"]={"record":x,"source_file":str(p),"source_line":line,
                "historical_feature_admission":False}
        counts[venue]={"requested":len(selection[venue]),"returned":len(rr),
            "with_rule_text":sum(bool(x.get("rules_primary") or x.get("description")) for x in rr)}
        inputs.update({str(p):sha(p),str(receipt):sha(receipt)})
    records=read(base/"adjudication_packet.jsonl")
    enriched=[];missing=set()
    for task in records:
        supplement=[]
        if task["kind"]=="family":
            review=task["submitted_review"]
            for field in ("reserved_contracts","development_contracts"):
                for c in review[field]:
                    if c["contract_id"] in evidence:
                        e=evidence[c["contract_id"]]
                        supplement.append({"side":field,"contract_id":c["contract_id"],**e})
                        if not(e["record"].get("rules_primary") or e["record"].get("description")):
                            missing.add(c["contract_id"])
        enriched.append({**task,"supplemental_rule_evidence":supplement})
    out.mkdir()
    with (out/"adjudication_packet.jsonl").open("w") as f:
        for r in enriched:f.write(json.dumps(r,sort_keys=True)+"\n")
    report={"recovery":counts,"adjudication_tasks":len(records),
        "unresolved_family_tasks_with_supplement":sum(t["kind"]=="family" and t["submitted_review"]["decision"]=="unresolved" and bool(t["supplemental_rule_evidence"]) for t in enriched),
        "contracts_still_without_rule_text":sorted(missing),"decisions_changed":0,"certified":False,
        "source_records_for_semantic_review_only":True,"outcomes_requested":False}
    (out/"report.json").write_text(json.dumps(report,indent=2)+"\n")
    (out/"manifest.json").write_text(json.dumps({"inputs":inputs,"code_sha256":sha(Path(__file__)),
        "outputs":{p.name:sha(p) for p in out.iterdir()}},indent=2)+"\n")
    print(json.dumps(report,indent=2))

if __name__=="__main__":main()
