"""Once-only closed-window audit, consumption, then endpoint/metric opening."""
import json
import math
import joblib
from eventx.v7.forecast_runtime_20261026 import *

def validate_emissions(records,schedule,market_ids):
    valid_keys={(cid,t) for cid in market_ids for t in schedule};dec={};commits={};ends={}
    for r in records:
        if r['kind'] not in ['decision','emission_commit','endpoint_receipt']: continue
        key=(r['market_id'],r['t'])
        if key not in valid_keys: raise RuntimeError('Out-of-scope forecast key')
        table=dec if r['kind']=='decision' else commits if r['kind']=='emission_commit' else ends
        if key in table: raise RuntimeError('Duplicate forecast/receipt key')
        table[key]=r
    for key,c in commits.items():
        d=dec.get(key)
        if d is None or c['decision_sha256']!=d['record_sha256']: raise RuntimeError('Unbound emission commit')
        expected=d['status']=='ready' and d['t']<=c['decision_durable_at']<=d['t']+30
        if c['decision_durable_at']<d['recorded_at'] or c['timely']!=expected: raise RuntimeError('Invalid durable deadline receipt')
    return valid_keys,dec,commits,ends

def main():
    verify_release();activation=BASE/'activation_receipt.json';receipt=json.loads(activation.read_text());require_activation(receipt,now())
    if now()<=receipt['open_after']+30: raise RuntimeError('Window still sealed')
    out=BASE/'evaluation'
    if out.exists(): raise RuntimeError('Evaluation already attempted; preserve receipt and do not rerun')
    source=REPO_ROOT/receipt['source_path'];emitter=BASE/'prospective/emitter'
    verify_manifest(source/'capture_manifest.json')
    rc=json.loads((emitter/'run_contract.json').read_text())
    if rc!={'activation_sha256':sha(activation),'implementation_sha256':sha(REL/'implementation_manifest.json')}: raise RuntimeError('Emitter binding mismatch')
    samples=[json.loads(l) for l in (OLDREL/'live_cohort.jsonl').read_text().splitlines()]
    records,_,_=read_chain(emitter/'journal.jsonl')
    if not records or records[-1]['kind']!='process_stopped': raise RuntimeError('Emitter not stopped')
    keys,dec,commits,ends=validate_emissions(records,grids(receipt['first_grid'],receipt['last_grid']),[s['market_id'] for s in samples])
    bundle=joblib.load(MODEL);source_cache={};replayed=0
    def load_prefix(r):
        offset=r['source_bytes']
        if offset not in source_cache:
            source_cache.clear()  # Bound memory; endpoint audit can reconstruct any immutable prefix.
            source_cache[offset]=Inputs(source,samples,offset)
        inp=source_cache[offset]
        if inp.head!=r['source_head']: raise RuntimeError('Source prefix binding failed')
        return inp
    # Current-time inputs and forecasts only. No endpoint computation before consumption.
    for key,d in sorted(dec.items(),key=lambda kv:kv[1]['source_bytes']):
        expected=decision(load_prefix(d),bundle,d['market_id'],d['t'],d['recorded_at'])
        for k in ['status','features','predictions','reasons','target_at']:
            if d[k]!=expected[k]: raise RuntimeError('Decision replay failed: '+k)
        replayed+=1
    for r in ends.values():
        load_prefix(r)
        expected=r['t']+1920<=r['recorded_at']<=r['t']+1950
        if r['adjudication_timely']!=expected: raise RuntimeError('Invalid endpoint timing receipt')
    out.mkdir()
    evidence={'activation_sha256':sha(activation),'source_capture_sha256':sha(source/'capture_manifest.json'),'emitter_journal_sha256':sha(emitter/'journal.jsonl'),'model_sha256':sha(MODEL),'implementation_sha256':sha(REL/'implementation_manifest.json')}
    write_new(out/'preopening_audit.json',{'at':now(),'passed':True,'decision_replays':replayed,'scheduled_keys':len(keys),'missing_decisions':len(keys-set(dec)),**evidence})
    write_new(out/'consumption_receipt.json',{'at':now(),'once_only':True,'scope':'This seven-day runtime only',**evidence})
    # Receipt exists before constructing or reading any target/score.
    try:
        rows=[];coverage=[]
        for cid,t in sorted(keys,key=lambda k:(k[1],k[0])):
            d=dec.get((cid,t));c=commits.get((cid,t));e=ends.get((cid,t))
            issued=bool(d and c and c['timely']);coverage.append({'market_id':cid,'t':t,'timely':issued,'status':d['status'] if d else 'missing_decision'})
            if not issued: continue
            endpoint=None;why=['missing_or_late_endpoint_receipt']
            if e and e['adjudication_timely']: endpoint,why=load_prefix(e).endpoint(cid,t)
            target=int(abs(endpoint-d['features'][0])>1e-12) if endpoint is not None else None
            rows.append({'market_id':cid,'t':t,'target':target,'endpoint_midpoint':endpoint,'endpoint_reasons':why,'predictions':d['predictions']})
        report=evaluate_rows(rows);report.update(at=iso(now()),scheduled=len(keys),timely=len(rows),abstained_or_uncommitted=len(keys)-len(rows),prospective_evaluation=True)
        write_new(out/'endpoint_ledger.json',rows);write_new(out/'coverage.json',coverage);write_new(out/'report.json',report)
    except Exception as e:
        write_new(out/'failure.json',{'at':now(),'type':type(e).__name__,'consumed':True});raise
    finally:
        write_new(out/'manifest.json',{'files':{str(p.relative_to(REPO_ROOT)):sha(p) for p in out.iterdir() if p.is_file()}})
    print(json.dumps(report,indent=2))
if __name__=='__main__':main()
