"""Post hoc segment discovery and replication on stored forecasts. Requested by the user on 1 Nov 2026.

Question: are there market or time segments where the frozen booster beats a baseline by more (or less) than it does
overall, and does such a pattern recur on later blocks? Everything below was fixed and committed before any segment
score was computed. Refits nothing; generates no new forecast; reads no unopened period. All five blocks are already
consumed, so this is descriptive, opened-data analysis, not a confirmatory test.

Comparisons (per-row log-loss gain, comparator minus booster):
  C1  row_hgb7 vs online contract rate   (pooled quote information vs the contract's own history)
  C2  row_hgb7 vs activity_logit         (the frozen headline comparison)
Blocks:
  discovery    May 13-19 (dev50), June 1-7 (dev50), June 8-14 (new contracts)
  replication  June 15-28 (new contracts), 29 June-12 July (new contracts; features rebuilt read-only from the
               captured source with the frozen build_panel, phase `features`)
Segment families (cut points fixed here, not from data):
  category      regex rules of analyze_v7_category_breakdown_20261027, unchanged
  utc_hour      00-05, 06-11, 12-17, 18-23
  price         current midpoint <0.05, 0.05-0.20, 0.20-0.80, 0.80-0.95, >=0.95
  spread        <=0.01, 0.01-0.03, >0.03
  activity30    valid quote states in last 30 min: 0-2, 3-20, >20  (expm1 of log_valid_updates30)
  moved30       |midpoint change over 30 min| == 0 vs > 0 (unavailable counts as 0)
  history       matured known outcomes 0-11, 12-47, >=48
  to_end        listed end date minus decision time: <3 d, 3-14 d, >=14 d
Per segment and comparison: rows, contracts, mean gain, and the INTERACTION = segment mean gain minus complement mean
gain, with a contract-clustered bootstrap (2,000 draws). Segments with <500 rows or <5 contracts in a phase are not
scored in that phase.
Discovery flag: interaction 95% CI excludes zero on the pooled discovery blocks AND the interaction has the same sign
in at least 2 of the 3 discovery blocks. Flag direction = sign ("stronger" / "weaker" than elsewhere).
Replication: for flagged segments only, one-sided contract-clustered p-value of the interaction in the same direction
on the pooled replication blocks; replicated if Holm-adjusted p < 0.05 across all flagged segments of both comparisons.
Unflagged segments are also reported on replication, descriptively.
Output: data/v7/segment_replication_20261101/{features_jul.parquet, result.json}
"""
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd

from eventx.tasks.analyze_v7_category_breakdown_20261027 import category
from eventx.tasks.analyze_v7_dependence_coverage_20261028 import logloss
from eventx.tasks.analyze_v7_online_rate_replication_20261028 import load
from eventx.tasks.research_v7_change_probability_20261025 import FEATURES

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / 'data/v7/segment_replication_20261101'
JUL = ROOT / 'data/v7/history_stack_20261031/test'
B, SEED, MIN_ROWS, MIN_CONTRACTS = 2000, 20261101, 500, 5
DISCOVERY = {'may_13_19': (ROOT / 'data/v7/week_replication_20261025', 'development50'),
             'jun_1_7': (ROOT / 'data/v7/june_replication_20261026', 'development50'),
             'jun_8_14': (ROOT / 'data/v7/new_identity_test_20261026_recovered', None)}
REPLICATION = {'jun_15_28': (ROOT / 'data/v7/late_june_test_20261027_v2', None), 'jun29_jul12': (JUL, None)}
COMPARISONS = {'C1_vs_rate': 'adaptive_rate', 'C2_vs_activity_logit': 'activity_logit'}
FI = {f: i for i, f in enumerate(FEATURES)}


def metadata():
    old = json.loads((ROOT / 'data/v7/family_training_20261025_v02/cohort/cohorts.json').read_text())
    ms = old['development50'] + old['unseen10']
    for p in ['data/v7/new_identity_test_20261026/cohort/cohort.json', 'data/v7/late_june_test_20261027_v2/cohort/cohort.json',
              'data/v7/history_stack_20261031/test/cohort/cohort.json']:
        ms += json.loads((ROOT / p).read_text())['new']
    end = lambda s: datetime.fromisoformat(s.replace('Z', '+00:00')).timestamp() if s else np.nan
    return {m['market_id']: (category(m['question']), end(m.get('endDate'))) for m in ms}


def rebuild_july_features():
    """Read-only: re-derive the frozen features of the issued July rows from the captured, hash-verified source."""
    from eventx.tasks.run_v7_history_stack_test_20261031 import DATES, load_cohort
    from eventx.v7.calibration_transport_20261025 import build_panel
    sel, rows = load_cohort(), []
    for k in range(0, len(sel), 15):
        for r in build_panel(JUL / 'source', DATES, sel[k:k + 15]):
            if r['current_valid']:
                rows.append({'market_id': r['market_id'], 'decision_at': r['decision_at'], 'current_midpoint': r['current_midpoint'],
                             **{f: r['features'][i] for f, i in FI.items()}})
    OUT.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(rows).to_parquet(OUT / 'features_jul.parquet')
    print(json.dumps({'phase': 'features', 'rows': len(rows)}), flush=True)


def block(name, base, cohort):
    if name == 'jun29_jul12':
        k = pd.read_parquet(base / 'evaluation/issued_predictions.parquet')
        k = k[k.endpoint_eligible].reset_index(drop=True)
        f = pd.read_parquet(OUT / 'features_jul.parquet')
    else:
        k = load(base, cohort)
        led = pd.read_parquet(base / 'evaluation/grid_ledger.parquet', columns=['market_id', 'decision_at', 'features', 'current_midpoint'])
        led = led[led.features.notna()]
        f = pd.DataFrame({'market_id': led.market_id.values, 'decision_at': led.decision_at.values,
                          'current_midpoint': led.current_midpoint.values,
                          **{n: [x[i] for x in led.features] for n, i in FI.items()}})
    k = k.merge(f[['market_id', 'decision_at', 'current_midpoint', 'spread', 'log_valid_updates30', 'abs_delta30', 'missing30']],
                on=['market_id', 'decision_at'], how='left', validate='one_to_one')
    assert k['spread'].notna().all(), name
    k['block'] = name
    return k


def segments(k, meta):
    cat = k.market_id.map(lambda c: meta[c][0])
    end = k.market_id.map(lambda c: meta[c][1]).astype(float)
    hour = (k['t'] % 86400) // 3600
    mid, spr = k['current_midpoint'], k['spread']
    act = np.expm1(k['log_valid_updates30']).round()
    moved = (k['abs_delta30'] > 0) & (k['missing30'] == 0)
    days = (end - k['t']) / 86400
    S = {}
    for c in sorted(set(cat)):
        S[f'category={c}'] = cat == c
    for lo in [0, 6, 12, 18]:
        S[f'utc_hour={lo:02d}-{lo + 5:02d}'] = (hour >= lo) & (hour <= lo + 5)
    for lab, lo, hi in [('<0.05', 0, .05), ('0.05-0.20', .05, .2), ('0.20-0.80', .2, .8), ('0.80-0.95', .8, .95), ('>=0.95', .95, 2)]:
        S[f'price={lab}'] = (mid >= lo) & (mid < hi)
    S['spread<=0.01'], S['spread=0.01-0.03'], S['spread>0.03'] = spr <= .01 + 1e-9, (spr > .01 + 1e-9) & (spr <= .03 + 1e-9), spr > .03 + 1e-9
    S['activity30=0-2'], S['activity30=3-20'], S['activity30>20'] = act <= 2, (act >= 3) & (act <= 20), act > 20
    S['moved30=no'], S['moved30=yes'] = ~moved, moved
    S['history=0-11'], S['history=12-47'], S['history>=48'] = k['history'] <= 11, (k['history'] >= 12) & (k['history'] <= 47), k['history'] >= 48
    S['to_end<3d'], S['to_end=3-14d'], S['to_end>=14d'] = days < 3, (days >= 3) & (days < 14), days >= 14
    return {n: m.to_numpy(bool) for n, m in S.items()}


def interaction(g, m, ids, rng):
    """Segment mean minus complement mean, resampling whole contracts."""
    keys, inv = np.unique(ids, return_inverse=True)
    s1, n1 = np.bincount(inv, g * m, len(keys)), np.bincount(inv, m.astype(float), len(keys))
    s0, n0 = np.bincount(inv, g * ~m, len(keys)), np.bincount(inv, (~m).astype(float), len(keys))
    d = rng.integers(0, len(keys), size=(B, len(keys)))
    with np.errstate(invalid='ignore', divide='ignore'):
        st = s1[d].sum(1) / n1[d].sum(1) - s0[d].sum(1) / n0[d].sum(1)
    st = st[np.isfinite(st)]
    est = g[m].mean() - g[~m].mean()
    return {'interaction': float(est), 'ci95': [float(np.quantile(st, .025)), float(np.quantile(st, .975))],
            'p_gt0': float((np.sum(st <= 0) + 1) / (len(st) + 1)), 'p_lt0': float((np.sum(st >= 0) + 1) / (len(st) + 1))}


def score(k, segs, rng):
    y, ids = k['target'].to_numpy(float), k['market_id'].to_numpy()
    out = {}
    for cname, comp in COMPARISONS.items():
        g = logloss(y, k[comp].to_numpy()) - logloss(y, k['row_hgb7'].to_numpy())
        res = {'overall_gain': float(g.mean())}
        for sname, m in segs.items():
            n, nc = int(m.sum()), int(len(set(ids[m])))
            r = {'rows': n, 'contracts': nc}
            if n >= MIN_ROWS and nc >= MIN_CONTRACTS and (~m).sum() >= MIN_ROWS:
                r.update(gain=float(g[m].mean()), **interaction(g, m, ids, rng))
            res[sname] = r
        out[cname] = res
    return out


def holm(ps):
    order, adj, run = np.argsort(ps), np.empty(len(ps)), 0.0
    for rank, i in enumerate(order):
        run = max(run, min(1.0, (len(ps) - rank) * ps[i]))
        adj[i] = run
    return adj


def main():
    if 'features' in sys.argv[1:]:
        return rebuild_july_features()
    meta, rng = metadata(), np.random.default_rng(SEED)
    data = {n: block(n, *cfg) for n, cfg in {**DISCOVERY, **REPLICATION}.items()}
    result = {'at': datetime.now(timezone.utc).isoformat(), 'post_hoc': True, 'descriptive_only': True, 'model_refit': False,
              'blocks': {n: {'rows': len(k), 'contracts': int(k.market_id.nunique())} for n, k in data.items()},
              'per_block': {}, 'discovery_pooled': {}, 'replication_pooled': {}, 'flags': []}
    for n, k in data.items():
        result['per_block'][n] = score(k, segments(k, meta), rng)
    disc = pd.concat([data[n] for n in DISCOVERY], ignore_index=True)
    rep = pd.concat([data[n] for n in REPLICATION], ignore_index=True)
    result['discovery_pooled'] = score(disc, segments(disc, meta), rng)
    result['replication_pooled'] = score(rep, segments(rep, meta), rng)
    for cname in COMPARISONS:
        for sname, r in result['discovery_pooled'][cname].items():
            if sname == 'overall_gain' or 'ci95' not in r:
                continue
            lo, hi = r['ci95']
            if lo <= 0 <= hi:
                continue
            sign = 1 if lo > 0 else -1
            agree = sum(1 for b in DISCOVERY if 'interaction' in result['per_block'][b][cname][sname]
                        and np.sign(result['per_block'][b][cname][sname]['interaction']) == sign)
            if agree < 2:
                continue
            rr = result['replication_pooled'][cname][sname]
            p = rr.get('p_gt0' if sign > 0 else 'p_lt0', 1.0)
            result['flags'].append({'comparison': cname, 'segment': sname, 'direction': 'stronger' if sign > 0 else 'weaker',
                                    'discovery_interaction': r['interaction'], 'discovery_ci95': r['ci95'], 'discovery_blocks_agree': agree,
                                    'replication_interaction': rr.get('interaction'), 'replication_ci95': rr.get('ci95'),
                                    'replication_gain': rr.get('gain'), 'replication_p_one_sided': p})
    if result['flags']:
        adj = holm(np.array([f['replication_p_one_sided'] for f in result['flags']]))
        for f, a in zip(result['flags'], adj):
            f['holm_p'], f['replicated'] = float(a), bool(a < 0.05)
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / 'result.json').write_text(json.dumps(result, indent=1))
    print(json.dumps({'blocks': result['blocks'], 'flags': result['flags']}, indent=1))


if __name__ == '__main__':
    main()
