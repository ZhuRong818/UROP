"""Inventory only allowlisted opened-development source arrays; no outcome access.

Observed trade-clock V24 summaries are diagnostics, not certified as-of features.
No model, eligibility labels, training cutoffs or experiment admission is produced.
"""
from collections import Counter, defaultdict
from datetime import datetime, timedelta, timezone
import hashlib
import json
import os
from pathlib import Path
import tempfile

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / 'data/v5/readiness_inventory_20260914'
PREP = ROOT / 'data/v3_1_historical/primary/development/prepared'
SOURCE = ROOT / 'data/v5/source_readiness_20260908'
ASSURANCE = ROOT / 'eventx/release/v5/NEWS_CONTENT_ASSURANCE_20260914.md'
MINUTE = 60_000_000
DAY = 1440 * MINUTE
START = int(datetime(2026, 5, 17, tzinfo=timezone.utc).timestamp() * 1e6)
END = int(datetime(2026, 7, 22, tzinfo=timezone.utc).timestamp() * 1e6)


def digest(p):
    with p.open('rb') as f:
        return hashlib.file_digest(f, 'sha256').hexdigest()


def records(p):
    with p.open() as f:
        for line in f:
            yield json.loads(line)


def trailing_notional(times, values, decisions):
    if np.any(np.diff(times) < 0) or np.any(~np.isfinite(values)) or np.any(values < 0):
        raise ValueError('Invalid sorted trade input')
    cumulative = np.r_[0., np.cumsum(values)]
    return (cumulative[np.searchsorted(times, decisions, side='right')] -
            cumulative[np.searchsorted(times, decisions - DAY, side='right')])


def main():
    if OUT.exists():
        raise FileExistsError('Refusing to overwrite evidence')
    paths = [SOURCE / 'report.json', SOURCE / 'news_provenance_staging.jsonl',
             ROOT / 'data/v5/recovery_summary_20260910/candidate_family_queue.jsonl',
             ROOT / 'data/v5/family_certification_20260910/candidate_components.json',
             ROOT / 'data/v5/family_certification_20260910/report.json',
             ROOT / 'data/v5/lineage_recovery_20260909/report.json',
             PREP / 'manifest.json', PREP / 'market_index.jsonl',
             PREP / 'trades.bin', PREP / 'news_associations.bin', ASSURANCE]
    hashes = {str(p.relative_to(ROOT)): digest(p) for p in paths}
    manifest = json.loads((PREP / 'manifest.json').read_text())
    locked = {a['path']: a['sha256'] for a in manifest['artifacts']}
    for name in ['market_index.jsonl', 'trades.bin', 'news_associations.bin']:
        key = str((PREP / name).relative_to(ROOT))
        if hashes[key] != locked[key]:
            raise ValueError(f'Historical input hash mismatch: {name}')
    old = json.loads((SOURCE / 'report.json').read_text())
    components = json.loads(paths[3].read_text())
    component = {event: number for number, group in enumerate(components) for event in group}
    queue = list(records(paths[2]))
    markets = {(r['venue'], r['market_id']): r for r in queue}
    # Explicit projection: terminal, prices, selected activity and outcomes ignored.
    index = {r['market_index']: markets[(r['venue'], r['market_id'])]
             for r in records(PREP / 'market_index.jsonl')}
    news = np.memmap(PREP / 'news_associations.bin', mode='r',
                     dtype=[('market', '<u4'), ('timestamp_us', '<i8')])
    if np.any((news['timestamp_us'] < START) | (news['timestamp_us'] >= END)):
        raise ValueError('Association outside opened development')
    counts = Counter(map(int, news['market']))
    trades = np.memmap(PREP / 'trades.bin', mode='r', dtype=[('market', '<u4'),
        ('timestamp_us', '<i8'), ('price', '<f8'), ('notional', '<f8'), ('ordinal', '<u8')])
    if np.any((trades['timestamp_us'] < START) | (trades['timestamp_us'] >= END)):
        raise ValueError('Trades outside opened development')
    if np.any(trades['market'][1:] < trades['market'][:-1]):
        raise ValueError('Unsorted markets')
    boundaries = np.r_[0, np.flatnonzero(np.diff(trades['market'])) + 1, len(trades)]
    trade_summary = {}
    # Start after one full day of the export, without implying source completeness.
    grid = np.arange(START + DAY, END, 5 * MINUTE, dtype=np.int64)
    for left, right in zip(boundaries[:-1], boundaries[1:]):
        block = trades[left:right]
        v24 = trailing_notional(block['timestamp_us'], block['notional'], grid)
        trade_summary[int(block['market'][0])] = {
            'observed_trades': int(right-left), 'diagnostic_grid_rows': len(grid),
            'positive_v24_grid_rows': int(np.sum(v24 > 0)),
            'observed_v24_quantiles': dict(zip(['p0', 'p50', 'p90', 'p100'],
                map(float, np.quantile(v24, [0, .5, .9, 1])))),
            'availability_certified': False, 'activity_band': None}
    group_rows, ledger = [], []
    for venue in ['kalshi', 'polymarket']:
        for topic in ['politics', 'macro', 'crypto', 'sports', 'other']:
            selected = [(i, r) for i, r in index.items()
                        if r['venue'] == venue and r['category'] == topic]
            ids = {component[r['candidate_family_id']] for _, r in selected}
            associated = [(i, r) for i, r in selected if counts[i]]
            group_rows.append({'venue': venue, 'legacy_topic': topic,
                'topic_reviewed': False, 'markets': len(selected),
                'provisional_components': len(ids), 'approved_families': 0,
                'legacy_association_events': sum(counts[i] for i, _ in selected),
                'markets_with_legacy_associations': len(associated),
                'provisional_components_with_legacy_associations': len({
                    component[r['candidate_family_id']] for _, r in associated}),
                'certified_days': None, 'eligible_exposed_rows': None,
                'activity_band': None, 'status': 'inventory_only_not_admitted'})
    for i, r in index.items():
        ledger.append({**r, 'provisional_component': component[r['candidate_family_id']],
            'proposed_six_topic_assignment': None, 'topic_review_status': 'pending',
            'legacy_association_events': counts[i], 'observed_trade_clock_diagnostic': trade_summary.get(i),
            'training_admissible': False})
    day_rows = []
    d = datetime(2026, 5, 17, tzinfo=timezone.utc)
    while d < datetime(2026, 7, 22, tzinfo=timezone.utc):
        key = d.date().isoformat()
        day_rows.append({'day': key, 'observed_news_rows': old['news']['availability_days'].get(key, 0),
                         'coverage_certified': False, 'zero_is_proven_empty': False})
        d += timedelta(days=1)
    # Prior failed/partial status indicates investigation priority, not invalid rows.
    report = {'status': 'readiness_inventory_complete_admission_blocked',
        'scope': '[2026-05-17,2026-07-22) opened development only',
        'news_content_assurance': 'accepted_provisionally_user_relayed_admin_statement',
        'assurance_path': str(ASSURANCE.relative_to(ROOT)),
        'news_rows': old['news']['discovery_rows'],
        'clock_inconsistent_rows': old['news']['clock_inconsistent_rows'],
        'news_rows_in_partial_failed_aborted_runs': sum(old['news']['run_status_counts'][s]
            for s in ['partial', 'failed', 'aborted']),
        'days_in_window': len(day_rows),
        'days_with_zero_export_rows': [r['day'] for r in day_rows if not r['observed_news_rows']],
        'coverage_status': 'unreconciled_zero_export_days_not_proven_outages',
        'lineage_reconciliation': json.loads(paths[5].read_text()),
        'market_count': len(index), 'provisional_components': len(components),
        'final_approved_families': 0, 'observed_trade_rows': len(trades),
        'legacy_association_events': len(news), 'groups': group_rows,
        'activity_bands': 'not_assigned_no_admitted_training_scope',
        'trade_clock_summary': 'all-grid retrospective diagnostic; no status/eligibility or availability certification',
        'blockers': ['news_feed_reconciliation', 'historical_metadata_status_and_validity',
            'final_family_boundaries', 'reviewed_topic_assignments', 'certified_inference'],
        'labels_read': False, 'protected_holdouts_touched': False, 'models_fitted': 0}
    OUT.parent.mkdir(parents=True, exist_ok=True)
    stage = Path(tempfile.mkdtemp(prefix='.readiness-inventory-', dir=OUT.parent))
    (stage / 'report.json').write_text(json.dumps(report, indent=2) + '\n')
    (stage / 'daily_news_inventory.json').write_text(json.dumps(day_rows, indent=2) + '\n')
    with (stage / 'market_review_inventory.jsonl').open('w') as f:
        for r in ledger:
            f.write(json.dumps(r) + '\n')
    text = ['# V5 readiness inventory — 14 September 2026', '',
        'News-content assurance accepted provisionally. Dataset admission remains blocked.', '',
        '| Venue | Legacy topic | Markets | Provisional components | Markets with legacy news links |',
        '|---|---|---:|---:|---:|']
    for r in group_rows:
        text.append(f"| {r['venue']} | {r['legacy_topic']} | {r['markets']} | {r['provisional_components']} | {r['markets_with_legacy_associations']} |")
    text += ['', 'These are legacy inventory labels and links, not certified topics, independent families or exposure.',
        f"News rows: {report['news_rows']}; partial/failed/aborted-linked: {report['news_rows_in_partial_failed_aborted_runs']}.",
        f"Zero-row export days: {', '.join(report['days_with_zero_export_rows'])}; actual emptiness/outage unproven.",
        'Observed trade-clock V24 summaries are in the market ledger. Availability, eligibility and training cutoffs',
        'are not certified; no low/medium/high assignments or confirmatory support claims are made.',
        'Next: reconcile intended feed windows/retries, obtain metadata history, review family boundaries and topics,',
        'then compute certified activity strata. Inference must pass before outcome access.']
    (stage / 'REPORT.md').write_text('\n'.join(text) + '\n')
    (stage / 'manifest.json').write_text(json.dumps({'inputs': hashes,
        'script_sha256': digest(Path(__file__)), 'outputs': {p.name: digest(p) for p in stage.iterdir()}}, indent=2)+'\n')
    if OUT.exists():
        raise FileExistsError('Output appeared during audit')
    os.rename(stage, OUT)
    print(json.dumps(report, indent=2))


if __name__ == '__main__':
    main()
