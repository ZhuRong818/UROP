"""Bound the V3.1 news increment: market-clustered bootstrap of B1-vs-B0 on frozen development OOF predictions.

Post hoc and descriptive (guardrail D12). Reads only the already-opened, hash-checked development
out-of-fold predictions; the consumed historical holdout is not read and nothing is refit. Combined with the
label-blind design sensitivity frozen before labels (data/v3_1_historical/primary/power/report.json) this turns
"no gain found" into an upper bound on the gain that the data allow.
"""
import hashlib
import json

import numpy as np

from eventx.tasks.discover_v7_direct_pilot_20261022 import REPO_ROOT, now, write

DEV = REPO_ROOT / 'data/v3_1_historical/primary/development'
POWER = REPO_ROOT / 'data/v3_1_historical/primary/power/report.json'
OUT = REPO_ROOT / 'data/v3_1_historical/news_bound_20261027'
SAMPLES, SEED = 2000, 20261027


def sha256(path):
    digest = hashlib.sha256()
    with path.open('rb') as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b''):
            digest.update(chunk)
    return digest.hexdigest()


def load():
    selection = json.loads((DEV / 'selection_result.json').read_text())
    art = selection['oof_artifact']
    path = REPO_ROOT / art['path']
    if sha256(path) != art['sha256']:
        raise SystemExit('OOF artifact hash mismatch')
    dtype = np.dtype([(name, kind) for name, kind in art['dtype']])
    return selection, np.fromfile(path, dtype=dtype)


def weighted_ap(order, y, w):
    """Step-wise average precision with row weights (ties broken by the fixed sort order)."""
    yw, ww = (y * w)[order], w[order]
    tp, seen = np.cumsum(yw), np.cumsum(ww)
    return float(np.sum(yw * tp / np.maximum(seen, 1e-12)) / max(tp[-1], 1e-12))


def metrics(y, p0, p1, w, orders):
    total = w.sum()
    brier = [float(np.sum(w * (p - y) ** 2) / total) for p in (p0, p1)]
    ll = [float(-np.sum(w * (y * np.log(p) + (1 - y) * np.log1p(-p))) / total) for p in (np.clip(p0, 1e-7, 1 - 1e-7),
                                                                                       np.clip(p1, 1e-7, 1 - 1e-7))]
    ap = [weighted_ap(o, y, w) for o in orders]
    return {'delta_ap': ap[1] - ap[0], 'brier_improvement': brier[0] - brier[1], 'logloss_improvement': ll[0] - ll[1],
            'b0_brier': brier[0], 'b0_logloss': ll[0], 'b0_ap': ap[0]}


def summary(values):
    v = np.asarray(values)
    return {'mean': float(v.mean()), 'ci95': [float(np.quantile(v, 0.025)), float(np.quantile(v, 0.975))],
            'one_sided_95_upper': float(np.quantile(v, 0.95)), 'probability_positive': float((v > 0).mean())}


def main():
    selection, oof = load()
    y = oof['label'].astype(np.float64)
    p0, p1 = oof['b0'].astype(np.float64), oof['b1'].astype(np.float64)
    orders = [np.argsort(-p0, kind='stable'), np.argsort(-p1, kind='stable')]
    markets, inverse = np.unique(oof['market'], return_inverse=True)
    point = metrics(y, p0, p1, np.ones_like(y), orders)
    rng = np.random.default_rng(SEED)
    draws = {k: [] for k in ('delta_ap', 'brier_improvement', 'logloss_improvement')}
    for _ in range(SAMPLES):
        counts = rng.multinomial(len(markets), np.full(len(markets), 1 / len(markets))).astype(np.float64)
        m = metrics(y, p0, p1, counts[inverse], orders)
        for k in draws:
            draws[k].append(m[k])
    base_rate = float(y.mean())
    climatology_brier = base_rate * (1 - base_rate)
    b0_skill = climatology_brier - point['b0_brier']
    boot = {k: summary(v) for k, v in draws.items()}
    power = json.loads(POWER.read_text())
    excluded = [s['name'] for s in power['results']
                if s['brier_improvement'] > boot['brier_improvement']['one_sided_95_upper']
                and s['delta_ap'] > boot['delta_ap']['one_sided_95_upper']]
    result = {
        'at': now().isoformat(), 'descriptive_post_hoc': True, 'holdout_read': False, 'refit': False,
        'source': {'oof': selection['oof_artifact'], 'power_report_sha256': sha256(POWER)},
        'rows': int(len(y)), 'market_clusters': int(len(markets)), 'samples': SAMPLES, 'seed': SEED,
        'method': 'market-cluster bootstrap (multinomial market weights) on frozen 5-fold OOF predictions',
        'point': point, 'stored_point_check': selection['aggregate_oof']['incremental_b1_over_b0'],
        'bootstrap': boot,
        'scale': {'base_rate': base_rate, 'climatology_brier': climatology_brier, 'b0_brier_skill_over_climatology': b0_skill,
                  'brier_upper_bound_as_share_of_b0_skill': boot['brier_improvement']['one_sided_95_upper'] / b0_skill,
                  'brier_upper_bound_relative_to_b0_brier': boot['brier_improvement']['one_sided_95_upper'] / point['b0_brier']},
        'frozen_design_sensitivity': power['results'],
        'preregistered_scenarios_excluded_by_both_upper_bounds': excluded,
    }
    OUT.mkdir(parents=True, exist_ok=True)
    write(OUT / 'result.json', result)
    print(json.dumps({'point': point, 'bootstrap': boot, 'scale': result['scale'], 'excluded': excluded}, indent=1))


if __name__ == '__main__':
    main()
