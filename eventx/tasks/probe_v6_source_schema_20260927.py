"""Bounded read-only Lumid catalog schema check for V6 source certification."""
from __future__ import annotations
from datetime import datetime, timezone
from pathlib import Path
import hashlib
import json
import sys
import httpx
from eventx.settings import ApiSettings

ROOT=Path(__file__).resolve().parents[2]
OUT=ROOT/'data/v6/source_schema_probe_20260927'
PATHS={
 'news_articles':'/catalog/tables/news/articles/schema.json',
 'kalshi_markets':'/catalog/tables/prediction_markets/kalshi_markets/schema.json',
 'polymarket_markets':'/catalog/tables/prediction_markets/polymarket_markets/schema.json',
}
NEEDED=('revision','version','valid_from','valid_until','updated','modified','historical','as_of')

def sha(b):return hashlib.sha256(b).hexdigest()
def put(p,x):p.write_text(json.dumps(x,indent=2,sort_keys=True)+'\n')
def now():return datetime.now(timezone.utc).isoformat()
def inputs():
 p=Path(__file__)
 q=ROOT/'eventx/release/v5/LUMID_CERTIFICATION_REQUEST_20260910.md'
 return {str(x.relative_to(ROOT)):sha(x.read_bytes()) for x in (p,q)}
def prepare():
 assert not OUT.exists()
 OUT.mkdir(parents=True)
 spec={'version':'v6-source-schema-probe-v0.1-20260927','paths':PATHS,
       'method':'three authenticated GETs, schema field names and response hashes only; no row queries or protected data',
       'interpretation':'catalog field absence does not disprove private archive/version guarantee'}
 put(OUT/'spec.json',spec)
 put(OUT/'receipt.json',{'created_at_utc':now(),'inputs':inputs(),
                         'spec_sha256':sha((OUT/'spec.json').read_bytes()),
                         'written_before_requests':True})
 print('prepared three catalog GETs')
def run():
 assert {p.name for p in OUT.iterdir()}=={'spec.json','receipt.json'}
 receipt=json.loads((OUT/'receipt.json').read_text())
 assert receipt['inputs']==inputs() and receipt['spec_sha256']==sha((OUT/'spec.json').read_bytes())
 s=ApiSettings.from_env()
 rows=[]
 with httpx.Client(base_url=s.base_url,headers={'Authorization':f'Bearer {s.token}'},timeout=20.0,follow_redirects=True) as client:
  for name,path in PATHS.items():
   row={'name':name,'path':path,'observed_at_utc':now()}
   try:
    response=client.get(path)
    row['status_code']=response.status_code
    row['response_sha256']=sha(response.content)
    if response.status_code==200:
     payload=response.json()
     props=payload.get('properties',{}) if isinstance(payload,dict) else {}
     row['fields']=sorted(props)
     row['candidate_version_fields']=[x for x in sorted(props) if any(n in x.lower() for n in NEEDED)]
     row['field_count']=len(props)
    else:row['fields']=[];row['candidate_version_fields']=[];row['field_count']=0
   except (httpx.HTTPError,ValueError) as exc:
    row['error_type']=type(exc).__name__
    row['fields']=[];row['candidate_version_fields']=[];row['field_count']=0
   rows.append(row)
 report={'version':'v6-source-schema-probe-v0.1-20260927','rows':rows,
         'all_http_200':all(x.get('status_code')==200 for x in rows),
         'point_in_time_certified':False,
         'conclusion':'No visible revision/version/history fields in these catalog schemas. Provider-side archive or documented immutability and run/feed/status proofs remain required.'}
 put(OUT/'report.json',report)
 put(OUT/'manifest.json',{'inputs':receipt['inputs'],
     'outputs':{p.name:sha(p.read_bytes()) for p in OUT.iterdir() if p.name!='manifest.json'}})
 print(json.dumps({'statuses':{x['name']:x.get('status_code') for x in rows},
                   'field_counts':{x['name']:x['field_count'] for x in rows},
                   'candidate_version_fields':{x['name']:x['candidate_version_fields'] for x in rows}},sort_keys=True))
if __name__=='__main__':
 assert len(sys.argv)==2 and sys.argv[1] in ('prepare','run')
 (prepare if sys.argv[1]=='prepare' else run)()
