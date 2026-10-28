"""What drives the frozen row_hgb7 quote-change booster: permutation importance and reliability on June 1-7.

Post hoc and descriptive (guardrail D12). June 1-7 is already consumed for this model; the frozen booster and
logistic baseline are only re-applied to the hash-checked grid ledger (reproduction is asserted against the stored
issued predictions). No model, feature or threshold is refit or changed, and no unopened block is read.
"""
import json

import joblib
import numpy as np
import pyarrow.parquet as pq

from eventx.tasks.discover_v7_direct_pilot_20261022 import REPO_ROOT, now, write
from eventx.tasks.research_v7_change_probability_20261025 import ACTIVITY, FEATURES
from eventx.tasks.run_v7_archive_week_pilot_20261025 import verify

EVAL = REPO_ROOT / 'data/v7/june_replication_20261026/evaluation'
MODELS = REPO_ROOT / 'data/v7/family_training_20261025_v02/development/frozen_models.joblib'
OUT = REPO_ROOT / 'data/v7/booster_drivers_20261027'
REPEATS, SEED = 10, 20261027
# Groups keep correlated columns together so one cannot stand in for its permuted twin.
GROUPS = {
    'price_level': ['midpoint', 'logit_midpoint'],
    'spread': ['spread'],
    'quote_freshness': ['source_age', 'receive_age'],
    'time_of_day': ['hour_sin', 'hour_cos'],
    'update_activity': ['log_valid_updates30', 'valid_state_fraction30'],
    'recent_moves_5m': ['delta5', 'abs_delta5', 'missing5'],
    'recent_moves_15m': ['delta15', 'abs_delta15', 'missing15'],
    'recent_moves_30m': ['delta30', 'abs_delta30', 'missing30'],
}
LOGISTIC_ONLY = [FEATURES[i] for i in ACTIVITY]


def logloss(y, p):
    p = np.clip(p, 1e-6, 1 - 1e-6)
    return float(-np.mean(y * np.log(p) + (1 - y) * np.log1p(-p)))


def reliability(y, p, bins=10):
    edges = np.quantile(p, np.linspace(0, 1, bins + 1))
    k = np.clip(np.searchsorted(edges, p, side='right') - 1, 0, bins - 1)
    rows = [{'n': int((k == i).sum()), 'mean_prediction': float(p[k == i].mean()), 'observed_rate': float(y[k == i].mean())}
            for i in range(bins) if (k == i).any()]
    ece = sum(r['n'] * abs(r['mean_prediction'] - r['observed_rate']) for r in rows) / len(p)
    return {'bins': rows, 'ece_equal_frequency': float(ece)}


def main():
    verify(EVAL / 'manifest.json')
    bundle = joblib.load(MODELS)
    assert bundle['selected'] == 'row_hgb7' and bundle['features'] == FEATURES
    booster, logit = bundle['models']['row_hgb7']['estimator'], bundle['models']['activity_logit']['estimator']
    led = pq.read_table(EVAL / 'grid_ledger.parquet').to_pydict()
    issued = np.asarray(led['current_valid'], dtype=bool)
    stored = pq.read_table(EVAL / 'issued_predictions.parquet').to_pydict()
    x_all = np.asarray([f for f, keep in zip(led['features'], issued) if keep], dtype=float)
    p_all = booster.predict_proba(x_all)[:, 1]
    reproduction_error = float(np.max(np.abs(np.clip(p_all, 1e-6, 1 - 1e-6) - np.asarray(stored['row_hgb7']))))
    assert reproduction_error < 1e-9, reproduction_error
    keep = np.asarray(stored['endpoint_eligible'], dtype=bool) & (np.asarray(stored['cohort']) == 'development50')
    x, y = x_all[keep], np.asarray([v or 0 for v in stored['target']])[keep].astype(float)
    p_boost, p_logit = booster.predict_proba(x)[:, 1], logit.predict_proba(x[:, ACTIVITY])[:, 1]
    base = {'booster': logloss(y, p_boost), 'logistic': logloss(y, p_logit)}
    gap = base['logistic'] - base['booster']
    rng = np.random.default_rng(SEED)

    def permuted(columns):
        idx = [FEATURES.index(c) for c in columns]
        losses = []
        for _ in range(REPEATS):
            xp = x.copy()
            order = rng.permutation(len(x))  # joint permutation keeps within-group relations
            xp[:, idx] = x[order][:, idx]
            losses.append(logloss(y, booster.predict_proba(xp)[:, 1]) - base['booster'])
        return {'mean_logloss_increase': float(np.mean(losses)), 'sd': float(np.std(losses, ddof=1)),
                'share_of_booster_gap_over_logistic': float(np.mean(losses) / gap)}

    groups = {g: {'features': cols, **permuted(cols)} for g, cols in GROUPS.items()}
    single = {f: permuted([f]) for f in FEATURES}
    extra = [f for f in FEATURES if f not in LOGISTIC_ONLY]
    result = {
        'at': now().isoformat(), 'descriptive_post_hoc': True, 'refit': False, 'block': 'June 1-7 development50, consumed',
        'rows': int(keep.sum()), 'positives': int(y.sum()), 'repeats': REPEATS, 'seed': SEED,
        'reproduction_max_abs_error_vs_stored': reproduction_error,
        'logloss': base, 'booster_gain_over_logistic': gap,
        'group_permutation': groups, 'feature_permutation': single,
        'features_unavailable_to_logistic': extra,
        'permute_all_features_unavailable_to_logistic': permuted(extra),
        'reliability': {'booster': reliability(y, p_boost), 'logistic': reliability(y, p_logit)},
    }
    OUT.mkdir(parents=True, exist_ok=True)
    write(OUT / 'result.json', result)
    print(json.dumps({k: result[k] for k in ('rows', 'logloss', 'booster_gain_over_logistic',
                                             'permute_all_features_unavailable_to_logistic')}, indent=1))
    for g, v in sorted(groups.items(), key=lambda kv: -kv[1]['mean_logloss_increase']):
        print(f"{g:18s} {v['mean_logloss_increase']:.4f} ({v['share_of_booster_gap_over_logistic']:.0%} of gap)")
    print({m: round(r['ece_equal_frequency'], 4) for m, r in result['reliability'].items()})


if __name__ == '__main__':
    main()
