"""Frozen calibration and disjoint-family transport study; no base-model retraining."""
import argparse
from concurrent.futures import ThreadPoolExecutor,as_completed
from collections import Counter,defaultdict
from datetime import datetime,timezone
import hashlib,json
from pathlib import Path
import httpx,joblib
import numpy as np
import pyarrow as pa
import pyarrow.compute as pc
import pyarrow.parquet as pq
from scipy.optimize import minimize
from scipy.special import expit,logit
from eventx.v7.calibration_transport_20261025 import build_panel,fetch
from eventx.tasks.research_v7_change_probability_20261025 import predict,metrics,arrays
from eventx.tasks.run_v7_archive_week_pilot_20261025 import Cached,COLS,EX,verify
from eventx.v7.archive_ranges_20261024 import read_columns
from eventx.tasks.discover_v7_direct_pilot_20261022 import REPO_ROOT,now,sha,write,verify_originals

REL=REPO_ROOT/'eventx/release/v7/calibration_transport_20261025'
BASE=REPO_ROOT/'data/v7/calibration_transport_20261025'
OLDREL=REPO_ROOT/'eventx/release/v7/archive_week_pilot_20261025'
MODEL=REPO_ROOT/'data/v7/change_probability_20261025/development/frozen_models.joblib'
CAL_DATES=['2026-05-01','2026-05-02','2026-05-03']
TEST_DATES=['2026-05-04','2026-05-05','2026-05-06']


def freeze(out,extras=()):
    ps=[p for p in out.iterdir() if p.is_file() and p.name!='manifest.json']+list(extras)
    write(out/'manifest.json',{'files':{str(p.relative_to(REPO_ROOT)):sha(p) for p in ps}})


def prepare():
    verify_originals();verify(REL/'implementation_manifest.json');verify(OLDREL/'selection_manifest.json')
    out=BASE/'cohort';out.mkdir(parents=True,exist_ok=False)
    old=json.loads((OLDREL/'selected_markets.json').read_text())['markets'];oldids={m['market_id'] for m in old};families={e['id'] for m in old for e in m['events']}
    excluded=set(json.loads(EX.read_text()))|oldids
    first5=json.loads((REPO_ROOT/'data/v7/archive_sample_20261025_v03/attempt_20261025T011030Z_66d836/selected_before_economic_reads.json').read_text())['markets'];excluded|={m['market_id'] for m in first5}
    cache=Cached();sets=[]
    for h in ['2026-04-21T12','2026-04-21T13']:
        url='https://r2v2.pmxt.dev/polymarket_orderbook_'+h+'.parquet';meta=cache.metadata(url)
        t=read_columns(cache,url,meta,0,COLS[:5],'identity_only_cached');books=t.filter(pc.equal(t['event_type'],'book'));counts=Counter(x.decode() for x in books['market'].to_pylist());ids=sorted(x.decode() for x in t['market'].unique().to_pylist())
        sets.append({c for c,n in counts.items() if n>=2 and c not in excluded and c not in [ids[0],ids[-1]]})
    candidates=sorted(set.intersection(*sets),key=lambda c:hashlib.sha256(('transport-v1:'+c).encode()).hexdigest())[:160]
    write(out/'candidates_before_metadata.json',candidates);chosen=[];receipts=[];seenfamilies=set(families)
    with httpx.Client(timeout=30) as client:
        for cid in candidates:
            rec={'market_id':cid,'requests':[]}
            try:
                for query in [{'condition_ids':cid},{'condition_ids':cid,'closed':'true'}]:
                    response=client.get('https://gamma-api.polymarket.com/markets',params=query);rec['requests'].append({'at':now().isoformat(),'query':query,'http_status':response.status_code,'sha256':hashlib.sha256(response.content).hexdigest()});response.raise_for_status();raw=response.json()
                    if raw!=[]:break
                if not isinstance(raw,list) or len(raw)!=1 or raw[0].get('conditionId')!=cid:raise ValueError('identity')
                m=raw[0];tok=m.get('clobTokenIds');oc=m.get('outcomes')
                if isinstance(tok,str):tok=json.loads(tok)
                if isinstance(oc,str):oc=json.loads(oc)
                ev=[{k:e.get(k) for k in ['id','title','slug']} for e in m.get('events',[])];ids={e['id'] for e in ev if e['id']}
                keep={k:m.get(k) for k in ['question','description','startDate','endDate','active','closed','acceptingOrders']};keep.update(market_id=cid,token_ids=tok,outcomes=oc,events=ev);rec['metadata']=keep
                start=datetime.fromisoformat(m['startDate'].replace('Z','+00:00'));end=datetime.fromisoformat(m['endDate'].replace('Z','+00:00'))
                good=oc==['Yes','No'] and isinstance(tok,list) and len(tok)==2 and bool(m.get('description')) and bool(ids) and not ids&seenfamilies and start<datetime(2026,5,1,tzinfo=timezone.utc) and end>datetime(2026,5,7,tzinfo=timezone.utc)
                rec['selected']=good
                if good:chosen.append(keep);seenfamilies|=ids
            except Exception as e:rec['error']=type(e).__name__
            receipts.append(rec);write(out/'metadata_receipts.json',receipts)
            if len(chosen)>=10:break
    if len(chosen)!=10:
        freeze(out,[REL/'implementation_manifest.json']);raise RuntimeError('Insufficient new families; no silent expansion')
    write(out/'cohorts.json',{'at':now().isoformat(),'original':old,'transport':chosen,'contract_overlap':0,'known_event_id_overlap':0,'selection_before_new_prices':True})
    freeze(out,[REL/'implementation_manifest.json',OLDREL/'selection_manifest.json'])
    print(json.dumps({'selected_new':len(chosen),'lookups':len(receipts),'questions':[m['question'] for m in chosen]},indent=2),flush=True)


def capture(stage):
    verify_originals();verify(REL/'implementation_manifest.json');verify(BASE/'cohort/manifest.json')
    cohorts=json.loads((BASE/'cohort/cohorts.json').read_text());selected=cohorts['original'] if stage=='cal' else cohorts['original']+cohorts['transport'];dates=CAL_DATES if stage=='cal' else TEST_DATES
    if stage=='test':verify(BASE/'calibration/manifest.json')
    out=BASE/('source_'+stage);out.mkdir(exist_ok=True);(out/'hours').mkdir(exist_ok=True)
    excluded=set(json.loads(EX.read_text()));hours=[d+f'T{h:02d}' for d in dates for h in range(24)];receipts=[]
    with ThreadPoolExecutor(max_workers=2) as pool:
        fs={pool.submit(fetch,h,selected,excluded,out):h for h in hours}
        for future in as_completed(fs):
            r=future.result();receipts.append(r);status={'at':now().isoformat(),'stage':stage,'phase':'capturing','pid':__import__('os').getpid(),'completed':len(receipts),'successful':sum(r['complete'] for r in receipts),'new_bytes':sum(r['archive_bytes'] for r in receipts),'last_hour':r['hour']};write(out/'status.json',status);write(out/'file_receipts.json',sorted(receipts,key=lambda r:r['hour']))
            if len(receipts)%12==0 or not r['complete']:print(json.dumps(status),flush=True)
    result={'at':now().isoformat(),'stage':stage,'phase':'captured','files':72,'successful_files':sum(r['complete'] for r in receipts),'archive_bytes':sum(r['archive_bytes'] for r in receipts),'events':sum(r.get('retained_rows',0) for r in receipts),'excluded_pre_holdout_rows_decoded':sum(r.get('excluded_pre_holdout_rows_decoded',0) for r in receipts),'protected_period_rows_read':0}
    write(out/'capture_report.json',result);write(out/'status.json',result)
    paths=[out/'capture_report.json',out/'file_receipts.json',REL/'implementation_manifest.json',BASE/'cohort/manifest.json']+list((out/'hours').glob('*/manifest.json'))
    if stage=='test':paths.append(BASE/'calibration/manifest.json')
    write(out/'capture_manifest.json',{'files':{str(p.relative_to(REPO_ROOT)):sha(p) for p in paths}})
    print(json.dumps(result,indent=2),flush=True)


def transform(p,params):return np.clip(expit(params['a']*logit(np.clip(p,1e-6,1-1e-6))+params['b']),1e-6,1-1e-6)


def calibrator(kind,p,y):
    if kind=='identity':return {'kind':kind,'a':1.,'b':0.}
    z=logit(np.clip(p,1e-6,1-1e-6))
    def objective(v):
        a,b=(1.,v[0]) if kind=='intercept' else v
        q=a*z+b
        return float(np.mean(np.logaddexp(0,q)-y*q)+.001*((a-1)**2+b*b))
    x0=[0.] if kind=='intercept' else [1.,0.];bounds=[(-5,5)] if kind=='intercept' else [(.05,5),(-5,5)]
    r=minimize(objective,x0,bounds=bounds,method='L-BFGS-B')
    if not r.success:raise RuntimeError('Calibration optimizer failed')
    a,b=(1.,r.x[0]) if kind=='intercept' else r.x
    return {'kind':kind,'a':float(a),'b':float(b),'penalty':.001}


def calibrate():
    verify(REL/'implementation_manifest.json');verify(BASE/'cohort/manifest.json')
    out=BASE/'calibration';out.mkdir(exist_ok=False);cohorts=json.loads((BASE/'cohort/cohorts.json').read_text())
    try:
        ledger=build_panel(BASE/'source_cal',CAL_DATES,cohorts['original']);pq.write_table(pa.Table.from_pylist(ledger),out/'grid_ledger.parquet');rows=[r for r in ledger if r['endpoint_eligible']]
        train=[r for r in rows if r['date']<='2026-05-02'];valid=[r for r in rows if r['date']=='2026-05-03'];frozen=joblib.load(MODEL);model=frozen['models'][frozen['selected']]
        p=predict(model,train);pv=predict(model,valid);_,y=arrays(train);_,yv=arrays(valid)
        sufficient=len(train)>=500 and y.sum()>=30 and (len(y)-y.sum())>=30 and len(valid)>=100 and yv.sum()>=10 and (len(yv)-yv.sum())>=10
        selection=[];chosen='identity';best=float('inf')
        for kind in ['identity','intercept','sigmoid']:
            if kind!='identity' and not sufficient:selection.append({'kind':kind,'status':'gate_failed'});continue
            params=calibrator(kind,p,y);m=metrics(yv,transform(pv,params));selection.append({'kind':kind,'params':params,**m})
            if m['log_loss'] is not None and m['log_loss']<best-1e-12:best=m['log_loss'];chosen=kind
        allp=predict(model,rows);_,ally=arrays(rows);params=calibrator(chosen,allp,ally)
        rate=(int(ally.sum())+1)/(len(ally)+2)
        write(out/'frozen_calibration.json',{'at':now().isoformat(),'selected':chosen,'params':params,'updated_global_rate':rate,'original_model_sha256':sha(MODEL),'base_model_unchanged':True,'cohort_manifest_sha256':sha(BASE/'cohort/manifest.json')})
        write(out/'selection.json',{'at':now().isoformat(),'fit_rows':len(train),'fit_positives':int(y.sum()),'selection_rows':len(valid),'selection_positives':int(yv.sum()),'refit_rows':len(rows),'refit_positives':int(ally.sum()),'sufficient':sufficient,'chosen':chosen,'candidates':selection,'original_only':True})
        print(json.dumps(json.loads((out/'selection.json').read_text()),indent=2),flush=True)
    finally:freeze(out,[REL/'implementation_manifest.json',BASE/'source_cal/capture_manifest.json',MODEL,BASE/'cohort/manifest.json'])


def evaluate():
    verify(REL/'implementation_manifest.json');verify(BASE/'calibration/manifest.json');verify(BASE/'cohort/manifest.json')
    out=BASE/'evaluation';out.mkdir(exist_ok=False)
    write(out/'consumption_receipt.json',{'at':now().isoformat(),'status':'started','dates':TEST_DATES,'scope':'historical temporal and disjoint-family transfer'})
    try:
        cohorts=json.loads((BASE/'cohort/cohorts.json').read_text());newids={m['market_id'] for m in cohorts['transport']};selected=cohorts['original']+cohorts['transport']
        ledger=build_panel(BASE/'source_test',TEST_DATES,selected)
        for r in ledger:r['cohort']='transport' if r['market_id'] in newids else 'original'
        pq.write_table(pa.Table.from_pylist(ledger),out/'grid_ledger.parquet');rows=[r for r in ledger if r['endpoint_eligible']];_,y=arrays(rows)
        models=joblib.load(MODEL)['models'];cal=json.loads((BASE/'calibration/frozen_calibration.json').read_text());assert cal['original_model_sha256']==sha(MODEL)
        predictions={n:predict(m,rows) for n,m in models.items()};predictions['calibrated_hgb7']=transform(predictions['hgb7'],cal['params']);predictions['updated_global_rate']=np.full(len(rows),cal['updated_global_rate'])
        results={}
        for cohort in ['original','transport','all']:
            mask=np.array([r['cohort']==cohort or cohort=='all' for r in rows]);strict=mask&np.array([r['strict_eligible'] for r in rows]);thin=mask&np.array([r['t']%1800==0 for r in rows]);ll=[r for r in ledger if r['cohort']==cohort or cohort=='all']
            results[cohort]={'scheduled':len(ll),'current_valid':sum(r['current_valid'] for r in ll),'eligible':int(mask.sum()),'markets':len({r['market_id'] for r in rows if r['cohort']==cohort or cohort=='all'}),'primary':{n:metrics(y[mask],p[mask]) for n,p in predictions.items()},'strict_secondary':{n:metrics(y[strict],p[strict]) for n,p in predictions.items()},'nonoverlap':{n:metrics(y[thin],p[thin]) for n,p in predictions.items()}}
        groups=[]
        for field in ['date','market_id']:
            for value in sorted({r[field] for r in rows}):
                for cohort in ['original','transport']:
                    mask=np.array([r[field]==value and r['cohort']==cohort for r in rows]);
                    if mask.sum():groups.append({'field':field,'value':value,'cohort':cohort,'models':{n:metrics(y[mask],p[mask]) for n,p in predictions.items()}})
        bins=[]
        for cohort in ['original','transport']:
            cm=np.array([r['cohort']==cohort for r in rows])
            for name in ['hgb7','calibrated_hgb7']:
                p=predictions[name]
                for lo,hi in zip([0,.05,.1,.2,.4,.6,.8],[.05,.1,.2,.4,.6,.8,1.00001]):
                    mask=cm&(p>=lo)&(p<hi);n=int(mask.sum());bins.append({'cohort':cohort,'model':name,'lo':lo,'hi':min(hi,1),'n':n,'mean_prediction':float(p[mask].mean()) if n else None,'observed_rate':float(y[mask].mean()) if n else None})
        ps=[{'date':r['date'],'market_id':r['market_id'],'cohort':r['cohort'],'decision_at':r['decision_at'],'target':int(r['target']),'strict_eligible':r['strict_eligible'],**{n:float(p[i]) for n,p in predictions.items()}} for i,r in enumerate(rows)]
        pq.write_table(pa.Table.from_pylist(ps),out/'predictions.parquet');write(out/'groups.json',groups);write(out/'calibration_bins.json',bins)
        result={'at':now().isoformat(),'calibrator':cal,'cohort_results':results,'base_model_retrained':False,'old_evaluations_reused':False,'new_contract_event_id_overlap':0,'prospective':False,'statistical_significance_claim':False,'model_promoted':False}
        write(out/'result.json',result);write(out/'consumption_receipt.json',{'at':now().isoformat(),'status':'completed','dates':TEST_DATES,'scope':'historical temporal and disjoint-family transfer'})
        print(json.dumps(result,indent=2),flush=True)
    finally:freeze(out,[REL/'implementation_manifest.json',BASE/'calibration/manifest.json',BASE/'source_test/capture_manifest.json',BASE/'cohort/manifest.json'])

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('phase',choices=['prepare','capture_cal','calibrate','capture_test','evaluate']);a=p.parse_args()
    {'prepare':prepare,'capture_cal':lambda:capture('cal'),'calibrate':calibrate,'capture_test':lambda:capture('test'),'evaluate':evaluate}[a.phase]()
