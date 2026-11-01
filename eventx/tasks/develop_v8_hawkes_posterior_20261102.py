"""Development study (opened blocks only): more training data, self-exciting change history, market-wide activity and
a pooled-prior / contract-posterior online correction. Requested by the user on 2 Nov 2026 ("anything we can do to
improve performance ... feel free to ... propose new and novel algo"). Fixed and committed before any score.

All seven blocks are opened and consumed, so this is DEVELOPMENT evidence only: no result here is a confirmatory
test, and a winner would need its own frozen prospective test. No unopened period is read; features come from the
stored frozen-feature tables (no new archive read).

Blocks: may_13_19, jun_1_7 (development50), jun_8_14, jun_15_28, jun29_jul12, jul_13_21, jul22_aug8 (new contracts).
Evaluation: leave-one-block-out (LOBO); score = mean held-out log loss over the five new-contract blocks. The
jul22_aug8 fold is also strictly forward (trained only on earlier blocks).

Derived causal inputs (from each contract's stored issued rows, i.e. every grid with a valid current quote; endpoint
availability is never used):
  chg5      midpoint changed over the last 5 min (delta5 != 0 and missing5 == 0) at this grid
  hx        log1p(minutes since the last grid with chg5, capped at 1,440; 1,440 if none);
            exponentially weighted counts of chg5 with half-lives 30 min, 2 h, 12 h (current grid included);
            count of chg5 in the previous 24 h
  mkt       at the same grid, share of the OTHER contracts of the block with a 30-min move (abs_delta30 > 0,
            missing30 == 0), and log1p(number of contracts quoting)
Candidates (all HistGradientBoosting: 31 leaves, rate 0.05, 300 iterations, min leaf 200, L2 1.0, no early stopping,
seed 20261106, unless stated):
  seg_ref     the frozen seg_hgb design (booster, rate, history, activity logit, move, spread, size of move), refit
              per fold with its own frozen settings: the reference
  e2e         18 frozen features + logit(online rate) + log1p(history)          (more data, no frozen booster)
  e2e_hx      e2e + hx
  e2e_hx_mkt  e2e_hx + mkt
  pp_cp       pooled prior, contract posterior: logit p = f(x) + b_c, with f = e2e_hx_mkt's held-out logit and b_c a
              per-contract random-walk offset updated online by a one-step Laplace (extended Kalman) update each time
              an outcome matures (t' <= t - 2,100 s, the online rate's lag). Prior b ~ N(0, 1); process noise 0.02
              per hour. No parameter is fitted or tuned.
Inference: held-out per-row gain vs seg_ref and vs the online rate, contract-clustered 95% CI (2,000 draws, seed
20261106). Output: data/v8/hawkes_posterior_20261102/result.json
"""
import json
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.ensemble import HistGradientBoostingClassifier

from eventx.tasks.analyze_v7_dependence_coverage_20261028 import logloss, one_way
from eventx.tasks.benchmark_v7_sota_baselines_20261101 import BLOCKS, FEATURES, LATER, OUT as SOTA, load_block, logit
from eventx.tasks.develop_v7_segment_stack_20261101 import design as seg_design, model as seg_model

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / 'data/v8/hawkes_posterior_20261102'
NEW = BLOCKS[2:]
SEED, LAG, P0, Q_PER_HOUR = 20261106, 2100, 1.0, 0.02
HX = ['log_since_change', 'ew_30m', 'ew_2h', 'ew_12h', 'changes_24h']
MKT = ['mkt_moved_share', 'mkt_log_quoting']


def feature_table(name):
    """All issued (current-valid) rows of a block with the 18 frozen features (read-only)."""
    from eventx.tasks.analyze_v7_segment_replication_20261101 import DISCOVERY, REPLICATION, OUT as SEGOUT
    if name in LATER:
        f = pd.read_parquet(SOTA / f'features_{name}.parquet')
    elif name == 'jun29_jul12':
        f = pd.read_parquet(SEGOUT / 'features_jul.parquet')
    else:
        base = {**DISCOVERY, **REPLICATION}[name][0]
        led = pd.read_parquet(base / 'evaluation/grid_ledger.parquet', columns=['market_id', 'decision_at', 'features'])
        led = led[led.features.notna()]
        f = pd.DataFrame({'market_id': led.market_id.values, 'decision_at': led.decision_at.values,
                          **{n: [x[i] for x in led.features] for i, n in enumerate(FEATURES)}})
    sec = (pd.to_datetime(f['decision_at'], utc=True) - pd.Timestamp(0, tz='UTC')) / pd.Timedelta(seconds=1)
    f['grid'] = np.round(sec.to_numpy() / 300).astype(np.int64)
    return f[['market_id', 'decision_at', 'grid'] + FEATURES]


def derived(f):
    f = f.sort_values(['market_id', 'grid']).reset_index(drop=True)
    chg = ((f['delta5'] != 0) & (f['missing5'] == 0)).to_numpy(float)
    moved = ((f['abs_delta30'] > 0) & (f['missing30'] == 0)).to_numpy(float)
    out = {c: np.empty(len(f)) for c in HX}
    for _, g in f.groupby('market_id', sort=False):
        ix, gr, c = g.index.to_numpy(), g['grid'].to_numpy(), chg[g.index.to_numpy()]
        last, ew, prev = -10 ** 9, np.zeros(3), gr[0]
        hl = np.array([6.0, 24.0, 144.0])  # half-lives in 5-min grids
        times = gr[c > 0]
        for j, (i, t) in enumerate(zip(ix, gr)):
            ew *= 0.5 ** ((t - prev) / hl)
            prev = t
            if c[j]:
                ew += 1
                last = t
            out['log_since_change'][i] = np.log1p(min(1440.0, 5.0 * (t - last)))
            out['ew_30m'][i], out['ew_2h'][i], out['ew_12h'][i] = ew
            out['changes_24h'][i] = np.searchsorted(times, t, 'right') - np.searchsorted(times, t - 288, 'right')
    for c in HX:
        f[c] = out[c]
    by = pd.DataFrame({'grid': f['grid'], 'm': moved}).groupby('grid')['m'].agg(['sum', 'count'])
    s, n = f['grid'].map(by['sum']).to_numpy(), f['grid'].map(by['count']).to_numpy()
    f['mkt_moved_share'] = np.where(n > 1, (s - moved) / np.maximum(n - 1, 1), 0.0)
    f['mkt_log_quoting'] = np.log1p(n)
    return f


def load(name):
    k = load_block(name)
    d = derived(feature_table(name))[['market_id', 'decision_at'] + HX + MKT]
    k = k.merge(d, on=['market_id', 'decision_at'], how='left', validate='one_to_one')
    assert k[HX + MKT].notna().all().all(), name
    return k


def x_of(k, name):
    base = np.c_[k[FEATURES].to_numpy(), logit(k['adaptive_rate'].to_numpy()), np.log1p(k['history'].to_numpy())]
    if name == 'e2e':
        return base
    if name == 'e2e_hx':
        return np.c_[base, k[HX].to_numpy()]
    return np.c_[base, k[HX + MKT].to_numpy()]


def hgb():
    return HistGradientBoostingClassifier(max_leaf_nodes=31, learning_rate=0.05, max_iter=300, min_samples_leaf=200,
                                          l2_regularization=1.0, early_stopping=False, random_state=SEED)


def posterior(k, z):
    """Pooled prior, contract posterior: online Laplace update of a random-walk contract offset on logit z."""
    out = np.empty(len(k))
    for _, g in k.groupby('market_id', sort=False):
        o = np.argsort(g['t'].to_numpy())
        ix, ts, y, zz = g.index.to_numpy()[o], g['t'].to_numpy()[o], g['target'].to_numpy(float)[o], z[g.index.to_numpy()[o]]
        b, P, last, j = 0.0, P0, ts[0], 0
        for i in range(len(ix)):
            while j < len(ix) and ts[j] <= ts[i] - LAG:  # outcomes matured by this decision, in order
                P += Q_PER_HOUR * max(0.0, ts[j] + LAG - last) / 3600
                last = ts[j] + LAG
                p = 1 / (1 + np.exp(-(zz[j] + b)))
                w = p * (1 - p)
                b += P * (y[j] - p) / (1 + P * w)
                P = P / (1 + P * w)
                j += 1
            out[ix[i]] = 1 / (1 + np.exp(-(zz[i] + b)))
    return np.clip(out, 1e-6, 1 - 1e-6)


def main():
    rng = np.random.default_rng(SEED)
    data = {b: load(b) for b in BLOCKS}
    res = {'at': datetime.now(timezone.utc).isoformat(), 'development_only': True,
           'blocks': {b: {'rows': len(k), 'contracts': int(k.market_id.nunique())} for b, k in data.items()}, 'held_out': {}}
    for b, k in data.items():
        tr = pd.concat([data[x] for x in data if x != b], ignore_index=True)
        ytr, y = tr['target'].to_numpy(int), k['target'].to_numpy(float)
        p = {'rate': k['adaptive_rate'].to_numpy(), 'row_hgb7': k['row_hgb7'].to_numpy()}
        p['seg_ref'] = seg_model('seg_hgb').fit(seg_design(tr, 'seg_hgb'), ytr).predict_proba(seg_design(k, 'seg_hgb'))[:, 1]
        for n in ['e2e', 'e2e_hx', 'e2e_hx_mkt']:
            p[n] = hgb().fit(x_of(tr, n), ytr).predict_proba(x_of(k, n))[:, 1]
        p['pp_cp'] = posterior(k, logit(p['e2e_hx_mkt']))
        ll = {n: logloss(y, np.clip(v, 1e-6, 1 - 1e-6)) for n, v in p.items()}
        ids = k['market_id'].to_numpy()
        res['held_out'][b] = {'log_loss': {n: float(v.mean()) for n, v in ll.items()},
                              'vs_seg_ref': {n: {'gain': float((ll['seg_ref'] - ll[n]).mean()), **one_way(ll['seg_ref'] - ll[n], ids, rng)}
                                             for n in ['e2e', 'e2e_hx', 'e2e_hx_mkt', 'pp_cp']},
                              'vs_rate': {n: float((ll['rate'] - ll[n]).mean()) for n in ll if n != 'rate'}}
        print(json.dumps({'block': b, **res['held_out'][b]['log_loss']}), flush=True)
    names = ['rate', 'row_hgb7', 'seg_ref', 'e2e', 'e2e_hx', 'e2e_hx_mkt', 'pp_cp']
    res['score_new_blocks'] = {n: float(np.mean([res['held_out'][b]['log_loss'][n] for b in NEW])) for n in names}
    res['blocks_beating_seg_ref'] = {n: int(sum(res['held_out'][b]['vs_seg_ref'][n]['gain'] > 0 for b in NEW))
                                     for n in ['e2e', 'e2e_hx', 'e2e_hx_mkt', 'pp_cp']}
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / 'result.json').write_text(json.dumps(res, indent=1))
    print(json.dumps({k: res[k] for k in ['score_new_blocks', 'blocks_beating_seg_ref']}, indent=1))


if __name__ == '__main__':
    main()
