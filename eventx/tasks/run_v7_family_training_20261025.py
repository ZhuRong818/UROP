"""Broader family training, fixed weighting ablation, and fresh time/family test."""
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
from sklearn.ensemble import HistGradientBoostingClassifier
from eventx.v7.calibration_transport_20261025 import build_panel,fetch
from eventx.tasks.research_v7_change_probability_20261025 import fit,predict,metrics,arrays,FEATURES
from eventx.tasks.run_v7_archive_week_pilot_20261025 import Cached,COLS,EX,verify
from eventx.v7.archive_ranges_20261024 import read_columns
from eventx.tasks.discover_v7_direct_pilot_20261022 import REPO_ROOT,now,sha,write,verify_originals

BASE=REPO_ROOT/'data/v7/family_training_20261025'
REL=REPO_ROOT/'eventx/release/v7/family_training_20261025'
PRIOR=REPO_ROOT/'data/v7/calibration_transport_20261025/cohort'
LEGACY=REPO_ROOT/'data/v7/change_probability_20261025/development/frozen_models.joblib'
DEV=['2026-05-07','2026-05-08','2026-05-09'];TEST=['2026-05-10','2026-05-11','2026-05-12']
CANDIDATES=['global_rate','market_rate','activity_logit','row_hgb7','family_hgb7','blend_hgb7']


def freeze(out,extra=()):
    ps=[p for p in out.iterdir() if p.is_file() and p.name!='manifest.json']+list(extra)
    write(out/'manifest.json',{'files':{str(p.relative_to(REPO_ROOT)):sha(p) for p in ps}})


def prepare():
    verify_originals();verify(REL/'implementation_manifest.json');verify(PRIOR/'manifest.json')
    out=BASE/'cohort';out.mkdir(parents=True,exist_ok=False)
    prior=json.loads((PRIOR/'cohorts.json').read_text());old=prior['original']+prior['transport'];ids={m['market_id'] for m in old};families={e['id'] for m in old for e in m['events']}
    excluded=set(json.loads(EX.read_text()))|ids
    five=json.loads((REPO_ROOT/'data/v7/archive_sample_20261025_v03/attempt_20261025T011030Z_66d836/selected_before_economic_reads.json').read_text())['markets'];excluded|={m['market_id'] for m in five}
    cache=Cached();sets=[]
    for hour in ['2026-04-21T12','2026-04-21T13']:
        url='https://r2v2.pmxt.dev/polymarket_orderbook_'+hour+'.parquet';meta=cache.metadata(url);t=read_columns(cache,url,meta,0,COLS[:5],'cached_identity_only');books=t.filter(pc.equal(t['event_type'],'book'));counts=Counter(x.decode() for x in books['market'].to_pylist());allids=sorted(x.decode() for x in t['market'].unique().to_pylist())
        sets.append({c for c,n in counts.items() if n>=2 and c not in excluded and c not in [allids[0],allids[-1]]})
    candidates=sorted(set.intersection(*sets),key=lambda c:hashlib.sha256(('family-training-v1:'+c).encode()).hexdigest())[:240];write(out/'candidates_before_metadata.json',candidates)
    chosen=[];receipts=[];seen=set(families)
    with httpx.Client(timeout=30) as client:
        for cid in candidates:
            rec={'market_id':cid,'requests':[]}
            try:
                for query in [{'condition_ids':cid},{'condition_ids':cid,'closed':'true'}]:
                    r=client.get('https://gamma-api.polymarket.com/markets',params=query);rec['requests'].append({'at':now().isoformat(),'query':query,'status':r.status_code,'sha256':hashlib.sha256(r.content).hexdigest()});r.raise_for_status();raw=r.json()
                    if raw!=[]:break
                if not isinstance(raw,list) or len(raw)!=1 or raw[0].get('conditionId')!=cid:raise ValueError('identity')
                m=raw[0];tokens=m.get('clobTokenIds');outcomes=m.get('outcomes')
                if isinstance(tokens,str):tokens=json.loads(tokens)
                if isinstance(outcomes,str):outcomes=json.loads(outcomes)
                events=[{k:e.get(k) for k in ['id','title','slug']} for e in m.get('events',[])];ev={e['id'] for e in events if e['id']}
                keep={k:m.get(k) for k in ['question','description','startDate','endDate','active','closed','acceptingOrders']};keep.update(market_id=cid,token_ids=tokens,outcomes=outcomes,events=events);rec['metadata']=keep
                start=datetime.fromisoformat(m['startDate'].replace('Z','+00:00'));end=datetime.fromisoformat(m['endDate'].replace('Z','+00:00'))
                valid=outcomes==['Yes','No'] and isinstance(tokens,list) and len(tokens)==2 and bool(m.get('description')) and bool(ev) and not ev&seen and start<datetime(2026,5,7,tzinfo=timezone.utc) and end>datetime(2026,5,13,tzinfo=timezone.utc)
                rec['selected']=bool(valid)
                if valid:chosen.append(keep);seen|=ev;rec['role']='development' if len(chosen)<=20 else 'unseen'
            except Exception as e:rec['error']=type(e).__name__
            receipts.append(rec);write(out/'metadata_receipts.json',receipts)
            if len(chosen)==30:break
    if len(chosen)!=30:freeze(out,[REL/'implementation_manifest.json']);raise RuntimeError('Fewer than30new eligible families;stop without outcome-driven replacements')
    cohorts={'at':now().isoformat(),'prior30':old,'added20':chosen[:20],'unseen10':chosen[20:],'development50':old+chosen[:20],'selection_before_new_prices':True}
    # No shared current event IDs between development and unseen sets.
    a={e['id'] for m in cohorts['development50'] for e in m['events']};b={e['id'] for m in cohorts['unseen10'] for e in m['events']};assert not a&b
    write(out/'cohorts.json',cohorts);freeze(out,[REL/'implementation_manifest.json',PRIOR/'manifest.json'])
    print(json.dumps({'metadata_lookups':len(receipts),'development_contracts':50,'unseen_contracts':10,'event_id_overlap':0,'new_questions':[m['question'] for m in chosen]},indent=2),flush=True)


def capture(stage):
    verify_originals();verify(REL/'implementation_manifest.json');verify(BASE/'cohort/manifest.json');co=json.loads((BASE/'cohort/cohorts.json').read_text())
    if stage=='test':verify(BASE/'development/manifest.json')
    selected=co['development50'] if stage=='dev' else co['development50']+co['unseen10'];dates=DEV if stage=='dev' else TEST
    out=BASE/('source_'+stage);out.mkdir(exist_ok=True);(out/'hours').mkdir(exist_ok=True);excluded=set(json.loads(EX.read_text()));receipts=[]
    with ThreadPoolExecutor(max_workers=2) as pool:
        futures=[pool.submit(fetch,d+f'T{h:02d}',selected,excluded,out) for d in dates for h in range(24)]
        for f in as_completed(futures):
            r=f.result();receipts.append(r);st={'at':now().isoformat(),'phase':'capturing','stage':stage,'pid':__import__('os').getpid(),'completed':len(receipts),'successful':sum(x['complete'] for x in receipts),'bytes':sum(x['archive_bytes'] for x in receipts),'last_hour':r['hour']};write(out/'status.json',st);write(out/'file_receipts.json',sorted(receipts,key=lambda r:r['hour']))
            if len(receipts)%12==0 or not r['complete']:print(json.dumps(st),flush=True)
    report={'at':now().isoformat(),'phase':'captured','stage':stage,'files':72,'successful_files':sum(r['complete'] for r in receipts),'archive_bytes':sum(r['archive_bytes'] for r in receipts),'events':sum(r.get('retained_rows',0) for r in receipts),'excluded_pre_holdout_rows_decoded':sum(r.get('excluded_pre_holdout_rows_decoded',0) for r in receipts),'protected_period_rows_read':0}
    write(out/'capture_report.json',report);write(out/'status.json',report)
    paths=[out/'capture_report.json',out/'file_receipts.json',REL/'implementation_manifest.json',BASE/'cohort/manifest.json']+list((out/'hours').glob('*/manifest.json'))
    if stage=='test':paths.append(BASE/'development/manifest.json')
    write(out/'capture_manifest.json',{'files':{str(p.relative_to(REPO_ROOT)):sha(p) for p in paths}});print(json.dumps(report,indent=2),flush=True)


def family_map(co):
    return {m['market_id']:'|'.join(sorted(e['id'] for e in m['events'])) for m in co['development50']+co['unseen10']}


def weights(rows,fmap):
    counts=Counter(fmap[r['market_id']] for r in rows);n=len(rows);f=len(counts)
    w=np.asarray([np.sqrt(n/(f*counts[fmap[r['market_id']]])) for r in rows]);w=np.clip(w,.25,4);return w/w.mean()


def learn(rows,fmap):
    models={name:fit(name,rows) for name in ['global_rate','market_rate','activity_logit']};x,y=arrays(rows)
    models['row_hgb7']=fit('hgb7',rows)
    est=HistGradientBoostingClassifier(max_iter=100,learning_rate=.05,max_leaf_nodes=7,min_samples_leaf=100,l2_regularization=10,early_stopping=False,random_state=20261025)
    est.fit(x,y,sample_weight=weights(rows,fmap));models['family_hgb7']={'name':'hgb7','rate':models['global_rate']['rate'],'estimator':est}
    return models


def probabilities(models,rows):
    p={n:predict(m,rows) for n,m in models.items()};p['blend_hgb7']=.5*p['row_hgb7']+.5*p['family_hgb7'];return p


def family_macro(rows,y,p,fmap):
    groups=defaultdict(list)
    for i,r in enumerate(rows):groups[fmap[r['market_id']]].append(i)
    if not groups:return None
    return float(np.mean([metrics(y[ix],p[ix])['log_loss'] for ix in groups.values()]))


def develop():
    verify_originals();verify(REL/'implementation_manifest.json');verify(BASE/'cohort/manifest.json');co=json.loads((BASE/'cohort/cohorts.json').read_text());fmap=family_map(co)
    out=BASE/'development';out.mkdir(exist_ok=False)
    try:
        ledger=build_panel(BASE/'source_dev',DEV,co['development50']);pq.write_table(pa.Table.from_pylist(ledger),out/'grid_ledger.parquet');rows=[r for r in ledger if r['endpoint_eligible']];train=[r for r in rows if r['date']<='2026-05-08'];valid=[r for r in rows if r['date']=='2026-05-09'];_,yt=arrays(train);_,yv=arrays(valid)
        gate=bool(len(train)>=1000 and int(yt.sum())>=50 and len(yt)-int(yt.sum())>=50 and len(valid)>=200 and int(yv.sum())>=20 and len(yv)-int(yv.sum())>=20 and len({fmap[r['market_id']] for r in train})>=8)
        if not gate:raise RuntimeError('Frozen diversity/sample gate failed')
        models=learn(train,fmap);pred=probabilities(models,valid);selection=[{'candidate':n,**metrics(yv,pred[n]),'family_macro_log_loss':family_macro(valid,yv,pred[n],fmap)} for n in CANDIDATES]
        chosen=CANDIDATES[0];best=selection[0]['log_loss']
        for row in selection[1:]:
            if row['log_loss']<best-1e-12:best=row['log_loss'];chosen=row['candidate']
        write(out/'selection_before_test.json',{'at':now().isoformat(),'selected':chosen,'gate_passed':gate,'fit_rows':len(train),'fit_positives':int(yt.sum()),'fit_families':len({fmap[r['market_id']] for r in train}),'selection_rows':len(valid),'selection_positives':int(yv.sum()),'candidates':selection,'refit_rows':len(rows),'refit_positives':sum(r['target'] for r in rows),'refit_families':len({fmap[r['market_id']] for r in rows})})
        refit=learn(rows,fmap);joblib.dump({'models':refit,'selected':chosen,'features':FEATURES,'family_map':fmap},out/'frozen_models.joblib');w=weights(rows,fmap)
        write(out/'weight_audit.json',{'min':float(w.min()),'max':float(w.max()),'mean':float(w.mean()),'family_counts':dict(Counter(fmap[r['market_id']] for r in rows)),'formula':'clip(sqrt(N/(F*n_family)),.25,4),then normalize to mean1;no class weighting','all_weights_built_on_refit_training_only':True})
        print(json.dumps(json.loads((out/'selection_before_test.json').read_text()),indent=2),flush=True)
    except Exception as e:write(out/'failure.json',{'at':now().isoformat(),'error':type(e).__name__,'message':str(e)[:240]});raise
    finally:freeze(out,[REL/'implementation_manifest.json',BASE/'cohort/manifest.json',BASE/'source_dev/capture_manifest.json'])


def evaluate():
    verify_originals();verify(REL/'implementation_manifest.json');verify(BASE/'development/manifest.json');verify(BASE/'cohort/manifest.json')
    out=BASE/'evaluation';out.mkdir(exist_ok=False);write(out/'consumption_receipt.json',{'at':now().isoformat(),'status':'started','dates':TEST,'scope':'new historical dates and unseen families'})
    try:
        co=json.loads((BASE/'cohort/cohorts.json').read_text());newids={m['market_id'] for m in co['unseen10']};oldids={m['market_id'] for m in co['prior30']};fmap=family_map(co)
        ledger=build_panel(BASE/'source_test',TEST,co['development50']+co['unseen10'])
        for r in ledger:r['cohort']='unseen10' if r['market_id'] in newids else 'prior30' if r['market_id'] in oldids else 'added20'
        pq.write_table(pa.Table.from_pylist(ledger),out/'grid_ledger.parquet');rows=[r for r in ledger if r['endpoint_eligible']];_,y=arrays(rows);bundle=joblib.load(BASE/'development/frozen_models.joblib');ps=probabilities(bundle['models'],rows);ps['legacy_hgb7']=predict(joblib.load(LEGACY)['models']['hgb7'],rows);chosen=bundle['selected']
        cohorts={}
        def mask_for(c):return np.array([c=='all' or r['cohort']==c or (c=='development50' and r['cohort']!='unseen10') for r in rows],dtype=bool)
        for c in ['development50','unseen10','prior30','added20','all']:
            mask=mask_for(c);subset=[r for r,k in zip(rows,mask) if k];strict=mask&np.array([r['strict_eligible'] for r in rows]);thin=mask&np.array([r['t']%1800==0 for r in rows]);total=[r for r in ledger if c=='all' or r['cohort']==c or (c=='development50' and r['cohort']!='unseen10')]
            cohorts[c]={'scheduled':len(total),'current_valid':sum(r['current_valid'] for r in total),'eligible':int(mask.sum()),'markets':len({r['market_id'] for r in subset}),'primary':{n:{**metrics(y[mask],p[mask]),'family_macro_log_loss':family_macro(subset,y[mask],p[mask],fmap)} for n,p in ps.items()},'strict_secondary':{n:metrics(y[strict],p[strict]) for n,p in ps.items()},'nonoverlap':{n:metrics(y[thin],p[thin]) for n,p in ps.items()}}
        groups=[]
        for field in ['date','market_id']:
            for val in sorted({r[field] for r in rows}):
                for c in ['development50','unseen10']:
                    mask=mask_for(c)&np.array([r[field]==val for r in rows])
                    if mask.any():groups.append({'field':field,'value':val,'cohort':c,'models':{n:metrics(y[mask],p[mask]) for n,p in ps.items()}})
        calibration=[]
        for c in ['development50','unseen10']:
            cm=mask_for(c)
            for name in list(dict.fromkeys([chosen,'row_hgb7','family_hgb7','legacy_hgb7'])):
                p=ps[name]
                for lo,hi in zip([0,.05,.1,.2,.4,.6,.8],[.05,.1,.2,.4,.6,.8,1.00001]):
                    mask=cm&(p>=lo)&(p<hi);n=int(mask.sum());calibration.append({'cohort':c,'model':name,'lo':lo,'hi':min(hi,1),'n':n,'mean_prediction':float(p[mask].mean()) if n else None,'observed_rate':float(y[mask].mean()) if n else None})
        pred=[{'date':r['date'],'market_id':r['market_id'],'cohort':r['cohort'],'decision_at':r['decision_at'],'target':int(r['target']),'strict_eligible':r['strict_eligible'],**{n:float(p[i]) for n,p in ps.items()}} for i,r in enumerate(rows)]
        pq.write_table(pa.Table.from_pylist(pred),out/'predictions.parquet');write(out/'groups.json',groups);write(out/'calibration_bins.json',calibration)
        result={'at':now().isoformat(),'selected':chosen,'cohort_results':cohorts,'test_dates':TEST,'old_evaluations_reused':False,'prospective':False,'automatic_promotion':False,'news_tested':False,'statistical_significance_claim':False,'family_weighting_ablation_prespecified':True}
        write(out/'result.json',result);write(out/'consumption_receipt.json',{'at':now().isoformat(),'status':'completed','dates':TEST,'scope':'new historical dates and unseen families'})
        print(json.dumps({'selected':chosen,'development50':cohorts['development50']['primary'],'unseen10':cohorts['unseen10']['primary']},indent=2),flush=True)
    except Exception as e:write(out/'failure.json',{'at':now().isoformat(),'error':type(e).__name__,'message':str(e)[:240]});raise
    finally:freeze(out,[REL/'implementation_manifest.json',BASE/'development/manifest.json',BASE/'source_test/capture_manifest.json',BASE/'cohort/manifest.json'])

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('phase',choices=['prepare','capture_dev','develop','capture_test','evaluate']);a=p.parse_args()
    {'prepare':prepare,'capture_dev':lambda:capture('dev'),'develop':develop,'capture_test':lambda:capture('test'),'evaluate':evaluate}[a.phase]()
