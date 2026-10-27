"""Freeze the local memory-tier forecast service and its immutable fitted models."""
import json
from pathlib import Path
import plistlib
from eventx.tasks.discover_v7_direct_pilot_20261022 import REPO_ROOT,now,sha,write,verify_originals
from eventx.tasks.run_v7_memory_shadow_20261024 import RELEASE,OUT

def main():
    verify_originals();dev=REPO_ROOT/'data/v7/memory_quote_20261024/development';parent=REPO_ROOT/'eventx/release/v7/memory_quote_20261024'
    for path in [dev/'manifest.json',parent/'implementation_manifest.json']:
        m=json.loads(path.read_text())
        for p,h in m.get('locked_files',m.get('files',{})).items():
            if sha(REPO_ROOT/p)!=h:raise RuntimeError('Development lock mismatch')
    RELEASE.mkdir(exist_ok=False);OUT.mkdir(parents=True,exist_ok=True)
    cfg={'at':now().isoformat(),'source_live':'data/v7/quote_source_20261024_v02/live',
        'quote_policy':'eventx/release/v7/memory_quote_20261024/policy.json',
        'cohort':'eventx/release/v7/memory_quote_20261024/forward_cohort.jsonl','models':'data/v7/memory_quote_20261024/development/models.json',
        'reference':'persistence','candidate_promotion':False,'retuning':False,'trading':False,'network_requests':False,
        'scope':'Separate receipt-clock quote prediction; original trade classifier and protected studies unchanged'}
    write(RELEASE/'activation_policy.json',cfg)
    label='com.eventx.memory-shadow.20261024'
    plist={'Label':label,'ProgramArguments':['/usr/bin/caffeinate','-i','-s',str(REPO_ROOT/'.venv/bin/python'),'-m','eventx.tasks.run_v7_memory_shadow_20261024'],
        'WorkingDirectory':str(REPO_ROOT),'RunAtLoad':True,'KeepAlive':False,'ThrottleInterval':60,'EnvironmentVariables':{'PYTHONUNBUFFERED':'1'},
        'StandardOutPath':str(OUT/'stdout.log'),'StandardErrorPath':str(OUT/'stderr.log')}
    (RELEASE/(label+'.plist')).write_bytes(plistlib.dumps(plist))
    files=list(RELEASE.iterdir())+[Path(__file__).resolve(),dev/'manifest.json',dev/'models.json',parent/'implementation_manifest.json',parent/'policy.json',parent/'forward_cohort.jsonl',
        REPO_ROOT/'eventx/release/v7/quote_source_20261024_v02/implementation_manifest.json',
        REPO_ROOT/'eventx/v7/memory_quote_20261024.py',REPO_ROOT/'eventx/v7/quote_experiment_20261024.py']
    for n in ['run_v7_memory_shadow_20261024.py','launch_v7_memory_shadow_20261024.py','show_v7_quote_forecasts_20261024.py','run_v7_quote_experiment_20261024.py']:
        files.append(REPO_ROOT/'eventx/tasks'/n)
    write(RELEASE/'implementation_manifest.json',{'locked_files':{str(p.relative_to(REPO_ROOT)):sha(p) for p in files}})
    print(json.dumps({'frozen':str(RELEASE.relative_to(REPO_ROOT)),'reference':'persistence','promotion':False}))

if __name__=='__main__':main()
