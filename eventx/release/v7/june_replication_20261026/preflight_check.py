from pathlib import Path
import itertools,json
import numpy as np
import pyarrow.parquet as pq
from eventx.tasks.run_v7_june_replication_20261026 import infer,load_models,missing_bounds,PRIOR,REL,MODELS,DATES
from eventx.tasks.discover_v7_direct_pilot_20261022 import write,now
rows=pq.read_table(PRIOR/'evaluation/grid_ledger.parquet').to_pylist();rows=[r for r in rows if r['endpoint_eligible']]
pred=pq.read_table(PRIOR/'evaluation/predictions.parquet').to_pylist();lookup={(r['market_id'],r['decision_at']):r for r in pred};models=load_models();errors={}
for name in MODELS:
 got=infer(models[name],rows);expected=np.array([lookup[r['market_id'],r['decision_at']][name] for r in rows]);errors[name]=float(np.max(abs(got-expected)));assert errors[name]<1e-12
 sample=rows[0];variants=[dict(sample,target=x,endpoint_eligible=x is not None) for x in [None,0,1]];out=infer(models[name],variants);assert np.max(out)-np.min(out)<1e-15
assert infer(models['row_hgb7'],[]).size==0
p=np.array([.3,.6,.8]);q=np.array([.2,.9,.5]);targets=[1,None,None];b=missing_bounds(targets,p,q);d=[]
for v in itertools.product([0,1],repeat=2):
 y=np.array([1,*v]);d.append(float(np.mean(-(y*np.log(q)+(1-y)*np.log1p(-q))+(y*np.log(p)+(1-y)*np.log1p(-p)))))
assert abs(b['lower']-min(d))<1e-15 and abs(b['upper']-max(d))<1e-15
identical=missing_bounds(targets,p,p);assert identical['lower']==identical['upper']==0
known=missing_bounds([1,0,1],p,q);assert known['lower']==known['upper']
assert missing_bounds([],np.array([]),np.array([]))['lower'] is None
assert len(DATES)==7 and DATES[0]=='2026-06-01' and DATES[-1]=='2026-06-07'
report={'at':now().isoformat(),'passed':True,'parity_rows':len(rows),'max_prediction_errors':errors,'labels_and_eligibility_do_not_change_predictions':True,'bounds_verified_by_exhaustive_binary_label_assignments':True,'old_evaluation_rerun':False,'model_fit':False}
write(REL/'preflight.json',report);print(json.dumps(report,indent=2))
