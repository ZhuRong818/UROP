"""Install and start the prepared local user source-capture service."""
from pathlib import Path
import hashlib
import json
import os
import re
import shutil
import subprocess
from datetime import datetime, timezone

ROOT=Path(__file__).resolve().parents[2]
RELEASE=ROOT/'eventx/release/v7/original_source_capture_20261018_v02'
OUT=ROOT/'data/v7/official_source_capture_20261018'
LABEL='com.eventx.original-releases.20261018.v02'
def sha(p):
 with p.open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()
def main():
 manifest=json.loads((RELEASE/'implementation_manifest.json').read_text())
 for rel,h in manifest['locked_files'].items():
  if sha(ROOT/rel)!=h:raise RuntimeError('Implementation lock mismatch: '+rel)
 source=RELEASE/(LABEL+'.plist');target=Path.home()/'Library/LaunchAgents'/source.name
 target.parent.mkdir(parents=True,exist_ok=True)
 if target.exists() and target.read_bytes()!=source.read_bytes():raise RuntimeError('Preserve existing service configuration')
 if not target.exists():shutil.copyfile(source,target)
 domain='gui/'+str(os.getuid());service=domain+'/'+LABEL
 prior=subprocess.run(['/bin/launchctl','print',service],capture_output=True,text=True)
 if prior.returncode:
  result=subprocess.run(['/bin/launchctl','bootstrap',domain,str(target)],capture_output=True,text=True)
  if result.returncode:raise RuntimeError('launchctl bootstrap failed: '+result.stderr[:400])
 result=subprocess.run(['/bin/launchctl','print',service],capture_output=True,text=True)
 pid=re.search(r'\bpid = (\d+)',result.stdout)
 receipt={'at':datetime.now(timezone.utc).isoformat(),'service':service,'installed_plist':str(target),'plist_sha256':sha(target),
  'launchctl_status':result.returncode,'pid':int(pid.group(1)) if pid else None,'scope':'local source capture through31December; market model fixed',
  'polling_health':'Check live/status.json; launchctl registration alone does not prove network capture.'}
 path=OUT/'service_install_receipt.json'
 if path.exists():path=OUT/('service_check_'+datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')+'.json')
 path.write_text(json.dumps(receipt,indent=2)+'\n');print(json.dumps(receipt,indent=2))
if __name__=='__main__':main()
