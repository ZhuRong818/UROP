"""Retain a full180s SSE observation: distinguish idle read timeout from no events."""
import argparse
import asyncio
import json
import time
from datetime import datetime,timezone
from eventx.settings import REPO_ROOT
from eventx.tasks.discover_v7_source_control_20261018 import sha,write
from eventx.tasks.run_v7_source_verification_20261018 import Diagnostic,iso

RELEASE=REPO_ROOT/'eventx/release/v7/source_verification_20261018_sse_v02'
def prepare():
 if RELEASE.exists():raise RuntimeError('Preserve version')
 RELEASE.mkdir(parents=True)
 write(RELEASE/'plan.json',{'created_at':iso(),'purpose':'SSE idle-timeout diagnosis only, same eight preselected markets',
  'change':'Original attempt had20s idle ReadTimeout; absence of data in that interval is not proof of a failed stream. This version uses180s total deadline and no idle read timeout.',
  'observation_seconds':180,'source':'Lumid prediction-markets/stream','model_development':False})
 paths=[RELEASE/'plan.json',REPO_ROOT/'eventx/tasks/run_v7_sse_verification_20261018_v02.py',
  REPO_ROOT/'eventx/release/v7/source_verification_20261018/implementation_manifest.json']
 write(RELEASE/'implementation_manifest.json',{'locked_files':{str(p.relative_to(REPO_ROOT)):sha(p) for p in paths}})
 print(str(RELEASE.relative_to(REPO_ROOT)))
async def run():
 for p,h in json.loads((RELEASE/'implementation_manifest.json').read_text())['locked_files'].items():assert sha(REPO_ROOT/p)==h
 d=Diagnostic();write(d.out/'sse_v02_contract.json',json.loads((RELEASE/'plan.json').read_text()))
 params={'condition_ids':','.join(sorted(d.markets)),'asset_ids':','.join(sorted(d.assets))}
 state={'status':'connecting','started_at':iso(),'frames':0,'data_frames':0,'comment_frames':0};d.streams['lumid_sse_v02']=state
 started=time.monotonic()
 try:
  # One overall deadline bounds connect plus observation. No short idle-read cutoff.
  async with asyncio.timeout(180):
   async with d.lumid.stream('GET','/prediction-markets/stream',params=params,timeout=None) as r:
    state['http_status']=r.status_code;state['connected_at']=iso();d.log({'kind':'sse_v02_connected','params':params,'http_status':r.status_code,'at':iso()})
    if r.status_code!=200:state.update(status='failed_http',payload_sha256=d.store(await r.aread()))
    else:
     state['status']='observing';lines=[]
     async for line in r.aiter_lines():
      if line:lines.append(line);continue
      if not lines:continue
      text='\n'.join(x[5:].strip() for x in lines if x.startswith('data:'))
      if text:d.validate(json.loads(text));state['data_frames']+=1
      else:state['comment_frames']+=1
      h=d.store(('\n'.join(lines)+'\n\n').encode());d.log({'kind':'sse_frame','payload_sha256':h,'available_at':iso()})
      state['frames']+=1;state['last_frame_at']=iso();lines=[];d.heartbeat()
     state['status']='server_closed'
 except TimeoutError:state['status']='bounded_window_complete'
 except Exception as e:state.update(status='failed',error_type=type(e).__name__)
 state.update(finished_at=iso(),elapsed_seconds=time.monotonic()-started)
 d.log({'kind':'sse_v02_finished','state':state});d.heartbeat();await d.lumid.aclose();await d.public.aclose();d.verify_locks()
 write(d.out/'report.json',{'kind':'sse_idle_timeout_recheck_v02','state':state,'production_locks_and_model_match':True,'forecasts_or_labels_computed':False})
 write(d.out/'manifest.json',{'files':{str(p.relative_to(REPO_ROOT)):sha(p) for p in d.out.iterdir() if p.is_file()},
  'payloads':{p.name:sha(p) for p in (d.out/'objects').iterdir()}})
 print(json.dumps({'directory':str(d.out.relative_to(REPO_ROOT)),'state':state},indent=2))
def main():
 ap=argparse.ArgumentParser();ap.add_argument('--prepare',action='store_true');args=ap.parse_args()
 if args.prepare:prepare()
 else:asyncio.run(run())
if __name__=='__main__':main()
