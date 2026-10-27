"""Frozen development only. Never opens an historical test or starts prospective forecasts."""
from collections import defaultdict
from datetime import datetime,timezone
from pathlib import Path
import json
import joblib
import numpy as np
import pyarrow as pa
import pyarrow.parquet as pq
from eventx.tasks.discover_v7_direct_pilot_20261022 import REPO_ROOT,now,sha,write,verify_originals
from eventx.tasks.run_v7_archive_week_pilot_20261025 import verify
from eventx.v7.source_time_quote_inputs_20261026 import SourceTimeQuoteTape,FEATURES,CONTRACT
from eventx.v7.source_time_study_20261026 import fit,predict,target_record,paired_summary

BASE=REPO_ROOT/'data/v7/source_time_study_20261026'
REL=REPO_ROOT/'eventx/release/v7/source_time_study_20261026'
DEV=REPO_ROOT/'data/v7/family_training_20261025_v02'

def main():
 verify_originals();verify(REL/'implementation_manifest.json');verify(DEV/'source_dev/capture_manifest.json')
 out=BASE/'development';out.mkdir(parents=True,exist_ok=False)
 write(out/'development_access_receipt.json',{'at':now().isoformat(),'scope':'May7–9 outcome-open development only; new source-time labels','test_consumed':False})
 try:
  cohorts=json.loads((DEV/'cohort/cohorts.json').read_text())['development50'];ledger=[]
  for date in ['2026-05-07','2026-05-08','2026-05-09']:
   by=defaultdict(list)
   for h in range(24):
    folder=DEV/'source_dev/hours'/(date+f'T{h:02}');verify(folder/'manifest.json')
    for r in pq.read_table(folder/'quotes.parquet').to_pylist():by[r['market'].decode()].append(r)
   start=int(datetime.fromisoformat(date+'T00:00:00+00:00').timestamp())
   for sample in cohorts:
    cid=sample['market_id'];tape=SourceTimeQuoteTape(by[cid])
    for t in range(start+1800,start+84600,300):
     ledger.append({'market_id':cid,'date':date,**target_record(tape,t)})
   print(json.dumps({'date':date,'grids':len(ledger),'known_targets':sum(r['target'] is not None for r in ledger)}),flush=True)
  pq.write_table(pa.Table.from_pylist(ledger),out/'grid_ledger.parquet')
  known=[r for r in ledger if r['target'] is not None];train=[r for r in known if r['date']<='2026-05-08']
  valid=[r for r in ledger if r['date']=='2026-05-09' and r['current_valid']]
  vy=[r['target'] for r in valid if r['target'] is not None];ty=[r['target'] for r in train]
  sample_gate=len(train)>=1000 and sum(ty)>=50 and len(ty)-sum(ty)>=50 and len(vy)>=200 and sum(vy)>=20 and len(vy)-sum(vy)>=20 and len({r['market_id'] for r in train})>=8
  if not sample_gate:raise RuntimeError('Frozen development sample gate failed')
  initial=fit(train);joblib.dump(initial,out/'fit_may7_8.joblib')
  p=predict(initial,valid);summary=paired_summary(valid,p)
  scores=summary['metrics'];model_gate=all(scores['hgb7']['log_loss']<scores[n]['log_loss'] and scores['hgb7']['brier']<=scores[n]['brier'] for n in ['full_logit','global_rate'])
  nonoverlap=[i for i,r in enumerate(valid) if r['t']%1800==0]
  summary['nonoverlap']=paired_summary([valid[i] for i in nonoverlap],{n:v[nonoverlap] for n,v in p.items()})
  groups=[]
  for cid in sorted({r['market_id'] for r in valid}):
   ix=[i for i,r in enumerate(valid) if r['market_id']==cid]
   groups.append({'market_id':cid,**paired_summary([valid[i] for i in ix],{n:v[ix] for n,v in p.items()})})
  write(out/'validation_by_market.json',groups)
  pq.write_table(pa.Table.from_pylist([{'market_id':r['market_id'],'t':r['t'],'target':r['target'],**{n:float(v[i]) for n,v in p.items()}} for i,r in enumerate(valid)]),out/'validation_predictions.parquet')
  coverage=[]
  for date in ['2026-05-07','2026-05-08','2026-05-09']:
   rr=[r for r in ledger if r['date']==date];kk=[r for r in rr if r['target'] is not None]
   coverage.append({'date':date,'grids':len(rr),'current_valid':sum(r['current_valid'] for r in rr),'known':len(kk),'positive':sum(r['target'] for r in kk),'markets':len({r['market_id'] for r in kk})})
  final=fit(known);joblib.dump(final,out/'frozen_models.joblib')
  report={'at':now().isoformat(),'scope':'Exploratory development, not independent confirmation','input_contract':CONTRACT,'features':FEATURES,
    'coverage':coverage,'fit_rows':len(train),'fit_positives':sum(ty),'fit_markets':len({r['market_id'] for r in train}),
    'validation':summary,'refit_rows':len(known),'refit_positives':sum(r['target'] for r in known),'refit_markets':len({r['market_id'] for r in known}),
    'sample_gate_passed':bool(sample_gate),'development_model_gate_passed':bool(model_gate),'primary_classifier':'hgb7',
    'hyperparameter_search':False,'live_activation_authorized_by_result':False,'prospective_test_started':False}
  write(out/'report.json',report);print(json.dumps(report,indent=2),flush=True)
 except Exception as e:
  write(out/'failure.json',{'at':now().isoformat(),'type':type(e).__name__,'message':str(e)[:240]});raise
 finally:
  paths=list(out.iterdir())+[REL/'implementation_manifest.json',DEV/'source_dev/capture_manifest.json',DEV/'cohort/manifest.json']
  write(out/'manifest.json',{'files':{str(p.relative_to(REPO_ROOT)):sha(p) for p in paths}})
if __name__=='__main__':main()
