from pathlib import Path
from collections import defaultdict
import json,re
import pyarrow.parquet as pq
from eventx.v7.live_quote_inputs_20261026 import project_ws
from eventx.v7.clock_bounded_quote_inputs_20261026 import SourceTimeQuoteTape
from eventx.v7.source_time_quote_inputs_20261026 import SourceTimeQuoteTape as Strict
root=Path('/Users/zhurong/UROP');base=root/'data/v7/source_time_study_20261026_v03';probe=root/'data/v7/clock_alignment_20261026'
checks=[];excluded=[]
for r in json.loads((probe/'ntp.json').read_text()):
 selected=r['raw'].split('selected:')[-1]
 header=re.search(r'header:\s*(\w+)',selected)
 if not header or header[1]=='00':
  excluded.append({'host':r['host'],'reported_offset':r['offset_seconds'],'reported_uncertainty':r['reported_uncertainty_seconds'],'reason':'Native selected packet missing/zero;summary is not a valid offset estimate'})
  assert r['reported_uncertainty_seconds']>.1
  continue
 vals={k:float(re.search(r'^\s*'+k+r':.*\(([-\d.]+)\)',selected,re.M)[1]) for k in ['t1','t2','t3','t4']}
 estimate=((vals['t2']-vals['t1'])+(vals['t3']-vals['t4']))/2
 assert abs(estimate-r['offset_seconds'])<2e-6
 checks.append({'host':r['host'],'offset_recomputed_seconds':estimate,'offset_reported_seconds':r['offset_seconds']})
old=root/'data/v7/source_time_study_20261026/readiness';sample=root/'eventx/release/v7/source_time_study_20261026_v03/live_cohort.jsonl';samples=[json.loads(l) for l in sample.read_text().splitlines()];by=defaultdict(list)
for r in map(json.loads,(old/'journal.jsonl').read_text().splitlines()):
 if r['kind']=='ws_frame':
  for x in project_ws(json.loads((old/'objects'/r['payload_sha256']).read_text()),r['available_at'],r['response_received_at'],samples):by[x['market'].decode()].append(x)
ledger=pq.read_table(root/'data/v7/source_time_study_20261026_v02/readiness_audit/coverage_ledger.parquet').to_pylist();rows=[]
for s in samples:
 cid=s['market_id'];a=Strict(by[cid]);b=SourceTimeQuoteTape(by[cid])
 rr=[r for r in ledger if r['market_id']==cid]
 rows.append({'market_id':cid,'grids':len(rr),'strict_quote_valid':sum(a.features(r['t']) is not None for r in rr),'corrected_quote_valid':sum(b.features(r['t']) is not None for r in rr),
  'postwarmup_quote_and_metadata_valid_without_clock_monitor_DIAGNOSTIC_ONLY':sum(b.features(r['t']) is not None and r['transport_ready'] and r['metadata_ready'] for r in rr)})
report={'ntp_offset_sign':'server minus local; positive means local behind','native_sntp_four_timestamp_checks':checks,'excluded_native_summaries':excluded,'old_capture_input_only_replay':rows,
 'old_capture_clock_gate_can_be_verified':False,'interpretation':'Old-source mechanism diagnosis only; contemporary clock probes cannot validate past clocks. No live targets or predictions.'}
(base/'clock_semantics_qa.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps({'ntp_checks':len(checks),'excluded_native_summaries':excluded,'old_capture_input_only_replay':rows},indent=2))
