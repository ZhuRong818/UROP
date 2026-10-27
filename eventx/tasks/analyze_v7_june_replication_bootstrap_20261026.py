"""Clustered bootstrap intervals for the June replication log-loss differences.

Analysis-only; reads the frozen issued predictions after the single evaluation.
Resamples whole contracts (and, separately, whole dates) so shared-contract and
calendar dependence is not treated as i.i.d. rows.
"""
import json

import numpy as np
import pyarrow.parquet as pq

from eventx.tasks.discover_v7_direct_pilot_20261022 import now, write
from eventx.tasks.run_v7_june_replication_20261026 import BASE, MODELS, verify

B = 5000
SEED = 20261026


def losses(y, p):
    return -(y * np.log(p) + (1 - y) * np.log1p(-p))


def clustered(diff, clusters, rng):
    keys = np.unique(clusters)
    idx = {k: np.flatnonzero(clusters == k) for k in keys}
    sums = np.array([diff[idx[k]].sum() for k in keys])
    counts = np.array([len(idx[k]) for k in keys])
    draws = rng.integers(0, len(keys), size=(B, len(keys)))
    stats = sums[draws].sum(1) / counts[draws].sum(1)
    return {'clusters': int(len(keys)), 'mean': float(diff.mean()),
            'ci95': [float(np.quantile(stats, .025)), float(np.quantile(stats, .975))],
            'share_positive': float((stats > 0).mean())}


def main():
    verify(BASE / 'evaluation/manifest.json')
    rows = pq.read_table(BASE / 'evaluation/issued_predictions.parquet').to_pylist()
    rows = [r for r in rows if r['endpoint_eligible']]
    rng = np.random.default_rng(SEED)
    out = {'at': now().isoformat(), 'replicates': B, 'seed': SEED,
           'statistic': 'mean baseline-minus-row_hgb7 log loss (positive favors row_hgb7)', 'cohorts': {}}
    for cohort in ['development50', 'training_excluded10', 'all']:
        rr = [r for r in rows if cohort == 'all' or r['cohort'] == cohort]
        if not rr:
            continue
        y = np.array([r['target'] for r in rr], dtype=float)
        sel = losses(y, np.array([r['row_hgb7'] for r in rr]))
        res = {'n': len(rr), 'positives': int(y.sum())}
        for name in MODELS:
            if name == 'row_hgb7':
                continue
            diff = losses(y, np.array([r[name] for r in rr])) - sel
            res[name] = {'by_contract': clustered(diff, np.array([r['market_id'] for r in rr]), rng),
                         'by_date': clustered(diff, np.array([r['date'] for r in rr]), rng)}
        out['cohorts'][cohort] = res
    write(BASE / 'bootstrap.json', out)
    print(json.dumps(out, indent=1))


if __name__ == '__main__':
    main()
