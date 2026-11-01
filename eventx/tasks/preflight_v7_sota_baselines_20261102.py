"""Label-free preflight for the once-only SOTA benchmark evaluation (review finding, 2 Nov 2026).

The sequence driver checks process exit, not outputs, and the v3 evaluator writes v1's result.json before the v3
models are merged. This check reads only keys and prediction columns (never targets) and exits non-zero unless every
expected output exists, covers exactly its rows, and holds finite probabilities in (0, 1).
"""
import json
import sys

import numpy as np
import pandas as pd

from eventx.tasks.benchmark_v7_sota_baselines_20261101 import BLOCKS, OUT

KEY = ['market_id', 'decision_at']


def check():
    problems, seen = [], {}
    for b in BLOCKS:
        keys = pd.read_parquet(OUT / f'tier_b/input_{b}.parquet', columns=KEY + ['t'])
        full, half = keys[KEY], keys.loc[keys['t'] % 1800 == 0, KEY]
        want = [(f'tier_a/{m}_{b}.parquet', m, full) for m in ['tabm', 'realmlp', 'tabicl', 'catboost']]
        want += [(f'tier_b/moirai_moe_{b}.parquet', 'moirai_moe', full)]
        want += [(f'tier_b/{m}_{b}.parquet', m, half) for m in ['sundial', 'time_moe']]
        if b == 'jul22_aug8':
            want += [(f'tier_c/{m}_{b}.parquet', m, full) for m in ['tabm', 'realmlp']]
        for path, col, ref in want:
            p = OUT / path
            if not p.exists():
                problems.append(f'missing {path}')
                continue
            f = pd.read_parquet(p, columns=KEY + [col])
            v = f[col].to_numpy(float)
            same = len(f) == len(ref) and f[KEY].merge(ref, on=KEY, how='inner').shape[0] == len(ref)
            ok = same and np.isfinite(v).all() and ((v > 0) & (v < 1)).all() and not f.duplicated(KEY).any()
            seen[path] = len(f)
            if not ok:
                problems.append(f'bad {path}: rows {len(f)} vs {len(ref)}')
    if (OUT / 'result.json').exists() or (OUT / 'result_v3.json').exists():
        problems.append('a result file already exists: evaluation must not be repeated')
    print(json.dumps({'files_checked': len(seen), 'problems': problems}, indent=1))
    return not problems


if __name__ == '__main__':
    sys.exit(0 if check() else 1)
