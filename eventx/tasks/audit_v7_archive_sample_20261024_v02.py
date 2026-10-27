"""April-only source audit with row-level cohort exclusion before economic analysis."""
from bisect import bisect_right
from collections import Counter,defaultdict
from datetime import datetime,timezone
import json
import math
from pathlib import Path
import uuid
import numpy as np
import pyarrow as pa
import pyarrow.compute as pc
import pyarrow.parquet as pq
from eventx.tasks.discover_v7_direct_pilot_20261022 import REPO_ROOT,now,sha,write,verify_originals
from eventx.v7.archive_ranges_20261024 import RangeStore,read_columns

BASE=REPO_ROOT/'data/v7/archive_sample_20261024_v02'
RELEASE=REPO_ROOT/'eventx/release/v7/archive_sample_20261024_v02'
PARENT=REPO_ROOT/'data/v7/archive_compatibility_20261024/metadata_20261024T144333Z_f4cf4b'
HOURS=['2026-04-21T12','2026-04-21T13']
START=datetime(2026,4,21,12,tzinfo=timezone.utc).timestamp();END=START+7200

def levels(raw):
    v=json.loads(raw) if isinstance(raw,str) else raw
    if not isinstance(v,list):raise ValueError('Unexpected depth shape')
    result={}
    for z in v:
        p,q=(z['price'],z['size']) if isinstance(z,dict) else z
        p,q=float(p),float(q)
        if not math.isfinite(p) or not math.isfinite(q) or not 0<=p<=1 or q<0:raise ValueError('Invalid level')
        if q>0:result[p]=result.get(p,0)+q
    return result

def touch(bids,asks):
    if not bids or not asks:return None
    b=max(bids);a=min(asks);qb=bids[b];qa=asks[a]
    return (b,a,qb,qa)

def replay(rows):
    bids=asks=None;interval_updates=0;interval_ties=False;last_snapshot=None;snaps=[];comparisons=[];counts=Counter();groups=defaultdict(list)
    for r in rows:groups[r['timestamp_received']].append(r)
    for received,group in sorted(groups.items()):
        updates=[r for r in group if r['event_type']=='price_change'];books=[r for r in group if r['event_type']=='book']
        ukeys=[(r.get('side'),str(r.get('price'))) for r in updates]
        conflicting=any(len({str(r.get('size')) for r in updates if (r.get('side'),str(r.get('price')))==k})>1 for k in set(ukeys))
        if len(group)>1:counts['receive_time_tie_groups']+=1
        if conflicting or (books and updates):interval_ties=True;counts['ambiguous_receive_time_groups']+=1
        for r in books:
            counts['book_rows']+=1
            try:b,a=levels(r['bids']),levels(r['asks'])
            except (ValueError,TypeError,KeyError,json.JSONDecodeError):counts['invalid_snapshot_encoding']+=1;continue
            t=touch(b,a);quality=bool(t and 0<t[0]<=t[1]<1 and t[1]-t[0]<=.05+1e-12 and min(t[2:])>=10)
            if last_snapshot is not None:
                old=touch(bids,asks);same=bool(old and t and all(abs(x-y)<1e-9 for x,y in zip(old,t)))
                comparisons.append({'from':last_snapshot.isoformat(),'to':received.isoformat(),'updates':interval_updates,'ambiguous_tie':interval_ties,
                    'touch_matches':same,'full_book_matches':bids==b and asks==a})
            source=r['timestamp'];lag=(received-source).total_seconds()
            snaps.append({'received_at':received.isoformat(),'source_at':source.isoformat(),'lag_seconds':lag,'quality':quality,'touch':t,
                'midpoint':(t[0]+t[1])/2 if t else None})
            if quality:counts['quality_snapshots']+=1
            if t and t[0]>t[1]:counts['crossed_snapshots']+=1
            if lag<0:counts['future_source_timestamp_snapshots']+=1
            bids,asks=b,a;last_snapshot=received;interval_updates=0;interval_ties=False
        # This is a diagnostic replay assumption, never a certified reconstruction.
        for r in updates:
            if bids is None:counts['unseeded_updates']+=1;continue
            try:
                side=r['side'];p=float(r['price']);q=float(r['size'])
                if side not in ['BUY','SELL'] or not all(math.isfinite(x) for x in [p,q]) or not 0<=p<=1 or q<0:raise ValueError()
                book=bids if side=='BUY' else asks
                if q==0:book.pop(p,None)
                else:book[p]=q
                interval_updates+=1
            except (ValueError,TypeError,KeyError):counts['invalid_updates']+=1
    return snaps,comparisons,dict(counts)

def main():
    verify_originals();BASE.mkdir(exist_ok=True)
    for p,h in json.loads((PARENT/'manifest.json').read_text())['files'].items():
        if sha(REPO_ROOT/p)!=h:raise RuntimeError('Parent audit drift')
    if not RELEASE.exists():
        RELEASE.mkdir();ex=REPO_ROOT/'eventx/release/v7/archive_compatibility_20261024/excluded_market_ids.json'
        (RELEASE/'excluded_market_ids.json').write_bytes(ex.read_bytes())
        policy={'at':now().isoformat(),'scope':'New V7 external archive source audit, not EventX v2 research or a model evaluation',
            'hours':HOURS,'allowed_clock_interval':['2026-04-21T12:00:00Z','2026-04-21T14:00:00Z'],
            'protected_periods_not_read':['v1 OOT July23–30 plus July22warmup','v3.1 July22–Aug8','v4 Sep6–Oct30'],
            'scope_correction':'V01 entire-row-group exclusion found zero usable groups. April predates all frozen evaluations; V02 permits mixed April column chunks and excludes cohort IDs before economic analysis/retained rows.',
            'excluded_id_count':len(json.loads(ex.read_text())),'physical_read_note':'Arrow may decode excluded-market April column values; no held-out period is read. Those April rows are not inspected, analyzed or retained in the selected panel.',
            'groups_per_hour':[0],'max_metadata_candidates':16,'max_selected_markets':5,'max_bytes':96*1024*1024,
            'selection':'Sorted nonexcluded condition IDs common to both hours, excluding row-group boundary IDs; at least2book events in identity-only data; current metadata has exact binary mapping and scheduled end beyond sample',
            'current_metadata':'Only identity/question/rules/token/end/status projection retained; present status is not historical status proof',
            'replay':'Diagnostic level-update assumption; ambiguous ties/missing updates prevent exact replay certification',
            'forecast_eligibility':'Snapshot-only receipt-age<=120s and observed-quality coverage; historical status unavailable =>zero fully admitted forecasts',
            'models_fitted_or_scored':False,'performance_labels_constructed':False,'byte_budget_is_per_attempt':True}
        write(RELEASE/'policy.json',policy)
        paths=list(RELEASE.iterdir())+[PARENT/'manifest.json',Path(__file__).resolve(),REPO_ROOT/'eventx/v7/archive_ranges_20261024.py']
        write(RELEASE/'implementation_manifest.json',{'locked_files':{str(p.relative_to(REPO_ROOT)):sha(p) for p in paths}})
    for p,h in json.loads((RELEASE/'implementation_manifest.json').read_text())['locked_files'].items():
        if sha(REPO_ROOT/p)!=h:raise RuntimeError('Sample policy drift')
    policy=json.loads((RELEASE/'policy.json').read_text());excluded=set(json.loads((RELEASE/'excluded_market_ids.json').read_text()))
    out=BASE/('attempt_'+now().strftime('%Y%m%dT%H%M%SZ')+'_'+uuid.uuid4().hex[:6]);out.mkdir()
    store=RangeStore(out/'ranges',policy['max_bytes']);meta_by={};ids_by={};identity_by={};metadata_receipts=[];selected=[];error=None;summary={}
    try:
        # Freeze market allowlist from identity/event coverage and metadata before any economic column requests.
        for hour in HOURS:
            url='https://r2v2.pmxt.dev/polymarket_orderbook_'+hour+'.parquet';meta,info=store.metadata(url)
            old=json.loads((PARENT/(hour+'_metadata.json')).read_text())
            if info['etag']!=old['etag'] or info['size']!=old['object_size']:raise RuntimeError('Archive object changed since metadata audit')
            meta_by[hour]=(url,meta);cols=['market','asset_id','event_type','timestamp_received','timestamp']
            table=read_columns(store,url,meta,0,cols,'identity_clocks_only')
            clocks=table['timestamp_received'];lo=pc.min(clocks).as_py().timestamp();hi=pc.max(clocks).as_py().timestamp()
            if not START<=lo<=hi<END:raise RuntimeError('Receipt time outside April allowlist')
            identity_by[hour]=table
            bids=table.filter(pc.equal(table['event_type'],'book'))
            counts=Counter(v.decode() for v in bids['market'].to_pylist());allids=sorted({v.decode() for v in table['market'].unique().to_pylist()})
            ids_by[hour]={c for c,n in counts.items() if n>=2 and c not in excluded and c not in [allids[0],allids[-1]]}
        candidates=sorted(set.intersection(*ids_by.values()))[:policy['max_metadata_candidates']]
        write(out/'candidate_ids_before_prices.json',candidates)
        for cid in candidates:
            receipt={'at':now().isoformat(),'market_id':cid,'url':'https://gamma-api.polymarket.com/markets','query':{'condition_ids':cid}}
            try:
                response=store.client.get(receipt['url'],params=receipt['query']);receipt['http_status']=response.status_code;response.raise_for_status()
                raw=response.json();receipt['raw_response_sha256']=__import__('hashlib').sha256(response.content).hexdigest()
                if not isinstance(raw,list) or len(raw)!=1 or raw[0].get('conditionId')!=cid:raise ValueError('Metadata identity')
                m=raw[0];tokens=m.get('clobTokenIds');outcomes=m.get('outcomes')
                if isinstance(tokens,str):tokens=json.loads(tokens)
                if isinstance(outcomes,str):outcomes=json.loads(outcomes)
                keep={k:m.get(k) for k in ['question','description','startDate','endDate','active','closed','acceptingOrders']};keep.update(market_id=cid,clob_token_ids=tokens,outcomes=outcomes,metadata_received_at=now().isoformat())
                receipt['metadata']=keep
                end=datetime.fromisoformat(m['endDate'].replace('Z','+00:00')).timestamp() if m.get('endDate') else 0
                valid=bool(outcomes==['Yes','No'] and isinstance(tokens,list) and len(tokens)==2 and end>END and m.get('description'))
                receipt['selected']=valid
                if valid:selected.append(keep)
            except Exception as exc:receipt['error_type']=type(exc).__name__
            metadata_receipts.append(receipt)
            if len(selected)>=policy['max_selected_markets']:break
        write(out/'metadata_receipts.json',metadata_receipts);write(out/'selected_before_economic_reads.json',{'at':now().isoformat(),'markets':selected,'holdout_overlap':0})
        if not selected:raise RuntimeError('No metadata-compatible candidates')
        allow={r['market_id'] for r in selected};yes={r['market_id']:r['clob_token_ids'][0] for r in selected};tables=[];excluded_rows_decoded=0
        cols=['market','asset_id','event_type','timestamp_received','timestamp','bids','asks','price','size','side','best_bid','best_ask']
        for hour in HOURS:
            url,meta=meta_by[hour];table=read_columns(store,url,meta,0,cols,'April_only_mixed_columns_then_allowlist_filter')
            excluded_rows_decoded+=sum(v.decode() in excluded for v in table['market'].to_pylist())
            mask=pc.is_in(table['market'],value_set=pa.array([c.encode() for c in allow],type=table['market'].type));table=table.filter(mask)
            mask=pa.array([a==yes[c.decode()] for c,a in zip(table['market'].to_pylist(),table['asset_id'].to_pylist())]);table=table.filter(mask)
            # No excluded April market reaches a retained economic row.
            if any(c.decode() in excluded for c in table['market'].unique().to_pylist()):raise RuntimeError('Excluded row retained')
            tables.append(table)
        panel=pa.concat_tables(tables);pq.write_table(panel,out/'selected_yes_events.parquet');rows=panel.to_pylist()
        by=defaultdict(list)
        for r in rows:
            r['market']=r['market'].decode();by[r['market']].append(r)
        metrics=[];snapshots=[];replays=[]
        for cid,rr in sorted(by.items()):
            rr.sort(key=lambda r:r['timestamp_received']);ss,cc,counts=replay(rr)
            snapshots.extend([{'market_id':cid,**s} for s in ss]);replays.extend([{'market_id':cid,**c} for c in cc])
            times=[datetime.fromisoformat(s['received_at']).timestamp() for s in ss];gaps=np.diff(times)
            def at(t):
                i=bisect_right(times,t)-1
                return ss[i] if i>=0 and ss[i]['quality'] and ss[i]['lag_seconds']>=0 and 0<=t-times[i]<=120 else None
            def covers(a,b):
                if not at(a):return False
                i=bisect_right(times,a);j=bisect_right(times,b);prev=times[i-1]
                for n in range(i,j):
                    if not ss[n]['quality'] or ss[n]['lag_seconds']<0 or times[n]-prev>120:return False
                    prev=times[n]
                return b-prev<=120
            grids=list(range(int(START+1800),int(END-1800),300));current=sum(at(t) is not None for t in grids)
            paired=sum(at(t) is not None and at(t+1800) is not None for t in grids)
            history=sum(covers(t-1800,t) for t in grids);full=sum(covers(t-1800,t+1800) for t in grids)
            lag=[s['lag_seconds'] for s in ss];clear=[c for c in cc if not c['ambiguous_tie']]
            metrics.append({'market_id':cid,'question':next(r['question'] for r in selected if r['market_id']==cid),'events':len(rr),
                'event_types':dict(Counter(r['event_type'] for r in rr)),**counts,'snapshot_gap_seconds':{'median':float(np.median(gaps)),'max':float(max(gaps))} if len(gaps) else None,
                'snapshot_source_lag_seconds':{'min':min(lag),'median':float(np.median(lag)),'max':max(lag)} if lag else None,
                'grid_count':len(grids),'fresh_current_snapshot_grids':current,'fresh_paired_snapshot_grids':paired,'continuous_30m_history_grids':history,
                'continuous_history_and_forward_grids':full,'replay_intervals':len(cc),'unambiguous_replay_intervals':len(clear),
                'unambiguous_touch_matches':sum(c['touch_matches'] for c in clear),'unambiguous_full_book_matches':sum(c['full_book_matches'] for c in clear)})
        (out/'snapshots.jsonl').write_text(''.join(json.dumps(r,sort_keys=True)+'\n' for r in snapshots));write(out/'replay_intervals.json',replays);write(out/'market_metrics.json',metrics)
        summary={'selected_markets':len(selected),'retained_yes_events':len(rows),'event_types':dict(Counter(r['event_type'] for r in rows)),
            'snapshots':len(snapshots),'quality_snapshots':sum(s['quality'] for s in snapshots),'planned_grids':sum(m['grid_count'] for m in metrics),
            'fresh_paired_snapshot_grids':sum(m['fresh_paired_snapshot_grids'] for m in metrics),'continuous_history_and_forward_grids':sum(m['continuous_history_and_forward_grids'] for m in metrics),
            'fully_forecast_eligible':0,'historical_status_verified':False,'exact_replay_certified':False,'excluded_April_rows_decoded_but_not_analyzed_or_retained':excluded_rows_decoded,
            'protected_evaluation_period_rows_read':0,'models_fitted_or_scored':False,'forecast_performance_computed':False}
    except Exception as exc:error=type(exc).__name__;raise
    finally:
        store.client.close();write(out/'report.json',{'at':now().isoformat(),'error_type':error,'bytes_downloaded':store.total,**summary})
        paths=[p for p in out.rglob('*') if p.is_file()]+[RELEASE/'implementation_manifest.json'];write(out/'manifest.json',{'files':{str(p.relative_to(REPO_ROOT)):sha(p) for p in paths}})
        print(json.dumps({'directory':str(out.relative_to(REPO_ROOT)),'error_type':error,'bytes':store.total,**summary},indent=2))

if __name__=='__main__':main()
