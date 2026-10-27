"""Bounded metadata-only discovery of US macro measurement contracts.

No price, quote, outcome-price, result or trade fields are requested. The V4
cohort is read only for immutable IDs/questions, never protected payloads.
"""
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlsplit
import hashlib
import json
import uuid
import httpx
from eventx.settings import ApiSettings, REPO_ROOT

BASE=REPO_ROOT/'data/v7/market_cohort_capture_20261018'
def sha(p):
 with p.open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()
def write(p,x):p.write_text(json.dumps(x,indent=2,sort_keys=True)+'\n')

def main():
 out=BASE/'discovery'/uuid.uuid4().hex;out.mkdir(parents=True)
 settings=ApiSettings.from_env();at=datetime.now(timezone.utc).isoformat()
 queries={
 'kalshi':f"""SELECT ticker, event_ticker, title, yes_sub_title, no_sub_title,
market_type, status, open_time, close_time, expiration_time, ingest_ts,
source, source_endpoint, source_run_id,
raw->>'rules_primary' AS rules_primary, raw->>'rules_secondary' AS rules_secondary,
raw->>'series_ticker' AS series_ticker
FROM prediction_markets.kalshi_markets
WHERE close_time > TIMESTAMPTZ '{at}'
AND close_time < TIMESTAMPTZ '2027-03-01T00:00:00Z'
AND (title ~* '(consumer price|inflation|unemployment|payroll|gross domestic|GDP)'
 OR ticker ~* '^KX(CPI|UNRATE|GDP)')
ORDER BY ticker LIMIT 1000""",
 'polymarket':f"""SELECT id, condition_id, question, slug, outcomes, clob_token_ids,
active, closed, archived, start_date, end_date, ingest_ts, source, source_endpoint, source_run_id,
raw->>'description' AS description, raw->>'groupItemTitle' AS yes_sub_title,
raw->>'resolutionSource' AS resolution_source
FROM prediction_markets.polymarket_markets
WHERE end_date > TIMESTAMPTZ '{at}'
AND end_date < TIMESTAMPTZ '2027-03-01T00:00:00Z'
AND question ~* '(consumer price|inflation|unemployment|payroll|gross domestic|GDP)'
ORDER BY condition_id LIMIT 1000"""}
 write(out/'request_receipt.json',{'created_at':at,'scope':'metadata only; max1000 per venue, no price/status outcome fields beyond open/closed state',
  'v4_cohort_sha256':sha(REPO_ROOT/'data/v4/confirmatory/cohort_gate/cohort.jsonl'),
  'queries':queries,'model_selection':False,'prohibited':['prices','results','outcome_prices','trades','protected payloads']})
 reports=[]
 with httpx.Client(base_url=settings.base_url,headers={'Authorization':'Bearer '+settings.token},timeout=180) as client:
  for venue,sql in queries.items():
   (out/(venue+'.sql')).write_text(sql+'\n');r={'venue':venue,'started_at':datetime.now(timezone.utc).isoformat()}
   try:
    response=client.post('/retrieve',json={'sql':sql,'output_format':'jsonl'});r['http_status']=response.status_code
    if response.status_code!=200:
     r['status']='failed_http';r['response_sha256']=hashlib.sha256(response.content).hexdigest()
    else:
     receipt=response.json();uri=receipt.get('materialized_uri')
     if not uri:raise ValueError('No materialized URI')
     same_host=urlsplit(uri).hostname in [None,urlsplit(settings.base_url).hostname]
     if same_host:download=client.get(uri)
     else:
      with httpx.Client(timeout=180,follow_redirects=True) as public:download=public.get(uri)
     download.raise_for_status();body=download.content
     path=out/(venue+'.jsonl');path.write_bytes(body)
     rows=[json.loads(line) for line in body.splitlines() if line.strip()]
     forbidden={'price','last_price','yes_bid','yes_ask','outcome_prices','result','label'}
     if any(forbidden.intersection(row) for row in rows):raise ValueError('Forbidden column in source projection')
     r.update(status='complete',rows=len(rows),cap_reached=len(rows)>=1000,data_sha256=sha(path),run_id=receipt.get('run_id'),size_bytes=len(body))
   except Exception as e:r.update(status='failed',error_type=type(e).__name__)
   r['completed_at']=datetime.now(timezone.utc).isoformat();reports.append(r)
   write(out/'report.json',{'created_at':at,'queries':reports,'prices_or_outcomes_requested':False})
 write(out/'manifest.json',{'artifacts':{str(p.relative_to(REPO_ROOT)):sha(p) for p in out.iterdir() if p.is_file()}})
 print(json.dumps({'directory':str(out.relative_to(REPO_ROOT)),'queries':reports},indent=2))
if __name__=='__main__':main()
