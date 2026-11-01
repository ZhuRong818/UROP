"""Develop a segment-aware history stack: the frozen stack inputs plus the two confirmed segment signals.

New research cycle requested by the user on 1 Nov 2026 after the segment confirmation test (13-21 Jul) confirmed that
the booster's gain over the online rate is larger after a 30-min quote move (H1) and at spreads above 0.03 (H2).
Development uses only already-opened blocks and their stored forecasts; no unopened period is read:
  may_13_19, jun_1_7 (development50), jun_8_14, jun_15_28, jun29_jul12, jul_13_21 (new contracts).
Inputs per row, all available at decision time:
  lh = logit(row_hgb7), lr = logit(online rate), h = log1p(matured known outcomes), la = logit(activity_logit),
  m  = midpoint moved in last 30 min (abs_delta30 > 0 and the lag available), w = spread > 0.03.
Candidates (fixed before any held-out score was seen):
  stack_lin  logistic on [lh, lr, h]                                   (the frozen stack's form; reference)
  seg_lin    logistic on [lh, lr, h, m, w, m*lh, m*lr, w*lh, w*lr]     (weights may move with the segment)
  seg_int    seg_lin plus [h*lh, h*lr]
  seg_hgb    HistGradientBoosting (depth 3, 200 iterations, rate 0.05, min leaf 200) on [lh, lr, h, la, m, spread,
             log1p(abs_delta30)]
Selection: leave-one-block-out over all six blocks; score = mean held-out log loss over the four new-contract blocks.
The best seg_* candidate wins; a tie within 0.0005 nats goes to the simpler one (seg_lin < seg_int < seg_hgb).
Go/no-go for a confirmatory test, fixed here: the winner's score must be at least 0.001 nats below stack_lin's.
The winner is refit on all six blocks and saved. Output: data/v7/segment_stack_20261101/development/
"""
import json
from datetime import datetime, timezone
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.linear_model import LogisticRegression

from eventx.tasks.analyze_v7_dependence_coverage_20261028 import logloss, one_way
from eventx.tasks.analyze_v7_segment_replication_20261101 import DISCOVERY, REPLICATION, block

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / 'data/v7/segment_stack_20261101/development'
JUL13 = ROOT / 'data/v7/segment_confirm_20261101/test/evaluation/issued_predictions.parquet'
NEW = ['jun_8_14', 'jun_15_28', 'jun29_jul12', 'jul_13_21']
ORDER = ['seg_lin', 'seg_int', 'seg_hgb']
SEED = 20261103


def logit(p):
    p = np.clip(p, 1e-6, 1 - 1e-6)
    return np.log(p / (1 - p))


def design(k, name):
    lh, lr, h, la = logit(k['row_hgb7'].to_numpy()), logit(k['adaptive_rate'].to_numpy()), \
        np.log1p(k['history'].to_numpy()), logit(k['activity_logit'].to_numpy())
    m = ((k['abs_delta30'] > 0) & (k['missing30'] == 0)).to_numpy(float)
    w = (k['spread'] > 0.03 + 1e-9).to_numpy(float)
    seg = np.c_[lh, lr, h, m, w, m * lh, m * lr, w * lh, w * lr]
    return {'stack_lin': np.c_[lh, lr, h], 'seg_lin': seg, 'seg_int': np.c_[seg, h * lh, h * lr],
            'seg_hgb': np.c_[lh, lr, h, la, m, k['spread'].to_numpy(), np.log1p(k['abs_delta30'].to_numpy())]}[name]


def model(name):
    if name == 'seg_hgb':
        return HistGradientBoostingClassifier(max_depth=3, max_iter=200, learning_rate=0.05, min_samples_leaf=200,
                                              random_state=SEED)
    return LogisticRegression(C=1.0, max_iter=2000)


def load_blocks():
    data = {n: block(n, base, cohort) for n, (base, cohort) in {**DISCOVERY, **REPLICATION}.items()}
    k = pd.read_parquet(JUL13)
    data['jul_13_21'] = k[k.endpoint_eligible].reset_index(drop=True)
    return data


def main():
    data = load_blocks()
    rng = np.random.default_rng(SEED)
    out = {'at': datetime.now(timezone.utc).isoformat(),
           'blocks': {b: {'rows': len(k), 'contracts': int(k.market_id.nunique())} for b, k in data.items()}, 'held_out': {}}
    for b, k in data.items():
        train = [data[x] for x in data if x != b]
        y = k['target'].to_numpy(float)
        res = {'rate': float(logloss(y, k['adaptive_rate'].to_numpy()).mean()),
               'row_hgb7': float(logloss(y, k['row_hgb7'].to_numpy()).mean())}
        ll = {}
        for name in ['stack_lin'] + ORDER:
            m = model(name).fit(np.vstack([design(t, name) for t in train]),
                                np.concatenate([t['target'].to_numpy(int) for t in train]))
            ll[name] = logloss(y, m.predict_proba(design(k, name))[:, 1])
            res[name] = float(ll[name].mean())
        for name in ORDER:
            res[name + '_vs_stack_lin_ci95'] = one_way(ll['stack_lin'] - ll[name], k['market_id'].to_numpy(), rng)['ci95']
        out['held_out'][b] = res
    score = {n: float(np.mean([out['held_out'][b][n] for b in NEW])) for n in ['stack_lin'] + ORDER + ['rate', 'row_hgb7']}
    best = min(ORDER, key=lambda n: score[n])
    chosen = next(n for n in ORDER if score[n] <= score[best] + 0.0005)
    go = bool(score[chosen] <= score['stack_lin'] - 0.001)
    final = model(chosen).fit(np.vstack([design(k, chosen) for k in data.values()]),
                              np.concatenate([k['target'].to_numpy(int) for k in data.values()]))
    out.update(selection_score_new_blocks=score, selected=chosen, gain_over_stack_lin=score['stack_lin'] - score[chosen],
               go_for_confirmatory_test=go)
    if chosen != 'seg_hgb':
        out['coefficients'] = {'intercept': float(final.intercept_[0]), 'coef': final.coef_[0].tolist()}
    OUT.mkdir(parents=True, exist_ok=True)
    joblib.dump({'name': chosen, 'model': final}, OUT / 'segment_stack.joblib')
    (OUT / 'result.json').write_text(json.dumps(out, indent=1))
    print(json.dumps(out, indent=1))


if __name__ == '__main__':
    main()
