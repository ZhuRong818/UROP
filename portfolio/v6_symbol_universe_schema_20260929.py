"""Read-only live schema check for the relayed symbol-universe evidence."""
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import sys

import httpx
from eventx.settings import ApiSettings

HERE = Path(__file__).resolve().parent
OUT = HERE / 'v6_symbol_universe_schema_20260929'
SCRIPT = Path(__file__).resolve()
SQL = """SELECT column_name, data_type, ordinal_position
FROM information_schema.columns
WHERE table_schema = 'reference' AND table_name = 'symbol_universe'
ORDER BY ordinal_position LIMIT 100"""


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
        'scope': 'read-only reference.symbol_universe schema metadata; no rows, outcomes or protected data',
        'catalog_path': '/catalog/tables/reference/symbol_universe/schema.json',
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
    report = {'base_url': settings.base_url, 'queried_at_utc': datetime.now(timezone.utc).isoformat()}
    with httpx.Client(base_url=settings.base_url, headers={'Authorization': 'Bearer ' + settings.token}, timeout=30, follow_redirects=True) as client:
        response = client.get(receipt['catalog_path'])
        report['catalog_status'] = response.status_code
        report['catalog_response_sha256'] = hashlib.sha256(response.content).hexdigest()
        if response.status_code == 200:
            report['catalog_schema'] = response.json()
        response = client.post('/retrieve', json={'sql': SQL, 'output_format': 'jsonl'})
        report['retrieve_status'] = response.status_code
        if response.status_code == 200:
            info = response.json()
            uri = info.get('materialized_uri')
            if uri:
                materialized = client.get(uri)
                report['materialized_status'] = materialized.status_code
                if materialized.status_code == 200:
                    report['columns'] = [json.loads(x) for x in materialized.text.splitlines() if x.strip()][:100]
            else:
                report['retrieve_response_keys'] = sorted(info)
    write(OUT / 'report.json', report)
    write(OUT / 'manifest.json', {'outputs': {x: sha(OUT / x) for x in ('query.sql', 'receipt.json', 'report.json')}})
    print(json.dumps({'catalog_status': report.get('catalog_status'), 'retrieve_status': report.get('retrieve_status'), 'columns': report.get('columns', [])}, indent=2))


if __name__ == '__main__':
    {'prepare': prepare, 'run': run}[sys.argv[1]]()
