"""Training-only arithmetic parity and label-blind live-input replay. No scoring."""
from collections import Counter,defaultdict
from datetime import datetime,timezone
from pathlib import Path
import json
import numpy as np
import pyarrow as pa
import pyarrow.parquet as pq
from eventx.tasks.discover_v7_direct_pilot_20261022 import REPO_ROOT,now,sha,write,verify_originals
from eventx.tasks.run_v7_archive_week_pilot_20261025 import verify
from eventx.tasks.audit_v7_quote_shadow_20261024 import chain
from eventx.v7.live_quote_inputs_20261026 import FeatureTape,project_ws,transport_ready,InputCompatibilityError,FEATURES
from eventx.v7.memory_quote_20261024 import MemoryQuoteTape
from eventx.v7.quote_experiment_20261024 import stamp
BASE=REPO_ROOT/'data/v7/live_input_compatibility_20261026'
DEV=REPO_ROOT/'data/v7/family_training_20261025_v02'
SRC=REPO_ROOT/'data/v7/quote_source_20261024_v02/live'
REL=REPO_ROOT/'eventx/release/v7/live_input_compatibility_20261026'

def main():
 if (BASE/'report.json').exists():raise RuntimeError('Audit exists; create a new version')
 verify_originals();verify(DEV/'development/manifest.json');verify(DEV/'source_dev/capture_manifest.json')
 write(BASE/'audit_receipt.json',{'at':now().isoformat(),'scope':'Features only;May7–9 training inputs plus closed two-contract WS receipts','labels_read':False,'models_fit':False,'prediction_metrics_computed':False})
 # Explicit column projection excludes all target and endpoint fields.
 reference=pq.read_table(DEV/'development/grid_ledger.parquet',columns=['market_id','date','t','current_valid','features']).to_pylist()
 cohorts=json.loads((DEV/'cohort/cohorts.json').read_text());good={r['hour'] for r in json.loads((DEV/'source_dev/file_receipts.json').read_text()) if r['complete']}
 parity=[];archive_types=Counter();archive_nulls=Counter();multiplicity=[];source_spans=[];max_error=0.;all_train=[]
 for date in ['2026-05-07','2026-05-08','2026-05-09']:
  by=defaultdict(list)
  for h in range(24):
   folder=DEV/'source_dev/hours'/(date+f'T{h:02}');verify(folder/'manifest.json')
   for r in pq.read_table(folder/'quotes.parquet').to_pylist():
    by[r['market'].decode()].append(r);archive_types[r['event_type']]+=1;archive_nulls[r['event_type']]+=r['best_bid'] is None or r['best_ask'] is None
  nvalid=0
  for m in cohorts['development50']:
   rr=by[m['market_id']];tape=FeatureTape(rr,good)
   groups=defaultdict(list)
   for x in rr:groups[x['timestamp_received']].append(x['timestamp'].timestamp())
   for values in groups.values():multiplicity.append(len(values));source_spans.append(max(values)-min(values))
   for ref in [r for r in reference if r['date']==date and r['market_id']==m['market_id']]:
    f=tape.model_inputs(ref['t']);assert (f is not None)==ref['current_valid']
    if f is not None:
     err=float(np.max(np.abs(np.asarray(f)-ref['features'])));assert err<1e-12;max_error=max(max_error,err);all_train.append(f);nvalid+=1
  parity.append({'date':date,'grids':13800,'current_valid':nvalid,'passed':True});print(json.dumps(parity[-1]),flush=True)
 samples=[json.loads(x) for x in (REPO_ROOT/'eventx/release/v7/memory_quote_20261024/forward_cohort.jsonl').read_text().splitlines()]
 policy=json.loads((REPO_ROOT/'eventx/release/v7/memory_quote_20261024/policy.json').read_text());journal=chain(SRC/'journal.jsonl');tape=MemoryQuoteTape(SRC,samples,policy);tape.refresh_live()
 by=defaultdict(list);live_types=Counter();errors=[];payload_hashes={};clock_lags=[];duplicate_hashes=Counter()
 for r in journal:
  if r['kind']!='ws_frame':continue
  p=SRC/'objects'/r['payload_sha256'];assert sha(p)==r['payload_sha256'];payload_hashes[str(p.relative_to(REPO_ROOT))]=r['payload_sha256'];payload=json.loads(p.read_text())
  clock_lags.append(stamp(r['available_at'])-stamp(r['response_received_at']))
  try:projected=project_ws(payload,r['available_at'],r['response_received_at'],samples)
  except InputCompatibilityError as e:errors.append({'record':r['record_sha256'],'reason':str(e)});continue
  for row in projected:by[row['market'].decode()].append(row);live_types[row['event_type']]+=1
  for msg in payload if isinstance(payload,list) else [payload]:
   for leg in msg.get('price_changes',[]) if msg.get('event_type')=='price_change' else [msg]:
    if leg.get('hash'):duplicate_hashes[(leg.get('asset_id'),leg['hash'])]+=1
 contract=json.loads((REPO_ROOT/'data/v7/memory_quote_20261024/shadow/run_contract.json').read_text());results=[];xtrain=np.asarray(all_train);qlo=np.quantile(xtrain,.01,axis=0);qhi=np.quantile(xtrain,.99,axis=0)
 for sample in samples:
  cid=sample['market_id'];ft=FeatureTape(by[cid]);dd=[]
  for t in range(int(stamp(contract['first_grid_at'])),int(stamp(contract['last_grid_at']))+1,300):
   f=ft.features(t);ok,reasons=transport_ready(journal,t)
   meta=tape.at(cid,'market_metadata',t);resolution=tape.at(cid,'resolution_state',t)
   status_ok=bool(meta and resolution and meta['scheduled_end'] is not None and meta['scheduled_end']>t+1800)
   in_grid=1800<=t%86400<84600
   ready=f is not None and ok and status_ok and in_grid and not errors
   dd.append({'market_id':cid,'decision_at':datetime.fromtimestamp(t,timezone.utc).isoformat(),'features':f,'quote_eligible':f is not None,'transport_ready':ok,'transport_reasons':reasons,'status_ready':status_ok,'daily_grid_ready':in_grid,'mechanically_ready':ready,'frozen_model_compatible':False})
   if f is not None:
    try:ft.model_inputs(t)
    except InputCompatibilityError:pass
    else:raise AssertionError('Unverified live feed reached model input gate')
  results.extend(dd)
 # Post-projection sensitivity without model scoring: recompute grouping on wire receipt clock.
 wire_by=defaultdict(list)
 for rec in journal:
  if rec['kind']!='ws_frame':continue
  payload=json.loads((SRC/'objects'/rec['payload_sha256']).read_text())
  try:rr=project_ws(payload,rec['response_received_at'],rec['response_received_at'],samples)
  except InputCompatibilityError:continue
  for row in rr:wire_by[row['market'].decode()].append(row)
 clock_diffs=Counter()
 for s in samples:
  ft=FeatureTape(wire_by[s['market_id']])
  for r in [x for x in results if x['market_id']==s['market_id']]:
   f=ft.features(stamp(r['decision_at']));a=r['features']
   if (f is None)!=(a is None):clock_diffs['eligibility']+=1
   elif f is not None:
    for i,name in enumerate(FEATURES):clock_diffs[name]+=abs(f[i]-a[i])>1e-12
 stats=[]
 for s in samples:
  rr=[r for r in results if r['market_id']==s['market_id']];valid=[r for r in rr if r['features'] is not None]
  stats.append({'market_id':s['market_id'],'question':s['question'],'grids':len(rr),'projected_yes_events':len(by[s['market_id']]),'quote_eligible':len(valid),'mechanically_ready':sum(r['mechanically_ready'] for r in rr),'frozen_model_admissions':0})
 valid=[r['features'] for r in results if r['features'] is not None];distribution=[]
 for i,name in enumerate(FEATURES):
  v=np.asarray([r[i] for r in valid]);distribution.append({'feature':name,'training_p01':float(qlo[i]),'training_p99':float(qhi[i]),'training_median':float(np.median(xtrain[:,i])),'live_median':float(np.median(v)) if len(v) else None,'live_outside_training_p01_p99':int(((v<qlo[i])|(v>qhi[i])).sum()),'live_n':len(v)})
 report={'at':now().isoformat(),'arithmetic_parity_passed':True,'parity':parity,'feature_vectors_matched':len(all_train),'max_abs_error':max_error,'archive_event_counts':dict(archive_types),'archive_null_quote_counts':dict(archive_nulls),'archive_receipt_groups':len(multiplicity),'archive_multirow_receipt_groups':sum(n>1 for n in multiplicity),'archive_group_max_rows':max(multiplicity),'archive_group_source_span_max_seconds':max(source_spans),'live_projected_event_counts':dict(live_types),'parse_errors':errors,'live_market_coverage':stats,'feature_distribution_diagnostic':distribution,'wire_vs_durable_feature_differences':dict(clock_diffs),'durability_delay_max_seconds':max(clock_lags),'repeated_asset_hash_occurrences':sum(n-1 for n in duplicate_hashes.values()),'readiness':'BLOCKED_CLOCK_AND_DEDUP_EQUIVALENCE_UNVERIFIED','prospective_test_started':False,'forecasts_issued':0,'labels_read':False,'prediction_metrics_computed':False,'models_modified':False,'source_version_warning':'Public collector commit31July2026 is not verified as the May archive deployment;database default clock/dedup are source-code evidence,not deployment attestation.'}
 write(BASE/'report.json',report);pq.write_table(pa.Table.from_pylist(results),BASE/'live_input_ledger.parquet');write(BASE/'audit_receipt.json',{'at':now().isoformat(),'status':'completed','scope':'Label-blind input compatibility only','labels_read':False})
 paths=list(BASE.iterdir())+[Path(__file__).resolve(),REPO_ROOT/'eventx/v7/live_quote_inputs_20261026.py',REPO_ROOT/'eventx/tasks/check_v7_live_quote_inputs_20261026.py',DEV/'development/manifest.json',SRC/'journal.jsonl',REL/'upstream/source_receipt.json']+list((REL/'upstream').rglob('*.rs'))+list((REL/'upstream').rglob('*.py'))
 write(BASE/'manifest.json',{'files':{**payload_hashes,**{str(p.relative_to(REPO_ROOT)):sha(p) for p in paths}}})
 print(json.dumps({k:v for k,v in report.items() if k!='feature_distribution_diagnostic'},indent=2))
if __name__=='__main__':main()
