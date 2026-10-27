"""Label-free named-matrix contract for the V5-R timing/content comparison.

Not yet wired into the research evaluator. Inputs must already pass source/PIT gates.
"""

import numpy as np
from scipy.special import logit

from eventx.features.v5_market import MARKET_FEATURE_NAMES


def matched_matrices(market, names, p0, exposed, age_minutes, capped_log_count,
                     qmax, qlast):
    names = tuple(names)
    if len(set(names)) != len(names) or set(names) != set(MARKET_FEATURE_NAMES):
        raise ValueError("Exactly the 15 named canonical market inputs are required")
    market = np.asarray(market, dtype=float)
    if market.ndim != 2 or market.shape[1] != len(names) or not np.isfinite(market).all():
        raise ValueError("Invalid market matrix")
    market = market[:, [names.index(n) for n in MARKET_FEATURE_NAMES]]
    arrays = [np.asarray(a, dtype=float) for a in
              [p0, age_minutes, capped_log_count, qmax, qlast]]
    if any(a.shape != (len(market),) or not np.isfinite(a).all() for a in arrays):
        raise ValueError("Features must be finite and row aligned")
    p0, age, count, maximum, last = arrays
    exposed = np.asarray(exposed)
    if exposed.dtype != bool or exposed.shape != p0.shape:
        raise ValueError("Explicit aligned boolean exposure gate required")
    if np.any((p0 <= 0) | (p0 >= 1)):
        raise ValueError("Base probabilities must be strictly inside (0,1)")
    if np.any((age < 0) | (age >= 30) | (count < 0)):
        raise ValueError("Invalid half-open E30 age/count inputs")
    if np.any((maximum < 0) | (maximum > 1) | (last < 0) | (last > maximum)):
        raise ValueError("Invalid relevance-novelty scores")
    if any(np.any(a[~exposed] != 0) for a in [age, count, maximum, last]):
        raise ValueError("Unexposed news inputs must be canonical zeros")
    a, c = age / 30, count
    z = np.column_stack([market, p0, logit(p0)])
    common = np.column_stack([z, a, c])
    terminal = market[:, MARKET_FEATURE_NAMES.index("log1p_minutes_to_scheduled_terminal")]
    return {"context": z, "timing": common,
            "timing_matched": np.column_stack([common, a*a, c*c, a*c]),
            "news": np.column_stack([common, maximum, last, maximum*terminal])}
