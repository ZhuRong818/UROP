"""Label-free health check of the running V02 prospective test (reads no endpoints or scores)."""
from collections import Counter
import json
import subprocess
import time

from eventx.v7 import forecast_runtime_20261026_v02 as rt


def main():
    receipt = json.loads((rt.BASE/'activation_receipt.json').read_text())
    src, em = rt.REPO_ROOT/receipt['source_path'], rt.BASE/'prospective/emitter'
    procs = subprocess.run(['pgrep', '-f', 'forecast_runtime_20261026_v02'], capture_output=True, text=True).stdout.split()
    clock = json.loads((src/'clock_state.json').read_text())
    status = {k: v for k, v in json.loads((em/'status.json').read_text()).items()} if (em/'status.json').exists() else {}
    decisions = Counter()
    reasons = Counter()
    if (em/'journal.jsonl').exists():
        for line in (em/'journal.jsonl').open():
            r = json.loads(line)
            if r['kind'] == 'decision':
                decisions[r['status']] += 1
                reasons.update(r['reasons'])
            if r['kind'] == 'emission_commit' and r['timely']:
                decisions['timely_commits'] += 1
    src_status = json.loads((src/'status.json').read_text())
    print(json.dumps({'now_utc': rt.iso(time.time()), 'processes': len(procs),
                      'source_age_s': round(time.time()-rt.stamp(src_status['at'])),
                      'ws': {k: v.get('status') for k, v in src_status.get('streams', {}).items()},
                      'clock_valid': clock['valid'], 'offset_ms': round((clock['offset_seconds'] or 0)*1000, 1),
                      'emitter_age_s': round(time.time()-status['at']) if status else None,
                      'decisions': dict(decisions), 'top_abstain_reasons': reasons.most_common(4),
                      'first_grid': rt.iso(receipt['first_grid']), 'evaluation_opens': rt.iso(receipt['open_after']+30)}, indent=1))


if __name__ == '__main__':
    main()
