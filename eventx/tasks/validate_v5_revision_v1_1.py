"""Versioned SYNTHETIC screen and read-only source-status inventory.

No real labels/prices/predictions loaded; no network; never certifies inference.
"""

from datetime import datetime, timezone
import hashlib
import io
import json
from pathlib import Path
import unittest

import numpy as np
from threadpoolctl import threadpool_limits

from eventx.v5_corrected.uncertainty_v1_1 import moving_block_draws, wilson

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT/'data/v5/revision_v1_1_20260910'
SCENARIOS = ('iid', 'family_day', 'ar05', 'ar09', 'regime', 'sparse_unbalanced')
BLOCKS = (3, 7, 14)
SEED = 11092026


def simulate(scenario, nd, seed):
    rng = np.random.default_rng(seed)
    nf = 30
    signal = rng.normal(0, .02, (nf, nd))
    if scenario != 'iid':
        signal += rng.normal(0, .003, (nf, 1))
    if scenario == 'family_day':
        signal += rng.normal(0, .006, (1, nd))
    if scenario in ('ar05', 'ar09', 'sparse_unbalanced'):
        rho = .5 if scenario == 'ar05' else .9
        process = np.empty(nd)
        process[0] = rng.normal(0, .01)
        for d in range(1, nd):
            process[d] = rho*process[d-1]+rng.normal(0, .01*np.sqrt(1-rho*rho))
        signal += process[None, :]
    if scenario == 'regime':
        signal += np.repeat(rng.normal(0, .01, 3), (nd+2)//3)[:nd][None, :]
    counts = np.ones((nf, nd), dtype=int)
    exposed_fraction = None
    if scenario == 'sparse_unbalanced':
        # Count imbalance and exposure are independent of zero-mean outcomes.
        counts = np.broadcast_to(rng.integers(1, 9, (nf, 1)), (nf, nd)).copy()
        exposed = rng.random((nf, nd)) < .04
        exposed_fraction = float(np.sum(exposed*counts)/counts.sum())
        signal *= exposed
    f, d = np.repeat(np.arange(nf), nd), np.tile(np.arange(nd), nf)
    return (np.repeat(signal.ravel(), counts.ravel()), np.repeat(f, counts.ravel()),
            np.repeat(d, counts.ravel()), exposed_fraction)


def screen(trials=100, replicates=1000):
    records = []
    for nd in (35, 140):
        for si, scenario in enumerate(SCENARIOS):
            accum = {b: {'covered': 0, 'false_positive_lower': 0, 'failed_trials': 0,
                         'widths': [], 'exposure': []} for b in BLOCKS}
            for trial in range(trials):
                x, family, day, exposure = simulate(scenario, nd, SEED+nd*100000+si*1000+trial)
                for b in BLOCKS:
                    state = accum[b]
                    try:
                        draws = moving_block_draws(x, family, day, block_days=b,
                            replicates=replicates, seed=SEED+trial)[:, 0]
                        lb, ub = np.quantile(draws, [.025, .975])
                    except ValueError:
                        state['failed_trials'] += 1
                        continue
                    state['covered'] += int(lb <= 0 <= ub)
                    state['false_positive_lower'] += int(lb > 0)
                    state['widths'].append(float(ub-lb))
                    if exposure is not None:
                        state['exposure'].append(exposure)
            for b, state in accum.items():
                records.append({'days': nd, 'scenario': scenario, 'block_days': b,
                    'trials': trials, 'failed_trials': state['failed_trials'],
                    'coverage': state['covered']/trials,
                    'coverage_wilson95': wilson(state['covered'], trials),
                    'false_positive_lower_rate': state['false_positive_lower']/trials,
                    'false_positive_wilson95': wilson(state['false_positive_lower'], trials),
                    'mean_width': float(np.mean(state['widths'])) if state['widths'] else None,
                    'mean_exposure_fraction': float(np.mean(state['exposure'])) if state['exposure'] else None})
            print(f'Synthetic screen finished: days={nd} scenario={scenario}', flush=True)
    return {'status': 'development_screen_only', 'certified': False,
            'selected_method': None, 'full_hierarchy_power': False,
            'trials_per_cell': trials, 'replicates_per_trial': replicates,
            'seed': SEED, 'records': records,
            'limitations': ['Hypothetical loss processes, not fitted models or cohort-specific power',
                           'Short/regime-dependent calendars may defeat every candidate',
                           'Independent validation seeds and 1000-trial/5000-draw audit still required']}


def main():
    # Verify frozen non-outcome code and earlier evidence before producing new work.
    checked = 0
    manifests = ['data/v5/experiment_implementation_20260910/manifest.json',
                 'data/v5/recovery_summary_20260910/manifest.json',
                 'eventx/release/v4/holdout_implementation_manifest.json']
    for name in manifests:
        manifest = json.loads((ROOT/name).read_text())
        for entry in manifest['artifacts']:
            path = ROOT/entry['path']
            if hashlib.sha256(path.read_bytes()).hexdigest() != entry['sha256']:
                raise RuntimeError(f'Prior hash conflict: {entry["path"]}')
            checked += 1
    OUT.mkdir(parents=True, exist_ok=False)
    modules = ['test_v5_revision_v1_1', 'test_v5_experiment_v1', 'test_v5_content_integration',
               'test_v5_label_blind_contract', 'test_v5_corrected_pipeline',
               'test_algorithm_audit', 'test_v5_source_readiness', 'test_v5_recovery_requests']
    suite = unittest.TestSuite(unittest.defaultTestLoader.loadTestsFromName('eventx.tasks.'+m) for m in modules)
    buffer = io.StringIO()
    with threadpool_limits(limits=2):
        result = unittest.TextTestRunner(stream=buffer, verbosity=2).run(suite)
        (OUT/'tests.txt').write_text(buffer.getvalue())
        if not result.wasSuccessful():
            raise RuntimeError('Tests failed; retained output; no certification')
        print(f'Passed {result.testsRun} synthetic/regression tests', flush=True)
        screens = screen()
    (OUT/'uncertainty_screen.json').write_text(json.dumps(screens, indent=2)+'\n')
    recovery = json.loads((ROOT/'data/v5/recovery_summary_20260910/report.json').read_text())
    # Source-only review queue: no labels, prices or sealed payloads.
    groups = set()
    counts = {'markets': 0, 'approved_families': 0, 'missing_candidate_ids': 0}
    approved = set()
    with (ROOT/'data/v5/recovery_summary_20260910/candidate_family_queue.jsonl').open() as handle:
        for line in handle:
            row = json.loads(line)
            counts['markets'] += 1
            if row.get('candidate_family_id'):
                groups.add(row['candidate_family_id'])
            else:
                counts['missing_candidate_ids'] += 1
            if row.get('family_verified') and row.get('approved_family_id'):
                approved.add(row['approved_family_id'])
    counts['approved_families'] = len(approved)
    counts['candidate_groups'] = len(groups)
    status = {'created_at': datetime.now(timezone.utc).isoformat(),
              'status': 'revision_implemented_real_data_blocked',
              'tests_run': result.testsRun, 'test_failures': len(result.failures),
              'test_errors': len(result.errors), 'prior_manifest_records_verified': checked,
              'hash_mismatches': 0, 'family_queue': counts,
              'historical_versions_certified': recovery['snapshot_version_history_certified'],
              'news_intervals_reconciled': recovery['news_intervals_reconciled'],
              'uncertainty_certified': False, 'candidate_frozen': False,
              'real_labels_accessed': False, 'research_data_fetched': False,
              'next_gates': ['independent uncertainty validation', 'source-version and news reconciliation',
                            'final family approval', 'unopened scope and exact split freeze',
                            'production target adapter/serialization/one-shot runner', 'full-hierarchy power']}
    (OUT/'report.json').write_text(json.dumps(status, indent=2)+'\n')
    artifacts = [ROOT/'eventx/release/v5/PROTOCOL_V1_1.md', Path(__file__),
                 ROOT/'eventx/tasks/test_v5_revision_v1_1.py',
                 *sorted((ROOT/'eventx/v5_corrected').glob('*v1_1.py')),
                 *sorted(OUT.iterdir())]
    (OUT/'manifest.json').write_text(json.dumps({'status': 'synthetic_revision_evidence_not_research_freeze',
        'artifacts': [{'path': str(p.relative_to(ROOT)), 'sha256': hashlib.sha256(p.read_bytes()).hexdigest()}
                      for p in artifacts]}, indent=2)+'\n')
    print(json.dumps(status, indent=2), flush=True)


if __name__ == '__main__':
    main()
