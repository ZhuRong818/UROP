"""Local order-sensitivity diagnostic; no forecast labels, fitting or evaluation."""
from collections import Counter, defaultdict
from datetime import datetime
import json
from pathlib import Path

import pyarrow.parquet as pq

from eventx.tasks.audit_v7_archive_sample_20261025_v03 import START, END, levels, touch
from eventx.tasks.discover_v7_direct_pilot_20261022 import REPO_ROOT, now, sha, write

PARENT = REPO_ROOT / 'data/v7/archive_sample_20261025_v03/attempt_20261025T011030Z_66d836'
OUT = REPO_ROOT / 'data/v7/archive_replay_diagnosis_20261025'


def main():
    for name, digest in json.loads((PARENT / 'manifest.json').read_text())['files'].items():
        assert sha(REPO_ROOT / name) == digest, name
    OUT.mkdir(exist_ok=False)
    rows = pq.read_table(PARENT / 'selected_yes_events.parquet').to_pylist()
    by = defaultdict(list)
    for row in rows:
        by[row['market'].decode()].append(row)
    results = []
    grids = list(range(int(START + 1800), int(END - 1800), 300))
    for cid, records in sorted(by.items()):
        groups = defaultdict(list)
        for row in records:
            groups[row['timestamp_received']].append(row)
        runs = {}
        for ordering in ['stored', 'reverse_ties', 'source_time_within_receive_ties']:
            states = []
            bids = asks = None
            uncertain = False
            latest = None
            comparisons = []
            for received, group in sorted(groups.items()):
                updates = [r for r in group if r['event_type'] == 'price_change']
                books = [r for r in group if r['event_type'] == 'book']
                keys = {(r['side'], str(r['price'])) for r in updates}
                conflict = any(len({str(r['size']) for r in updates if (r['side'], str(r['price'])) == k}) > 1 for k in keys)
                # Multiple simultaneous snapshots and snapshot/update ordering lack sequence proof.
                ambiguous = conflict or bool(books and updates) or len(books) > 1
                if ordering == 'reverse_ties':
                    group = list(reversed(group))
                elif ordering == 'source_time_within_receive_ties':
                    group = sorted(group, key=lambda r: r['timestamp'])
                for row in group:
                    if row['event_type'] == 'book':
                        nb, na = levels(row['bids']), levels(row['asks'])
                        if bids is not None:
                            comparisons.append({'touch_match': touch(bids, asks) == touch(nb, na),
                                                'full_book_match': bids == nb and asks == na})
                        bids, asks = nb, na
                        uncertain = False
                    elif row['event_type'] == 'price_change' and bids is not None:
                        if row['side'] not in ['BUY', 'SELL'] or row['price'] is None or row['size'] is None:
                            uncertain = True
                            continue
                        book = bids if row['side'] == 'BUY' else asks
                        price, size = float(row['price']), float(row['size'])
                        if size == 0:
                            book.pop(price, None)
                        else:
                            book[price] = size
                    else:
                        continue
                    latest = row
                uncertain = uncertain or ambiguous
                if bids is not None and latest is not None:
                    states.append({'received': received.timestamp(), 'source': latest['timestamp'].timestamp(),
                                   'touch': touch(bids, asks), 'ambiguous_since_seed': uncertain})
            grid_rows = []
            for grid in grids:
                previous = [s for s in states if s['received'] <= grid]
                state = previous[-1] if previous else None
                t = state['touch'] if state else None
                valid = bool(t and 0 < t[0] <= t[1] < 1 and t[1] - t[0] <= .05 + 1e-12 and min(t[2:]) >= 10)
                fresh = bool(state and 0 <= grid - state['received'] <= 120 and state['source'] <= state['received'])
                grid_rows.append({'grid': grid, 'state': state, 'receipt_fresh_quality': valid and fresh,
                                  'source_fresh_quality': bool(valid and fresh and 0 <= grid-state['source'] <= 120),
                                  'receipt_fresh_quality_no_known_tie': bool(valid and fresh and not state['ambiguous_since_seed'])})
            runs[ordering] = {'grids': grid_rows, 'snapshot_comparisons': comparisons}
        baseline = runs['stored']['grids']
        sensitive = sum(any(runs[o]['grids'][i]['state'] and b['state'] and
                            runs[o]['grids'][i]['state']['touch'] != b['state']['touch']
                            for o in runs if o != 'stored') for i, b in enumerate(baseline))
        lags = [(r['timestamp_received']-r['timestamp']).total_seconds() for r in records]
        results.append({'market_id': cid, 'events': len(records), 'grid_count': len(grids),
                        'non_null_best_bid': sum(r['best_bid'] is not None for r in records),
                        'non_null_best_ask': sum(r['best_ask'] is not None for r in records),
                        'negative_source_lags': sum(x < 0 for x in lags),
                        'source_lags_over_120s': sum(x > 120 for x in lags),
                        'touch_order_sensitive_grids': sensitive,
                        'runs': runs})
    write(OUT/'details.json', results)
    summary = {'at': now().isoformat(), 'markets': len(results), 'events': len(rows),
               'planned_grids': len(grids)*len(results),
               'touch_order_sensitive_grids': sum(r['touch_order_sensitive_grids'] for r in results),
               'non_null_best_bid': sum(r['non_null_best_bid'] for r in results),
               'non_null_best_ask': sum(r['non_null_best_ask'] for r in results),
               'negative_source_lags': sum(r['negative_source_lags'] for r in results),
               'source_lags_over_120s': sum(r['source_lags_over_120s'] for r in results),
               'ordering_results': {}, 'fully_admitted_forecasts': 0,
               'limitations': ['Three orderings are sensitivity checks, not exhaustive possible sequences.',
                              'A later matching snapshot does not prove every intermediate state.',
                              'No known tie is not evidence of feed completeness or historical status.',
                              'Current-grid diagnostics only; no forecast targets or performance scored.']}
    for ordering in results[0]['runs']:
        gs = [g for r in results for g in r['runs'][ordering]['grids']]
        cs = [c for r in results for c in r['runs'][ordering]['snapshot_comparisons']]
        summary['ordering_results'][ordering] = {
            **{k: sum(g[k] for g in gs) for k in ['receipt_fresh_quality', 'source_fresh_quality', 'receipt_fresh_quality_no_known_tie']},
            'snapshot_comparisons': len(cs), 'touch_matches': sum(c['touch_match'] for c in cs),
            'full_book_matches': sum(c['full_book_match'] for c in cs)}
    write(OUT/'report.json', summary)
    paths = [OUT/'details.json', OUT/'report.json', PARENT/'manifest.json', Path(__file__).resolve(),
             REPO_ROOT/'eventx/tasks/audit_v7_archive_sample_20261025_v03.py']
    write(OUT/'manifest.json', {'files': {str(p.relative_to(REPO_ROOT)): sha(p) for p in paths}})
    print(json.dumps(summary, indent=2))


if __name__ == '__main__':
    main()
