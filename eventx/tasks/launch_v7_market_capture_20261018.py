"""Install/start the locked, exact-cohort market source pilot."""
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
from datetime import datetime,timezone
from eventx.settings import REPO_ROOT
from eventx.tasks.prepare_v7_market_capture_20261018 import BASE,RELEASE,sha,write

LABEL='com.eventx.market-capture.20261018'
def main():
 for rel,h in json.loads((RELEASE/'implementation_manifest.json').read_text())['locked_files'].items():
  if sha(REPO_ROOT/rel)!=h:raise RuntimeError('Lock mismatch: '+rel)
 source=RELEASE/(LABEL+'.plist');target=Path.home()/'Library/LaunchAgents'/source.name
 target.parent.mkdir(parents=True,exist_ok=True)
 if target.exists() and target.read_bytes()!=source.read_bytes():raise RuntimeError('Preserve existing service')
 if not target.exists():shutil.copyfile(source,target)
 domain='gui/'+str(os.getuid());service=domain+'/'+LABEL
 result=subprocess.run(['/bin/launchctl','print',service],capture_output=True,text=True)
 if result.returncode:
  result=subprocess.run(['/bin/launchctl','bootstrap',domain,str(target)],capture_output=True,text=True)
  if result.returncode:raise RuntimeError('launchctl bootstrap failed: '+result.stderr[:300])
 result=subprocess.run(['/bin/launchctl','print',service],capture_output=True,text=True);pid=re.search(r'\bpid = (\d+)',result.stdout)
 receipt={'at':datetime.now(timezone.utc).isoformat(),'service':service,'pid':int(pid.group(1)) if pid else None,
  'installed_plist':str(target),'plist_sha256':sha(target),'launchctl_status':result.returncode,
  'health':'Registration alone does not prove capture. Inspect live/status.json and journal receipts.'}
 p=BASE/('service_'+datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')+'.json');write(p,receipt);print(json.dumps(receipt,indent=2))
if __name__=='__main__':main()
