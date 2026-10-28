"""Post hoc: does the online-rate result recur on May 13-19, and where in a contract's history does the booster gain?

Descriptive only, on three already-consumed blocks (completed consumption receipts are checked). Reuses the
online-rate definition of analyze_v7_dependence_coverage_20261028 unchanged (pseudocount 20 toward the stored
global rate, maturity lag 2,100 s). Refits nothing and regenerates no prediction. Fixed before the first run
on 28 Oct 2026:

1. May 13-19 (development50, 30 contracts, opened 25 Oct): booster vs online rate and vs activity_logit, log
   loss, Brier and AUC, with contract and contract x date intervals (5,000 draws, seed 20261030).
2. History strata, all three blocks: rows grouped by the number of the contract's matured known outcomes at
   decision time (0, 1-11, 12-47, >=48, i.e. none, under 1 h, 1-4 h, over 4 h of matured 5-minute outcomes).
   Per stratum: rows, contracts, booster-minus-rate and logistic-minus-booster log-loss gains with contract
   intervals. Strata are descriptive; the first stratum is the cold-start comparison.
Added after the first run (separate generator, seed 20261031, so items 1-2 are unchanged): 3. May 13-19 Brier
gain over the rate with a contract interval; each history stratum's share of the block's aggregate log-loss
gain over the rate (stratum gain x rows / total gain x rows).
Output: data/v7/online_rate_replication_20261028/result.json
"""
import json
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.metrics import roc_auc_score

from eventx.tasks.analyze_v7_dependence_coverage_20261028 import LAG, adaptive_rate, logloss, one_way, two_way

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / 'data/v7/online_rate_replication_20261028'
SEED = 20261030
STRATA = [(0, 0), (1, 11), (12, 47), (48, 10**9)]
BLOCKS = {'may_13_19_development50': (ROOT / 'data/v7/week_replication_20261025', 'development50'),
          'june_1_7_development50': (ROOT / 'data/v7/june_replication_20261026', 'development50'),
          'june_8_14_new_identities': (ROOT / 'data/v7/new_identity_test_20261026_recovered', None)}


def load(base, cohort):
    if json.loads((base / 'evaluation/consumption_receipt.json').read_text()).get('status') != 'completed':
        raise RuntimeError(f'{base} has no completed consumption receipt')
    led = pd.read_parquet(base / 'evaluation/grid_ledger.parquet', columns=['market_id', 'decision_at', 't'] + (['cohort'] if cohort else []))
    iss = pd.read_parquet(base / 'evaluation/issued_predictions.parquet')
    if cohort:
        led, iss = led[led.cohort == cohort].drop(columns='cohort'), iss[iss.cohort == cohort]
    iss = iss.merge(led, on=['market_id', 'decision_at'], how='left', validate='one_to_one').reset_index(drop=True)
    assert iss['t'].notna().all()
    iss['adaptive_rate'] = adaptive_rate(iss)
    # matured known outcomes available at each decision (same rule as the rate)
    hist = np.empty(len(iss), dtype=int)
    for _, g in iss.groupby('market_id', sort=False):
        o = np.argsort(g['t'].to_numpy())
        ts, known = g['t'].to_numpy()[o], g['endpoint_eligible'].to_numpy()[o]
        cn = np.concatenate([[0], np.cumsum(known)])
        hist[g.index.to_numpy()[o]] = cn[np.searchsorted(ts, ts - LAG, side='right')]
    iss['history'] = hist
    return iss[iss.endpoint_eligible].reset_index(drop=True)


def main():
    rng, rng3 = np.random.default_rng(SEED), np.random.default_rng(SEED + 1)
    out = {'at': datetime.now(timezone.utc).isoformat(), 'post_hoc': True, 'descriptive_only': True,
           'model_refit': False, 'seed': SEED, 'blocks': {}}
    for name, (base, cohort) in BLOCKS.items():
        k = load(base, cohort)
        y, ids, dates = k['target'].to_numpy(float), k['market_id'].to_numpy(), k['date'].to_numpy()
        ll = {m: logloss(y, k[m].to_numpy()) for m in ['row_hgb7', 'adaptive_rate', 'activity_logit']}
        vs_rate, vs_logit = ll['adaptive_rate'] - ll['row_hgb7'], ll['activity_logit'] - ll['row_hgb7']
        b = {'known': int(len(k)), 'contracts': int(len(set(ids))),
             'log_loss': {m: float(v.mean()) for m, v in ll.items()},
             'brier': {m: float(np.mean((k[m].to_numpy() - y) ** 2)) for m in ll},
             'roc_auc': {m: float(roc_auc_score(y, k[m])) for m in ll}}
        if name.startswith('may'):
            b['booster_vs_rate'] = {'gain_nats': float(vs_rate.mean()), 'relative_pct': float(100 * vs_rate.mean() / ll['adaptive_rate'].mean()),
                                    'by_contract': one_way(vs_rate, ids, rng), 'two_way_contract_date': two_way(vs_rate, ids, dates, rng),
                                    'contracts_favouring_booster': int(sum(vs_rate[ids == c].mean() > 0 for c in set(ids))),
                                    'dates_favouring_booster': int(sum(vs_rate[dates == d].mean() > 0 for d in set(dates)))}
            bd = (k['adaptive_rate'].to_numpy() - y) ** 2 - (k['row_hgb7'].to_numpy() - y) ** 2
            b['booster_vs_rate']['brier_gain_added'] = {'gain': float(bd.mean()), 'by_contract': one_way(bd, ids, rng3)}
        b['history_strata'] = []
        for lo, hi in STRATA:
            m = (k['history'] >= lo).to_numpy() & (k['history'] <= hi).to_numpy()
            if not m.any():
                continue
            b['history_strata'].append({'matured_outcomes': [lo, None if hi >= 10**9 else hi], 'rows': int(m.sum()),
                                        'contracts': int(len(set(ids[m]))),
                                        'booster_minus_rate_gain': float(vs_rate[m].mean()),
                                        'booster_minus_rate_ci95': one_way(vs_rate[m], ids[m], rng)['ci95'],
                                        'logit_minus_booster_gain': float(vs_logit[m].mean()),
                                        'logit_minus_booster_ci95': one_way(vs_logit[m], ids[m], rng)['ci95']})
        for st in b['history_strata']:
            st['share_of_aggregate_gain_added'] = st['booster_minus_rate_gain'] * st['rows'] / (vs_rate.mean() * len(k))
        out['blocks'][name] = b
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / 'result.json').write_text(json.dumps(out, indent=1))
    print(json.dumps(out, indent=1))


if __name__ == '__main__':
    main()
