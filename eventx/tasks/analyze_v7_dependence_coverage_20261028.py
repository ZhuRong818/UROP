"""Post hoc dependence, coverage and adaptive-rate analysis of the two consumed June blocks.

Descriptive only. It reads the stored ledgers and issued predictions of the June 1-7 (development50) and
June 8-14 (new identities) evaluations, after their consumption receipts. It refits nothing, regenerates no
prediction, changes no frozen model and is not a pass/fail test. All definitions below were fixed before the
script was first run on 28 Oct 2026:

1. Reproduce the stored primary log loss and contract-clustered interval (check of data handling).
2. Joint dependence: pigeonhole two-way bootstrap (contract x date; and event family x date), resampling
   contracts and dates independently with replacement and weighting each row by the product of its
   multiplicities; 5,000 draws, seed 20261028. Statistic: row-weighted log-loss gain of row_hgb7 over the
   comparator (comparator minus booster, positive favours the booster).
3. Adaptive contract rate: an online baseline that uses only outcomes already observable at each decision,
   p = (k + 20 g) / (n + 20), where k, n are the positives and count of the same contract's known outcomes
   from decisions at t' with t' + 1800 + 300 <= t (endpoint matured plus one grid step), pooled over earlier
   dates in the block, and g is the row's stored frozen global-rate forecast. Pseudocount 20 matches the
   frozen market-rate baseline. One variant only; no tuning.
4. Coverage decomposition of scheduled decisions: issued; not issued after the contract's listed endDate
   (current metadata, so approximate); not issued in a contract-day with no issued decision; not issued
   within an otherwise active contract-day.
5. Selection check: gain over activity_logit by tertile of contract-day issuance coverage (contract-day
   coverage among scheduled decisions; tertiles over contract-days with a known outcome), and the Spearman
   correlation of per-contract coverage with per-contract gain.
Added after the first run, once the adaptive rate proved close to the booster (separate generator, seed
20261029, so items 1-5 are unchanged): 6. Brier gain over the adaptive rate with a contract-clustered interval,
ROC AUC of booster, adaptive rate and activity_logit, and the per-date log-loss gain over the adaptive rate.
Output: data/v7/dependence_coverage_20261028/result.json
"""
import json
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.stats import spearmanr
from sklearn.metrics import roc_auc_score

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / 'data/v7/dependence_coverage_20261028'
B, SEED, PSEUDO, LAG = 5000, 20261028, 20, 1800 + 300
BLOCKS = {
    'june_1_7_development50': dict(base=ROOT / 'data/v7/june_replication_20261026', cohort='development50',
                                   meta=ROOT / 'data/v7/family_training_20261025_v02/cohort/cohorts.json'),
    'june_8_14_new_identities': dict(base=ROOT / 'data/v7/new_identity_test_20261026_recovered', cohort=None,
                                     meta=ROOT / 'data/v7/new_identity_test_20261026_recovered/cohort/cohort.json'),
}
COMPARATORS = ['activity_logit', 'global_rate', 'market_rate', 'legacy_hgb7', 'adaptive_rate']


def receipt_completed(base):
    r = json.loads((base / 'evaluation/consumption_receipt.json').read_text())
    if r.get('status') != 'completed':
        raise RuntimeError(f'{base} has no completed consumption receipt')


def metadata(path):
    c = json.loads(path.read_text())
    rows = [m for v in c.values() if isinstance(v, list) for m in v if isinstance(m, dict) and 'market_id' in m]
    return {m['market_id']: {'family': '|'.join(sorted(e['id'] for e in m.get('events') or [])) or m['market_id'],
                             'end': pd.Timestamp(m['endDate']).timestamp() if m.get('endDate') else np.inf}
            for m in rows}


def logloss(y, p):
    return -(y * np.log(p) + (1 - y) * np.log1p(-p))


def one_way(diff, groups, rng):
    keys, inv = np.unique(groups, return_inverse=True)
    s, n = np.bincount(inv, diff), np.bincount(inv)
    d = rng.integers(0, len(keys), size=(B, len(keys)))
    st = s[d].sum(1) / n[d].sum(1)
    return {'clusters': int(len(keys)), 'ci95': [float(np.quantile(st, .025)), float(np.quantile(st, .975))]}


def two_way(diff, a, b, rng):
    ka, ia = np.unique(a, return_inverse=True)
    kb, ib = np.unique(b, return_inverse=True)
    S, N = np.zeros((len(ka), len(kb))), np.zeros((len(ka), len(kb)))
    np.add.at(S, (ia, ib), diff)
    np.add.at(N, (ia, ib), 1)
    ma = rng.multinomial(len(ka), np.full(len(ka), 1 / len(ka)), size=B).astype(float)
    mb = rng.multinomial(len(kb), np.full(len(kb), 1 / len(kb)), size=B).astype(float)
    st = np.einsum('ri,ij,rj->r', ma, S, mb) / np.einsum('ri,ij,rj->r', ma, N, mb)
    return {'clusters': [int(len(ka)), int(len(kb))], 'ci95': [float(np.quantile(st, .025)), float(np.quantile(st, .975))]}


def adaptive_rate(df):
    p = np.empty(len(df))
    for _, g in df.groupby('market_id', sort=False):
        t = g['t'].to_numpy()
        order = np.argsort(t)
        known = g['endpoint_eligible'].to_numpy()[order]
        y = np.nan_to_num(g['target'].to_numpy()[order])
        ts = t[order]
        ck, cn = np.concatenate([[0], np.cumsum(y * known)]), np.concatenate([[0], np.cumsum(known)])
        j = np.searchsorted(ts, ts - LAG, side='right')  # rows with t' <= t - LAG
        gr = g['global_rate'].to_numpy()[order]
        p[g.index.to_numpy()[order]] = (ck[j] + PSEUDO * gr) / (cn[j] + PSEUDO)
    return np.clip(p, 1e-6, 1 - 1e-6)


def block(name, cfg, rng, rng6):
    base = cfg['base']
    receipt_completed(base)
    stored = json.loads((base / 'evaluation/result.json').read_text())
    led = pd.read_parquet(base / 'evaluation/grid_ledger.parquet',
                          columns=['market_id', 'date', 't', 'decision_at', 'current_valid'] + (['cohort'] if cfg['cohort'] else []))
    iss = pd.read_parquet(base / 'evaluation/issued_predictions.parquet')
    if cfg['cohort']:
        led, iss = led[led.cohort == cfg['cohort']], iss[iss.cohort == cfg['cohort']]
        stored = stored['cohorts'][cfg['cohort']]
    iss = iss.merge(led[['market_id', 'decision_at', 't']], on=['market_id', 'decision_at'], how='left',
                    validate='one_to_one').reset_index(drop=True)
    assert iss['t'].notna().all() and len(iss) == int(led.current_valid.sum())
    iss['adaptive_rate'] = adaptive_rate(iss)
    meta = metadata(cfg['meta'])
    k = iss[iss.endpoint_eligible].reset_index(drop=True)
    y = k['target'].to_numpy(float)
    loss = {m: logloss(y, k[m].to_numpy()) for m in ['row_hgb7'] + COMPARATORS}
    ids, dates = k['market_id'].to_numpy(), k['date'].to_numpy()
    fams = np.array([meta[i]['family'] for i in ids])
    out = {'known': int(len(k)), 'issued': int(len(iss)), 'scheduled': int(len(led)),
           'contracts': int(len(set(ids))), 'families': int(len(set(fams))), 'dates': int(len(set(dates))),
           'log_loss': {m: float(v.mean()) for m, v in loss.items()},
           'brier': {m: float(np.mean((k[m].to_numpy() - y) ** 2)) for m in ['row_hgb7'] + COMPARATORS},
           'stored_check': {'row_hgb7_log_loss': stored['primary']['row_hgb7']['log_loss'],
                            'activity_logit_log_loss': stored['primary']['activity_logit']['log_loss'],
                            'stored_contract_ci95': stored.get('bootstrap', {}).get('activity_logit', {}).get('by_contract', {}).get('ci95')},
           'gain_vs': {}}
    for m in COMPARATORS:
        diff = loss[m] - loss['row_hgb7']
        out['gain_vs'][m] = {'gain_nats': float(diff.mean()), 'relative_pct': float(100 * diff.mean() / loss[m].mean()),
                             'by_contract': one_way(diff, ids, rng), 'by_date': one_way(diff, dates, rng),
                             'by_family': one_way(diff, fams, rng),
                             'two_way_contract_date': two_way(diff, ids, dates, rng),
                             'two_way_family_date': two_way(diff, fams, dates, rng),
                             'contracts_favouring_booster': int(sum(diff[ids == c].mean() > 0 for c in set(ids)))}
    # 4. coverage decomposition over scheduled decisions
    led = led.copy()
    led['cday'] = led.market_id + '|' + led.date
    active = led.groupby('cday').current_valid.transform('any')
    after_end = led.t.to_numpy() > np.array([meta.get(i, {'end': np.inf})['end'] for i in led.market_id])
    n = len(led)
    cats = {'issued': led.current_valid.to_numpy(),
            'not_issued_after_listed_end': ~led.current_valid.to_numpy() & after_end,
            'not_issued_inactive_contract_day': ~led.current_valid.to_numpy() & ~after_end & ~active.to_numpy(),
            'not_issued_within_active_contract_day': ~led.current_valid.to_numpy() & ~after_end & active.to_numpy()}
    out['coverage'] = {c: {'n': int(v.sum()), 'pct': float(100 * v.sum() / n)} for c, v in cats.items()}
    per_c = led.groupby('market_id').current_valid.agg(['sum', 'size'])
    out['coverage']['contracts_scheduled'] = int(len(per_c))
    out['coverage']['contracts_never_issued'] = int((per_c['sum'] == 0).sum())
    out['coverage']['issued_pct_within_active_contract_days'] = float(100 * led.current_valid[active].mean())
    # 5. selection check
    cov = led.groupby('cday').current_valid.mean()
    k['cday'] = k.market_id + '|' + k.date
    kc = cov.reindex(k['cday'].unique())
    edges = np.quantile(kc, [1 / 3, 2 / 3])
    tert = np.digitize(cov.reindex(k['cday']).to_numpy(), edges, right=True)
    diff = loss['activity_logit'] - loss['row_hgb7']
    out['gain_by_contract_day_coverage_tertile'] = []
    for i in range(3):
        m = tert == i
        out['gain_by_contract_day_coverage_tertile'].append(
            {'tertile': i + 1, 'coverage_range': [float(kc[np.digitize(kc, edges, right=True) == i].min()),
                                                 float(kc[np.digitize(kc, edges, right=True) == i].max())],
             'known': int(m.sum()), 'contracts': int(len(set(ids[m]))), 'gain_nats': float(diff[m].mean()),
             'by_contract': one_way(diff[m], ids[m], rng)})
    pc = pd.DataFrame({'id': ids, 'd': diff}).groupby('id').d.mean()
    pcov = (per_c['sum'] / per_c['size']).reindex(pc.index)
    rho = spearmanr(pcov, pc)
    out['spearman_contract_coverage_vs_gain'] = {'rho': float(rho.statistic), 'p': float(rho.pvalue), 'n': int(len(pc))}
    # 6. added after the first run
    sq = {m: (k[m].to_numpy() - y) ** 2 for m in ['row_hgb7', 'adaptive_rate']}
    bd = sq['adaptive_rate'] - sq['row_hgb7']
    da = loss['adaptive_rate'] - loss['row_hgb7']
    out['vs_adaptive_rate_added'] = {
        'brier_gain': float(bd.mean()), 'brier_gain_by_contract': one_way(bd, ids, rng6),
        'roc_auc': {m: float(roc_auc_score(y, k[m])) for m in ['row_hgb7', 'adaptive_rate', 'activity_logit']},
        'log_loss_gain_by_date': {d: float(da[dates == d].mean()) for d in sorted(set(dates))},
        'dates_favouring_booster': int(sum(da[dates == d].mean() > 0 for d in set(dates)))}
    return out


def main():
    rng, rng6 = np.random.default_rng(SEED), np.random.default_rng(SEED + 1)
    result = {'at': datetime.now(timezone.utc).isoformat(), 'post_hoc': True, 'descriptive_only': True,
              'model_refit': False, 'predictions_regenerated': False, 'seed': SEED, 'resamples': B,
              'adaptive_rate': {'pseudocount': PSEUDO, 'maturity_lag_s': LAG, 'prior': 'stored global_rate'},
              'blocks': {name: block(name, cfg, rng, rng6) for name, cfg in BLOCKS.items()}}
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / 'result.json').write_text(json.dumps(result, indent=1))
    print(json.dumps(result, indent=1))


if __name__ == '__main__':
    main()
