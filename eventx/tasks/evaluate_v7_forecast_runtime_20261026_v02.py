"""V02 once-only evaluator. Same audit -> consumption -> scoring order and checks as V01,
with single forward passes over the source journal (BoundedInputs) instead of a full
prefix rebuild per grid. Adds a contract-clustered bootstrap for the primary contrast.
"""
import json

import joblib
import numpy as np

from eventx.tasks.evaluate_v7_frozen_classifier_20261026 import validate_emissions
from eventx.v7 import forecast_runtime_20261026_v02 as rt
from eventx.v7.forecast_runtime_20261026 import read_chain, write_new


def passes(source, samples, items):
    """Yield (item, inputs) advancing one BoundedInputs through items sorted by source_bytes."""
    inp = None
    for r in sorted(items, key=lambda r: r['source_bytes']):
        if inp is None:
            inp = rt.BoundedInputs(source, samples, limit=r['source_bytes'])
        elif r['source_bytes'] > inp.offset:
            inp.advance(r['source_bytes'])
        if inp.head != r['source_head'] or inp.offset != r['source_bytes']:
            raise RuntimeError('Source prefix binding failed')
        yield r, inp


def clustered(rows, base, b=5000, seed=20261026):
    y = np.array([r['target'] for r in rows], dtype=float)
    def loss(n):
        p = np.array([r['predictions'][n] for r in rows])
        return -(y*np.log(p)+(1-y)*np.log1p(-p))
    diff = loss(base)-loss('hgb7')
    ids = np.array([r['market_id'] for r in rows])
    keys = np.unique(ids)
    sums = np.array([diff[ids == k].sum() for k in keys])
    counts = np.array([(ids == k).sum() for k in keys])
    draws = np.random.default_rng(seed).integers(0, len(keys), size=(b, len(keys)))
    stats = sums[draws].sum(1)/counts[draws].sum(1)
    return {'clusters': int(len(keys)), 'mean_gain_nats': float(diff.mean()),
            'ci95': [float(np.quantile(stats, .025)), float(np.quantile(stats, .975))]}


def main():
    rt.verify_release()
    activation = rt.BASE/'activation_receipt.json'
    receipt = json.loads(activation.read_text())
    rt.require_activation(receipt, rt.now())
    if rt.now() <= receipt['open_after']+30:
        raise RuntimeError('Window still sealed')
    out = rt.BASE/'evaluation'
    if out.exists():
        raise RuntimeError('Evaluation already attempted; preserve receipt and do not rerun')
    source = rt.REPO_ROOT/receipt['source_path']
    emitter = rt.BASE/'prospective/emitter'
    rt.v01.verify_manifest(source/'capture_manifest.json')
    rc = json.loads((emitter/'run_contract.json').read_text())
    if rc != {'activation_sha256': rt.sha(activation), 'implementation_sha256': rt.sha(rt.REL/'implementation_manifest.json')}:
        raise RuntimeError('Emitter binding mismatch')
    samples = rt.load_cohort()
    records, _, _ = read_chain(emitter/'journal.jsonl')
    if not records or records[-1]['kind'] != 'process_stopped':
        raise RuntimeError('Emitter not stopped')
    keys, dec, commits, ends = validate_emissions(records, rt.grids(receipt['first_grid'], receipt['last_grid']),
                                                  [s['market_id'] for s in samples])
    bundle = joblib.load(rt.MODEL)
    replayed = 0
    for d, inp in passes(source, samples, list(dec.values())):
        expected = rt.decision(inp, bundle, d['market_id'], d['t'], d['recorded_at'])
        for k in ['status', 'features', 'predictions', 'reasons', 'target_at']:
            if d[k] != expected[k]:
                raise RuntimeError('Decision replay failed: '+k)
        replayed += 1
    for r in ends.values():
        if r['adjudication_timely'] != (r['t']+1920 <= r['recorded_at'] <= r['t']+1950):
            raise RuntimeError('Invalid endpoint timing receipt')
    out.mkdir()
    evidence = {'activation_sha256': rt.sha(activation), 'source_capture_sha256': rt.sha(source/'capture_manifest.json'),
                'emitter_journal_sha256': rt.sha(emitter/'journal.jsonl'), 'model_sha256': rt.sha(rt.MODEL),
                'implementation_sha256': rt.sha(rt.REL/'implementation_manifest.json')}
    write_new(out/'preopening_audit.json', {'at': rt.now(), 'passed': True, 'decision_replays': replayed,
                                            'scheduled_keys': len(keys), 'missing_decisions': len(keys-set(dec)), **evidence})
    write_new(out/'consumption_receipt.json', {'at': rt.now(), 'once_only': True, 'scope': 'This V02 three-day runtime only', **evidence})
    # Receipt exists before constructing or reading any target/score.
    try:
        endpoint = {}
        timely_ends = [e for e in ends.values() if e['adjudication_timely']]
        for e, inp in passes(source, samples, timely_ends):
            endpoint[(e['market_id'], e['t'])] = inp.endpoint(e['market_id'], e['t'])
        rows, coverage = [], []
        for cid, t in sorted(keys, key=lambda k: (k[1], k[0])):
            d, c = dec.get((cid, t)), commits.get((cid, t))
            issued = bool(d and c and c['timely'])
            coverage.append({'market_id': cid, 't': t, 'timely': issued, 'status': d['status'] if d else 'missing_decision'})
            if not issued:
                continue
            value, why = endpoint.get((cid, t), (None, ['missing_or_late_endpoint_receipt']))
            target = int(abs(value-d['features'][0]) > 1e-12) if value is not None else None
            rows.append({'market_id': cid, 't': t, 'target': target, 'endpoint_midpoint': value, 'endpoint_reasons': why,
                         'predictions': d['predictions']})
        report = rt.evaluate_rows(rows)
        known = [r for r in rows if r['target'] is not None]
        report['bootstrap_contract_clustered'] = {n: clustered(known, n) for n in ['full_logit', 'global_rate', 'market_rate']} if known else None
        report.update(at=rt.iso(rt.now()), scheduled=len(keys), timely=len(rows), abstained_or_uncommitted=len(keys)-len(rows),
                      prospective_evaluation=True)
        write_new(out/'endpoint_ledger.json', rows)
        write_new(out/'coverage.json', coverage)
        write_new(out/'report.json', report)
    except Exception as e:
        write_new(out/'failure.json', {'at': rt.now(), 'type': type(e).__name__, 'consumed': True})
        raise
    finally:
        write_new(out/'manifest.json', {'files': {str(p.relative_to(rt.REPO_ROOT)): rt.sha(p) for p in out.iterdir() if p.is_file()}})
    print(json.dumps({k: v for k, v in report.items() if k not in ('by_market', 'by_date', 'calibration')}, indent=1, default=str))


if __name__ == '__main__':
    main()
