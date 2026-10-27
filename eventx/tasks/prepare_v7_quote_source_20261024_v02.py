"""Freeze a new24h run; preserve the completed6h source experiment."""
from datetime import timedelta
import json
from pathlib import Path
import plistlib
from eventx.tasks.discover_v7_direct_pilot_20261022 import REPO_ROOT,PROTECTED,now,sha,write,verify_originals

BASE=REPO_ROOT/'data/v7/quote_source_20261024_v02'
RELEASE=REPO_ROOT/'eventx/release/v7/quote_source_20261024_v02'

def main():
    verify_originals();parent=REPO_ROOT/'eventx/release/v7/expansion_source_pilot_20261024'
    for p,h in json.loads((parent/'implementation_manifest.json').read_text())['locked_files'].items():
        if sha(REPO_ROOT/p)!=h:raise RuntimeError('Parent source drift')
    RELEASE.mkdir(exist_ok=False);(BASE/'live').mkdir(parents=True,exist_ok=True)
    for name in ['sample.jsonl','episode_reservation.json','enrollment_report.json','evidence_link_plan.jsonl']:(RELEASE/name).write_bytes((parent/name).read_bytes())
    spec=json.loads((parent/'spec.json').read_text());at=now()
    spec.update(version='quote_source_20261024_v02',created_at=at.isoformat(),live_duration_seconds=86400,
        rehearsal_stop_at=(at+timedelta(hours=25)).isoformat(),
        scope='24h source capture for separate snapshot/30m-history midpoint forecasting; same two metadata-defined markets',
        observation_policy='eventx/release/v7/memory_quote_20261024/policy.json',
        dependencies='Quote service gates current book/status independently; original trade/news gates unchanged',
        rehearsal_criteria='Record all gaps and errors; completed wall time does not imply continuous capture',
        cold_start='New receipt clock; no imports to fill history gaps; snapshot forecast needs current valid book/status only')
    write(RELEASE/'spec.json',spec)
    label='com.eventx.quote-source.20261024-v02'
    p={'Label':label,'ProgramArguments':['/usr/bin/caffeinate','-i','-s',str(REPO_ROOT/'.venv/bin/python'),'-m','eventx.tasks.collect_v7_quote_source_20261024_v02'],
        'WorkingDirectory':str(REPO_ROOT),'RunAtLoad':True,'KeepAlive':{'SuccessfulExit':False},'ThrottleInterval':60,
        'EnvironmentVariables':{'PYTHONUNBUFFERED':'1'},'StandardOutPath':str(BASE/'live/stdout.log'),'StandardErrorPath':str(BASE/'live/stderr.log')}
    (RELEASE/(label+'.plist')).write_bytes(plistlib.dumps(p))
    files=list(RELEASE.iterdir())+[Path(__file__).resolve(),PROTECTED,parent/'implementation_manifest.json',REPO_ROOT/'eventx/release/v7/memory_quote_20261024/implementation_manifest.json']
    for n in ['collect_v7_quote_source_20261024_v02.py','launch_v7_quote_source_20261024_v02.py','collect_v7_expansion_pilot_20261024.py',
        'collect_v7_direct_pilot_20261022_v03.py','audit_v7_direct_pilot_20261022_v03.py']:
        files.append(REPO_ROOT/'eventx/tasks'/n)
    files.append(REPO_ROOT/'eventx/v7/source_request_scheduler_v02.py')
    write(RELEASE/'implementation_manifest.json',{'locked_files':{str(p.relative_to(REPO_ROOT)):sha(p) for p in files}})
    print(json.dumps({'source_hours':24,'markets':2,'old_collector_changed':False}))

if __name__=='__main__':main()
