"""Bounded catalog/SQL inventory for opened V6 source-history surfaces."""
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import sys

import httpx

from eventx.settings import ApiSettings

HERE = Path(__file__).resolve().parent
OUT = HERE / 'v6_history_surface_inventory_20260928'
SCRIPT = Path(__file__).resolve()
PATHS = {
    'provenance_tables': '/catalog/schemas/provenance/tables',
    'prediction_market_tables': '/catalog/schemas/prediction_markets/tables',
}
SQL = """SELECT table_schema, table_name
FROM information_schema.tables
WHERE table_schema IN ('provenance', 'prediction_markets')
ORDER BY table_schema, table_name
LIMIT 200"""


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write(path, obj):
    path.write_text(json.dumps(obj, indent=2, sort_keys=True) + '\n')


def prepare():
    OUT.mkdir(exist_ok=False)
    (OUT / 'query.sql').write_text(SQL + '\n')
    write(OUT / 'receipt.json', {
        'created_at_utc': datetime.now(timezone.utc).isoformat(),
        'written_before_requests': True,
        'scope': 'two catalog table-list GETs plus one bounded information_schema table-name query; no market/news rows, labels or protected data',
        'paths': PATHS,
        'script_sha256': sha(SCRIPT),
        'query_sha256': sha(OUT / 'query.sql'),
    })


def run():
    receipt = json.loads((OUT / 'receipt.json').read_text())
    if sha(SCRIPT) != receipt['script_sha256'] or sha(OUT / 'query.sql') != receipt['query_sha256']:
        raise ValueError('receipt input changed')
    if (OUT / 'report.json').exists():
        raise FileExistsError('report already exists')
    settings = ApiSettings.from_env()
    report = {'base_url': settings.base_url, 'queried_at_utc': datetime.now(timezone.utc).isoformat(), 'catalog': {}}
    with httpx.Client(base_url=settings.base_url, headers={'Authorization': 'Bearer ' + settings.token}, timeout=30, follow_redirects=True) as client:
        for name, path in PATHS.items():
            response = client.get(path)
            item = {'status': response.status_code, 'response_sha256': hashlib.sha256(response.content).hexdigest()}
            if response.status_code == 200:
                try:
                    body = response.json()
                    item['top_level_type'] = type(body).__name__
                    if isinstance(body, list):
                        item['items'] = body[:200]
                    elif isinstance(body, dict):
                        item['keys'] = sorted(body)
                        item['items'] = {key: value[:200] for key, value in body.items() if isinstance(value, list)}
                except ValueError:
                    item['parse_error'] = True
            report['catalog'][name] = item
        response = client.post('/retrieve', json={'sql': (OUT / 'query.sql').read_text(), 'output_format': 'jsonl'})
        item = {'retrieve_status': response.status_code, 'rows': []}
        if response.status_code == 200:
            try:
                info = response.json()
                uri = info.get('materialized_uri')
                if uri:
                    materialized = client.get(uri)
                    item['materialized_status'] = materialized.status_code
                    if materialized.status_code == 200:
                        item['rows'] = [json.loads(x) for x in materialized.text.splitlines() if x.strip()][:200]
                else:
                    item['response_keys'] = sorted(info)
            except ValueError:
                item['parse_error'] = True
        report['information_schema'] = item
    report['historical_coverage_certified'] = False
    report['predictive_admissions'] = 0
    write(OUT / 'report.json', report)
    write(OUT / 'manifest.json', {'outputs': {name: sha(OUT / name) for name in ('query.sql', 'receipt.json', 'report.json')}})
    print(json.dumps(report, indent=2, sort_keys=True))


if __name__ == '__main__':
    {'prepare': prepare, 'run': run}[sys.argv[1]]()
