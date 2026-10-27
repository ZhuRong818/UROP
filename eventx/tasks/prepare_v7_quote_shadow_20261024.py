"""Freeze a bounded read-only shadow consumer of the existing two-market feed."""
import json
from pathlib import Path
import plistlib
from eventx.tasks.discover_v7_direct_pilot_20261022 import REPO_ROOT,now,sha,write,verify_originals
from eventx.tasks.run_v7_quote_shadow_20261024 import RELEASE,OUT

def main():
    verify_originals()
    dev=REPO_ROOT/'data/v7/quote_experiment_20261024/development'
    for p,h in json.loads((dev/'manifest.json').read_text())['files'].items():
        if sha(REPO_ROOT/p)!=h:raise RuntimeError('Development artifact drift')
    if not (dev/'ridge_model.json').exists():raise RuntimeError('No fitted fixed candidate; preserve failure')
    RELEASE.mkdir(parents=True,exist_ok=False);OUT.mkdir(parents=True,exist_ok=True)
    cfg={'at':now().isoformat(),'scope':'New user-authorized V7 quote experiment; old trade model gated and unchanged',
        'source_live':'data/v7/expansion_source_pilot_20261024/live',
        'quote_policy':'eventx/release/v7/quote_experiment_20261024/policy.json',
        'cohort':'eventx/release/v7/quote_experiment_20261024/forward_cohort.jsonl',
        'model':'data/v7/quote_experiment_20261024/development/ridge_model.json',
        'reference':'persistence','candidate_promotion':False,'network_requests':False,
        'reporting':'All three frozen forecasts on identical keys; no retuning or claim of independent validation'}
    write(RELEASE/'activation_policy.json',cfg)
    label='com.eventx.quote-shadow.20261024'
    plist={'Label':label,'ProgramArguments':['/usr/bin/caffeinate','-i','-s',str(REPO_ROOT/'.venv/bin/python'),'-m','eventx.tasks.run_v7_quote_shadow_20261024'],
        'WorkingDirectory':str(REPO_ROOT),'RunAtLoad':True,'KeepAlive':False,'ThrottleInterval':60,
        'EnvironmentVariables':{'PYTHONUNBUFFERED':'1'},'StandardOutPath':str(OUT/'stdout.log'),'StandardErrorPath':str(OUT/'stderr.log')}
    (RELEASE/(label+'.plist')).write_bytes(plistlib.dumps(plist))
    files=list(RELEASE.iterdir())+[Path(__file__).resolve(),dev/'manifest.json',dev/'ridge_model.json',
        REPO_ROOT/'eventx/release/v7/quote_experiment_20261024/implementation_manifest.json',
        REPO_ROOT/'eventx/release/v7/quote_experiment_20261024/policy.json',
        REPO_ROOT/'eventx/release/v7/quote_experiment_20261024/forward_cohort.jsonl',
        REPO_ROOT/'eventx/release/v7/expansion_source_pilot_20261024/implementation_manifest.json',
        REPO_ROOT/'eventx/v7/quote_experiment_20261024.py',
        REPO_ROOT/'eventx/tasks/run_v7_quote_shadow_20261024.py',REPO_ROOT/'eventx/tasks/launch_v7_quote_shadow_20261024.py']
    write(RELEASE/'implementation_manifest.json',{'locked_files':{str(p.relative_to(REPO_ROOT)):sha(p) for p in files}})
    print(json.dumps({'scope':cfg['scope'],'models':['persistence','weighted_midpoint','ridge'],'source_collector_changed':False}))

if __name__=='__main__':main()
