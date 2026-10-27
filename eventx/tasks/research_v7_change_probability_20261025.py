"""New observational change-probability cycle with endpoint eligibility and frozen later test."""
import argparse
from bisect import bisect_right
from collections import defaultdict,Counter
from datetime import datetime,timezone
import hashlib
import json
from pathlib import Path
import joblib
import numpy as np
import pyarrow as pa
import pyarrow.parquet as pq
from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import log_loss,brier_score_loss,average_precision_score,roc_auc_score
from eventx.tasks.evaluate_v7_observational_quotes_20261025 import states_from,grids_for
from eventx.tasks.run_v7_archive_week_pilot_20261025 import verify
from eventx.tasks.discover_v7_direct_pilot_20261022 import REPO_ROOT,now,sha,write,verify_originals

REL=REPO_ROOT/'eventx/release/v7/change_probability_20261025'
BASE=REPO_ROOT/'data/v7/change_probability_20261025'
OLD=REPO_ROOT/'data/v7/archive_fullweek_20261025'
NEW=REPO_ROOT/'data/v7/archive_change_test_20261025'
COHORT=REPO_ROOT/'eventx/release/v7/archive_week_pilot_20261025/selected_markets.json'
FEATURES=['midpoint','logit_midpoint','spread','source_age','receive_age','hour_sin','hour_cos','log_valid_updates30','valid_state_fraction30','delta5','abs_delta5','missing5','delta15','abs_delta15','missing15','delta30','abs_delta30','missing30']
ACTIVITY=[0,2,7,10,11,13,14,16,17]
CANDIDATES=['global_rate','market_rate','activity_logit','full_logit_0.01','full_logit_0.1','full_logit_1','hgb3','hgb7']


def build_panel(source,dates):
    verify(source/'capture_manifest.json')
    selected=json.loads(COHORT.read_text())['markets'];good={r['hour'] for r in json.loads((source/'file_receipts.json').read_text()) if r['complete']}
    allrows=[]
    for date in dates:
        by=defaultdict(list)
        for h in range(24):
            hour=date+f'T{h:02d}';folder=source/'hours'/hour
            if hour in good:
                verify(folder/'manifest.json');p=folder/'quotes.parquet'
                if p.exists():
                    for row in pq.read_table(p).to_pylist():by[row['market'].decode()].append(row)
        for m in selected:
            cid=m['market_id'];states=states_from(by[cid]);times=[s['at'] for s in states]
            strict={r['t']:r for r in grids_for(states,date,cid,good)}
            def at(t):
                hour=datetime.fromtimestamp(t,timezone.utc).strftime('%Y-%m-%dT%H')
                if hour not in good:return None
                i=bisect_right(times,t)-1
                if i<0:return None
                s=states[i]
                return s if s['valid'] and 0<=t-s['at']<=120 and t-s['source']<=120 else None
            for t,old in strict.items():
                current=at(t);endpoint=at(t+1800)
                r={'date':date,'market_id':cid,'t':t,'decision_at':old['decision_at'],'current_valid':current is not None,'endpoint_eligible':current is not None and endpoint is not None,'strict_eligible':old['complete'],'features':None,'target':None,'current_midpoint':None,'endpoint_midpoint':None}
                if current is not None:
                    mid=current['midpoint'];hour=(t%86400)/3600;i,j=bisect_right(times,t-1800),bisect_right(times,t);nvalid=sum(s['valid'] for s in states[i:j])
                    f=[mid,float(np.log(mid/(1-mid))),current['spread'],t-current['source'],t-current['at'],np.sin(2*np.pi*hour/24),np.cos(2*np.pi*hour/24),np.log1p(nvalid),nvalid/max(1,j-i)]
                    for lag in [300,900,1800]:
                        previous=at(t-lag);delta=mid-previous['midpoint'] if previous else 0.
                        f.extend([delta,abs(delta),float(previous is None)])
                    assert len(f)==len(FEATURES) and np.isfinite(f).all();r.update(features=f,current_midpoint=mid)
                    if endpoint is not None:r.update(endpoint_midpoint=endpoint['midpoint'],target=int(abs(endpoint['midpoint']-mid)>1e-12))
                allrows.append(r)
        print(json.dumps({'phase':'panel','date':date,'grids':len(allrows),'eligible':sum(r['endpoint_eligible'] for r in allrows)}),flush=True)
    return allrows


def arrays(rows):return np.asarray([r['features'] for r in rows],dtype=float).reshape(-1,len(FEATURES)),np.asarray([r['target'] for r in rows],dtype=int)


def fit(name,rows):
    x,y=arrays(rows);rate=(int(y.sum())+1)/(len(y)+2);obj={'name':name,'rate':rate,'estimator':None}
    if name=='global_rate':return obj
    if name=='market_rate':
        groups=defaultdict(list)
        for r in rows:groups[r['market_id']].append(r['target'])
        obj['rates']={cid:(sum(ys)+20*rate)/(len(ys)+20) for cid,ys in groups.items()};return obj
    if len(np.unique(y))<2:obj['fallback_single_class']=True;return obj
    if name=='activity_logit':
        est=make_pipeline(StandardScaler(),LogisticRegression(C=.1,max_iter=2000,random_state=20261025));x=x[:,ACTIVITY]
    elif name.startswith('full_logit_'):
        est=make_pipeline(StandardScaler(),LogisticRegression(C=float(name.rsplit('_',1)[1]),max_iter=2000,random_state=20261025))
    else:est=HistGradientBoostingClassifier(max_iter=100,learning_rate=.05,max_leaf_nodes=int(name[-1]),min_samples_leaf=100,l2_regularization=10,early_stopping=False,random_state=20261025)
    est.fit(x,y);obj['estimator']=est;return obj


def predict(obj,rows):
    if obj['name']=='market_rate':p=np.array([obj['rates'].get(r['market_id'],obj['rate']) for r in rows])
    elif obj['estimator'] is None:p=np.full(len(rows),obj['rate'])
    else:
        x,_=arrays(rows)
        if obj['name']=='activity_logit':x=x[:,ACTIVITY]
        p=obj['estimator'].predict_proba(x)[:,1] if len(rows) else np.array([])
    return np.clip(p,1e-6,1-1e-6)


def metrics(y,p):
    if not len(y):return {'n':0,'positives':0,'log_loss':None,'brier':None,'average_precision':None,'roc_auc':None}
    return {'n':len(y),'positives':int(y.sum()),'log_loss':float(log_loss(y,p,labels=[0,1])),'brier':float(brier_score_loss(y,p)),'average_precision':float(average_precision_score(y,p)) if y.sum() else None,'roc_auc':float(roc_auc_score(y,p)) if len(np.unique(y))==2 else None}


def save_manifest(out,extra):
    paths=[p for p in out.iterdir() if p.is_file() and p.name!='manifest.json']+extra
    write(out/'manifest.json',{'files':{str(p.relative_to(REPO_ROOT)):sha(p) for p in paths}})


def develop():
    verify_originals();verify(REL/'implementation_manifest.json')
    out=BASE/'development';out.mkdir(parents=True,exist_ok=False)
    try:
        rows=build_panel(OLD,['2026-04-21','2026-04-22','2026-04-23','2026-04-24']);pq.write_table(pa.Table.from_pylist(rows),out/'grid_ledger.parquet')
        rr=[r for r in rows if r['endpoint_eligible']];train=[r for r in rr if r['date']<='2026-04-23'];valid=[r for r in rr if r['date']=='2026-04-24'];_,yv=arrays(valid)
        summary=[]
        for date in sorted({r['date'] for r in rows}):
            dd=[r for r in rows if r['date']==date];ee=[r for r in dd if r['endpoint_eligible']]
            summary.append({'date':date,'grids':len(dd),'current_valid':sum(r['current_valid'] for r in dd),'endpoint_eligible':len(ee),'positives':sum(r['target'] for r in ee),'strict_eligible':sum(r['strict_eligible'] for r in dd),'markets':len({r['market_id'] for r in ee})})
        write(out/'coverage_by_day.json',summary)
        if len(train)<500 or sum(r['target'] for r in train)<30 or len(valid)<100 or int(yv.sum())<10:raise RuntimeError('Prespecified development data gate failed')
        selection=[]
        for name in CANDIDATES:
            obj=fit(name,train);p=predict(obj,valid);selection.append({'candidate':name,**metrics(yv,p)})
        # Lower log loss wins, ties at 1e-12 favor listed simpler baseline order.
        winner=CANDIDATES[0];best=selection[0]['log_loss']
        for s in selection[1:]:
            if s['log_loss']<best-1e-12:winner=s['candidate'];best=s['log_loss']
        final_names=list(dict.fromkeys(['global_rate','market_rate','activity_logit',winner]));bundle={name:fit(name,rr) for name in final_names}
        joblib.dump({'models':bundle,'selected':winner,'features':FEATURES,'activity_indices':ACTIVITY},out/'frozen_models.joblib')
        write(out/'selection.json',{'at':now().isoformat(),'train_dates':['2026-04-21','2026-04-22','2026-04-23'],'selection_date':'2026-04-24','train_rows':len(train),'train_positives':sum(r['target'] for r in train),'selection_rows':len(valid),'selection_positives':int(yv.sum()),'selected':winner,'candidates':selection,'refit_rows':len(rr),'refit_positives':sum(r['target'] for r in rr),'test_dates':['2026-04-28','2026-04-29','2026-04-30'],'no_Apr25_27_used':True})
        print(json.dumps(json.loads((out/'selection.json').read_text()),indent=2),flush=True)
    except Exception as e:write(out/'failure.json',{'error':type(e).__name__,'message':str(e)});raise
    finally:save_manifest(out,[REL/'implementation_manifest.json',OLD/'capture_manifest.json'])


def evaluate():
    verify_originals();verify(REL/'implementation_manifest.json');verify(BASE/'development/manifest.json');verify(NEW/'capture_manifest.json')
    out=BASE/'evaluation';out.mkdir(exist_ok=False)
    write(out/'consumption_receipt.json',{'at':now().isoformat(),'status':'started','period':'2026-04-28..30','scope':'new historical time block,not prospective','model_sha256':sha(BASE/'development/frozen_models.joblib')})
    try:
        rows=build_panel(NEW,['2026-04-28','2026-04-29','2026-04-30']);pq.write_table(pa.Table.from_pylist(rows),out/'grid_ledger.parquet')
        rr=[r for r in rows if r['endpoint_eligible']];_,y=arrays(rr);frozen=joblib.load(BASE/'development/frozen_models.joblib');selected=frozen['selected'];pred={n:predict(m,rr) for n,m in frozen['models'].items()}
        primary={n:metrics(y,p) for n,p in pred.items()};strict=np.array([r['strict_eligible'] for r in rr],dtype=bool)
        secondary={n:metrics(y[strict],p[strict]) for n,p in pred.items()}
        groups=[]
        for field in ['date','market_id']:
            for value in sorted({r[field] for r in rr}):
                mask=np.array([r[field]==value for r in rr]);groups.append({'group_by':field,'group':value,'models':{n:metrics(y[mask],p[mask]) for n,p in pred.items()}})
        calibration=[]
        for name,p in pred.items():
            for low,high in zip([0,.05,.1,.2,.4,.6,.8],[.05,.1,.2,.4,.6,.8,1.00001]):
                mask=(p>=low)&(p<high);n=int(mask.sum())
                calibration.append({'model':name,'lower':low,'upper':min(high,1),'n':n,'mean_prediction':float(p[mask].mean()) if n else None,'observed_rate':float(y[mask].mean()) if n else None})
        ps=[{'market_id':r['market_id'],'date':r['date'],'decision_at':r['decision_at'],'target':int(r['target']),'strict_eligible':r['strict_eligible'],**{n:float(p[i]) for n,p in pred.items()}} for i,r in enumerate(rr)]
        pq.write_table(pa.Table.from_pylist(ps),out/'predictions.parquet');write(out/'groups.json',groups);write(out/'calibration.json',calibration)
        # Non-overlapping reporting grid, fixed in advance; no claim that this eliminates market/day dependence.
        thinned=np.array([r['t']%1800==0 for r in rr],dtype=bool);nonoverlap={n:metrics(y[thinned],p[thinned]) for n,p in pred.items()}
        differences={}
        for name in ['global_rate','market_rate','activity_logit']:
            b=primary[name]['log_loss'];a=primary[selected]['log_loss'];differences[name]={'log_loss_reduction':b-a if b is not None else None,'relative_reduction_pct':100*(b-a)/b if b else None,'brier_reduction':primary[name]['brier']-primary[selected]['brier'] if b is not None else None}
        result={'at':now().isoformat(),'scope':'frozen_new_historical_time_block_observational','selected':selected,'scheduled_grids':len(rows),'current_valid':sum(r['current_valid'] for r in rows),'eligible_rows':len(rr),'positives':int(y.sum()),'evaluation_markets':len({r['market_id'] for r in rr}),'evaluation_dates':len({r['date'] for r in rr}),'primary_models':primary,'strict_secondary':secondary,'nonoverlap_sensitivity':nonoverlap,'differences':differences,'prospective':False,'new_time_block':True,'same_cohort':True,'historical_status_verified':False,'news_tested':False,'model_promoted':False,'no_retuning':True}
        write(out/'result.json',result);write(out/'consumption_receipt.json',{'at':now().isoformat(),'status':'completed','period':'2026-04-28..30','scope':'new historical time block,not prospective','model_sha256':sha(BASE/'development/frozen_models.joblib')})
        print(json.dumps(result,indent=2),flush=True)
    except Exception as e:write(out/'failure.json',{'error':type(e).__name__,'message':str(e)});raise
    finally:save_manifest(out,[REL/'implementation_manifest.json',BASE/'development/manifest.json',NEW/'capture_manifest.json'])

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('phase',choices=['develop','evaluate']);args=parser.parse_args()
    develop() if args.phase=='develop' else evaluate()
