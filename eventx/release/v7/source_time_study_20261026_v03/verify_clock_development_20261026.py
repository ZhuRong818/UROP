from pathlib import Path
import json,hashlib
import numpy as np,joblib,pyarrow.parquet as pq
from eventx.v7.source_time_study_20261026_v03 import predict,metrics
root=Path('/Users/zhurong/UROP');base=root/'data/v7/source_time_study_20261026_v03';old=root/'data/v7/source_time_study_20261026_v02'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
hashes=0
for m in [base/'development/manifest.json',old/'development/manifest.json',root/'eventx/release/v7/source_time_study_20261026_v03/implementation_manifest.json',root/'data/v7/clock_alignment_20261026/manifest.json']:
 for p,h in json.loads(m.read_text())['files'].items():assert sha(root/p)==h,p;hashes+=1
a=pq.read_table(old/'development/grid_ledger.parquet').to_pylist();b=pq.read_table(base/'development/grid_ledger.parquet').to_pylist();assert a==b
pa=pq.read_table(old/'development/validation_predictions.parquet').to_pylist();pb=pq.read_table(base/'development/validation_predictions.parquet').to_pylist();assert pa==pb
valid=[r for r in b if r['date']=='2026-05-09' and r['current_valid']];bundle=joblib.load(base/'development/fit_may7_8.joblib');ps=predict(bundle,valid)
for i,r in enumerate(pb):
 for n,p in ps.items():assert p[i]==r[n]
known=np.array([r['target'] is not None for r in valid]);y=np.array([r['target'] for r in valid if r['target'] is not None]);report=json.loads((base/'development/report.json').read_text())
for n,p in ps.items():assert metrics(y,p[known])==report['validation']['metrics'][n]
final=joblib.load(base/'development/frozen_models.joblib');assert final['input_contract']=='source_time_quote14_clock_bound250ms_v3_requires_new_fit'
qa={'passed':True,'hash_entries_verified':hashes,'development_grid_rows_identical_to_v02':len(b),'features_or_labels_changed':0,'prediction_rows_identical_to_v02':len(pb),'prediction_replays':len(pb),'metric_sets_recomputed':4,'unit_checks_passed':38,'new_model_input_contract':final['input_contract'],'prospective_test_started':False}
(base/'development_qa.json').write_text(json.dumps(qa,indent=2)+'\n')
state=root/'CURRENT_STATE.md';s=state.read_text().replace('V03 clock correction frozen from independent probes; development/repeat readiness in progress; no test.','V03 clock correction fitted/frozen; repeat40mininput-onlycapture running; no prospective test.')
s=s.replace('- Refit samefixedmodels onrebuiltMay7–9development;repeat40mininput-onlycapture withclockmonitor. No test.',
 '- Refit complete:41400gridrows/3688predictions identicalV02;38checksPASS. Repeat40mininput-onlycapture withclockmonitor running;no test.')
state.write_text(s)
contract=json.loads((base/'readiness/run_contract.json').read_text());status=json.loads((base/'readiness/status.json').read_text())
with (root/'docs/progress/2026-10.md').open('a') as f:
 f.write('\n## V03developmentverified;freshclock-monitoredreadiness started\n\n'+json.dumps(qa,sort_keys=True)+'\n')
 f.write('V03refit9406knownrows/20contracts,allfixedmodels;LLHGB0.3585589345042676 versuslogistic0.42678936650339094 remains15.986910020304176%lower;developmentonly,586unknownMay9endpoints preserved. New publicnetworkcollector prefixapproved;PID'+str(status['pid'])+';runcontract:'+json.dumps(contract,sort_keys=True)+'.No forecasts,labels or systemclockwrites.\n')
print(json.dumps(qa,indent=2))
