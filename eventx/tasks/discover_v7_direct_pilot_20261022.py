"""Metadata-only discovery and dated health receipt for a new V7 source pilot."""
import hashlib
import json
import uuid
from datetime import datetime, timedelta, timezone
from urllib.parse import urlsplit
import httpx
from eventx.settings import ApiSettings, REPO_ROOT

BASE = REPO_ROOT / 'data/v7/direct_source_pilot_20261022'
RELEASE = REPO_ROOT / 'eventx/release/v7/direct_source_pilot_20261022'
PROTECTED = REPO_ROOT / 'eventx/release/v7/market_capture_20261018/protected_ids.json'
MODEL = REPO_ROOT / 'data/v5/market_condition_tuning_20261012/selected_model.joblib'
MODEL_HASH = 'd5d5a8c12fd999674f687c712e14f3a4406e7ab5ec34774baf1828f644f73a3c'

def now():
    return datetime.now(timezone.utc)

def sha(path):
    with path.open('rb') as f:
        return hashlib.file_digest(f, 'sha256').hexdigest()

def write(path, value):
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + '\n')

def verify_originals():
    count = 0
    for rel in ['eventx/release/v7/market_capture_20261018/implementation_manifest.json',
                'eventx/release/v7/original_source_capture_20261018_v02/implementation_manifest.json']:
        for p, h in json.loads((REPO_ROOT / rel).read_text())['locked_files'].items():
            if sha(REPO_ROOT / p) != h:
                raise RuntimeError('Original lock mismatch: ' + p)
            count += 1
    if sha(MODEL) != MODEL_HASH:
        raise RuntimeError('Fixed model mismatch')
    return count

def snapshot(out):
    at = now()
    report = {'at': at.isoformat(), 'production_locks_verified': verify_originals(), 'sources': {}}
    for name, rel in [('original_source', 'data/v7/official_source_capture_20261018/live'),
                      ('market', 'data/v7/market_cohort_capture_20261018/live')]:
        live = REPO_ROOT / rel
        status_path = out / (name + '_status.json')
        status_path.write_bytes((live / 'status.json').read_bytes())
        status_read_at = now()
        s = json.loads(status_path.read_text())
        body = (live / 'journal.jsonl').read_bytes()
        body = body[:body.rfind(b'\n') + 1]
        journal_path = out / (name + '_journal.jsonl')
        journal_path.write_bytes(body)
        times = []
        for line in body.splitlines():
            r = json.loads(line)
            t = next((r[k] for k in ['recorded_at', 'finished_at', 'at', 'available_at'] if r.get(k)), None)
            if t:
                times.append(datetime.fromisoformat(t.replace('Z', '+00:00')))
        times.sort()
        gaps = sorted([{'from': a.isoformat(), 'to': b.isoformat(), 'seconds': (b-a).total_seconds()}
                       for a, b in zip(times, times[1:])], key=lambda x: x['seconds'], reverse=True)
        report['sources'][name] = {
            'status_at': s['at'], 'pid_from_checkpoint': s['pid'],
            'status_read_at': status_read_at.isoformat(),
            'heartbeat_age_seconds': (status_read_at-datetime.fromisoformat(s['at'])).total_seconds(),
            'journal_records': len(body.splitlines()), 'document_versions': s.get('document_versions'),
            'largest_receipt_gaps': gaps[:3], 'journal_sha256': sha(journal_path),
            'nonempty_latest_quote_markets': sum(bool(m.get('latest_quote_rows')) for m in s.get('markets', {}).values()),
            'source_completeness_certified': False}
    write(out / 'health.json', report)
    return report

def main():
    out = BASE / 'discovery' / uuid.uuid4().hex
    out.mkdir(parents=True)
    health = snapshot(out)
    ids = json.loads(PROTECTED.read_text())
    assert len(ids) == 470 and all(len(x) == 66 and x.startswith('0x') and all(c in '0123456789abcdef' for c in x[2:]) for x in ids)
    exclusions = ','.join("'" + x + "'" for x in ids)
    at = now()
    projection = """condition_id, question, outcomes, clob_token_ids, active, closed, archived,
start_date, end_date, ingest_ts, liquidity_num, volume_num, source, source_run_id,
raw->>'description' AS description, raw->>'resolutionSource' AS resolution_source"""
    common = f"active=TRUE AND closed=FALSE AND COALESCE(archived,FALSE)=FALSE AND condition_id NOT IN ({exclusions})"
    queries = {
        'macro': f"""SELECT {projection} FROM prediction_markets.polymarket_markets
WHERE {common} AND end_date > TIMESTAMPTZ '{at.isoformat()}'
AND end_date < TIMESTAMPTZ '2027-03-01T00:00:00Z'
AND question ~* '(consumer price|inflation|unemployment|payroll|gross domestic|GDP)'
ORDER BY condition_id LIMIT 1000""",
        'controls': f"""SELECT {projection} FROM prediction_markets.polymarket_markets
WHERE {common} AND end_date > TIMESTAMPTZ '{(at+timedelta(hours=30)).isoformat()}'
AND end_date < TIMESTAMPTZ '{(at+timedelta(days=8)).isoformat()}'
AND question ~* '(Bitcoin|BTC)' ORDER BY liquidity_num DESC NULLS LAST,
volume_num DESC NULLS LAST, condition_id LIMIT 5"""}
    settings = ApiSettings.from_env()
    reports = []
    with httpx.Client(base_url=settings.base_url, headers={'Authorization': 'Bearer '+settings.token}, timeout=90) as c:
        for name, sql in queries.items():
            (out / (name+'.sql')).write_text(sql+'\n')
            r = {'kind': name, 'requested_at': now().isoformat()}
            try:
                response = c.post('/retrieve', json={'sql': sql, 'output_format': 'jsonl'})
                r['http_status'] = response.status_code
                response.raise_for_status()
                receipt = response.json()
                uri = receipt['materialized_uri']
                if urlsplit(uri).hostname in [None, urlsplit(settings.base_url).hostname]:
                    download = c.get(uri)
                else:
                    with httpx.Client(timeout=90, follow_redirects=True) as public:
                        download = public.get(uri)
                download.raise_for_status()
                rows = [json.loads(x) for x in download.content.splitlines() if x]
                if any(x['condition_id'] in ids for x in rows):
                    raise ValueError('Protected metadata returned')
                forbidden = {'price', 'outcome_prices', 'result', 'label', 'last_price'}
                if any(forbidden.intersection(x) for x in rows):
                    raise ValueError('Unexpected price projection')
                p = out / (name+'.jsonl')
                p.write_bytes(download.content)
                r.update(status='complete', rows=len(rows), cap_reached=len(rows)>=(1000 if name=='macro' else 5),
                         data_sha256=sha(p), run_id=receipt.get('run_id'))
            except Exception as e:
                r.update(status='failed', error_type=type(e).__name__)
            r['finished_at'] = now().isoformat()
            reports.append(r)
    report = {'created_at': at.isoformat(), 'queries': reports, 'protected_ids_excluded': 470,
              'scope': 'metadata inventory and source controls; no price/outcome selection',
              'health_snapshot': health, 'predictive_admissions': 0}
    write(out/'report.json', report)
    write(out/'manifest.json', {'files': {str(p.relative_to(REPO_ROOT)): sha(p) for p in out.iterdir() if p.is_file()}})
    print(json.dumps({'directory': str(out.relative_to(REPO_ROOT)), 'queries': reports,
                      'health': health}, indent=2))

if __name__ == '__main__':
    main()
