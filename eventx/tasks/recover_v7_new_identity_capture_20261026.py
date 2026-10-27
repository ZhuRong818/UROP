"""Outcome-blind recovery of DNS-failed hours for the new-identity test (protocol deviation).

The frozen capture lost 74 hours to a local DNS outage ([Errno 8] ConnectError) on both
permitted attempts. Before any evaluation, this refetches ONLY those hours with the same
fetch code into a separate directory, builds a recovered source with its own manifest, and
evaluates once from it. The original source/ stays untouched and is not evaluated.
Genuine 404 hours remain missing.
"""
import argparse
from concurrent.futures import ThreadPoolExecutor, as_completed
import json
from pathlib import Path

from eventx.tasks import run_v7_new_identity_test_20261026 as run
from eventx.tasks.discover_v7_direct_pilot_20261022 import REPO_ROOT, now, sha, write
from eventx.v7.family_capture_20261025_v02 import fetch

ORIG = run.BASE
RECOVERED = REPO_ROOT/'data/v7/new_identity_test_20261026_recovered'


def recover():
    run.verify_setup()
    run.verify(ORIG/'source/capture_manifest.json')
    if (ORIG/'evaluation').exists():
        raise RuntimeError('Original already evaluated; recovery would not be outcome-blind')
    out = RECOVERED/'source'
    out.mkdir(parents=True, exist_ok=False)
    (RECOVERED/'cohort').symlink_to(ORIG/'cohort', target_is_directory=True)
    receipts = {r['hour']: r for r in json.loads((ORIG/'source/file_receipts.json').read_text())}
    dns = [h for h, r in receipts.items() if not r['complete'] and r.get('error') == 'ConnectError']
    write(RECOVERED/'recovery_plan.json', {'at': now().isoformat(), 'hours': dns, 'reason': 'local DNS outage',
                                           'evaluation_opened_before': False, 'protocol_deviation': True})
    selected = run.load_cohort()
    excluded = set(json.loads(run.EX.read_text()))
    folder = out/'attempt_3'
    (folder/'hours').mkdir(parents=True)
    new = {}
    with ThreadPoolExecutor(max_workers=2) as pool:
        for f in as_completed([pool.submit(fetch, h, selected, excluded, folder) for h in dns]):
            r = dict(f.result(), attempt=3)
            new[r['hour']] = r
    (out/'hours').mkdir()
    final = []
    for hour, rec in receipts.items():
        rec = new[hour] if hour in new and new[hour]['complete'] else rec
        src = folder/'hours'/hour if rec['attempt'] == 3 else ORIG/'source'/f"attempt_{rec['attempt']}"/'hours'/hour
        (out/'hours'/hour).symlink_to(src, target_is_directory=True)
        final.append(rec)
    write(out/'file_receipts.json', final)
    write(out/'attempt_receipts.json', list(new.values()))
    report = {'at': now().isoformat(), 'phase': 'captured_recovered', 'files': len(final),
              'successful_files': sum(r['complete'] for r in final), 'recovered_hours': sum(r['complete'] for r in new.values()),
              'missing_hours': [r['hour'] for r in final if not r['complete']], 'protected_period_rows_read': 0}
    write(out/'capture_report.json', report)
    files = [out/'capture_report.json', out/'file_receipts.json', out/'attempt_receipts.json', ORIG/'source/capture_manifest.json',
             run.REL/'implementation_manifest.json']+list(folder.glob('hours/*/manifest.json'))
    write(out/'capture_manifest.json', {'files': {str(p.relative_to(REPO_ROOT)): sha(p) for p in files}})
    print(json.dumps(report), flush=True)


def evaluate():
    # Same frozen evaluator, pointed at the recovered source; writes RECOVERED/evaluation.
    run.BASE = RECOVERED
    run.evaluate()


def evaluate_v03():
    from eventx.tasks import evaluate_v7_new_identity_v03_20261026 as v03
    run.BASE = v03.BASE = RECOVERED
    v03.main()


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('phase', choices=['recover', 'evaluate', 'evaluate_v03'])
    {'recover': recover, 'evaluate': evaluate, 'evaluate_v03': evaluate_v03}[parser.parse_args().phase]()
