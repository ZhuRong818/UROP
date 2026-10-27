"""Compare three V6 catalog run records with exact-UUID warehouse SQL lookup."""
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import sys

import httpx

from eventx.settings import ApiSettings, REPO_ROOT

OUT = REPO_ROOT / 'data/v6/lineage_sql_surface_20260928'
PRIOR = REPO_ROOT / 'data/v6/lineage_surface_conflict_20260928/lineage.jsonl'
SCRIPT = REPO_ROOT / 'eventx/tasks/verify_v6_lineage_sql_surface_20260928.py'
IDS = (
    'fd734424-86f2-4d65-a67c-868d6f80730a',
    '592ebc42-79ad-4b33-af2d-628b5edb6167',
    '86c568d4-f947-43e2-950b-8cf740690a9e',
)


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write(path, value):
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + '\n')


def prepare():
    OUT.mkdir(exist_ok=False)
    values = ', '.join("'" + rid + "'::uuid" for rid in IDS)
    sql = f"""SELECT run_id::text AS run_id, endpoint_id, started_at, ended_at,
       status, rows_inserted, rows_updated, rows_failed,
       args->>'to' AS requested_to
FROM provenance.runs
WHERE run_id IN ({values})
ORDER BY run_id
LIMIT 3"""
    (OUT / 'query.sql').write_text(sql + '\n')
    write(OUT / 'receipt.json', {
        'created_at_utc': datetime.now(timezone.utc).isoformat(),
        'written_before_request': True,
        'query_sha256': sha(OUT / 'query.sql'),
        'inputs': {str(p.relative_to(REPO_ROOT)): sha(p) for p in (PRIOR, SCRIPT)},
        'scope': 'three opened-development failed run IDs; exact UUID lookup only',
    })


def run():
    receipt = json.loads((OUT / 'receipt.json').read_text())
    if receipt['query_sha256'] != sha(OUT / 'query.sql') or receipt['inputs'] != {str(p.relative_to(REPO_ROOT)): sha(p) for p in (PRIOR, SCRIPT)}:
        raise ValueError('query inputs changed')
    if (OUT / 'report.json').exists():
        raise FileExistsError('report exists')
    settings = ApiSettings.from_env()
    sql = (OUT / 'query.sql').read_text()
    result = {'base_url': settings.base_url, 'queried_at_utc': datetime.now(timezone.utc).isoformat()}
    with httpx.Client(base_url=settings.base_url, headers={'Authorization': 'Bearer ' + settings.token}, timeout=30) as client:
        response = client.post('/retrieve', json={'sql': sql, 'output_format': 'jsonl'})
        result['retrieve_status'] = response.status_code
        if response.status_code == 200:
            info = response.json()
            uri = info.get('materialized_uri')
            if uri:
                materialized = client.get(uri)
                result['materialized_status'] = materialized.status_code
                if materialized.status_code == 200:
                    result['rows'] = [json.loads(line) for line in materialized.text.splitlines() if line.strip()]
                else:
                    result['rows'] = []
            else:
                result['response_keys'] = sorted(info)
                result['rows'] = []
        else:
            try:
                body = response.json()
                result['error_keys'] = sorted(body) if isinstance(body, dict) else []
            except ValueError:
                result['error_keys'] = []
            result['rows'] = []
    write(OUT / 'report.json', {
        **result,
        'catalog_prior_200': 3,
        'exact_sql_matches': len({r.get('run_id') for r in result['rows']} & set(IDS)),
        'coverage_certified': False,
        'predictive_admissions': 0,
    })
    write(OUT / 'manifest.json', {
        'inputs': receipt['inputs'],
        'outputs': {name: sha(OUT / name) for name in ('query.sql', 'receipt.json', 'report.json')},
    })
    print(json.dumps(json.loads((OUT / 'report.json').read_text()), indent=2, sort_keys=True))


if __name__ == '__main__':
    {'prepare': prepare, 'run': run}[sys.argv[1]]()
