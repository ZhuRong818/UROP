"""Secondary: frozen V03 14-feature source-time booster (the live-runtime model) on the
new-identity June 8-14 capture. Registered in the protocol addendum before evaluation.

Lag history carries across dates exactly as in V03 development; June 7 is not fetched,
so June 8 00:30-01:00 lags are left-censored (same as May 7 in development).
"""
from collections import defaultdict
from datetime import datetime
import json

import joblib
import numpy as np
import pyarrow as pa
import pyarrow.parquet as pq

from eventx.tasks.discover_v7_direct_pilot_20261022 import REPO_ROOT, now, sha, write
from eventx.tasks.run_v7_new_identity_test_20261026 import BASE, REL, DATES, load_cohort, verify, clustered
from eventx.v7.clock_bounded_quote_inputs_20261026 import SourceTimeQuoteTape
from eventx.v7.source_time_study_20261026_v03 import predict, target_record, metrics, NAMES

MODEL = REPO_ROOT / 'data/v7/source_time_study_20261026_v03/development/frozen_models.joblib'


def main():
    verify(REL / 'protocol_addendum_manifest.json')
    verify(BASE / 'source/capture_manifest.json')
    selected = load_cohort()
    out = BASE / 'evaluation_v03'
    out.mkdir(exist_ok=False)
    write(out / 'consumption_receipt.json', {'at': now().isoformat(), 'status': 'started'})
    receipts = {r['hour']: r for r in json.loads((BASE / 'source/file_receipts.json').read_text())}
    by, ledger = defaultdict(list), []
    for date in DATES:
        good = True
        for h in range(24):
            hour = date + f'T{h:02d}'
            folder = BASE / 'source/hours' / hour
            if not receipts[hour]['complete']:
                good = False
                continue
            verify(folder / 'manifest.json')
            if (folder / 'quotes.parquet').exists():
                for r in pq.read_table(folder / 'quotes.parquet').to_pylist():
                    by[r['market'].decode()].append(r)
        start = int(datetime.fromisoformat(date + 'T00:00:00+00:00').timestamp())
        for m in selected:
            tape = SourceTimeQuoteTape(by[m['market_id']])
            for t in range(start + 1800, start + 84600, 300):
                ledger.append({'market_id': m['market_id'], 'date': date, 'all_hours_complete': good,
                               **target_record(tape, t)})
    pq.write_table(pa.Table.from_pylist(ledger), out / 'grid_ledger.parquet')
    issued = [r for r in ledger if r['current_valid']]
    bundle = joblib.load(MODEL)
    ps = predict(bundle, issued)
    known = np.array([r['target'] is not None for r in issued])
    y = np.array([r['target'] or 0 for r in issued])
    ids = np.array([r['market_id'] for r in issued])
    dates = np.array([r['date'] for r in issued])
    loss = {n: -(y * np.log(p) + (1 - y) * np.log1p(-p)) for n, p in ps.items()}
    rng = np.random.default_rng(20261026)
    per_contract = []
    for cid in sorted(set(ids[known])):
        mk = known & (ids == cid)
        per_contract.append({'market_id': cid, 'n': int(mk.sum()), **{n: metrics(y[mk], p[mk]) for n, p in ps.items()}})
    result = {'at': now().isoformat(), 'model_sha256': sha(MODEL), 'scheduled': len(ledger), 'issued': len(issued),
              'observed': int(known.sum()), 'contributing_contracts': len(set(ids[known])),
              'primary': {n: metrics(y[known], p[known]) for n, p in ps.items()},
              'nonoverlap': {n: metrics(y[known & (np.array([r['t'] for r in issued]) % 1800 == 0)],
                                        p[known & (np.array([r['t'] for r in issued]) % 1800 == 0)]) for n, p in ps.items()},
              'bootstrap_vs_hgb7': {n: {'by_contract': clustered((loss[n] - loss['hgb7'])[known], ids[known], rng),
                                        'by_date': clustered((loss[n] - loss['hgb7'])[known], dates[known], rng)}
                                    for n in NAMES if n != 'hgb7'},
              'contracts_favoring_hgb7_vs_logit': sum(c['hgb7']['log_loss'] < c['full_logit']['log_loss'] for c in per_contract),
              'per_contract': per_contract, 'model_refit': False}
    write(out / 'result.json', result)
    write(out / 'consumption_receipt.json', {'at': now().isoformat(), 'status': 'completed'})
    write(out / 'manifest.json', {'files': {str(p.relative_to(REPO_ROOT)): sha(p) for p in out.iterdir() if p.is_file() and p.name != 'manifest.json'}})
    print(json.dumps({k: result[k] for k in ['issued', 'observed', 'contributing_contracts', 'primary']}, indent=1))


if __name__ == '__main__':
    main()
