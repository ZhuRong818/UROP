"""Uncertified synchronous multi-day bootstrap candidates; no research file I/O.

Blocks cross outer-fold boundaries: the estimand conditions on fitted fold models,
not independent fold errors. Calendar stationarity/mixing still needs validation.
"""

import numpy as np


def moving_block_draws(values, family, day, *, block_days, replicates=5000,
                      seed=20260910, resample_families=True):
    values = np.asarray(values, float)
    if values.ndim == 1:
        values = values[:, None]
    family, day = np.asarray(family), np.asarray(day)
    n = len(values)
    if (values.ndim != 2 or not n or not np.isfinite(values).all()
            or family.shape != (n,) or day.shape != (n,) or day.dtype.kind not in 'iu'
            or isinstance(block_days, bool) or not isinstance(block_days, int)
            or block_days < 1 or not isinstance(replicates, int) or replicates < 1):
        raise ValueError('Invalid values/UTC-day indices/block settings')
    families, fi = np.unique(family, return_inverse=True)
    days, di = np.unique(day, return_inverse=True)
    nf, nd, k = len(families), len(days), values.shape[1]
    if np.any(np.diff(days) != 1):
        raise ValueError('Missing calendar days: no compression of temporal gaps')
    if nd < 2*block_days:
        raise ValueError('Fewer than two block lengths of calendar support')
    cells = fi*nd+di
    counts = np.bincount(cells, minlength=nf*nd).reshape(nf, nd)
    sums = np.stack([np.bincount(cells, weights=values[:, j], minlength=nf*nd)
                     for j in range(k)], axis=-1).reshape(nf, nd, k)
    rng = np.random.default_rng(seed)
    output = []
    for start in range(0, replicates, 64):
        fw, dw = [], []
        for _ in range(min(64, replicates-start)):
            f = rng.multinomial(nf, np.full(nf, 1/nf))
            starts = rng.integers(0, nd-block_days+1, size=(nd+block_days-1)//block_days)
            sampled = (starts[:, None]+np.arange(block_days)).ravel()[:nd]
            fw.append(f if resample_families else np.ones(nf))
            dw.append(np.bincount(sampled, minlength=nd))
        fw, dw = np.asarray(fw), np.asarray(dw)
        denominator = np.einsum('bf,fd,bd->b', fw, counts, dw, optimize=True)
        if np.any(denominator <= 0):
            raise ValueError('Empty-weight replicate; do not redraw/drop')
        numerator = np.einsum('bf,fdk,bd->bk', fw, sums, dw, optimize=True)
        output.append(numerator/denominator[:, None])
    return np.concatenate(output)


def wilson(successes, trials, z=1.959963984540054):
    if trials < 1 or not 0 <= successes <= trials:
        raise ValueError('Invalid binomial count')
    p = successes/trials
    den = 1+z*z/trials
    mid = (p+z*z/(2*trials))/den
    half = z*np.sqrt(p*(1-p)/trials+z*z/(4*trials*trials))/den
    return [float(mid-half), float(mid+half)]


def interpret_interval(lower, upper, useful_margin=.001):
    """Scientific interpretation, independent of the decision to stop a branch."""
    if not np.isfinite([lower, upper, useful_margin]).all() or lower > upper or useful_margin < 0:
        raise ValueError('Invalid interval/margin')
    if upper < 0:
        return 'evidence_of_harm'
    if upper < useful_margin:
        return 'useful_gain_excluded'
    if lower > 0:
        return 'positive_effect_useful_magnitude_not_necessarily_established'
    return 'inconclusive'


def news_decision(means, bounds, *, subgroup_lower=(), certified=False):
    """Policy-only helper. Never authorizes I/O or candidate freeze by itself.

    Order: market replication, news vs market, matched attribution, Brier.
    Certification false is checked before accessing metric arguments.
    """
    if not certified:
        return {'status': 'incomplete', 'promote_news': False}
    means, bounds = np.asarray(means, float), np.asarray(bounds, float)
    if (means.shape != (4,) or bounds.shape != (2, 4)
            or not np.isfinite(means).all() or not np.isfinite(bounds).all()
            or np.any(bounds[0] > bounds[1])):
        raise ValueError('Invalid required metrics')
    subgroup_lower = np.asarray(subgroup_lower, float)
    if subgroup_lower.ndim != 1 or not np.isfinite(subgroup_lower).all():
        raise ValueError('Invalid subgroup bounds')
    lb = bounds[0]
    gates = {'news_vs_market': bool(means[1] >= .001 and lb[1] > 0),
             'matched_attribution': bool(lb[2] > 0),
             'brier': bool(lb[3] > -.0005),
             'subgroups': bool(np.all(subgroup_lower > -.001))}
    passed = all(gates.values())
    return {'status': 'policy_pass_not_execution_authority' if passed else 'stop_news_branch',
            'promote_news': passed, 'gates': gates,
            'market_replication_passed': bool(means[0] >= .001 and lb[0] > 0),
            'news_interpretation': interpret_interval(*bounds[:, 1]),
            'subgroup_assessment': 'assessed' if len(subgroup_lower) else 'not_assessable'}
