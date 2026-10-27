"""Same collector for a fixed input-only rehearsal or a separately activated source."""
import argparse
import asyncio
from collections import Counter
from datetime import datetime,timedelta,timezone
import json
import signal
import time
import httpx
from eventx.tasks.collect_v7_clock_readiness_20261026 import Capture as Parent
from eventx.tasks.discover_v7_direct_pilot_20261022 import PROTECTED,verify_originals
from eventx.v7.source_request_scheduler_v02 import EndpointScheduler
from eventx.v7.forecast_runtime_20261026 import BASE,REL,OLDREL,OLD,REPO_ROOT,verify_release,require_activation,sha,write_new,now,iso
from eventx.v7.native_clock_receipt_20261026 import selected_packet_check

class Capture(Parent):
    def __init__(self,prospective=False):
        verify_release();verify_originals()
        self.cfg=json.loads((OLDREL/'readiness_spec.json').read_text())
        self.rows=[json.loads(l) for l in (OLDREL/'live_cohort.jsonl').read_text().splitlines()]
        self.markets={r['market_id'] for r in self.rows};self.assets={r[k] for r in self.rows for k in ['yes_asset_id','no_asset_id']}
        if self.markets.intersection(json.loads(PROTECTED.read_text())): raise RuntimeError('Protected scope')
        self.run_start=datetime.now(timezone.utc)
        if prospective:
            receipt=json.loads((BASE/'activation_receipt.json').read_text());require_activation(receipt,now())
            self.stop_at=datetime.fromtimestamp(receipt['open_after']+30,timezone.utc)
            if now()>=receipt['first_grid']: raise RuntimeError('Source must start before first grid; no implicit restart')
            self.out=BASE/'prospective/source'
        else:
            self.stop_at=self.run_start+timedelta(seconds=2400);self.out=BASE/'readiness'
        self.out.mkdir(parents=True,exist_ok=False);(self.out/'objects').mkdir()
        self.head=None;self.seq=0;self.counts=Counter();self.stopping=False;self.streams={};self.cycle=0
        self.journal_path=self.out/'journal.jsonl';self.public=httpx.AsyncClient(timeout=20)
        self.scheduler=EndpointScheduler({'venue_metadata':1.})
        write_new(self.out/'run_contract.json',{'started_at':self.run_start.isoformat(),'stop_at':self.stop_at.isoformat(),'mode':'prospective_source' if prospective else 'input_readiness_only','implementation_sha256':sha(REL/'implementation_manifest.json'),'prospective_test_started':prospective})
        self.log({'kind':'process_started','at':self.run_start.isoformat(),'scope':'source_only'});self.save()
    def log(self,value):
        if value.get('kind')=='clock_probe':
            value={**value,'packet_validation':[{'host':m['host'],**selected_packet_check(m)} for m in value['measurements']]}
        super().log(value)
    async def run(self):
        tasks=[asyncio.create_task(self.rest()),asyncio.create_task(self.ws()),asyncio.create_task(self.clocks())]
        try:
            await asyncio.wait_for(asyncio.gather(*tasks),timeout=max(0,self.stop_at.timestamp()-now()))
        except asyncio.TimeoutError: self.log({'kind':'run_deadline_reached','at':iso(now())})
        finally:
            self.stopping=True
            for task in tasks: task.cancel()
            await asyncio.gather(*tasks,return_exceptions=True);await self.public.aclose()
            for state in self.streams.values(): state.update(status='stopped',stopped_at=iso(now()))
            self.log({'kind':'process_stopped','at':iso(now()),'production_locks_verified':verify_originals()});self.save()
            paths=[p for p in self.out.rglob('*') if p.is_file()]+[REL/'implementation_manifest.json',OLD/'development/manifest.json']
            write_new(self.out/'capture_manifest.json',{'files':{str(p.relative_to(REPO_ROOT)):sha(p) for p in paths}})
        print(json.dumps({'capture_completed':True,'directory':str(self.out.relative_to(REPO_ROOT))}),flush=True)

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--prospective',action='store_true');args=parser.parse_args()
    c=Capture(args.prospective)
    def stop(*_): c.stopping=True
    signal.signal(signal.SIGTERM,stop);signal.signal(signal.SIGINT,stop)
    asyncio.run(c.run())
if __name__=='__main__': main()
