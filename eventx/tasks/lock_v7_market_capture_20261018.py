"""Lock the concrete market capture specification and local service configuration."""
import json
import plistlib
from datetime import datetime,timezone
from eventx.settings import REPO_ROOT
from eventx.tasks.prepare_v7_market_capture_20261018 import RELEASE,BASE,sha,write

LABEL='com.eventx.market-capture.20261018'
def main():
 if (RELEASE/'implementation_manifest.json').exists():raise RuntimeError('Preserve lock')
 live=BASE/'live';live.mkdir(exist_ok=True)
 config={'Label':LABEL,'ProgramArguments':['/usr/bin/caffeinate','-i','-s',str(REPO_ROOT/'.venv/bin/python'),
  '-m','eventx.tasks.collect_v7_market_capture_20261018'],'WorkingDirectory':str(REPO_ROOT),
  'RunAtLoad':True,'KeepAlive':{'SuccessfulExit':False},'ThrottleInterval':60,
  'StandardOutPath':str(live/'stdout.log'),'StandardErrorPath':str(live/'stderr.log'),
  'EnvironmentVariables':{'PYTHONUNBUFFERED':'1'}}
 with (RELEASE/(LABEL+'.plist')).open('wb') as f:plistlib.dump(config,f)
 files=list(RELEASE.glob('*'))+[REPO_ROOT/'eventx/tasks'/n for n in [
  'collect_v7_market_capture_20261018.py','prepare_v7_market_capture_20261018.py',
  'launch_v7_market_capture_20261018.py','lock_v7_market_capture_20261018.py']]
 write(RELEASE/'implementation_manifest.json',{'created_at':datetime.now(timezone.utc).isoformat(),
  'locked_files':{str(p.relative_to(REPO_ROOT)):sha(p) for p in files if p.is_file()},
  'scope':'collection feasibility, not model selection or confirmatory evaluation'})
 print(json.dumps({'release':str(RELEASE.relative_to(REPO_ROOT)),'locked_files':len(files),'label':LABEL}))
if __name__=='__main__':main()
