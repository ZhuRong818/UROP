"""Feature-only replay of a new measurement contract; no targets or model fitting."""
from collections import Counter, defaultdict
import json
from pathlib import Path
import numpy as np
import pyarrow as pa
import pyarrow.parquet as pq
from eventx.tasks.audit_v7_live_input_compatibility_20261026 import BASE, DEV, SRC, REPO_ROOT
from eventx.tasks.discover_v7_direct_pilot_20261022 import now, sha, write, verify_originals
from eventx.tasks.run_v7_archive_week_pilot_20261025 import verify
from eventx.tasks.audit_v7_quote_shadow_20261024 import chain
from eventx.v7.live_quote_inputs_20261026 import project_ws
from eventx.v7.source_time_quote_inputs_20261026 import SourceTimeQuoteTape, FEATURES, CONTRACT
from eventx.v7.quote_experiment_20261024 import stamp

OUT = BASE / 'source_time_v2'

def main():
    if (OUT / 'report.json').exists():
        raise RuntimeError('Completed replay exists; create a new version')
    OUT.mkdir(parents=True, exist_ok=True)
    verify_originals(); verify(BASE / 'manifest.json')
    verify(DEV / 'source_dev/capture_manifest.json')
    write(OUT / 'audit_receipt.json', {'started_at': now().isoformat(), 'scope': 'Features only', 'labels_read': False})
    reference = pq.read_table(DEV / 'development/grid_ledger.parquet', columns=['market_id', 'date', 't', 'current_valid']).to_pylist()
    cohort = json.loads((DEV / 'cohort/cohorts.json').read_text())['development50']
    coverage = []; ledger = []
    for date in ['2026-05-07', '2026-05-08', '2026-05-09']:
        by = defaultdict(list)
        for h in range(24):
            folder = DEV / 'source_dev/hours' / (date + f'T{h:02}')
            verify(folder / 'manifest.json')
            for row in pq.read_table(folder / 'quotes.parquet').to_pylist():
                by[row['market'].decode()].append(row)
        count = Counter()
        for sample in cohort:
            cid = sample['market_id']; tape = SourceTimeQuoteTape(by[cid])
            for row in (r for r in reference if r['date'] == date and r['market_id'] == cid):
                f = tape.features(row['t']); old = row['current_valid']
                count['grids'] += 1; count['v2_valid'] += f is not None
                count['v1_valid'] += old
                count['both_valid'] += old and f is not None
                count['v2_only'] += not old and f is not None
                count['v1_only'] += old and f is None
                ledger.append({'source': 'development', 'date': date, 'market_id': cid, 't': row['t'], 'features': f})
        coverage.append({'date': date, **count}); print(json.dumps(coverage[-1]), flush=True)
    samples = [json.loads(x) for x in (REPO_ROOT / 'eventx/release/v7/memory_quote_20261024/forward_cohort.jsonl').read_text().splitlines()]
    durable, wire = defaultdict(list), defaultdict(list)
    for rec in chain(SRC / 'journal.jsonl'):
        if rec['kind'] != 'ws_frame': continue
        p = SRC / 'objects' / rec['payload_sha256']; assert sha(p) == rec['payload_sha256']
        payload = json.loads(p.read_text())
        for dest, clock in [(durable, rec['available_at']), (wire, rec['response_received_at'])]:
            for row in project_ws(payload, clock, rec['response_received_at'], samples):
                dest[row['market'].decode()].append(row)
    previous = pq.read_table(BASE / 'live_input_ledger.parquet').to_pylist()
    live = []; differences = Counter(); live_ledger = []
    for sample in samples:
        cid = sample['market_id']; a = SourceTimeQuoteTape(durable[cid]); b = SourceTimeQuoteTape(wire[cid]); count = Counter()
        for row in (r for r in previous if r['market_id'] == cid):
            t = stamp(row['decision_at']); f = a.features(t); g = b.features(t)
            count['grids'] += 1; count['v2_quote_eligible'] += f is not None
            ready = bool(f is not None and row['transport_ready'] and row['status_ready'] and row['daily_grid_ready'])
            count['mechanically_ready'] += ready
            if (f is None) != (g is None): differences['eligibility'] += 1
            elif f is not None:
                for i, name in enumerate(FEATURES): differences[name] += abs(f[i]-g[i]) > 1e-12
            live_ledger.append({'market_id': cid, 't': t, 'features': f, 'mechanically_ready': ready,
                                'input_contract': CONTRACT, 'model_admitted': False})
        live.append({'market_id': cid, 'question': sample['question'], **count})
    pq.write_table(pa.Table.from_pylist(ledger), OUT / 'development_features.parquet')
    pq.write_table(pa.Table.from_pylist(live_ledger), OUT / 'live_features.parquet')
    report = {'completed_at': now().isoformat(), 'input_contract': CONTRACT, 'features': FEATURES,
              'development_coverage': coverage, 'live_coverage': live,
              'wire_vs_durable_differences': dict(differences), 'labels_read': False,
              'models_fit': False, 'forecasts_issued': 0, 'prospective_test_started': False,
              'readiness': 'SHARED_MEASUREMENT_IMPLEMENTED_REQUIRES_NEW_MODEL_AND_VALIDATION',
              'limitations': ['Availability and missing-event differences remain', 'Historical May collector deployment unverified',
                              'Different quote process; old model and performance do not transfer', 'Two live contracts do not establish broad coverage']}
    write(OUT / 'report.json', report)
    write(OUT / 'audit_receipt.json', {'completed_at': now().isoformat(), 'status': 'completed', 'scope': 'Features only; no targets, model fit or evaluation'})
    paths = list(OUT.iterdir()) + [Path(__file__).resolve(), REPO_ROOT / 'eventx/v7/source_time_quote_inputs_20261026.py',
             REPO_ROOT / 'eventx/tasks/check_v7_source_time_quote_inputs_20261026.py', BASE / 'manifest.json',
             DEV / 'source_dev/capture_manifest.json', DEV / 'development/manifest.json', DEV / 'cohort/cohorts.json']
    write(OUT / 'manifest.json', {'files': {str(p.relative_to(REPO_ROOT)): sha(p) for p in paths}})
    print(json.dumps(report, indent=2))

if __name__ == '__main__': main()
