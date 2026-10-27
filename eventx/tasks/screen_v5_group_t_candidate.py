"""Synthetic-only grouped-t feasibility; not a V5 protocol amendment.

Tests disjoint family/time diagonal groups. This discards off-diagonal cells and
requires independent approximately Gaussian group estimates: NOT the existing
all-row crossed bootstrap estimand/estimator. No automatic method promotion.
"""

from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path

import numpy as np
from scipy.stats import t

from eventx.tasks.validate_v5_revision_v1_1 import simulate, SCENARIOS
from eventx.v5_corrected.uncertainty_v1_1 import wilson

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT/'data/v5/group_t_candidate_20260910'


def group_interval(values, family, day, groups=4):
    """Preassigned family modulo groups × chronological calendar partitions."""
    values, family, day = map(np.asarray, (values, family, day))
    if values.ndim != 1 or not np.isfinite(values).all():
        raise ValueError('Invalid values')
    days = np.unique(day)
    if len(days) < 2*groups or np.any(np.diff(days) != 1):
        raise ValueError('Insufficient/noncontiguous calendar')
    means, used = [], 0
    for g, dates in enumerate(np.array_split(days, groups)):
        mask = (family % groups == g) & np.isin(day, dates)
        if not mask.any():
            raise ValueError('Empty diagonal group')
        means.append(values[mask].mean())
        used += int(mask.sum())
    means = np.asarray(means)
    half = t.ppf(.975, groups-1)*means.std(ddof=1)/np.sqrt(groups)
    return float(means.mean()-half), float(means.mean()+half), used/len(values)


def main():
    OUT.mkdir(parents=True, exist_ok=False)
    config = {'groups': 4, 'calendar_days': [35, 140], 'trials': 1000,
              'seed': 2026091012, 'scenarios': list(SCENARIOS),
              'method_selected': False, 'scope_change_approved': False,
              'screen_not_independent_certification': True,
              'bootstrap_draws': 'not applicable: analytical Student-t critical value'}
    (OUT/'config.json').write_text(json.dumps(config, indent=2)+'\n')
    rows = []
    for nd in config['calendar_days']:
        for si, scenario in enumerate(SCENARIOS):
            cover = positive = 0
            widths, used = [], []
            for trial in range(config['trials']):
                x, family, day, _ = simulate(scenario, nd, config['seed']+nd*100000+si*1000+trial)
                lb, ub, fraction = group_interval(x, family, day)
                cover += int(lb <= 0 <= ub)
                positive += int(lb > 0)
                widths.append(ub-lb)
                used.append(fraction)
            row = {'days': nd, 'scenario': scenario, 'coverage': cover/config['trials'],
                   'coverage_wilson95': wilson(cover, config['trials']),
                   'false_positive_lower': positive/config['trials'],
                   'false_positive_wilson95': wilson(positive, config['trials']),
                   'mean_width': float(np.mean(widths)), 'mean_rows_used_fraction': float(np.mean(used))}
            rows.append(row)
            print(json.dumps(row), flush=True)
    report = {'created_at': datetime.now(timezone.utc).isoformat(), 'config': config,
              'results': rows, 'certified': False, 'new_research_labels_read': False,
              'limitations': ['Group independence/Gaussianity not established by group assignment',
                             'Diagonal groups discard most rows and average groups, not the current all-row estimator',
                             'These loss-process screens are not full fitted-pipeline or promotion power']}
    (OUT/'report.json').write_text(json.dumps(report, indent=2)+'\n')
    paths = [Path(__file__), ROOT/'eventx/tasks/validate_v5_revision_v1_1.py',
             ROOT/'eventx/v5_corrected/uncertainty_v1_1.py', *sorted(OUT.iterdir())]
    (OUT/'manifest.json').write_text(json.dumps({'artifacts': [
        {'path': str(p.relative_to(ROOT)), 'sha256': hashlib.sha256(p.read_bytes()).hexdigest()}
        for p in paths]}, indent=2)+'\n')


if __name__ == '__main__':
    main()
