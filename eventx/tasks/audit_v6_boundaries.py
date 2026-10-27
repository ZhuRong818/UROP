"""Outcome-blind boundary audit. Similarity is review evidence, not certification."""
import hashlib
import json
from pathlib import Path
import re
import tempfile
from collections import defaultdict
import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer

ROOT=Path(__file__).resolve().parents[2]
OUT=ROOT/"data/v6/boundary_audit_20260916"

def read(path):
    return [json.loads(x) for x in path.open()]

def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def normalize(text):
    return " ".join(re.findall(r"\w+",(text or "").casefold()))

def nearest(left,right):
    results={}
    for channel,kw in [("word",dict(analyzer="word",ngram_range=(1,2))),
                       ("char",dict(analyzer="char_wb",ngram_range=(3,5)))]:
        x=TfidfVectorizer(sublinear_tf=True,**kw).fit_transform(left+right)
        scores=(x[:len(left)]@x[len(left):].T).toarray()
        for i,row in enumerate(scores):
            for j in np.argsort(-row,kind="stable")[:3]:
                results.setdefault((i,int(j)),{})[channel]=float(row[j])
    return results

def main():
    if OUT.exists():raise FileExistsError(OUT)
    paths={
        "dev":ROOT/"data/v6/hybrid_development_reviews_20260916/packet.jsonl",
        "reserved":ROOT/"data/v6/hybrid_audit_20260916/reserved_review_packet.jsonl",
        "cards":ROOT/"data/v6/contract_link_pilot_20260916/contract_cards.jsonl",
        "components":ROOT/"data/v5/reviewed_pair_graph_20260915/candidate_components.json",
        "unknown":ROOT/"data/v5/unresolved_followup_validation_20260915/remaining_unresolved.jsonl",
        "proposed":ROOT/"data/v5/unresolved_followup_validation_20260915/proposed_links.jsonl",
        "enriched":ROOT/"data/v5/unresolved_pair_enrichment_20260915/enriched_pairs.jsonl"}
    for release in [paths["dev"].parent,paths["reserved"].parent,paths["cards"].parent]:
        m=json.loads((release/"manifest.json").read_text())
        assert all(digest(release/n)==h for n,h in m["outputs"].items())
    dev,res=read(paths["dev"]),read(paths["reserved"])
    articles=lambda rows:sorted({r["article"]["article_id"]:r["article"] for r in rows}.values(),key=lambda a:a["article_id"])
    da,ra=articles(dev),articles(res)
    text=lambda a:"\n".join(a.get(k) or "" for k in ("headline","summary"))
    story_scores=nearest([text(a) for a in ra],[text(a) for a in da])
    exact=[]
    for i,a in enumerate(ra):
        for j,b in enumerate(da):
            fields=[k for k in ("headline","summary") if normalize(a.get(k)) and normalize(a.get(k))==normalize(b.get(k))]
            if fields:
                exact.append({"reserved_article_id":a["article_id"],"development_article_id":b["article_id"],"matching_fields":fields})
                story_scores.setdefault((i,j),{})["exact_field"]=fields
    stories=[];score_ledger=[]
    for (i,j),scores in sorted(story_scores.items()):
        identity="story-"+hashlib.sha256((ra[i]["article_id"]+"|"+da[j]["article_id"]).encode()).hexdigest()[:16]
        stories.append({"review_id":identity,"reserved_article":ra[i],"development_article":da[j],
                        "decision":None,"reviewer":None,"rationale":None})
        score_ledger.append({"review_id":identity,**scores})
    cards=read(paths["cards"])
    grouped=defaultdict(list)
    for c in cards:grouped[c["provisional_split_group"]].append(c)
    groups=lambda rr:{p["contract"]["provisional_split_group"] for p in rr}
    dg,rg=groups(dev),groups(res)
    dt,rt=sorted(dg),sorted(rg)
    group_text=lambda g:"\n".join(dict.fromkeys(" ".join(filter(None,[c["question"],c["yes_subtitle"],*c["event_titles"]])) for c in grouped[g]))
    family_scores=nearest([group_text(g) for g in rt],[group_text(g) for g in dt])
    families=[]
    for (i,j),scores in sorted(family_scores.items()):
        identity="boundary-"+hashlib.sha256((rt[i]+"|"+dt[j]).encode()).hexdigest()[:16]
        families.append({"review_id":identity,"reserved_group":rt[i],"development_group":dt[j],
            "reserved_contracts":grouped[rt[i]],"development_contracts":grouped[dt[j]],
            "decision":None,"reviewer":None,"rationale":None})
        score_ledger.append({"review_id":identity,**scores})
    comps=json.loads(paths["components"].read_text())
    eventgroup={e:"family-"+hashlib.sha256("|".join(sorted(cc)).encode()).hexdigest()[:16] for cc in comps for e in cc}
    # Keep all graph nodes, including unsampled intermediary events.
    parent={g:g for g in eventgroup.values()}
    def find(x):
        while parent[x]!=x:
            parent[x]=parent[parent[x]];x=parent[x]
        return x
    uncertain=[]
    for category in ("unknown","proposed"):
        for r in read(paths[category]):
            nodes=[e for e in r["evidence_refs"] if e in eventgroup]
            if len(nodes)!=2:raise ValueError("Need two explicit event references")
            a,b=map(eventgroup.get,nodes)
            parent[find(a)]=find(b)
            uncertain.append({"pair_id":r["pair_id"],"status":category,"events":nodes,"groups":[a,b]})
    cross_roots={find(g) for g in dg}&{find(g) for g in rg}
    affected_reserved=sorted(g for g in rg if find(g) in cross_roots)
    affected_dev=sorted(g for g in dg if find(g) in cross_roots)
    report={"status":"not_certified_review_required","development_groups":len(dg),"reserved_groups":len(rg),
        "direct_group_overlap":len(dg&rg),"exact_article_field_matches":len(exact),
        "story_review_pairs":len(stories),"family_review_pairs":len(families),
        "unresolved_or_unadopted_edges":len(uncertain),
        "conservative_bridge_reserved_groups":affected_reserved,"conservative_bridge_development_groups":affected_dev,
        "story_certified":False,"family_certified":False,"human_reviews_added":0,"protected_outcomes_accessed":False,
        "limits":["Top3 word/character candidates are not exhaustive semantic review",
                   "Uncertain-edge union is a quarantine preview, not an adopted graph",
                   "Exact common headlines can be boilerplate; inspect context",
                   "No statistical independence certificate is possible from semantic grouping alone"]}
    stage=Path(tempfile.mkdtemp(prefix=".boundary-",dir=OUT.parent))
    for name,records in [("story_review_packet",stories),("family_review_packet",families),
                         ("score_ledger",score_ledger),("exact_article_matches",exact),("uncertain_edges",uncertain)]:
        with (stage/f"{name}.jsonl").open("w") as f:
            for r in records:f.write(json.dumps(r,sort_keys=True)+"\n")
    (stage/"report.json").write_text(json.dumps(report,indent=2)+"\n")
    manifest={"inputs":{str(p.relative_to(ROOT)):digest(p) for p in paths.values()},
        "code_sha256":digest(Path(__file__)),"outputs":{p.name:digest(p) for p in stage.iterdir()}}
    (stage/"manifest.json").write_text(json.dumps(manifest,indent=2)+"\n")
    stage.rename(OUT)
    print(json.dumps(report,indent=2))

if __name__=="__main__":main()
