"""Finite exploratory segment/model search on already-open development data."""
from collections import Counter
import hashlib
import json
from pathlib import Path
import numpy as np
import sklearn
from sklearn.ensemble import HistGradientBoostingRegressor
from sklearn.linear_model import Ridge,LogisticRegression
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler
from eventx.tasks.discover_v7_direct_pilot_20261022 import REPO_ROOT,now,sha,write,verify_originals
from eventx.tasks.run_v7_quote_experiment_20261024 import metric
from eventx.v7.quote_experiment_20261024 import stamp

BASE=REPO_ROOT/'data/v7/segment_research_20261024'
RELEASE=REPO_ROOT/'eventx/release/v7/segment_research_20261024'
DEV=REPO_ROOT/'data/v7/memory_quote_20261024/development'

def segments(x):
    p,spread=x[:,0],x[:,1];depth=np.minimum(np.expm1(x[:,2]),np.expm1(x[:,3]));imb=x[:,4]
    age=np.expm1(x[:,6]);m5,m30,vol=x[:,7],x[:,8],x[:,9]
    active=vol>1e-12;tight=spread<=.010000000001;strong=abs(imb)>=.5
    return {'all':np.ones(len(x),bool),'spread_le_001':tight,'spread_gt_001':~tight,
        'spread_le_002':spread<=.020000000001,'depth_ge_100':depth>=100,'depth_lt_100':depth<100,
        'depth_ge_1000':depth>=1000,'imbalance_abs_ge_05':strong,'imbalance_abs_lt_05':~strong,
        'imbalance_abs_ge_08':abs(imb)>=.8,'price_interior_01_09':(p>.1)&(p<.9),'price_le_01':p<=.1,'price_ge_09':p>=.9,
        'source_age_le_1m':age<=1,'source_age_gt_1m':age>1,'source_age_le_5m':age<=5,
        'past30_nonzero_volatility':active,'past30_zero_volatility':~active,
        'past30_positive_momentum':m30>1e-12,'past30_negative_momentum':m30< -1e-12,'past30_zero_momentum':abs(m30)<=1e-12,
        'past5_changed':abs(m5)>1e-12,'momentum_imbalance_aligned':m30*imb>1e-12,
        'momentum_imbalance_opposed':m30*imb< -1e-12,'active_and_tight':active&tight,
        'strong_imbalance_and_tight':strong&tight,'active_and_interior':active&(p>.1)&(p<.9),
        'active_and_boundary':active&((p<=.1)|(p>=.9))}

def candidates(xtrain,ytrain,x):
    out={'persistence':x[:,0]};fitmeta={}
    for a in [.01,.05,.1,.25,1.]:out['weighted_'+str(a)]=np.clip(x[:,0]+a*x[:,5],0,1)
    for col,h in [(7,'5'),(8,'30')]:
        a=.25 if h=='5' else .1
        out['momentum'+h]=np.clip(x[:,0]+a*x[:,col],0,1)
        out['reversion'+h]=np.clip(x[:,0]-a*x[:,col],0,1)
    for alpha in [10.,100.,1000.]:
        model=make_pipeline(StandardScaler(),Ridge(alpha=alpha));model.fit(xtrain,ytrain)
        out['ridge_'+str(alpha)]=np.clip(x[:,0]+model.predict(x),0,1)
    for loss in ['squared_error','absolute_error']:
        model=HistGradientBoostingRegressor(loss=loss,max_iter=100,learning_rate=.05,max_leaf_nodes=7,max_depth=3,
            min_samples_leaf=20,l2_regularization=10,early_stopping=False,random_state=20261024)
        model.fit(xtrain,ytrain);out['hgb_'+loss]=np.clip(x[:,0]+model.predict(x),0,1)
    # Change occurrence and direction as a 3-class hurdle; conditional class sizes learned only in training.
    classes=np.where(ytrain>1e-12,1,np.where(ytrain< -1e-12,-1,0));unique=np.unique(classes)
    if len(unique)==1:delta=np.full(len(x),float(np.mean(ytrain)))
    else:
        model=make_pipeline(StandardScaler(),LogisticRegression(C=.1,max_iter=2000,random_state=20261024))
        model.fit(xtrain,classes);prob=model.predict_proba(x)
        values=np.array([float(np.mean(ytrain[classes==c])) for c in model[-1].classes_]);delta=prob@values
    out['hurdle_mean']=np.clip(x[:,0]+delta,0,1)
    return out,{'training_rows':len(ytrain),'changed_training':int((abs(ytrain)>1e-12).sum()),'class_counts':{str(c):int((classes==c).sum()) for c in unique}}

def arrays(rows):
    x=np.array([r['features']['short_features'] for r in rows]);y=np.array([r['target']['midpoint'] for r in rows]);return x,y

def score(rows,y,p,mask):
    if not mask.any():return None
    b=np.array([r['features']['midpoint'] for r in rows]);a=metric(y[mask],p[mask]);ref=metric(y[mask],b[mask])
    diff=ref['mae']-a['mae'];fallback=np.where(mask,p,b)
    return {'rows':int(mask.sum()),'markets':len({r['market_id'] for r,m in zip(rows,mask) if m}),
        'coverage':float(mask.mean()),'changed_rows':int((abs(y[mask]-b[mask])>1e-12).sum()),
        'baseline':ref,'candidate':a,'mae_gain':diff,'relative_mae_reduction':diff/ref['mae'] if ref['mae']>0 else None,
        'whole_population_with_persistence_elsewhere':metric(y,fallback),
        'whole_population_mae_gain':float(np.mean(abs(y-b))-np.mean(abs(y-fallback)))}

def main():
    verify_originals()
    for p,h in json.loads((DEV/'manifest.json').read_text())['files'].items():
        if sha(REPO_ROOT/p)!=h:raise RuntimeError('Development hash mismatch')
    BASE.mkdir(exist_ok=False);RELEASE.mkdir(exist_ok=False)
    folds=[{'train_endpoint_before':'2026-10-23T19:30:00Z','start':'2026-10-23T20:00:00Z','end':'2026-10-23T21:00:00Z'},
           {'train_endpoint_before':'2026-10-23T20:30:00Z','start':'2026-10-23T21:00:00Z','end':'2026-10-23T22:00:00Z'},
           {'train_endpoint_before':'2026-10-23T21:30:00Z','start':'2026-10-23T22:00:00Z','end':'2026-10-23T23:30:00Z'}]
    policy={'at':now().isoformat(),'scope':'User-authorized segment/model discovery; all underlying data already outcome-exposed',
        'not_confirmatory':True,'protected_or_live_outcomes_used':False,'input_manifest_sha256':sha(DEV/'manifest.json'),
        'folds':folds,'selection':'Choose on inner forward predictions before computing outer descriptive scores',
        'candidate_selection_min_rows':50,'min_markets':3,'min_coverage':.1,'min_positive_inner_folds':2,
        'fold_positive_rule':'At least10selected rows and positive baseline MAE and positive MAE gain',
        'ranking':'Largest whole-population MAE gain with persistence outside segment; tie by segment/model name',
        'fallback_if_no_candidate':'persistence','segment_definition':'Fixed code rules from current/pre-decision features only; no identities or future changes',
        'objective':'30-minute midpoint MAE; RMSE secondary; retain all experiments and discovery-only winners',
        'source':'https://scikit-learn.org/1.7/auto_examples/model_selection/plot_nested_cross_validation_iris.html',
        'sklearn_version':sklearn.__version__,'model_count_including_persistence':16,'segment_count':28,
        'deployment':'No mutation of live service; any selected candidate needs a separately frozen future evaluation'}
    write(RELEASE/'policy.json',policy)
    write(RELEASE/'implementation_manifest.json',{'locked_files':{str(p.relative_to(REPO_ROOT)):sha(p) for p in [Path(__file__).resolve(),RELEASE/'policy.json',DEV/'manifest.json']}})
    write(BASE/'consumption_receipt.json',{'at':now().isoformat(),'scope':'Previously exposed V7 development only; no sealed labels','manifest_sha256':sha(RELEASE/'implementation_manifest.json')})
    data=[json.loads(l) for l in (DEV/'observations.jsonl').read_text().splitlines()]
    data=[r for r in data if r['target'] and r['features']['short_features'] is not None]
    train=sorted([r for r in data if r['split']=='training'],key=lambda r:(r['grid_at'],r['market_id']))
    outer=sorted([r for r in data if r['split']=='validation'],key=lambda r:(r['grid_at'],r['market_id']))
    inner_rows=[];inner_preds={};inner_fold=[];fold_reports=[]
    for i,fold in enumerate(folds):
        fit=[r for r in train if stamp(r['target_at'])<stamp(fold['train_endpoint_before'])]
        val=[r for r in train if stamp(fold['start'])<=stamp(r['grid_at'])<stamp(fold['end'])]
        if len(fit)<50 or not val:raise RuntimeError('Insufficient frozen fold')
        xt,yt=arrays(fit);x,y=arrays(val);pred,meta=candidates(xt,yt-xt[:,0],x)
        for k,v in pred.items():inner_preds.setdefault(k,[]).extend(v.tolist())
        inner_rows.extend(val);inner_fold.extend([i]*len(val));fold_reports.append({'fold':i,**fold,**meta,'validation_rows':len(val)})
    x,y=arrays(inner_rows);rules=segments(x);fid=np.array(inner_fold);ledger=[]
    for segment,mask in rules.items():
        for model,p in inner_preds.items():
            if model=='persistence':continue
            p=np.array(p);s=score(inner_rows,y,p,mask)
            if s is None:continue
            fs=[]
            for i in range(len(folds)):
                indices=np.flatnonzero(fid==i);rr=[inner_rows[j] for j in indices]
                fs.append(score(rr,y[indices],p[indices],mask[indices]))
            wins=sum(bool(z and z['rows']>=10 and z['baseline']['mae']>0 and z['mae_gain']>1e-15) for z in fs)
            eligible=s['rows']>=50 and s['markets']>=3 and s['coverage']>=.1 and wins>=2 and s['mae_gain']>1e-15
            ledger.append({'segment':segment,'model':model,'inner':s,'folds':fs,'positive_inner_folds':wins,'selection_eligible':eligible})
    eligible=sorted([r for r in ledger if r['selection_eligible']],key=lambda r:(-r['inner']['whole_population_mae_gain'],r['segment'],r['model']))
    chosen={'segment':eligible[0]['segment'],'model':eligible[0]['model'],'inner':eligible[0]['inner']} if eligible else {'segment':'all','model':'persistence','reason':'No candidate passes frozen inner selection screen'}
    # Persist selection before obtaining any outer model predictions or rankings.
    write(BASE/'selection_before_outer.json',{'at':now().isoformat(),**chosen,'eligible_candidates':len(eligible)})
    (BASE/'inner_search.jsonl').write_text(''.join(json.dumps(r,sort_keys=True)+'\n' for r in ledger));write(BASE/'folds.json',fold_reports)
    xt,yt=arrays(train);xo,yo=arrays(outer);opred,meta=candidates(xt,yt-xt[:,0],xo);orules=segments(xo)
    selected_score=score(outer,yo,opred[chosen['model']],orules[chosen['segment']]);outer_ledger=[]
    for seg,mask in orules.items():
        for model,p in opred.items():
            if model=='persistence':continue
            s=score(outer,yo,p,mask)
            if s:outer_ledger.append({'segment':seg,'model':model,'outer':s,'selection_eligible':next(r['selection_eligible'] for r in ledger if r['segment']==seg and r['model']==model) if any(r['segment']==seg and r['model']==model for r in ledger) else False})
    (BASE/'outer_discovery_search.jsonl').write_text(''.join(json.dumps(r,sort_keys=True)+'\n' for r in outer_ledger))
    winners=sorted([r for r in outer_ledger if r['outer']['rows']>=20 and r['outer']['markets']>=3 and r['outer']['mae_gain']>1e-15],key=lambda r:(-r['outer']['whole_population_mae_gain'],r['segment'],r['model']))
    prediction_rows=[{'market_id':r['market_id'],'grid_at':r['grid_at'],'target_midpoint':float(yo[i]),'current_midpoint':float(xo[i,0]),
        'predictions':{k:float(p[i]) for k,p in opred.items()},'segments':[k for k,m in orules.items() if m[i]]} for i,r in enumerate(outer)]
    (BASE/'outer_predictions.jsonl').write_text(''.join(json.dumps(r,sort_keys=True)+'\n' for r in prediction_rows))
    report={'at':now().isoformat(),'scope':'Exploratory selection research on already-exposed data; no independent confirmation',
        'train_rows':len(train),'inner_rows':len(inner_rows),'outer_rows':len(outer),'model_count':len(opred),'segment_count':len(rules),
        'nominal_model_segment_comparisons':(len(opred)-1)*len(rules),'nonempty_inner_comparisons':len(ledger),'nonempty_outer_comparisons':len(outer_ledger),
        'inner_selected':chosen,'selected_outer':selected_score,'eligible_inner_candidates':len(eligible),'discovery_only_positive_candidates':len(winners),
        'top_discovery_only':winners[:10],'outer_full_baseline':metric(yo,xo[:,0]),
        'interpretation':'Outer-ranked winners are hypotheses, not validated gains. No data discarded; whole-population fallback and every candidate retained.',
        'live_policy_changed':False,'confirmation':False,'news_effect_tested':False,'old_trade_model_changed':False}
    write(BASE/'report.json',report)
    paths=list(BASE.iterdir())+[RELEASE/'implementation_manifest.json'];write(BASE/'manifest.json',{'files':{str(p.relative_to(REPO_ROOT)):sha(p) for p in paths}})
    print(json.dumps({k:report[k] for k in ['model_count','segment_count','nominal_model_segment_comparisons','inner_selected','selected_outer','eligible_inner_candidates','discovery_only_positive_candidates','top_discovery_only']},indent=2))

if __name__=='__main__':main()
