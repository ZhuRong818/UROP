"""Fixed-model seven-day replication, including forecasts with missing outcomes."""
import argparse
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
import json
import os
from pathlib import Path

import joblib
import numpy as np
import pyarrow as pa
import pyarrow.parquet as pq

from eventx.tasks.discover_v7_direct_pilot_20261022 import REPO_ROOT, now, sha, write, verify_originals
from eventx.tasks.run_v7_archive_week_pilot_20261025 import EX, verify
from eventx.tasks.research_v7_change_probability_20261025 import FEATURES, ACTIVITY, metrics
from eventx.tasks.run_v7_family_training_20261025_v02 import family_map, family_macro
from eventx.v7.calibration_transport_20261025 import build_panel
from eventx.v7.family_capture_20261025_v02 import fetch

BASE = REPO_ROOT / 'data/v7/week_replication_20261025'
REL = REPO_ROOT / 'eventx/release/v7/week_replication_20261025'
PRIOR = REPO_ROOT / 'data/v7/family_training_20261025_v02'
LEGACY = REPO_ROOT / 'data/v7/change_probability_20261025/development/frozen_models.joblib'
DATES = [f'2026-05-{d:02d}' for d in range(13, 20)]
MODELS = ['global_rate', 'market_rate', 'activity_logit', 'row_hgb7', 'legacy_hgb7']
RETRYABLE = {'ReadTimeout', 'ConnectTimeout', 'ReadError', 'RemoteProtocolError', 'ConnectError'}


def freeze(folder, extra=()):
    files = [p for p in folder.rglob('*') if p.is_file() and p.name != 'manifest.json'] + list(extra)
    write(folder / 'manifest.json', {'files': {str(p.relative_to(REPO_ROOT)): sha(p) for p in files}})


def load_models():
    bundle = joblib.load(PRIOR / 'development/frozen_models.joblib')
    assert bundle['selected'] == 'row_hgb7' and bundle['features'] == FEATURES
    models = {n: bundle['models'][n] for n in MODELS if n != 'legacy_hgb7'}
    models['legacy_hgb7'] = joblib.load(LEGACY)['models']['hgb7']
    return models


def infer(model, rows):
    """Inference deliberately never reads labels or endpoint eligibility."""
    if model['name'] == 'market_rate':
        p = np.asarray([model['rates'].get(r['market_id'], model['rate']) for r in rows])
    elif model['estimator'] is None:
        p = np.full(len(rows), model['rate'])
    elif rows:
        x = np.asarray([r['features'] for r in rows], dtype=float)
        if model['name'] == 'activity_logit':
            x = x[:, ACTIVITY]
        p = model['estimator'].predict_proba(x)[:, 1]
    else:
        p = np.array([], dtype=float)
    return np.clip(p, 1e-6, 1 - 1e-6)


def missing_bounds(targets, selected, baseline):
    """Sharp label-only bounds on mean baseline-minus-selected log loss.

    These are deterministic partial-identification bounds, not confidence intervals.
    Predictions and the set of current-valid decisions are fixed.
    """
    if not len(targets):
        return {'n': 0, 'observed': 0, 'missing': 0, 'lower': None, 'upper': None}
    known = np.asarray([y is not None for y in targets], dtype=bool)
    y = np.asarray([0 if v is None else int(v) for v in targets])
    d0 = np.log1p(-selected) - np.log1p(-baseline)
    d1 = np.log(selected) - np.log(baseline)
    observed = np.where(y == 1, d1, d0)[known].sum()
    return {'n': len(targets), 'observed': int(known.sum()), 'missing': int((~known).sum()),
            'lower': float((observed + np.minimum(d0, d1)[~known].sum()) / len(targets)),
            'upper': float((observed + np.maximum(d0, d1)[~known].sum()) / len(targets))}


def verify_setup():
    verify_originals()
    verify(REL / 'implementation_manifest.json')
    verify(PRIOR / 'development/manifest.json')
    verify(PRIOR / 'cohort/manifest.json')
    return json.loads((PRIOR / 'cohort/cohorts.json').read_text())


def capture():
    co = verify_setup()
    selected = co['development50'] + co['unseen10']
    out = BASE / 'source'
    if (out / 'capture_manifest.json').exists():
        raise RuntimeError('Capture already finalized; do not rerun')
    out.mkdir(parents=True, exist_ok=True)
    excluded = set(json.loads(EX.read_text()))
    assert not {m['market_id'] for m in selected} & excluded
    hours = [d + f'T{h:02d}' for d in DATES for h in range(24)]
    all_receipts = []
    chosen = {}
    pending = hours
    for attempt in [1, 2]:
        folder = out / f'attempt_{attempt}'
        (folder / 'hours').mkdir(parents=True, exist_ok=True)
        with ThreadPoolExecutor(max_workers=2) as pool:
            futures = [pool.submit(fetch, h, selected, excluded, folder) for h in pending]
            for future in as_completed(futures):
                rec = future.result()
                tagged = dict(rec, attempt=attempt)
                all_receipts.append(tagged)
                chosen[rec['hour']] = tagged
                write(out / 'attempt_receipts.json', all_receipts)
                status = {'at': now().isoformat(), 'phase': 'capturing', 'pid': os.getpid(),
                          'attempt': attempt, 'hours_completed': len(chosen), 'hours_planned': len(hours),
                          'successful_files': sum(r['complete'] for r in chosen.values()),
                          'archive_bytes': sum(r['archive_bytes'] for r in all_receipts)}
                write(out / 'status.json', status)
                if len(all_receipts) % 12 == 0 or not rec['complete']:
                    print(json.dumps(status), flush=True)
        pending = [h for h in hours if not chosen[h]['complete'] and chosen[h].get('error') in RETRYABLE]
        if not pending:
            break
    # A successful retry supersedes only a transport failure. Both attempts remain frozen.
    (out / 'hours').mkdir(exist_ok=False)
    for hour, rec in chosen.items():
        (out / 'hours' / hour).symlink_to(Path('..') / f"attempt_{rec['attempt']}" / 'hours' / hour,
                                        target_is_directory=True)
    write(out / 'file_receipts.json', [chosen[h] for h in hours])
    report = {'at': now().isoformat(), 'phase': 'captured', 'files': len(hours),
              'successful_files': sum(r['complete'] for r in chosen.values()),
              'attempts': len(all_receipts), 'failed_attempts': sum(not r['complete'] for r in all_receipts),
              'recovered_hours': sum(r['attempt'] == 2 and r['complete'] for r in chosen.values()),
              'archive_bytes': sum(r['archive_bytes'] for r in all_receipts),
              'events': sum(r.get('retained_rows', 0) for r in chosen.values() if r['complete']),
              'excluded_pre_holdout_rows_decoded': sum(r.get('excluded_pre_holdout_rows_decoded', 0) for r in all_receipts),
              'protected_period_rows_read': 0,
              'missing_hours': [h for h in hours if not chosen[h]['complete']]}
    write(out / 'capture_report.json', report)
    write(out / 'status.json', report)
    files = [out / 'capture_report.json', out / 'file_receipts.json', out / 'attempt_receipts.json',
             REL / 'implementation_manifest.json'] + list(out.glob('attempt_*/hours/*/manifest.json'))
    write(out / 'capture_manifest.json', {'files': {str(p.relative_to(REPO_ROOT)): sha(p) for p in files}})
    print(json.dumps(report), flush=True)


def evaluate():
    co = verify_setup()
    verify(BASE / 'source/capture_manifest.json')
    out = BASE / 'evaluation'
    out.mkdir(exist_ok=False)
    write(out / 'consumption_receipt.json', {'at': now().isoformat(), 'status': 'started', 'dates': DATES})
    try:
        ledger = build_panel(BASE / 'source', DATES, co['development50'] + co['unseen10'])
        heldout = {m['market_id'] for m in co['unseen10']}
        for r in ledger:
            r['cohort'] = 'training_excluded10' if r['market_id'] in heldout else 'development50'
        assert len(ledger) == 115920
        pq.write_table(pa.Table.from_pylist(ledger), out / 'grid_ledger.parquet')
        issued = [r for r in ledger if r['current_valid']]
        models = load_models()
        ps = {n: infer(models[n], issued) for n in MODELS}
        # Preserve null outcomes; forecasts exist before filtering by outcome availability.
        predictions = [{'market_id': r['market_id'], 'date': r['date'], 'decision_at': r['decision_at'],
                        'cohort': r['cohort'], 'target': r['target'], 'endpoint_eligible': r['endpoint_eligible'],
                        'strict_eligible': r['strict_eligible'], **{n: float(p[i]) for n, p in ps.items()}}
                       for i, r in enumerate(issued)]
        pq.write_table(pa.Table.from_pylist(predictions), out / 'issued_predictions.parquet')
        observed = np.asarray([r['endpoint_eligible'] for r in issued], dtype=bool)
        # y's placeholder is masked from every score and never exported as a label.
        y = np.asarray([r['target'] if r['endpoint_eligible'] else 0 for r in issued], dtype=int)
        fmap = family_map(co)
        results = {}
        groups = []
        for c in ['development50', 'training_excluded10', 'all']:
            population = np.asarray([c == 'all' or r['cohort'] == c for r in issued], dtype=bool)
            current_rows = [r for r, keep in zip(issued, population) if keep]
            primary = population & observed
            rr = [r for r, keep in zip(issued, primary) if keep]
            masks = {'primary': primary,
                     'strict': primary & np.asarray([r['strict_eligible'] for r in issued], dtype=bool),
                     'nonoverlap': primary & np.asarray([r['t'] % 1800 == 0 for r in issued], dtype=bool)}
            results[c] = {'scheduled': sum(c == 'all' or r['cohort'] == c for r in ledger),
                          'issued': int(population.sum()), 'observed': int(primary.sum()),
                          'missing_outcomes': int((population & ~observed).sum()),
                          'contributing_contracts': len({r['market_id'] for r in rr}),
                          'primary': {n: {**metrics(y[primary], p[primary]),
                                         'family_macro_log_loss': family_macro(rr, y[primary], p[primary], fmap)}
                                      for n, p in ps.items()},
                          'strict': {n: metrics(y[masks['strict']], p[masks['strict']]) for n, p in ps.items()},
                          'nonoverlap': {n: metrics(y[masks['nonoverlap']], p[masks['nonoverlap']]) for n, p in ps.items()},
                          'missing_outcome_bounds': {n: missing_bounds([r['target'] for r in current_rows],
                                                                      ps['row_hgb7'][population], ps[n][population])
                                                     for n in MODELS if n != 'row_hgb7'}}
            for field, values in [('date', DATES), ('market_id', sorted({r['market_id'] for r in ledger}))]:
                for value in values:
                    mask = population & np.asarray([r[field] == value for r in issued], dtype=bool)
                    scored = mask & observed
                    if mask.any():
                        groups.append({'cohort': c, 'field': field, 'value': value,
                                       'issued': int(mask.sum()), 'observed': int(scored.sum()),
                                       'models': {n: metrics(y[scored], p[scored]) for n, p in ps.items()}})
        calibration = []
        for c in ['development50', 'training_excluded10']:
            cm = observed & np.asarray([r['cohort'] == c for r in issued], dtype=bool)
            for n, p in ps.items():
                for lo, hi in zip([0, .05, .1, .2, .4, .6, .8], [.05, .1, .2, .4, .6, .8, 1.00001]):
                    mask = cm & (p >= lo) & (p < hi)
                    calibration.append({'cohort': c, 'model': n, 'lo': lo, 'hi': min(hi, 1), 'n': int(mask.sum()),
                                        'mean_prediction': float(p[mask].mean()) if mask.any() else None,
                                        'observed_rate': float(y[mask].mean()) if mask.any() else None})
        write(out / 'groups.json', groups)
        write(out / 'calibration_bins.json', calibration)
        result = {'at': now().isoformat(), 'selected': 'row_hgb7', 'dates': DATES, 'cohorts': results,
                  'model_refit': False, 'new_contract_identities': False, 'prospective': False,
                  'news_tested': False, 'automatic_promotion': False, 'significance_claim': False,
                  'missing_bounds_are_confidence_intervals': False}
        write(out / 'result.json', result)
        write(out / 'consumption_receipt.json', {'at': now().isoformat(), 'status': 'completed', 'dates': DATES})
        print(json.dumps(result), flush=True)
    except Exception as e:
        write(out / 'failure.json', {'at': now().isoformat(), 'error': type(e).__name__, 'message': str(e)[:240]})
        raise
    finally:
        freeze(out, [REL / 'implementation_manifest.json', BASE / 'source/capture_manifest.json'])


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('phase', choices=['capture', 'evaluate'])
    args = parser.parse_args()
    {'capture': capture, 'evaluate': evaluate}[args.phase]()
