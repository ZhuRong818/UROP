"""Later-date event opportunity inventory, with candidates frozen before labels."""
from collections import defaultdict,Counter
from datetime import datetime,timezone
from pathlib import Path
import json,re,hashlib
import numpy as np
from eventx.tasks.run_v5_residual_feasibility import REPO_ROOT,OOF,EXAMPLES,EVENTS,MARKETS,START_US,read_jsonl,sha256_file,verify_manifest,EXAMPLES_MANIFEST,OOF_MANIFEST,EVENT_MANIFEST
from eventx.tasks.run_v4_discovery_models import OOF_DTYPE
from eventx.tasks.build_v4_discovery_examples import EXAMPLE_DTYPE
from eventx.tasks.prepare_v4_discovery_news_quality import EVENT_DTYPE,load_documents
from eventx.tasks.diagnose_v7_signed_evidence_coverage_20261012 import write_json,write_jsonl,MINUTE_US

OUT=REPO_ROOT/'data/v7/event_opportunity_inventory_20261014'
CONTEXT=REPO_ROOT/'data/v7/relaxed_policy_context_v04_1_20261012'
ASSETS={'bitcoin':re.compile(r'\b(?:bitcoin|btc)\b',re.I),'ethereum':re.compile(r'\b(?:ethereum|ether|eth)\b',re.I)}
EVENT=re.compile(r'\b(?:ETF|ETFs|SEC|inflows?|outflows?|approv\w*|reject\w*|launch\w*|treasur\w*|purchas\w*|buys?|bought|acquir\w*|sells?|sold|hack\w*|upgrad\w*|adopt\w*|liquidat\w*)\b',re.I)
COMMENTARY=re.compile(r'\b(?:prediction|predicts?|forecast\w*|technical analysis|could|may|might|will|should|would|if|can)\b',re.I)
MARKET_ODDS=re.compile(r'\b(?:polymarket|kalshi|prediction markets?)\b',re.I)

def main():
    if OUT.exists():raise SystemExit('Preserve existing inventory')
    for p in [EXAMPLES_MANIFEST,OOF_MANIFEST,EVENT_MANIFEST,CONTEXT/'delivery_manifest.json']:verify_manifest(p)
    OUT.mkdir(parents=True)
    inputs=[EXAMPLES,OOF,EVENTS,MARKETS,CONTEXT/'association_trace.jsonl']
    contract={'created_at':datetime.now(timezone.utc).isoformat(),'scope':'opened event-cohort design inventory, no forecast fit or replacement evaluation','later_dates_minutes':[55*1440,66*1440],'populations':['existing fold5','all opened eligible example keys over same dates'],'primary_freshness_minutes':5,'trailing_trade_requirement':'at least 3 trades in preceding60m, in addition to inherited eligibility','event_rules':{'Fed':'reuse existing unsigned policy-decision-context links unchanged','crypto':'headline and linked question name same Bitcoin/Ethereum asset; headline contains event cue; exclude modal/forecast and prediction-market references','crypto_event_pattern':EVENT.pattern,'crypto_commentary_exclusion':COMMENTARY.pattern},'primary_news_availability_window_minutes':30,'candidate_packet':'up to100 unique articles, original fold5 coverage first and then low publication lag/availability, without using outcomes','outcomes':'opened labels only after candidate packet hash receipt; counts descriptive','independence':'exact text signatures only, not verified episodes','code_sha256':sha256_file(Path(__file__)),'inputs':[{'path':str(p.relative_to(REPO_ROOT)),'sha256':sha256_file(p)} for p in inputs]}
    write_json(OUT/'contract.json',contract)
    oof=np.memmap(OOF,mode='r',dtype=OOF_DTYPE);ex=np.memmap(EXAMPLES,mode='r',dtype=EXAMPLE_DTYPE);events=np.memmap(EVENTS,mode='r',dtype=EVENT_DTYPE)
    docs,docstats=load_documents();markets={int(m['market_index']):m for m in read_jsonl(MARKETS)}
    context={r['event_index']:r for r in read_jsonl(CONTEXT/'association_trace.jsonl') if r['context']['tier']=='policy_decision_context'}
    if not np.all(ex['market'][1:]>=ex['market'][:-1]):raise RuntimeError('examples not sorted by market')
    # Only key/feature fields used during selection; labels are not read here.
    caches={};records=[];rowsets={'fold5':set(),'all_groups':set()};eventrows={}
    start,end=55*1440,66*1440
    oof_by_market={}
    for m in np.unique(oof['market'][oof['fold']==5]):
        idx=np.flatnonzero((oof['market']==m)&(oof['fold']==5));oof_by_market[int(m)]=idx[np.argsort(oof['minute'][idx])]
    for i,e in enumerate(events):
        t=int(e['timestamp_us']);minute=(t-START_US)/MINUTE_US
        if not (start-30<minute<end):continue
        m,d=int(e['market']),int(e['document']);doc=docs[d];question=markets[m]['question'];headline=doc['headline']
        source=context.get(i)
        if source is not None:domain='fed_policy_context';role='unsigned policy-decision context'
        else:
            asset=next((name for name,pat in ASSETS.items() if pat.search(question) and pat.search(headline)),None)
            if not asset or not EVENT.search(headline) or COMMENTARY.search(headline) or MARKET_ODDS.search(headline):continue
            domain=asset;role='unreviewed crypto event headline'
        if t!=int(round(doc['available_at'].timestamp()*1e6)):raise RuntimeError('clock mismatch')
        if m not in caches:
            a,b=np.searchsorted(ex['market'],[m,m+1]);idx=np.arange(a,b)
            mask=(ex['minute'][idx]>=start)&(ex['minute'][idx]<end)&(ex['price_age'][idx]<=5)&(ex['features'][idx,6]>=3)
            idx=idx[mask];idx=idx[np.argsort(ex['minute'][idx])];caches[m]=idx
        idx=caches[m];times=START_US+ex['minute'][idx].astype(np.int64)*MINUTE_US
        lo=np.searchsorted(times,t,side='left');hi=np.searchsorted(times,t+30*MINUTE_US,side='left');hits=idx[lo:hi]
        oldidx=oof_by_market.get(m,np.empty(0,dtype=int));oldtimes=START_US+oof['minute'][oldidx].astype(np.int64)*MINUTE_US
        oldlo=np.searchsorted(oldtimes,t,side='left');oldhi=np.searchsorted(oldtimes,t+30*MINUTE_US,side='left');oldhits=oldidx[oldlo:oldhi]
        # Intersect original fold5 keys with the same fresh-feature screen.
        hitminutes=set(map(int,ex['minute'][hits]));oldhits=np.asarray([j for j in oldhits if int(oof['minute'][j]) in hitminutes],dtype=int)
        if not len(hits):continue
        summary=doc['text'][len(headline):].strip() if doc['text'].startswith(headline) else doc['text']
        sigtext=re.sub(r'\s+',' ',headline+'\n'+summary.split('Most Read from Bloomberg')[0]).strip().lower()
        r={'event_index':i,'article_id':doc['doc_id'],'domain':domain,'role':role,'headline':headline,'summary':summary,'available_at':doc['available_at'].isoformat(),'published_at':doc['published_at'].isoformat(),'lag_minutes':(doc['available_at']-doc['published_at']).total_seconds()/60,'market_id':markets[m]['market_id'],'question':question,'market_group':markets[m]['market_group'],'article_text_signature':hashlib.sha256(sigtext.encode()).hexdigest(),'all_group_fresh_rows':len(hits),'original_fold5_fresh_rows':len(oldhits),'earliest_fresh_decision_minute':int(ex['minute'][hits[0]]),'relevance':'unreviewed','novelty':'unknown','direction':None}
        records.append(r);eventrows[i]={'all_groups':hits,'fold5':oldhits}
        rowsets['all_groups'].update(map(int,hits));rowsets['fold5'].update(map(int,oldhits))
    # Receipt the complete outcome-free candidate ledger and review sample before
    # inspecting labels. Outcome diagnostic never changes candidate membership.
    write_jsonl(OUT/'candidate_ledger.jsonl',records)
    unique={}
    for r in sorted(records,key=lambda r:(r['original_fold5_fresh_rows']==0,r['lag_minutes'],r['available_at'],r['article_id'])):
        unique.setdefault(r['article_id'],r)
    packet=[]
    for r in list(unique.values())[:100]:
        rr=dict(r,review={'reviewer_id':None,'material_relevance':None,'source_role':None,'episode_id':None,'evidence_span':None,'novelty':None,'rationale':None});packet.append(rr)
    write_jsonl(OUT/'review_packet.jsonl',packet)
    write_json(OUT/'candidate_receipt_before_outcomes.json',{'created_at':datetime.now(timezone.utc).isoformat(),'candidates':len(records),'distinct_articles':len(unique),'review_articles':len(packet),'ledger_sha256':sha256_file(OUT/'candidate_ledger.jsonl'),'packet_sha256':sha256_file(OUT/'review_packet.jsonl'),'outcome_fields_read_before_receipt':False})
    print(f'Frozen {len(unique)} article candidates with fresh rows before outcome counts',flush=True)
    summaries={};labeled=[]
    for name,indices in rowsets.items():
        idx=np.asarray(sorted(indices),dtype=int);data=oof if name=='fold5' else ex
        rec=[r for r in records if len(eventrows[r['event_index']][name])]
        docsbyid={r['article_id']:r for r in rec}
        labels=data['label'][idx]
        summaries[name]={'rows':len(idx),'movement_rows':int(labels.sum()),'nonmovement_rows':int(len(labels)-labels.sum()),'markets':len(np.unique(data['market'][idx])),'articles':len(docsbyid),'arrival_dates':len({r['available_at'][:10] for r in rec}),'text_signatures':len({r['article_text_signature'] for r in rec}),'domain_articles':dict(Counter(r['domain'] for r in docsbyid.values())),'articles_publication_lag_le_minutes':{str(w):sum(r['lag_minutes']<=w for r in docsbyid.values()) for w in (30,60,180)}}
    for r in records:
        rr=dict(r,coverage={})
        for name in rowsets:
            idx=eventrows[r['event_index']][name];data=oof if name=='fold5' else ex
            rr['coverage'][name]={'rows':len(idx),'movement_rows':int(data['label'][idx].sum()),'nonmovement_rows':int(len(idx)-data['label'][idx].sum())}
        labeled.append(rr)
    write_jsonl(OUT/'coverage_after_candidate_freeze.jsonl',labeled)
    receipt=json.loads((OUT/'candidate_receipt_before_outcomes.json').read_text())
    if sha256_file(OUT/'candidate_ledger.jsonl')!=receipt['ledger_sha256'] or sha256_file(OUT/'review_packet.jsonl')!=receipt['packet_sha256']:raise RuntimeError('candidate changed after outcomes')
    lag=np.array([r['lag_minutes'] for r in unique.values()]);report={'status':'complete','documents':docstats,'date_window_UTC':['2026-07-11T00:00:00Z','2026-07-22T00:00:00Z'],'freshness_minutes':5,'count60_minimum':3,'news_window_minutes':30,'populations':summaries,'review_packet_articles':len(packet),'article_lag_quantiles':{str(q):float(np.quantile(lag,q)) if len(lag) else None for q in (0,.5,.9,1)},'checks':{'candidates_frozen_before_label_reads':True,'candidate_hashes_unchanged_after_outcome_counts':True,'clock_matches':True,'protected_payloads_read':False,'forecast_models_fit':0},'limits':['All-groups population is an exploratory event-cohort inventory, not a replacement for original reporting fold.','Legacy retrieval/snapshot rules and source validity remain unverified.','Crypto headline events and Fed context require independent material-relevance review.','Text signatures do not establish independent event count or novelty.','Outcome class balance counts are descriptive only, not selection criteria.']}
    write_json(OUT/'report.json',report)
    md=['# Fresh-market event candidates','','Development inventory over 11–21 July. Article selection uses text, availability and fresh-price/trading coverage; review packet omits outcomes. Broader all-group coverage is not the original held-market evaluation. Relevance and novelty remain unreviewed.','']
    for n,r in enumerate(packet,1):
        md += [f'## {n}. {r["headline"]}','',f'Article {r["article_id"]}; domain {r["domain"]}; available {r["available_at"]}; publication lag {r["lag_minutes"]:.1f} minutes.','',f'Contract: {r["question"]}','',f'Fresh rows: all groups {r["all_group_fresh_rows"]}; original fold5 {r["original_fold5_fresh_rows"]}.','',r['summary'],'','Review material relevance, evidence span, episode and novelty: ______','']
    (OUT/'REVIEW_PACKET.md').write_text('\n'.join(md))
    for r in contract['inputs']:
        if sha256_file(REPO_ROOT/r['path'])!=r['sha256']:raise RuntimeError('input changed')
    write_json(OUT/'manifest.json',{'artifacts':[{'path':str(p.relative_to(REPO_ROOT)),'sha256':sha256_file(p)} for p in list(OUT.iterdir())+[Path(__file__)] if p.is_file()]})
    print(json.dumps(report,indent=2),flush=True)

if __name__=='__main__':main()
