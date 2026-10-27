"""Separate two-contract source run reusing frozen V03 transport and audit code."""
import asyncio
import signal
import time
from eventx.tasks import collect_v7_direct_pilot_20261022_v03 as transport
from eventx.tasks import audit_v7_direct_pilot_20261022_v03 as auditor
from eventx.tasks.prepare_v7_expansion_pilot_20261024 import BASE, RELEASE

# Explicit new run roots; imported implementation files stay byte-for-byte frozen.
transport.BASE=auditor.BASE=BASE
transport.RELEASE=auditor.RELEASE=RELEASE

class Capture(transport.Capture):
    async def rest(self):
        previous_cycle_at=None
        while self.active():
            begin=time.monotonic();at=transport.now()
            if previous_cycle_at is not None and (at-previous_cycle_at).total_seconds()>120:
                self.log({'kind':'operational_cycle_gap','at':at.isoformat(),
                    'seconds':(at-previous_cycle_at).total_seconds(),
                    'interpretation':'Not a source-completeness claim; affected future prediction history must be invalidated.'})
            previous_cycle_at=at;self.cycle+=1
            end=int(at.timestamp());reconcile=self.cycle==1 or self.cycle%5==0
            start=end-(21600 if reconcile else 1800);jobs=[]
            for row in self.rows:
                jobs.append(self.trades(row,'venue',start,end))
                for key in ['yes_asset_id','no_asset_id']:
                    jobs.append(self.request(row,'book_'+key,'https://clob.polymarket.com/book',{'token_id':row[key]}))
                jobs.append(self.request(row,'market_metadata','https://gamma-api.polymarket.com/markets',{'condition_ids':row['market_id']}))
                jobs.append(self.request(row,'resolution_state','https://data-api.polymarket.com/v2/resolutions',{'condition':row['market_id']}))
                if reconcile:
                    jobs.append(self.trades(row,'lumid',start,end))
                    jobs.append(self.request(row,'quotes','/prediction-markets/orderbook/polymarket/'+row['yes_asset_id'],{'limit':1},'lumid'))
            await asyncio.gather(*jobs)
            self.log({'kind':'cycle_finished','at':transport.now().isoformat(),'cycle':self.cycle,
                'common_trade_window':[start,end],'reconciliation':reconcile,'duration_seconds':time.monotonic()-begin})
            self.save();await self.pause(max(0,self.cfg['poll_seconds']-(time.monotonic()-begin)))

def main():
    c=Capture()
    def stop(*_):c.stopping=True
    signal.signal(signal.SIGTERM,stop);signal.signal(signal.SIGINT,stop)
    asyncio.run(c.run())

if __name__=='__main__':main()
