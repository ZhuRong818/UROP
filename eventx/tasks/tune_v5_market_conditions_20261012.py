"""Bounded market-only tuning on already opened discovery folds, version 20261012."""
from datetime import datetime, timezone
import json
from pathlib import Path
import joblib
import numpy as np
from scipy.special import expit
from sklearn.ensemble import HistGradientBoostingClassifier
from threadpoolctl import threadpool_limits
from eventx.features.v5_market import market_values, MARKET_FEATURE_NAMES
from eventx.tasks.audit_v5_algorithms import SEED, block_interval
from eventx.tasks.screen_v5_market_learners_20261009 import write_json
from eventx.tasks.build_v4_discovery_examples import EXAMPLE_DTYPE
from eventx.tasks.run_v4_discovery_models import OOF_DTYPE
from eventx.tasks.run_v4_exploratory_novelty_diffusion import reconstruct_oof_indices
from eventx.tasks.run_v5_residual_feasibility import (
    EXAMPLES, EXAMPLES_MANIFEST, OOF, OOF_MANIFEST, MARKETS, FUTURE,
    REPO_ROOT, metric, point_loss, read_jsonl, sha256_file, terminal_metadata, verify_manifest,
)

OUT = REPO_ROOT / 'data/v5/market_condition_tuning_20261012'
PARENT = REPO_ROOT / 'data/v5/algorithm_audit_20260907'
INCUMBENT = REPO_ROOT / 'data/v5/market_learner_screen_20261009'
BASE = dict(max_iter=600, learning_rate=.05, max_leaf_nodes=7, max_depth=3,
            min_samples_leaf=100, l2_regularization=10.)
CONFIGS = [
    dict(name='larger_120k', cap=120000, augmented=False, half_life=None, params=BASE),
    dict(name='larger_200k', cap=200000, augmented=False, half_life=None, params=BASE),
    dict(name='larger_120k_15leaf', cap=120000, augmented=False, half_life=None,
         params={**BASE, 'max_leaf_nodes':15, 'max_depth':4, 'max_iter':500}),
    dict(name='condition_60k', cap=60000, augmented=True, half_life=None, params=BASE),
    dict(name='condition_120k', cap=120000, augmented=True, half_life=None, params=BASE),
    dict(name='condition_120k_15leaf', cap=120000, augmented=True, half_life=None,
         params={**BASE, 'max_leaf_nodes':15, 'max_depth':4, 'max_iter':500}),
    dict(name='recent_120k_14d', cap=120000, augmented=False, half_life=14., params=BASE),
    dict(name='recent_condition_120k_14d', cap=120000, augmented=True, half_life=14., params=BASE),
    dict(name='recent_condition_120k_30d', cap=120000, augmented=True, half_life=30., params=BASE),
]
EXTRA_NAMES = ['vol_ratio_30_240', 'momentum5_scaled_vol30',
               'momentum30_scaled_vol30', 'momentum120_scaled_vol240',
               'momentum5_vs30', 'count_rate_ratio', 'size_rate_ratio',
               'age_x_vol30', 'price_uncertainty']

def augment(x):
    v30, v240 = np.maximum(x[:,4], 0), np.maximum(x[:,5],0)
    # Bounded ratios handle zero volatility without fitting any evaluation statistics.
    ratio = lambda a,b: np.clip(a/(b+1e-6), -50, 50)
    count60, count240 = np.expm1(x[:,6]), np.expm1(x[:,7])
    size60, size240 = np.expm1(x[:,8]), np.expm1(x[:,9])
    p = expit(x[:,0])
    extra = np.column_stack([ratio(v30,v240), ratio(x[:,1],v30),
        ratio(x[:,2],v30), ratio(x[:,3],v240), x[:,1]-x[:,2]/6,
        4*count60/(count240+1), 4*size60/(size240+1),
        np.log1p(x[:,12])*v30, p*(1-p)])
    return np.column_stack([x, extra]).astype(np.float32)

def main():
    if OUT.exists():
        raise SystemExit('Existing run must be preserved; create a new version')
    for p in (FUTURE/'consumption_receipt.json', FUTURE/'examples/examples.bin', FUTURE/'evaluation/result.json'):
        if p.exists(): raise RuntimeError('Protected artifact exists; stop')
    for p in (EXAMPLES_MANIFEST, OOF_MANIFEST, PARENT/'manifest.json', INCUMBENT/'manifest.json'):
        verify_manifest(p)
    OUT.mkdir(parents=True)
    contract = dict(created_at=datetime.now(timezone.utc).isoformat(),
        scope='User-authorized opened-development market-only tuning; May-July, not October',
        target_eligibility_splits_unchanged=True, selection_fold=4, reporting_fold=5,
        reporting_fold_already_opened=True, configs=CONFIGS,
        candidate_fallback='retained_hgb_7_600',
        selection='Lowest fold-4 log loss among completed models with Brier no worse than incumbent; otherwise retain incumbent. Selection recorded before fold-5 fits.',
        seed=SEED, threads=2, extra_features=EXTRA_NAMES,
        ratio_clipping=50, denominator_epsilon=1e-6,
        inputs=[dict(path=str(p.relative_to(REPO_ROOT)),sha256=sha256_file(p)) for p in
                (EXAMPLES, OOF, MARKETS, PARENT/'predictions.npz', INCUMBENT/'predictions.npz')],
        limitations=['adaptive opened-data search','no independent confirmation',
                    'upstream eligibility/status uncertainty','event/calendar dependence unresolved'])
    write_json(OUT/'contract.json', contract)
    examples=np.memmap(EXAMPLES,mode='r',dtype=EXAMPLE_DTYPE)
    oof=np.memmap(OOF,mode='r',dtype=OOF_DTYPE)
    idx=reconstruct_oof_indices(examples,oof)
    terminal,known=terminal_metadata(list(read_jsonl(MARKETS)))
    x=market_values(examples['features'][idx,:12],oof['market'],oof['minute'],
                    examples['price_age'][idx],terminal,known)[:,[*range(12),14]]
    xa=augment(x)
    assert np.isfinite(xa).all()
    selected_rows=np.flatnonzero(oof['fold']>=3)
    frozen=np.load(PARENT/'predictions.npz',allow_pickle=False)
    for k in ('market','minute','fold','label'):
        assert np.array_equal(frozen[k],oof[k][selected_rows]), k
    old=np.load(INCUMBENT/'predictions.npz',allow_pickle=False)
    results={}; predictions={}; selected='retained_hgb_7_600'
    with threadpool_limits(limits=2):
        for fold in (4,5):
            valid=np.flatnonzero(oof['fold']==fold)
            earlier=np.flatnonzero((oof['fold']<fold)&(oof['minute']+30<fold*11*1440))
            assert not np.intersect1d(oof['market'][earlier],oof['market'][valid]).size
            assert oof['minute'][earlier].max()+30<oof['minute'][valid].min()
            baseline=old[f'hgb_7_600__fold{fold}']
            assert len(baseline)==len(valid)
            results.setdefault('retained_hgb_7_600',{'folds':{}})['folds'][str(fold)]={'status':'complete','metrics':metric(oof['label'][valid],baseline)}
            predictions[f'retained_hgb_7_600__fold{fold}']=baseline
            for c in CONFIGS:
                entry=results.setdefault(c['name'],{'config':c,'folds':{}})
                try:
                    train=earlier
                    if len(train)>c['cap']:
                        train=np.sort(np.random.default_rng(SEED+fold+20).choice(train,c['cap'],replace=False))
                    weights=None
                    if c['half_life']:
                        ages=(oof['minute'][train].max()-oof['minute'][train])/1440.
                        weights=np.exp2(-ages/c['half_life']);weights/=weights.mean()
                    matrix=xa if c['augmented'] else x
                    model=HistGradientBoostingClassifier(early_stopping=False,random_state=SEED,**c['params'])
                    model.fit(matrix[train],oof['label'][train],sample_weight=weights)
                    score=model.predict_proba(matrix[valid])[:,1]
                    assert np.isfinite(score).all()
                    predictions[f"{c['name']}__fold{fold}"]=score
                    entry['folds'][str(fold)]={'status':'complete','training_rows':len(train),'metrics':metric(oof['label'][valid],score)}
                    if fold==5 and c['name']==selected:
                        joblib.dump({'model':model,'config':c,'base_feature_names':[MARKET_FEATURE_NAMES[i] for i in [*range(12),14]],'extra_names':EXTRA_NAMES if c['augmented'] else [],'development_only':True},OUT/'selected_model.joblib')
                except Exception as e:
                    entry['folds'][str(fold)]={'status':'failed','error':str(e)}
                result=entry['folds'][str(fold)]
                print(f"fold {fold} {c['name']}: {result}",flush=True)
                write_json(OUT/'checkpoint.json',dict(results=results,selected_on_fold4=selected if fold==5 else None))
            if fold==4:
                guard=results['retained_hgb_7_600']['folds']['4']['metrics']['brier']
                eligible=[n for n,e in results.items() if e['folds']['4']['status']=='complete' and e['folds']['4']['metrics']['brier']<=guard]
                selected=min(eligible,key=lambda n:(results[n]['folds']['4']['metrics']['log_loss'],n))
                write_json(OUT/'selection_receipt.json',dict(selected=selected,selected_at=datetime.now(timezone.utc).isoformat(),fold5_new_scores_not_computed=True))
                print('SELECTED ON FOLD 4: '+selected,flush=True)
    valid=np.flatnonzero(oof['fold']==5);y=oof['label'][valid]
    score=predictions.get(f'{selected}__fold5')
    if score is None: raise RuntimeError('Selected candidate failed later fold; no replacement selection')
    comparisons={}
    for name,ref in [('previous_selected_hgb',old['hgb_7_600__fold5']),('earlier_tree',frozen['tree_no_terminal'][frozen['fold']==5]),('logistic',frozen['linear_no_terminal'][frozen['fold']==5])]:
        m=metric(y,ref);delta=point_loss(y,ref)-point_loss(y,score)
        comparisons[name]=dict(baseline_metrics=m,improvement=block_interval({'market':oof['market'][valid]},delta),log_loss_percent_reduction=float(100*delta.mean()/m['log_loss']))
    bins=[]
    for name,values,edges in [('price_age_minutes',x[valid,12],[0,5,15,30,60,np.inf]),('trade_count_60m',np.expm1(x[valid,6]),[0,3,10,30,100,np.inf]),('price_probability',expit(x[valid,0]),[0,.1,.3,.7,.9,1.01])]:
        for lo,hi in zip(edges[:-1],edges[1:]):
            mask=(values>=lo)&(values<hi)
            if not mask.any():continue
            bins.append(dict(feature=name,lower=lo,upper=None if not np.isfinite(hi) else hi,rows=int(mask.sum()),selected=metric(y[mask],score[mask]),incumbent=metric(y[mask],old['hgb_7_600__fold5'][mask])))
    np.savez_compressed(OUT/'predictions.npz',market=oof['market'][selected_rows],minute=oof['minute'][selected_rows],fold=oof['fold'][selected_rows],**predictions)
    report=dict(status='complete',selected_on_fold4=selected,results=results,selected_fold5_metrics=metric(y,score),comparisons=comparisons,subgroups=bins,protected_outcomes_read=False,candidate_promotion=False,current_october_conditions_evaluated=False)
    write_json(OUT/'report.json',report)
    artifacts=[p for p in OUT.iterdir() if p.is_file()]+[Path(__file__)]
    write_json(OUT/'manifest.json',{'artifacts':[{'path':str(p.relative_to(REPO_ROOT)),'sha256':sha256_file(p)} for p in artifacts]})
    print(json.dumps({'status':'complete','selected':selected,'metrics':report['selected_fold5_metrics'],'comparisons':comparisons},indent=2),flush=True)

if __name__=='__main__':main()
