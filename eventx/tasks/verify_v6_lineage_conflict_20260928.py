"""Recheck three disputed V6 run IDs through the same scoped Lumid catalog API."""
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import sys

import httpx

from eventx.settings import ApiSettings, REPO_ROOT

OUT = REPO_ROOT / 'data/v6/lineage_surface_conflict_20260928'
PRIOR = REPO_ROOT / 'data/v6/scoped_source_evidence_20260927/lineage.jsonl'
SCOPE = REPO_ROOT / 'data/v6/context_development_review_20260927/provider_scope.json'
SCRIPT = REPO_ROOT / 'eventx/tasks/verify_v6_lineage_conflict_20260928.py'
IDS = {
    '189518836': 'fd734424-86f2-4d65-a67c-868d6f80730a',
    '197137081': '592ebc42-79ad-4b33-af2d-628b5edb6167',
    '201756152': '86c568d4-f947-43e2-950b-8cf740690a9e',
}


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write(path, value):
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + '\n')


def prepare():
    OUT.mkdir(exist_ok=False)
    scope = json.loads(SCOPE.read_text())
    exact = {str(a['article_id']): a['source_run_id'] for a in scope['articles']}
    if any(exact.get(aid) != rid for aid, rid in IDS.items()):
        raise ValueError('run IDs differ from fixed provider scope')
    write(OUT / 'spec.json', {
        'purpose': 'recheck only the three runs claimed absent in the relayed SQL ledger',
        'method': 'authenticated GET /catalog/lineage/run/{run_id}, no row text or outcomes',
        'run_ids': IDS,
        'interpretation': 'API presence establishes catalog run record, not a complete feed window or matching SQL deployment',
    })
    write(OUT / 'receipt.json', {
        'created_at_utc': datetime.now(timezone.utc).isoformat(),
        'written_before_requests': True,
        'spec_sha256': sha(OUT / 'spec.json'),
        'inputs': {str(p.relative_to(REPO_ROOT)): sha(p) for p in (PRIOR, SCOPE, SCRIPT)},
    })


def run():
    receipt = json.loads((OUT / 'receipt.json').read_text())
    if receipt['spec_sha256'] != sha(OUT / 'spec.json') or receipt['inputs'] != {str(p.relative_to(REPO_ROOT)): sha(p) for p in (PRIOR, SCOPE, SCRIPT)}:
        raise ValueError('probe inputs changed')
    if (OUT / 'report.json').exists():
        raise FileExistsError('report exists')
    old = {r['run_id']: r for r in (json.loads(line) for line in PRIOR.read_text().splitlines() if line.strip())}
    settings = ApiSettings.from_env()
    results = []
    with httpx.Client(base_url=settings.base_url, headers={'Authorization': 'Bearer ' + settings.token}, timeout=30) as client:
        for aid, rid in IDS.items():
            response = client.get('/catalog/lineage/run/' + rid)
            rec = {
                'article_id': aid, 'run_id': rid, 'http_status': response.status_code,
                'prior_http_status': old[rid]['http_status'],
                'prior_status': old[rid]['lineage']['status'],
                'checked_at_utc': datetime.now(timezone.utc).isoformat(),
            }
            if response.status_code == 200:
                row = response.json()
                if row.get('run_id') != rid:
                    raise ValueError('run ID mismatch')
                rec['lineage'] = {k: row.get(k) for k in ('run_id', 'endpoint_id', 'started_at', 'ended_at', 'status', 'rows_inserted', 'rows_updated', 'rows_failed')}
                rec['args'] = {k: v for k, v in (row.get('args') or {}).items() if k in ('to', 'n_symbols')}
                rec['error_category'] = 'abandoned_run_cleanup' if 'abandoned' in str(row.get('error_text') or '').lower() else 'other_or_empty'
            results.append(rec)
    with (OUT / 'lineage.jsonl').open('w') as stream:
        for row in results:
            stream.write(json.dumps(row, sort_keys=True) + '\n')
    report = {
        'catalog_api_base_url': settings.base_url,
        'prior_200': sum(r['prior_http_status'] == 200 for r in results),
        'current_200': sum(r['http_status'] == 200 for r in results),
        'runs_rechecked': len(results),
        'scope': 'three opened-development failed run IDs; no feed or market-status certificate',
        'interpretation': 'A catalog API record conflicting with a separate SQL ledger absence calls for deployment/auth/filter alignment; it does not establish coverage or justify a different ingestion-path claim.',
        'predictive_admissions': 0,
    }
    write(OUT / 'report.json', report)
    write(OUT / 'manifest.json', {
        'inputs': receipt['inputs'],
        'outputs': {name: sha(OUT / name) for name in ('spec.json', 'receipt.json', 'lineage.jsonl', 'report.json')},
    })
    print(json.dumps(report, indent=2, sort_keys=True))


if __name__ == '__main__':
    {'prepare': prepare, 'run': run}[sys.argv[1]]()
