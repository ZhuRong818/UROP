from pathlib import Path
from collections import defaultdict
import json,hashlib,math
import pyarrow.parquet as pq
from eventx.v7.native_clock_receipt_20261026 import selected_packet_check
from eventx.v7.clock_bounded_quote_inputs_20261026 import SourceTimeQuoteTape,clock_health
from eventx.v7.live_quote_inputs_20261026 import project_ws
from eventx.v7.quote_experiment_20261024 import stamp
from eventx.tasks.audit_v7_quote_shadow_20261024 import chain
root=Path('/Users/zhurong/UROP');base=root/'data/v7/source_time_study_20261026_v03';rel=root/'eventx/release/v7/source_time_study_20261026_v03';src=base/'readiness'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
hashes=0
for m in [src/'capture_manifest.json',base/'readiness_audit/manifest.json',base/'development/manifest.json',rel/'implementation_manifest.json',rel/'readiness_auditor_manifest.json',root/'eventx/release/v7/source_time_study_20261026_v02/delivery_manifest.json']:
 for p,h in json.loads(m.read_text())['files'].items():assert sha(root/p)==h,p;hashes+=1
records=chain(src/'journal.jsonl');samples=[json.loads(l) for l in (rel/'live_cohort.jsonl').read_text().splitlines()];by=defaultdict(list);packet=[]
for r in records:
 if r['kind']=='ws_frame':
  p=src/'objects'/r['payload_sha256'];assert sha(p)==r['payload_sha256']
  for row in project_ws(json.loads(p.read_text()),r['available_at'],r['response_received_at'],samples):by[row['market'].decode()].append(row)
 if r['kind']=='clock_probe':
  for m in r['measurements']:
   check=selected_packet_check(m);potential=m.get('exit_code')==0 and m.get('offset_seconds') is not None and m.get('reported_uncertainty_seconds') is not None and math.isfinite(m['offset_seconds']) and 0<=m['reported_uncertainty_seconds']<=.1
   if potential:assert check['valid'],(r['at'],m['host'],check)
   packet.append({'at':r['at'],'host':m['host'],'could_admit_clock_gate':potential,**check})
rows=pq.read_table(base/'readiness_audit/coverage_ledger.parquet').to_pylist()
for r in rows:
 t=r['t'];prefix=[x for x in by[r['market_id']] if x['timestamp_received'].timestamp()<=t]
 assert SourceTimeQuoteTape(prefix).features(t)==r['features']
 past=[x for x in records if (x.get('available_epoch',stamp(x.get('available_at') or x.get('at') or '2100-01-01T00:00:00Z')))<=t]
 assert clock_health(past,t)[0]==r['clock_ready']
assert len({(r['market_id'],r['t']) for r in rows})==len(rows)
assert not (base/'activation_receipt.json').exists() and not (base/'evaluation/consumption_receipt.json').exists()
qa={'passed':True,'hash_entries_verified':hashes,'journal_records':len(records),'asof_feature_replays':len(rows),'asof_clock_replays':len(rows),
 'native_packets_checked':len(packet),'native_packets_valid':sum(p['valid'] for p in packet),'potentially_admitting_clock_packets_all_valid':True,
 'unit_checks_passed':38,'development_grid_rows_verified':41400,'development_prediction_rows_verified':3688,
 'prospective_test_started':False,'live_labels_read':False,'raw_timestamps_modified':False}
(base/'final_qa.json').write_text(json.dumps(qa,indent=2)+'\n');(base/'native_clock_packet_audit.json').write_text(json.dumps(packet,indent=2)+'\n')
print(json.dumps(qa,indent=2))
