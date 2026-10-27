"""Bounded API/source feasibility observations for the metadata-defined pilot."""
import json
import uuid
from datetime import datetime, timedelta, timezone
from urllib.parse import urlsplit
import httpx
from eventx.settings import ApiSettings,REPO_ROOT
from eventx.tasks.prepare_v7_market_capture_20261018 import BASE,RELEASE,sha,write

def main():
 out=BASE/'probes'/uuid.uuid4().hex;out.mkdir(parents=True)
 cohort=[json.loads(l) for l in (RELEASE/'cohort.jsonl').read_text().splitlines()]
 protected=set(json.loads((RELEASE/'protected_ids.json').read_text()))
 assert not protected.intersection(r['market_id'] for r in cohort)
 settings=ApiSettings.from_env();now=datetime.now(timezone.utc);reports=[]
 with httpx.Client(base_url=settings.base_url,headers={'Authorization':'Bearer '+settings.token},timeout=90) as c:
  requests=[('openapi','/openapi.json',{})]
  seen=set()
  for r in cohort:
   if r['episode_id'] in seen:continue
   seen.add(r['episode_id'])
   params={'from':(now-timedelta(hours=6)).isoformat(),'to':now.isoformat(),'limit':1000}
   requests.extend([(r['episode_id']+'_trades','/prediction-markets/trades/polymarket/'+r['market_id'],params),
    (r['episode_id']+'_quotes','/prediction-markets/orderbook/polymarket/'+r['yes_asset_id'],params)])
  for name,path,params in requests:
   receipt={'name':name,'path':path,'params':params,'started_at':datetime.now(timezone.utc).isoformat()}
   try:
    response=c.get(path,params=params);receipt['http_status']=response.status_code
    p=out/(name+'.json');p.write_bytes(response.content);receipt['sha256']=sha(p)
    if response.status_code==200:
     v=response.json();receipt['type']=type(v).__name__
     if isinstance(v,list):receipt.update(rows=len(v),keys=list(v[0]) if v else [])
     elif isinstance(v,dict):receipt['keys']=list(v)
   except Exception as e:receipt['error_type']=type(e).__name__
   receipt['completed_at']=datetime.now(timezone.utc).isoformat();reports.append(receipt)
   write(out/'report.json',reports)
  # Narrow indexed ticker ranges replace the failed broad title query.
  for family,lo,hi in [('CPI','KXCPI','KXCPJ'),('UNRATE','KXUNRATE','KXUNRATF'),('GDP','KXGDP','KXGDQ')]:
   sql=f"""SELECT ticker,event_ticker,title,yes_sub_title,no_sub_title,status,close_time,expiration_time,ingest_ts,
raw->>'rules_primary' AS rules_primary,raw->>'rules_secondary' AS rules_secondary
FROM prediction_markets.kalshi_markets WHERE ticker >= '{lo}' AND ticker < '{hi}'
AND close_time > TIMESTAMPTZ '{now.isoformat()}' AND close_time < TIMESTAMPTZ '2027-03-01T00:00:00Z'
ORDER BY ticker LIMIT 300"""
   (out/('kalshi_'+family+'.sql')).write_text(sql+'\n')
   receipt={'name':'kalshi_'+family,'started_at':datetime.now(timezone.utc).isoformat(),'metadata_only':True}
   try:
    response=c.post('/retrieve',json={'sql':sql,'output_format':'jsonl'});receipt['http_status']=response.status_code
    if response.status_code==200:
     v=response.json();uri=v['materialized_uri']
     if urlsplit(uri).hostname in [None,urlsplit(settings.base_url).hostname]:d=c.get(uri)
     else:
      with httpx.Client(timeout=90,follow_redirects=True) as public:d=public.get(uri)
     d.raise_for_status();p=out/('kalshi_'+family+'.jsonl');p.write_bytes(d.content)
     receipt.update(rows=len(d.content.splitlines()),sha256=sha(p),run_id=v.get('run_id'))
    else:receipt['response_sha256']=__import__('hashlib').sha256(response.content).hexdigest()
   except Exception as e:receipt['error_type']=type(e).__name__
   receipt['completed_at']=datetime.now(timezone.utc).isoformat();reports.append(receipt);write(out/'report.json',reports)
 write(out/'manifest.json',{'files':{str(p.relative_to(REPO_ROOT)):sha(p) for p in out.iterdir() if p.is_file()}})
 print(json.dumps({'directory':str(out.relative_to(REPO_ROOT)),'requests':reports},indent=2))
if __name__=='__main__':main()
