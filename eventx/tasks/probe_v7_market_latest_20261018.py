"""Diagnose latest source observations for exactly one contract per pilot episode."""
import json
import uuid
from datetime import datetime,timezone
import httpx
from eventx.settings import ApiSettings
from eventx.tasks.prepare_v7_market_capture_20261018 import BASE,RELEASE,sha,write
def main():
 out=BASE/'latest_probes'/uuid.uuid4().hex;out.mkdir(parents=True)
 cohort=[json.loads(l) for l in (RELEASE/'cohort.jsonl').read_text().splitlines()]
 protected=set(json.loads((RELEASE/'protected_ids.json').read_text()));seen=set();reports=[]
 settings=ApiSettings.from_env()
 with httpx.Client(base_url=settings.base_url,headers={'Authorization':'Bearer '+settings.token},timeout=90) as c:
  for r in cohort:
   if r['episode_id'] in seen:continue
   seen.add(r['episode_id']);assert r['market_id'] not in protected
   for kind,path in [('trades','/prediction-markets/trades/polymarket/'+r['market_id']),
                     ('quotes','/prediction-markets/orderbook/polymarket/'+r['yes_asset_id'])]:
    receipt={'episode_id':r['episode_id'],'market_id':r['market_id'],'kind':kind,'path':path,'params':{'limit':1},
     'started_at':datetime.now(timezone.utc).isoformat()}
    try:
     response=c.get(path,params=receipt['params']);p=out/(r['episode_id']+'_'+kind+'.json');p.write_bytes(response.content)
     receipt.update(http_status=response.status_code,sha256=sha(p))
     if response.status_code==200:
      rows=response.json();receipt['rows']=len(rows)
      if rows:receipt.update(keys=list(rows[0]),latest_source_ts=rows[0].get('ts',rows[0].get('snapshot_ts')))
    except Exception as e:receipt['error_type']=type(e).__name__
    receipt['completed_at']=datetime.now(timezone.utc).isoformat();reports.append(receipt);write(out/'report.json',reports)
 write(out/'manifest.json',{'files':{str(p):sha(p) for p in out.iterdir() if p.is_file()}})
 print(json.dumps({'directory':str(out),'reports':reports},indent=2))
if __name__=='__main__':main()
