"""Protected-scope-first bounded metadata/identity inspection; no price columns."""
from collections import Counter
import hashlib
import json
from pathlib import Path
import uuid
import pyarrow
from eventx.tasks.discover_v7_direct_pilot_20261022 import REPO_ROOT,now,sha,write,verify_originals
from eventx.v7.archive_ranges_20261024 import RangeStore,read_columns

BASE=REPO_ROOT/'data/v7/archive_compatibility_20261024'
RELEASE=REPO_ROOT/'eventx/release/v7/archive_compatibility_20261024'
HOURS=['2026-04-21T12','2026-04-21T13']

def main():
    verify_originals();BASE.mkdir(exist_ok=True)
    if not RELEASE.exists():
        RELEASE.mkdir()
        v1=REPO_ROOT/'data/v1/toy/selected_markets.jsonl';v3=REPO_ROOT/'data/v3_1_historical/primary/label_blind_inputs/cohort.jsonl';v4=REPO_ROOT/'eventx/release/v7/market_capture_20261018/protected_ids.json'
        if sha(v1)!=json.loads((REPO_ROOT/'data/v1_oot_20260723_20260730/frozen_holdout_manifest.json').read_text())['artifacts']['frozen_cohort']['sha256']:raise RuntimeError('v1 cohort drift')
        if sha(v3)!=json.loads((REPO_ROOT/'eventx/release/v3_1_historical_primary/protocol.json').read_text())['cohort']['sha256']:raise RuntimeError('v3 cohort drift')
        ids=set(json.loads(v4.read_text()))
        for p in [v1,v3]:
            for line in p.read_text().splitlines():
                r=json.loads(line)
                if r['venue']=='polymarket':ids.add(r['market_id'])
        write(RELEASE/'excluded_market_ids.json',sorted(ids))
        write(RELEASE/'policy.json',{'at':now().isoformat(),'scope':'Bounded external archive compatibility audit; no model fitting or protected evaluation',
            'hours':HOURS,'date_rule':'April sample precedes v1 development and all protected evaluation periods',
            'excluded_market_count':len(ids),'exclusion':'Conservative entire-market union of v1,v3.1 cohort and470V4contracts',
            'metadata_columns':['market','asset_id','event_type','timestamp_received','timestamp'],
            'phase_one':'Footer and identity/event-type columns only; no price/size/book columns',
            'phase_two':'Only row groups whose actual identity column contains zero excluded markets, then freeze allowed market IDs before economic columns',
            'scan_limit_groups_per_hour':40,'select_limit_groups_per_hour':2,'max_bytes_per_attempt':96*1024*1024,
            'selection':'First row groups in sorted file order without excluded IDs; structural compatibility sample, not representative or selected by prediction outcomes',
            'intended_phase_two_markets':5,'models_scored':False,'target_labels_built':False,'source':'https://r2v2.pmxt.dev/',
            'limitations':'Metadata/status at historical decision time unknown; file presence not completeness; timestamps may tie',
            'pyarrow_version':pyarrow.__version__})
        paths=list(RELEASE.iterdir())+[v1,v3,v4,Path(__file__).resolve(),REPO_ROOT/'eventx/v7/archive_ranges_20261024.py']
        write(RELEASE/'implementation_manifest.json',{'locked_files':{str(p.relative_to(REPO_ROOT)):sha(p) for p in paths}})
    for p,h in json.loads((RELEASE/'implementation_manifest.json').read_text())['locked_files'].items():
        if sha(REPO_ROOT/p)!=h:raise RuntimeError('Audit freeze drift')
    out=BASE/('metadata_'+now().strftime('%Y%m%dT%H%M%SZ')+'_'+uuid.uuid4().hex[:6]);out.mkdir()
    policy=json.loads((RELEASE/'policy.json').read_text());excluded=set(json.loads((RELEASE/'excluded_market_ids.json').read_text()))
    store=RangeStore(out/'ranges',policy['max_bytes_per_attempt']);reports=[];error=None
    try:
        for hour in HOURS:
            url='https://r2v2.pmxt.dev/polymarket_orderbook_'+hour+'.parquet';meta,info=store.metadata(url)
            schema=[{'name':meta.schema.column(i).path,'physical_type':meta.schema.column(i).physical_type,'logical_type':str(meta.schema.column(i).logical_type)} for i in range(meta.num_columns)]
            hreport={'hour':hour,'url':url,'object_size':info['size'],'etag':info.get('etag'),'file_rows':meta.num_rows,'row_groups':meta.num_row_groups,'schema':schema,'scanned_groups':[],'selected_groups':[]}
            reports.append(hreport);retained=0
            for g in range(min(meta.num_row_groups,policy['scan_limit_groups_per_hour'])):
                table=read_columns(store,url,meta,g,['market'],'identity_scan')
                ids={x.decode() if isinstance(x,bytes) else x for x in table['market'].unique().to_pylist()}
                overlap=ids&excluded
                item={'group':g,'rows':len(table),'market_count':len(ids),'protected_overlap_count':len(overlap)};hreport['scanned_groups'].append(item)
                if overlap:continue
                # Only after the full ID scan establishes a protected-free group.
                cols=['market','asset_id','event_type','timestamp_received','timestamp']
                table=read_columns(store,url,meta,g,cols,'protected_free_identity_and_clocks')
                import pyarrow.parquet as pq
                pq.write_table(table,out/(hour+'_rg'+str(g)+'_identity.parquet'))
                item['event_types']=dict(Counter(table['event_type'].to_pylist()))
                item['allowed_market_ids']=sorted(ids)
                hreport['selected_groups'].append(item);retained+=1
                if retained>=policy['select_limit_groups_per_hour']:break
            write(out/(hour+'_metadata.json'),hreport)
    except Exception as exc:error=type(exc).__name__;raise
    finally:
        store.client.close()
        report={'at':now().isoformat(),'phase':'metadata_identity_only','error_type':error,'hours':reports,'bytes_downloaded':store.total,
            'excluded_market_count':len(excluded),'economic_columns_read':False,'protected_price_rows_read':False,'models_scored':False}
        write(out/'report.json',report)
        paths=[p for p in out.rglob('*') if p.is_file()]+[RELEASE/'implementation_manifest.json'];write(out/'manifest.json',{'files':{str(p.relative_to(REPO_ROOT)):sha(p) for p in paths}})
        print(json.dumps({'directory':str(out.relative_to(REPO_ROOT)),'bytes':store.total,'error_type':error,
            'hours':[{'hour':r['hour'],'file_rows':r['file_rows'],'scanned':len(r['scanned_groups']),'selected':len(r['selected_groups'])} for r in reports]},indent=2))

if __name__=='__main__':main()
