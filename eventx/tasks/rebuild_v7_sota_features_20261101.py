"""Read-only: re-derive the frozen 18 quote features of the issued rows of the two latest consumed tests.

Needed by the state-of-the-art baseline benchmark (benchmark_v7_sota_baselines_20261101), because those two evaluators
stored predictions but not features. Same frozen build_panel, same hash-verified captured source, same cohort; no
target is read or scored here and no model is fitted. Mirrors analyze_v7_segment_replication_20261101.rebuild_july_features.
Output: data/v7/sota_baselines_20261101/features_{jul_13_21,jul22_aug8}.parquet
"""
import json
import sys
from pathlib import Path

import pandas as pd

from eventx.tasks.research_v7_change_probability_20261025 import FEATURES
from eventx.v7.calibration_transport_20261025 import build_panel

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / 'data/v7/sota_baselines_20261101'
FI = {f: i for i, f in enumerate(FEATURES)}


def rebuild(name):
    if name == 'jul_13_21':
        from eventx.tasks.run_v7_segment_confirm_test_20261101_v2 import BASE, DATES, load_cohort
    else:
        from eventx.tasks.run_v7_segment_stack_test_20261101 import BASE, DATES, load_cohort
    sel, rows = load_cohort(), []
    for k in range(0, len(sel), 15):
        for r in build_panel(BASE / 'source', DATES, sel[k:k + 15]):
            if r['current_valid']:
                rows.append({'market_id': r['market_id'], 'decision_at': r['decision_at'],
                             'current_midpoint': r['current_midpoint'], **{f: r['features'][i] for f, i in FI.items()}})
    OUT.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(rows).to_parquet(OUT / f'features_{name}.parquet')
    print(json.dumps({'phase': 'features', 'block': name, 'rows': len(rows)}), flush=True)


if __name__ == '__main__':
    rebuild(sys.argv[1])
