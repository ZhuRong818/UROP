"""Fixed feature ablations and earlier-period calibration selection, development only."""
from datetime import datetime,timezone
from pathlib import Path
import json,joblib
import numpy as np
from scipy.optimize import minimize
from scipy.special import expit,logit
from sklearn.ensemble import HistGradientBoostingClassifier
from threadpoolctl import threadpool_limits
from eventx.tasks.tune_v5_market_conditions_20261012 import augment,BASE,SEED,EXTRA_NAMES
from eventx.features.v5_market import market_values
from eventx.tasks.run_v4_exploratory_novelty_diffusion import reconstruct_oof_indices
from eventx.tasks.build_v4_discovery_examples import EXAMPLE_DTYPE
from eventx.tasks.run_v4_discovery_models import OOF_DTYPE
from eventx.tasks.run_v5_residual_feasibility import REPO_ROOT,EXAMPLES,OOF,MARKETS,metric,read_jsonl,terminal_metadata,sha256_file,verify_manifest
from eventx.tasks.diagnose_v7_signed_evidence_coverage_20261012 import write_json
from eventx.tasks.continue_v7_strong_market_news_20261014 import calibration

PARENT=REPO_ROOT/'data/v5/market_condition_tuning_20261012'
OUT=REPO_ROOT/'data/v5/market_ablation_calibration_20261014'
GROUPS={'without_volatility_scaled_features':[13,14,15,16],
        'without_momentum_contrast':[17], 'without_activity_ratios':[18,19],
        'without_age_volatility':[20],'without_price_uncertainty':[21]}

def fit_calibrator(p,y,method):
    if method=='identity':return {'method':'identity'}
    z=logit(np.clip(p,1e-7,1-1e-7))
    def objective(b):
        a=np.exp(b[0]);inter=b[1] if method=='platt' else 0.
        v=a*z+inter;q=expit(v);err=q-y
        loss=np.mean(np.logaddexp(0,v)-y*v)+.0005*(b@b)
        grad=[np.mean(err*a*z)+.001*b[0]]
        if method=='platt':grad.append(np.mean(err)+.001*b[1])
        return float(loss),np.array(grad)
    result=minimize(objective,np.zeros(2 if method=='platt' else 1),jac=True,method='L-BFGS-B',bounds=[(-2.,2.)]+([(-3.,3.)] if method=='platt' else []),options={'maxiter':1500,'gtol':1e-7,'ftol':1e-12})
    if not result.success:raise RuntimeError(result.message)
    return {'method':method,'slope':float(np.exp(result.x[0])),'intercept':float(result.x[1]) if method=='platt' else 0.,'penalty':.001,'iterations':int(result.nit)}

def apply_calibrator(p,fit):
    return p.copy() if fit['method']=='identity' else expit(fit['slope']*logit(np.clip(p,1e-7,1-1e-7))+fit['intercept'])

def main():
    if OUT.exists():raise SystemExit('Preserve existing cycle')
    verify_manifest(PARENT/'manifest.json')
    OUT.mkdir(parents=True)
    inputs=[EXAMPLES,OOF,MARKETS,PARENT/'predictions.npz',PARENT/'selection_receipt.json']
    write_json(OUT/'contract.json',{'created_at':datetime.now(timezone.utc).isoformat(),'scope':'opened development ablations/calibration; no promotion','baseline':'condition_120k','ablation_groups':GROUPS,'training':'same parent deterministic 120000 rows, fixed parameters, earlier folds and 30m purge','hyperparameters':BASE,'calibration_methods':['identity','temperature','platt'],'calibration_penalty':.001,'calibration_selection':'chronological 70/30 split inside fold4, 30m purge, minimum validation LL with Brier no worse identity; selection receipt before calibrated fold5 scores','fold5_previously_opened':True,'no_ablation_model_selection':True,'code_sha256':sha256_file(Path(__file__)),'inputs':[{'path':str(p.relative_to(REPO_ROOT)),'sha256':sha256_file(p)} for p in inputs]})
    examples=np.memmap(EXAMPLES,mode='r',dtype=EXAMPLE_DTYPE);oof=np.memmap(OOF,mode='r',dtype=OOF_DTYPE)
    idx=reconstruct_oof_indices(examples,oof);terminal,known=terminal_metadata(list(read_jsonl(MARKETS)))
    x=market_values(examples['features'][idx,:12],oof['market'],oof['minute'],examples['price_age'][idx],terminal,known)[:,[*range(12),14]]
    xa=augment(x);saved=np.load(PARENT/'predictions.npz',allow_pickle=False)
    parent_report=json.loads((PARENT/'report.json').read_text())
    results={};preds={}
    with threadpool_limits(limits=2):
        for fold in (4,5):
            valid=np.flatnonzero(oof['fold']==fold);earlier=np.flatnonzero((oof['fold']<fold)&(oof['minute']+30<fold*11*1440))
            if len(earlier)>120000:earlier=np.sort(np.random.default_rng(SEED+fold+20).choice(earlier,120000,replace=False))
            if np.intersect1d(oof['market'][earlier],oof['market'][valid]).size or oof['minute'][earlier].max()+30>=oof['minute'][valid].min():raise RuntimeError('split failure')
            y=oof['label'][valid]
            for name in ['condition_120k','larger_120k']:
                p=saved[f'{name}__fold{fold}'];results.setdefault(name,{'folds':{}})['folds'][str(fold)]=metric(y,p);preds[f'{name}__fold{fold}']=p
            for name,removed in GROUPS.items():
                keep=[j for j in range(22) if j not in removed]
                model=HistGradientBoostingClassifier(early_stopping=False,random_state=SEED,**BASE)
                model.fit(xa[earlier][:,keep],oof['label'][earlier]);p=model.predict_proba(xa[valid][:,keep])[:,1]
                results.setdefault(name,{'removed_features':[EXTRA_NAMES[j-13] for j in removed],'folds':{}})['folds'][str(fold)]=metric(y,p)
                preds[f'{name}__fold{fold}']=p
                write_json(OUT/'checkpoint.json',{'results':results,'status':'running'})
                print(f'fold {fold} {name}: LL {results[name]["folds"][str(fold)]["log_loss"]}',flush=True)
    v4=np.flatnonzero(oof['fold']==4);v5=np.flatnonzero(oof['fold']==5)
    times=oof['minute'][v4];cut=int(np.quantile(np.unique(times),.7))
    train=times+30<cut;valid=times>=cut
    p4=saved['condition_120k__fold4'];p5=saved['condition_120k__fold5'];y4=oof['label'][v4];y5=oof['label'][v5]
    choices={}
    for method in ('identity','temperature','platt'):
        fit=fit_calibrator(p4[train],y4[train],method);p=apply_calibrator(p4[valid],fit)
        choices[method]={'fit':fit,'validation_metrics':metric(y4[valid],p)}
    floor=choices['identity']['validation_metrics']['brier']
    eligible=[k for k,v in choices.items() if v['validation_metrics']['brier']<=floor]
    selected=min(eligible,key=lambda k:(choices[k]['validation_metrics']['log_loss'],k))
    receipt={'selected':selected,'recorded_at':datetime.now(timezone.utc).isoformat(),'fold4_internal_cut_minute':cut,'train_rows':int(train.sum()),'validation_rows':int(valid.sum()),'fold5_new_calibrated_scores_not_computed':True,'choices':choices}
    write_json(OUT/'calibration_selection_receipt.json',receipt)
    finalfit=fit_calibrator(p4,y4,selected);calibrated=apply_calibrator(p5,finalfit)
    preds['selected_calibrated__fold5']=calibrated
    cal={'selection':receipt,'final_fit_on_all_fold4':finalfit,'raw_fold5':metric(y5,p5),'calibrated_fold5':metric(y5,calibrated),'log_loss_gain':float(metric(y5,p5)['log_loss']-metric(y5,calibrated)['log_loss']),'raw_reliability':calibration(y5,p5),'calibrated_reliability':calibration(y5,calibrated)}
    ablation=[{'name':k,'removed_features':v.get('removed_features',EXTRA_NAMES if k=='larger_120k' else []),'fold4_LL_change_versus_full':v['folds']['4']['log_loss']-results['condition_120k']['folds']['4']['log_loss'],'fold5_LL_change_versus_full':v['folds']['5']['log_loss']-results['condition_120k']['folds']['5']['log_loss']} for k,v in results.items() if k!='condition_120k']
    subgroups=[]
    for name,values,edges in [('price_age_minutes',x[v5,12],[0,5,15,30,60,np.inf]),('trade_count_60m',np.expm1(x[v5,6]),[0,3,10,30,100,np.inf]),('price_probability',expit(x[v5,0]),[0,.1,.3,.7,.9,1.01])]:
        for lo,hi in zip(edges[:-1],edges[1:]):
            mask=(values>=lo)&(values<hi)
            if mask.any():subgroups.append({'feature':name,'lower':lo,'upper':None if not np.isfinite(hi) else hi,'rows':int(mask.sum()),'raw':metric(y5[mask],p5[mask]),'calibrated':metric(y5[mask],calibrated[mask])})
    report={'status':'complete','ablation_results':results,'ablation_summary':ablation,'calibration':cal,'condition_subgroups':subgroups,'new_booster_fits':10,'candidate_promotion':False,'protected_outcomes_read':False,'limits':['Opened adaptive development; no independent confirmation.','Ablations explain this configuration but do not identify causal market mechanisms.','Calibration selection uses within-fold time split, not new held-out events.','No ablation model substituted using fold5.']}
    write_json(OUT/'report.json',report)
    np.savez_compressed(OUT/'predictions.npz',market4=oof['market'][v4],minute4=oof['minute'][v4],market5=oof['market'][v5],minute5=oof['minute'][v5],label5=y5,**preds)
    write_json(OUT/'calibrator.json',finalfit)
    contract=json.loads((OUT/'contract.json').read_text())
    for r in contract['inputs']:
        if sha256_file(REPO_ROOT/r['path'])!=r['sha256']:raise RuntimeError('input changed')
    write_json(OUT/'manifest.json',{'artifacts':[{'path':str(p.relative_to(REPO_ROOT)),'sha256':sha256_file(p)} for p in list(OUT.iterdir())+[Path(__file__)] if p.is_file()]})
    print(json.dumps({'ablation_summary':ablation,'calibration_selected':selected,'raw':cal['raw_fold5'],'calibrated':cal['calibrated_fold5'],'calibration_gain':cal['log_loss_gain']},indent=2),flush=True)

if __name__=='__main__':main()
