"""Frozen, bounded seven-date direct-topquote source pilot; no model evaluation."""
import argparse
from bisect import bisect_right
from collections import Counter, defaultdict
from datetime import datetime, timedelta, timezone
import hashlib
import io
import json
from pathlib import Path
import httpx
import pyarrow as pa
import pyarrow.compute as pc
import pyarrow.parquet as pq
from eventx.v7.archive_ranges_20261024 import RangeStore, read_columns
from eventx.tasks.discover_v7_direct_pilot_20261022 import REPO_ROOT, now, sha, write, verify_originals

BASE=REPO_ROOT/'data/v7/archive_week_pilot_20261025'
REL=REPO_ROOT/'eventx/release/v7/archive_week_pilot_20261025'
PARENT=REPO_ROOT/'data/v7/archive_sample_20261025_v03/attempt_20261025T011030Z_66d836'
EX=REPO_ROOT/'eventx/release/v7/archive_compatibility_20261024/excluded_market_ids.json'
DATES=[f'2026-04-{d:02d}' for d in range(21,28)]
COLS=['market','asset_id','event_type','timestamp_received','timestamp','best_bid','best_ask']


def verify(path,key='files'):
    for name,h in json.loads(path.read_text())[key].items():
        if sha(REPO_ROOT/name)!=h:raise RuntimeError('Hash drift: '+name)


class Cached:
    def __init__(self):
        self.folder=PARENT/'ranges';self.rs=[json.loads(x) for x in (self.folder/'requests.jsonl').read_text().splitlines()];self.objects={}
        for r in self.rs:
            if r['method']=='HEAD' and r.get('http_status')==200:self.objects[r['url']]=r
    def get(self,url,start,end,role):
        r=next(r for r in self.rs if r['url']==url and r.get('start')==start and r.get('end')==end and 'sha256'in r)
        b=(self.folder/r['sha256']).read_bytes();assert hashlib.sha256(b).hexdigest()==r['sha256'];return b
    def metadata(self,url):
        r=next(r for r in self.rs if r['url']==url and r.get('role')=='footer_only')
        b=self.get(url,r['start'],r['end'],'cache');return pq.read_metadata(io.BytesIO(b'PAR1'+b+len(b).to_bytes(4,'little')+b'PAR1'))


def prepare():
    verify_originals();verify(PARENT/'manifest.json');BASE.mkdir(exist_ok=False);REL.mkdir(exist_ok=False)
    excluded=set(json.loads(EX.read_text()));cache=Cached();sets=[]
    for hour in ['2026-04-21T12','2026-04-21T13']:
        url='https://r2v2.pmxt.dev/polymarket_orderbook_'+hour+'.parquet';m=cache.metadata(url)
        t=read_columns(cache,url,m,0,COLS[:5],'cached_identity_only');books=t.filter(pc.equal(t['event_type'],'book'))
        counts=Counter(x.decode() for x in books['market'].to_pylist());ids=sorted(x.decode() for x in t['market'].unique().to_pylist())
        sets.append({c for c,n in counts.items() if n>=2 and c not in excluded and c not in [ids[0],ids[-1]]})
    candidates=sorted(set.intersection(*sets),key=lambda c:hashlib.sha256(('EventX-week-pilot-v1:'+c).encode()).hexdigest())[:128]
    write(REL/'candidates_before_metadata.json',candidates)
    policy={'at':now().isoformat(),'dates':DATES,'hours_utc':[12,13],'scheduled_files':14,'hours_sampled':14,'full_week_capture':False,
            'max_markets':20,'max_metadata_candidates':128,'archive_byte_cap':512*1024*1024,'max_groups_per_file':4,
            'selection':'Seeded SHA256 ordering of nonexcluded IDs with >=2book events in each cached April21 identity chunk; first20 exact Yes/No mappings with start before sample and scheduled end beyond final sample. No price/performance selection.',
            'seed':'EventX-week-pilot-v1:','selection_population_bias':'First sorted-market row group of two April21 hours; availability-conditioned convenience sample, not market-universe representative. Five prior markets have exposed source diagnostics.',
            'metadata':'Current identity/rules only; current status never proves historical status. Event identity projected without prices/outcomes.',
            'protected_periods_read':False,'excluded_id_count':len(excluded),'scope':'April-only mixed chunks; excluded cohort rows physically decoded then filtered before retained economic analysis.',
            'quality':'Unique same-receipt top pair; 0<bid<=ask<1;spread<=.05;source and receipt age<=120s. Any unknown/ambiguous state resets until unambiguous quote. No depth imputation.',
            'grid':'12:30 through13:25 inclusive every5m each day;30m history and forward coverage inside two-hour daily slice.',
            'missing':'Failed/absent files or markets remain missing; no market replacements. Per-file failures retained; no automatic retries in this version.',
            'model_scoring':False,'fully_admitted_forecasts':0,'historical_status_verified':False}
    write(REL/'policy.json',policy)
    paths=[Path(__file__).resolve(),EX,PARENT/'manifest.json',REL/'policy.json',REL/'candidates_before_metadata.json',REPO_ROOT/'eventx/v7/archive_ranges_20261024.py']
    write(REL/'implementation_manifest.json',{'files':{str(p.relative_to(REPO_ROOT)):sha(p) for p in paths}})
    chosen=[];receipts=[]
    try:
        with httpx.Client(timeout=30) as client:
            for cid in candidates:
                rec={'market_id':cid,'lookups':[]}
                try:
                    raw=[]
                    for query in [{'condition_ids':cid},{'condition_ids':cid,'closed':'true'}]:
                        r=client.get('https://gamma-api.polymarket.com/markets',params=query)
                        rec['lookups'].append({'at':now().isoformat(),'query':query,'http_status':r.status_code,'body_sha256':hashlib.sha256(r.content).hexdigest()})
                        r.raise_for_status();raw=r.json()
                        if raw!=[]:break
                    if not isinstance(raw,list) or len(raw)!=1 or raw[0].get('conditionId')!=cid:raise ValueError('identity mismatch')
                    m=raw[0];tokens=m.get('clobTokenIds');outcomes=m.get('outcomes')
                    if isinstance(tokens,str):tokens=json.loads(tokens)
                    if isinstance(outcomes,str):outcomes=json.loads(outcomes)
                    keep={k:m.get(k) for k in ['question','description','startDate','endDate','active','closed','acceptingOrders','slug']}
                    keep.update(market_id=cid,token_ids=tokens,outcomes=outcomes,events=[{k:e.get(k) for k in ['id','title','slug']} for e in m.get('events',[])])
                    rec['metadata']=keep
                    end=datetime.fromisoformat(m['endDate'].replace('Z','+00:00'));start=datetime.fromisoformat(m['startDate'].replace('Z','+00:00'))
                    valid=outcomes==['Yes','No'] and isinstance(tokens,list) and len(tokens)==2 and bool(m.get('description')) and start<datetime(2026,4,21,12,tzinfo=timezone.utc) and end>datetime(2026,4,27,14,tzinfo=timezone.utc)
                    rec['selected']=valid
                    if valid:chosen.append(keep)
                except Exception as e:rec['error']=type(e).__name__
                receipts.append(rec);write(BASE/'metadata_receipts.json',receipts)
                if len(chosen)>=20:break
        if not chosen:raise RuntimeError('No eligible metadata')
        write(REL/'selected_markets.json',{'at':now().isoformat(),'markets':chosen,'selected_before_new_economic_reads':True})
        paths=[REL/'implementation_manifest.json',REL/'selected_markets.json',BASE/'metadata_receipts.json']
        write(REL/'selection_manifest.json',{'files':{str(p.relative_to(REPO_ROOT)):sha(p) for p in paths}})
        print(json.dumps({'phase':'prepared','selected':len(chosen),'looked_up':len(receipts),'candidate_count':len(candidates)}),flush=True)
    except Exception as e:
        write(BASE/'preparation_failure.json',{'at':now().isoformat(),'error':type(e).__name__});raise


def coverage(rows,cid,date,available):
    start=datetime.fromisoformat(date+'T12:00:00+00:00').timestamp();groups=defaultdict(list)
    for r in rows:groups[r['timestamp_received']].append(r)
    states=[];reasons=Counter()
    for received,rs in sorted(groups.items()):
        qs=[r for r in rs if r['best_bid'] is not None and r['best_ask'] is not None]
        pairs={(float(r['best_bid']),float(r['best_ask'])) for r in qs}
        reason='valid';oldest=None
        if not qs:reason='no_direct_quote'
        elif len(pairs)!=1:reason='conflicting_tie'
        else:
            b,a=next(iter(pairs));oldest=min(r['timestamp'].timestamp() for r in qs)
            if not 0<b<=a<1:reason='invalid_or_terminal_price'
            elif a-b>.05+1e-12:reason='wide_spread'
            elif any(not 0<=(received-r['timestamp']).total_seconds()<=120 for r in qs):reason='source_clock_or_age'
        reasons[reason]+=1;states.append({'at':received.timestamp(),'valid':reason=='valid','oldest':oldest})
    times=[s['at'] for s in states]
    def at(t):
        i=bisect_right(times,t)-1
        return i>=0 and states[i]['valid'] and 0<=t-times[i]<=120 and t-states[i]['oldest']<=120
    def covers(a,b):
        if not at(a):return False
        i,j=bisect_right(times,a),bisect_right(times,b);prev=states[i-1]
        for k in range(i,j):
            cur=states[k]
            if not cur['valid'] or cur['at']-prev['at']>120 or cur['at']-prev['oldest']>120:return False
            prev=cur
        return b-prev['at']<=120 and b-prev['oldest']<=120
    grids=list(range(int(start+1800),int(start+5400),300))
    return {'date':date,'market_id':cid,'files_available':available,'events':len(rows),'groups':len(states),'reasons':dict(reasons),
            'planned_grids':12,'fresh_current':sum(at(t) for t in grids) if available else 0,
            'fresh_pairs':sum(at(t) and at(t+1800) for t in grids) if available else 0,
            'continuous_forward':sum(covers(t,t+1800) for t in grids) if available else 0,
            'continuous_history_forward':sum(covers(t-1800,t+1800) for t in grids) if available else 0}


def collect():
    verify_originals();verify(REL/'implementation_manifest.json');verify(REL/'selection_manifest.json')
    selected=json.loads((REL/'selected_markets.json').read_text())['markets'];policy=json.loads((REL/'policy.json').read_text());excluded=set(json.loads(EX.read_text()))
    out=BASE/'capture';out.mkdir(exist_ok=False);store=RangeStore(out/'ranges',policy['archive_byte_cap']);file_receipts=[];daily=[]
    try:
        for date in DATES:
            daytables=[];available=True
            for hr in [12,13]:
                hour=date+f'T{hr:02d}';url='https://r2v2.pmxt.dev/polymarket_orderbook_'+hour+'.parquet';rec={'hour':hour,'at':now().isoformat()};tables=[]
                try:
                    meta,info=store.metadata(url);rec.update(size=info['size'],etag=info['etag'])
                    ix=meta.schema.names.index('market');groups=[]
                    for i in range(meta.num_row_groups):
                        stat=meta.row_group(i).column(ix).statistics
                        if not stat or not stat.has_min_max:raise RuntimeError('Market bounds missing')
                        if any(stat.min<=m['market_id'].encode()<=stat.max for m in selected):groups.append(i)
                    if len(groups)>policy['max_groups_per_file']:raise RuntimeError('Group cap exceeded')
                    rec['groups']=groups;rec['excluded_april_rows_decoded']=0
                    for i in groups:
                        t=read_columns(store,url,meta,i,COLS,'April_topquote_filter_before_analysis')
                        low=pc.min(t['timestamp_received']).as_py();high=pc.max(t['timestamp_received']).as_py()
                        hstart=datetime.fromisoformat(hour+':00:00+00:00')
                        if not hstart<=low<=high<hstart+timedelta(hours=1):raise RuntimeError('Clock outside approved hour')
                        rec['excluded_april_rows_decoded']+=pc.sum(pc.is_in(t['market'],value_set=pa.array([x.encode() for x in excluded],type=t['market'].type))).as_py()
                        mask=pc.is_in(t['market'],value_set=pa.array([m['market_id'].encode() for m in selected],type=t['market'].type));t=t.filter(mask)
                        yes={m['market_id']:m['token_ids'][0] for m in selected}
                        t=t.filter(pa.array([a==yes[c.decode()] for c,a in zip(t['market'].to_pylist(),t['asset_id'].to_pylist())],type=pa.bool_()))
                        if any(c.decode() in excluded for c in t['market'].unique().to_pylist()):raise RuntimeError('Excluded retained')
                        tables.append(t)
                    if tables:
                        t=pa.concat_tables(tables);pq.write_table(t,out/(hour+'.parquet'));daytables.append(t);rec['retained_rows']=t.num_rows
                    else:rec['retained_rows']=0
                    rec['complete']=True
                except Exception as e:
                    rec.update(error=type(e).__name__,message=str(e)[:160],complete=False);available=False
                file_receipts.append(rec);write(out/'file_receipts.json',file_receipts)
                write(BASE/'status.json',{'at':now().isoformat(),'phase':'capturing','files_attempted':len(file_receipts),'bytes':store.total,'last_file':rec})
                print(json.dumps({'hour':hour,'complete':rec['complete'],'rows':rec.get('retained_rows'),'bytes':store.total}),flush=True)
            by=defaultdict(list)
            for t in daytables:
                for r in t.to_pylist():by[r['market'].decode()].append(r)
            daily.extend(coverage(by[m['market_id']],m['market_id'],date,available) for m in selected)
            write(out/'market_day_metrics.json',daily)
        summary={'at':now().isoformat(),'selected_markets':len(selected),'dates':7,'hours_sampled':14,'full_week_capture':False,
                 'files_complete':sum(r['complete'] for r in file_receipts),'files_attempted':len(file_receipts),'archive_bytes':store.total,
                 **{k:sum(r[k] for r in daily) for k in ['events','planned_grids','fresh_current','fresh_pairs','continuous_forward','continuous_history_forward']},
                 'markets_with_continuous_windows':len({r['market_id'] for r in daily if r['continuous_history_forward']}),
                 'dates_with_continuous_windows':len({r['date'] for r in daily if r['continuous_history_forward']}),
                 'market_days_with_continuous_windows':sum(r['continuous_history_forward']>0 for r in daily),
                 'excluded_april_rows_decoded':sum(r.get('excluded_april_rows_decoded',0) for r in file_receipts),
                 'protected_period_rows_read':0,'historical_status_verified':False,'fully_admitted_forecasts':0,'performance_scored':False}
        write(out/'report.json',summary);write(BASE/'status.json',{'phase':'complete',**summary});print(json.dumps(summary,indent=2),flush=True)
    finally:
        store.client.close();paths=[p for p in out.rglob('*') if p.is_file()]+[REL/'selection_manifest.json',REL/'implementation_manifest.json']
        write(out/'manifest.json',{'files':{str(p.relative_to(REPO_ROOT)):sha(p) for p in paths}})

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('phase',choices=['prepare','collect']);args=parser.parse_args()
    prepare() if args.phase=='prepare' else collect()
