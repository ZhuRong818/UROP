"""One frozen exploratory quote comparison, kept separate from all holdouts."""
from collections import Counter
import json
from pathlib import Path
import numpy as np
from eventx.tasks.discover_v7_direct_pilot_20261022 import REPO_ROOT,now,sha,write,verify_originals
from eventx.tasks.freeze_v7_quote_experiment_20261024 import RELEASE,BASE,AUDIT
from eventx.v7.quote_experiment_20261024 import QuoteTape,stamp,iso,predictions,FEATURES

def metric(y,p):
    e=np.array(p)-np.array(y)
    return {'rows':len(e),'mae':float(np.mean(abs(e))),'rmse':float(np.sqrt(np.mean(e*e))),'mean_error':float(np.mean(e))}

def main():
    OUT=BASE/'development'
    if OUT.exists():raise RuntimeError('Do not rerun frozen development evaluation')
    for manifest in [RELEASE/'implementation_manifest.json',AUDIT/'manifest.json']:
        m=json.loads(manifest.read_text())
        for p,h in m.get('locked_files',m.get('files',{})).items():
            if sha(REPO_ROOT/p)!=h:raise RuntimeError('Input hash mismatch')
    verify_originals();OUT.mkdir(parents=True,exist_ok=False)
    write(OUT/'consumption_receipt.json',{'at':now().isoformat(),'scope':'Previously source-exposed V7 development quotes only',
        'protected_holdouts_opened':False,'policy_sha256':sha(RELEASE/'policy.json'),
        'freeze_manifest_sha256':sha(RELEASE/'implementation_manifest.json'),'rerun_allowed':False})
    policy=json.loads((RELEASE/'policy.json').read_text())
    samples=[json.loads(l) for l in (RELEASE/'development_cohort.jsonl').read_text().splitlines()]
    ar=json.loads((AUDIT/'report.json').read_text());rc=json.loads((AUDIT/'run_contract.json').read_text())
    tape=QuoteTape(REPO_ROOT/ar['run'],samples,policy);tape.load_frozen(AUDIT/'journal.jsonl')
    begin=int(np.ceil(stamp(rc['started_at'])/300)*300);end=int(stamp(rc['stop_at'])//300*300)
    split=stamp('2026-10-24T00:00:00Z');valid_start=stamp('2026-10-24T00:30:00Z')
    ledger=[];complete=[];failures=Counter();endpoint_failures=Counter()
    for s in samples:
        for t in range(begin,end+1,300):
            feature,reasons=tape.features(s['market_id'],t)
            row={'market_id':s['market_id'],'question':s['question'],'grid_at':iso(t),'target_at':iso(t+1800),
                'decision_eligible':feature is not None,'decision_failures':reasons,'split':'training' if t+1800<split else 'validation' if t>=valid_start else 'purged',
                'target_status':'not_attempted','retrospective':True}
            if feature is not None:
                row.update(feature)
                target,why=(None,['target_outside_frozen_snapshot']) if t+1800>stamp(rc['stop_at']) else tape.endpoint(s['market_id'],t)
                row.update(target_status='observed' if target else 'unavailable',endpoint_failures=why,target=target)
                if target:complete.append(row)
                endpoint_failures.update(why)
            failures.update(reasons);ledger.append(row)
    train=[r for r in complete if r['split']=='training'];valid=[r for r in complete if r['split']=='validation']
    (OUT/'observation_ledger.jsonl').write_text(''.join(json.dumps(r,sort_keys=True)+'\n' for r in ledger))
    write(OUT/'coverage.json',{'scheduled_grids':len(ledger),'decision_eligible':sum(r['decision_eligible'] for r in ledger),
        'complete_rows':len(complete),'training_rows':len(train),'validation_rows':len(valid),
        'training_markets':len({r['market_id'] for r in train}),'validation_markets':len({r['market_id'] for r in valid}),
        'decision_failure_counts':dict(failures),'endpoint_failure_counts':dict(endpoint_failures)})
    if len(train)<policy['minimum_training_rows'] or len({r['market_id'] for r in train})<policy['minimum_training_markets'] or not valid:
        write(OUT/'report.json',{'status':'insufficient_data_under_frozen_policy','model_fitted':False,'metrics':None})
    else:
        x=np.array([r['features'] for r in train]);y=np.array([r['target']['midpoint']-r['midpoint'] for r in train])
        center=x.mean(0);scale=x.std(0);scale[scale==0]=1
        z=(x-center)/scale;ym=float(y.mean());coef=np.linalg.solve(z.T@z+policy['ridge_alpha']*np.eye(z.shape[1]),z.T@(y-ym))
        model={'at':now().isoformat(),'feature_names':FEATURES,'center':center.tolist(),'scale':scale.tolist(),
            'intercept':ym,'coefficients':coef.tolist(),'ridge_alpha':policy['ridge_alpha'],'training_rows':len(train),
            'training_feature_min':x.min(0).tolist(),'training_feature_max':x.max(0).tolist(),'development_only':True}
        write(OUT/'ridge_model.json',model)
        scores=[]
        for r in valid:
            p=predictions(r,model);scores.append({'market_id':r['market_id'],'grid_at':r['grid_at'],'target_midpoint':r['target']['midpoint'],
                'current_midpoint':r['midpoint'],'predictions':p,'retrospective':True})
        metrics={k:metric([r['target_midpoint'] for r in scores],[r['predictions'][k] for r in scores]) for k in policy['models']}
        market_metrics=[]
        for cid in sorted({r['market_id'] for r in scores}):
            rr=[r for r in scores if r['market_id']==cid]
            market_metrics.append({'market_id':cid,'metrics':{k:metric([r['target_midpoint'] for r in rr],[r['predictions'][k] for r in rr]) for k in policy['models']}})
        (OUT/'validation_predictions.jsonl').write_text(''.join(json.dumps(r,sort_keys=True)+'\n' for r in scores))
        write(OUT/'per_market_metrics.json',market_metrics)
        write(OUT/'report.json',{'status':'completed_exploratory_comparison','metrics':metrics,'training_rows':len(train),'validation_rows':len(valid),
            'validation_markets':len(market_metrics),'validation_changed_midpoint_rows':sum(abs(r['target_midpoint']-r['current_midpoint'])>1e-12 for r in scores),
            'model_fitted':True,'old_trade_model_loaded_or_changed':False,'model_promoted':False,'news_effect_tested':False,
            'independent_confirmation':False,'confidence_intervals':None,'limits':['source-exposed retrospective data','overlapping horizons','one shared short calendar period','sampled active-state evidence','no independent release episode yield']})
    write(OUT/'payload_hashes.json',{str(Path(p).relative_to(REPO_ROOT)):h for p,h in tape.payload_hashes.items()})
    files=list(OUT.iterdir())+[RELEASE/'implementation_manifest.json']
    write(OUT/'manifest.json',{'files':{str(p.relative_to(REPO_ROOT)):sha(p) for p in files}})
    print(json.dumps({'coverage':json.loads((OUT/'coverage.json').read_text()),'result':json.loads((OUT/'report.json').read_text())},indent=2))

if __name__=='__main__':main()
