"""Bounded public-source input readiness only; no models, labels or predictions."""
import asyncio
from collections import Counter
from datetime import datetime,timedelta
import json
import signal
import time
import httpx
from eventx.tasks.collect_v7_direct_pilot_20261022_v03 import Capture as Transport
from eventx.tasks.discover_v7_direct_pilot_20261022 import PROTECTED,now,sha,write,verify_originals
from eventx.tasks.run_v7_archive_week_pilot_20261025 import verify
from eventx.tasks.run_v7_source_time_study_20261026 import BASE,REL,REPO_ROOT
from eventx.v7.source_request_scheduler_v02 import EndpointScheduler

class Capture(Transport):
 def __init__(self):
  verify_originals();verify(REL/'implementation_manifest.json');verify(BASE/'development/manifest.json')
  self.cfg=json.loads((REL/'readiness_spec.json').read_text());self.rows=[json.loads(l) for l in (REL/'live_cohort.jsonl').read_text().splitlines()]
  self.markets={r['market_id'] for r in self.rows};self.assets={r[k] for r in self.rows for k in ['yes_asset_id','no_asset_id']}
  assert not self.markets.intersection(json.loads(PROTECTED.read_text()))
  self.out=BASE/'readiness';self.out.mkdir(parents=True,exist_ok=False);(self.out/'objects').mkdir()
  self.head=None;self.seq=0;self.counts=Counter();self.stopping=False;self.streams={};self.cycle=0
  self.run_start=now();self.stop_at=self.run_start+timedelta(seconds=self.cfg['duration_seconds']);self.journal_path=self.out/'journal.jsonl'
  self.public=httpx.AsyncClient(timeout=20);self.scheduler=EndpointScheduler({'venue_metadata':1.})
  write(self.out/'run_contract.json',{'started_at':self.run_start.isoformat(),'stop_at':self.stop_at.isoformat(),'spec_sha256':sha(REL/'readiness_spec.json'),'scope':'input_readiness_only','prospective_test_started':False})
  self.log({'kind':'process_started','at':now().isoformat(),'scope':'input_readiness_only'});self.save()

 async def rest(self):
  previous=None
  while self.active():
   at=now();begin=time.monotonic()
   if previous and (at-previous).total_seconds()>120:self.log({'kind':'operational_cycle_gap','at':at.isoformat(),'seconds':(at-previous).total_seconds()})
   previous=at;self.cycle+=1
   jobs=[]
   for row in self.rows:
    jobs.append(self.request(row,'market_metadata','https://gamma-api.polymarket.com/markets',{'condition_ids':row['market_id']}))
    jobs.append(self.request(row,'resolution_state','https://data-api.polymarket.com/v2/resolutions',{'condition':row['market_id']}))
   await asyncio.gather(*jobs);self.log({'kind':'cycle_finished','at':now().isoformat(),'cycle':self.cycle});self.save()
   await self.pause(max(0,60-(time.monotonic()-begin)))

 async def run(self):
  tasks=[asyncio.create_task(self.rest()),asyncio.create_task(self.ws())]
  try:
   await asyncio.wait_for(asyncio.gather(*tasks),timeout=max(0,(self.stop_at-now()).total_seconds()))
  except asyncio.TimeoutError:self.log({'kind':'run_deadline_reached','at':now().isoformat()})
  finally:
   self.stopping=True
   for task in tasks:task.cancel()
   await asyncio.gather(*tasks,return_exceptions=True);await self.public.aclose()
   self.log({'kind':'process_stopped','at':now().isoformat(),'production_locks_verified':verify_originals()});self.save()
   paths=[p for p in self.out.rglob('*') if p.is_file()]+[REL/'implementation_manifest.json',BASE/'development/manifest.json']
   write(self.out/'capture_manifest.json',{'files':{str(p.relative_to(REPO_ROOT)):sha(p) for p in paths}})
  print(json.dumps({'capture_completed':True,'directory':str(self.out.relative_to(REPO_ROOT))}),flush=True)

def main():
 c=Capture()
 def stop(*_):c.stopping=True
 signal.signal(signal.SIGTERM,stop);signal.signal(signal.SIGINT,stop)
 asyncio.run(c.run())
if __name__=='__main__':main()
