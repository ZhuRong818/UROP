"""Register the separately frozen autonomous source workflow."""
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
from eventx.settings import REPO_ROOT
from eventx.tasks.discover_v7_direct_pilot_20261022 import now, sha, write, verify_originals
BASE=REPO_ROOT/"data/v7/source_workflow_20261022"
RELEASE=REPO_ROOT/"eventx/release/v7/source_workflow_20261022"

def main():
    verify_originals()
    for rel,h in json.loads((RELEASE/'implementation_manifest.json').read_text())['locked_files'].items():
        if sha(REPO_ROOT/rel)!=h:
            raise RuntimeError('Pilot lock mismatch: '+rel)
    label='com.eventx.source-workflow.20261022'
    source=RELEASE/(label+'.plist')
    target=Path.home()/'Library/LaunchAgents'/source.name
    target.parent.mkdir(parents=True,exist_ok=True)
    if target.exists() and target.read_bytes()!=source.read_bytes():
        raise RuntimeError('Preserve existing service')
    if not target.exists():shutil.copyfile(source,target)
    domain='gui/'+str(os.getuid())
    result=subprocess.run(['/bin/launchctl','print',domain+'/'+label],capture_output=True,text=True)
    if result.returncode:
        result=subprocess.run(['/bin/launchctl','bootstrap',domain,str(target)],capture_output=True,text=True)
        if result.returncode:raise RuntimeError('Service registration failed: '+result.stderr[:200])
    result=subprocess.run(['/bin/launchctl','print',domain+'/'+label],capture_output=True,text=True)
    pid=re.search(r'\bpid = (\d+)',result.stdout)
    receipt={'at':now().isoformat(),'service':domain+'/'+label,'pid':int(pid.group(1)) if pid else None,
             'plist_sha256':sha(target),'launchctl_status':result.returncode,
             'scope':'source workflow waiting for original completion, then24h API-v2 rehearsal; no event scoring',
             'health':'Registration is not capture success; inspect receipts and final audit.'}
    write(BASE/('service_'+now().strftime('%Y%m%dT%H%M%SZ')+'.json'),receipt)
    print(json.dumps(receipt,indent=2))

if __name__=='__main__':main()
