"""Frozen quote-change booster on never-used contracts over the unopened week June 8-14.

Phases (each runs once): select -> capture -> evaluate.
Selection reads only identity/event-type/clock columns from June 7 hours (already
consumed block, before the test week) plus current Gamma metadata. No price, quote or
outcome column is read before the cohort is frozen.
"""
import argparse
from collections import Counter, defaultdict
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path

import httpx
import numpy as np
import pyarrow as pa
import pyarrow.compute as pc
import pyarrow.parquet as pq

from eventx.tasks.discover_v7_direct_pilot_20261022 import REPO_ROOT, now, sha, write, verify_originals
from eventx.tasks.run_v7_archive_week_pilot_20261025 import COLS, EX, verify
from eventx.tasks.research_v7_change_probability_20261025 import metrics
from eventx.tasks.run_v7_week_replication_20261025 import MODELS, RETRYABLE, infer, load_models, missing_bounds, freeze
from eventx.v7.archive_ranges_20261024 import read_columns, RangeStore
from eventx.v7.calibration_transport_20261025 import build_panel
from eventx.v7.family_capture_20261025_v02 import fetch

BASE = REPO_ROOT / 'data/v7/new_identity_test_20261026'
REL = REPO_ROOT / 'eventx/release/v7/new_identity_test_20261026'
OLD_COHORT = REPO_ROOT / 'data/v7/family_training_20261025_v02/cohort'
DATES = [f'2026-06-{d:02d}' for d in range(8, 15)]
IDENTITY_HOURS = ['2026-06-07T12', '2026-06-07T13']
ID_RANGE = ('0x10', '0x18')  # disjoint from every earlier cohort ID (all < 0x0a)
TARGET_N = 40
SALT = 'new-identity-v1:'


def verify_setup():
    verify_originals()
    verify(REL / 'implementation_manifest.json')
    verify(OLD_COHORT / 'manifest.json')
    return json.loads((OLD_COHORT / 'cohorts.json').read_text())


def in_range(cid):
    return ID_RANGE[0] <= cid[:4] < ID_RANGE[1]


def select():
    old = verify_setup()
    out = BASE / 'cohort'
    out.mkdir(parents=True, exist_ok=False)
    previous = old['development50'] + old['unseen10']
    seen_events = {e['id'] for m in previous for e in m['events']}
    excluded = set(json.loads(EX.read_text())) | {m['market_id'] for m in previous}
    store = RangeStore(out / 'identity_ranges', 32 * 1024 * 1024)
    sets, read_groups = [], {}
    try:
        for hour in IDENTITY_HOURS:
            url = 'https://r2v2.pmxt.dev/polymarket_orderbook_' + hour + '.parquet'
            meta, _ = store.metadata(url)
            ix = meta.schema.names.index('market')
            groups = [i for i in range(meta.num_row_groups)
                      if meta.row_group(i).column(ix).statistics.max[:4].decode() >= ID_RANGE[0]
                      and meta.row_group(i).column(ix).statistics.min[:4].decode() < ID_RANGE[1]]
            if len(groups) > 6:
                raise RuntimeError('Identity group cap exceeded')
            read_groups[hour] = groups
            union = set()
            start = datetime.fromisoformat(hour + ':00:00+00:00').timestamp()
            for g in groups:
                t = read_columns(store, url, meta, g, COLS[:5], 'june7_identity_event_clocks_only')
                lo = pc.min(t['timestamp_received']).as_py().timestamp()
                hi = pc.max(t['timestamp_received']).as_py().timestamp()
                if not start <= lo <= hi < start + 3600:
                    raise RuntimeError('Identity clock outside approved hour')
                books = t.filter(pc.equal(t['event_type'], 'book'))
                counts = Counter(x.decode() for x in books['market'].to_pylist())
                union |= {c for c, n in counts.items() if n >= 2 and in_range(c) and c not in excluded}
            sets.append(union)
    finally:
        store.client.close()
        write(out / 'identity_read_receipt.json', {'at': now().isoformat(), 'bytes': store.total,
                                                  'groups': read_groups, 'economic_columns_read': False})
    candidates = sorted(set.intersection(*sets), key=lambda c: hashlib.sha256((SALT + c).encode()).hexdigest())
    write(out / 'candidates_before_metadata.json', {'candidates': candidates})
    chosen, receipts = [], []
    lo_t, hi_t = datetime(2026, 6, 8, tzinfo=timezone.utc), datetime(2026, 6, 15, tzinfo=timezone.utc)
    with httpx.Client(timeout=30) as client:
        for cid in candidates:
            rec = {'market_id': cid, 'requests': []}
            try:
                for query in [{'condition_ids': cid}, {'condition_ids': cid, 'closed': 'true'}]:
                    r = client.get('https://gamma-api.polymarket.com/markets', params=query)
                    rec['requests'].append({'at': now().isoformat(), 'query': query, 'status': r.status_code,
                                            'sha256': hashlib.sha256(r.content).hexdigest()})
                    r.raise_for_status()
                    raw = r.json()
                    if raw != []:
                        break
                if not isinstance(raw, list) or len(raw) != 1 or raw[0].get('conditionId') != cid:
                    raise ValueError('identity')
                m = raw[0]
                tokens, outcomes = m.get('clobTokenIds'), m.get('outcomes')
                tokens = json.loads(tokens) if isinstance(tokens, str) else tokens
                outcomes = json.loads(outcomes) if isinstance(outcomes, str) else outcomes
                events = [{k: e.get(k) for k in ['id', 'title', 'slug']} for e in m.get('events', [])]
                ev = {e['id'] for e in events if e['id']}
                keep = {k: m.get(k) for k in ['question', 'description', 'startDate', 'endDate', 'active', 'closed', 'acceptingOrders']}
                keep.update(market_id=cid, token_ids=tokens, outcomes=outcomes, events=events)
                rec['metadata'] = keep
                start = datetime.fromisoformat(m['startDate'].replace('Z', '+00:00'))
                end = datetime.fromisoformat(m['endDate'].replace('Z', '+00:00'))
                # One contract per event; no event shared with any earlier cohort.
                valid = (outcomes == ['Yes', 'No'] and isinstance(tokens, list) and len(tokens) == 2
                         and bool(m.get('description')) and bool(ev) and not ev & seen_events
                         and start < lo_t and end > hi_t)
                rec['selected'] = bool(valid)
                if valid:
                    chosen.append(keep)
                    seen_events |= ev
            except Exception as e:
                rec['error'] = type(e).__name__
            receipts.append(rec)
            write(out / 'metadata_receipts.json', receipts)
            if len(chosen) == TARGET_N:
                break
    cohort = {'at': now().isoformat(), 'new': chosen, 'selection_before_prices': True,
              'candidates': len(candidates), 'lookups': len(receipts)}
    write(out / 'cohort.json', cohort)
    freeze(out, [REL / 'implementation_manifest.json'])
    print(json.dumps({'candidates': len(candidates), 'lookups': len(receipts), 'selected': len(chosen),
                      'questions': [m['question'] for m in chosen]}, indent=1), flush=True)


def load_cohort():
    verify(BASE / 'cohort/manifest.json')
    return json.loads((BASE / 'cohort/cohort.json').read_text())['new']


def capture():
    verify_setup()
    selected = load_cohort()
    out = BASE / 'source'
    if (out / 'capture_manifest.json').exists():
        raise RuntimeError('Capture already finalized; do not rerun')
    out.mkdir(parents=True, exist_ok=True)
    excluded = set(json.loads(EX.read_text()))
    hours = [d + f'T{h:02d}' for d in DATES for h in range(24)]
    all_receipts, chosen, pending = [], {}, hours
    for attempt in [1, 2]:
        folder = out / f'attempt_{attempt}'
        (folder / 'hours').mkdir(parents=True, exist_ok=True)
        with ThreadPoolExecutor(max_workers=2) as pool:
            for future in as_completed([pool.submit(fetch, h, selected, excluded, folder) for h in pending]):
                rec = dict(future.result(), attempt=attempt)
                all_receipts.append(rec)
                chosen[rec['hour']] = rec
                write(out / 'attempt_receipts.json', all_receipts)
                write(out / 'status.json', {'at': now().isoformat(), 'phase': 'capturing', 'pid': os.getpid(),
                                            'attempt': attempt, 'hours_completed': len(chosen),
                                            'successful_files': sum(r['complete'] for r in chosen.values())})
        pending = [h for h in hours if not chosen[h]['complete'] and chosen[h].get('error') in RETRYABLE]
        if not pending:
            break
    (out / 'hours').mkdir(exist_ok=False)
    for hour, rec in chosen.items():
        (out / 'hours' / hour).symlink_to(Path('..') / f"attempt_{rec['attempt']}" / 'hours' / hour,
                                        target_is_directory=True)
    write(out / 'file_receipts.json', [chosen[h] for h in hours])
    report = {'at': now().isoformat(), 'phase': 'captured', 'files': len(hours),
              'successful_files': sum(r['complete'] for r in chosen.values()),
              'attempts': len(all_receipts), 'failed_attempts': sum(not r['complete'] for r in all_receipts),
              'archive_bytes': sum(r['archive_bytes'] for r in all_receipts),
              'events': sum(r.get('retained_rows', 0) for r in chosen.values() if r['complete']),
              'protected_period_rows_read': 0,
              'missing_hours': [h for h in hours if not chosen[h]['complete']]}
    write(out / 'capture_report.json', report)
    write(out / 'status.json', report)
    files = [out / 'capture_report.json', out / 'file_receipts.json', out / 'attempt_receipts.json',
             REL / 'implementation_manifest.json'] + list(out.glob('attempt_*/hours/*/manifest.json'))
    write(out / 'capture_manifest.json', {'files': {str(p.relative_to(REPO_ROOT)): sha(p) for p in files}})
    print(json.dumps(report), flush=True)


def clustered(diff, clusters, rng, b=5000):
    keys = np.unique(clusters)
    sums = np.array([diff[clusters == k].sum() for k in keys])
    counts = np.array([(clusters == k).sum() for k in keys])
    draws = rng.integers(0, len(keys), size=(b, len(keys)))
    stats = sums[draws].sum(1) / counts[draws].sum(1)
    return {'clusters': int(len(keys)), 'mean': float(diff.mean()),
            'ci95': [float(np.quantile(stats, .025)), float(np.quantile(stats, .975))]}


def evaluate():
    verify_setup()
    selected = load_cohort()
    verify(BASE / 'source/capture_manifest.json')
    out = BASE / 'evaluation'
    out.mkdir(exist_ok=False)
    write(out / 'consumption_receipt.json', {'at': now().isoformat(), 'status': 'started', 'dates': DATES})
    try:
        ledger = build_panel(BASE / 'source', DATES, selected)
        pq.write_table(pa.Table.from_pylist(ledger), out / 'grid_ledger.parquet')
        issued = [r for r in ledger if r['current_valid']]
        models = load_models()
        ps = {n: infer(models[n], issued) for n in MODELS}
        pq.write_table(pa.Table.from_pylist(
            [{'market_id': r['market_id'], 'date': r['date'], 'decision_at': r['decision_at'],
              'target': r['target'], 'endpoint_eligible': r['endpoint_eligible'],
              'strict_eligible': r['strict_eligible'], **{n: float(p[i]) for n, p in ps.items()}}
             for i, r in enumerate(issued)]), out / 'issued_predictions.parquet')
        observed = np.asarray([r['endpoint_eligible'] for r in issued], dtype=bool)
        y = np.asarray([r['target'] if r['endpoint_eligible'] else 0 for r in issued], dtype=int)
        fam = {m['market_id']: '|'.join(sorted(e['id'] for e in m['events'])) for m in selected}
        masks = {'primary': observed,
                 'strict': observed & np.asarray([r['strict_eligible'] for r in issued], dtype=bool),
                 'nonoverlap': observed & np.asarray([r['t'] % 1800 == 0 for r in issued], dtype=bool)}
        ids = np.asarray([r['market_id'] for r in issued])
        dates = np.asarray([r['date'] for r in issued])
        rng = np.random.default_rng(20261026)
        loss = {n: -(y * np.log(p) + (1 - y) * np.log1p(-p)) for n, p in ps.items()}
        boot = {n: {'by_contract': clustered((loss[n] - loss['row_hgb7'])[observed], ids[observed], rng),
                    'by_date': clustered((loss[n] - loss['row_hgb7'])[observed], dates[observed], rng)}
                for n in MODELS if n != 'row_hgb7'}
        groups = []
        for field, arr in [('date', dates), ('market_id', ids)]:
            for value in sorted(set(arr)):
                m = observed & (arr == value)
                if m.any():
                    groups.append({'field': field, 'value': value, 'observed': int(m.sum()),
                                   'models': {n: metrics(y[m], p[m]) for n, p in ps.items()}})
        per_contract = [g for g in groups if g['field'] == 'market_id']
        result = {'at': now().isoformat(), 'selected': 'row_hgb7', 'dates': DATES,
                  'scheduled': len(ledger), 'issued': len(issued), 'observed': int(observed.sum()),
                  'missing_outcomes': int((~observed).sum()),
                  'contributing_contracts': len(set(ids[observed])),
                  'families': len({fam[i] for i in ids[observed]}),
                  **{pop: {n: metrics(y[m], p[m]) for n, p in ps.items()} for pop, m in masks.items()},
                  'equal_contract_log_loss': {n: float(np.mean([g['models'][n]['log_loss'] for g in per_contract]))
                                              for n in MODELS},
                  'contracts_favoring_selected_vs_logit': sum(g['models']['row_hgb7']['log_loss'] < g['models']['activity_logit']['log_loss'] for g in per_contract),
                  'dates_favoring_selected_vs_logit': sum(g['models']['row_hgb7']['log_loss'] < g['models']['activity_logit']['log_loss'] for g in groups if g['field'] == 'date'),
                  'bootstrap': boot,
                  'missing_outcome_bounds': {n: missing_bounds([r['target'] for r in issued], ps['row_hgb7'], ps[n])
                                             for n in MODELS if n != 'row_hgb7'},
                  'model_refit': False, 'new_contract_identities': True, 'prospective': False,
                  'news_tested': False, 'missing_bounds_are_confidence_intervals': False}
        write(out / 'groups.json', groups)
        write(out / 'result.json', result)
        write(out / 'consumption_receipt.json', {'at': now().isoformat(), 'status': 'completed', 'dates': DATES})
        print(json.dumps({k: result[k] for k in ['issued', 'observed', 'contributing_contracts', 'primary']}, indent=1))
    except Exception as e:
        write(out / 'failure.json', {'at': now().isoformat(), 'error': type(e).__name__, 'message': str(e)[:240]})
        raise
    finally:
        freeze(out, [REL / 'implementation_manifest.json', BASE / 'source/capture_manifest.json'])


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('phase', choices=['select', 'capture', 'evaluate'])
    {'select': select, 'capture': capture, 'evaluate': evaluate}[parser.parse_args().phase]()
