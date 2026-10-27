"""Source-grounded episode ledger and descriptive opened-development coverage.

No estimator, forecast scoring or protected holdout access. The source findings
are manual retrospective research notes; this script makes their row joins and
deduplication reproducible. Existing outcome exposure is disclosed in the receipt.
"""
from collections import Counter, defaultdict
from datetime import datetime, timezone, timedelta
from pathlib import Path
import hashlib
import json

import numpy as np

from eventx.tasks.build_v4_discovery_examples import EXAMPLE_DTYPE, DEVELOPMENT_START_US
from eventx.tasks.run_v4_discovery_models import OOF_DTYPE

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / 'data/v7/verified_event_ledger_20261015'
INV = ROOT / 'data/v7/event_opportunity_inventory_20261014'
REV = ROOT / 'data/v7/event_relevance_review_20261015'
EX = ROOT / 'data/v4/discovery/examples/examples.bin'
OOF = ROOT / 'data/v4/discovery/models/oof_predictions.bin'
MARKETS = ROOT / 'data/v3_1_historical/primary/development/prepared/market_index.jsonl'
NEWS = ROOT / 'data/v3_historical/primary/label_blind_inputs/news.jsonl'
MINUTE_US = 60_000_000
START, END = 55 * 1440, 66 * 1440
AMBIGUOUS = 'KXFEDDECISION-26JUL-H0'


def read(path):
    return [json.loads(line) for line in path.open() if line.strip()]


def sha(path):
    with path.open('rb') as f:
        return hashlib.file_digest(f, 'sha256').hexdigest()


def write(name, obj):
    (OUT / name).write_text(json.dumps(obj, indent=2, sort_keys=True, allow_nan=False) + '\n')


def lines(name, rows):
    (OUT / name).write_text(''.join(json.dumps(r, sort_keys=True, allow_nan=False) + '\n' for r in rows))


def utc(value):
    return datetime.fromisoformat(value.replace('Z', '+00:00'))


def stamp(minute):
    return datetime.fromtimestamp((DEVELOPMENT_START_US + int(minute) * MINUTE_US) / 1e6, timezone.utc).isoformat()


def verify(path):
    obj = json.loads(path.read_text())
    for a in obj['artifacts']:
        if sha(ROOT / a['path']) != a['sha256']:
            raise RuntimeError('Frozen artifact changed: ' + a['path'])


def main():
    if (OUT / 'report.json').exists():
        raise FileExistsError('Preserve completed output; use a new version')
    for p in [REV / 'delivery_manifest.json', INV / 'manifest.json']:
        verify(p)
    source = json.loads((OUT / 'source_findings.json').read_text())
    findings = {r['article_id']: r for r in source['articles']}
    events = {r['event_id']: r for r in source['events']}
    pairs = read(REV / 'agreed_context_pairs.jsonl')
    candidates = {(r['article_id'], r['market_id']): r for r in read(INV / 'candidate_ledger.jsonl')}
    if set(findings) != {p['article_id'] for p in pairs} or len(pairs) != 32:
        raise ValueError('Reviewed set does not match manual ledger')
    markets = {r['market_id']: r for r in read(MARKETS)}
    packet = {r['contract']['market_id']: r['contract'] for r in read(REV / 'packet_A.jsonl')}
    # Connected components are split safeguards, not independent event estimates.
    parent = {e: e for e in events}

    def find(e):
        while parent[e] != e:
            e = parent[e]
        return e

    for f in findings.values():
        for e in f['event_ids'][1:]:
            parent[find(e)] = find(f['event_ids'][0])
    roots = sorted({find(e) for e in events})
    component = {e: 'isolation_' + str(roots.index(find(e)) + 1) for e in events}
    raw_news = {}
    for r in read(NEWS):
        if str(r['id']) in findings:
            raw_news.setdefault(str(r['id']), []).append(r)
    article_records = []
    for aid, f in sorted(findings.items()):
        c = next(v for k, v in candidates.items() if k[0] == aid)
        raw = next((r for r in raw_news[aid] if utc(r['available_at']) == utc(c['available_at'])), None)
        if raw is None:
            raise ValueError('Raw article availability mismatch: ' + aid)
        delays = []
        for eid in f['event_ids']:
            e = events[eid]
            delays.append({'event_id': eid, 'release_to_system_minutes':
                (utc(c['available_at']) - utc(e['source_public_at'])).total_seconds() / 60
                if e['source_public_at'] else None,
                'event_date': e['source_public_date'], 'clock_kind': e['clock_kind']})
        article_records.append({**f, 'headline': c['headline'], 'cached_summary': c['summary'],
            'cached_url': raw.get('url'), 'cached_publisher': raw.get('publisher'),
            'published_at': c['published_at'], 'available_at': c['available_at'],
            'publication_to_system_minutes': c['lag_minutes'], 'event_delays': delays,
            'isolation_component': component[f['event_ids'][0]],
            'historical_text_version_authenticated': False})
    lines('article_ledger.jsonl', article_records)
    lines('pair_ledger.jsonl', [{**candidates[(p['article_id'], p['market_id'])],
        'pair_id': p['pair_id'], 'review_status': 'two_assistant_agreed_material_context',
        'event_ids': findings[p['article_id']]['event_ids'],
        'isolation_component': component[findings[p['article_id']]['event_ids'][0]],
        'ambiguous_contract': p['market_id'] == AMBIGUOUS} for p in pairs])
    contract_records = [{**packet[mid], 'market_index': int(markets[mid]['market_index']),
        'diagnostic_disposition': 'exclude_in_nonambiguous_sensitivity' if mid == AMBIGUOUS else 'retain_unsigned_context_with_historical_terms_uncertainty',
        'official_rule_recovery': 'HTTP404; no new official metadata' if mid == AMBIGUOUS else 'cached_only'}
        for mid in sorted({p['market_id'] for p in pairs})]
    lines('contract_ledger.jsonl', contract_records)
    lines('event_ledger.jsonl', [{**e, 'isolation_component': component[eid],
        'article_ids': [r['article_id'] for r in article_records if eid in r['event_ids']],
        'independence_verified': False, 'surprise_measured': False} for eid, e in events.items()])
    manifests = [ROOT / 'data/v4/discovery/examples/manifest.json', ROOT / 'data/v4/discovery/models/manifest.json']
    # Check only binary inputs needed here against their canonical manifests;
    # no model bundles or protected future data are read.
    for target, manifest in zip([EX, OOF], manifests):
        records = json.loads(manifest.read_text())['artifacts']
        expected = next(a['sha256'] for a in records if ROOT / a['path'] == target)
        if sha(target) != expected:
            raise RuntimeError('Binary hash mismatch')
    inputs = [REV / 'delivery_manifest.json', INV / 'manifest.json', REV / 'agreed_context_pairs.jsonl',
        INV / 'candidate_ledger.jsonl', INV / 'coverage_after_candidate_freeze.jsonl',
        OUT / 'source_findings.json', EX, OOF, MARKETS, NEWS, Path(__file__)]
    input_hashes = {str(p.relative_to(ROOT)): sha(p) for p in inputs}
    receipt = {'created_at': datetime.now(timezone.utc).isoformat(),
        'scope': 'opened July 11-21 development coverage, no forecast fit',
        'prior_outcome_exposure': 'Root already knows original 174/49 aggregate and earlier development results; this is not an outcome-blind preregistration.',
        'new_labels_read_before_this_receipt': False,
        'article_and_episode_assignment_uses': 'review agreement, text and sources only',
        'eligibility': {'article_window': '(decision-30m,decision]', 'price_age_max_minutes': 5,
            'preceding60m_trade_count_min': 3, 'inherited_example_eligibility': True},
        'landmarks': 'earliest reviewed article arrival per isolation-component/contract; first eligible row in that article window, no later-arrival substitution',
        'populations': ['all_agreed', 'exclude_ambiguous_H0', 'exclude_H0_and_ppi_summary_discrepancy'],
        'source_clock_diagnostic': 'CPI and PPI 0-30m after official release over same five contracts; hypothetical source capture, never historical news features',
        'ledger_hashes': {name: sha(OUT / name) for name in ['article_ledger.jsonl','pair_ledger.jsonl','contract_ledger.jsonl','event_ledger.jsonl']},
        'inputs': input_hashes}
    write('coverage_receipt_before_new_counts.json', receipt)
    print('Source ledger and coverage definitions receipted before new label counts', flush=True)
    ex = np.memmap(EX, dtype=EXAMPLE_DTYPE, mode='r')
    oof = np.memmap(OOF, dtype=OOF_DTYPE, mode='r')
    caches = {}
    for r in contract_records:
        m = r['market_index']
        a, b = np.searchsorted(ex['market'], [m, m + 1])
        ix = np.arange(a, b)
        keep = ((ex['minute'][ix] >= START) & (ex['minute'][ix] < END)
            & (ex['price_age'][ix] <= 5) & (ex['features'][ix, 6] >= 3))
        caches[m] = ix[keep][np.argsort(ex['minute'][ix[keep]])]

    def window(m, available):
        ix = caches[m]
        times = DEVELOPMENT_START_US + ex['minute'][ix].astype(np.int64) * MINUTE_US
        us = int(round(utc(available).timestamp() * 1e6))
        return set(map(int, ix[np.searchsorted(times, us, side='left'):np.searchsorted(times, us + 30 * MINUTE_US, side='left')]))

    oof_keys = {(int(m), int(t)) for m, t in zip(oof['market'][oof['fold'] == 5], oof['minute'][oof['fold'] == 5])}

    def stats(indices):
        ix = np.array(sorted(indices), dtype=np.int64)
        labels = ex['label'][ix]
        return {'rows': len(ix), 'movement_rows': int(labels.sum()), 'nonmovement_rows': int(len(ix) - labels.sum()),
            'markets': len(set(map(int, ex['market'][ix]))),
            'decision_dates': sorted({stamp(t)[:10] for t in ex['minute'][ix]}),
            'original_fold5_rows': sum((int(ex['market'][i]), int(ex['minute'][i])) in oof_keys for i in ix)}

    pair_hits = {}
    previous = {(r['article_id'], r['market_id']): r for r in read(INV / 'coverage_after_candidate_freeze.jsonl')}
    pair_coverage = []
    memberships = defaultdict(list)
    for p in pairs:
        c = candidates[(p['article_id'], p['market_id'])]
        m = int(markets[p['market_id']]['market_index'])
        hits = window(m, c['available_at'])
        s = stats(hits)
        old = previous[(p['article_id'], p['market_id'])]['coverage']['all_groups']
        if any(s[k] != old[k] for k in ['rows', 'movement_rows', 'nonmovement_rows']):
            raise RuntimeError('Inherited pair coverage does not reproduce')
        pair_hits[p['pair_id']] = hits
        pair_coverage.append({'pair_id': p['pair_id'], 'article_id': p['article_id'], 'market_id': p['market_id'], **s})
        for i in hits:
            memberships[i].append(p)
    lines('pair_coverage.jsonl', pair_coverage)
    selected_sets = {
        'all_agreed': pairs,
        'exclude_ambiguous_H0': [p for p in pairs if p['market_id'] != AMBIGUOUS],
        'exclude_H0_and_ppi_summary_discrepancy': [p for p in pairs if p['market_id'] != AMBIGUOUS and p['article_id'] != '215472946']}
    populations = {}
    for name, ps in selected_sets.items():
        ix = set().union(*(pair_hits[p['pair_id']] for p in ps))
        articles = {p['article_id'] for p in ps}
        populations[name] = {**stats(ix), 'pairs': len(ps), 'articles': len(articles),
            'arrival_dates': len({candidates[(p['article_id'],p['market_id'])]['available_at'][:10] for p in ps}),
            'isolation_components': len({component[findings[a]['event_ids'][0]] for a in articles})}
    lines('row_coverage.jsonl', [{'example_index': i, 'market_index': int(ex['market'][i]),
        'decision_minute': int(ex['minute'][i]), 'decision_at': stamp(ex['minute'][i]),
        'target_end_at': stamp(int(ex['minute'][i]) + 30), 'label': int(ex['label'][i]),
        'price_age_minutes': float(ex['price_age'][i]), 'preceding60m_trade_count': float(ex['features'][i,6]),
        'article_ids': sorted({p['article_id'] for p in ps}),
        'pair_ids': sorted(p['pair_id'] for p in ps),
        'isolation_components': sorted({component[findings[p['article_id']]['event_ids'][0]] for p in ps})}
        for i, ps in sorted(memberships.items())])
    article_coverage = []
    for r in article_records:
        ps = [p for p in pairs if p['article_id'] == r['article_id']]
        ix = set().union(*(pair_hits[p['pair_id']] for p in ps))
        article_coverage.append({'article_id': r['article_id'], 'isolation_component': r['isolation_component'], **stats(ix)})
    lines('article_coverage.jsonl', article_coverage)
    event_coverage = []
    for eid in events:
        ps = [p for p in pairs if eid in findings[p['article_id']]['event_ids']]
        ix = set().union(*(pair_hits[p['pair_id']] for p in ps))
        event_coverage.append({'event_id': eid, 'articles': len({p['article_id'] for p in ps}), **stats(ix),
            'overlap_warning': 'Articles can reference multiple events; event counts must not be added.'})
    lines('event_coverage.jsonl', event_coverage)
    component_coverage = []
    for cid in sorted(set(component.values())):
        ps = [p for p in pairs if component[findings[p['article_id']]['event_ids'][0]] == cid]
        ix = set().union(*(pair_hits[p['pair_id']] for p in ps))
        component_coverage.append({'isolation_component': cid, 'event_ids': [e for e in events if component[e] == cid],
            'articles': len({p['article_id'] for p in ps}), **stats(ix), 'independence_verified': False})
    lines('isolation_component_coverage.jsonl', component_coverage)
    landmarks = []
    landmark_stats = {}
    for name, ps in selected_sets.items():
        buckets = defaultdict(list)
        for p in ps:
            buckets[(component[findings[p['article_id']]['event_ids'][0]], p['market_id'])].append(p)
        selected = set()
        for (cid, mid), group in sorted(buckets.items()):
            p = min(group, key=lambda p: (candidates[(p['article_id'], mid)]['available_at'], p['article_id']))
            ix = min(pair_hits[p['pair_id']], key=lambda i: int(ex['minute'][i]))
            selected.add(ix)
            landmarks.append({'population': name, 'isolation_component': cid, 'market_id': mid,
                'article_id': p['article_id'], 'example_index': ix, 'decision_at': stamp(ex['minute'][ix]), 'label': int(ex['label'][ix])})
        landmark_stats[name] = stats(selected)
    lines('earliest_arrival_landmarks.jsonl', landmarks)
    # Describe horizon overlap separately; nonoverlapping rows still share events.
    greedy = set()
    for m in caches:
        last = -10**12
        for i in sorted((i for i in memberships if int(ex['market'][i]) == m), key=lambda i: int(ex['minute'][i])):
            if int(ex['minute'][i]) >= last + 30:
                greedy.add(i)
                last = int(ex['minute'][i])
    source_windows = []
    for eid in ['cpi_2026_06', 'ppi_2026_06']:
        allhits = set()
        for r in contract_records:
            hits = window(r['market_index'], events[eid]['source_public_at'])
            allhits.update(hits)
            source_windows.append({'event_id': eid, 'market_id': r['market_id'], 'source_public_at': events[eid]['source_public_at'], **stats(hits),
                'interpretation': 'hypothetical original-source capture; no article made available earlier'})
        source_windows.append({'event_id': eid, 'market_id': 'ALL_FIVE', **stats(allhits)})
    lines('official_release_window_coverage.jsonl', source_windows)
    lag = [r['publication_to_system_minutes'] for r in article_records]
    release_articles = [r for r in article_records if any(e['release_to_system_minutes'] is not None and e['event_id'] in ['cpi_2026_06','ppi_2026_06'] for e in r['event_delays'])]
    delays = [min(e['release_to_system_minutes'] for e in r['event_delays'] if e['release_to_system_minutes'] is not None and e['event_id'] in ['cpi_2026_06','ppi_2026_06']) for r in release_articles]
    report = {'status': 'complete_with_explicit_source_verification_limits', 'populations': populations,
        'event_identities': len(events), 'official_source_document_or_programme_identities': sum(e['verification'].startswith('official_') for e in events.values()),
        'exact_release_clock_events': sum(e['source_public_at'] is not None for e in events.values()),
        'independent_event_count': None, 'isolation_components': len(set(component.values())),
        'earliest_arrival_landmarks': landmark_stats, 'greedy_same_market_nonoverlapping_rows': stats(greedy),
        'publication_to_system_lag_minutes': {'min': min(lag), 'median': float(np.median(lag)), 'max': max(lag)},
        'articles_publication_lag_le_minutes': {str(w): sum(v <= w for v in lag) for w in [30,60,180]},
        'cpi_ppi_release_to_system_delay': {'articles': len(release_articles), 'min_minutes': min(delays), 'median_minutes': float(np.median(delays)), 'max_minutes': max(delays), 'articles_within30m': sum(v <= 30 for v in delays)},
        'official_release_window_totals': [r for r in source_windows if r['market_id'] == 'ALL_FIVE'],
        'original_access_counts': dict(Counter(r['original_access'] for r in article_records)),
        'data_quality_flags': ['Article 215472946 annual PPI sign/scope mismatch', 'H0 missing official rules/subtitle; official GET returned404', 'Historical text versions unauthenticated', 'Published timestamps are not release clocks'],
        'decision': 'Descriptive pilot only. No adequate independent confirmation sample established; prioritize faster original-source capture across new event dates. Unsigned context remains a valid development hypothesis.',
        'checks': {'all_32_pair_counts_reproduced': True, 'forecast_models_fit': 0, 'protected_payloads_read': False, 'new_forecast_metrics': False,
            'ledger_unchanged_after_counts': all(sha(OUT / n) == h for n,h in receipt['ledger_hashes'].items())},
        'power': {'effective_sample_size': None, 'minimum_detectable_effect': None, 'reason': 'Seven referenced identities/four co-isolation groups are not verified independent draws; no valid empirical variance or adopted dependence inference.'}}
    if not report['checks']['ledger_unchanged_after_counts']:
        raise RuntimeError('Ledger changed during coverage')
    write('report.json', report)
    # Binary inputs already checked before counting; small inputs checked again.
    for p in inputs:
        if p not in [EX, OOF, NEWS] and sha(p) != input_hashes[str(p.relative_to(ROOT))]:
            raise RuntimeError('Input changed during execution')
    write('manifest.json', {'inputs': input_hashes, 'artifacts': [{'path': str(p.relative_to(ROOT)), 'sha256': sha(p)} for p in sorted(OUT.iterdir()) if p.is_file()]})
    print(json.dumps(report, indent=2), flush=True)


if __name__ == '__main__':
    main()
