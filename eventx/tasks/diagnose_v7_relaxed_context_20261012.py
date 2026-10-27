"""Measure relaxed unsigned evidence yield and existing-key coverage, no labels."""
from collections import defaultdict
from datetime import datetime,timezone
from pathlib import Path
import json
import numpy as np
from eventx.tasks.diagnose_v7_signed_evidence_coverage_20261012 import write_json,write_jsonl,utc,groups,MINUTE_US
from eventx.tasks.prepare_v4_discovery_news_quality import EVENT_DTYPE,load_documents
from eventx.tasks.run_v4_discovery_models import OOF_DTYPE
from eventx.tasks.run_v5_residual_feasibility import REPO_ROOT,OOF,EVENTS,MARKETS,START_US,read_jsonl,sha256_file
from eventx.v7.policy_context_v04 import extract_context

OUT=REPO_ROOT/'data/v7/relaxed_policy_context_v04_1_20261012'

def main():
    if OUT.exists(): raise SystemExit('Existing output preserved; create another version')
    receipt=json.loads((REPO_ROOT/'data/v7/signed_evidence_v03_3_development_20261012/contract.json').read_text())
    for e in receipt['inputs']:
        if sha256_file(REPO_ROOT/e['path'])!=e['sha256']: raise RuntimeError(e['path'])
    OUT.mkdir(parents=True)
    code=[Path(__file__).resolve(),REPO_ROOT/'eventx/v7/policy_context_v04.py']
    write_json(OUT/'contract.json',{'created_at':datetime.now(timezone.utc).isoformat(),'inputs':receipt['inputs'],'code':[{'path':str(p.relative_to(REPO_ROOT)),'sha256':sha256_file(p)} for p in code],'policy':{'target_articles':100,'scope':'unsigned Fed policy context, not exact predicate implication','tiers':['policy_decision_context','policy_topic_context'],'primary_window_minutes':30,'sensitivity_windows_minutes':[60,180],'selection':'fixed rules before counts; do not tune to hit 100','unchanged_availability_and_existing_oof_keys':True,'labels_read':False,'models_fit':0}})
    raw=np.memmap(OOF,mode='r',dtype=OOF_DTYPE)
    rows=np.empty(len(raw),dtype=[('market','<u4'),('minute','<i4'),('fold','u1')])
    for f in rows.dtype.names: rows[f]=raw[f]
    del raw
    bymarket=groups(rows,'market'); times={m:START_US+rows['minute'][idx].astype(np.int64)*MINUTE_US for m,idx in bymarket.items()}
    for m,idx in bymarket.items():
        order=np.argsort(times[m]); bymarket[m]=idx[order]; times[m]=times[m][order]
    docs,stats=load_documents(); events=np.memmap(EVENTS,mode='r',dtype=EVENT_DTYPE)
    markets={int(m['market_index']):m for m in read_jsonl(MARKETS)}
    traces=[]; cache={}; coverage=defaultdict(set); articles=defaultdict(set); days=defaultdict(set)
    for i,e in enumerate(events):
        m,d=int(e['market']),int(e['document']); doc=docs[d]
        key=(d,markets[m]['question'])
        if key not in cache:
            summary=doc['text'][len(doc['headline']):].strip() if doc['text'].startswith(doc['headline']) else doc['text']
            cache[key]=extract_context(doc['headline'],summary,markets[m]['question'])
        result=cache[key]
        if result['tier']=='none': continue
        t=int(e['timestamp_us']); dt=int(round(doc['available_at'].timestamp()*1e6))
        if t!=dt: raise RuntimeError('availability clock mismatch')
        summary=doc['text'][len(doc['headline']):].strip() if doc['text'].startswith(doc['headline']) else doc['text']
        source='\n'.join(x for x in (doc['headline'],summary) if x)
        if any(source[s['start']:s['end']]!=s['text'] for s in result['spans']): raise RuntimeError('span mismatch')
        rec={'event_index':i,'article_id':doc['doc_id'],'market_index':m,'market_id':markets[m]['market_id'],'question':markets[m]['question'],'headline':doc['headline'],'summary':summary,'available_at':doc['available_at'].isoformat(),'published_at':doc['published_at'].isoformat(),'lag_minutes':(doc['available_at']-doc['published_at']).total_seconds()/60,'context':result,'coverage':{}}
        ts=times.get(m,np.empty(0,dtype=np.int64)); idx=bymarket.get(m,np.empty(0,dtype=int))
        for minutes in (30,60,180):
            lo=np.searchsorted(ts,t,side='left'); hi=np.searchsorted(ts,t+minutes*MINUTE_US,side='left'); hits=idx[lo:hi]
            rec['coverage'][str(minutes)]={'rows':len(hits),'folds':{str(f):int((rows['fold'][hits]==f).sum()) for f in range(1,6)}}
            for tier in (result['tier'],'all_context'):
                coverage[(tier,minutes)].update(map(int,hits))
                if len(hits): articles[(tier,minutes)].add(doc['doc_id']); days[(tier,minutes)].add(rec['available_at'][:10])
        traces.append(rec)
    print(f'Retained {len(traces)} contextual associations',flush=True)
    tiers={}
    for tier in ('policy_decision_context','policy_topic_context','all_context'):
        subset=[r for r in traces if tier=='all_context' or r['context']['tier']==tier]
        tiers[tier]={'associations':len(subset),'articles':len({r['article_id'] for r in subset}),'markets':len({r['market_id'] for r in subset}),'arrival_dates':len({r['available_at'][:10] for r in subset}),'coverage':{str(w):{'articles':len(articles[(tier,w)]),'rows':len(coverage[(tier,w)]),'arrival_dates':len(days[(tier,w)]),'folds':{str(f):{'rows':sum(rows['fold'][j]==f for j in coverage[(tier,w)]),'articles':len({r['article_id'] for r in subset if r['coverage'][str(w)]['folds'][str(f)]>0})} for f in range(1,6)}} for w in (30,60,180)}}
    # One review record per distinct article: decision context and actual primary
    # row coverage first; round-robin arrival dates to reduce date concentration.
    unique={}
    for r in sorted(traces,key=lambda r:(r['coverage']['30']['rows']==0,r['context']['tier']!='policy_decision_context',r['available_at'],r['article_id'],r['market_id'])):
        unique.setdefault(r['article_id'],r)
    eligible=[r for r in unique.values() if r['coverage']['30']['rows']>0]
    buckets=defaultdict(list)
    for r in eligible: buckets[r['available_at'][:10]].append(r)
    packet=[]
    while buckets and len(packet)<100:
        for day in sorted(list(buckets)):
            packet.append(buckets[day].pop(0))
            if not buckets[day]: del buckets[day]
            if len(packet)==100: break
    write_jsonl(OUT/'association_trace.jsonl',traces)
    write_jsonl(OUT/'review_packet_up_to_100.jsonl',[dict(r,review={'relevance':None,'claim_role':None,'wrong_period':None,'market_odds_repetition':None,'rationale':None}) for r in packet])
    report={'status':'complete','documents':stats,'associations_processed':len(events),'tiers':tiers,'review_packet':{'distinct_articles':len(packet),'arrival_dates':len({r['available_at'][:10] for r in packet}),'primary_existing_row_coverage_required':True,'labels':'blank; independent review outstanding'},'checks':{'input_hashes_verified':len(receipt['inputs']),'spans_and_availability_clocks_match':True,'outcome_fields_read':False,'forecast_models_fit':0,'protected_holdouts_read':False},'limits':['Context is an unsigned candidate, not exact YES/NO evidence or surprise.','Article/date counts do not establish independent episodes.','Existing OOF key eligibility is not certified source or market status.','60/180-minute coverage is descriptive sensitivity, not selected forecasting evaluation.']}
    report=json.loads(json.dumps(report,default=lambda v: int(v)))
    write_json(OUT/'report.json',report)
    files=list(OUT.iterdir())+code
    write_json(OUT/'manifest.json',{'artifacts':[{'path':str(p.relative_to(REPO_ROOT)),'sha256':sha256_file(p)} for p in files if p.is_file()]})
    print(json.dumps(report,indent=2,default=int),flush=True)

if __name__=='__main__': main()
