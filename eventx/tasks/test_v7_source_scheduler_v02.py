"""Failure-mode checks for the staged scheduler, using no real API traffic."""
import asyncio
from datetime import datetime, timezone
import unittest
from eventx.v7.source_request_scheduler_v02 import EndpointScheduler, retry_seconds

class FakeClock:
    def __init__(self): self.t=0.; self.waits=[]
    def now(self): return self.t
    async def sleep(self,seconds): self.waits.append(seconds); self.t+=seconds

class SchedulerTests(unittest.IsolatedAsyncioTestCase):
    async def test_trade_backoff_does_not_block_book(self):
        c=FakeClock();s=EndpointScheduler({'trade':2.,'book':.5},c.now,c.sleep)
        s.defer('trade',60)
        async with s.slot('book'): self.assertEqual(c.t,0)
        async with s.slot('trade'): self.assertEqual(c.t,60)

    async def test_same_bucket_paced_and_longer_backoff_preserved(self):
        c=FakeClock();s=EndpointScheduler({'trade':2.},c.now,c.sleep)
        async with s.slot('trade'): pass
        async with s.slot('trade'): self.assertEqual(c.t,2)
        s.defer('trade',120);s.defer('trade',60)
        async with s.slot('trade'): self.assertEqual(c.t,122)

    async def test_no_second_inflight_before_429_is_recorded(self):
        s=EndpointScheduler({'trade':.001});entered=asyncio.Event();release=asyncio.Event();order=[]
        async def first():
            async with s.slot('trade'):
                order.append('first');entered.set();await release.wait();s.defer('trade',.01)
        async def second():
            await entered.wait()
            async with s.slot('trade'): order.append('second')
        a=asyncio.create_task(first());b=asyncio.create_task(second())
        await entered.wait();await asyncio.sleep(0)
        self.assertEqual(order,['first']);release.set();await asyncio.gather(a,b)
        self.assertEqual(order,['first','second'])

    async def test_global_server_constraint_propagates(self):
        c=FakeClock();s=EndpointScheduler({'trade':2.,'book':.5},c.now,c.sleep)
        s.defer_all(90)
        async with s.slot('book'): self.assertEqual(c.t,90)

    async def test_cancellation_releases_lock(self):
        s=EndpointScheduler({'trade':.001});entered=asyncio.Event()
        async def first():
            async with s.slot('trade'): entered.set();await asyncio.Event().wait()
        task=asyncio.create_task(first());await entered.wait();task.cancel()
        with self.assertRaises(asyncio.CancelledError):await task
        async with s.slot('trade'): pass

    async def test_retry_after_forms_and_invalid_values(self):
        at=datetime(2026,10,22,6,0,tzinfo=timezone.utc)
        self.assertEqual(retry_seconds('180',at),180)
        self.assertEqual(retry_seconds('Thu, 22 Oct 2026 06:02:00 GMT',at),120)
        for value in [None,'garbage','NaN','-2']:
            self.assertEqual(retry_seconds(value,at),60)

if __name__=='__main__':unittest.main()
