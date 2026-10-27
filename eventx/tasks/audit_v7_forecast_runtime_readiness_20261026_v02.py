"""V02 readiness audit: no model scoring, no labels. Gate frozen in REL/protocol.json."""
import json
import math

from eventx.v7 import forecast_runtime_20261026_v02 as rt
from eventx.v7.sntp_client_20261026 import validate, estimate

MIN_READY, MIN_MARKETS = 10, 3


def main():
    rt.verify_release()
    src = rt.BASE/'readiness'
    rt.v01.verify_manifest(src/'capture_manifest.json')
    out = rt.BASE/'readiness_audit'
    if out.exists():
        raise RuntimeError('Preserve prior readiness audit')
    samples = rt.load_cohort()
    contract = json.loads((src/'run_contract.json').read_text())
    if contract['implementation_sha256'] != rt.sha(rt.REL/'implementation_manifest.json'):
        raise RuntimeError('Collector freeze mismatch')
    inp = rt.Inputs(src, samples)
    recs = inp.records
    # 1. Clock evidence re-derives from raw packets and local clocks only.
    clock_errors, anchor, previous = [], None, None
    for r in recs:
        if r['kind'] == 'clock_estimate':
            for m in r['measurements']:
                core = {k: m[k] for k in m if k not in ('valid', 'reason', 'stratum', 'offset_seconds', 'half_delay_seconds')}
                if {**core, **validate(core)} != m:
                    clock_errors.append('packet_revalidation_mismatch')
            off, half, reasons = estimate(r['measurements'])
            if (off, half, reasons) != (r['offset_seconds'], r['half_width_seconds'], r['reasons']) or r['valid'] != (off is not None):
                clock_errors.append('estimate_mismatch')
        c = r.get('corrected_epoch')
        if c is not None and previous is not None and c < previous:
            clock_errors.append('corrected_time_decreased')
        if c is not None:
            previous = c
    # Corrected stamps reproduce from anchors: after each valid estimate, extrapolate by monotonic.
    stamp_errors = 0
    for r in recs:
        if r['kind'] == 'clock_estimate' and r['valid']:
            anchor = (r['local_wall_epoch']+r['offset_seconds'], r['monotonic_seconds'])
        elif anchor and r.get('corrected_epoch') is not None:
            expected = anchor[0]+(r['monotonic_seconds']-anchor[1])
            # Anchor is taken a few ms after logging; clamp keeps order. Allow 50 ms.
            if abs(r['corrected_epoch']-expected) > .05:
                stamp_errors += 1
    stops = [r for r in recs if r['kind'] == 'process_stopped']
    normal = bool(stops and stops[-1].get('monotonic_deadline_reached') and any(r['kind'] == 'run_deadline_reached' for r in recs))
    first = min(r['corrected_epoch'] for r in recs if r.get('corrected_epoch') is not None)
    last = max(r['corrected_epoch'] for r in recs if r.get('corrected_epoch') is not None)
    ledger = []
    for s in samples:
        cid = s['market_id']
        for t in rt.grids(math.ceil(first/300)*300, int(last)):
            f, why = inp.current(cid, t)
            ledger.append({'market_id': cid, 't': t, 'at': rt.iso(t), 'ready': f is not None, 'reasons': why})
    # Independent causal check on a sample of decisions: rebuild from records with corrected<=t.
    causal_mismatch = 0
    for row in ledger[::max(1, len(ledger)//60)]:
        sub = rt.Inputs.__new__(rt.Inputs)
        sub.root, sub.samples = inp.root, samples
        sub.records = [r for r in recs if r.get('corrected_epoch') is not None and r['corrected_epoch'] <= row['t']]
        sub.status = rt.QuoteTape(src, samples, {'book_max_age_seconds': 120, 'status_max_age_seconds': 360, 'max_spread': .05, 'min_best_size': 0})
        sub.by, sub.errors, sub.uncorrectable = rt.defaultdict(list), [], 0
        for r in sub.records:
            sub._ingest(r)
        sub._tapes()
        if (sub.current(row['market_id'], row['t'])[0] is not None) != row['ready']:
            causal_mismatch += 1
    ready = sum(r['ready'] for r in ledger)
    markets = len({r['market_id'] for r in ledger if r['ready']})
    post = [r for r in ledger if 'transport_history_warming' not in r['reasons']]
    reasons = {}
    for r in post:
        for x in r['reasons']:
            reasons[x] = reasons.get(x, 0)+1
    estimates = [r for r in recs if r['kind'] == 'clock_estimate']
    passed = (normal and not inp.errors and not any(r['kind'] == 'scope_rejected_stop' for r in recs)
              and not clock_errors and stamp_errors == 0 and causal_mismatch == 0
              and ready >= MIN_READY and markets >= MIN_MARKETS)
    report = {'completed_at': rt.iso(rt.now()), 'normal_completion': normal, 'scheduled_decisions': len(ledger),
              'post_warmup_decisions': len(post), 'fully_ready': ready, 'contributing_markets': markets,
              'cohort_markets': len(samples), 'post_warmup_reason_counts': reasons,
              'clock_estimates': len(estimates), 'valid_clock_estimates': sum(r['valid'] for r in estimates),
              'offsets_seconds': [r['offset_seconds'] for r in estimates if r['valid']],
              'clock_steps': sum(r['kind'] == 'clock_step' for r in recs), 'clock_errors': clock_errors,
              'stamp_errors': stamp_errors, 'causal_replay_mismatches': causal_mismatch,
              'uncorrectable_records': inp.uncorrectable, 'schema_errors': inp.errors, 'passed': passed,
              'gate': f'>={MIN_READY} ready across >={MIN_MARKETS} markets plus integrity checks',
              'prospective_test_started': False, 'forecasts_issued': 0, 'labels_constructed': 0,
              'implementation_sha256': rt.sha(rt.REL/'implementation_manifest.json')}
    out.mkdir()
    rt.v01.write_new(out/'coverage_ledger.json', ledger)
    rt.v01.write_new(out/'report.json', report)
    rt.v01.write_new(out/'manifest.json', {'files': {str(p.relative_to(rt.REPO_ROOT)): rt.sha(p) for p in out.iterdir() if p.is_file()}})
    print(json.dumps({k: v for k, v in report.items() if k != 'offsets_seconds'}, indent=2))


if __name__ == '__main__':
    main()
