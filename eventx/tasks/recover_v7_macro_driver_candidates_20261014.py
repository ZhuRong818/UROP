"""Outcome-independent macro-driver retrieval with opened coverage diagnostics."""
from collections import defaultdict
from datetime import datetime,timezone
from pathlib import Path
import re,json,numpy as np
from eventx.tasks.run_v5_residual_feasibility import REPO_ROOT,OOF,EVENTS,MARKETS,START_US,read_jsonl,sha256_file,verify_manifest,EVENT_MANIFEST,OOF_MANIFEST
from eventx.tasks.run_v4_discovery_models import OOF_DTYPE
from eventx.tasks.prepare_v4_discovery_news_quality import EVENT_DTYPE,load_documents
from eventx.tasks.diagnose_v7_signed_evidence_coverage_20261012 import write_json,write_jsonl,groups,MINUTE_US

OUT=REPO_ROOT/'data/v7/macro_driver_recovery_20261014'
PATTERN=re.compile(r'\b(?:nonfarm\s+payrolls?|payrolls?|jobs?\s+(?:data|report|growth|openings)|employment\s+(?:data|report)|ADP|CPI|PCE|(?:consumer|producer)\s+prices?|inflation\s+(?:data|report|readings?)|retail\s+sales)\b',re.I)
FED=re.compile(r'\bfed\b|federal reserve|\bfomc\b',re.I)
US=re.compile(r'\b(?:us|u\.s\.|united states|american)\b',re.I)
FOREIGN=re.compile(r'\b(?:china|chinese|eurozone|germany|german|britain|british|uk|u\.k\.|canada|canadian|japan|japanese|australia|australian|india|indian)\b',re.I)

def main():
    if OUT.exists():raise SystemExit('Preserve existing output')
    verify_manifest(EVENT_MANIFEST);verify_manifest(OOF_MANIFEST)
    OUT.mkdir(parents=True)
    inputs=[OOF,EVENTS,MARKETS]
    write_json(OUT/'contract.json',{'created_at':datetime.now(timezone.utc).isoformat(),'role':'macro-driver retrieval/coverage development diagnostic, no forecasting fit','headline_pattern':PATTERN.pattern,'contract_gate':'legacy-linked Fed/FOMC question','country_policy':'explicit US in headline/summary flagged, foreign headline flagged; unresolved retained as review candidates','primary_window_minutes':30,'publication_lag_bands_minutes':[30,60,180],'packet_selection':'all fold5 covered candidate articles, date/availability order, up to100; no label-dependent selection','no_new_episode_or_relevance_certification':True,'code_sha256':sha256_file(Path(__file__)),'inputs':[{'path':str(p.relative_to(REPO_ROOT)),'sha256':sha256_file(p)} for p in inputs]})
    raw=np.memmap(OOF,mode='r',dtype=OOF_DTYPE);events=np.memmap(EVENTS,mode='r',dtype=EVENT_DTYPE)
    markets={int(m['market_index']):m for m in read_jsonl(MARKETS)};docs,stats=load_documents()
    bymarket=groups(raw,'market');times={m:START_US+raw['minute'][idx].astype(np.int64)*MINUTE_US for m,idx in bymarket.items()}
    for m in bymarket:
        order=np.argsort(times[m]);bymarket[m]=bymarket[m][order];times[m]=times[m][order]
    records=[];covered_by_fold=defaultdict(set);articles=defaultdict(set)
    for i,e in enumerate(events):
        m,d=int(e['market']),int(e['document']);doc=docs[d]
        if not FED.search(markets[m]['question']) or not PATTERN.search(doc['headline']):continue
        ts=times.get(m,np.empty(0,dtype=np.int64));idx=bymarket.get(m,np.empty(0,dtype=int));t=int(e['timestamp_us'])
        lo=np.searchsorted(ts,t,side='left');hi=np.searchsorted(ts,t+30*MINUTE_US,side='left');hits=idx[lo:hi]
        if not len(hits):continue
        if t!=int(round(doc['available_at'].timestamp()*1e6)):raise RuntimeError('availability mismatch')
        summary=doc['text'][len(doc['headline']):].strip() if doc['text'].startswith(doc['headline']) else doc['text']
        r={'event_index':i,'article_id':doc['doc_id'],'headline':doc['headline'],'summary':summary,'market_id':markets[m]['market_id'],'question':markets[m]['question'],'available_at':doc['available_at'].isoformat(),'published_at':doc['published_at'].isoformat(),'lag_minutes':(doc['available_at']-doc['published_at']).total_seconds()/60,'country_explicit_US':bool(US.search(doc['headline']+' '+summary[:600])),'foreign_headline_flag':bool(FOREIGN.search(doc['headline'])),'headline_match':PATTERN.search(doc['headline'])[0],'signed_direction':None,'relevance':'unreviewed','coverage':{}}
        for f in range(1,6):
            fidx=hits[raw['fold'][hits]==f]
            r['coverage'][str(f)]={'rows':len(fidx),'movement_rows':int(raw['label'][fidx].sum()),'nonmovement_rows':int(len(fidx)-raw['label'][fidx].sum())}
            if len(fidx):covered_by_fold[f].update(map(int,fidx));articles[f].add(r['article_id'])
        records.append(r)
    foldsummary={str(f):{'articles':len(articles[f]),'rows':len(covered_by_fold[f]),'movement_rows':sum(int(raw['label'][j]) for j in covered_by_fold[f]),'nonmovement_rows':sum(int(raw['label'][j]==0) for j in covered_by_fold[f])} for f in range(1,6)}
    unique={}
    for r in sorted(records,key=lambda r:(r['available_at'],r['article_id'],r['market_id'])):
        if r['coverage']['5']['rows']:unique.setdefault(r['article_id'],r)
    # Outcome counts are withheld from the review packet; all covered fold5
    # articles are retained in chronological order without choosing positives.
    packet=[]
    for r in list(unique.values())[:100]:
        rr={k:v for k,v in r.items() if k!='coverage'};rr['review']={'reviewer_id':None,'material_context':None,'information_role':None,'US_measurement_identity':None,'episode_id':None,'novelty':None,'evidence_span':None};packet.append(rr)
    lag={r['article_id']:r['lag_minutes'] for r in unique.values()}
    report={'status':'complete','documents':stats,'covered_associations':len(records),'covered_articles_all_folds':len({r['article_id'] for r in records}),'folds':foldsummary,'fold5_article_lag_quantiles':{str(q):float(np.quantile(list(lag.values()),q)) if lag else None for q in [0,.5,1]},'fold5_articles_available_within_publication_lag':{str(w):sum(v<=w for v in lag.values()) for w in [30,60,180]},'review_packet':{'articles':len(packet),'selection_uses_outcome':False,'outcome_fields_omitted':True,'explicit_US_articles':sum(r['country_explicit_US'] for r in packet),'foreign_headline_flags':sum(r['foreign_headline_flag'] for r in packet)},'forecast_fits':0,'limits':['Macro-driver topic matches are unreviewed hypotheses, not exact contract evidence.','Availability lag is not first-public information timing.','Existing folds opened; coverage labels used only descriptively, not for candidate selection.','Country/report identity, episode duplication and novelty require review.']}
    write_jsonl(OUT/'association_coverage.jsonl',records);write_jsonl(OUT/'fold5_review_packet.jsonl',packet);write_json(OUT/'report.json',report)
    md=['# Later-fold macro-driver candidates','','Headline-level employment, inflation and retail-sales hypotheses linked to Fed markets. Candidate selection ignores movement outcomes. Country/report identity, material relevance and novelty remain unreviewed.','']
    for n,r in enumerate(packet,1):
        md += [f'## {n}. {r["headline"]}','',f'Article {r["article_id"]}; available {r["available_at"]}; publication lag {r["lag_minutes"]:.1f} minutes.','',f'Example contract: {r["question"]}','',r['summary'],'','Review role/relevance/episode: ______','']
    (OUT/'REVIEW_PACKET.md').write_text('\n'.join(md))
    write_json(OUT/'manifest.json',{'artifacts':[{'path':str(p.relative_to(REPO_ROOT)),'sha256':sha256_file(p)} for p in list(OUT.iterdir())+[Path(__file__)] if p.is_file()]})
    print(json.dumps(report,indent=2),flush=True)

if __name__=='__main__':main()
