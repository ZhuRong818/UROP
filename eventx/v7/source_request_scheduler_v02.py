"""Staged endpoint scheduler; not wired into any frozen/running collector."""
import asyncio
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
import math
import time

def retry_seconds(value, wall_now=None, minimum=60.):
    """Honor either HTTP Retry-After form; invalid values use a conservative floor."""
    wall_now = wall_now or datetime.now(timezone.utc)
    try:
        delay = float(value)
        if not math.isfinite(delay):
            raise ValueError('Non-finite delay')
    except (ValueError, TypeError):
        try:
            date = parsedate_to_datetime(value)
            if date.tzinfo is None:
                date = date.replace(tzinfo=timezone.utc)
            delay = (date-wall_now).total_seconds()
        except (ValueError, TypeError, OverflowError):
            delay = minimum
    return max(minimum, delay)

class EndpointScheduler:
    """One in-flight request per endpoint bucket; other buckets stay independent.

    Keys must be predeclared fixed endpoint groups, not generated per market/request.
    Call defer inside slot before releasing the response. A server-wide constraint
    can be propagated with defer_all; no alternate endpoint may replace a blocked
    trade request. This component does not establish provider quotas or coverage.
    """
    def __init__(self, intervals, clock=time.monotonic, sleep=asyncio.sleep):
        if not intervals or any(not math.isfinite(x) or x <= 0 for x in intervals.values()):
            raise ValueError('Positive finite pacing intervals required')
        self.intervals = dict(intervals)
        self.clock, self.sleep = clock, sleep
        self.locks = {k: asyncio.Lock() for k in intervals}
        self.next_start = {k: 0. for k in intervals}
        self.blocked_until = {k: 0. for k in intervals}

    @asynccontextmanager
    async def slot(self, key):
        async with self.locks[key]:
            while True:
                remaining = max(self.next_start[key], self.blocked_until[key])-self.clock()
                if remaining <= 0:
                    break
                await self.sleep(remaining)
            self.next_start[key] = self.clock()+self.intervals[key]
            yield

    def defer(self, key, seconds):
        if not math.isfinite(seconds) or seconds < 0:
            raise ValueError('Finite nonnegative backoff required')
        self.blocked_until[key] = max(self.blocked_until[key], self.clock()+seconds)

    def defer_all(self, seconds):
        for key in self.intervals:
            self.defer(key, seconds)
