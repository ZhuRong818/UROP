"""Equivalence of BoundedInputs (incremental, pruned) vs unbounded Inputs on the readiness journal."""
import json
import math
import sys

from eventx.v7 import forecast_runtime_20261026_v02 as rt


def main(horizon=2700):
    src = rt.BASE/'readiness'
    samples = rt.load_cohort()
    offsets, corrected, pos = [], [], 0
    with (src/'journal.jsonl').open('rb') as f:
        for line in f:
            pos += len(line)
            offsets.append(pos)
            corrected.append(json.loads(line).get('corrected_epoch'))
    def prefix(at):  # byte offset after the last record stamped <= at
        k = max(i for i, c in enumerate(corrected) if c is not None and c <= at)
        return offsets[k]
    first = min(c for c in corrected if c is not None)
    last = max(c for c in corrected if c is not None)
    bounded = rt.BoundedInputs(src, samples, limit=prefix(first+60), horizon=horizon)
    checks, mismatches, pruned = 0, [], False
    events = sorted([(t+5, 'decision', t) for t in rt.grids(math.ceil(first/300)*300, int(last)-5)] +
                    [(t+1920, 'endpoint', t) for t in rt.grids(math.ceil(first/300)*300, int(last)-1925)])
    for at, kind, t in events:
        lim = prefix(at)
        if lim < bounded.offset:
            continue
        bounded.advance(lim)
        if bounded.cutoff is None or (kind == 'decision' and t < bounded.cutoff+rt.SAFE_LOOKBACK) or (kind == 'endpoint' and t+1800 < bounded.cutoff+rt.SAFE_LOOKBACK):
            continue
        pruned = True
        full = rt.Inputs(src, samples, lim)
        for s in samples:
            cid = s['market_id']
            a = bounded.current(cid, t) if kind == 'decision' else bounded.endpoint(cid, t)
            b = full.current(cid, t) if kind == 'decision' else full.endpoint(cid, t)
            checks += 1
            if a != b:
                mismatches.append({'kind': kind, 't': t, 'market_id': cid, 'bounded': str(a)[:120], 'full': str(b)[:120]})
    ready = sum(1 for m in [] if m)
    report = {'horizon_seconds': horizon, 'checks': checks, 'mismatches': len(mismatches), 'examples': mismatches[:5],
              'pruning_exercised': pruned, 'final_cutoff': bounded.cutoff, 'passed': pruned and checks > 0 and not mismatches}
    rt.v01.write_new(rt.REL/'bounded_equivalence_qa.json', report)
    print(json.dumps(report, indent=1))


if __name__ == '__main__':
    main(*(int(a) for a in sys.argv[1:]))
