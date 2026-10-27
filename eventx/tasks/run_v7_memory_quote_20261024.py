"""One separately frozen, source-exposed memory-tier development comparison."""
from collections import Counter
import json
import numpy as np
from eventx.tasks.discover_v7_direct_pilot_20261022 import REPO_ROOT,now,sha,write,verify_originals
from eventx.tasks.freeze_v7_memory_quote_20261024 import RELEASE,BASE,AUDIT
from eventx.tasks.run_v7_quote_experiment_20261024 import metric
from eventx.v7.quote_experiment_20261024 import stamp,iso
from eventx.v7.memory_quote_20261024 import MemoryQuoteTape,SNAPSHOT,SHORT,predict

def main():
    OUT=BASE/'development'
    if OUT.exists():raise RuntimeError('Preserve completed development run')
    verify_originals()
    for path in [RELEASE/'implementation_manifest.json',AUDIT/'manifest.json']:
        m=json.loads(path.read_text())
        for p,h in m.get('locked_files',m.get('files',{})).items():
            if sha(REPO_ROOT/p)!=h:raise RuntimeError('Input lock mismatch')
    OUT.mkdir(exist_ok=False)
    write(OUT/'consumption_receipt.json',{'at':now().isoformat(),'scope':'Already-exposed V7 source-development data; no protected evaluation',
        'policy_sha256':sha(RELEASE/'policy.json'),'rerun_allowed':False})
    policy=json.loads((RELEASE/'policy.json').read_text());samples=[json.loads(l) for l in (RELEASE/'development_cohort.jsonl').read_text().splitlines()]
    source=json.loads((AUDIT/'report.json').read_text());contract=json.loads((AUDIT/'run_contract.json').read_text())
    tape=MemoryQuoteTape(REPO_ROOT/source['run'],samples,policy);tape.load_frozen(AUDIT/'journal.jsonl')
    begin=int(np.ceil(stamp(contract['started_at'])/300)*300);end=int(stamp(contract['stop_at'])//300*300)
    ledger=[];failures=Counter();endpoint_failures=Counter()
    for s in samples:
        for t in range(begin,end+1,300):
            f,why=tape.features(s['market_id'],t)
            r={'market_id':s['market_id'],'grid_at':iso(t),'target_at':iso(t+1800),'features':f,'decision_failures':why,
                'split':'training' if t+1800<stamp('2026-10-24T00:00:00Z') else 'validation' if t>=stamp('2026-10-24T00:30:00Z') else 'purged','target':None}
            if f:
                target,tw=(None,['target_outside_snapshot']) if t+1800>stamp(contract['stop_at']) else tape.endpoint(s['market_id'],t)
                r.update(target=target,endpoint_failures=tw);endpoint_failures.update(tw)
            failures.update(why);ledger.append(r)
    (OUT/'observations.jsonl').write_text(''.join(json.dumps(r,sort_keys=True)+'\n' for r in ledger))
    complete=[r for r in ledger if r['target']];models={};counts={};panels={}
    for tier,names in [('snapshot',SNAPSHOT),('short',SHORT)]:
        train=[r for r in complete if r['split']=='training' and r['features'][tier+'_features'] is not None]
        valid=[r for r in complete if r['split']=='validation' and r['features'][tier+'_features'] is not None]
        counts[tier]={'train':len(train),'training_markets':len({r['market_id'] for r in train}),'validation':len(valid),
            'validation_markets':len({r['market_id'] for r in valid}),'changed_validation':sum(abs(r['target']['midpoint']-r['features']['midpoint'])>1e-12 for r in valid)}
        if len(train)<policy['minimum_training_rows'] or counts[tier]['training_markets']<policy['minimum_training_markets']:continue
        x=np.array([r['features'][tier+'_features'] for r in train]);y=np.array([r['target']['midpoint']-r['features']['midpoint'] for r in train])
        center=x.mean(0);scale=x.std(0);scale[scale==0]=1;z=(x-center)/scale;intercept=float(y.mean())
        coef=np.linalg.solve(z.T@z+policy['ridge_alpha']*np.eye(z.shape[1]),z.T@(y-intercept))
        models[tier]={'feature_names':names,'center':center.tolist(),'scale':scale.tolist(),'intercept':intercept,'coefficients':coef.tolist(),
            'training_feature_min':x.min(0).tolist(),'training_feature_max':x.max(0).tolist(),'training_rows':len(train),'ridge_alpha':policy['ridge_alpha']}
    write(OUT/'models.json',models)
    predictions=[]
    for r in complete:
        if r['split']!='validation':continue
        pred,ood=predict(r['features'],models)
        predictions.append({'market_id':r['market_id'],'grid_at':r['grid_at'],'target_midpoint':r['target']['midpoint'],
            'current_midpoint':r['features']['midpoint'],'short_eligible':r['features']['short_features'] is not None,'predictions':pred,'outside_training_range':ood})
    (OUT/'predictions.jsonl').write_text(''.join(json.dumps(r,sort_keys=True)+'\n' for r in predictions))
    per_market={}
    for tier in ['snapshot','short']:
        rows=[r for r in predictions if tier=='snapshot' or r['short_eligible']]
        keys=['persistence','weighted_midpoint','snapshot_ridge']+(['short_ridge'] if tier=='short' else [])
        keys=[k for k in keys if all(k in r['predictions'] for r in rows)]
        panels[tier]={k:metric([r['target_midpoint'] for r in rows],[r['predictions'][k] for r in rows]) for k in keys} if rows else {}
        per_market[tier]=[{ 'market_id':cid,'metrics':{k:metric([r['target_midpoint'] for r in rows if r['market_id']==cid],
            [r['predictions'][k] for r in rows if r['market_id']==cid]) for k in keys}} for cid in sorted({r['market_id'] for r in rows})]
    write(OUT/'per_market_metrics.json',per_market)
    report={'at':now().isoformat(),'scope':'Exploratory already-exposed development','scheduled':len(ledger),'snapshot_eligible':sum(bool(r['features']) for r in ledger),
        'short_eligible':sum(bool(r['features'] and r['features']['short_features'] is not None) for r in ledger),'complete':len(complete),
        'counts':counts,'matched_metrics':panels,'decision_failures':dict(failures),'endpoint_failures':dict(endpoint_failures),
        'primary_reference':'persistence','promotion':False,'independent_confirmation':False,'news_effect':False,'old_trade_model_changed':False}
    write(OUT/'report.json',report);write(OUT/'payload_hashes.json',{str(__import__('pathlib').Path(p).relative_to(REPO_ROOT)):h for p,h in tape.payload_hashes.items()})
    files=list(OUT.iterdir())+[RELEASE/'implementation_manifest.json']
    write(OUT/'manifest.json',{'files':{str(p.relative_to(REPO_ROOT)):sha(p) for p in files}})
    print(json.dumps(report,indent=2))

if __name__=='__main__':main()
