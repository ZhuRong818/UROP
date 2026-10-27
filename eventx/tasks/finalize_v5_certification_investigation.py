"""Publish source-only/synthetic certification investigation evidence; no research run."""

from datetime import datetime, timezone
import hashlib
import io
import json
from pathlib import Path
import unittest

from threadpoolctl import threadpool_limits

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT/'data/v5/certification_resolution_20260910'


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    OUT.mkdir(parents=True, exist_ok=False)
    prior = ['data/v5/group_t_candidate_20260910/manifest.json',
             'data/v5/family_certification_20260910/manifest.json',
             'data/v5/revision_v1_1_20260910/manifest.json',
             'eventx/release/v4/holdout_implementation_manifest.json']
    verified = 0
    for name in prior:
        for record in json.loads((ROOT/name).read_text())['artifacts']:
            if digest(ROOT/record['path']) != record['sha256']:
                raise ValueError('Hash conflict: '+record['path'])
            verified += 1
    modules = ['test_v5_certification_resolution', 'test_v5_revision_v1_1',
               'test_v5_experiment_v1', 'test_v5_content_integration',
               'test_v5_label_blind_contract', 'test_v5_corrected_pipeline',
               'test_algorithm_audit', 'test_v5_source_readiness', 'test_v5_recovery_requests']
    suite = unittest.TestSuite(unittest.defaultTestLoader.loadTestsFromName('eventx.tasks.'+m) for m in modules)
    buffer = io.StringIO()
    with threadpool_limits(limits=2):
        result = unittest.TextTestRunner(stream=buffer, verbosity=2).run(suite)
    (OUT/'tests.txt').write_text(buffer.getvalue())
    if not result.wasSuccessful():
        raise RuntimeError('Tests failed; retained output; no certification')
    receipts, evidence = [], []
    for path in sorted((ROOT/'data/v5/provenance_recovery_20260908').glob('certification_*.json')):
        row = json.loads(path.read_text())
        receipts.append({'name': row['name'], 'status': row['status'],
                         'http_status': row.get('http_status'), 'rows': row.get('rows'),
                         'error_type': row.get('error_type')})
        evidence.append(path)
        if row.get('data_path'):
            data = ROOT/row['data_path']
            if digest(data) != row['data_sha256']:
                raise ValueError('Source receipt mismatch')
            evidence.append(data)
    report = {'created_at': datetime.now(timezone.utc).isoformat(),
              'status': 'investigated_not_certified_provider_evidence_and_inference_design_needed',
              'tests_run': result.testsRun, 'test_failures': len(result.failures),
              'test_errors': len(result.errors), 'prior_manifest_records_verified': verified,
              'hash_mismatches': 0, 'source_attempts': receipts,
              'source_certified': False, 'inference_certified': False, 'final_families_certified': False,
              'family_review': json.loads((ROOT/'data/v5/family_certification_20260910/report.json').read_text()),
              'inference': 'grouped-t candidate failed stress scenarios; not adopted',
              'research_labels_read': False, 'provider_message_sent': False,
              'v4_modified': False, 'new_model_frozen': False}
    (OUT/'report.json').write_text(json.dumps(report, indent=2)+'\n')
    paths = [Path(__file__), ROOT/'eventx/tasks/test_v5_certification_resolution.py',
             ROOT/'eventx/tasks/prepare_v5_certification_probe.py',
             ROOT/'eventx/release/v5/CERTIFICATION_RESOLUTION_20260910.md',
             ROOT/'eventx/release/v5/LUMID_CERTIFICATION_REQUEST_20260910.md',
             *[ROOT/p for p in prior], *evidence,
             *sorted((ROOT/'eventx/release/v5/certification_requests_20260910').glob('*.sql')),
             *sorted((ROOT/'data/v5/certification_probe_20260910').iterdir()),
             *sorted(OUT.iterdir())]
    (OUT/'manifest.json').write_text(json.dumps({'status': 'investigation_evidence_not_research_freeze',
        'artifacts': [{'path': str(p.relative_to(ROOT)), 'sha256': digest(p)} for p in paths]}, indent=2)+'\n')
    print(json.dumps(report, indent=2), flush=True)


if __name__ == '__main__':
    main()
