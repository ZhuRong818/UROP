"""Completed current-input coverage audit. No predictions or future target construction."""
from collections import Counter,defaultdict
from pathlib import Path
import json
import math
import pyarrow as pa
import pyarrow.parquet as pq
from eventx.tasks.run_v7_source_time_study_20261026 import BASE,REL,REPO_ROOT
from eventx.tasks.run_v7_archive_week_pilot_20261025 import verify
from eventx.tasks.discover_v7_direct_pilot_20261022 import now,sha,write,verify_originals
from eventx.tasks.audit_v7_quote_shadow_20261024 import chain
from eventx.v7.live_quote_inputs_20261026 import project_ws,transport_ready,InputCompatibilityError
from eventx.v7.source_time_quote_inputs_20261026 import SourceTimeQuoteTape
from eventx.v7.quote_experiment_20261024 import QuoteTape,stamp,iso

def main():
 src=BASE/'readiness';out=BASE/'readiness_audit'
 if out.exists():raise RuntimeError('Audit already exists; do not overwrite')
 verify_originals();verify(REL/'implementation_manifest.json');verify(src/'capture_manifest.json');verify(BASE/'development/manifest.json')
 out.mkdir();records=chain(src/'journal.jsonl');contract=json.loads((src/'run_contract.json').read_text())
 samples=[json.loads(l) for l in (REL/'live_cohort.jsonl').read_text().splitlines()]
 start=stamp(contract['started_at']);stop=stamp(contract['stop_at'])
 finished=[stamp(r['at']) for r in records if r['kind']=='process_stopped']
 bounded=bool(finished and finished[-1]>=stop-1 and any(r['kind']=='run_deadline_reached' for r in records))
 status=QuoteTape(src,samples,{'book_max_age_seconds':120,'status_max_age_seconds':360,'max_spread':.05,'min_best_size':0})
 status.load_frozen(src/'journal.jsonl');by=defaultdict(list);errors=[];event_types=Counter();rest=Counter()
 for r in records:
  if r['kind']=='rest':rest[r['endpoint_kind']+':'+r['status']]+=1
  if r['kind']!='ws_frame':continue
  p=src/'objects'/r['payload_sha256'];assert sha(p)==r['payload_sha256']
  try:rr=project_ws(json.loads(p.read_text()),r['available_at'],r['response_received_at'],samples)
  except (InputCompatibilityError,ValueError,TypeError,KeyError) as e:
   errors.append({'record_sha256':r['record_sha256'],'error':type(e).__name__,'reason':str(e)[:180]});continue
  for row in rr:by[row['market'].decode()].append(row);event_types[row['event_type']]+=1
 ledger=[];markets=[]
 for sample in samples:
  cid=sample['market_id'];tape=SourceTimeQuoteTape(by[cid]);counts=Counter();reasons=Counter()
  for t in range(math.ceil(start/300)*300,int(min(stop,finished[-1] if finished else stop))+1,300):
   in_grid=1800<=t%86400<84600
   if not in_grid:continue
   features=tape.features(t);transport,why=transport_ready(records,t)
   meta=status.at(cid,'market_metadata',t);resolution=status.at(cid,'resolution_state',t)
   identity=bool(meta and resolution and meta['scheduled_end'] is not None and meta['scheduled_end']>t+1800)
   failed=list(why)
   if features is None:failed.append('quote_missing_stale_invalid_or_conflicting')
   if not identity:failed.append('metadata_resolution_or_expiry_failed')
   if errors:failed.append('capture_schema_errors')
   ready=not failed
   counts['scheduled']+=1;counts['quote_valid']+=features is not None;counts['transport_ready']+=transport;counts['metadata_ready']+=identity;counts['fully_ready']+=ready
   reasons.update(failed)
   ledger.append({'market_id':cid,'t':t,'at':iso(t),'features':features,'quote_valid':features is not None,'transport_ready':transport,'metadata_ready':identity,'fully_ready':ready,'reasons':failed})
  markets.append({'market_id':cid,'question':sample['question'],'projected_yes_events':len(by[cid]),**counts,'reasons':dict(reasons)})
 ready=sum(r['fully_ready'] for r in ledger);contributing=sum(r['fully_ready']>0 for r in markets)
 scope_fail=any(r['kind']=='scope_rejected_stop' or r.get('status')=='scope_rejected_stop' for r in records)
 gate=bool(bounded and not errors and not scope_fail and ready>=2 and contributing>=1)
 development=json.loads((BASE/'development/report.json').read_text())
 report={'at':now().isoformat(),'capture_started_at':contract['started_at'],'capture_stop_at':contract['stop_at'],
  'capture_ended_at':iso(finished[-1]) if finished else None,'normal_bounded_completion':bounded,'event_types':dict(event_types),
  'journal_records':len(records),'rest_status_counts':dict(rest),'projection_errors':errors,'scope_failure':scope_fail,'markets':markets,
  'fully_ready_decisions':ready,'contributing_markets':contributing,'live_input_gate_passed':gate,
  'development_model_gate_passed':development['development_model_gate_passed'],
  'combined_preparation_gates_passed':gate and development['development_model_gate_passed'],
  'forecast_service_active':False,'prospective_test_started':False,'forecasts_issued':0,'live_labels_read':False,
  'interpretation':'Input-only short operational rehearsal; not accuracy, independent-event count, power or broad transfer. New service must warm up again; future test requires activation receipt and evaluator freeze.'}
 pq.write_table(pa.Table.from_pylist(ledger),out/'coverage_ledger.parquet');write(out/'report.json',report)
 paths=list(out.iterdir())+[Path(__file__).resolve(),src/'capture_manifest.json',BASE/'development/manifest.json',REL/'readiness_auditor_manifest.json']
 write(out/'manifest.json',{'files':{str(p.relative_to(REPO_ROOT)):sha(p) for p in paths}})
 print(json.dumps(report,indent=2))
if __name__=='__main__':main()
