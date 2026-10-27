"""Append-only forward quote forecasts from an existing collector; no networking."""
from datetime import datetime,timezone
import fcntl
import hashlib
import json
import math
import os
from pathlib import Path
import signal
import time
import numpy as np
from eventx.tasks.discover_v7_direct_pilot_20261022 import REPO_ROOT,now,sha,write,verify_originals
from eventx.v7.quote_experiment_20261024 import QuoteTape,stamp,iso,predictions
from eventx.tasks.run_v7_quote_experiment_20261024 import metric

RELEASE=REPO_ROOT/'eventx/release/v7/quote_shadow_20261024'
OUT=REPO_ROOT/'data/v7/quote_experiment_20261024/shadow'

def main():
    for p,h in json.loads((RELEASE/'implementation_manifest.json').read_text())['locked_files'].items():
        if sha(REPO_ROOT/p)!=h:raise RuntimeError('Shadow lock mismatch')
    verify_originals();cfg=json.loads((RELEASE/'activation_policy.json').read_text())
    policy=json.loads((REPO_ROOT/cfg['quote_policy']).read_text())
    model=json.loads((REPO_ROOT/cfg['model']).read_text())
    samples=[json.loads(l) for l in (REPO_ROOT/cfg['cohort']).read_text().splitlines()]
    protected=set(json.loads((REPO_ROOT/'eventx/release/v7/market_capture_20261018/protected_ids.json').read_text()))
    if protected.intersection(r['market_id'] for r in samples):raise RuntimeError('Protected scope')
    OUT.mkdir(parents=True,exist_ok=True);lock=(OUT/'process.lock').open('a');fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
    tape=QuoteTape(REPO_ROOT/cfg['source_live'],samples,policy)
    journal=OUT/'journal.jsonl';head=None;rows=[];stopping=False
    if journal.exists():
        for line in journal.read_bytes().splitlines():
            r=json.loads(line);v=dict(r);h=v.pop('record_sha256')
            actual=hashlib.sha256(json.dumps(v,sort_keys=True,separators=(',',':')).encode()).hexdigest()
            if h!=actual or v['previous_sha256']!=head:raise RuntimeError('Shadow journal chain mismatch')
            head=h;rows.append(r)
    def append(value):
        nonlocal head
        r={**value,'previous_sha256':head}
        r['record_sha256']=hashlib.sha256(json.dumps(r,sort_keys=True,separators=(',',':')).encode()).hexdigest()
        with journal.open('a') as f:f.write(json.dumps(r,sort_keys=True)+'\n');f.flush();os.fsync(f.fileno())
        head=r['record_sha256'];rows.append(r);return r
    def stop(*_):
        nonlocal stopping
        stopping=True
    signal.signal(signal.SIGTERM,stop);signal.signal(signal.SIGINT,stop)
    contract_path=OUT/'run_contract.json'
    if contract_path.exists():contract=json.loads(contract_path.read_text())
    else:
        start=math.floor(now().timestamp()/300)*300+300
        last=math.floor((stamp(policy['forward_collector_stop'])-1800-120)/300)*300
        contract={'activated_at':now().isoformat(),'first_grid_at':iso(start),'last_grid_at':iso(last),
            'stop_at':iso(last+1800+180),'implementation_manifest_sha256':sha(RELEASE/'implementation_manifest.json'),
            'model_sha256':sha(REPO_ROOT/cfg['model']),'scope':'Prospective quote-shadow feasibility, not news or old trade-model admission'}
        write(contract_path,contract)
    if contract['implementation_manifest_sha256']!=sha(RELEASE/'implementation_manifest.json'):raise RuntimeError('Activation drift')
    append({'kind':'process_started','at':now().isoformat(),'pid':os.getpid(),'resumed':len(rows)>0})
    done={(r['market_id'],r['grid_at']) for r in rows if r['kind']=='decision'}
    last_status=0;error=None
    try:
        while not stopping and not (OUT/'STOP').exists() and now().timestamp()<=stamp(contract['stop_at']):
            tape.refresh_live();clock=now().timestamp()
            for t in range(int(stamp(contract['first_grid_at'])),int(stamp(contract['last_grid_at']))+1,300):
                if t>clock:break
                for s in samples:
                    cid=s['market_id'];key=(cid,iso(t))
                    if key in done:continue
                    feature=None;why=[]
                    if now().timestamp()>t+policy['forward_emission_seconds']:
                        why=['missed_emission_deadline'];state='missed'
                    else:
                        feature,why=tape.features(cid,t);state='ready' if feature else 'abstained'
                    value={'kind':'decision','recorded_at':now().isoformat(),'market_id':cid,'question':s['question'],
                        'grid_at':iso(t),'target_at':iso(t+1800),'status':state,'reasons':why,
                        'source_journal_head':tape.head,'model_sha256':contract['model_sha256'],'predictions':None}
                    if feature:
                        value.update(feature);value['predictions']=predictions(feature,model)
                        x=np.array(feature['features']);value['outside_training_feature_range']=bool(np.any(x<model['training_feature_min']) or np.any(x>model['training_feature_max']))
                        if now().timestamp()>t+policy['forward_emission_seconds']:
                            value.update(status='missed',reasons=['computation_exceeded_emission_budget'],predictions=None)
                    decision=append(value);done.add(key)
                    if decision['status']=='ready':
                        committed_at=now().timestamp()
                        append({'kind':'emission_commit','at':iso(committed_at),'decision_sha256':decision['record_sha256'],
                            'timely':committed_at<=t+policy['forward_emission_seconds']})
            commitments={r['decision_sha256']:r for r in rows if r['kind']=='emission_commit'}
            adjudicated={r['decision_sha256'] for r in rows if r['kind']=='outcome'}
            for d in list(rows):
                h=d['record_sha256']
                if d['kind']!='decision' or h not in commitments or not commitments[h]['timely'] or h in adjudicated:continue
                if now().timestamp()<stamp(d['target_at'])+policy['forward_adjudication_delay_seconds']:continue
                target,why=tape.endpoint(d['market_id'],int(stamp(d['grid_at'])))
                append({'kind':'outcome','at':now().isoformat(),'decision_sha256':h,'market_id':d['market_id'],
                    'target_at':d['target_at'],'status':'observed' if target else 'unavailable','target':target,'reasons':why})
            if now().timestamp()-last_status>=15:
                decisions=[r for r in rows if r['kind']=='decision'];commits=[r for r in rows if r['kind']=='emission_commit' and r['timely']]
                status={'at':now().isoformat(),'pid':os.getpid(),'phase':'recording_shadow_or_abstentions',
                    'scheduled_decisions_recorded':len(decisions),'timely_forecasts':len(commits),
                    'abstentions':sum(r['status']=='abstained' for r in decisions),'missed':sum(r['status']=='missed' for r in decisions),
                    'outcomes_observed':sum(r['kind']=='outcome' and r['status']=='observed' for r in rows),
                    'old_trade_model_scored':False,'news_effect_tested':False,'stop_at':contract['stop_at'],
                    'source_records_read_bytes':tape.offset,'journal_head_sha256':head}
                tmp=OUT/'status.tmp';write(tmp,status);os.replace(tmp,OUT/'status.json');last_status=now().timestamp()
            time.sleep(2)
    except Exception as exc:
        error=type(exc).__name__;append({'kind':'process_error','at':now().isoformat(),'error_type':error})
        raise
    finally:
        append({'kind':'process_stopped','at':now().isoformat(),'error_type':error})
        decisions={r['record_sha256']:r for r in rows if r['kind']=='decision'}
        commits={r['decision_sha256']:r for r in rows if r['kind']=='emission_commit' and r['timely']}
        outcomes=[r for r in rows if r['kind']=='outcome' and r['status']=='observed' and r['decision_sha256'] in commits]
        metrics={k:metric([r['target']['midpoint'] for r in outcomes],[decisions[r['decision_sha256']]['predictions'][k] for r in outcomes]) for k in policy['models']} if outcomes else None
        result={'at':now().isoformat(),'phase':'stopped','error_type':error,'timely_forecasts':len(commits),
            'observed_endpoints':len(outcomes),'metrics':metrics,'old_trade_model_changed':False,'independent_confirmation':False,
            'limits':['two metadata-selected markets','small overlapping forecast series','no observed news release experiment','sampled quote and active-state target']}
        write(OUT/'completion_report.json',result)
        if (OUT/'status.json').exists():
            status=json.loads((OUT/'status.json').read_text());status.update(at=now().isoformat(),phase='stopped',error_type=error)
            write(OUT/'status.json',status)
        if error is None:
            files=[journal,contract_path,OUT/'completion_report.json',RELEASE/'implementation_manifest.json']
            write(OUT/'completion_manifest.json',{'files':{str(p.relative_to(REPO_ROOT)):sha(p) for p in files}})

if __name__=='__main__':main()
