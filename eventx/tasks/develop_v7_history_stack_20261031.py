"""Develop a history stack: the frozen booster's pooled forecast combined with the contract's own outcome history.

New research cycle authorized by the user on 31 Oct 2026. Development uses only the four already-consumed blocks
(May 13-19 and June 1-7 development50; June 8-14 and June 15-28 new contracts), from their stored predictions.
Nothing in the July test window is read. Inputs per row, all available at decision time:
  lh = logit(row_hgb7), the frozen booster (pooled across contracts);
  lr = logit(online contract rate): pseudocount 20 toward the stored global rate, outcomes matured >= 2,100 s;
  h  = log1p(number of the contract's matured known outcomes), history restarting at each block start;
  la = logit(activity_logit).
Candidates (fixed before any held-out score was seen):
  stack_lin  logistic on [lh, lr, h]
  stack_int  logistic on [lh, lr, h, h*lh, h*lr]   (lets the weight move from booster to rate as history grows)
  stack_hgb  HistGradientBoosting (depth 3, 200 iterations, rate 0.05, min leaf 200) on [lh, lr, h, la]
Selection: leave-one-block-out; the candidate with the lowest mean held-out log loss over the two new-contract
blocks wins; a tie within 0.0005 nats goes to the simpler model (lin < int < hgb). The winner is refit on all four
blocks and saved. Output: data/v7/history_stack_20261031/development/
"""
import json
from datetime import datetime, timezone
from pathlib import Path

import joblib
import numpy as np
from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.linear_model import LogisticRegression

from eventx.tasks.analyze_v7_dependence_coverage_20261028 import logloss, one_way
from eventx.tasks.analyze_v7_online_rate_replication_20261028 import BLOCKS, load

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / 'data/v7/history_stack_20261031/development'
BLOCKS = dict(BLOCKS, june_15_28_new_identities=(ROOT / 'data/v7/late_june_test_20261027_v2', None))
NEW = ['june_8_14_new_identities', 'june_15_28_new_identities']
ORDER = ['stack_lin', 'stack_int', 'stack_hgb']
SEED = 20261031


def logit(p):
    p = np.clip(p, 1e-6, 1 - 1e-6)
    return np.log(p / (1 - p))


def design(k, name):
    lh, lr, h, la = logit(k['row_hgb7'].to_numpy()), logit(k['adaptive_rate'].to_numpy()), \
        np.log1p(k['history'].to_numpy()), logit(k['activity_logit'].to_numpy())
    return {'stack_lin': np.c_[lh, lr, h], 'stack_int': np.c_[lh, lr, h, h * lh, h * lr],
            'stack_hgb': np.c_[lh, lr, h, la]}[name]


def model(name):
    if name == 'stack_hgb':
        return HistGradientBoostingClassifier(max_depth=3, max_iter=200, learning_rate=0.05, min_samples_leaf=200,
                                              random_state=SEED)
    return LogisticRegression(C=1.0, max_iter=2000)


def main():
    data = {b: load(base, cohort) for b, (base, cohort) in BLOCKS.items()}
    rng = np.random.default_rng(SEED)
    out = {'at': datetime.now(timezone.utc).isoformat(), 'blocks': {b: {'rows': len(k), 'contracts': int(k.market_id.nunique())}
                                                                    for b, k in data.items()}, 'held_out': {}}
    for b, k in data.items():
        train = [data[x] for x in data if x != b]
        y = k['target'].to_numpy(float)
        res = {'rate': float(logloss(y, k['adaptive_rate'].to_numpy()).mean()),
               'row_hgb7': float(logloss(y, k['row_hgb7'].to_numpy()).mean())}
        for name in ORDER:
            m = model(name).fit(np.vstack([design(t, name) for t in train]),
                                np.concatenate([t['target'].to_numpy(int) for t in train]))
            p = m.predict_proba(design(k, name))[:, 1]
            ll = logloss(y, p)
            res[name] = float(ll.mean())
            res[name + '_vs_rate_ci95'] = one_way(logloss(y, k['adaptive_rate'].to_numpy()) - ll, k['market_id'].to_numpy(), rng)['ci95']
        out['held_out'][b] = res
    score = {n: float(np.mean([out['held_out'][b][n] for b in NEW])) for n in ORDER + ['rate', 'row_hgb7']}
    best = min(ORDER, key=lambda n: score[n])
    chosen = next(n for n in ORDER if score[n] <= score[best] + 0.0005)
    final = model(chosen).fit(np.vstack([design(k, chosen) for k in data.values()]),
                              np.concatenate([k['target'].to_numpy(int) for k in data.values()]))
    out.update(selection_score_new_blocks=score, selected=chosen)
    if chosen != 'stack_hgb':
        out['coefficients'] = {'intercept': float(final.intercept_[0]), 'coef': final.coef_[0].tolist()}
    OUT.mkdir(parents=True, exist_ok=True)
    joblib.dump({'name': chosen, 'model': final}, OUT / 'stack.joblib')
    (OUT / 'result.json').write_text(json.dumps(out, indent=1))
    print(json.dumps(out, indent=1))


if __name__ == '__main__':
    main()
