from pathlib import Path
from datetime import datetime,timezone
from collections import Counter
import json,hashlib,subprocess,sys,time
root=Path('/Users/zhurong/UROP');base=root/'data/v7/forecast_runtime_20261026_v01';rel=root/'eventx/release/v7/forecast_runtime_20261026_v01'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def write(p,v):
 with p.open('x') as f:json.dump(v,f,indent=2,sort_keys=True);f.write('\n')
# May be invoked only after capture completion. Never extends/restarts collection.
assert (base/'readiness/capture_manifest.json').exists()
r=subprocess.run([sys.executable,'-m','eventx.tasks.audit_v7_classifier_readiness_20261026'],cwd=root,text=True,capture_output=True)
if r.returncode:print(r.stdout+r.stderr);raise RuntimeError('Frozen readiness auditor failed')
live=json.loads((base/'readiness_audit/report.json').read_text());rows=json.loads((base/'readiness_audit/coverage_ledger.json').read_text());packets=json.loads((base/'readiness_audit/packet_checks.json').read_text())
records=[json.loads(l) for l in (base/'readiness/journal.jsonl').read_text().splitlines()]
reasons=Counter(x for row in rows for x in row['reasons']);post=[row for row in rows if row['transport_ready']]
clock_reasons={'clock_probe_missing','clock_probe_stale','insufficient_precise_independent_clocks','clock_intervals_disagree','host_clock_offset_exceeds100ms_budget'}
without_clock=sum(not [reason for reason in row['reasons'] if reason not in clock_reasons] for row in post)
diagnosis={'at':datetime.now(timezone.utc).isoformat(),'scope':'Input-only operational diagnosis','decision_reason_counts':dict(reasons),'packet_failure_reasons':dict(Counter(r['reason'] for r in packets if not r['valid'])),'post_warmup_decisions':len(post),'post_warmup_ready':sum(r['ready'] for r in post),'post_warmup_details':post,'collector_counts':dict(Counter(r['kind'] for r in records)),'no_live_labels_or_forecasts':True,'prospective_test_started':False}
diagnosis['post_warmup_ready_without_clock_DIAGNOSTIC_ONLY']=without_clock
diagnosis['clock_step_details']=[{k:r[k] for k in ['at','wall_minus_monotonic_change_seconds']} for r in records if r['kind']=='clock_step']
write(base/'readiness_diagnosis.json',diagnosis)
report=root/'EVENTX_FROZEN_FORECAST_RUNTIME_20261026.md';s=report.read_text()
s=s.replace('is scheduled to stop at **12:06:11 UTC**','was scheduled to stop at **12:06:11 UTC**')
s=s.replace('The result will be appended after the frozen audit completes; a connected stream alone is insufficient.','The completed audit result is recorded below; a connected stream alone is insufficient.')
s+='\n## Completed rehearsal result\n\n'
s+=f"The collector stopped at **{live['capture_stopped_at']}**. Normal fixed-duration completion: **{live['normal_completion']}**. Fresh input gate: **{'PASS' if live['passed'] else 'FAIL'}**.\n\n"
s+='| Measurement | Result |\n|---|---:|\n'
for k,v in [('Scheduled market-decisions',live['scheduled_decisions']),('Fully ready under frozen runtime',live['fully_ready']),('Fully ready under strict timestamp comparison',live['strict_fully_ready']),('Contributing contracts',live['contributing_markets']),('Valid native selected packets',str(live['valid_clock_packets'])+'/'+str(live['clock_packets'])),('Detected clock steps',live['clock_steps']),('Live forecasts issued',0),('Live labels constructed',0)]:s+=f'| {k} | {v} |\n'
s+='\nDecision exclusion counts overlap: '+', '.join(f'`{k}`: {v}' for k,v in reasons.items())+'.\n\n'
s+=f"For diagnosis only, {without_clock} post-warmup decisions satisfied the other gates when clock failures were ignored. This does not admit those decisions or override the frozen clock requirement.\n\n"
if live['passed']:
 s+='The frozen runtime has passed this short readiness rehearsal. A separate activation receipt and a newly warmed source are still required before the seven-day prospective test. Passing does not establish forecast accuracy or sustained availability.\n'
else:
 s+='**Activation remains blocked by the fresh input gate.** Preserve this failed rehearsal. Address the recorded measurement/availability problem under a separately justified version and repeat the unchanged readiness design; do not reuse the earlier successful capture as a substitute. No threshold was relaxed, model retuned or capture extended to produce a pass.\n'
if diagnosis['packet_failure_reasons']:
 s+='\nThe native SNTP command returned some unusable selected-packet records. Exit code zero is not sufficient clock evidence. The runtime correctly excludes invalid packets; their printed offsets must not be interpreted as actual host offsets. The raw exchange/selection discrepancy needs investigation before replacing this measurement method.\n'
if diagnosis['clock_step_details']:
 s+='\nClock steps were also observed: '+', '.join(f"{r['wall_minus_monotonic_change_seconds']*1000:.3f} ms at {r['at']}" for r in diagnosis['clock_step_details'])+'. Each step reset the 30-minute transport warmup. A working replacement clock adapter alone would not remove this separate operational issue: the host must sustain the frozen clock and uninterrupted-warmup requirements. No system clock setting was changed by this task.\n'
s+='\n[Readiness audit](data/v7/forecast_runtime_20261026_v01/readiness_audit/report.json) · [Per-grid diagnosis](data/v7/forecast_runtime_20261026_v01/readiness_diagnosis.json)\n\n**No activation receipt exists, no forecast service is running, and no prospective test has started.**\n'
report.write_text(s)
from eventx.v7.forecast_runtime_20261026 import verify_release,verify_manifest
verify_release();verify_manifest(base/'readiness/capture_manifest.json');verify_manifest(base/'readiness_audit/manifest.json')
assert not (base/'activation_receipt.json').exists() and not (base/'prospective').exists() and not (base/'evaluation').exists()
write(base/'state.json',{'at':diagnosis['at'],'phase':'runtime_frozen_fresh_readiness_complete','readiness_passed':live['passed'],'activation_ready':live['passed'],'prospective_test_started':False,'forecast_service_running':False,'next_step':'Separate activation receipt and fresh source warmup' if live['passed'] else 'Resolve fresh operational failure in a new version before activation'})
paths=[report,base/'state.json',base/'integration_qa.json',base/'readiness_diagnosis.json',base/'readiness_audit/manifest.json',base/'readiness/capture_manifest.json',rel/'implementation_manifest.json',rel/'verify_runtime_integration.py']
finalizer=rel/'finalize_readiness.py';finalizer.write_bytes(Path(__file__).read_bytes());paths.append(finalizer)
write(rel/'delivery_manifest.json',{'created_at':diagnosis['at'],'files':{str(p.relative_to(root)):sha(p) for p in paths}})
state=root/'CURRENT_STATE.md';s=state.read_text();(root/'docs/progress/CURRENT_STATE_BEFORE_RUNTIME_DELIVERY_20261026.md').write_text(s)
s=s.replace('V03 emitter/evaluator frozen; fresh40mininput-onlyreadiness running; no prospective test.',f"V03 emitter/evaluator frozen; fresh inputgate {'PASS' if live['passed'] else 'FAIL'}; no prospective test.")
a=s.index('## Frozen classifier runtime (26October)');b=s.index('## Clock correction (26October)')
s=s[:a]+f'''## Frozen classifier runtime (26October)

- COMPLETED:`EVENTX_FROZEN_FORECAST_RUNTIME_20261026.md`;release`forecast_runtime_20261026_v01`.
- Emitter/evaluator+41dependenciesfrozen;51checks+syntheticintegrationPASS;model/target/cohortunchanged.
- Sourceprefix/durabledeadline receipts;onlinepacketvalidation;closed-windowonce-onlyevaluator.
- Fresh40mincapture stopped{live['capture_stopped_at']};gate{'PASS' if live['passed'] else 'FAIL'};ready{live['fully_ready']}/{live['scheduled_decisions']},contributing{live['contributing_markets']}.
- Nativepacketsvalid{live['valid_clock_packets']}/{live['clock_packets']};clocksteps{live['clock_steps']};diagnosis`data/v7/forecast_runtime_20261026_v01/readiness_diagnosis.json`.
- Delivery:`eventx/release/v7/forecast_runtime_20261026_v01/delivery_manifest.json`;no activation/forecasts/labels/test.
- {'Next:separateactivationreceiptandnewsourcewarmup;no automaticactivation.' if live['passed'] else 'ActivationBLOCKEDbyfreshgate;preservefailureandrepairinnewversion,nothresholdrelaxation.'}

'''+s[b:]
s=s.replace('2. Complete fresh frozen-runtime readinessaudit;retainpass/failwithoutcaptureextension.\n   Activation remainsseparate;newservice mustwarmupandenforcegates. No prospective teststarted.',('2. Freshreadinesspassed;separateactivationreceiptandnewsourcewarmuprequired.\n   No prospective teststarted;maintainongoinginputgates.' if live['passed'] else '2. Resolve fresh runtimeinputfailure fromreadinessdiagnosis inaseparatelyfrozenversion.\n   Do notactivateusingtheearlierV03pass;freshgatefailed.No prospective teststarted.'))
state.write_text(s)
with (root/'docs/progress/2026-10.md').open('a') as f:
 f.write('\n## '+diagnosis['at']+' — frozen-runtime fresh readiness completed\n\nReport:EVENTX_FROZEN_FORECAST_RUNTIME_20261026.md;delivery:eventx/release/v7/forecast_runtime_20261026_v01/delivery_manifest.json.\nAudit:'+json.dumps(live,sort_keys=True)+'\nDiagnosis:'+json.dumps(diagnosis,sort_keys=True)+'\nNo live predictions/labels,activation,trading,holdoutconsumption,modelrefit,thresholdchanges,captureextensionsorSSH. Earlierreadinessretainedasdatedevidence,notsubstitutefornewresult. Syntheticintegrationartifactexplicitlynotliveevidence.\n')
print(json.dumps({'readiness':live,'report':str(report),'current_state_lines':len(s.splitlines()),'delivery_files':len(paths)},indent=2))
