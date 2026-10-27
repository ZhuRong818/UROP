"""V02 live runtime: monotonic-anchored, SNTP-corrected clock; larger metadata-selected cohort.

Changes from V01 (which stays frozen and failed fresh readiness on host-clock discipline):
- Every collector record carries corrected_epoch = E.corrected + (monotonic - E.monotonic),
  where E is the latest valid SNTP estimate (eventx.v7.sntp_client_20261026) no older than
  360 s of monotonic time. Raw local wall times are retained unchanged.
- The clock gate checks estimate validity, age and residual uncertainty (<=50 ms) instead of
  requiring the raw host offset inside +/-100 ms. Wall-clock steps are logged for audit
  only; they cannot move corrected time, so they no longer reset transport warmup.
- Availability, transport warmup, metadata freshness and decision/emission clocks all use
  corrected time. Records without a valid estimate are unusable, never backfilled.
Model, features, target, freshness, spread and 250 ms source-lead rules are unchanged (V03).
"""
from collections import defaultdict
from datetime import datetime, timezone
import json
import time

from eventx.v7 import forecast_runtime_20261026 as v01
from eventx.v7.forecast_runtime_20261026 import (REPO_ROOT, OLD, MODEL, sha, read_chain, iso, stamp,
                                                  project_ws, grids, decision, evaluate_rows, subset)
from eventx.v7.quote_experiment_20261024 import QuoteTape
from eventx.v7.clock_bounded_quote_inputs_20261026 import SourceTimeQuoteTape, CONTRACT

REL = REPO_ROOT/'eventx/release/v7/forecast_runtime_20261026_v02'
BASE = REPO_ROOT/'data/v7/forecast_runtime_20261026_v02'
COHORT = REL/'live_cohort.jsonl'
PROTOCOL = REL/'protocol.json'
ESTIMATE_MAX_AGE = 360
WINDOW_DAYS = 3  # fixed before activation for the 1 Nov reporting deadline (V01: 7)
WARMUP = 1800
PONG_MAX_GAP = 35


def now():
    """Corrected time for this process, from the collector's latest valid clock state.

    Falls back to raw wall time when no valid state exists; every decision taken then
    is still gated by clock_gate() on the journal, so the fallback cannot admit input.
    """
    state = getattr(now, 'state_path', None)
    if state is not None:
        try:
            s = json.loads(state.read_text())
            age = time.monotonic()-s['monotonic_seconds']
            if s['valid'] and 0 <= age <= ESTIMATE_MAX_AGE:
                return s['corrected_epoch']+age
        except (OSError, ValueError, KeyError):
            pass
    return time.time()


def window(activated):
    """First full UTC date after activation; WINDOW_DAYS dates; grids 00:30..23:25; final endpoint +120 s."""
    day = int(activated//86400+1)*86400
    last = day+(WINDOW_DAYS-1)*86400+84300
    return {'first_grid': day+1800, 'last_grid': last, 'open_after': last+1920}


def load_cohort():
    return [json.loads(l) for l in COHORT.read_text().splitlines()]


def verify_release():
    v01.verify_manifest(REL/'implementation_manifest.json')


def clock_gate(records, t):
    """Latest VALID estimate at or before corrected t, no older than the collector's own
    correction horizon; its uncertainty bound (<=50 ms) is enforced by sntp_client.estimate.
    An invalid probe does not block while a fresh valid estimate still anchors correction."""
    est = None
    for r in records:
        if r.get('kind') == 'clock_estimate' and r['valid'] and r.get('corrected_epoch') is not None and r['corrected_epoch'] <= t:
            est = r
    if est is None:
        return False, ['clock_estimate_missing']
    if t-est['corrected_epoch'] > ESTIMATE_MAX_AGE:
        return False, ['clock_estimate_stale']
    return True, []


def transport_ready(records, t):
    """V01 rule on corrected time: connected, pong <=35 s, 30 min since connect/interruption."""
    connected, start, pong = False, None, None
    for r in records:
        at = r.get('corrected_epoch')
        if at is None or at > t:
            continue
        kind = r['kind']
        if kind == 'ws_connected':
            connected, start, pong = True, at, None
        elif kind in {'ws_disconnected', 'process_stopped', 'scope_rejected_stop'}:
            connected, start = False, None
        elif kind == 'operational_cycle_gap':
            start = at
        elif kind == 'ws_pong':
            if pong is not None and at-pong > PONG_MAX_GAP:
                start = at
            pong = at
    reasons = []
    if not connected:
        reasons.append('stream_disconnected')
    if pong is None or t-pong > PONG_MAX_GAP:
        reasons.append('pong_missing_or_old')
    if start is None or t-start < WARMUP:
        reasons.append('transport_history_warming')
    return not reasons, reasons


def corrected_view(r):
    """Record copy whose availability clocks are corrected; None if uncorrectable."""
    c = r.get('corrected_epoch')
    if c is None:
        return None
    out = dict(r, available_at=iso(c))
    if r['kind'] == 'ws_frame':
        lag = max(0., stamp(r['available_at'])-stamp(r['response_received_at']))
        out['response_received_at'] = iso(c-lag)
    return out


class Inputs(v01.Inputs):
    def __init__(self, root, samples, limit=None):
        from pathlib import Path
        self.root = Path(root)
        self.samples = samples
        self.records, self.head, self.offset = read_chain(self.root/'journal.jsonl', limit, partial=limit is None)
        self.status = QuoteTape(root, samples, {'book_max_age_seconds': 120, 'status_max_age_seconds': 360,
                                                'max_spread': .05, 'min_best_size': 0})
        self.by = defaultdict(list)
        self.errors = []
        self.uncorrectable = 0
        for r in self.records:
            self._ingest(r)
        self._tapes()

    def _ingest(self, r):
        if r['kind'] not in ('rest', 'ws_frame'):
            return
        v = corrected_view(r)
        if v is None:
            self.uncorrectable += 1
            return
        if r['kind'] == 'rest':
            self.status.ingest(v)
            return
        p = self.root/'objects'/r['payload_sha256']
        if sha(p) != r['payload_sha256']:
            raise RuntimeError('Payload hash mismatch')
        try:
            for row in project_ws(json.loads(p.read_text()), v['available_at'], v['response_received_at'], self.samples):
                self.by[row['market'].decode()].append(row)
        except (ValueError, TypeError, KeyError) as e:
            self.errors.append({'at': r['corrected_epoch'], 'reason': type(e).__name__})

    def _tapes(self):
        self.tapes = {s['market_id']: SourceTimeQuoteTape(self.by[s['market_id']]) for s in self.samples}

    def refresh(self):
        import hashlib
        with (self.root/'journal.jsonl').open('rb') as f:
            f.seek(self.offset)
            while True:
                line = f.readline()
                if not line or not line.endswith(b'\n'):
                    break
                r = json.loads(line)
                v = dict(r)
                h = v.pop('record_sha256')
                if v['previous_sha256'] != self.head or hashlib.sha256(json.dumps(v, sort_keys=True, separators=(',', ':')).encode()).hexdigest() != h:
                    raise RuntimeError('Incremental source chain mismatch')
                self.records.append(r)
                self.head = h
                self.offset = f.tell()
                self._ingest(r)
        self._tapes()

    def current(self, cid, t):
        f = self.tapes[cid].features(t)
        _, reasons = transport_ready(self.records, t)
        reasons += clock_gate(self.records, t)[1]
        if any(e['at'] <= t for e in self.errors):
            reasons.append('source_schema_error')
        if f is None:
            reasons.append('quote_missing_stale_invalid_or_conflicting')
        meta = self.status.at(cid, 'market_metadata', t)
        res = self.status.at(cid, 'resolution_state', t)
        if meta is None or res is None:
            reasons.append('metadata_resolution_invalid_or_stale')
        if meta and (meta['scheduled_end'] is None or meta['scheduled_end'] <= t+1800):
            reasons.append('expiry_not_beyond_horizon')
        return (f if not reasons else None), reasons

    def endpoint(self, cid, t):
        end = t+1800
        quote = self.tapes[cid].at(end)
        _, reasons = transport_ready(self.records, end)
        reasons += clock_gate(self.records, end)[1]
        if quote is None:
            reasons.append('endpoint_quote_invalid')
        if any(e['at'] <= end for e in self.errors):
            reasons.append('source_schema_error')
        for kind in ['market_metadata', 'resolution_state']:
            if not self.status.covers(cid, kind, t, end):
                reasons.append('forward_'+kind+'_coverage_failed')
        meta = [self.status.at(cid, 'market_metadata', t)]+[r for r in self.status.series[(cid, 'market_metadata')] if t < r['at'] <= end]
        if any(r is None or r.get('scheduled_end') is None or r['scheduled_end'] <= end for r in meta):
            reasons.append('forward_expiry_failed')
        return (quote['midpoint'] if quote and not reasons else None), reasons


# Pre-activation changes after readiness (window + bounded/incremental inputs + single-pass evaluator).
# The collector and every input/gate rule are unchanged; bounded inputs are verified equivalent.
WINDOW_ONLY = {'eventx/v7/forecast_runtime_20261026_v02.py', 'eventx/tasks/run_v7_forecast_runtime_20261026_v02.py',
               'eventx/tasks/evaluate_v7_forecast_runtime_20261026_v02.py', 'eventx/tasks/check_v7_forecast_runtime_20261026_v02.py'}
WINDOW_ADDED = {'eventx/release/v7/forecast_runtime_20261026_v02/protocol_addendum_window.json',
                'eventx/tasks/activate_v7_forecast_runtime_20261026_v02.py',
                'eventx/release/v7/forecast_runtime_20261026_v02/implementation_manifest_at_readiness.json',
                'eventx/release/v7/forecast_runtime_20261026_v02/forecast_runtime_20261026_v02_at_readiness.py.txt',
                'eventx/tasks/check_v7_bounded_inputs_20261026_v02.py',
                'eventx/release/v7/forecast_runtime_20261026_v02/bounded_equivalence_qa.json'}


def verify_readiness_binding():
    """Readiness ran before the pre-activation window change; bind it through the exact
    reconstructed manifest and allow only the documented window/tooling differences."""
    key = 'eventx/release/v7/forecast_runtime_20261026_v02/implementation_manifest.json'
    cap = json.loads((BASE/'readiness/capture_manifest.json').read_text())['files']
    for name, h in cap.items():
        if name != key and sha(REPO_ROOT/name) != h:
            raise RuntimeError('Readiness file mismatch: '+name)
    if cap[key] == sha(REL/'implementation_manifest.json'):
        return  # readiness ran on exactly the current frozen implementation
    then = REL/'implementation_manifest_at_readiness.json'
    if sha(then) != cap[key]:
        raise RuntimeError('Readiness implementation binding failed')
    old = json.loads(then.read_text())['files']
    new = json.loads((REL/'implementation_manifest.json').read_text())['files']
    changed = {k for k in old if new.get(k) != old[k]}
    if changed - WINDOW_ONLY or set(new)-set(old)-WINDOW_ADDED:
        raise RuntimeError('Undocumented change since readiness')
    import hashlib
    if hashlib.sha256((REL/'forecast_runtime_20261026_v02_at_readiness.py.txt').read_bytes()).hexdigest() != old['eventx/v7/forecast_runtime_20261026_v02.py']:
        raise RuntimeError('Readiness-time runtime source mismatch')


def require_activation(receipt, at):
    expected = window(receipt['activated_epoch'])
    if any(receipt.get(k) != v for k, v in expected.items()):
        raise RuntimeError('Invalid fixed seven-day window')
    if receipt['activated_epoch'] >= receipt['first_grid'] or at < receipt['activated_epoch']:
        raise RuntimeError('Activation clock invalid')
    if receipt.get('input_contract') != CONTRACT:
        raise RuntimeError('Activation input mismatch')
    for key, path in [('implementation_sha256', REL/'implementation_manifest.json'), ('model_sha256', MODEL),
                      ('cohort_sha256', COHORT), ('protocol_sha256', PROTOCOL)]:
        if receipt.get(key) != sha(path):
            raise RuntimeError('Activation hash mismatch: '+key)
    ready = BASE/'readiness_audit/report.json'
    v01.verify_manifest(BASE/'readiness_audit/manifest.json')
    verify_readiness_binding()
    if receipt.get('readiness_sha256') != sha(ready) or not json.loads(ready.read_text())['passed']:
        raise RuntimeError('Readiness missing or failed')
    if receipt['activated_epoch'] < stamp(json.loads(ready.read_text())['completed_at']):
        raise RuntimeError('Activation predates readiness')
    if receipt.get('source_path') != str((BASE/'prospective/source').relative_to(REPO_ROOT)):
        raise RuntimeError('Source path mismatch')
    return expected


GATE_KINDS = {'ws_connected', 'ws_disconnected', 'process_stopped', 'scope_rejected_stop',
              'operational_cycle_gap', 'ws_pong', 'clock_estimate'}
HORIZON = 3*3600  # retained history; every gate/feature/endpoint looks back <= 1920 s (+35 s pong gap)
SAFE_LOOKBACK = 2400


class BoundedInputs(Inputs):
    """Result-equivalent to Inputs for any t >= cutoff + SAFE_LOOKBACK, with bounded memory.

    Keeps only gate-relevant record summaries and quote rows within HORIZON of the newest
    corrected time; rebuilds tapes only for markets that received rows. Verified against the
    unbounded Inputs on the readiness journal (bounded_equivalence_qa.json).
    """
    def __init__(self, root, samples, limit=None, horizon=HORIZON):
        from pathlib import Path
        self.root, self.samples, self.horizon = Path(root), samples, horizon
        self.records, self.head, self.offset = [], None, 0
        self.status = QuoteTape(root, samples, {'book_max_age_seconds': 120, 'status_max_age_seconds': 360,
                                                'max_spread': .05, 'min_best_size': 0})
        self.by, self.errors, self.uncorrectable = defaultdict(list), [], 0
        self.tapes, self.latest, self.cutoff = {}, None, None
        self.changed = {s['market_id'] for s in samples}
        self.advance(limit)

    def _ingest(self, r):
        c = r.get('corrected_epoch')
        if c is not None:
            self.latest = c if self.latest is None else max(self.latest, c)
        if r['kind'] in GATE_KINDS:
            self.records.append({k: r[k] for k in ('kind', 'corrected_epoch', 'valid') if k in r})
        if r['kind'] == 'ws_frame' and r.get('corrected_epoch') is not None:
            before = {k: len(v) for k, v in self.by.items()}
            super()._ingest(r)
            self.changed |= {k for k, v in self.by.items() if len(v) != before.get(k, 0)}
        else:
            super()._ingest(r)

    def advance(self, limit=None):
        """Read journal records up to byte offset `limit` (or the current end)."""
        import hashlib
        with (self.root/'journal.jsonl').open('rb') as f:
            f.seek(self.offset)
            while limit is None or self.offset < limit:
                line = f.readline()
                if not line or not line.endswith(b'\n'):
                    break
                r = json.loads(line)
                v = dict(r)
                h = v.pop('record_sha256')
                if v['previous_sha256'] != self.head or hashlib.sha256(json.dumps(v, sort_keys=True, separators=(',', ':')).encode()).hexdigest() != h:
                    raise RuntimeError('Source chain mismatch')
                self.head, self.offset = h, f.tell()
                self._ingest(r)
                self.read_count = getattr(self, 'read_count', 0)+1
                if self.read_count % 20000 == 0:
                    self._prune()  # bound peak memory on long catch-up reads
        if limit is not None and self.offset != limit:
            raise RuntimeError('Invalid source prefix boundary')
        self.status.cache.clear()  # payloads already parsed into status items
        self.status.payload_hashes.clear()
        self._prune()
        self._tapes()

    refresh = advance

    def _prune(self):
        if self.latest is None or self.horizon is None:
            return
        cut = self.latest-self.horizon
        if self.cutoff is not None and cut <= self.cutoff:
            return
        self.cutoff = cut
        for cid, rows in self.by.items():
            i = 0
            while i < len(rows) and rows[i]['timestamp_received'].timestamp() < cut:
                i += 1
            if i:
                self.by[cid] = rows[i:]
                self.changed.add(cid)
        self.records = [r for r in self.records if r['kind'] not in ('ws_pong', 'clock_estimate')
                        or r['corrected_epoch'] is None or r['corrected_epoch'] >= cut]
        for key, series in self.status.series.items():
            times = self.status.times[key]
            from bisect import bisect_left
            j = max(0, bisect_left(times, cut)-1)  # keep the last item before the cutoff
            if j:
                self.status.series[key], self.status.times[key] = series[j:], times[j:]

    def _tapes(self):
        for s in self.samples:
            cid = s['market_id']
            if cid in self.changed or cid not in self.tapes:
                self.tapes[cid] = SourceTimeQuoteTape(self.by[cid])
        self.changed = set()

    def _guard(self, t):
        if self.cutoff is not None and t < self.cutoff+SAFE_LOOKBACK:
            raise RuntimeError('Decision time precedes retained history')

    def current(self, cid, t):
        self._guard(t)
        return super().current(cid, t)

    def endpoint(self, cid, t):
        self._guard(t+1800)
        return super().endpoint(cid, t)
