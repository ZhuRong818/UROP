"""Once-only test of the history stack on never-used contracts over the unopened fortnight 29 June - 12 July 2026.

New research cycle authorized by the user on 31 Oct 2026; protocol eventx/release/v7/history_stack_20261031/.
Copy of the late-June v2 runner (selection, capture and panel rules unchanged) with a new window, a new disjoint
ID range [0x28, 0x48), a larger cohort, the v03 fetcher (row-group cap 16) and a panel built in contract chunks.
Phases (each runs once): select -> capture -> evaluate.

Selection reads only identity/event-type/clock columns from 28 June hours (consumed late-June block, before the
window) plus current Gamma metadata; no price, quote or outcome column is read before the cohort is frozen.

Primary (frozen before capture): matched log loss of `stack` (frozen development/stack.joblib) against the online
contract rate (pseudocount 20 toward the stored global rate; outcomes matured >= 2,100 s; history restarting on
29 June). PASS requires stack log loss < rate, stack Brier <= rate, and the contract x date two-way bootstrap 95%
lower bound of (rate - stack) > 0 (5,000 draws, seed 20261101). Secondary, descriptive: stack vs row_hgb7, row_hgb7
vs rate (the pooled-vs-own-history question for the original booster), stack and row_hgb7 vs activity logistic,
contract-clustered intervals, missing-outcome bounds, per-contract and per-date wins, history strata.
"""
import argparse
import hashlib
import json
import os
from collections import Counter
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from pathlib import Path

import httpx
import joblib
import numpy as np
import pandas as pd
import pyarrow as pa
import pyarrow.compute as pc
import pyarrow.parquet as pq
from sklearn.metrics import roc_auc_score

from eventx.tasks.analyze_v7_dependence_coverage_20261028 import LAG, PSEUDO
from eventx.tasks.develop_v7_history_stack_20261031 import design
from eventx.tasks.discover_v7_direct_pilot_20261022 import REPO_ROOT, now, sha, write, verify_originals
from eventx.tasks.run_v7_archive_week_pilot_20261025 import COLS, EX, verify
from eventx.tasks.run_v7_week_replication_20261025 import RETRYABLE, infer, load_models, missing_bounds, freeze
from eventx.v7.archive_ranges_20261024 import read_columns, RangeStore
from eventx.v7.calibration_transport_20261025 import build_panel
from eventx.v7.family_capture_20261031_v03 import fetch

BASE = REPO_ROOT / 'data/v7/history_stack_20261031/test'
REL = REPO_ROOT / 'eventx/release/v7/history_stack_20261031'
STACK = REPO_ROOT / 'data/v7/history_stack_20261031/development/stack.joblib'
OLD_COHORT = REPO_ROOT / 'data/v7/family_training_20261025_v02/cohort'
PRIOR_NEW = REPO_ROOT / 'data/v7/new_identity_test_20261026/cohort'
LATE = REPO_ROOT / 'data/v7/late_june_test_20261027_v2/cohort'
DATES = [f'2026-06-{d:02d}' for d in (29, 30)] + [f'2026-07-{d:02d}' for d in range(1, 13)]
IDENTITY_HOURS = ['2026-06-28T12', '2026-06-28T13']
ID_RANGE = ('0x28', '0x48')  # disjoint from every earlier cohort (development < 0x0a, [0x10,0x18), [0x18,0x28))
TARGET_N = 150
SALT = 'history-stack-20261031:'
MODELS = ['global_rate', 'activity_logit', 'row_hgb7']
CHUNK = 15
SEED = 20261101
B = 5000


def verify_setup():
    verify_originals()
    verify(REL / 'implementation_manifest.json')
    for folder in (OLD_COHORT, PRIOR_NEW, LATE):
        verify(folder / 'manifest.json')
    old = json.loads((OLD_COHORT / 'cohorts.json').read_text())
    return (old['development50'] + old['unseen10'] + json.loads((PRIOR_NEW / 'cohort.json').read_text())['new']
            + json.loads((LATE / 'cohort.json').read_text())['new'])


def in_range(cid):
    return ID_RANGE[0] <= cid[:4] < ID_RANGE[1]


def select():
    previous = verify_setup()
    out = BASE / 'cohort'
    out.mkdir(parents=True, exist_ok=False)
    seen_events = {e['id'] for m in previous for e in m['events']}
    excluded = set(json.loads(EX.read_text())) | {m['market_id'] for m in previous}
    store = RangeStore(out / 'identity_ranges', 64 * 1024 * 1024)
    sets, read_groups = [], {}
    try:
        for hour in IDENTITY_HOURS:
            url = 'https://r2v2.pmxt.dev/polymarket_orderbook_' + hour + '.parquet'
            meta, _ = store.metadata(url)
            ix = meta.schema.names.index('market')
            groups = [i for i in range(meta.num_row_groups)
                      if meta.row_group(i).column(ix).statistics.max[:4].decode() >= ID_RANGE[0]
                      and meta.row_group(i).column(ix).statistics.min[:4].decode() < ID_RANGE[1]]
            if len(groups) > 16:
                raise RuntimeError('Identity group cap exceeded')
            read_groups[hour] = groups
            union = set()
            start = datetime.fromisoformat(hour + ':00:00+00:00').timestamp()
            for g in groups:
                t = read_columns(store, url, meta, g, COLS[:5], 'june28_identity_event_clocks_only')
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
    lo_t, hi_t = datetime(2026, 6, 29, tzinfo=timezone.utc), datetime(2026, 7, 6, tzinfo=timezone.utc)
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
    write(out / 'cohort.json', {'at': now().isoformat(), 'new': chosen, 'selection_before_prices': True,
                                'candidates': len(candidates), 'lookups': len(receipts)})
    freeze(out, [REL / 'implementation_manifest.json'])
    print(json.dumps({'candidates': len(candidates), 'lookups': len(receipts), 'selected': len(chosen)}), flush=True)


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


def online_rate(df):
    """Same rule as the development blocks: matured known outcomes only, pseudocount toward the global rate."""
    p, hist = np.empty(len(df)), np.empty(len(df), dtype=int)
    for _, g in df.groupby('market_id', sort=False):
        order = np.argsort(g['t'].to_numpy())
        ts = g['t'].to_numpy()[order]
        known = g['endpoint_eligible'].to_numpy()[order]
        y = np.nan_to_num(g['target'].to_numpy(dtype=float)[order])
        ck, cn = np.concatenate([[0], np.cumsum(y * known)]), np.concatenate([[0], np.cumsum(known)])
        j = np.searchsorted(ts, ts - LAG, side='right')
        gr = g['global_rate'].to_numpy()[order]
        idx = g.index.to_numpy()[order]
        p[idx] = (ck[j] + PSEUDO * gr) / (cn[j] + PSEUDO)
        hist[idx] = cn[j]
    return np.clip(p, 1e-6, 1 - 1e-6), hist


def one_way(diff, groups, rng):
    keys, inv = np.unique(groups, return_inverse=True)
    s, n = np.bincount(inv, diff), np.bincount(inv)
    draws = rng.integers(0, len(keys), size=(B, len(keys)))
    st = s[draws].sum(1) / n[draws].sum(1)
    return {'clusters': int(len(keys)), 'mean': float(diff.mean()),
            'ci95': [float(np.quantile(st, .025)), float(np.quantile(st, .975))]}


def two_way(diff, a, b, rng):
    ka, ia = np.unique(a, return_inverse=True)
    kb, ib = np.unique(b, return_inverse=True)
    S, N = np.zeros((len(ka), len(kb))), np.zeros((len(ka), len(kb)))
    np.add.at(S, (ia, ib), diff)
    np.add.at(N, (ia, ib), 1)
    ma = rng.multinomial(len(ka), np.full(len(ka), 1 / len(ka)), size=B).astype(float)
    mb = rng.multinomial(len(kb), np.full(len(kb), 1 / len(kb)), size=B).astype(float)
    st = np.einsum('ri,ij,rj->r', ma, S, mb) / np.einsum('ri,ij,rj->r', ma, N, mb)
    return {'clusters': [int(len(ka)), int(len(kb))], 'mean': float(diff.mean()),
            'ci95': [float(np.quantile(st, .025)), float(np.quantile(st, .975))]}


def scores(y, p):
    p = np.clip(p, 1e-6, 1 - 1e-6)
    return {'log_loss': float(-(y * np.log(p) + (1 - y) * np.log1p(-p)).mean()), 'brier': float(((p - y) ** 2).mean()),
            'roc_auc': float(roc_auc_score(y, p)), 'n': int(len(y)), 'positives': int(y.sum())}


def evaluate():
    verify_setup()
    selected = load_cohort()
    verify(BASE / 'source/capture_manifest.json')
    verify(REL / 'implementation_manifest.json')
    out = BASE / 'evaluation'
    out.mkdir(exist_ok=False)
    write(out / 'consumption_receipt.json', {'at': now().isoformat(), 'status': 'started', 'dates': DATES})
    try:
        models, stack = load_models(), joblib.load(STACK)
        ledger_n, frames = 0, []
        for k in range(0, len(selected), CHUNK):  # contracts are independent tapes; chunking bounds memory
            ledger = build_panel(BASE / 'source', DATES, selected[k:k + CHUNK])
            ledger_n += len(ledger)
            issued = [r for r in ledger if r['current_valid']]
            if not issued:
                continue
            ps = {n: infer(models[n], issued) for n in MODELS}
            frames.append(pd.DataFrame({'market_id': [r['market_id'] for r in issued], 'date': [r['date'] for r in issued],
                                        't': [r['t'] for r in issued], 'decision_at': [r['decision_at'] for r in issued],
                                        'target': [r['target'] for r in issued],
                                        'endpoint_eligible': [r['endpoint_eligible'] for r in issued], **ps}))
            del ledger, issued
        iss = pd.concat(frames, ignore_index=True)
        iss['adaptive_rate'], iss['history'] = online_rate(iss)
        iss['stack'] = stack['model'].predict_proba(design(iss, stack['name']))[:, 1]
        iss.to_parquet(out / 'issued_predictions.parquet')
        k = iss[iss.endpoint_eligible].reset_index(drop=True)
        y, ids, dates = k['target'].to_numpy(float), k['market_id'].to_numpy(), k['date'].to_numpy()
        names = ['stack', 'adaptive_rate', 'row_hgb7', 'activity_logit', 'global_rate']
        P = {n: np.clip(k[n].to_numpy(), 1e-6, 1 - 1e-6) for n in names}
        L = {n: -(y * np.log(p) + (1 - y) * np.log1p(-p)) for n, p in P.items()}
        rng = np.random.default_rng(SEED)
        d = L['adaptive_rate'] - L['stack']
        primary = {'stack_minus_rate_two_way': two_way(d, ids, dates, rng),
                   'stack_minus_rate_by_contract': one_way(d, ids, rng)}
        sc = {n: scores(y, P[n]) for n in names}
        passed = (sc['stack']['log_loss'] < sc['adaptive_rate']['log_loss'] and sc['stack']['brier'] <= sc['adaptive_rate']['brier']
                  and primary['stack_minus_rate_two_way']['ci95'][0] > 0)
        secondary = {}
        for cand, comp in [('stack', 'row_hgb7'), ('row_hgb7', 'adaptive_rate'), ('stack', 'activity_logit'),
                           ('row_hgb7', 'activity_logit')]:
            dd = L[comp] - L[cand]
            secondary[f'{cand}_vs_{comp}'] = {'gain': float(dd.mean()), 'relative_pct': float(100 * dd.mean() / L[comp].mean()),
                                              'two_way': two_way(dd, ids, dates, rng), 'by_contract': one_way(dd, ids, rng)}
        per_c = {c: float(d[ids == c].mean()) for c in np.unique(ids)}
        per_d = {x: float(d[dates == x].mean()) for x in np.unique(dates)}
        strata = []
        for lo, hi in [(0, 0), (1, 11), (12, 47), (48, 10**9)]:
            m = (k['history'] >= lo).to_numpy() & (k['history'] <= hi).to_numpy()
            if m.any():
                strata.append({'matured_outcomes': [lo, None if hi >= 10**9 else hi], 'rows': int(m.sum()),
                               'stack_minus_rate': float(d[m].mean()),
                               'stack_minus_rate_ci95': one_way(d[m], ids[m], rng)['ci95'],
                               'stack_minus_row_hgb7': float((L['row_hgb7'] - L['stack'])[m].mean())})
        all_targets = [None if not e else int(t) for t, e in zip(iss['target'], iss['endpoint_eligible'])]
        result = {'at': now().isoformat(), 'dates': DATES, 'selected_contracts': len(selected), 'scheduled': ledger_n,
                  'issued': int(len(iss)), 'observed': int(len(k)), 'missing_outcomes': int(len(iss) - len(k)),
                  'contributing_contracts': int(len(per_c)), 'stack_model': stack['name'],
                  'scores': sc, 'primary': primary, 'pass': bool(passed), 'secondary': secondary,
                  'contracts_favouring_stack_vs_rate': int(sum(v > 0 for v in per_c.values())),
                  'dates_favouring_stack_vs_rate': int(sum(v > 0 for v in per_d.values())),
                  'history_strata': strata,
                  'missing_outcome_bounds_stack_vs_rate': missing_bounds(
                      all_targets, np.clip(iss['stack'].to_numpy(), 1e-6, 1 - 1e-6), np.clip(iss['adaptive_rate'].to_numpy(), 1e-6, 1 - 1e-6)),
                  'model_refit': False, 'new_contract_identities': True, 'prospective': False,
                  'missing_bounds_are_confidence_intervals': False}
        write(out / 'result.json', result)
        write(out / 'consumption_receipt.json', {'at': now().isoformat(), 'status': 'completed', 'dates': DATES})
        print(json.dumps({x: result[x] for x in ['issued', 'observed', 'contributing_contracts', 'pass', 'scores', 'primary']}, indent=1))
    except Exception as e:
        write(out / 'failure.json', {'at': now().isoformat(), 'error': type(e).__name__, 'message': str(e)[:240]})
        raise
    finally:
        freeze(out, [REL / 'implementation_manifest.json', BASE / 'source/capture_manifest.json'])


if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('phase', choices=['select', 'capture', 'evaluate'])
    {'select': select, 'capture': capture, 'evaluate': evaluate}[ap.parse_args().phase]()
