"""Full-day extension of the fixed archive cohort; bounded source-only capture."""
from concurrent.futures import ThreadPoolExecutor, as_completed
from collections import defaultdict
from datetime import datetime,timedelta
import json
from pathlib import Path
import shutil
import pyarrow as pa
import pyarrow.compute as pc
import pyarrow.parquet as pq
from eventx.tasks.run_v7_archive_week_pilot_20261025 import COLS, DATES, EX, verify, coverage
from eventx.tasks.discover_v7_direct_pilot_20261022 import REPO_ROOT,now,sha,write,verify_originals
from eventx.v7.archive_ranges_20261024 import RangeStore
from eventx.v7.archive_ranges_20261024 import read_columns

BASE=REPO_ROOT/'data/v7/archive_fullweek_20261025'
REL=REPO_ROOT/'eventx/release/v7/archive_fullweek_20261025'
PARENT=REPO_ROOT/'data/v7/archive_week_pilot_20261025/capture'
OLDREL=REPO_ROOT/'eventx/release/v7/archive_week_pilot_20261025'


def fetch(hour,selected,excluded,parent_receipts):
    out=BASE/'hours'/hour;out.mkdir(exist_ok=True)
    if (out/'manifest.json').exists():
        verify(out/'manifest.json');return json.loads((out/'receipt.json').read_text())
    # Failed partial attempts are not silently overwritten or retried.
    if (out/'started.json').exists():raise RuntimeError('Incomplete prior attempt needs new version: '+hour)
    write(out/'started.json',{'at':now().isoformat(),'hour':hour})
    rec={'hour':hour,'at':now().isoformat(),'reused':False,'archive_bytes':0,'complete':False};store=None
    try:
        if hour in parent_receipts:
            old=parent_receipts[hour];assert old['complete']
            p=PARENT/(hour+'.parquet');shutil.copyfile(p,out/'quotes.parquet')
            rec.update(reused=True,parent_receipt=old,retained_rows=pq.read_metadata(p).num_rows,complete=True,excluded_april_rows_decoded=0)
        else:
            store=RangeStore(out/'ranges',16*1024*1024)
            url='https://r2v2.pmxt.dev/polymarket_orderbook_'+hour+'.parquet';meta,info=store.metadata(url)
            rec.update(size=info['size'],etag=info['etag'],excluded_april_rows_decoded=0)
            ix=meta.schema.names.index('market');groups=[]
            for i in range(meta.num_row_groups):
                st=meta.row_group(i).column(ix).statistics
                if not st or not st.has_min_max:raise RuntimeError('Market bounds missing')
                if any(st.min<=m['market_id'].encode()<=st.max for m in selected):groups.append(i)
            if len(groups)>4:raise RuntimeError('Group cap exceeded')
            rec['groups']=groups;tables=[];yes={m['market_id']:m['token_ids'][0] for m in selected}
            for i in groups:
                t=read_columns(store,url,meta,i,COLS,'April_topquote_filter_before_analysis')
                lo=pc.min(t['timestamp_received']).as_py();hi=pc.max(t['timestamp_received']).as_py();start=datetime.fromisoformat(hour+':00:00+00:00')
                if not start<=lo<=hi<start+timedelta(hours=1):raise RuntimeError('Receipt outside approved hour')
                rec['excluded_april_rows_decoded']+=pc.sum(pc.is_in(t['market'],value_set=pa.array([x.encode() for x in excluded],type=t['market'].type))).as_py()
                t=t.filter(pc.is_in(t['market'],value_set=pa.array([x.encode() for x in yes],type=t['market'].type)))
                t=t.filter(pa.array([a==yes[c.decode()] for c,a in zip(t['market'].to_pylist(),t['asset_id'].to_pylist())],type=pa.bool_()))
                assert not {x.decode() for x in t['market'].unique().to_pylist()}&excluded
                tables.append(t)
            if tables:
                panel=pa.concat_tables(tables);pq.write_table(panel,out/'quotes.parquet');rec['retained_rows']=panel.num_rows
            else:rec['retained_rows']=0
            rec['complete']=True
    except Exception as e:rec.update(error=type(e).__name__,message=str(e)[:180])
    finally:
        if store:rec['archive_bytes']=store.total;store.client.close()
        rec['finished_at']=now().isoformat();write(out/'receipt.json',rec)
        paths=[p for p in out.rglob('*') if p.is_file()]
        write(out/'manifest.json',{'files':{str(p.relative_to(REPO_ROOT)):sha(p) for p in paths}})
    return rec


def main():
    verify_originals();verify(REL/'implementation_manifest.json');verify(OLDREL/'selection_manifest.json');verify(PARENT/'manifest.json')
    BASE.mkdir(exist_ok=True);(BASE/'hours').mkdir(exist_ok=True)
    selected=json.loads((OLDREL/'selected_markets.json').read_text())['markets'];excluded=set(json.loads(EX.read_text()))
    prs={r['hour']:r for r in json.loads((PARENT/'file_receipts.json').read_text())}
    hours=[d+f'T{h:02d}' for d in DATES for h in range(24)];receipts=[]
    write(BASE/'status.json',{'at':now().isoformat(),'phase':'capturing','pid':__import__('os').getpid(),'completed':0,'scheduled':168})
    with ThreadPoolExecutor(max_workers=2) as pool:
        futures={pool.submit(fetch,h,selected,excluded,prs):h for h in hours}
        for future in as_completed(futures):
            try:r=future.result()
            except Exception as e:r={'hour':futures[future],'complete':False,'error':type(e).__name__,'message':str(e)[:180],'archive_bytes':0}
            receipts.append(r);status={'at':now().isoformat(),'phase':'capturing','pid':__import__('os').getpid(),'completed':len(receipts),'successful':sum(x['complete'] for x in receipts),'scheduled':168,'new_archive_bytes':sum(x['archive_bytes'] for x in receipts),'last_hour':r['hour'],'last_success':r['complete']}
            write(BASE/'status.json',status);write(BASE/'file_receipts.json',sorted(receipts,key=lambda r:r['hour']))
            if len(receipts)%12==0 or not r['complete']:print(json.dumps(status),flush=True)
    summary={'at':now().isoformat(),'phase':'captured','scheduled_files':168,'successful_files':sum(r['complete'] for r in receipts),'reused_files':sum(r.get('reused',False) for r in receipts),'new_archive_bytes':sum(r['archive_bytes'] for r in receipts),'retained_events':sum(r.get('retained_rows',0) for r in receipts),'new_excluded_april_rows_decoded':sum(r.get('excluded_april_rows_decoded',0) for r in receipts),'protected_period_rows_read':0,'models_scored':False}
    write(BASE/'capture_report.json',summary);write(BASE/'status.json',summary)
    paths=[BASE/'capture_report.json',BASE/'file_receipts.json',REL/'implementation_manifest.json']+list((BASE/'hours').glob('*/manifest.json'))
    write(BASE/'capture_manifest.json',{'files':{str(p.relative_to(REPO_ROOT)):sha(p) for p in paths}})
    print(json.dumps(summary,indent=2),flush=True)

if __name__=='__main__':main()
