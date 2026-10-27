"""Read-only live Finnhub n_symbols transitions in opened V6 interval."""
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import sys

import httpx
from eventx.settings import ApiSettings

HERE = Path(__file__).resolve().parent
OUT = HERE / 'v6_finnhub_universe_transitions_20260929'
SCRIPT = Path(__file__).resolve()
SQL = """WITH ordered AS (
 SELECT run_id, started_at, args->>'n_symbols' AS n_symbols,
 LAG(args->>'n_symbols') OVER (ORDER BY started_at, run_id) AS previous_n_symbols
 FROM provenance.runs
 WHERE endpoint_id = 'finnhub:company-news'
   AND started_at >= TIMESTAMPTZ '2026-05-17T00:00:00Z'
   AND started_at < TIMESTAMPTZ '2026-07-22T00:00:00Z'
)
SELECT run_id, started_at, previous_n_symbols, n_symbols
FROM ordered
WHERE n_symbols IS DISTINCT FROM previous_n_symbols
ORDER BY started_at, run_id LIMIT 50"""


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write(path, obj):
    path.write_text(json.dumps(obj, indent=2, sort_keys=True) + '\n')


def prepare():
    OUT.mkdir(exist_ok=False)
    (OUT / 'query.sql').write_text(SQL + '\n')
    write(OUT / 'receipt.json', {'created_at_utc': datetime.now(timezone.utc).isoformat(), 'written_before_requests': True,
        'scope': 'Finnhub endpoint run n_symbols transitions in opened V6 dates; no news rows, markets, outcomes or protected data',
        'script_sha256': sha(SCRIPT), 'query_sha256': sha(OUT / 'query.sql')})


def run():
    receipt = json.loads((OUT / 'receipt.json').read_text())
    if sha(SCRIPT) != receipt['script_sha256'] or sha(OUT / 'query.sql') != receipt['query_sha256']:
        raise ValueError('receipt input changed')
    if (OUT / 'report.json').exists():
        raise FileExistsError('report already exists')
    settings = ApiSettings.from_env()
    report = {'base_url': settings.base_url, 'queried_at_utc': datetime.now(timezone.utc).isoformat()}
    with httpx.Client(base_url=settings.base_url, headers={'Authorization': 'Bearer ' + settings.token}, timeout=45, follow_redirects=True) as client:
        response = client.post('/retrieve', json={'sql': SQL, 'output_format': 'jsonl'})
        report['retrieve_status'] = response.status_code
        if response.status_code == 200:
            uri = response.json().get('materialized_uri')
            if uri:
                materialized = client.get(uri)
                report['materialized_status'] = materialized.status_code
                if materialized.status_code == 200:
                    report['rows'] = [json.loads(x) for x in materialized.text.splitlines() if x.strip()][:50]
        else:
            report['error_prefix'] = response.text[:300]
    write(OUT / 'report.json', report)
    write(OUT / 'manifest.json', {'outputs': {x: sha(OUT / x) for x in ('query.sql', 'receipt.json', 'report.json')}})
    print(json.dumps(report, indent=2, sort_keys=True))


if __name__ == '__main__':
    {'prepare': prepare, 'run': run}[sys.argv[1]]()
