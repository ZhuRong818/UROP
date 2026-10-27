"""Bounded prospective quote forecasts with explicit availability and expiry."""
import fcntl
import hashlib
import json
import math
import os
import signal
import time
from eventx.tasks.discover_v7_direct_pilot_20261022 import REPO_ROOT,now,sha,write,verify_originals
from eventx.tasks.run_v7_quote_experiment_20261024 import metric
from eventx.v7.quote_experiment_20261024 import stamp,iso
from eventx.v7.memory_quote_20261024 import MemoryQuoteTape,predict

RELEASE=REPO_ROOT/'eventx/release/v7/memory_shadow_20261024'
OUT=REPO_ROOT/'data/v7/memory_quote_20261024/shadow'

def atomic(path,value):
    temp=path.with_suffix('.tmp');write(temp,value);os.replace(temp,path)

def main():
    for p,h in json.loads((RELEASE/'implementation_manifest.json').read_text())['locked_files'].items():
        if sha(REPO_ROOT/p)!=h:raise RuntimeError('Memory shadow lock mismatch')
    verify_originals();cfg=json.loads((RELEASE/'activation_policy.json').read_text())
    policy=json.loads((REPO_ROOT/cfg['quote_policy']).read_text());models=json.loads((REPO_ROOT/cfg['models']).read_text())
    samples=[json.loads(l) for l in (REPO_ROOT/cfg['cohort']).read_text().splitlines()]
    protected=set(json.loads((REPO_ROOT/'eventx/release/v7/market_capture_20261018/protected_ids.json').read_text()))
    if protected.intersection(s['market_id'] for s in samples):raise RuntimeError('Protected scope')
    source=REPO_ROOT/cfg['source_live'];source_contract=json.loads((source/'run_contract.json').read_text())
    OUT.mkdir(parents=True,exist_ok=True);lock=(OUT/'process.lock').open('a');fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
    tape=MemoryQuoteTape(source,samples,policy);journal=OUT/'journal.jsonl';rows=[];head=None;stopping=False
    if journal.exists():
        for line in journal.read_bytes().splitlines(keepends=True):
            if not line.endswith(b'\n'):raise RuntimeError('Partial journal; preserve for explicit recovery')
            r=json.loads(line);v=dict(r);h=v.pop('record_sha256')
            if v['previous_sha256']!=head or hashlib.sha256(json.dumps(v,sort_keys=True,separators=(',',':')).encode()).hexdigest()!=h:raise RuntimeError('Forecast chain mismatch')
            head=h;rows.append(r)
    def append(value):
        nonlocal head
        r={**value,'previous_sha256':head};r['record_sha256']=hashlib.sha256(json.dumps(r,sort_keys=True,separators=(',',':')).encode()).hexdigest()
        with journal.open('a') as f:f.write(json.dumps(r,sort_keys=True)+'\n');f.flush();os.fsync(f.fileno())
        head=r['record_sha256'];rows.append(r);return r
    def stop(*_):
        nonlocal stopping
        stopping=True
    signal.signal(signal.SIGINT,stop);signal.signal(signal.SIGTERM,stop)
    contract_path=OUT/'run_contract.json'
    if contract_path.exists():contract=json.loads(contract_path.read_text())
    else:
        start=math.floor(now().timestamp()/300)*300+300
        last=math.floor((stamp(source_contract['stop_at'])-1800-120)/300)*300
        contract={'activated_at':now().isoformat(),'first_grid_at':iso(start),'last_grid_at':iso(last),'stop_at':iso(last+1800+180),
            'implementation_manifest_sha256':sha(RELEASE/'implementation_manifest.json'),'models_sha256':sha(REPO_ROOT/cfg['models']),
            'source_contract_sha256':sha(source/'run_contract.json'),'scope':'Prospective quote-only feasibility; persistence reference, fixed candidates, no trading'}
        write(contract_path,contract)
    if contract['implementation_manifest_sha256']!=sha(RELEASE/'implementation_manifest.json') or contract['source_contract_sha256']!=sha(source/'run_contract.json'):raise RuntimeError('Run contract drift')
    append({'kind':'process_started','at':now().isoformat(),'pid':os.getpid(),'resumed':bool(rows)})
    done={(r['market_id'],r['grid_at']) for r in rows if r['kind']=='decision'};error=None;last_status=0
    def snapshot(phase):
        dec=[r for r in rows if r['kind']=='decision'];commits={r['decision_sha256']:r for r in rows if r['kind']=='emission_commit' and r['timely']}
        outcomes=[r for r in rows if r['kind']=='outcome'];counts={'scheduled_decisions_recorded':len(dec),'timely_forecasts':len(commits),
            'abstentions':sum(r['status']=='abstained' for r in dec),'missed':sum(r['status']=='missed' for r in dec),
            'outcomes_observed':sum(r['status']=='observed' for r in outcomes),'outcomes_unavailable':sum(r['status']!='observed' for r in outcomes)}
        latest={}
        for d in dec:
            timely=d['record_sha256'] in commits
            latest[d['market_id']]={'question':d['question'],'grid_at':d['grid_at'],'target_at':d['target_at'],
                'display_expires_at':iso(stamp(d['grid_at'])+300),'status':'forecast_recorded' if timely else d['status'] if d['status']!='ready' else 'uncommitted',
                'reasons':d['reasons'],'midpoint':d.get('midpoint'),'best_bid':d.get('best_bid'),'best_ask':d.get('best_ask'),
                'latest_book_available_at':d.get('latest_book_available_at'),'reference_midpoint_30m':d['predictions']['persistence'] if timely else None,
                'candidate_midpoints_30m':{k:v for k,v in (d.get('predictions') or {}).items() if k!='persistence'} if timely else {},
                'outside_training_range':d.get('outside_training_range'),'short_history_available':d.get('short_features') is not None,
                'short_unavailable_reasons':d.get('short_unavailable_reasons',[]),'decision_sha256':d['record_sha256']}
        status={'at':now().isoformat(),'pid':os.getpid(),'phase':phase,'error_type':error,**counts,'stop_at':contract['stop_at'],
            'journal_head_sha256':head,'source_bytes_verified':tape.offset,'old_trade_model_scored':False,'news_effect_tested':False}
        atomic(OUT/'latest_forecasts.json',{'at':status['at'],'phase':phase,'target':'Received YES-book midpoint30min later',
            'reference':'Persistence; unchanged midpoint, not a directional edge','forecasts':latest,'expires':'Reader must check display_expires_at and status heartbeat; no stale cache use'})
        atomic(OUT/'status.json',status);return status
    try:
        while not stopping and not (OUT/'STOP').exists() and now().timestamp()<=stamp(contract['stop_at']):
            tape.refresh_live();clock=now().timestamp()
            for t in range(int(stamp(contract['first_grid_at'])),int(stamp(contract['last_grid_at']))+1,300):
                if t>clock:break
                for s in samples:
                    key=(s['market_id'],iso(t))
                    if key in done:continue
                    f=None
                    if now().timestamp()>t+policy['forward_emission_seconds']:state='missed';why=['missed_emission_deadline']
                    else:
                        f,why=tape.features(s['market_id'],t);state='ready' if f else 'abstained'
                    r={'kind':'decision','recorded_at':now().isoformat(),'market_id':s['market_id'],'question':s['question'],
                        'grid_at':iso(t),'target_at':iso(t+1800),'status':state,'reasons':why,'predictions':None,
                        'models_sha256':contract['models_sha256'],'source_journal_head':tape.head}
                    if f:
                        predictions,ood=predict(f,models);r.update(f,predictions=predictions,outside_training_range=ood)
                        if now().timestamp()>t+policy['forward_emission_seconds']:r.update(status='missed',reasons=['computation_exceeded_emission_budget'],predictions=None)
                    d=append(r);done.add(key)
                    if d['status']=='ready':
                        at=now().timestamp();append({'kind':'emission_commit','at':iso(at),'decision_sha256':d['record_sha256'],'timely':at<=t+policy['forward_emission_seconds']})
            commits={r['decision_sha256'] for r in rows if r['kind']=='emission_commit' and r['timely']}
            observed={r['decision_sha256'] for r in rows if r['kind']=='outcome'}
            for d in list(rows):
                h=d['record_sha256']
                if d['kind']!='decision' or h not in commits or h in observed:continue
                if now().timestamp()<stamp(d['target_at'])+policy['forward_adjudication_delay_seconds']:continue
                target,why=tape.endpoint(d['market_id'],int(stamp(d['grid_at'])))
                append({'kind':'outcome','at':now().isoformat(),'decision_sha256':h,'market_id':d['market_id'],'target_at':d['target_at'],
                    'status':'observed' if target else 'unavailable','target':target,'reasons':why})
            if now().timestamp()-last_status>=10:snapshot('running');last_status=now().timestamp()
            time.sleep(1)
    except Exception as exc:
        error=type(exc).__name__;append({'kind':'process_error','at':now().isoformat(),'error_type':error});raise
    finally:
        append({'kind':'process_stopped','at':now().isoformat(),'error_type':error});status=snapshot('stopped')
        decisions={r['record_sha256']:r for r in rows if r['kind']=='decision'}
        successful=[r for r in rows if r['kind']=='outcome' and r['status']=='observed'];panels={}
        for tier in ['snapshot','short']:
            oo=[r for r in successful if tier=='snapshot' or 'short_ridge' in decisions[r['decision_sha256']]['predictions']]
            keys=['persistence','weighted_midpoint','snapshot_ridge']+(['short_ridge'] if tier=='short' else [])
            keys=[k for k in keys if all(k in decisions[r['decision_sha256']]['predictions'] for r in oo)]
            panels[tier]={k:metric([r['target']['midpoint'] for r in oo],[decisions[r['decision_sha256']]['predictions'][k] for r in oo]) for k in keys} if oo else None
        result={**status,'matched_metrics':panels,'independent_confirmation':False,'promotion':False,
            'limits':['Two markets, overlapping horizons and one short period','Sampled quote/status target, no fills or profitability','No news test','Availability-dependent endpoint exclusions must be reported']}
        write(OUT/'completion_report.json',result)
        if error is None:
            paths=[journal,contract_path,OUT/'completion_report.json',RELEASE/'implementation_manifest.json']
            write(OUT/'completion_manifest.json',{'files':{str(p.relative_to(REPO_ROOT)):sha(p) for p in paths}})

if __name__=='__main__':main()
