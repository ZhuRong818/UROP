"""Freeze an explicitly post-selection hypothesis for future observations only."""
import json
from pathlib import Path
import plistlib
import numpy as np
from sklearn.linear_model import LogisticRegression
from sklearn.preprocessing import StandardScaler
from eventx.tasks.discover_v7_direct_pilot_20261022 import REPO_ROOT,now,sha,write,verify_originals
from eventx.v7.segment_candidate_20261024 import forecast

RELEASE=REPO_ROOT/'eventx/release/v7/segment_candidate_20261024'
OUT=REPO_ROOT/'data/v7/segment_candidate_20261024'

def main():
    verify_originals();search=REPO_ROOT/'data/v7/segment_research_20261024';dev=REPO_ROOT/'data/v7/memory_quote_20261024/development'
    for path in [search/'manifest.json',dev/'manifest.json']:
        for p,h in json.loads(path.read_text())['files'].items():
            if sha(REPO_ROOT/p)!=h:raise RuntimeError('Discovery evidence drift')
    RELEASE.mkdir(exist_ok=False);OUT.mkdir(exist_ok=False)
    data=[json.loads(l) for l in (dev/'observations.jsonl').read_text().splitlines()]
    train=sorted([r for r in data if r['target'] and r['split']=='training' and r['features']['short_features'] is not None],key=lambda r:(r['grid_at'],r['market_id']))
    x=np.array([r['features']['short_features'] for r in train]);y=np.array([r['target']['midpoint']-r['features']['midpoint'] for r in train])
    labels=np.where(y>1e-12,1,np.where(y< -1e-12,-1,0));scaler=StandardScaler();z=scaler.fit_transform(x)
    fit=LogisticRegression(C=.1,max_iter=2000,random_state=20261024);fit.fit(z,labels)
    if list(fit.classes_)!=[-1,0,1]:raise RuntimeError('Unexpected classes; do not silently change predictor')
    model={'training_rows':len(train),'classes':fit.classes_.tolist(),'class_mean_changes':[float(y[labels==c].mean()) for c in fit.classes_],
        'center':scaler.mean_.tolist(),'scale':scaler.scale_.tolist(),'coefficients':fit.coef_.tolist(),'intercept':fit.intercept_.tolist(),
        'training_feature_min':x.min(0).tolist(),'training_feature_max':x.max(0).tolist(),'C':.1,'max_iter':2000,
        'target':'Receipt-clock midpoint change in30minutes; classes -1/0/+1 using1e-12 tolerance'}
    write(RELEASE/'model.json',model)
    pred={ (r['market_id'],r['grid_at']):r for r in [json.loads(l) for l in (search/'outer_predictions.jsonl').read_text().splitlines()]}
    errors=[];active=0
    for r in data:
        key=(r['market_id'],r['grid_at'])
        if key not in pred:continue
        result=forecast(r['features'],model);expected=pred[key]['predictions']['hurdle_mean'] if result['segment_active'] else r['features']['midpoint']
        errors.append(abs(result['prediction']-expected));active+=int(result['segment_active'])
    if not errors or max(errors)>1e-12:raise RuntimeError('Serialized model does not reproduce discovered policy')
    write(OUT/'export_parity.json',{'at':now().isoformat(),'rows':len(errors),'segment_rows':active,'maximum_absolute_difference':max(errors),
        'purpose':'Actual development prediction parity check, not new validation evidence'})
    policy={'at':now().isoformat(),'version':'segment_candidate_20261024','selection':'Post-hoc exploratory winner from420nominal model/segment comparisons; failed inner stability screen',
        'segment':'past30-minute midpoint momentum times current imbalance >1e-12; requires valid short features',
        'prediction':'Three-class regularized logistic probabilities times training-only conditional mean changes',
        'fallback':'Persistence outside segment or without30mhistory','source':'Already-running memory quote service; no new market selection or network requests',
        'activation':'First future5minute grid after launch; base commitment and this commitment both<=grid+30s',
        'endpoint':'Use only the existing frozen base-service endpoint after a timely candidate commitment',
        'outcomes':'All eligible base forecasts retained; report segment AND population fallback errors and missingness',
        'no_claims':['independent confirmation','news gain','profitability','algorithmic novelty'],
        'no_refit':True,'no_existing_service_changes':True,'stop':'Base run stop+60seconds; bounded read-only consumer'}
    write(RELEASE/'policy.json',policy)
    label='com.eventx.segment-candidate.20261024'
    plist={'Label':label,'ProgramArguments':['/usr/bin/caffeinate','-i','-s',str(REPO_ROOT/'.venv/bin/python'),'-m','eventx.tasks.run_v7_segment_candidate_20261024'],
        'WorkingDirectory':str(REPO_ROOT),'RunAtLoad':True,'KeepAlive':False,'EnvironmentVariables':{'PYTHONUNBUFFERED':'1'},
        'StandardOutPath':str(OUT/'stdout.log'),'StandardErrorPath':str(OUT/'stderr.log')}
    (RELEASE/(label+'.plist')).write_bytes(plistlib.dumps(plist))
    paths=list(RELEASE.iterdir())+[Path(__file__).resolve(),search/'manifest.json',dev/'manifest.json',
        REPO_ROOT/'eventx/v7/segment_candidate_20261024.py',REPO_ROOT/'eventx/tasks/run_v7_segment_candidate_20261024.py',
        REPO_ROOT/'eventx/tasks/launch_v7_segment_candidate_20261024.py',REPO_ROOT/'eventx/release/v7/memory_shadow_20261024/implementation_manifest.json',
        REPO_ROOT/'eventx/tasks/run_v7_quote_experiment_20261024.py']
    write(RELEASE/'implementation_manifest.json',{'locked_files':{str(p.relative_to(REPO_ROOT)):sha(p) for p in paths}})
    print(json.dumps({'frozen':str(RELEASE.relative_to(REPO_ROOT)),'training_rows':len(train),'export_parity_max':max(errors),'discovery_only':True}))

if __name__=='__main__':main()
