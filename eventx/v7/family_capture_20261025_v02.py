"""Reusable bounded data operations for calibration/transport v01; frozen predecessors intact."""
from bisect import bisect_right
from collections import defaultdict
from datetime import datetime,timedelta,timezone
import json,shutil
from pathlib import Path
import numpy as np
import pyarrow as pa
import pyarrow.compute as pc
import pyarrow.parquet as pq
from eventx.tasks.evaluate_v7_observational_quotes_20261025 import states_from,grids_for
from eventx.tasks.research_v7_change_probability_20261025 import FEATURES
from eventx.tasks.run_v7_archive_week_pilot_20261025 import COLS,verify
from eventx.v7.archive_ranges_20261024 import RangeStore,read_columns
from eventx.tasks.discover_v7_direct_pilot_20261022 import REPO_ROOT,now,sha,write


def fetch(hour,selected,excluded,base):
    out=base/'hours'/hour;out.mkdir(exist_ok=True)
    if (out/'manifest.json').exists():
        verify(out/'manifest.json');return json.loads((out/'receipt.json').read_text())
    # Failed partial attempts are not silently overwritten or retried.
    if (out/'started.json').exists():raise RuntimeError('Incomplete prior attempt needs new version: '+hour)
    write(out/'started.json',{'at':now().isoformat(),'hour':hour})
    rec={'hour':hour,'at':now().isoformat(),'reused':False,'archive_bytes':0,'complete':False};store=None
    try:
        store=RangeStore(out/'ranges',32*1024*1024)
        url='https://r2v2.pmxt.dev/polymarket_orderbook_'+hour+'.parquet';meta,info=store.metadata(url)
        rec.update(size=info['size'],etag=info['etag'],excluded_pre_holdout_rows_decoded=0)
        ix=meta.schema.names.index('market');groups=[]
        for i in range(meta.num_row_groups):
            st=meta.row_group(i).column(ix).statistics
            if not st or not st.has_min_max:raise RuntimeError('Market bounds missing')
            if any(st.min<=m['market_id'].encode()<=st.max for m in selected):groups.append(i)
        if len(groups)>8:raise RuntimeError('Group cap exceeded')
        rec['groups']=groups;tables=[];yes={m['market_id']:m['token_ids'][0] for m in selected}
        for i in groups:
            t=read_columns(store,url,meta,i,COLS,'May_pre_holdout_topquote_filter_before_analysis')
            lo=pc.min(t['timestamp_received']).as_py();hi=pc.max(t['timestamp_received']).as_py();start=datetime.fromisoformat(hour+':00:00+00:00')
            if not start<=lo<=hi<start+timedelta(hours=1):raise RuntimeError('Receipt outside approved hour')
            rec['excluded_pre_holdout_rows_decoded']+=pc.sum(pc.is_in(t['market'],value_set=pa.array([x.encode() for x in excluded],type=t['market'].type))).as_py()
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

