"""Repeat input-only capture with independent clocks and wall/monotonic step checks."""
import asyncio,json,time
from concurrent.futures import ThreadPoolExecutor
from eventx.tasks import collect_v7_source_time_readiness_20261026 as parent
from eventx.tasks.run_v7_source_time_study_20261026_v03 import BASE,REL,REPO_ROOT
from eventx.tasks.probe_v7_clock_alignment_20261026 import ntp
from eventx.tasks.discover_v7_direct_pilot_20261022 import now,write,sha,verify_originals

# New process-local roots; no predecessor source files or artifacts are modified.
parent.BASE=BASE;parent.REL=REL

class Capture(parent.Capture):
 def log(self,value):
  wall=time.time();mono=time.monotonic();previous=getattr(self,'clock_pair',None)
  self.clock_pair=(wall,mono)
  if previous:
   step=(wall-previous[0])-(mono-previous[1])
   if abs(step)>.02:
    super().log({'kind':'clock_step','at':now().isoformat(),'wall_minus_monotonic_change_seconds':step})
    super().log({'kind':'operational_cycle_gap','at':now().isoformat(),'reason':'clock_step_over20ms'})
  super().log(dict(value,local_wall_epoch=wall,monotonic_seconds=mono))

 async def clocks(self):
  while self.active():
   def measure():
    with ThreadPoolExecutor(max_workers=3) as pool:
     return list(pool.map(ntp,['time.google.com','time.cloudflare.com','time.apple.com']))
   try:rr=await asyncio.to_thread(measure)
   except Exception as e:rr=[];self.log({'kind':'clock_probe_error','at':now().isoformat(),'error':type(e).__name__})
   self.log({'kind':'clock_probe','at':now().isoformat(),'available_epoch':time.time(),'measurements':rr})
   await self.pause(300)

 async def run(self):
  tasks=[asyncio.create_task(self.rest()),asyncio.create_task(self.ws()),asyncio.create_task(self.clocks())]
  try:await asyncio.wait_for(asyncio.gather(*tasks),timeout=max(0,(self.stop_at-now()).total_seconds()))
  except asyncio.TimeoutError:self.log({'kind':'run_deadline_reached','at':now().isoformat()})
  finally:
   self.stopping=True
   for task in tasks:task.cancel()
   await asyncio.gather(*tasks,return_exceptions=True);await self.public.aclose()
   for state in self.streams.values():state.update(status='stopped',stopped_at=now().isoformat())
   self.log({'kind':'process_stopped','at':now().isoformat(),'production_locks_verified':verify_originals()});self.save()
   paths=[p for p in self.out.rglob('*') if p.is_file()]+[REL/'implementation_manifest.json',BASE/'development/manifest.json']
   write(self.out/'capture_manifest.json',{'files':{str(p.relative_to(REPO_ROOT)):sha(p) for p in paths}})
  print(json.dumps({'capture_completed':True,'directory':str(self.out.relative_to(REPO_ROOT))}),flush=True)

def main():
 import signal
 c=Capture()
 def stop(*_):c.stopping=True
 signal.signal(signal.SIGTERM,stop);signal.signal(signal.SIGINT,stop)
 asyncio.run(c.run())
if __name__=='__main__':main()
