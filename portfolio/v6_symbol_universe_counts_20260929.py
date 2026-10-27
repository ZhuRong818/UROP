"""Read-only live count check of the reported 7,851-to-7,258 roster clue."""
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import sys

import httpx
from eventx.settings import ApiSettings

HERE = Path(__file__).resolve().parent
OUT = HERE / 'v6_symbol_universe_counts_20260929'
SCRIPT = Path(__file__).resolve()
SQL = """SELECT COUNT(*) AS total_rows,
 COUNT(DISTINCT symbol) AS distinct_symbols,
 COUNT(*) FILTER (WHERE is_etf IS TRUE OR is_fund IS TRUE) AS etf_or_fund_rows,
 COUNT(*) FILTER (WHERE NOT (is_etf IS TRUE OR is_fund IS TRUE)) AS neither_etf_nor_fund_rows,
 COUNT(*) FILTER (WHERE is_actively_trading IS TRUE) AS active_rows,
 COUNT(*) FILTER (WHERE is_actively_trading IS TRUE AND NOT (is_etf IS TRUE OR is_fund IS TRUE)) AS active_plain_rows,
 MAX(ingest_ts) AS latest_ingest
FROM reference.symbol_universe"""


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write(path, obj):
    path.write_text(json.dumps(obj, indent=2, sort_keys=True) + '\n')


def prepare():
    OUT.mkdir(exist_ok=False)
    (OUT / 'query.sql').write_text(SQL + '\n')
    write(OUT / 'receipt.json', {'created_at_utc': datetime.now(timezone.utc).isoformat(), 'written_before_requests': True,
        'scope': 'aggregate fields only from reference.symbol_universe; no row text, outcomes or protected data',
        'script_sha256': sha(SCRIPT), 'query_sha256': sha(OUT / 'query.sql')})


def run():
    receipt = json.loads((OUT / 'receipt.json').read_text())
    if sha(SCRIPT) != receipt['script_sha256'] or sha(OUT / 'query.sql') != receipt['query_sha256']:
        raise ValueError('receipt input changed')
    if (OUT / 'report.json').exists():
        raise FileExistsError('report already exists')
    settings = ApiSettings.from_env()
    report = {'base_url': settings.base_url, 'queried_at_utc': datetime.now(timezone.utc).isoformat()}
    with httpx.Client(base_url=settings.base_url, headers={'Authorization': 'Bearer ' + settings.token}, timeout=30, follow_redirects=True) as client:
        response = client.post('/retrieve', json={'sql': SQL, 'output_format': 'jsonl'})
        report['retrieve_status'] = response.status_code
        if response.status_code == 200:
            uri = response.json().get('materialized_uri')
            if uri:
                materialized = client.get(uri)
                report['materialized_status'] = materialized.status_code
                if materialized.status_code == 200:
                    report['rows'] = [json.loads(x) for x in materialized.text.splitlines() if x.strip()][:1]
        else:
            report['error_prefix'] = response.text[:300]
    write(OUT / 'report.json', report)
    write(OUT / 'manifest.json', {'outputs': {x: sha(OUT / x) for x in ('query.sql', 'receipt.json', 'report.json')}})
    print(json.dumps(report, indent=2, sort_keys=True))


if __name__ == '__main__':
    {'prepare': prepare, 'run': run}[sys.argv[1]]()
