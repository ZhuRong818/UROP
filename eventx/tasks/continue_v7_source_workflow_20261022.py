"""Bounded autonomous source workflow. Never scores or activates event forecasting."""
import fcntl
import json
import os
from pathlib import Path
import subprocess
import sys
import time
from datetime import datetime,timezone,timedelta
from eventx.tasks.discover_v7_direct_pilot_20261022 import REPO_ROOT,now,sha,write,verify_originals

BASE=REPO_ROOT/'data/v7/source_workflow_20261022'
RELEASE=REPO_ROOT/'eventx/release/v7/source_workflow_20261022'
ORIGINAL=REPO_ROOT/'data/v7/direct_source_pilot_20261022'
REVISED=REPO_ROOT/'data/v7/direct_source_pilot_20261022_v03'
START='<!-- V7_SOURCE_WORKFLOW_STATUS_START -->'
END='<!-- V7_SOURCE_WORKFLOW_STATUS_END -->'

def verify():
    for p,h in json.loads((RELEASE/'implementation_manifest.json').read_text())['locked_files'].items():
        if sha(REPO_ROOT/p)!=h:raise RuntimeError('Frozen workflow dependency changed')
    verify_originals()

def save(state):
    state.update(at=now().isoformat(),pid=os.getpid(),models_scored=False,predictive_admissions=0,event_activation_enabled=False)
    tmp=BASE/'status.tmp';write(tmp,state);os.replace(tmp,BASE/'status.json')

def transition(state,phase,**values):
    state.update(phase=phase,**values);save(state)
    receipt=dict(state)
    with (BASE/'events.jsonl').open('a') as f:
        f.write(json.dumps(receipt,sort_keys=True)+'\n');f.flush();os.fsync(f.fileno())
    with (REPO_ROOT/'docs/progress/2026-10.md').open('a') as f:
        f.write('\n### Autonomous V7 source workflow — '+state['at']+'\n\n'+json.dumps(receipt,sort_keys=True)+'\n')
    # Update only the designated status block, preserving the rest of the handoff.
    p=REPO_ROOT/'CURRENT_STATE.md'
    for _ in range(3):
        before=p.read_text()
        if START not in before or END not in before:break
        a=before.index(START);b=before.index(END,a)+len(END)
        block=START+'\n- Autonomous source phase: **'+phase+'**, at'+state['at']+'.\n- Live status/evidence: `data/v7/source_workflow_20261022/status.json`.\n- Event activation disabled; model frozen; zero admissions.\n'+END
        updated=before[:a]+block+before[b:]
        if p.read_text()==before:
            tmp=p.with_suffix('.workflow.tmp');tmp.write_text(updated);os.replace(tmp,p);break

def final_audit(base):
    found=[]
    for p in (base/'audits').glob('*/report.json'):
        r=json.loads(p.read_text())
        if r['run']==str((base/'live').relative_to(REPO_ROOT)) and r['window_deadline_reached']:
            # Completion marker must be included in this immutable audit, not only live status.
            last=None
            with (p.parent/'journal.jsonl').open() as f:
                for line in f:
                    if line.strip():last=json.loads(line)
            if last and last['kind']=='process_stopped' and datetime.fromisoformat(last['at']) >= datetime.fromisoformat(r['scheduled_stop_at']):found.append(p.parent)
    return sorted(found)[-1] if found else None

def audit_manifest(path):
    for p,h in json.loads((path/'manifest.json').read_text())['files'].items():
        if sha(REPO_ROOT/p)!=h:raise RuntimeError('Audit artifact mismatch')

def run_active(base):
    p=base/'live/process.lock'
    if not p.exists():return False
    with p.open('r') as f:
        try:
            fcntl.flock(f,fcntl.LOCK_EX|fcntl.LOCK_NB)
            fcntl.flock(f,fcntl.LOCK_UN)
            return False
        except BlockingIOError:return True

def review(audit):
    audit_manifest(audit)
    r=json.loads((audit/'report.json').read_text())
    comparisons=[json.loads(l) for l in (audit/'market_comparison.jsonl').read_text().splitlines()]
    m=[x for x in comparisons if x['role']=='prospective_macro_candidate']
    gaps=json.loads((audit/'trade_receipt_gaps.json').read_text())
    return {'audit':str(audit.relative_to(REPO_ROOT)),'journal_records':r['journal_records'],
            'verified_payloads':r['verified_payloads'],'http_counts':r['rest_http_counts'],
            'request_status_counts':r['rest_status_counts'],'stream_disconnects':r['stream_disconnects'],
            'max_trade_receipt_gap_seconds':max((x['max_between_receipts_seconds'] or 0 for x in gaps),default=None),
            'candidate_comparable_windows':sum(x['status']=='comparable_single_page_window' for x in m),
            'candidate_activity_pass_windows':sum(x.get('observed_activity_screen',False) for x in m),
            'predictive_admissions':0,'source_completeness_certified':False,
            'limit':'Activity screen is diagnostic. V01 uses cash/inclusive boundaries; V03 uses size/inclusive boundaries. Neither is a completed model-input compatibility gate.'}

def main():
    BASE.mkdir(parents=True,exist_ok=True)
    lock=(BASE/'process.lock').open('a');fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
    cfg=json.loads((RELEASE/'spec.json').read_text());verify()
    state=json.loads((BASE/'status.json').read_text()) if (BASE/'status.json').exists() else {}
    if state.get('phase') in ['finished_source_review','human_action_required','stopped_by_user']:return
    deadline=datetime.fromisoformat(cfg['administrative_stop_at'])
    transition(state,'waiting_for_original_rehearsal',human_action_required=False)
    while now()<deadline:
        if (BASE/'STOP').exists():transition(state,'stopped_by_user');return
        verify()
        contract=json.loads((ORIGINAL/'live/run_contract.json').read_text())
        due=datetime.fromisoformat(contract['stop_at'])
        if now()>=due and not run_active(ORIGINAL):
            audit=final_audit(ORIGINAL)
            if audit is None:
                with (BASE/'original_audit.log').open('a') as log:
                    subprocess.run([sys.executable,'-m','eventx.tasks.audit_v7_direct_pilot_20261022'],cwd=REPO_ROOT,stdout=log,stderr=log,check=True)
                audit=final_audit(ORIGINAL)
            if audit is None:raise RuntimeError('Original final completion evidence unavailable')
            original_review=review(audit);write(BASE/'original_final_review.json',original_review)
            transition(state,'original_rehearsal_reviewed',original_audit=str(audit.relative_to(REPO_ROOT)))
            break
        save(state);time.sleep(30)
    else:raise RuntimeError('Original rehearsal did not finish before workflow deadline')
    verify()
    # Resume only this V03 run; Capture retains its original absolute deadline.
    transition(state,'running_revised_24h_rehearsal',human_action_required=False)
    with (BASE/'revised_collector.log').open('a') as log:
        # A controller restart must not start a second collector over an orphaned child.
        while run_active(REVISED):
            if (BASE/'STOP').exists():transition(state,'stopped_by_user');return
            if now()>=deadline:raise RuntimeError('Revised source process exceeded workflow deadline')
            save(state);time.sleep(30)
        already_done=final_audit(REVISED) if (REVISED/'audits').exists() else None
        if already_done is not None:
            write(BASE/'revised_final_review.json',review(already_done))
            transition(state,'finished_source_review',revised_audit=str(already_done.relative_to(REPO_ROOT)),human_action_required=False,awaiting_research_gate=True)
            return
        outer=datetime.fromisoformat(json.loads((REPO_ROOT/'eventx/release/v7/direct_source_pilot_20261022_v03/spec.json').read_text())['rehearsal_stop_at'])
        if not (REVISED/'live/run_contract.json').exists() and now()+timedelta(seconds=86400)>outer:
            raise RuntimeError('Too late to run full24h before fixed administrative deadline')
        child=subprocess.Popen([sys.executable,'-m','eventx.tasks.collect_v7_direct_pilot_20261022_v03'],cwd=REPO_ROOT,stdout=log,stderr=log)
        state['collector_pid']=child.pid
        while child.poll() is None:
            if (BASE/'STOP').exists() or now()>=deadline:
                (REVISED/'live/STOP').touch()
                child.terminate()
            save(state);time.sleep(30)
        if child.returncode:raise RuntimeError('Revised collector exited unsuccessfully; inspect scoped source evidence')
    audit=final_audit(REVISED)
    if audit is None:raise RuntimeError('Revised final completion evidence unavailable')
    revised_review=review(audit);write(BASE/'revised_final_review.json',revised_review)
    transition(state,'finished_source_review',revised_audit=str(audit.relative_to(REPO_ROOT)),
               next_step='Resolve documented execution-identity/coverage gaps; no event activation until separately frozen readiness passes.',
               human_action_required=False,awaiting_research_gate=True)

if __name__=='__main__':
    try:main()
    except Exception as e:
        BASE.mkdir(parents=True,exist_ok=True)
        state={'phase':'human_action_required','human_action_required':True,'error_type':type(e).__name__,
               'reason':'Workflow stopped on a failed integrity/completion/runtime gate; inspect local logs and source artifacts before restart.'}
        transition(state,'human_action_required')
        (BASE/'HUMAN_ACTION_REQUIRED.md').write_text('# Source workflow stopped\n\n'+state['reason']+'\n\nError type: '+state['error_type']+'\nNo model scores or predictive admissions were produced.\n')
