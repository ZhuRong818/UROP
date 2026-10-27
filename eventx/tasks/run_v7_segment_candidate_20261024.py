"""Read-only prospective hypothesis consumer; never rewrites the base forecasts."""
import fcntl
import hashlib
import json
import math
import os
import signal
import time
from pathlib import Path
from eventx.tasks.discover_v7_direct_pilot_20261022 import REPO_ROOT,now,sha,write,verify_originals
from eventx.tasks.prepare_v7_segment_candidate_20261024 import RELEASE,OUT
from eventx.tasks.run_v7_quote_experiment_20261024 import metric
from eventx.v7.quote_experiment_20261024 import stamp,iso
from eventx.v7.segment_candidate_20261024 import forecast

BASE=REPO_ROOT/'data/v7/memory_quote_20261024/shadow'
def digest_record(r):return hashlib.sha256(json.dumps(r,sort_keys=True,separators=(',',':')).encode()).hexdigest()

def main():
    verify_originals()
    for p,h in json.loads((RELEASE/'implementation_manifest.json').read_text())['locked_files'].items():
        if sha(REPO_ROOT/p)!=h:raise RuntimeError('Candidate lock mismatch')
    lock=(OUT/'process.lock').open('a');fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
    model=json.loads((RELEASE/'model.json').read_text());base_contract=json.loads((BASE/'run_contract.json').read_text())
    contract_path=OUT/'run_contract.json'
    if contract_path.exists():contract=json.loads(contract_path.read_text())
    else:
        contract={'at':now().isoformat(),'first_grid_at':iso(math.floor(now().timestamp()/300)*300+300),
            'stop_at':iso(stamp(base_contract['stop_at'])+60),'base_contract_sha256':sha(BASE/'run_contract.json'),
            'implementation_manifest_sha256':sha(RELEASE/'implementation_manifest.json')}
        write(contract_path,contract)
    if contract['implementation_manifest_sha256']!=sha(RELEASE/'implementation_manifest.json') or contract['base_contract_sha256']!=sha(BASE/'run_contract.json'):raise RuntimeError('Candidate contract drift')
    journal=OUT/'journal.jsonl';head=None;rows=[];stopping=False;error=None
    if journal.exists():
        for line in journal.read_bytes().splitlines(keepends=True):
            if not line.endswith(b'\n'):raise RuntimeError('Partial candidate journal; preserve')
            r=json.loads(line);v=dict(r);h=v.pop('record_sha256')
            if v['previous_sha256']!=head or digest_record(v)!=h:raise RuntimeError('Candidate journal failure')
            rows.append(r);head=h
    def append(value):
        nonlocal head
        r={**value,'previous_sha256':head};r['record_sha256']=digest_record(r)
        with journal.open('a') as f:f.write(json.dumps(r,sort_keys=True)+'\n');f.flush();os.fsync(f.fileno())
        head=r['record_sha256'];rows.append(r);return r
    def stop(*_):
        nonlocal stopping
        stopping=True
    signal.signal(signal.SIGINT,stop);signal.signal(signal.SIGTERM,stop)
    append({'kind':'process_started','at':now().isoformat(),'pid':os.getpid()})
    offset=0;base_head=None;base_decisions={};base_commits={};base_outcomes={};last_status=0
    def snapshot(phase):
        forecasts={r['record_sha256']:r for r in rows if r['kind']=='forecast'}
        committed={r['forecast_sha256'] for r in rows if r['kind']=='commit' and r['timely']}
        outcomes=[r for r in rows if r['kind']=='outcome']
        status={'at':now().isoformat(),'pid':os.getpid(),'phase':phase,'timely_forecasts':len(committed),
            'segment_active_forecasts':sum(forecasts[h]['segment_active'] for h in committed),
            'missed':sum(r['kind']=='missed' for r in rows),'observed_endpoints':sum(r['status']=='observed' for r in outcomes),
            'unavailable_endpoints':sum(r['status']!='observed' for r in outcomes),'error_type':error,'stop_at':contract['stop_at'],
            'journal_head_sha256':head,'base_bytes_verified':offset,'scope':'Post-selection hypothesis; not promoted or independently confirmed'}
        tmp=OUT/'status.tmp';write(tmp,status);os.replace(tmp,OUT/'status.json');return status
    try:
        while not stopping and not (OUT/'STOP').exists() and now().timestamp()<=stamp(contract['stop_at']):
            with (BASE/'journal.jsonl').open('rb') as f:
                f.seek(offset)
                while True:
                    line=f.readline()
                    if not line or not line.endswith(b'\n'):break
                    r=json.loads(line);v=dict(r);h=v.pop('record_sha256')
                    if v['previous_sha256']!=base_head or digest_record(v)!=h:raise RuntimeError('Base chain failure')
                    base_head=h;offset=f.tell()
                    if r['kind']=='decision' and stamp(r['grid_at'])>=stamp(contract['first_grid_at']):base_decisions[h]=r
                    elif r['kind']=='emission_commit':base_commits[r['decision_sha256']]=r
                    elif r['kind']=='outcome':base_outcomes[r['decision_sha256']]=r
            done={r['base_decision_sha256'] for r in rows if r['kind'] in ['forecast','missed']}
            for h,d in base_decisions.items():
                if h in done or h not in base_commits or not base_commits[h]['timely']:continue
                deadline=stamp(d['grid_at'])+30
                if now().timestamp()>deadline:append({'kind':'missed','at':now().isoformat(),'base_decision_sha256':h,'reason':'candidate_emission_deadline'});continue
                result=forecast(d,model)
                emitted=append({'kind':'forecast','at':now().isoformat(),'base_decision_sha256':h,'base_commit_sha256':base_commits[h]['record_sha256'],
                    'market_id':d['market_id'],'grid_at':d['grid_at'],'target_at':d['target_at'],'input_payload_hashes':d['input_payload_hashes'],
                    'model_sha256':sha(RELEASE/'model.json'),**result})
                at=now().timestamp();append({'kind':'commit','at':iso(at),'forecast_sha256':emitted['record_sha256'],'timely':at<=deadline})
            forecasts={r['record_sha256']:r for r in rows if r['kind']=='forecast'}
            committed={r['forecast_sha256'] for r in rows if r['kind']=='commit' and r['timely']}
            adjudicated={r['forecast_sha256'] for r in rows if r['kind']=='outcome'}
            for h in committed-adjudicated:
                d=forecasts[h];base=base_outcomes.get(d['base_decision_sha256'])
                if base is None:continue
                append({'kind':'outcome','at':now().isoformat(),'forecast_sha256':h,'base_outcome_sha256':base['record_sha256'],
                    'status':base['status'],'target':base['target'],'reasons':base['reasons']})
            if now().timestamp()-last_status>=10:snapshot('running');last_status=now().timestamp()
            time.sleep(1)
    except Exception as exc:
        error=type(exc).__name__;append({'kind':'error','at':now().isoformat(),'error_type':error});raise
    finally:
        append({'kind':'process_stopped','at':now().isoformat(),'error_type':error});status=snapshot('stopped')
        preds={r['record_sha256']:r for r in rows if r['kind']=='forecast'};outcomes=[r for r in rows if r['kind']=='outcome' and r['status']=='observed']
        panels={}
        for panel in ['all','segment']:
            rr=[r for r in outcomes if panel=='all' or preds[r['forecast_sha256']]['segment_active']]
            panels[panel]={k:metric([r['target']['midpoint'] for r in rr],[preds[r['forecast_sha256']][k] for r in rr]) for k in ['reference','prediction']} if rr else None
        write(OUT/'completion_report.json',{**status,'matched_metrics':panels,'independent_confirmation':False,'model_promoted':False})
        if error is None:
            paths=[journal,contract_path,OUT/'completion_report.json',RELEASE/'implementation_manifest.json'];write(OUT/'completion_manifest.json',{'files':{str(p.relative_to(REPO_ROOT)):sha(p) for p in paths}})

if __name__=='__main__':main()
