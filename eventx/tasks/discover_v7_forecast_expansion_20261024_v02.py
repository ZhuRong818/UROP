"""Bounded price-blind metadata fetch under a separately frozen V7 policy."""
import json
import uuid
from pathlib import Path
from urllib.parse import urlsplit
import httpx
from eventx.settings import ApiSettings
from eventx.tasks.prepare_v7_forecast_path_20261023 import RELEASE
from eventx.tasks.discover_v7_direct_pilot_20261022 import REPO_ROOT, now, sha, write, verify_originals

def main():
    for p,h in json.loads((RELEASE/'manifest.json').read_text())['files'].items():
        if sha(REPO_ROOT/p)!=h: raise RuntimeError('Policy lock mismatch')
    verify_originals()
    policy=json.loads((RELEASE/'expansion_policy.json').read_text())
    ids=json.loads((REPO_ROOT/policy['protected_ids_path']).read_text())
    if not all(len(x)==66 and x.startswith('0x') and all(c in '0123456789abcdef' for c in x[2:]) for x in ids):
        raise ValueError('Invalid protected ID')
    exclusions=','.join("'"+x+"'" for x in ids)
    sql=f"""SELECT condition_id, question, outcomes, clob_token_ids, active, closed, archived,
start_date, end_date, ingest_ts, source, source_run_id,
raw->>'description' AS description, raw->>'resolutionSource' AS resolution_source
FROM prediction_markets.polymarket_markets
WHERE active=TRUE AND closed=FALSE AND COALESCE(archived,FALSE)=FALSE
AND condition_id NOT IN ({exclusions})
AND end_date > TIMESTAMPTZ '{policy['end_after']}'
AND end_date < TIMESTAMPTZ '{policy['end_before']}'
AND question ~* '{policy['question_pattern']}'
AND NOT (question ~* '{policy['quarantine_pattern']}')
ORDER BY condition_id LIMIT {policy['maximum_rows']}"""
    out=REPO_ROOT/'data/v7/forecast_expansion_20261024_v02'/uuid.uuid4().hex
    out.mkdir(parents=True,exist_ok=False)
    (out/'query.sql').write_text(sql+'\n')
    report={'started_at':now().isoformat(),'policy_sha256':sha(RELEASE/'expansion_policy.json'),
            'protected_ids_excluded':len(ids),'prices_or_outcomes_requested':False,'predictive_admissions':0}
    write(out/'request.json',report)
    settings=ApiSettings.from_env()
    try:
        with httpx.Client(base_url=settings.base_url,headers={'Authorization':'Bearer '+settings.token},timeout=120) as client:
            response=client.post('/retrieve',json={'sql':sql,'output_format':'jsonl'})
            report['http_status']=response.status_code
            if response.status_code != 200:
                report['response_sha256']=__import__('hashlib').sha256(response.content).hexdigest()
                report['sanitized_error']=response.text.replace(settings.token,'[REDACTED]').replace(settings.base_url,'[API]')[:3000]
            response.raise_for_status()
            receipt=response.json();uri=receipt['materialized_uri']
            if urlsplit(uri).hostname in [None,urlsplit(settings.base_url).hostname]:
                download=client.get(uri)
            else:
                with httpx.Client(timeout=120,follow_redirects=True) as public:
                    download=public.get(uri)
            download.raise_for_status()
            rows=[json.loads(l) for l in download.content.splitlines() if l]
            allowed=set(policy['projection'])
            if any(set(r)-allowed or r['condition_id'] in ids for r in rows):
                raise ValueError('Unexpected projection or protected scope')
            (out/'metadata.jsonl').write_bytes(download.content)
            report.update(status='complete',rows=len(rows),cap_reached=len(rows)>=policy['maximum_rows'],run_id=receipt.get('run_id'))
    except Exception as exc:
        report.update(status='failed',error_type=type(exc).__name__)
    report['completed_at']=now().isoformat()
    write(out/'report.json',report)
    files=list(out.iterdir())+[Path(__file__).resolve(),RELEASE/'manifest.json']
    write(out/'manifest.json',{'files':{str(p.relative_to(REPO_ROOT)):sha(p) for p in files}})
    print(json.dumps({'directory':str(out.relative_to(REPO_ROOT)),**report},indent=2))
    if report['status']!='complete': raise SystemExit(1)

if __name__=='__main__': main()
