"""Metadata-only discovery of a liquid-proxy control, excluding V4 IDs in SQL."""
import hashlib
import json
import uuid
from datetime import datetime,timezone,timedelta
from urllib.parse import urlsplit
import httpx
from eventx.settings import ApiSettings,REPO_ROOT

BASE=REPO_ROOT/'data/v7/source_verification_20261018'
PROTECTED=REPO_ROOT/'eventx/release/v7/market_capture_20261018/protected_ids.json'
def sha(p):
 with p.open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()
def write(p,v):p.write_text(json.dumps(v,sort_keys=True,indent=2)+'\n')
def main():
 out=BASE/'control_discovery'/uuid.uuid4().hex;out.mkdir(parents=True)
 protected=json.loads(PROTECTED.read_text());assert len(protected)==470
 assert all(len(x)==66 and x.startswith('0x') and all(c in '0123456789abcdef' for c in x[2:]) for x in protected)
 at=datetime.now(timezone.utc);exclusions=','.join("'"+x+"'" for x in protected)
 sql=f"""SELECT condition_id,question,outcomes,clob_token_ids,active,closed,archived,start_date,end_date,
ingest_ts,liquidity_num,volume_num,raw->>'volume24hr' AS reported_volume24hr,source,source_run_id
FROM prediction_markets.polymarket_markets
WHERE active=TRUE AND closed=FALSE AND COALESCE(archived,FALSE)=FALSE
AND end_date > TIMESTAMPTZ '{(at+timedelta(hours=2)).isoformat()}'
AND end_date < TIMESTAMPTZ '{(at+timedelta(days=8)).isoformat()}'
AND question ~* '(Bitcoin|BTC)' AND condition_id NOT IN ({exclusions})
ORDER BY liquidity_num DESC NULLS LAST, volume_num DESC NULLS LAST, condition_id LIMIT 5"""
 (out/'query.sql').write_text(sql+'\n')
 report={'started_at':at.isoformat(),'scope':'metadata-only liquid-proxy control, not a research cohort',
  'selection':'first valid canonical YES/NO record in metadata liquidity order; do not use observed prices/movements',
  'v4_excluded_in_query':470,'protected_ids_sha256':sha(PROTECTED)}
 settings=ApiSettings.from_env()
 try:
  with httpx.Client(base_url=settings.base_url,headers={'Authorization':'Bearer '+settings.token},timeout=90) as c:
   response=c.post('/retrieve',json={'sql':sql,'output_format':'jsonl'});report['http_status']=response.status_code
   if response.status_code==200:
    receipt=response.json();uri=receipt['materialized_uri']
    if urlsplit(uri).hostname in [None,urlsplit(settings.base_url).hostname]:d=c.get(uri)
    else:
     with httpx.Client(timeout=90,follow_redirects=True) as public:d=public.get(uri)
    d.raise_for_status();p=out/'candidates.jsonl';p.write_bytes(d.content)
    rows=[json.loads(l) for l in d.content.splitlines() if l]
    assert not any(r['condition_id'] in protected for r in rows)
    report.update(rows=len(rows),data_sha256=sha(p),run_id=receipt.get('run_id'))
   else:report['response_sha256']=hashlib.sha256(response.content).hexdigest()
 except Exception as e:report['error_type']=type(e).__name__
 report['completed_at']=datetime.now(timezone.utc).isoformat();write(out/'report.json',report)
 write(out/'manifest.json',{'files':{str(p.relative_to(REPO_ROOT)):sha(p) for p in out.iterdir() if p.is_file()}})
 print(json.dumps({'directory':str(out.relative_to(REPO_ROOT)),'report':report},indent=2))
if __name__=='__main__':main()
