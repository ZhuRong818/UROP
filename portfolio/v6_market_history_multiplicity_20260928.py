"""Bounded history check for the 15 opened V6 contract IDs."""
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import sys

import httpx

from eventx.settings import ApiSettings

HERE = Path(__file__).resolve().parent
OUT = HERE / 'v6_market_history_multiplicity_20260928'
SCRIPT = Path(__file__).resolve()
SCOPE = HERE.parent / 'data/v6/context_development_review_20260927/provider_scope.json'


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write(path, obj):
    path.write_text(json.dumps(obj, indent=2, sort_keys=True) + '\n')


def queries():
    scope = json.loads(SCOPE.read_text())
    ids = [x['contract_id'].split(':', 2)[-1] for x in scope['contracts'] if x['venue'] == 'polymarket']
    ticker = [x['contract_id'].split(':', 2)[-1] for x in scope['contracts'] if x['venue'] == 'kalshi']
    assert len(ids) == 14 and len(ticker) == 1
    assert all(x.startswith('0x') and len(x) == 66 and all(c in '0123456789abcdef' for c in x[2:]) for x in ids)
    assert all(c.isalnum() or c == '-' for c in ticker[0])
    quoted_ids = ','.join("'" + x + "'" for x in ids)
    return {
        'polymarket': f"""SELECT condition_id, COUNT(*) AS row_count,
 MIN(ingest_ts) AS first_ingest, MAX(ingest_ts) AS last_ingest,
 COUNT(DISTINCT source_run_id) AS run_count,
 COUNT(DISTINCT question) AS question_versions,
 COUNT(DISTINCT outcomes::text) AS outcome_versions,
 COUNT(DISTINCT (active, closed, archived, enable_order_book)) AS status_states
FROM prediction_markets.polymarket_markets
WHERE condition_id IN ({quoted_ids})
GROUP BY condition_id ORDER BY condition_id LIMIT 14""",
        'kalshi': f"""SELECT ticker, COUNT(*) AS row_count,
 MIN(ingest_ts) AS first_ingest, MAX(ingest_ts) AS last_ingest,
 COUNT(DISTINCT source_run_id) AS run_count,
 COUNT(DISTINCT title) AS title_versions,
 COUNT(DISTINCT (yes_sub_title, no_sub_title)) AS outcome_versions,
 COUNT(DISTINCT status) AS status_states
FROM prediction_markets.kalshi_markets
WHERE ticker = '{ticker[0]}'
GROUP BY ticker LIMIT 1""",
    }


def prepare():
    OUT.mkdir(exist_ok=False)
    q = queries()
    for key, sql in q.items():
        (OUT / f'{key}.sql').write_text(sql + '\n')
    write(OUT / 'receipt.json', {
        'created_at_utc': datetime.now(timezone.utc).isoformat(),
        'written_before_requests': True,
        'scope': 'aggregate only, exact 15 opened-development contracts; no article, price, resolution, protected data or model fitting',
        'script_sha256': sha(SCRIPT),
        'provider_scope_sha256': sha(SCOPE),
        'queries_sha256': {key: sha(OUT / f'{key}.sql') for key in q},
    })


def run():
    receipt = json.loads((OUT / 'receipt.json').read_text())
    q = queries()
    if sha(SCRIPT) != receipt['script_sha256'] or sha(SCOPE) != receipt['provider_scope_sha256']:
        raise ValueError('receipt input changed')
    if any(sha(OUT / f'{key}.sql') != receipt['queries_sha256'][key] for key in q):
        raise ValueError('query changed')
    if (OUT / 'report.json').exists():
        raise FileExistsError('report already exists')
    settings = ApiSettings.from_env()
    report = {'base_url': settings.base_url, 'queried_at_utc': datetime.now(timezone.utc).isoformat(), 'results': {}}
    with httpx.Client(base_url=settings.base_url, headers={'Authorization': 'Bearer ' + settings.token}, timeout=60, follow_redirects=True) as client:
        for key, sql in q.items():
            response = client.post('/retrieve', json={'sql': sql, 'output_format': 'jsonl'})
            item = {'retrieve_status': response.status_code, 'rows': []}
            if response.status_code == 200:
                info = response.json()
                uri = info.get('materialized_uri')
                if uri:
                    materialized = client.get(uri)
                    item['materialized_status'] = materialized.status_code
                    if materialized.status_code == 200:
                        item['rows'] = [json.loads(x) for x in materialized.text.splitlines() if x.strip()][:14]
                else:
                    item['response_keys'] = sorted(info)
            else:
                item['response_text_prefix'] = response.text[:300]
            report['results'][key] = item
    report['historical_coverage_certified'] = False
    report['predictive_admissions'] = 0
    write(OUT / 'report.json', report)
    write(OUT / 'manifest.json', {'outputs': {name: sha(OUT / name) for name in ('polymarket.sql', 'kalshi.sql', 'receipt.json', 'report.json')}})
    print(json.dumps(report, indent=2, sort_keys=True))


if __name__ == '__main__':
    {'prepare': prepare, 'run': run}[sys.argv[1]]()
