"""Capture exact-cohort market observations. Never fit, score or construct labels."""
import argparse
import fcntl
import hashlib
import json
import os
import signal
import time
from datetime import datetime,timedelta,timezone
from pathlib import Path
import httpx
from eventx.settings import ApiSettings,REPO_ROOT

RELEASE=REPO_ROOT/'eventx/release/v7/market_capture_20261018'
LIVE=REPO_ROOT/'data/v7/market_cohort_capture_20261018/live'
def now():return datetime.now(timezone.utc)
def parse(s):return datetime.fromisoformat(str(s).replace('Z','+00:00'))
def sha(p):
 with p.open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()
def atomic(p,v):
 tmp=p.with_suffix('.tmp');tmp.write_text(json.dumps(v,sort_keys=True,indent=2)+'\n');os.replace(tmp,p)
class Capture:
 def __init__(self):
  self.lock=json.loads((RELEASE/'implementation_manifest.json').read_text())
  for rel,h in self.lock['locked_files'].items():
   if sha(REPO_ROOT/rel)!=h:raise RuntimeError('Capture lock mismatch: '+rel)
  self.cfg=json.loads((RELEASE/'capture_spec.json').read_text())
  self.cohort=[json.loads(l) for l in (RELEASE/'cohort.jsonl').read_text().splitlines()]
  self.protected=set(json.loads((RELEASE/'protected_ids.json').read_text()))
  assert not self.protected.intersection(r['market_id'] for r in self.cohort)
  assert sha(REPO_ROOT/self.cfg['model_path'])==self.cfg['model_sha256']
  LIVE.mkdir(parents=True,exist_ok=True);(LIVE/'objects').mkdir(exist_ok=True)
  self.fd=(LIVE/'collector.lock').open('a');fcntl.flock(self.fd,fcntl.LOCK_EX|fcntl.LOCK_NB)
  self.state=json.loads((LIVE/'checkpoint.json').read_text()) if (LIVE/'checkpoint.json').exists() else {
   'started_at':now().isoformat(),'cycles':0,'markets':{},'journal_records':0,'head_sha256':None}
  self.recover_journal()
  settings=ApiSettings.from_env()
  self.client=httpx.Client(base_url=settings.base_url,headers={'Authorization':'Bearer '+settings.token},timeout=45)
  self.last=0.;self.stopping=False
 def recover_journal(self):
  p=LIVE/'journal.jsonl';head=None;n=0
  if p.exists():
   with p.open('rb') as f:
    for line in f:
     r=json.loads(line);digest=r.pop('record_sha256')
     assert r['previous_sha256']==head
     assert hashlib.sha256(json.dumps(r,sort_keys=True,separators=(',',':')).encode()).hexdigest()==digest
     head=digest;n+=1
  self.state.update(head_sha256=head,journal_records=n)
 def journal(self,r):
  r=dict(r,previous_sha256=self.state['head_sha256'])
  r['record_sha256']=hashlib.sha256(json.dumps(r,sort_keys=True,separators=(',',':')).encode()).hexdigest()
  with (LIVE/'journal.jsonl').open('a') as f:f.write(json.dumps(r,sort_keys=True)+'\n');f.flush();os.fsync(f.fileno())
  self.state['head_sha256']=r['record_sha256'];self.state['journal_records']+=1
 def save(self):
  atomic(LIVE/'checkpoint.json',self.state)
  atomic(LIVE/'status.json',{'at':now().isoformat(),'pid':os.getpid(),'started_at':self.state['started_at'],
   'cycles':self.state['cycles'],'journal_records':self.state['journal_records'],'journal_head_sha256':self.state['head_sha256'],
   'scope':'market_source_feasibility_capture_only','market_model_fixed':True,'labels_or_predictions_computed':False,
   'v4_payloads_read':False,'cohort_markets':len(self.cohort),'markets_observed':len(self.state['markets']),
   'markets':self.state['markets'],'stop_at':self.cfg['stop_at']})
 def request(self,r,kind,params):
  assert r['market_id'] not in self.protected
  path=('/prediction-markets/trades/polymarket/'+r['market_id'] if kind=='trades' else
        '/prediction-markets/orderbook/polymarket/'+r['yes_asset_id'])
  if self.state.get('provider_blocked_until') and now()<parse(self.state['provider_blocked_until']):
   receipt={'kind':kind,'market_id':r['market_id'],'path':path,'params':params,'status':'deferred_provider_backoff',
    'finished_at':now().isoformat(),'blocked_until':self.state['provider_blocked_until']}
   self.journal(receipt);self.save();return None,receipt
  delay=self.cfg['request_min_seconds']-(time.monotonic()-self.last)
  if delay>0:time.sleep(delay)
  self.last=time.monotonic();receipt={'kind':kind,'market_id':r['market_id'],'path':path,'params':params,
   'requested_at':now().isoformat(),'episode_id':r['episode_id']};rows=None
  try:
   response=self.client.get(path,params=params);receipt['http_status']=response.status_code
   body=response.content;h=hashlib.sha256(body).hexdigest();p=LIVE/'objects'/h
   if not p.exists():
    with p.open('xb') as f:f.write(body);f.flush();os.fsync(f.fileno())
   receipt.update(payload_sha256=h,available_at=now().isoformat(),size_bytes=len(body))
   if response.status_code==200:
    value=response.json()
    if not isinstance(value,list):raise ValueError('Unrecognized response envelope')
    if any(not isinstance(x,dict) for x in value):raise ValueError('Unrecognized row')
    if any(str(x.get('condition_id',r['market_id']))!=r['market_id'] for x in value):raise ValueError('Unexpected condition ID')
    if kind=='quotes' and any(str(x.get('asset_id',r['yes_asset_id']))!=r['yes_asset_id'] for x in value):raise ValueError('Unexpected quote asset')
    rows=value;receipt.update(status='observed',rows=len(rows))
   else:receipt['status']='failed_http'
   if response.status_code==429:
    try:receipt['retry_after_seconds']=max(60,float(response.headers.get('Retry-After','60')))
    except ValueError:receipt['retry_after_seconds']=60
   elif response.status_code in (401,403):receipt['retry_after_seconds']=21600
  except Exception as e:receipt.update(status='failed',error_type=type(e).__name__)
  receipt['finished_at']=now().isoformat();self.journal(receipt);self.save()
  if receipt.get('retry_after_seconds'):
   self.state['provider_blocked_until']=(now()+timedelta(seconds=receipt['retry_after_seconds'])).isoformat();self.save()
  return rows,receipt
 def capture_market(self,r):
  m=self.state['markets'].setdefault(r['market_id'],{'episode_id':r['episode_id']})
  end=now();start=parse(m['window_through'])-timedelta(minutes=self.cfg['overlap_minutes']) if m.get('window_through') else end-timedelta(hours=self.cfg['warmup_hours'])
  cursor=end;seen=set();complete=False;problem=None;count=0;yes=0;latest=None
  for page in range(self.cfg['max_pages']):
   rows,receipt=self.request(r,'trades',{'from':start.isoformat(),'to':cursor.isoformat(),'limit':self.cfg['page_limit']})
   m['trades_last_receipt']=receipt['finished_at'];m['trades_http_status']=receipt.get('http_status')
   if rows is None:problem='failed_request';break
   try:
    ts=[parse(x['ts']) for x in rows]
    if any(t<start or t>end for t in ts):raise ValueError('Rows outside requested interval')
   except Exception:problem='invalid_or_out_of_window_timestamps';break
   for x,t in zip(rows,ts):
    key=hashlib.sha256(json.dumps(x,sort_keys=True).encode()).hexdigest()
    if key in seen:continue
    seen.add(key);count+=1
    if str(x.get('token_id',x.get('asset_id','')))==r['yes_asset_id']:
     yes+=1;latest=max(latest,t) if latest else t
   if len(rows)<self.cfg['page_limit']:complete=True;break
   oldest=min(ts)
   if oldest>=cursor:problem='stalled_boundary_or_timestamp_tie';break
   cursor=oldest
  if not complete and not problem:problem='page_cap_reached'
  # An empty response is observed absence from this endpoint, never certified inactivity.
  m.update(last_window_from=start.isoformat(),last_window_to=end.isoformat(),last_window_rows=count,
   last_window_yes_rows=yes,last_window_status='bounded_endpoint_window_returned' if complete else 'unknown_incomplete',
   problem=problem,source_completeness_certified=False)
  if latest:m['last_observed_yes_trade_ts']=latest.isoformat()
  if complete:m['window_through']=end.isoformat()
  rows,receipt=self.request(r,'quotes',{'to':now().isoformat(),'limit':1})
  m.update(quotes_http_status=receipt.get('http_status'),quotes_last_receipt=receipt['finished_at'],
   latest_quote_rows=None if rows is None else len(rows))
  if rows:
   m['quote_snapshot_ts']=rows[0].get('snapshot_ts');m['quote_freshness_certified']=False
  self.journal({'kind':'window_summary','market_id':r['market_id'],'at':now().isoformat(),'summary':dict(m)});self.save()
 def run(self,once=False):
  self.save()
  while not self.stopping and now()<parse(self.cfg['stop_at']) and not (LIVE/'STOP').exists():
   if sha(REPO_ROOT/self.cfg['model_path'])!=self.cfg['model_sha256']:raise RuntimeError('Fixed model hash changed')
   start=time.monotonic()
   for r in self.cohort:
    if self.stopping or (LIVE/'STOP').exists():break
    if now()>parse(r['end_date'])+timedelta(days=1):continue
    self.capture_market(r)
   self.state['cycles']+=1;self.save()
   if once:break
   while time.monotonic()-start<self.cfg['poll_seconds']:
    if self.stopping or (LIVE/'STOP').exists():break
    self.save();time.sleep(5)
  self.journal({'kind':'collector_stopped','at':now().isoformat(),'once':once});self.save();self.client.close()
def main():
 ap=argparse.ArgumentParser();ap.add_argument('--once',action='store_true');args=ap.parse_args()
 c=Capture()
 def stop(*_):c.stopping=True
 signal.signal(signal.SIGTERM,stop);signal.signal(signal.SIGINT,stop)
 c.run(args.once)
if __name__=='__main__':main()
