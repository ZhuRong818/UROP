"""Score-blinded union of legacy pilot and hybrid top-five development pairs."""
import hashlib
import json
from pathlib import Path
import random
import tempfile

def main():
    pilot=Path("data/v6/contract_link_pilot_20260916")
    hybrid=Path("data/v6/hybrid_audit_20260916")
    out=Path("data/v6/hybrid_development_reviews_20260916")
    if out.exists():raise FileExistsError(out)
    read=lambda p:[json.loads(x) for x in p.open()]
    digest=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
    for release in (pilot,hybrid):
        manifest=json.loads((release/"manifest.json").read_text())
        assert all(digest(release/n)==h for n,h in manifest["outputs"].items())
    cards={c["contract_id"]:c for c in read(pilot/"contract_cards.jsonl")}
    articles={a["article_id"]:a for a in read(pilot/"articles.jsonl")}
    packet={p["pair_id"]:p for p in read(pilot/"development_review_packet.jsonl")}
    original=len(packet)
    for r in read(hybrid/"development_top5.jsonl"):
        identity=hashlib.sha256((r["article_id"]+"|"+r["contract_id"]).encode()).hexdigest()[:24]
        packet.setdefault(identity,{"pair_id":identity,"article":articles[r["article_id"]],
            "contract":cards[r["contract_id"]],"reviewer_id":None,
            "labels":{"relevance":None,"outcome_applicability":None,"evidence_spans":[],"identity_problem":None}})
    reserved=read(hybrid/"reserved_review_packet.jsonl")
    assert not {p["contract"]["provisional_split_group"] for p in packet.values()} & {p["contract"]["provisional_split_group"] for p in reserved}
    rr=list(packet.values());random.Random(20260918).shuffle(rr)
    stage=Path(tempfile.mkdtemp(prefix=".dev-review-",dir=out.parent))
    def write(name,rows):
        with (stage/name).open("w") as f:
            for r in rows:f.write(json.dumps(r,sort_keys=True)+"\n")
    write("packet.jsonl",rr)
    for suffix in ("A","B"):
        write(f"reviewer_{suffix}_responses.jsonl",[{k:r[k] for k in ("pair_id","labels","reviewer_id")} for r in rr])
    report={"status":"development_only_unlabelled","pairs":len(rr),"original_pairs":original,
            "additional_hybrid_pairs":len(rr)-original,"reserved_group_overlap":0,"human_labels":0}
    (stage/"report.json").write_text(json.dumps(report,indent=2)+"\n")
    manifest={"inputs":{str(p):digest(p) for p in [pilot/"manifest.json",hybrid/"manifest.json"]},
        "code_sha256":digest(Path(__file__)),"outputs":{p.name:digest(p) for p in stage.iterdir()}}
    (stage/"manifest.json").write_text(json.dumps(manifest,indent=2)+"\n")
    stage.rename(out)
    print(json.dumps(report))

if __name__ == "__main__":main()
