"""Register only the separately frozen 24-hour source rehearsal service."""
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
from eventx.settings import REPO_ROOT
from eventx.tasks.discover_v7_direct_pilot_20261022 import BASE, RELEASE, now, sha, write, verify_originals

def main():
    verify_originals()
    for rel,h in json.loads((RELEASE/'implementation_manifest.json').read_text())['locked_files'].items():
        if sha(REPO_ROOT/rel)!=h:
            raise RuntimeError('Pilot lock mismatch: '+rel)
    label='com.eventx.direct-source-pilot.20261022'
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
             'scope':'separate bounded source rehearsal; no old service changed',
             'health':'Registration is not capture success; inspect receipts and final audit.'}
    write(BASE/('service_'+now().strftime('%Y%m%dT%H%M%SZ')+'.json'),receipt)
    print(json.dumps(receipt,indent=2))

if __name__=='__main__':main()
