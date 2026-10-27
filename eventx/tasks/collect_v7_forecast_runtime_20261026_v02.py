"""V02 source collector: readiness rehearsal or activated prospective source.

Same public WebSocket/REST transport as V01. Adds monotonic-anchored SNTP correction:
every journal record carries corrected_epoch (None until a valid estimate exists).
Deadlines use the monotonic clock; wall steps are logged for audit and trigger a re-probe.
"""
import argparse
import asyncio
from collections import Counter
from concurrent.futures import ThreadPoolExecutor
import json
import os
import signal
import time
from datetime import timedelta

import httpx

from eventx.tasks.collect_v7_direct_pilot_20261022_v03 import Capture as Transport
from eventx.tasks.discover_v7_direct_pilot_20261022 import PROTECTED, now as wall_now, verify_originals
from eventx.v7.source_request_scheduler_v02 import EndpointScheduler
from eventx.v7.sntp_client_20261026 import HOSTS, probe, estimate
from eventx.v7 import forecast_runtime_20261026_v02 as rt

READINESS_SECONDS = 3600
PROBE_SECONDS = 60
STEP_THRESHOLD = .02


class Capture(Transport):
    def __init__(self, prospective=False):
        rt.verify_release()
        verify_originals()
        self.cfg = json.loads((rt.REL/'readiness_spec.json').read_text())
        self.rows = rt.load_cohort()
        self.markets = {r['market_id'] for r in self.rows}
        self.assets = {r[k] for r in self.rows for k in ['yes_asset_id', 'no_asset_id']}
        if self.markets & set(json.loads(PROTECTED.read_text())):
            raise RuntimeError('Protected scope')
        self.anchor = None
        self.last_corrected = None
        self.clock_pair = None
        self.reprobe = None
        self.head = None
        self.seq = 0
        self.counts = Counter()
        self.stopping = False
        self.streams = {}
        self.cycle = 0
        self.run_start = wall_now()
        self.start_mono = time.monotonic()
        self.out = rt.BASE/('prospective/source' if prospective else 'readiness')
        self.out.mkdir(parents=True, exist_ok=False)
        (self.out/'objects').mkdir()
        self.journal_path = self.out/'journal.jsonl'
        self.state_path = self.out/'clock_state.json'
        self.public = httpx.AsyncClient(timeout=20)
        self.scheduler = EndpointScheduler({'venue_metadata': self.cfg['metadata_request_interval_seconds']})
        self.stop_at = self.run_start+timedelta(seconds=READINESS_SECONDS)
        self.log({'kind': 'process_started', 'at': self.run_start.isoformat(), 'scope': 'source_only'})
        self.measure_clock()  # A valid anchor is required to convert any corrected deadline.
        if prospective:
            receipt = json.loads((rt.BASE/'activation_receipt.json').read_text())
            rt.require_activation(receipt, self.corrected())
            if self.corrected() >= receipt['first_grid']-rt.WARMUP:
                raise RuntimeError('Source must start >=30 min before first grid; no implicit restart')
            duration = receipt['open_after']+30-self.corrected()
        else:
            duration = READINESS_SECONDS
        self.stop_mono = self.start_mono+duration
        self.stop_at = self.run_start+timedelta(seconds=duration)  # informational; deadline is monotonic
        rt.v01.write_new(self.out/'run_contract.json', {
            'started_at': self.run_start.isoformat(), 'duration_seconds': duration, 'deadline_clock': 'monotonic',
            'mode': 'prospective_source' if prospective else 'input_readiness_only',
            'implementation_sha256': rt.sha(rt.REL/'implementation_manifest.json'), 'prospective_test_started': prospective})
        self.save()

    def corrected(self, mono=None):
        if self.anchor is None:
            return None
        mono = time.monotonic() if mono is None else mono
        if mono-self.anchor['monotonic_seconds'] > rt.ESTIMATE_MAX_AGE:
            return None
        return self.anchor['corrected_epoch']+(mono-self.anchor['monotonic_seconds'])

    def active(self):
        return not self.stopping and time.monotonic() < getattr(self, 'stop_mono', float('inf')) and not (self.out/'STOP').exists()

    def log(self, value):
        wall, mono = time.time(), time.monotonic()
        previous, self.clock_pair = self.clock_pair, (wall, mono)
        if previous:
            step = (wall-previous[0])-(mono-previous[1])
            if abs(step) > STEP_THRESHOLD:
                self._append({'kind': 'clock_step', 'at': wall_now().isoformat(), 'wall_minus_monotonic_change_seconds': step,
                              'local_wall_epoch': wall, 'monotonic_seconds': mono, 'corrected_epoch': self._stamp(mono),
                              'effect': 'audit_only_corrected_clock_unaffected'})
                if self.reprobe is not None:
                    self.reprobe.set()
        self._append(dict(value, local_wall_epoch=wall, monotonic_seconds=mono, corrected_epoch=self._stamp(mono)))

    def _stamp(self, mono):
        c = self.corrected(mono)
        if c is not None and self.last_corrected is not None:
            c = max(c, self.last_corrected)  # Journal order never runs backwards in corrected time.
        if c is not None:
            self.last_corrected = c
        return c

    def _append(self, value):
        Transport.log(self, value)

    @staticmethod
    def probe_all():
        """Network-only; runs in a worker thread and touches no collector state."""
        with ThreadPoolExecutor(max_workers=len(HOSTS)) as pool:
            return list(pool.map(probe, HOSTS))

    def measure_clock(self, ms=None):
        """Estimate, anchor and log. Must run on the event-loop thread: log() advances the
        hash chain, and a concurrent call from another thread forks it (superseded activation 2)."""
        ms = self.probe_all() if ms is None else ms
        offset, half, reasons = estimate(ms)
        wall, mono = time.time(), time.monotonic()
        if offset is not None:
            self.anchor = {'corrected_epoch': wall+offset, 'monotonic_seconds': mono}
        self.log({'kind': 'clock_estimate', 'at': wall_now().isoformat(), 'measurements': ms, 'offset_seconds': offset,
                  'half_width_seconds': half, 'valid': offset is not None, 'reasons': reasons})
        mono = time.monotonic()
        c = self.corrected(mono)
        tmp = self.out/'clock_state.tmp'
        tmp.write_text(json.dumps({'valid': c is not None, 'corrected_epoch': c, 'monotonic_seconds': mono,
                                   'offset_seconds': offset, 'half_width_seconds': half}))
        os.replace(tmp, self.state_path)

    async def clocks(self):
        self.reprobe = asyncio.Event()
        while self.active():
            try:
                await asyncio.wait_for(self.reprobe.wait(), timeout=PROBE_SECONDS)
            except asyncio.TimeoutError:
                pass
            self.reprobe.clear()
            if not self.active():
                break
            try:
                self.measure_clock(await asyncio.to_thread(self.probe_all))
            except Exception as e:
                self.log({'kind': 'clock_probe_error', 'at': wall_now().isoformat(), 'error': type(e).__name__})

    async def ws(self):
        # A connection logged before any valid clock anchor would carry no corrected time,
        # leaving transport_ready() blind to it for the whole run (readiness attempt 2).
        while self.active() and self.corrected() is None:
            await self.pause(1)
        await Transport.ws(self)

    async def rest(self):
        previous = None
        while self.active():
            begin = time.monotonic()
            if previous is not None and begin-previous > 120:
                self.log({'kind': 'operational_cycle_gap', 'at': wall_now().isoformat(), 'seconds': begin-previous})
            previous = begin
            self.cycle += 1
            jobs = []
            for row in self.rows:
                jobs.append(self.request(row, 'market_metadata', 'https://gamma-api.polymarket.com/markets', {'condition_ids': row['market_id']}))
                jobs.append(self.request(row, 'resolution_state', 'https://data-api.polymarket.com/v2/resolutions', {'condition': row['market_id']}))
            await asyncio.gather(*jobs)
            self.log({'kind': 'cycle_finished', 'at': wall_now().isoformat(), 'cycle': self.cycle})
            self.save()
            await self.pause(max(0, self.cfg['poll_seconds']-(time.monotonic()-begin)))

    async def run(self):
        tasks = [asyncio.create_task(self.rest()), asyncio.create_task(self.ws()), asyncio.create_task(self.clocks())]
        try:
            await asyncio.wait_for(asyncio.gather(*tasks), timeout=max(0, self.stop_mono-time.monotonic()))
        except asyncio.TimeoutError:
            self.log({'kind': 'run_deadline_reached', 'at': wall_now().isoformat()})
        finally:
            self.stopping = True
            for task in tasks:
                task.cancel()
            await asyncio.gather(*tasks, return_exceptions=True)
            await self.public.aclose()
            for state in self.streams.values():
                state.update(status='stopped', stopped_at=wall_now().isoformat())
            self.log({'kind': 'process_stopped', 'at': wall_now().isoformat(), 'production_locks_verified': verify_originals(),
                      'monotonic_deadline_reached': time.monotonic() >= self.stop_mono})
            self.save()
            paths = [p for p in self.out.rglob('*') if p.is_file()]+[rt.REL/'implementation_manifest.json']
            rt.v01.write_new(self.out/'capture_manifest.json', {'files': {str(p.relative_to(rt.REPO_ROOT)): rt.sha(p) for p in paths}})
        print(json.dumps({'capture_completed': True, 'directory': str(self.out.relative_to(rt.REPO_ROOT))}), flush=True)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--prospective', action='store_true')
    c = Capture(parser.parse_args().prospective)

    def stop(*_):
        c.stopping = True
    signal.signal(signal.SIGTERM, stop)
    signal.signal(signal.SIGINT, stop)
    asyncio.run(c.run())


if __name__ == '__main__':
    main()
