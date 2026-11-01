"""Descriptive log-loss table by market state on the consumed segment confirmation test (13-21 Jul 2026).

Reads only the stored issued predictions of run_v7_segment_confirm_test_20261101_v2 (evaluated once); refits nothing.
States are the two confirmed segments: active = midpoint moved in the last 30 min or spread > 0.03; quiet = neither.
Output: data/v7/segment_confirm_20261101/state_table.json
"""
import json
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
BASE = ROOT / 'data/v7/segment_confirm_20261101'
MODELS = ['adaptive_rate', 'row_hgb7', 'stack', 'activity_logit']


def main():
    k = pd.read_parquet(BASE / 'test/evaluation/issued_predictions.parquet')
    k = k[k.endpoint_eligible].reset_index(drop=True)
    y = k['target'].to_numpy(float)
    L = {n: -(y * np.log(np.clip(k[n].to_numpy(), 1e-6, 1 - 1e-6)) + (1 - y) * np.log1p(-np.clip(k[n].to_numpy(), 1e-6, 1 - 1e-6)))
         for n in MODELS}
    moved, wide = k['moved30'].to_numpy(bool), k['wide'].to_numpy(bool)
    states = {'moved': moved, 'wide': wide, 'active': moved | wide, 'quiet': ~(moved | wide), 'all': np.ones(len(k), bool)}
    out = {}
    for s, m in states.items():
        ll = {n: float(L[n][m].mean()) for n in MODELS}
        out[s] = {'rows': int(m.sum()), 'share': float(m.mean()), 'change_rate': float(y[m].mean()), 'log_loss': ll,
                  'reduction_vs_rate_pct': {n: 100 * (ll['adaptive_rate'] - ll[n]) / ll['adaptive_rate'] for n in ['row_hgb7', 'stack']},
                  'stack_reduction_vs_activity_logit_pct': 100 * (ll['activity_logit'] - ll['stack']) / ll['activity_logit']}
    (BASE / 'state_table.json').write_text(json.dumps(out, indent=1))
    print(json.dumps(out, indent=1))


if __name__ == '__main__':
    main()
