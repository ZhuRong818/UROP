"""Synthetic V02 runtime checks: corrected clock, gates, SNTP validation. No live labels."""
import hashlib
import json
from pathlib import Path
import struct
import tempfile
import time
import unittest

from eventx.v7 import forecast_runtime_20261026_v02 as rt
from eventx.v7.forecast_runtime_20261026 import Journal, iso, OLDREL
from eventx.v7.sntp_client_20261026 import validate, estimate, NTP_EPOCH
from eventx.tasks.collect_v7_forecast_runtime_20261026_v02 import Capture

HOST_OFFSET = .3  # host wall clock 300 ms behind true time; V01 rejected anything beyond 100 ms


def ntp(x):
    x += NTP_EPOCH
    return struct.pack('!II', int(x), int((x % 1)*2**32))


def packet(t1, t4, offset, nonce=b'12345678', header=0x24, stratum=1):
    t2, t3 = t1+offset+.004, t1+offset+.005
    data = bytes([header, stratum])+bytes(22)+nonce+ntp(t2)+ntp(t3)
    return {'host': 'h', 'request_hex': (bytes([0x23])+bytes(39)+b'12345678').hex(), 'response_hex': data.hex(),
            't1': t1, 't4': t4, 'monotonic_elapsed': t4-t1}


class SntpChecks(unittest.TestCase):
    def test_valid_packet_offset(self):
        v = validate(packet(1000., 1000.01, .3))
        self.assertTrue(v['valid'])
        self.assertAlmostEqual(v['offset_seconds'], .3-.0005+.0045-.005+.0005, places=3)

    def test_zero_packet_rejected(self):
        r = packet(1000., 1000.01, .3)
        r['response_hex'] = bytes(48).hex()
        self.assertEqual(validate(r)['reason'], 'invalid_header_or_stratum')

    def test_originate_mismatch_rejected(self):
        self.assertEqual(validate(packet(1000., 1000.01, .3, nonce=b'87654321'))['reason'], 'originate_mismatch')

    def test_local_step_during_exchange_rejected(self):
        r = packet(1000., 1000.01, .3)
        r['monotonic_elapsed'] = .2
        self.assertEqual(validate(r)['reason'], 'local_step_during_exchange')

    def test_estimate_rules(self):
        good = lambda h, o, d: {'host': h, 'valid': True, 'offset_seconds': o, 'half_delay_seconds': d}
        off, half, why = estimate([good('a', .30, .01), good('b', .305, .02)])
        self.assertFalse(why)
        self.assertAlmostEqual(off, .30)
        self.assertEqual(estimate([good('a', .3, .01)])[2], ['insufficient_precise_independent_clocks'])
        self.assertEqual(estimate([good('a', .3, .01), good('b', .5, .01)])[2], ['clock_intervals_disagree'])
        self.assertEqual(estimate([good('a', .3, .05), good('b', .3, .01)])[0] is not None, True)
        self.assertEqual(estimate([good('a', 3., .01), good('b', 3., .01)])[2], ['host_offset_implausible'])


class RuntimeChecks(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.samples = [json.loads(l) for l in (OLDREL/'live_cohort.jsonl').read_text().splitlines()]
        cls.cid = cls.samples[0]['market_id']
        cls.t = 1793005200

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        (self.root/'objects').mkdir()
        self.j = Journal(self.root/'journal.jsonl')

    def tearDown(self):
        self.temp.cleanup()

    def add(self, kind, corrected, **v):
        # Raw local wall clock is HOST_OFFSET behind; corrected_epoch is true time.
        local = corrected-HOST_OFFSET
        return self.j.append({'kind': kind, 'at': iso(local), 'local_wall_epoch': local, 'monotonic_seconds': local,
                              'corrected_epoch': corrected, **v})

    def payload(self, p):
        b = json.dumps(p).encode()
        h = hashlib.sha256(b).hexdigest()
        (self.root/'objects'/h).write_bytes(b)
        return h

    def estimate_record(self, at, valid=True):
        self.add('clock_estimate', at, measurements=[], offset_seconds=HOST_OFFSET if valid else None,
                 half_width_seconds=.003 if valid else None, valid=valid, reasons=[] if valid else ['clock_intervals_disagree'])

    def quote(self, at, bid='.40', ask='.42', available=None):
        available = at+.01 if available is None else available
        p = {'event_type': 'price_change', 'market': self.cid, 'timestamp': str(int(at*1000)),
             'price_changes': [{'asset_id': self.samples[0]['yes_asset_id'], 'best_bid': bid, 'best_ask': ask}]}
        local = available-HOST_OFFSET
        return self.add('ws_frame', available, response_received_at=iso(local-.001), available_at=iso(local),
                        payload_sha256=self.payload(p))

    def metadata(self, at, ok=True):
        s = self.samples[0]
        p = [{'conditionId': self.cid, 'clobTokenIds': [s['yes_asset_id'], s['no_asset_id']], 'outcomes': ['Yes', 'No'],
              'description': s['rules'], 'acceptingOrders': ok, 'closed': False, 'active': True, 'endDate': iso(self.t+10000)}]
        self.add('rest', at, market_id=self.cid, endpoint_kind='market_metadata', source='venue', status='observed',
                 available_at=iso(at-HOST_OFFSET), payload_sha256=self.payload(p))
        p = {'data': [{'condition_id': self.cid, 'status': 'posed', 'resolved_at': None, 'was_disputed': False}]}
        self.add('rest', at, market_id=self.cid, endpoint_kind='resolution_state', source='venue', status='observed',
                 available_at=iso(at-HOST_OFFSET), payload_sha256=self.payload(p))

    def setup_valid(self, estimates=True):
        t = self.t
        self.add('ws_connected', t-1900)
        for x in range(t-1890, t+1801, 10):
            self.add('ws_pong', x)
        for x in range(t-300, t+1801, 60):
            if estimates:
                self.estimate_record(x)
            if x % 300 == t % 300:
                self.metadata(x)
        self.quote(t-1)
        self.quote(t+1799, '.41', '.43')
        return rt.Inputs(self.root, self.samples)

    def test_offset_host_is_ready(self):
        f, r = self.setup_valid().current(self.cid, self.t)
        self.assertFalse(r)
        self.assertAlmostEqual(f[0], .41)

    def test_endpoint(self):
        v, r = self.setup_valid().endpoint(self.cid, self.t)
        self.assertFalse(r)
        self.assertAlmostEqual(v, .42)

    def test_no_estimate_abstains(self):
        f, r = self.setup_valid(estimates=False).current(self.cid, self.t)
        self.assertIsNone(f)
        self.assertIn('clock_estimate_missing', r)

    def test_stale_estimate_abstains(self):
        self.estimate_record(self.t-1000)
        inp = self.setup_valid(estimates=False)
        self.assertIn('clock_estimate_stale', inp.current(self.cid, self.t)[1])

    def test_invalid_probe_does_not_block_fresh_valid(self):
        inp = self.setup_valid()
        self.estimate_record(self.t-1, valid=False)
        inp.refresh()
        self.assertIsNotNone(inp.current(self.cid, self.t)[0])

    def test_clock_step_does_not_reset_warmup(self):
        inp = self.setup_valid()
        self.add('clock_step', self.t-5, wall_minus_monotonic_change_seconds=-.11)
        inp.refresh()
        self.assertIsNotNone(inp.current(self.cid, self.t)[0])

    def test_rest_cycle_gap_resets_warmup(self):
        inp = self.setup_valid()
        self.add('operational_cycle_gap', self.t-5, seconds=200)
        inp.refresh()
        self.assertIn('transport_history_warming', inp.current(self.cid, self.t)[1])

    def test_uncorrected_connect_is_invisible(self):
        inp = self.setup_valid()
        recs = [r for r in inp.records if r['kind'] != 'ws_connected']
        self.assertIn('stream_disconnected', rt.transport_ready(recs, self.t)[1])

    def test_uncorrectable_record_ignored(self):
        inp = self.setup_valid()
        p = {'event_type': 'price_change', 'market': self.cid, 'timestamp': str(int((self.t-0.5)*1000)),
             'price_changes': [{'asset_id': self.samples[0]['yes_asset_id'], 'best_bid': '.60', 'best_ask': '.62'}]}
        self.j.append({'kind': 'ws_frame', 'at': iso(self.t-1), 'corrected_epoch': None, 'response_received_at': iso(self.t-1),
                       'available_at': iso(self.t-1), 'payload_sha256': self.payload(p)})
        inp.refresh()
        self.assertEqual(inp.uncorrectable, 1)
        self.assertAlmostEqual(inp.current(self.cid, self.t)[0][0], .41)

    def test_future_observation_unchanged(self):
        inp = self.setup_valid()
        before = inp.current(self.cid, self.t)
        self.quote(self.t+10, '.60', '.62')
        inp.refresh()
        self.assertEqual(inp.current(self.cid, self.t), before)

    def test_late_endpoint_quote_cannot_repair(self):
        inp = self.setup_valid()
        self.quote(self.t+1800, '.49', '.51', self.t+1801)
        inp.refresh()
        self.assertAlmostEqual(inp.endpoint(self.cid, self.t)[0], .42)

    def test_corrected_now(self):
        state = self.root/'clock_state.json'
        rt.now.state_path = state
        state.write_text(json.dumps({'valid': True, 'corrected_epoch': 5000., 'monotonic_seconds': time.monotonic()}))
        self.assertLess(abs(rt.now()-5000.), .5)
        state.write_text(json.dumps({'valid': True, 'corrected_epoch': 5000., 'monotonic_seconds': time.monotonic()-400}))
        self.assertGreater(rt.now(), 1e9)  # stale state falls back to raw wall time
        rt.now.state_path = None


class CollectorStampChecks(unittest.TestCase):
    def test_clock_logging_stays_on_event_loop(self):
        import inspect
        src = inspect.getsource(Capture.clocks)
        self.assertNotIn('to_thread(self.measure_clock', src)
        self.assertIn('to_thread(self.probe_all)', src)

    def test_stamp_monotone_and_extrapolated(self):
        c = Capture.__new__(Capture)
        c.anchor, c.last_corrected = None, None
        self.assertIsNone(c._stamp(10.))
        c.anchor = {'corrected_epoch': 1000., 'monotonic_seconds': 10.}
        self.assertAlmostEqual(c._stamp(12.), 1002.)
        c.anchor = {'corrected_epoch': 1001., 'monotonic_seconds': 12.5}  # new estimate 1.5 ms... behind
        self.assertGreaterEqual(c._stamp(12.6), 1002.)
        self.assertIsNone(c.corrected(12.5+rt.ESTIMATE_MAX_AGE+1))



class EvaluatorIntegration(RuntimeChecks):
    """Real V02 evaluator main() on a synthetic source + emitter journal in a sandbox BASE."""
    def test_end_to_end(self):
        import joblib
        from unittest import mock
        from eventx.tasks import evaluate_v7_forecast_runtime_20261026_v02 as ev
        self.setup_valid()
        src = self.root
        (src/'capture_manifest.json').write_text(json.dumps({'files': {}}))
        bundle = joblib.load(rt.MODEL)
        inp = rt.BoundedInputs(src, self.samples)
        base = self.root/'base'
        (base/'prospective/emitter').mkdir(parents=True)
        (base/'prospective/source').symlink_to(src, target_is_directory=True)
        receipt = {'first_grid': self.t, 'last_grid': self.t, 'open_after': self.t+1920, 'source_path': None}
        ej = Journal(base/'prospective/emitter/journal.jsonl')
        d = ej.append(rt.decision(inp, bundle, self.cid, self.t, self.t+1))
        self.assertEqual(d['status'], 'ready')
        ej.append({'kind': 'emission_commit', 'market_id': self.cid, 't': self.t, 'decision_sha256': d['record_sha256'],
                   'decision_durable_at': self.t+2, 'timely': True})
        ej.append({'kind': 'endpoint_receipt', 'market_id': self.cid, 't': self.t, 'recorded_at': self.t+1925,
                   'source_bytes': inp.offset, 'source_head': inp.head, 'adjudication_timely': True})
        ej.append({'kind': 'process_stopped', 'at': self.t+3000, 'early': False})
        with mock.patch.object(rt, 'BASE', base), mock.patch.object(rt, 'REPO_ROOT', self.root), \
             mock.patch.object(rt, 'verify_release', lambda: None), mock.patch.object(rt, 'require_activation', lambda r, a: None), \
             mock.patch.object(rt, 'now', lambda: self.t+5000), mock.patch.object(rt, 'load_cohort', lambda: self.samples[:1]), \
             mock.patch.object(rt.v01, 'verify_manifest', lambda p: None):
            receipt['source_path'] = 'base/prospective/source'
            (base/'activation_receipt.json').write_text(json.dumps(receipt))
            (base/'prospective/emitter/run_contract.json').write_text(json.dumps(
                {'activation_sha256': rt.sha(base/'activation_receipt.json'), 'implementation_sha256': rt.sha(rt.REL/'implementation_manifest.json')}))
            ev.main()
            report = json.loads((base/'evaluation/report.json').read_text())
            self.assertEqual((report['timely'], report['known']), (1, 1))
            with self.assertRaises(RuntimeError):
                ev.main()  # once-only


if __name__ == '__main__':
    unittest.main(verbosity=1)
