"""Activated V03 emitter; refuses to run without a separate immutable receipt."""
import fcntl
import json
import os
import signal
import time
import joblib
from eventx.v7.forecast_runtime_20261026 import *

def main():
    verify_release()
    receipt_path=BASE/'activation_receipt.json'
    receipt=json.loads(receipt_path.read_text())  # Missing receipt blocks before creating any run files.
    require_activation(receipt,now())
    if now()>receipt['open_after']: raise RuntimeError('Closed window cannot be restarted')
    out=BASE/'prospective/emitter';out.mkdir(parents=True,exist_ok=True)
    lock=(out/'process.lock').open('a');fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
    contract={'activation_sha256':sha(receipt_path),'implementation_sha256':sha(REL/'implementation_manifest.json')}
    if (out/'run_contract.json').exists():
        if json.loads((out/'run_contract.json').read_text())!=contract: raise RuntimeError('Run contract changed')
    else: write_new(out/'run_contract.json',contract)
    journal=Journal(out/'journal.jsonl');previous=read_chain(journal.path)[0] if journal.path.exists() else []
    done={(r['market_id'],r['t']) for r in previous if r['kind']=='decision'}
    adjudicated={(r['market_id'],r['t']) for r in previous if r['kind']=='endpoint_receipt'}
    samples=[json.loads(l) for l in (OLDREL/'live_cohort.jsonl').read_text().splitlines()]
    bundle=joblib.load(MODEL);source=REPO_ROOT/receipt['source_path'];stopping=False
    def stop(*_):
        nonlocal stopping
        stopping=True
    signal.signal(signal.SIGTERM,stop);signal.signal(signal.SIGINT,stop)
    journal.append({'kind':'process_started','at':now(),'pid':os.getpid()})
    schedule=grids(receipt['first_grid'],receipt['last_grid']);inputs=None
    try:
        while not stopping and now()<=receipt['open_after']+30:
            clock=now()
            pending=[t for t in schedule if t<=clock and any((s['market_id'],t) not in done for s in samples)]
            endpoints=[t for t in schedule if t+1920<=clock and any((s['market_id'],t) not in adjudicated for s in samples)]
            if pending or endpoints:
                if inputs is None: inputs=Inputs(source,samples)
                else: inputs.refresh()
            for t in pending:
                for s in samples:
                    cid=s['market_id']
                    if (cid,t) in done: continue
                    r=journal.append(decision(inputs,bundle,cid,t,now()))
                    durable=now()  # Measured after decision fsync, not before the write.
                    journal.append({'kind':'emission_commit','market_id':cid,'t':t,'decision_sha256':r['record_sha256'],'decision_durable_at':durable,'timely':r['status']=='ready' and t<=durable<=t+30})
                    done.add((cid,t))
            for t in endpoints:
                for s in samples:
                    cid=s['market_id']
                    if (cid,t) in adjudicated: continue
                    # No endpoint values, labels or performance are computed online.
                    adjudicated_at=now()
                    journal.append({'kind':'endpoint_receipt','market_id':cid,'t':t,'recorded_at':adjudicated_at,'source_bytes':inputs.offset,'source_head':inputs.head,'adjudication_timely':t+1920<=adjudicated_at<=t+1950})
                    adjudicated.add((cid,t))
            status={'at':now(),'pid':os.getpid(),'decisions_recorded':len(done),'endpoint_receipts':len(adjudicated),'labels_computed':False,'performance_opened':False,'test_ends':receipt['open_after']}
            temp=out/'status.tmp'
            temp.write_text(json.dumps(status,indent=2)+'\n');os.replace(temp,out/'status.json')
            time.sleep(1)
    finally:
        journal.append({'kind':'process_stopped','at':now(),'early':now()<receipt['open_after']})
        write_new(out/('stop_'+str(time.time_ns())+'.json'),{'at':now(),'journal_head':journal.head})

if __name__=='__main__': main()
