"""Reconstruct all22 feature columns from frozen source-accounting diagnostics.

Only retained histories with an unambiguous computable path are reconstructed.
This checks source sensitivity, not production feature parity or model performance.
"""
from collections import Counter
import json
from pathlib import Path
import numpy as np
from eventx.features.v5_market import market_values, MARKET_FEATURE_NAMES
from eventx.tasks.tune_v5_market_conditions_20261012 import augment, EXTRA_NAMES
from eventx.tasks.discover_v7_direct_pilot_20261022 import REPO_ROOT,now,sha,write,verify_originals

SRC=REPO_ROOT/'data/v7/input_eligibility_20261023'
OUT=REPO_ROOT/'data/v7/full_feature_compatibility_20261024'
NAMES=[MARKET_FEATURE_NAMES[i] for i in [*range(12),14]]+EXTRA_NAMES

def vector(f):
    if not f['mathematical_240m_history_available'] or f['latest_price'] is None:return None
    p=np.clip(f['latest_price'],.0001,.9999)
    raw=np.array([[np.log(p/(1-p)),f['momentum5'],f['momentum30'],f['momentum120'],
        f['sigma30'],f['sigma240'],f['count60'],f['count240'],f['quantity60'],f['quantity240'],
        f['price_age_minutes'],1]],dtype=np.float32)
    # Identical cast/transformation order to selected-model training, after upstream summaries.
    x=market_values(raw,np.array([0]),np.array([0]),raw[:,10],np.array([0]),np.array([False]))[:,[*range(12),14]]
    values=augment(x)[0]
    if not np.isfinite(values).all():raise ValueError('Nonfinite vector')
    return values

def main():
    for p,h in json.loads((SRC/'manifest.json').read_text())['files'].items():
        if sha(REPO_ROOT/p)!=h:raise RuntimeError('Input lock mismatch')
    semantic=json.loads((REPO_ROOT/'data/v7/feature_semantics_20261022/report.json').read_text())
    for item in semantic['verified_code_chain']:
        if sha(REPO_ROOT/item['code'])!=item['sha256']:raise RuntimeError('Historical code mismatch')
    verify_originals();OUT.mkdir(parents=True,exist_ok=False)
    rows=[json.loads(l) for l in (SRC/'accounting_compatibility.jsonl').read_text().splitlines()]
    vectors=[];comparisons=[]
    for r in rows:
        vv={}
        for name,f in r['variants'].items():
            v=vector(f);vv[name]=v
            vectors.append({'market_id':r['market_id'],'question':r['question'],'role':r['role'],'variant':name,
                'diagnostic_grid':r['diagnostic_grid'],'feature_names':NAMES,
                'values':None if v is None else v.tolist(),'status':'reconstructed_retained_history' if v is not None else f['history_math_reason'],
                'asof_or_completeness_verified':False,'production_parity_verified':False})
        for a,b in [('provider_original','provider_mapped_order_fills'),('provider_original','direct_taker_only'),('direct_inclusive','direct_taker_only'),('provider_original','provider_late')]:
            if a not in vv or b not in vv or vv[a] is None or vv[b] is None:continue
            delta=vv[b].astype(float)-vv[a].astype(float)
            comparisons.append({'market_id':r['market_id'],'question':r['question'],'role':r['role'],'baseline':a,'alternative':b,
                'changed_columns_float32':[NAMES[i] for i in np.flatnonzero(delta)],
                'changed_columns_above_1e_6':[NAMES[i] for i in np.flatnonzero(abs(delta)>1e-6)],
                'deltas':dict(zip(NAMES,delta.tolist()))})
    report={'at':now().isoformat(),'feature_columns':len(NAMES),'variant_records':len(vectors),
        'reconstructed_vectors':sum(r['values'] is not None for r in vectors),
        'reconstructed_markets':len({r['market_id'] for r in vectors if r['values'] is not None}),
        'pair_comparisons':len(comparisons),'pairs_with_changes_above_1e_6':sum(bool(r['changed_columns_above_1e_6']) for r in comparisons),
        'source_compatibility_promoted':False,'model_loaded_or_scored':False,'labels_computed':False,
        'limits':['Retrospective22October common windows; not live forecasts or current market coverage.',
                  'Upstream summary volatility and ordering remain source-sensitive; not a bitwise reproduction of historical cumulative calculations.',
                  'Unavailable histories remain missing, never filled with zero.',
                  'One numerical tolerance is descriptive; it is not a validated equivalence threshold.']}
    for name,rs in [('vectors',vectors),('comparisons',comparisons)]:
        (OUT/(name+'.jsonl')).write_text(''.join(json.dumps(r,sort_keys=True)+'\n' for r in rs))
    write(OUT/'report.json',report)
    files=list(OUT.iterdir())+[Path(__file__).resolve(),SRC/'manifest.json',REPO_ROOT/'eventx/features/v5_market.py',REPO_ROOT/'eventx/tasks/tune_v5_market_conditions_20261012.py']
    write(OUT/'manifest.json',{'files':{str(p.relative_to(REPO_ROOT)):sha(p) for p in files}})
    print(json.dumps(report,indent=2))

if __name__=='__main__':main()
