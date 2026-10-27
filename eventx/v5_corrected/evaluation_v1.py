"""Pure-array V5 decision rules and paired family/calendar uncertainty.

No file readers or implicit holdout access. Real-data callers still need a frozen
source/split manifest and a separate consumption workflow. Synthetic validation of
coverage is reported separately from deterministic software correctness.
"""

import numpy as np
from sklearn.metrics import average_precision_score

from .experiment_v1 import ll


def bootstrap(deltas, family, day, fold, masks=None, replicates=5000, seed=20260909,
              mode="crossed"):
    """Aggregate once by family/date; draws are paired across metrics/subgroups.

    Family multiplicity is global across time folds. Calendar days are resampled
    synchronously across families, separately within each outer time fold.
    """
    deltas = np.asarray(deltas, float)
    if deltas.ndim == 1:
        deltas = deltas[:, None]
    n = len(deltas)
    family, day, fold = map(np.asarray, (family, day, fold))
    if (not n or deltas.ndim != 2 or not np.isfinite(deltas).all()
            or any(x.shape != (n,) for x in (family, day, fold))
            or replicates < 1 or mode not in {"crossed", "family", "calendar"}):
        raise ValueError("Invalid bootstrap inputs")
    families, fi = np.unique(family, return_inverse=True)
    days, di = np.unique(day, return_inverse=True)
    dayfold = []
    for d in days:
        f = np.unique(fold[day == d])
        if len(f) != 1:
            raise ValueError("A UTC day cannot belong to multiple outer time blocks")
        dayfold.append(f[0])
    dayfold = np.asarray(dayfold)
    groups = {"all": np.ones(n, bool), **(masks or {})}
    if masks and "all" in masks:
        raise ValueError("Reserved group name")
    nf, nd, k = len(families), len(days), deltas.shape[1]
    cells = fi*nd+di
    aggregates = {}
    for name, mask in groups.items():
        mask = np.asarray(mask)
        if mask.dtype != bool or mask.shape != (n,) or not mask.any():
            raise ValueError("Empty/invalid required bootstrap group")
        counts = np.bincount(cells[mask], minlength=nf*nd).reshape(nf, nd)
        sums = np.stack([np.bincount(cells[mask], weights=deltas[mask, j], minlength=nf*nd)
                         for j in range(k)], axis=-1).reshape(nf, nd, k)
        aggregates[name] = counts, sums
    rng = np.random.default_rng(seed)
    output = {name: [] for name in groups}
    # Fixed per-replicate RNG order makes chunk size a memory detail, not a new draw.
    for start in range(0, replicates, 64):
        fw, dw = [], []
        for _ in range(min(64, replicates-start)):
            f = rng.multinomial(nf, np.full(nf, 1/nf))
            d = np.zeros(nd)
            for block in np.unique(dayfold):
                ids = np.flatnonzero(dayfold == block)
                d[ids] = rng.multinomial(len(ids), np.full(len(ids), 1/len(ids)))
            fw.append(np.ones(nf) if mode == "calendar" else f)
            dw.append(np.ones(nd) if mode == "family" else d)
        fw, dw = np.asarray(fw), np.asarray(dw)
        for name, (counts, sums) in aggregates.items():
            denominator = np.einsum("bf,fd,bd->b", fw, counts, dw, optimize=True)
            if np.any(denominator <= 0):
                raise ValueError("Empty-weight replicate; uncertainty gate incomplete")
            numerator = np.einsum("bf,fdk,bd->bk", fw, sums, dw, optimize=True)
            output[name].append(numerator/denominator[:, None])
    return {name: np.concatenate(parts) for name, parts in output.items()}


def breadth(family, day, fold, exposed):
    failures = []
    if len(np.unique(family)) < 30:
        failures.append("fewer_than_30_families")
    if len(np.unique(day)) < 28:
        failures.append("fewer_than_28_days")
    if len(np.unique(family[exposed])) < 20:
        failures.append("fewer_than_20_exposed_families")
    blocks = np.unique(fold)
    if len(blocks) != 5:
        failures.append("not_five_outer_time_blocks")
    if any(len(np.unique(family[exposed & (fold == b)])) < 5 for b in blocks):
        failures.append("fewer_than_5_exposed_families_in_time_fold")
    return failures


def evaluate(y, predictions, family, day, fold, exposed, subgroups, *,
             source_gate_passed=False, software_gate_passed=False, replicates=5000):
    """Fail closed before label access when source/software authorization is absent.

    `subgroups` contains the predeclared venue and broad-category masks. Eligibility
    is exposure/family based, never selected from subgroup outcome performance.
    """
    if not source_gate_passed or not software_gate_passed:
        return {"status": "incomplete", "reason": "source_or_software_gate_failed",
                "labels_accessed": False, "promote_news": False}
    family, day, fold, exposed = map(np.asarray, (family, day, fold, exposed))
    n = len(family)
    if (any(a.shape != (n,) for a in (day, fold, exposed)) or exposed.dtype != bool):
        raise ValueError("Invalid row metadata")
    failures = breadth(family, day, fold, exposed)
    if failures:
        return {"status": "incomplete", "reason": failures, "labels_accessed": False,
                "promote_news": False}
    eligible = {}
    for name, mask in subgroups.items():
        mask = np.asarray(mask)
        if mask.shape != (n,) or mask.dtype != bool or name == "all":
            raise ValueError("Invalid predeclared subgroup")
        if (np.count_nonzero(mask & exposed) >= 1000 and
                len(np.unique(family[mask & exposed])) >= 20):
            eligible[name] = mask
    y = np.asarray(y, float)
    if y.shape != (n,) or not np.isin(y, [0, 1]).all():
        raise ValueError("Required labels invalid")
    required = {"linear", "nonlinear", "context", "timing", "timing_matched", "news"}
    if set(predictions) != required:
        raise ValueError("All six prespecified arms required, no row/model substitution")
    losses, briers, metrics = {}, {}, {}
    for name, values in predictions.items():
        p = np.asarray(values, float)
        if p.shape != (n,) or not np.isfinite(p).all() or np.any((p < 0) | (p > 1)):
            raise ValueError("Invalid prediction probabilities")
        if name not in {"linear", "nonlinear"} and not np.array_equal(
                p[~exposed], np.asarray(predictions["nonlinear"])[~exposed]):
            raise ValueError("Unexposed invariant failed")
        p = np.clip(p, 1e-12, 1-1e-12)
        losses[name], briers[name] = ll(y, p), (p-y)**2
        metrics[name] = {"log_loss": float(losses[name].mean()),
                         "brier": float(briers[name].mean()),
                         "ap": float(average_precision_score(y, p)) if y.any() else None}
    contrasts = np.column_stack([losses["linear"]-losses["nonlinear"],
        losses["nonlinear"]-losses["news"], losses["timing_matched"]-losses["news"],
        briers["nonlinear"]-briers["news"]])
    try:
        draws = bootstrap(contrasts, family, day, fold, eligible, replicates)
        intervals = np.quantile(draws["all"], [.025, .975], axis=0)
        sensitivity = {mode: np.quantile(bootstrap(contrasts, family, day, fold,
            replicates=replicates, mode=mode)["all"], [.025, .975], axis=0).tolist()
            for mode in ("family", "calendar")}
    except ValueError as error:
        return {"status": "incomplete", "reason": str(error), "promote_news": False,
                "labels_accessed": True, "metrics": metrics}
    means, lower = contrasts.mean(axis=0), intervals[0]
    subgroup_bounds = {g: float(np.quantile(draws[g][:, 1], .05/len(eligible))) for g in eligible}
    gates = {"market_replication": bool(means[0] >= .001 and lower[0] > 0),
             "news_vs_market": bool(means[1] >= .001 and lower[1] > 0),
             "content_attribution": bool(lower[2] > 0),
             "brier_noninferiority": bool(lower[3] > -.0005),
             "subgroup_guardrail": all(lb > -.001 for lb in subgroup_bounds.values())}
    passed = all(gates.values())
    return {"status": "eligible_for_candidate_freeze" if passed else "negative_stop_news_branch",
            "promote_news": passed, "labels_accessed": True, "metrics": metrics,
            "contrast_order": ["market_replication", "news_vs_market", "content_attribution", "brier"],
            "mean_improvements": means.tolist(), "intervals": intervals.tolist(), "gates": gates,
            "subgroup_lower_bounds": subgroup_bounds,
            "subgroup_assessment": "assessed" if eligible else "not_assessable_pooled_claim_only",
            "sensitivity_intervals": sensitivity,
            "exposed_improvements": contrasts[exposed].mean(axis=0).tolist(),
            "market_balanced_improvements": np.mean([
                contrasts[family == f].mean(axis=0) for f in np.unique(family)], axis=0).tolist(),
            "time_fold_improvements": {str(b): contrasts[fold == b].mean(axis=0).tolist()
                                       for b in np.unique(fold)}}
