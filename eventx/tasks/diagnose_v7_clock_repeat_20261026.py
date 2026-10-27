"""Clock/readiness evidence only; no live targets or prediction metrics."""
from pathlib import Path
from collections import defaultdict
import json
import numpy as np
import pyarrow.parquet as pq
from eventx.tasks.run_v7_source_time_study_20261026_v03 import BASE,REL,REPO_ROOT
from eventx.tasks.discover_v7_direct_pilot_20261022 import now,sha,write
from eventx.tasks.run_v7_archive_week_pilot_20261025 import verify
from eventx.tasks.audit_v7_quote_shadow_20261024 import chain
from eventx.v7.live_quote_inputs_20261026 import project_ws
from eventx.v7.clock_bounded_quote_inputs_20261026 import clock_health

def main():
 if (BASE/'clock_repeat_diagnosis.json').exists():raise RuntimeError('Preserve completed diagnosis')
 src=BASE/'readiness';verify(src/'capture_manifest.json');verify(BASE/'readiness_audit/manifest.json')
 samples=[json.loads(l) for l in (REL/'live_cohort.jsonl').read_text().splitlines()];records=chain(src/'journal.jsonl')
 leads=[];clocks=[];steps=[];previous=None
 for r in records:
  if r['kind']=='ws_frame':
   for row in project_ws(json.loads((src/'objects'/r['payload_sha256']).read_text()),r['available_at'],r['response_received_at'],samples):
    if row['event_type']=='price_change':leads.append(row['timestamp'].timestamp()-row['timestamp_received'].timestamp())
  if r['kind']=='clock_probe':
   ok,reasons=clock_health(records,r['available_epoch'])
   clocks.append({'at':r['at'],'gate_passed':ok,'reasons':reasons,'measurements':[{k:x.get(k) for k in ['host','offset_seconds','reported_uncertainty_seconds','exit_code']} for x in r['measurements']]})
  if 'local_wall_epoch' in r:
   current=(r['local_wall_epoch'],r['monotonic_seconds'])
   if previous:steps.append((current[0]-previous[0])-(current[1]-previous[1]))
   previous=current
 rows=pq.read_table(BASE/'readiness_audit/coverage_ledger.parquet').to_pylist()
 report={'at':now().isoformat(),'scope':'Input clocks only;no live targets or forecasts','price_change_rows':len(leads),
   'source_ahead_of_durability':sum(x>0 for x in leads),'source_lead_over250ms':sum(x>.250+1e-9 for x in leads),
   'source_minus_durability_quantiles_seconds':np.quantile(leads,[0,.1,.5,.9,1]).tolist() if leads else None,
   'clock_rounds':clocks,'clock_rounds_passing':sum(r['gate_passed'] for r in clocks),
   'max_abs_wall_monotonic_step_seconds':max(map(abs,steps)) if steps else None,
   'strict_ready':sum(r['strict_fully_ready'] for r in rows),'corrected_ready':sum(r['fully_ready'] for r in rows),
   'strict_quote_valid':sum(r['strict_quote_valid'] for r in rows),'corrected_quote_valid':sum(r['quote_valid'] for r in rows),
   'post_warmup_ready_if_clock_health_ignored_DIAGNOSTIC_ONLY':sum(r['quote_valid'] and r['transport_ready'] and r['metadata_ready'] for r in rows),
   'post_warmup':[{'at':r['at'],'market_id':r['market_id'],'strict_quote_valid':r['strict_quote_valid'],'corrected_quote_valid':r['quote_valid'],'clock_ready':r['clock_ready'],'fully_ready':r['fully_ready'],'reasons':r['reasons']} for r in rows if r['transport_ready']],
   'gate_relaxed_after_capture':False,'timestamps_modified':False,'prospective_test_started':False}
 write(BASE/'clock_repeat_diagnosis.json',report)
 print(json.dumps(report,indent=2))
if __name__=='__main__':main()
