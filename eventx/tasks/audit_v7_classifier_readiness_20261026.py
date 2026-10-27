"""Fresh rehearsal audit with the exact frozen emitter input code; no model scoring."""
import json
import math
from eventx.v7.forecast_runtime_20261026 import *
from eventx.v7.source_time_quote_inputs_20261026 import SourceTimeQuoteTape as StrictTape

def main():
    verify_release();src=BASE/'readiness';verify_manifest(src/'capture_manifest.json')
    out=BASE/'readiness_audit'
    if out.exists(): raise RuntimeError('Preserve prior readiness audit')
    samples=[json.loads(l) for l in (OLDREL/'live_cohort.jsonl').read_text().splitlines()]
    inp=Inputs(src,samples);contract=json.loads((src/'run_contract.json').read_text())
    if contract['implementation_sha256']!=sha(REL/'implementation_manifest.json'): raise RuntimeError('Collector freeze mismatch')
    start=stamp(contract['started_at']);stop=stamp(contract['stop_at'])
    stopped=[stamp(r['at']) for r in inp.records if r['kind']=='process_stopped']
    normal=bool(stopped and stopped[-1]>=stop and any(r['kind']=='run_deadline_reached' for r in inp.records))
    ledger=[];packet=[]
    for r in inp.records:
        if r['kind']=='clock_probe':
            checks=[{'host':m['host'],**selected_packet_check(m)} for m in r['measurements']]
            if checks!=r['packet_validation']: raise RuntimeError('Online packet validation mismatch')
            packet.extend(checks)
    for s in samples:
        cid=s['market_id'];strict=StrictTape(inp.by[cid])
        for t in grids(math.ceil(start/300)*300,int(stop)):
            f,why=inp.current(cid,t);tr,_=transport_ready(inp.records,t);clk,_=packet_clock_health(inp.records,t)
            # Independent prefix-only feature and clock replay; no later observations help.
            rr=[r for r in inp.by[cid] if r['timestamp_received'].timestamp()<=t]
            assert SourceTimeQuoteTape(rr).features(t)==inp.tapes[cid].features(t)
            earlier=[r for r in inp.records if stamp(r.get('available_at') or r.get('at') or r.get('response_received_at'))<=t]
            assert packet_clock_health(earlier,t)[0]==clk
            strict_ready=strict.features(t) is not None and not [x for x in why if x!='quote_missing_stale_invalid_or_conflicting']
            ledger.append({'market_id':cid,'t':t,'at':iso(t),'ready':f is not None,'strict_ready':bool(strict_ready),'transport_ready':tr,'clock_ready':clk,'reasons':why})
    count=sum(r['ready'] for r in ledger);contributing=len({r['market_id'] for r in ledger if r['ready']})
    scope=any(r['kind']=='scope_rejected_stop' for r in inp.records)
    passed=normal and not inp.errors and not scope and count>=2 and contributing>=1
    report={'completed_at':iso(now()),'capture_started_at':contract['started_at'],'capture_stopped_at':iso(stopped[-1]) if stopped else None,'normal_completion':normal,'scheduled_decisions':len(ledger),'fully_ready':count,'strict_fully_ready':sum(r['strict_ready'] for r in ledger),'contributing_markets':contributing,'clock_packets':len(packet),'valid_clock_packets':sum(r['valid'] for r in packet),'schema_errors':inp.errors,'scope_failure':scope,'clock_steps':sum(r['kind']=='clock_step' for r in inp.records),'passed':passed,'prospective_test_started':False,'forecasts_issued':0,'labels_constructed':0,'implementation_sha256':sha(REL/'implementation_manifest.json')}
    out.mkdir();write_new(out/'coverage_ledger.json',ledger);write_new(out/'packet_checks.json',packet);write_new(out/'report.json',report)
    write_new(out/'manifest.json',{'files':{str(p.relative_to(REPO_ROOT)):sha(p) for p in out.iterdir() if p.is_file()}})
    print(json.dumps(report,indent=2))
if __name__=='__main__':main()
