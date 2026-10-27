"""Fixed-window taker-filter and exact-cohort warehouse checks after source mismatch."""
import json
import uuid
from datetime import datetime,timezone
from urllib.parse import urlsplit
import httpx
from eventx.settings import ApiSettings,REPO_ROOT
from eventx.tasks.discover_v7_source_control_20261018 import BASE,sha,write

def main():
 out=BASE/'followup'/uuid.uuid4().hex;out.mkdir(parents=True)
 sample=[json.loads(l) for l in (REPO_ROOT/'eventx/release/v7/source_verification_20261018/sample.jsonl').read_text().splitlines()]
 protected=set(json.loads((REPO_ROOT/'eventx/release/v7/market_capture_20261018/protected_ids.json').read_text()))
 assert not protected.intersection(r['market_id'] for r in sample)
 receipts=json.loads((BASE/'runs/7386a2e9c114494281a4040874253dc3/receipts.json').read_text())
 reference=next(r for r in receipts if r['endpoint_kind']=='lumid_trades' and r['round']==1)
 start=reference['params']['from'];end=reference['params']['to'];reports=[]
 targets=[r for r in sample if r.get('metadata_rank')==4 or 'unemployment' in r['question']]
 write(out/'contract.json',{'at':datetime.now(timezone.utc).isoformat(),'scope':'same frozen round1 window; taker-filter and warehouse aggregates only',
  'from':start,'to':end,'control_selection':'previously fixed metadata rank4; no cohort change','model_development':False})
 settings=ApiSettings.from_env()
 with httpx.Client(timeout=90) as public:
  for r in targets:
   for taker in ['true','false']:
    params={'market':r['market_id'],'start':int(datetime.fromisoformat(start).timestamp()),
     'end':int(datetime.fromisoformat(end).timestamp()),'limit':1000,'takerOnly':taker}
    receipt={'kind':'venue_taker_filter','market_id':r['market_id'],'params':params,'requested_at':datetime.now(timezone.utc).isoformat()}
    try:
     response=public.get('https://data-api.polymarket.com/trades',params=params);p=out/(r['market_id']+'_'+taker+'.json');p.write_bytes(response.content)
     receipt.update(http_status=response.status_code,sha256=sha(p),file=str(p.relative_to(REPO_ROOT)))
     if response.status_code==200:
      rows=response.json();assert isinstance(rows,list) and all(x['conditionId']==r['market_id'] for x in rows);receipt['rows']=len(rows)
    except Exception as e:receipt['error_type']=type(e).__name__
    receipt['finished_at']=datetime.now(timezone.utc).isoformat();reports.append(receipt)
 ids=','.join("'"+r['market_id']+"'" for r in sample)
 sql=f"""SELECT condition_id,COALESCE(asset_id,'') AS asset_id,COUNT(*) AS rows,
COUNT(DISTINCT trade_id) AS distinct_trade_ids,MIN(ts) AS first_trade_ts,MAX(ts) AS last_trade_ts
FROM prediction_markets.polymarket_trades
WHERE condition_id IN ({ids}) AND ts >= TIMESTAMPTZ '{start}' AND ts <= TIMESTAMPTZ '{end}'
GROUP BY condition_id,COALESCE(asset_id,'') ORDER BY condition_id,COALESCE(asset_id,'') LIMIT 32"""
 (out/'warehouse.sql').write_text(sql+'\n');receipt={'kind':'warehouse_aggregate','requested_at':datetime.now(timezone.utc).isoformat()}
 try:
  with httpx.Client(base_url=settings.base_url,headers={'Authorization':'Bearer '+settings.token},timeout=90) as c:
   response=c.post('/retrieve',json={'sql':sql,'output_format':'jsonl'});receipt['http_status']=response.status_code
   if response.status_code==200:
    v=response.json();uri=v['materialized_uri']
    if urlsplit(uri).hostname in [None,urlsplit(settings.base_url).hostname]:d=c.get(uri)
    else:
     with httpx.Client(timeout=90,follow_redirects=True) as public:d=public.get(uri)
    d.raise_for_status();p=out/'warehouse.jsonl';p.write_bytes(d.content)
    rows=[json.loads(l) for l in d.content.splitlines() if l];assert all(r['condition_id'] in {x['market_id'] for x in sample} for r in rows)
    receipt.update(rows=len(rows),sha256=sha(p),file=str(p.relative_to(REPO_ROOT)),run_id=v.get('run_id'))
   else:receipt['response_sha256']=__import__('hashlib').sha256(response.content).hexdigest()
 except Exception as e:receipt['error_type']=type(e).__name__
 receipt['finished_at']=datetime.now(timezone.utc).isoformat();reports.append(receipt);write(out/'report.json',reports)
 write(out/'manifest.json',{'files':{str(p.relative_to(REPO_ROOT)):sha(p) for p in out.iterdir() if p.is_file()}})
 print(json.dumps({'directory':str(out.relative_to(REPO_ROOT)),'report':reports},indent=2))
if __name__=='__main__':main()
