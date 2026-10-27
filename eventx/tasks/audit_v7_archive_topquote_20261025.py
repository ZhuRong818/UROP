"""Coverage of direct top quotes, separate from frozen depth-feature forecasting."""
from bisect import bisect_right
from collections import defaultdict
from datetime import datetime
import json
from pathlib import Path
import pyarrow.parquet as pq
from eventx.tasks.audit_v7_archive_sample_20261025_v03 import START, END
from eventx.tasks.discover_v7_direct_pilot_20261022 import REPO_ROOT, now, sha, write

PARENT = REPO_ROOT/'data/v7/archive_sample_20261025_v03/attempt_20261025T011030Z_66d836'
OUT = REPO_ROOT/'data/v7/archive_topquote_audit_20261025'


def main():
    for path, digest in json.loads((PARENT/'manifest.json').read_text())['files'].items():
        assert sha(REPO_ROOT/path) == digest, path
    OUT.mkdir(exist_ok=False)
    rows = pq.read_table(PARENT/'selected_yes_events.parquet').to_pylist()
    by = defaultdict(lambda: defaultdict(list))
    for row in rows:
        by[row['market'].decode()][row['timestamp_received']].append(row)
    results = []
    for cid, groups in sorted(by.items()):
        states = []
        for received, group in sorted(groups.items()):
            quotes = [r for r in group if r['best_bid'] is not None and r['best_ask'] is not None]
            if not quotes:
                # A snapshot without direct top fields is a conservative reset, not fabricated top-quote evidence.
                states.append({'at': received.timestamp(), 'valid': False, 'reason': 'no_direct_topquote'})
                continue
            pairs = {(float(r['best_bid']), float(r['best_ask'])) for r in quotes}
            unique = len(pairs) == 1
            bid, ask = next(iter(pairs)) if unique else (None, None)
            valid = bool(unique and 0 < bid <= ask < 1 and ask-bid <= .05+1e-12
                         and all(0 <= (received-r['timestamp']).total_seconds() <= 120 for r in quotes))
            states.append({'at': received.timestamp(), 'valid': valid, 'unique': unique,
                           'reason': 'valid' if valid else 'ambiguous_or_invalid',
                           'oldest_source': min(r['timestamp'].timestamp() for r in quotes)})
        times = [s['at'] for s in states]
        def at(t):
            i = bisect_right(times, t)-1
            return i >= 0 and states[i]['valid'] and 0 <= t-times[i] <= 120 and t-states[i]['oldest_source'] <= 120
        def covers(a,b):
            if not at(a):
                return False
            i,j = bisect_right(times,a),bisect_right(times,b)
            prev = states[i-1]
            for k in range(i,j):
                current = states[k]
                if not current['valid'] or current['at']-prev['at'] > 120 or current['at']-prev['oldest_source'] > 120:
                    return False
                prev = current
            return b-prev['at'] <= 120 and b-prev['oldest_source'] <= 120
        grids = list(range(int(START+1800),int(END-1800),300))
        results.append({'market_id':cid,'receive_groups':len(states),'valid_unique_groups':sum(s['valid'] for s in states),
                        'conflicting_topquote_groups':sum(s.get('unique') is False for s in states),
                        'planned_grids':len(grids),'fresh_current_grids':sum(at(t) for t in grids),
                        'fresh_paired_grids':sum(at(t) and at(t+1800) for t in grids),
                        'continuous_forward_grids':sum(covers(t,t+1800) for t in grids),
                        'continuous_history_and_forward_grids':sum(covers(t-1800,t+1800) for t in grids)})
    summary = {'at':now().isoformat(),'markets':len(results),
               **{k:sum(r[k] for r in results) for k in results[0] if k!='market_id'},
               'depth_available_for_this_method':False,'historical_status_verified':False,
               'fully_admitted_forecasts':0,'performance_computed':False,
               'scope':'Source coverage only. Separate proposed price-only method; frozen depth model unchanged.',
               'interpretation':'Fresh endpoint pairs do not establish continuous coverage; ambiguous tied top quotes invalidate state until a later unambiguous quote. No carry through unknown gaps.'}
    write(OUT/'market_metrics.json',results);write(OUT/'report.json',summary)
    paths=[OUT/'report.json',OUT/'market_metrics.json',PARENT/'manifest.json',Path(__file__).resolve(),REPO_ROOT/'eventx/tasks/audit_v7_archive_sample_20261025_v03.py']
    write(OUT/'manifest.json',{'files':{str(p.relative_to(REPO_ROOT)):sha(p) for p in paths}})
    print(json.dumps(summary,indent=2))


if __name__=='__main__':
    main()
