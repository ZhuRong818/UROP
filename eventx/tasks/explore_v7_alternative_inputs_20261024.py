"""Coverage-only exploration of outcome-side trades and book measurements.

Uses fixed historical source-rehearsal snapshots, not holdouts. No predictor,
forward return, label, performance statistic or production substitution.
"""
from bisect import bisect_right
from collections import Counter,defaultdict
from datetime import datetime,timezone
import json
import math
from pathlib import Path
import numpy as np
from eventx.tasks.discover_v7_direct_pilot_20261022 import REPO_ROOT,now,sha,write,verify_originals

OUT=REPO_ROOT/'data/v7/alternative_inputs_20261024'
SOURCES=[
 ('completed_v03','data/v7/direct_source_pilot_20261022_v03/audits/20261024T060327Z_808a25',
  'eventx/release/v7/direct_source_pilot_20261022_v03'),
 ('expansion_interim','data/v7/expansion_source_pilot_20261024/audits/20261024T082628Z_598812',
  'eventx/release/v7/expansion_source_pilot_20261024'),
]

def stamp(v):
    if isinstance(v,(int,float)) or str(v).replace('.','',1).isdigit():
        n=float(v);return n/1000 if n>1e11 else n
    return datetime.fromisoformat(v.replace('Z','+00:00')).timestamp()

def iso(t):return datetime.fromtimestamp(t,timezone.utc).isoformat()

def stats(v):
    if not v:return None
    return {'n':len(v),'min':float(min(v)),'median':float(np.median(v)),
            'p90':float(np.quantile(v,.9)),'max':float(max(v))}

def main():
    OUT.mkdir(parents=True,exist_ok=False)
    write(OUT/'exploration_contract.json',{
        'at':now().isoformat(),'status':'exploratory coverage diagnostic; not confirmatory study',
        'source_audits':[x[1] for x in SOURCES],'grid_seconds':300,
        'book_receipt_max_age_seconds':120,'optional_book_source_timestamp_age_seconds':300,
        'book_screen':{'max_probability_spread':.05,'minimum_size_each_best_level':10},
        'same_side_pair_receipt_skew_max_seconds':30,
        'trade_screen':'latest complete six-hour single-page venue window available by grid, receipt age<=120s; compare YES,NO and pooled raw records',
        'count_warning':'Maker-inclusive observations are not proven unique executions; pooled activity is an optimistic representation diagnostic',
        'quantity':'token size; windows(t-window,t]',
        'quote_history':'241 minute samples from already durable books, every receipt age<=120s and chosen quality screen; no filling across missing coverage',
        'no_retrospective_availability':True,'models_scored':False,'labels_computed':False,
        'screen_choices':'Exploratory, fixed before this run reads payloads; not tuned for predictive performance',
    })
    protected=set(json.loads((REPO_ROOT/'eventx/release/v7/market_capture_20261018/protected_ids.json').read_text()))
    grid_rows=[];window_rows=[];market_rows=[];used={};books_seen=[]
    for name,rel,release_rel in SOURCES:
        audit=REPO_ROOT/rel;release=REPO_ROOT/release_rel
        manifest=json.loads((audit/'manifest.json').read_text())
        for path,h in manifest['files'].items():
            if sha(REPO_ROOT/path)!=h:raise RuntimeError('Audit hash mismatch')
        for path,h in json.loads((release/'implementation_manifest.json').read_text())['locked_files'].items():
            if sha(REPO_ROOT/path)!=h:raise RuntimeError('Implementation hash mismatch')
        report=json.loads((audit/'report.json').read_text());run=REPO_ROOT/report['run']
        contract=json.loads((audit/'run_contract.json').read_text())
        begin=math.ceil(stamp(contract['started_at'])/300)*300
        end=math.floor(min(stamp(contract['stop_at']),stamp(report['created_at']))/300)*300
        samples=[json.loads(l) for l in (release/'sample.jsonl').read_text().splitlines()]
        if protected.intersection(r['market_id'] for r in samples):raise RuntimeError('Protected overlap')
        records=defaultdict(list);summaries={}
        with (audit/'journal.jsonl').open() as f:
            for line in f:
                r=json.loads(line)
                if r['kind']=='rest' and r['source']=='venue' and r.get('status')=='observed':
                    records[r['market_id'],r['endpoint_kind']].append(r)
                elif r['kind']=='window_summary' and r['source']=='venue':summaries[r['market_id'],r['cycle']]=r
        for s in samples:
            cid=s['market_id'];cache={}
            def payload(r):
                h=r['payload_sha256'];p=run/'objects'/h
                if h not in cache:
                    if sha(p)!=h:raise RuntimeError('Payload hash mismatch')
                    used[str(p.relative_to(REPO_ROOT))]=h;cache[h]=json.loads(p.read_text())
                return cache[h]
            bseries={}
            for side,asset in [('yes',s['yes_asset_id']),('no',s['no_asset_id'])]:
                series=[]
                for r in records[cid,'book_'+side+'_asset_id']:
                    b=payload(r)
                    if str(b.get('asset_id'))!=asset or b.get('market')!=cid:raise RuntimeError('Book identity mismatch')
                    bids=[(float(x['price']),float(x['size'])) for x in b.get('bids',[]) if float(x['size'])>0]
                    asks=[(float(x['price']),float(x['size'])) for x in b.get('asks',[]) if float(x['size'])>0]
                    f={'available_at':stamp(r['available_at']),'payload_sha256':r['payload_sha256'],'valid':False}
                    if bids and asks:
                        bid=max(x[0] for x in bids);ask=min(x[0] for x in asks)
                        bq=sum(q for p,q in bids if p==bid);aq=sum(q for p,q in asks if p==ask)
                        valid=0<bid<=ask<1
                        f.update(valid=valid,bid=bid,ask=ask,bid_size=bq,ask_size=aq,spread=ask-bid,
                            midpoint=(bid+ask)/2,imbalance=(bq-aq)/(bq+aq),weighted_mid=(ask*bq+bid*aq)/(bq+aq),
                            source_at=stamp(b['timestamp']) if b.get('timestamp') else None,
                            quality=valid and ask-bid<=.05+1e-12 and min(bq,aq)>=10)
                    series.append(f)
                series.sort(key=lambda r:r['available_at']);bseries[side]=([r['available_at'] for r in series],series)
                books_seen.append({'source':name,'market_id':cid,'side':side,'receipts':len(series),
                    'valid_two_sided_receipts':sum(r['valid'] for r in series)})
            def book(side,t):
                times,rs=bseries[side];i=bisect_right(times,t)-1
                if i<0:return None
                b=rs[i]
                if t-b['available_at']>120 or not b['valid']:return None
                if b['source_at'] is not None and b['source_at']>t:return None
                return b
            trade_windows=[]
            bycycle=defaultdict(list)
            for r in records[cid,'trades']:bycycle[r['cycle']].append(r)
            for cycle,rs in sorted(bycycle.items()):
                w=summaries.get((cid,cycle))
                if len(rs)!=1 or not w or not w.get('endpoint_window_returned') or w['end']-w['start']<14400:continue
                r=rs[0];v=payload(r);rr=[]
                for x in v['data']:
                    token=str(x['token_id'])
                    if token not in [s['yes_asset_id'],s['no_asset_id']]:raise RuntimeError('Trade token scope mismatch')
                    ts=stamp(x['timestamp'])
                    if not w['start']<=ts<=w['end']:continue
                    rr.append({'side':'yes' if token==s['yes_asset_id'] else 'no','time':ts,'size':float(x['size']),
                        'price':float(x['price']) if token==s['yes_asset_id'] else 1-float(x['price'])})
                av=max(stamp(r['available_at']),stamp(w['at']))
                trade_windows.append((av,w,rr))
                counts=Counter(x['side'] for x in rr)
                window_rows.append({'source':name,'market_id':cid,'role':s['diagnostic_role'],'cycle':cycle,
                    'available_at':av,'window_start':w['start'],'window_end':w['end'],
                    'yes_records':counts['yes'],'no_records':counts['no'],'raw_records':len(rr),
                    'distinct_timestamps':len({x['time'] for x in rr}),
                    'not_unique_execution_counts':True})
            trade_windows.sort(key=lambda x:x[0]);tt=[x[0] for x in trade_windows]
            def trade_features(rr,t,side):
                rr=[x for x in rr if x['time']<=t and (side=='pooled' or x['side']==side)]
                c60=sum(t-3600<x['time'] for x in rr);c240=sum(t-14400<x['time'] for x in rr)
                q240=sum(x['size'] for x in rr if t-14400<x['time']);last=max((x['time'] for x in rr),default=None)
                ages=None if last is None else t-last;pp={round(x['price'],12) for x in rr if x['time']==last}
                fresh=ages is not None and 0<=ages<=300
                return {'count60':c60,'count240':c240,'quantity240':q240,'age_seconds':ages,
                    'fresh':fresh,'last_price':next(iter(pp)) if len(pp)==1 else None,'ambiguous_last_timestamp':len(pp)>1,
                    'raw_activity_screen':fresh and c60>=3 and c240>=3 and q240>=100,
                    'source_completeness':False}
            own=[]
            for t in range(begin,end+1,300):
                y,n=book('yes',t),book('no',t)
                row={'source':name,'market_id':cid,'question':s['question'],'role':s['diagnostic_role'],'grid_at':iso(t),
                    'yes_book_available':y is not None,'no_book_available':n is not None,
                    'yes_book_quality':bool(y and y['quality']),'no_book_quality':bool(n and n['quality']),
                    'yes_book_source_timestamp_recent':bool(y and y['source_at'] is not None and 0<=t-y['source_at']<=300),
                    'composite_available':False,'composite_crossed':False,'quote_history240_quality':False,
                    'positive_quote_sigma240':False,'trade_window_current':False,'trade_features':None}
                if y:
                    row.update(yes_midpoint=y['midpoint'],yes_spread=y['spread'],yes_imbalance=y['imbalance'],
                        weighted_mid_deviation=y['weighted_mid']-y['midpoint'],yes_receipt_sha256=y['payload_sha256'])
                if y and n and abs(y['available_at']-n['available_at'])<=30:
                    bid=max(y['bid'],1-n['ask']);ask=min(y['ask'],1-n['bid'])
                    row.update(composite_crossed=bid>ask+1e-12,composite_available=bid<=ask+1e-12,
                        composite_bid=bid,composite_ask=ask,complement_mid_disagreement=abs(y['midpoint']-(1-n['midpoint'])),
                        no_receipt_sha256=n['payload_sha256'])
                history=[book('yes',u) for u in range(t-14400,t+1,60)]
                if all(b and b['quality'] for b in history):
                    mids=np.clip([b['midpoint'] for b in history],.0001,.9999)
                    sigma=float(np.std(np.diff(np.log(mids/(1-mids))),ddof=0))
                    row.update(quote_history240_quality=True,quote_sigma240=sigma,positive_quote_sigma240=sigma>0)
                ix=bisect_right(tt,t)-1
                if ix>=0:
                    av,w,rr=trade_windows[ix]
                    if 0<=t-av<=120 and w['start']<=t-14400:
                        row['trade_window_current']=True
                        row['trade_features']={side:trade_features(rr,t,side) for side in ['yes','no','pooled']}
                own.append(row);grid_rows.append(row)
            counters={k:sum(bool(r[k]) for r in own) for k in ['yes_book_available','no_book_available','yes_book_quality','no_book_quality','yes_book_source_timestamp_recent',
                'composite_available','composite_crossed','quote_history240_quality','positive_quote_sigma240','trade_window_current']}
            for side in ['yes','no','pooled']:
                counters[side+'_fresh_trade_grids']=sum(bool(r['trade_features'] and r['trade_features'][side]['fresh']) for r in own)
                counters[side+'_raw_activity_grids']=sum(bool(r['trade_features'] and r['trade_features'][side]['raw_activity_screen']) for r in own)
            market_rows.append({'source':name,'market_id':cid,'question':s['question'],'role':s['diagnostic_role'],'grids':len(own),
                **counters,'spread_stats':stats([r['yes_spread'] for r in own if r['yes_book_available']]),
                'weighted_mid_abs_deviation_stats':stats([abs(r['weighted_mid_deviation']) for r in own if r['yes_book_available']]),
                'complement_mid_disagreement_stats':stats([r['complement_mid_disagreement'] for r in own if 'complement_mid_disagreement' in r])})
    groups=[]
    for source,role in sorted({(r['source'],r['role']) for r in market_rows}):
        rr=[r for r in market_rows if r['source']==source and r['role']==role]
        keys=['grids']+[k for k in rr[0] if k.endswith('_grids')]+['yes_book_available','no_book_available','yes_book_quality','no_book_quality','yes_book_source_timestamp_recent','composite_available','composite_crossed','quote_history240_quality','positive_quote_sigma240','trade_window_current']
        groups.append({'source':source,'role':role,'markets':len(rr),**{k:sum(r[k] for r in rr) for k in keys}})
    report={'at':now().isoformat(),'groups':groups,'original_locks_verified':verify_originals(),
        'payloads_read_and_verified':len(used),'models_loaded_or_scored':False,'forward_labels_computed':False,
        'predictive_admissions':0,'production_substitution':False,
        'interpretation':'Book and trade quantities measure input coverage only. Quote target and both-token representation require separately specified studies and prospective baselines.',
        'limits':['Trade snapshot screen omits intervening short-window updates; this conservative view can undercount current activity.',
            'Counts are maker-inclusive raw records; pooling YES and NO can double count economic executions.',
            'Fresh book receipt is not a fresh execution or a newly changed quote. Source-timestamp recency reported separately.',
            'Quality screen is exploratory, not a guarantee of executability or calibrated probability.',
            'No forward return, directional accuracy, log loss, Brier or AP was computed.',
            'Market grids and overlapping windows are dependent, not independent episodes.']}
    for name,rows in [('grids',grid_rows),('markets',market_rows),('trade_windows',window_rows),('book_counts',books_seen)]:
        (OUT/(name+'.jsonl')).write_text(''.join(json.dumps(r,sort_keys=True)+'\n' for r in rows))
    write(OUT/'report.json',report);write(OUT/'payload_hashes.json',used)
    files=list(OUT.iterdir())+[Path(__file__).resolve()]+[REPO_ROOT/rel/'manifest.json' for _,rel,_ in SOURCES]
    write(OUT/'manifest.json',{'files':{str(p.relative_to(REPO_ROOT)):sha(p) for p in files}})
    print(json.dumps(report,indent=2))

if __name__=='__main__':main()
