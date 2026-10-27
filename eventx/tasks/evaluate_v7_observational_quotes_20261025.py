"""Frozen chronological development study of archived quotes, not tradable forecasts."""
from bisect import bisect_right
from collections import Counter,defaultdict
from datetime import datetime,timedelta
import json
import math
from pathlib import Path
import joblib
import numpy as np
import pyarrow as pa
import pyarrow.parquet as pq
from sklearn.ensemble import HistGradientBoostingRegressor
from sklearn.linear_model import Ridge
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler
from eventx.tasks.run_v7_archive_fullweek_20261025 import BASE as SOURCE, REL, OLDREL
from eventx.tasks.run_v7_archive_week_pilot_20261025 import DATES, verify
from eventx.tasks.discover_v7_direct_pilot_20261022 import REPO_ROOT, now, sha, write, verify_originals

OUT=REPO_ROOT/'data/v7/observational_quote_development_20261025'
FEATURES=['midpoint','spread','delta5','delta15','delta30','volatility30','minimum30','maximum30','source_age','receive_age','updates30','hour_sin','hour_cos']
CANDIDATES=['persistence','drift_0.1','drift_0.25','ridge_1','ridge_100','hgb_absolute']


def states_from(rows):
    groups=defaultdict(list)
    for r in rows:groups[r['timestamp_received']].append(r)
    states=[]
    for received,rs in sorted(groups.items()):
        qs=[r for r in rs if r['best_bid'] is not None and r['best_ask'] is not None]
        pairs={(float(r['best_bid']),float(r['best_ask'])) for r in qs};reason='valid';b=a=oldest=None
        if not qs:reason='no_direct_quote'
        elif len(pairs)!=1:reason='conflicting_tie'
        else:
            b,a=next(iter(pairs));oldest=min(r['timestamp'].timestamp() for r in qs)
            if not 0<b<=a<1:reason='invalid_or_terminal_price'
            elif a-b>.05+1e-12:reason='wide_spread'
            elif any(not 0<=(received-r['timestamp']).total_seconds()<=120 for r in qs):reason='source_clock_or_age'
        states.append({'at':received.timestamp(),'source':oldest,'valid':reason=='valid','reason':reason,'midpoint':(a+b)/2 if a is not None else None,'spread':a-b if a is not None else None})
    return states


def grids_for(states,date,cid,successful,hours=(0,24)):
    times=[s['at'] for s in states];day=datetime.fromisoformat(date+'T00:00:00+00:00').timestamp()
    def at(t):
        i=bisect_right(times,t)-1
        if i<0:return None
        s=states[i]
        return s if s['valid'] and 0<=t-s['at']<=120 and t-s['source']<=120 else None
    def covers(a,b):
        if not at(a):return False
        i,j=bisect_right(times,a),bisect_right(times,b);prev=states[i-1]
        for k in range(i,j):
            s=states[k]
            if not s['valid'] or s['at']-prev['at']>120 or s['at']-prev['source']>120:return False
            prev=s
        return b-prev['at']<=120 and b-prev['source']<=120
    def files_ok(a,b):
        return all(date+f'T{h:02d}' in successful for h in range(int((a-day)//3600),int((b-day)//3600)+1))
    output=[]
    for t in range(int(day+hours[0]*3600+1800),int(day+hours[1]*3600-1800),300):
        row={'date':date,'market_id':cid,'decision_at':datetime.fromtimestamp(t,__import__('datetime').timezone.utc).isoformat(),'t':t,'features':None,'target':None}
        current=at(t);end=at(t+1800)
        current_ok=files_ok(t,t) and current is not None
        pairs=files_ok(t,t+1800) and current is not None and end is not None
        history=files_ok(t-1800,t) and covers(t-1800,t)
        forward=files_ok(t,t+1800) and covers(t,t+1800)
        complete=history and forward
        row.update(fresh_current=current_ok,fresh_pairs=pairs,history_valid=history,forward_valid=forward,complete=complete,
                   missing_file=not files_ok(t-1800,t+1800))
        if history:
            sampled=[at(t-d*300)['midpoint'] for d in reversed(range(7))]
            i,j=bisect_right(times,t-1800),bisect_right(times,t)
            history_mid=[at(t-1800)['midpoint']]+[s['midpoint'] for s in states[i:j]]
            hour=(t-day)/3600
            row['features']=[current['midpoint'],current['spread'],sampled[-1]-sampled[-2],sampled[-1]-sampled[-4],sampled[-1]-sampled[0],float(np.std(np.diff(sampled))),min(history_mid),max(history_mid),t-current['source'],t-current['at'],j-i,math.sin(2*math.pi*hour/24),math.cos(2*math.pi*hour/24)]
            if not np.isfinite(row['features']).all():raise RuntimeError('Nonfinite features')
        if complete:row['target']=end['midpoint']
        output.append(row)
    return output


def estimator(name):
    if name.startswith('ridge_'):return make_pipeline(StandardScaler(),Ridge(alpha=float(name.split('_')[1])))
    if name=='hgb_absolute':return HistGradientBoostingRegressor(loss='absolute_error',max_iter=100,learning_rate=.05,max_leaf_nodes=7,min_samples_leaf=50,l2_regularization=10,early_stopping=False,random_state=20261025)
    return None


def predict(name,model,x):
    if name=='persistence':pred=x[:,0]
    elif name.startswith('drift_'):pred=x[:,0]+float(name.split('_')[1])*x[:,4]
    else:pred=x[:,0]+model.predict(x)
    return np.clip(pred,0,1)


def scores(y,p):
    if len(y)==0:return {'n':0,'mae':None,'rmse':None}
    return {'n':len(y),'mae':float(np.mean(np.abs(y-p))),'rmse':float(np.sqrt(np.mean((y-p)**2)))}


def main():
    verify_originals();verify(REL/'implementation_manifest.json');verify(REL/'evaluation_implementation_manifest.json');verify(SOURCE/'capture_manifest.json')
    if OUT.exists():raise RuntimeError('One-shot development run already exists; do not rerun')
    OUT.mkdir();write(OUT/'consumption_receipt.json',{'at':now().isoformat(),'status':'started','scope':'chronological_development_only','not_protected_holdout':True})
    for p in (SOURCE/'hours').glob('*/manifest.json'):verify(p)
    selected=json.loads((OLDREL/'selected_markets.json').read_text())['markets'];receipts=json.loads((SOURCE/'file_receipts.json').read_text());successful={r['hour'] for r in receipts if r['complete']}
    ledger=[];parity=[]
    prior=json.loads((REPO_ROOT/'data/v7/archive_week_pilot_20261025/capture/market_day_metrics.json').read_text())
    try:
        for date in DATES:
            by=defaultdict(list)
            for h in range(24):
                p=SOURCE/'hours'/(date+f'T{h:02d}')/'quotes.parquet'
                if date+f'T{h:02d}' in successful and p.exists():
                    for r in pq.read_table(p).to_pylist():by[r['market'].decode()].append(r)
            for m in selected:
                cid=m['market_id'];states=states_from(by[cid]);ledger.extend(grids_for(states,date,cid,successful))
                # Reproduce old 12-14 coverage from exactly the original input interval.
                subset=[s for s in states if datetime.fromtimestamp(s['at'],__import__('datetime').timezone.utc).hour in [12,13]]
                oldgrids=grids_for(subset,date,cid,successful,(12,14));old=next(r for r in prior if r['date']==date and r['market_id']==cid)
                pairs=[('fresh_current','fresh_current'),('fresh_pairs','fresh_pairs'),('forward_valid','continuous_forward'),('complete','continuous_history_forward')]
                for k,pk in pairs:
                    value=sum(r[k] for r in oldgrids)
                    if value!=old[pk]:raise RuntimeError('Pilot parity failed: '+str((date,cid,k,value,old[pk])))
                parity.append({'date':date,'market_id':cid,'passed':True})
            print(json.dumps({'date':date,'grids':len(ledger),'complete':sum(r['complete'] for r in ledger)}),flush=True)
        assert len(ledger)==38640 and len({(r['market_id'],r['t']) for r in ledger})==38640
        pq.write_table(pa.Table.from_pylist(ledger),OUT/'grid_ledger.parquet')
        write(OUT/'parity.json',parity)
        coverage={'at':now().isoformat(),'scheduled_grids':len(ledger),'fresh_current':sum(r['fresh_current'] for r in ledger),'fresh_pairs':sum(r['fresh_pairs'] for r in ledger),'history_eligible':sum(r['history_valid'] for r in ledger),'continuous_forward':sum(r['forward_valid'] for r in ledger),'observational_complete_rows':sum(r['complete'] for r in ledger),'missing_file_grids':sum(r['missing_file'] for r in ledger),'legacy_tradable_admissions':0,'historical_status_verified':False,'observational_scope_only':True}
        write(OUT/'coverage.json',coverage)
        complete=[r for r in ledger if r['complete']]
        train=[r for r in complete if r['date']<='2026-04-23'];valid=[r for r in complete if r['date']=='2026-04-24'];test=[r for r in complete if r['date']>='2026-04-25']
        def arrays(rr):return np.asarray([r['features'] for r in rr],dtype=float).reshape(-1,len(FEATURES)),np.asarray([r['target'] for r in rr],dtype=float)
        xt,yt=arrays(train);xv,yv=arrays(valid);xe,ye=arrays(test)
        minimum=len(train)>=100 and len(valid)>=30 and len({r['market_id'] for r in valid})>=3
        selection=[];models={}
        for name in CANDIDATES:
            if not minimum and name!='persistence':selection.append({'candidate':name,'status':'not_fit_minimum_gate_failed'});continue
            model=estimator(name)
            if model is not None:model.fit(xt,yt-xt[:,0])
            models[name]=model;pred=predict(name,model,xv) if len(valid) else np.array([])
            selection.append({'candidate':name,'status':'scored',**scores(yv,pred)})
        chosen='persistence';best=next(s['mae'] for s in selection if s['candidate']=='persistence')
        if minimum:
            for r in selection[1:]:
                if r['mae']<best-1e-15:chosen=r['candidate'];best=r['mae']
        write(OUT/'selection_before_evaluation.json',{'at':now().isoformat(),'minimum_gate_passed':minimum,'train_rows':len(train),'selection_rows':len(valid),'selection_markets':len({r['market_id'] for r in valid}),'selected':chosen,'candidates':selection})
        fit=train+valid;xf,yf=arrays(fit);final=estimator(chosen)
        if final is not None:final.fit(xf,yf-xf[:,0])
        # Persist selected model/feature order and receipt BEFORE calculating evaluation errors.
        joblib.dump({'candidate':chosen,'estimator':final,'features':FEATURES,'protocol':str(REL/'observational_protocol.json')},OUT/'selected_model.joblib')
        write(OUT/'evaluation_receipt.json',{'at':now().isoformat(),'scope':'development_evaluation_Apr25_27','model_sha256':sha(OUT/'selected_model.joblib'),'selection_sha256':sha(OUT/'selection_before_evaluation.json'),'status':'opening_once'})
        bp=xe[:,0] if len(test) else np.array([]);pred=predict(chosen,final,xe) if len(test) else np.array([])
        ps=[]
        for row,b,p in zip(test,bp,pred):
            ps.append({'market_id':row['market_id'],'date':row['date'],'decision_at':row['decision_at'],'target':row['target'],'persistence':float(b),'selected_prediction':float(p)})
        pq.write_table(pa.Table.from_pylist(ps),OUT/'evaluation_predictions.parquet')
        groups=[]
        for field in ['date','market_id']:
            for value in sorted({r[field] for r in test}):
                mask=np.asarray([r[field]==value for r in test]);groups.append({'group_by':field,'group':value,'baseline':scores(ye[mask],bp[mask]),'selected':scores(ye[mask],pred[mask])})
        write(OUT/'evaluation_groups.json',groups)
        changed=np.abs(ye-bp)>1e-12
        result={'at':now().isoformat(),'scope':'observational_chronological_development_not_prospective','selected':chosen,'training_rows':len(train),'selection_rows':len(valid),'evaluation_rows':len(test),'evaluation_markets':len({r['market_id'] for r in test}),'evaluation_dates':len({r['date'] for r in test}),'persistence':scores(ye,bp),'selected_model':scores(ye,pred),'changed_rows':int(changed.sum()),'unchanged_rows':int((~changed).sum()),'changed_diagnostic':{'persistence':scores(ye[changed],bp[changed]),'selected':scores(ye[changed],pred[changed])},'unchanged_diagnostic':{'persistence':scores(ye[~changed],bp[~changed]),'selected':scores(ye[~changed],pred[~changed])},'independent_confirmation':False,'news_tested':False,'tradability_claim':False,'model_promoted':False,'intervals_reported':False}
        base=result['persistence']['mae'];cand=result['selected_model']['mae'];result['mae_reduction']=base-cand if base is not None else None;result['relative_mae_reduction_pct']=100*(base-cand)/base if base else None
        write(OUT/'result.json',result);write(OUT/'consumption_receipt.json',{'at':now().isoformat(),'status':'completed','scope':'chronological_development_only','not_protected_holdout':True})
        print(json.dumps(result,indent=2),flush=True)
    except Exception as e:
        write(OUT/'failure.json',{'at':now().isoformat(),'error':type(e).__name__,'message':str(e)[:240]});raise
    finally:
        paths=[p for p in OUT.iterdir() if p.is_file()]+[REL/'evaluation_implementation_manifest.json',SOURCE/'capture_manifest.json']
        write(OUT/'manifest.json',{'files':{str(p.relative_to(REPO_ROOT)):sha(p) for p in paths}})

if __name__=='__main__':main()
