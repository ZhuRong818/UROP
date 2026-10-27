"""V03 cursor-paginated endpoint-scheduled source rehearsal; never constructs forecast labels."""
import argparse
import asyncio
from collections import Counter
from datetime import datetime, timedelta, timezone
import fcntl
import hashlib
import json
import math
import os
import signal
import time
import uuid
import httpx
import websockets
from eventx.settings import ApiSettings, REPO_ROOT
from eventx.tasks.discover_v7_direct_pilot_20261022 import (
    PROTECTED, now, sha, write, verify_originals)
from eventx.v7.source_request_scheduler_v02 import EndpointScheduler, retry_seconds as parse_retry_seconds
BASE = REPO_ROOT/"data/v7/direct_source_pilot_20261022_v03"
RELEASE = REPO_ROOT/"eventx/release/v7/direct_source_pilot_20261022_v03"

class ScopeError(ValueError):
    pass

def check_scope(value, markets, assets):
    if isinstance(value, list):
        for v in value:
            check_scope(v, markets, assets)
    elif isinstance(value, dict):
        for key in ('condition_id', 'conditionId', 'market'):
            v = value.get(key)
            if isinstance(v, str) and v.startswith('0x') and len(v) == 66 and v not in markets:
                raise ScopeError('Unrequested market')
        for key in ('asset', 'asset_id', 'assetId', 'token_id'):
            v = value.get(key)
            if v is not None and str(v).isdigit() and str(v) not in assets:
                raise ScopeError('Unrequested token')
        for v in value.values():
            if isinstance(v, (dict, list)):
                check_scope(v, markets, assets)

def valid_trade_window(rows, start, end, source):
    if not isinstance(rows, list):
        return False
    try:
        times = [int(r['timestamp']) if source == 'venue' else
                 datetime.fromisoformat(r['ts'].replace('Z', '+00:00')).timestamp() for r in rows]
        return all(start <= t <= end for t in times)
    except (ValueError, KeyError, TypeError):
        return False

class Capture:
    def __init__(self, smoke_seconds=None):
        self.cfg = json.loads((RELEASE/'spec.json').read_text())
        for rel, h in json.loads((RELEASE/'implementation_manifest.json').read_text())['locked_files'].items():
            if sha(REPO_ROOT/rel) != h:
                raise RuntimeError('Pilot implementation mismatch: '+rel)
        verify_originals()
        self.rows = [json.loads(l) for l in (RELEASE/'sample.jsonl').read_text().splitlines()]
        self.markets = {r['market_id'] for r in self.rows}
        self.assets = {r[k] for r in self.rows for k in ['yes_asset_id', 'no_asset_id']}
        assert not self.markets.intersection(json.loads(PROTECTED.read_text()))
        self.out = BASE/'smoke'/uuid.uuid4().hex if smoke_seconds else BASE/'live'
        self.out.mkdir(parents=True, exist_ok=True)
        (self.out/'objects').mkdir(exist_ok=True)
        self.lock = (self.out/'process.lock').open('a')
        fcntl.flock(self.lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        self.head = None
        self.seq = 0
        self.counts = Counter()
        self.stopping = False
        self.streams = {}
        self.cycle = 0
        self.run_start = now()
        self.stop_at = (now()+timedelta(seconds=smoke_seconds)) if smoke_seconds else datetime.fromisoformat(self.cfg['rehearsal_stop_at'])
        contract_path = self.out/'run_contract.json'
        if contract_path.exists():
            contract = json.loads(contract_path.read_text())
            if contract['spec_sha256'] != sha(RELEASE/'spec.json'):
                raise RuntimeError('Run contract spec mismatch')
            self.stop_at = datetime.fromisoformat(contract['stop_at'])
        else:
            if not smoke_seconds:
                self.stop_at = min(self.stop_at, now()+timedelta(seconds=self.cfg['live_duration_seconds']))
            write(contract_path, {'started_at': self.run_start.isoformat(), 'stop_at': self.stop_at.isoformat(),
                                 'spec_sha256': sha(RELEASE/'spec.json'), 'smoke_seconds': smoke_seconds})
        self.journal_path = self.out/'journal.jsonl'
        if self.journal_path.exists():
            with self.journal_path.open('rb') as f:
                for line in f:
                    if not line.endswith(b'\n'):
                        raise RuntimeError('Partial journal tail: preserve for explicit recovery')
                    r = json.loads(line)
                    h = r.pop('record_sha256')
                    if r['previous_sha256'] != self.head or hashlib.sha256(json.dumps(r, sort_keys=True, separators=(',', ':')).encode()).hexdigest() != h:
                        raise RuntimeError('Journal chain mismatch')
                    self.head = h
                    self.seq += 1
                    self.counts[r['kind']] += 1
        settings = ApiSettings.from_env()
        self.lumid = httpx.AsyncClient(base_url=settings.base_url, headers={'Authorization': 'Bearer '+settings.token}, timeout=25)
        self.public = httpx.AsyncClient(timeout=20)
        self.scheduler = EndpointScheduler(self.cfg['endpoint_intervals_seconds'])
        self.log({'kind': 'process_started', 'at': now().isoformat(), 'pid': os.getpid(),
                  'stop_at': self.stop_at.isoformat(), 'spec_sha256': sha(RELEASE/'spec.json'),
                  'scope': 'source_feasibility_only', 'resumed': self.seq > 0})
        self.save()

    def active(self):
        return not self.stopping and now() < self.stop_at and not (self.out/'STOP').exists()

    def log(self, value):
        r = dict(value, previous_sha256=self.head)
        r['record_sha256'] = hashlib.sha256(json.dumps(r, sort_keys=True, separators=(',', ':')).encode()).hexdigest()
        with self.journal_path.open('a') as f:
            f.write(json.dumps(r, sort_keys=True)+'\n')
            f.flush()
            os.fsync(f.fileno())
        self.head = r['record_sha256']
        self.seq += 1
        self.counts[r['kind']] += 1

    def store(self, body):
        h = hashlib.sha256(body).hexdigest()
        p = self.out/'objects'/h
        if not p.exists():
            with p.open('xb') as f:
                f.write(body)
                f.flush()
                os.fsync(f.fileno())
        return h

    def save(self):
        value = {'at': now().isoformat(), 'pid': os.getpid(), 'started_at': self.run_start.isoformat(),
                 'stop_at': self.stop_at.isoformat(), 'journal_records': self.seq,
                 'journal_head_sha256': self.head, 'counts': dict(self.counts), 'cycle': self.cycle,
                 'streams': self.streams, 'scope': 'source_feasibility_only', 'predictive_admissions': 0,
                 'models_scored': False, 'labels_computed': False, 'source_completeness_certified': False}
        tmp = self.out/'status.tmp'
        write(tmp, value)
        os.replace(tmp, self.out/'status.json')

    async def pause(self, seconds):
        end = time.monotonic()+seconds
        while self.active() and time.monotonic() < end:
            self.save()
            await asyncio.sleep(min(2, max(.01, end-time.monotonic())))

    async def request(self, row, kind, path, params, source='venue'):
        cid = row['market_id']
        assert cid in self.markets
        if source == 'lumid':
            bucket = 'lumid_rest'
        elif kind == 'trades':
            bucket = 'venue_trades'
        elif kind.startswith('book_'):
            bucket = 'venue_books'
        elif kind in ('market_metadata', 'resolution_state'):
            bucket = 'venue_metadata'
        else:
            raise ValueError('Undeclared endpoint')
        rec = {'kind': 'rest', 'endpoint_kind': kind, 'source': source, 'cycle': self.cycle,
               'market_id': cid, 'path': path, 'params': params, 'queued_at': now().isoformat(),
               'scheduler_bucket': bucket}
        value = None
        try:
            async with self.scheduler.slot(bucket):
                if not self.active():
                    rec['status'] = 'not_dispatched_run_ended'
                    return None
                rec['requested_at'] = now().isoformat()
                response = await (self.lumid if source=='lumid' else self.public).get(path, params=params)
                rec.update(http_status=response.status_code, response_received_at=now().isoformat())
                if response.status_code == 200:
                    value = response.json()
                    check_scope(value, {cid}, {row['yes_asset_id'], row['no_asset_id']})
                    if source == 'venue' and kind == 'trades':
                        if not isinstance(value, dict) or not isinstance(value.get('data'), list) or not isinstance(value.get('pagination'), dict) or 'next_cursor' not in value['pagination']:
                            raise ValueError('Invalid v2 trade envelope')
                        for trade in value['data']:
                            if trade.get('condition_id') != cid or str(trade.get('token_id')) not in {row['yes_asset_id'],row['no_asset_id']}:
                                raise ScopeError('Missing or invalid explicit v2 scope')
                            if not all(math.isfinite(float(trade[k])) for k in ('price','size','timestamp')) or not 0 <= float(trade['price']) <= 1 or float(trade['size']) < 0 or float(trade['timestamp']) < 0:
                                raise ValueError('Invalid v2 economic fields')
                        rec['rows'] = len(value['data'])
                    if source == 'venue' and kind == 'resolution_state':
                        if not isinstance(value, dict) or not isinstance(value.get('data'), list):
                            raise ValueError('Invalid resolution envelope')
                        if any(x.get('condition_id') != cid for x in value['data']):
                            raise ScopeError('Invalid resolution scope')
                    rec.update(payload_sha256=self.store(response.content), available_at=now().isoformat(), status='observed')
                    if isinstance(value, list):
                        rec['rows'] = len(value)
                else:
                    rec.update(status='failed_http', error_body_sha256=hashlib.sha256(response.content).hexdigest())
                    if response.status_code in (401, 403, 429):
                        delay = parse_retry_seconds(response.headers.get('Retry-After'))
                        if response.status_code in (401, 403):
                            delay = max(delay, 3600)
                            self.scheduler.defer_all(delay)
                            rec['backoff_scope'] = 'all_rest_auth_or_access_failure'
                        else:
                            self.scheduler.defer(bucket, delay)
                            rec['backoff_scope'] = bucket
                        rec['backoff_seconds'] = delay
        except asyncio.CancelledError:
            rec['status'] = 'cancelled_in_flight' if 'requested_at' in rec else 'cancelled_before_dispatch'
            raise
        except ScopeError:
            self.stopping = True
            (self.out/'STOP').touch()
            rec['status'] = 'scope_rejected_stop'
            raise
        except Exception as e:
            value = None
            rec.update(status='failed', error_type=type(e).__name__)
        finally:
            rec['finished_at'] = now().isoformat()
            self.log(rec)
            self.save()
        return value

    async def trades(self, row, source, start, end):
        cid = row['market_id']
        total = 0
        complete = False
        issue = 'page_cap'
        cursor = None if source == 'venue' else end
        seen_cursors, page_hashes = set(), set()
        previous_oldest = None
        pages = 0
        for page in range(self.cfg['max_pages']):
            if not self.active():
                issue = 'stopped'
                break
            if source == 'venue':
                path = 'https://data-api.polymarket.com/v2/trades'
                params = {'condition':cid, 'limit':1000, 'taker_only':'false'}
                if cursor is not None:
                    params['cursor'] = cursor
                value = await self.request(row, 'trades', path, params, source)
                if value is None:
                    issue = 'failed_request'
                    break
                raw_rows = value['data']
                times = [int(r['timestamp']) for r in raw_rows]
                if any(a < b for a,b in zip(times,times[1:])) or (times and previous_oldest is not None and times[0] > previous_oldest):
                    issue = 'cursor_timestamp_order_unverified'
                    break
                rows = [r for r in raw_rows if start <= int(r['timestamp']) <= end]
                next_cursor = value['pagination']['next_cursor']
                if next_cursor is not None and (not isinstance(next_cursor,str) or not next_cursor or next_cursor in seen_cursors):
                    issue = 'invalid_or_repeated_cursor'
                    break
                if times:
                    previous_oldest = times[-1]
            else:
                path = '/prediction-markets/trades/polymarket/'+cid
                params = {'from': datetime.fromtimestamp(start, timezone.utc).isoformat(),
                          'to': datetime.fromtimestamp(cursor, timezone.utc).isoformat(), 'limit':1000}
                rows = await self.request(row, 'trades', path, params, source)
                if rows is None:
                    issue = 'failed_request'
                    break
                if not valid_trade_window(rows, start, end, source):
                    issue = 'invalid_envelope_or_window'
                    break
                raw_rows = rows
            pages += 1
            fingerprint = hashlib.sha256(json.dumps(raw_rows,sort_keys=True).encode()).hexdigest()
            if fingerprint in page_hashes and raw_rows:
                issue = 'repeated_page'
                break
            page_hashes.add(fingerprint)
            total += len(rows)
            if source == 'venue':
                if next_cursor is None or (times and times[-1] < start):
                    complete, issue = True, None
                    break
                seen_cursors.add(next_cursor)
                cursor = next_cursor
            else:
                if len(rows)<1000:
                    complete, issue = True, None
                    break
                oldest=min(datetime.fromisoformat(x['ts'].replace('Z','+00:00')).timestamp() for x in rows)
                if oldest>=cursor:
                    issue='timestamp_boundary_stall'
                    break
                cursor=oldest
        self.log({'kind':'window_summary','at':now().isoformat(),'market_id':cid,'source':source,
                  'cycle':self.cycle,'start':start,'end':end,'pages_processed':pages,
                  'returned_rows_with_possible_page_overlap':total,'endpoint_window_returned':complete,
                  'issue':issue,'source_completeness_certified':False,
                  'pagination_note':'v2 descending cursor with local window filter; provider inclusive timestamp cursor; neither certifies exchange completeness'})

    async def rest(self):
        while self.active():
            begin = time.monotonic()
            self.cycle += 1
            end = int(now().timestamp())
            reconcile = self.cycle == 1 or self.cycle % 5 == 0
            start = end - (21600 if reconcile else 1800)
            jobs = []
            for row in self.rows:
                jobs.append(self.trades(row, 'venue', start, end))
                for key in ('yes_asset_id', 'no_asset_id'):
                    jobs.append(self.request(row, 'book_'+key, 'https://clob.polymarket.com/book', {'token_id': row[key]}))
                if reconcile:
                    jobs.append(self.trades(row, 'lumid', start, end))
                    jobs.append(self.request(row, 'quotes', '/prediction-markets/orderbook/polymarket/'+row['yes_asset_id'], {'limit': 1}, 'lumid'))
                    jobs.append(self.request(row, 'resolution_state', 'https://data-api.polymarket.com/v2/resolutions', {'condition':row['market_id']}))
                    jobs.append(self.request(row, 'market_metadata', 'https://gamma-api.polymarket.com/markets', {'condition_ids': row['market_id']}))
            await asyncio.gather(*jobs)
            self.log({'kind': 'cycle_finished', 'at': now().isoformat(), 'cycle': self.cycle,
                      'common_trade_window': [start, end], 'reconciliation': reconcile,
                      'duration_seconds': time.monotonic()-begin})
            self.save()
            await self.pause(max(0, self.cfg['poll_seconds']-(time.monotonic()-begin)))

    async def ws(self):
        while self.active():
            state = {'status': 'connecting', 'at': now().isoformat(), 'frames': 0}
            self.streams['venue_ws'] = state
            try:
                async with websockets.connect(self.cfg['websocket_url'], open_timeout=20, close_timeout=5,
                                              max_size=4*1024*1024, ping_interval=None) as ws:
                    sub = {'assets_ids': sorted(self.assets), 'type': 'market'}
                    await ws.send(json.dumps(sub))
                    self.log({'kind': 'ws_connected', 'at': now().isoformat(), 'subscription': sub})
                    state['status'] = 'connected'
                    last_ping = last_pong = time.monotonic()
                    while self.active():
                        if time.monotonic()-last_ping >= 10:
                            await ws.send('PING')
                            last_ping = time.monotonic()
                        if time.monotonic()-last_pong > 35:
                            raise TimeoutError('Application pong deadline')
                        try:
                            msg = await asyncio.wait_for(ws.recv(), timeout=2)
                        except asyncio.TimeoutError:
                            self.save()
                            continue
                        received = now().isoformat()
                        if msg == 'PONG':
                            last_pong = time.monotonic()
                            self.log({'kind': 'ws_pong', 'at': received})
                            continue
                        body = msg.encode() if isinstance(msg, str) else msg
                        value = json.loads(body)
                        check_scope(value, self.markets, self.assets)
                        h = self.store(body)
                        self.log({'kind': 'ws_frame', 'response_received_at': received,
                                  'available_at': now().isoformat(), 'payload_sha256': h})
                        state['frames'] += 1
                        state['last_data_at'] = received
                        self.save()
            except ScopeError:
                self.stopping = True
                (self.out/'STOP').touch()
                self.log({'kind': 'scope_rejected_stop', 'at': now().isoformat(), 'source': 'venue_ws'})
                raise
            except Exception as e:
                state.update(status='disconnected', error_type=type(e).__name__)
                self.log({'kind': 'ws_disconnected', 'at': now().isoformat(), 'error_type': type(e).__name__})
            if self.active():
                await self.pause(10)

    async def sse(self):
        params = {'condition_ids': ','.join(sorted(self.markets)), 'asset_ids': ','.join(sorted(self.assets))}
        while self.active():
            retry_seconds = 60
            state = {'status': 'connecting', 'at': now().isoformat(), 'frames': 0}
            self.streams['lumid_sse'] = state
            try:
                async with self.lumid.stream('GET', '/prediction-markets/stream', params=params,
                                             timeout=httpx.Timeout(25, read=None)) as response:
                    self.log({'kind': 'sse_connected', 'at': now().isoformat(), 'http_status': response.status_code, 'params': params})
                    if response.status_code in (401, 403, 429):
                        retry_seconds = parse_retry_seconds(response.headers.get('Retry-After'))
                        if response.status_code in (401, 403):
                            retry_seconds = max(retry_seconds, 3600)
                    response.raise_for_status()
                    state['status'] = 'connected'
                    iterator = response.aiter_lines().__aiter__()
                    lines = []
                    while self.active():
                        line = await asyncio.wait_for(iterator.__anext__(), timeout=min(65, max(.1, (self.stop_at-now()).total_seconds())))
                        if line:
                            lines.append(line)
                            continue
                        if lines:
                            received = now().isoformat()
                            data = '\n'.join(x[5:].strip() for x in lines if x.startswith('data:'))
                            if data:
                                check_scope(json.loads(data), self.markets, self.assets)
                            h = self.store(('\n'.join(lines)+'\n\n').encode())
                            self.log({'kind': 'sse_frame', 'response_received_at': received,
                                      'available_at': now().isoformat(), 'payload_sha256': h})
                            state['frames'] += 1
                            state['last_frame_at'] = received
                            lines = []
                            self.save()
            except ScopeError:
                self.stopping = True
                (self.out/'STOP').touch()
                self.log({'kind': 'scope_rejected_stop', 'at': now().isoformat(), 'source': 'lumid_sse'})
                raise
            except Exception as e:
                state.update(status='disconnected', error_type=type(e).__name__)
                self.log({'kind': 'sse_disconnected', 'at': now().isoformat(), 'error_type': type(e).__name__})
            if self.active():
                await self.pause(retry_seconds)

    async def run(self):
        tasks = [asyncio.create_task(f()) for f in (self.rest, self.ws, self.sse)]
        try:
            try:
                await asyncio.wait_for(asyncio.gather(*tasks), timeout=max(0., (self.stop_at-now()).total_seconds()))
            except asyncio.TimeoutError:
                self.log({'kind': 'run_deadline_reached', 'at': now().isoformat()})
        finally:
            self.stopping = True
            for task in tasks:
                task.cancel()
            await asyncio.gather(*tasks, return_exceptions=True)
            for name, state in self.streams.items():
                state.update(status='stopped', stopped_at=now().isoformat())
                self.log({'kind': 'stream_stopped', 'source': name, 'at': state['stopped_at'], 'reason': 'local_run_shutdown'})
            await self.public.aclose()
            await self.lumid.aclose()
            self.log({'kind': 'process_stopped', 'at': now().isoformat(), 'production_locks_verified': verify_originals()})
            self.save()
            from eventx.tasks.audit_v7_direct_pilot_20261022_v03 import audit
            audit(self.out)
        print(json.dumps({'directory': str(self.out.relative_to(REPO_ROOT)), 'journal_records': self.seq,
                          'predictive_admissions': 0}))

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--smoke-seconds', type=int)
    args = parser.parse_args()
    if args.smoke_seconds is not None and not 30 <= args.smoke_seconds <= 600:
        parser.error('Smoke duration must be 30..600 seconds')
    c = Capture(args.smoke_seconds)
    def stop(*_):
        c.stopping = True
    signal.signal(signal.SIGTERM, stop)
    signal.signal(signal.SIGINT, stop)
    asyncio.run(c.run())

if __name__ == '__main__':
    main()
