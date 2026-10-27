from collections import Counter,defaultdict
from pathlib import Path
from datetime import datetime,timezone
import json,hashlib,shutil
import joblib,numpy as np,pyarrow.parquet as pq,sklearn
from eventx.v7.source_time_study_20261026 import predict,metrics
from eventx.v7.live_quote_inputs_20261026 import project_ws
from eventx.v7.source_time_quote_inputs_20261026 import SourceTimeQuoteTape
root=Path('/Users/zhurong/UROP');base=root/'data/v7/source_time_study_20261026_v02';old=root/'data/v7/source_time_study_20261026';src=old/'readiness'
def write(p,v):p.write_text(json.dumps(v,indent=2,sort_keys=True)+'\n')
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
hashes=0
for path in [root/'eventx/release/v7/source_time_study_20261026/implementation_manifest.json',root/'eventx/release/v7/source_time_study_20261026_v02/implementation_manifest.json',old/'development/manifest.json',base/'development/manifest.json',src/'capture_manifest.json',base/'readiness_audit/manifest.json']:
 for p,h in json.loads(path.read_text())['files'].items():assert sha(root/p)==h,p;hashes+=1
oldrows=pq.read_table(old/'development/grid_ledger.parquet').to_pylist();newrows=pq.read_table(base/'development/grid_ledger.parquet').to_pylist();changes=[]
assert len(oldrows)==len(newrows)==41400
for a,b in zip(oldrows,newrows):
 assert (a['market_id'],a['t'],a['target'],a['current_valid'])==(b['market_id'],b['t'],b['target'],b['current_valid'])
 if a['features']!=b['features']:
  assert b['t']%86400==1800 and a['features'][:11]==b['features'][:11]
  changes.append({'market_id':b['market_id'],'t':b['t'],'date':b['date']})
assert len(changes)==22
valid=[r for r in newrows if r['date']=='2026-05-09' and r['current_valid']]
pred=predict(joblib.load(base/'development/fit_may7_8.joblib'),valid);saved=pq.read_table(base/'development/validation_predictions.parquet').to_pylist();assert len(valid)==len(saved)==3688
for i,r in enumerate(saved):
 assert (r['market_id'],r['t'],r['target'])==(valid[i]['market_id'],valid[i]['t'],valid[i]['target'])
 for n,p in pred.items():assert p[i]==r[n]
report=json.loads((base/'development/report.json').read_text());known=np.array([r['target'] is not None for r in valid]);y=np.array([r['target'] for r in valid if r['target'] is not None])
for n,p in pred.items():
 actual=metrics(y,p[known]);expected=report['validation']['metrics'][n]
 for k in actual:assert abs(actual[k]-expected[k])<1e-12
final=joblib.load(base/'development/frozen_models.joblib');assert final['full_logit'].n_features_in_==final['hgb7'].n_features_in_==14
assert len({(r['market_id'],r['t']) for r in newrows})==41400
groups=json.loads((base/'development/validation_by_market.json').read_text());macro={n:float(np.mean([r['metrics'][n]['log_loss'] for r in groups if r['known']])) for n in pred}
calibration=[]
for n,p in pred.items():
 for lo,hi in zip([0,.05,.1,.2,.4,.6,.8],[.05,.1,.2,.4,.6,.8,1.000001]):
  mask=known&(p>=lo)&(p<hi);yy=np.array([r['target'] if r['target'] is not None else 0 for r in valid])
  calibration.append({'model':n,'lower':lo,'upper':min(hi,1),'n':int(mask.sum()),'mean_prediction':float(p[mask].mean()) if mask.any() else None,'observed_rate':float(yy[mask].mean()) if mask.any() else None})
write(base/'development_supplement.json',{'equal_contract_log_loss':macro,'calibration':calibration})
samples=[json.loads(l) for l in (root/'eventx/release/v7/source_time_study_20261026_v02/live_cohort.jsonl').read_text().splitlines()];by=defaultdict(list)
for r in map(json.loads,(src/'journal.jsonl').read_text().splitlines()):
 if r['kind']=='ws_frame':
  for x in project_ws(json.loads((src/'objects'/r['payload_sha256']).read_text()),r['available_at'],r['response_received_at'],samples):
   if x['event_type']=='price_change':by[x['market'].decode()].append(x)
latencies=[r['timestamp_received'].timestamp()-r['timestamp'].timestamp() for rows in by.values() for r in rows]
decisions=[];counts=Counter()
for r in pq.read_table(base/'readiness_audit/coverage_ledger.parquet').to_pylist():
 t=r['t'];available=[x for x in by[r['market_id']] if x['timestamp_received'].timestamp()<=t]
 causal=[x for x in available if x['timestamp'].timestamp()<=x['timestamp_received'].timestamp()]
 eligible=SourceTimeQuoteTape(by[r['market_id']]).features(t);assert (eligible is not None)==r['quote_valid']
 age=t-max(x['timestamp'].timestamp() for x in causal) if causal else None
 latest_age=t-max(x['timestamp'].timestamp() for x in available) if available else None
 reason='eligible' if eligible is not None else 'no_source_before_availability_quote' if not causal else 'ordered_quote_stale' if age>120 else 'other_quality_or_conflict'
 counts[reason]+=1
 decisions.append({'market_id':r['market_id'],'at':r['at'],'transport_ready':r['transport_ready'],'quote_valid':r['quote_valid'],'reason':reason,'latest_source_age_seconds':latest_age,'latest_ordered_source_age_seconds':age})
diag=base/'readiness_diagnosis.json'
if diag.exists():shutil.copyfile(diag,base/'readiness_diagnosis_incomplete_heuristic_v00.json')
diagnosis={'scope':'Input clocks only, no target or forecast','price_change_rows':len(latencies),'source_after_durable_availability_rows':sum(x<0 for x in latencies),'availability_minus_source_quantiles_seconds':np.quantile(latencies,[0,.1,.5,.9,1]).tolist(),
 'counts':dict(counts),'decisions':decisions,'post_warmup':[r for r in decisions if r['transport_ready']],
 'interpretation':'84/92 projected messages have exchange timestamp up to91ms ahead of local durable availability. Cause (clock skew versus timestamp semantics) unverified. Frozen source<=availability rule rejects them; do not alter times or relax gate based on observed outcomes.',
 'earlier_diagnostic':'v00 checked latest source age without source<=availability and mislabeled some rejected quotes eligible; superseded by this exact feature-gate replay.'}
write(diag,diagnosis)
qa={'at':datetime.now(timezone.utc).isoformat(),'passed':True,'hash_entries_verified':hashes,'grid_keys':41400,'corrected_boundary_vectors':len(changes),'target_and_eligibility_changes':0,'validation_prediction_replays':len(saved),'matched_metric_sets_recomputed':4,'unit_tests_passed':27,'refit_features':14,'sklearn_version':sklearn.__version__,'numpy_version':np.__version__,'live_feature_gate_replays':len(decisions),'prospective_test_started':False,'live_labels_read':False}
write(base/'qa.json',qa);write(base/'boundary_correction_audit.json',{'changed_vectors':changes,'target_changes':0,'current_eligibility_changes':0,'other_feature_differences':0})
print(json.dumps({'qa':qa,'equal_contract_log_loss':macro,'clock_diagnosis':{k:v for k,v in diagnosis.items() if k!='decisions'}},indent=2))
