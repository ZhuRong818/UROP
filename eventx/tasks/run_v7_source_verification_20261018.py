"""Independent finite REST/WS/SSE diagnosis; preserve all production collectors."""
import asyncio
import hashlib
import json
import os
import time
import uuid
from datetime import datetime,timedelta,timezone
from pathlib import Path
import httpx
import websockets
from eventx.settings import ApiSettings,REPO_ROOT
from eventx.tasks.discover_v7_source_control_20261018 import BASE,sha,write

RELEASE=REPO_ROOT/'eventx/release/v7/source_verification_20261018'
def now():return datetime.now(timezone.utc)
def iso():return now().isoformat()
class Diagnostic:
 def __init__(self):
  self.cfg=json.loads((RELEASE/'plan.json').read_text());self.rows=[json.loads(l) for l in (RELEASE/'sample.jsonl').read_text().splitlines()]
  self.markets={r['market_id'] for r in self.rows};self.assets={r[k] for r in self.rows for k in ['yes_asset_id','no_asset_id']}
  self.protected=set(json.loads((REPO_ROOT/'eventx/release/v7/market_capture_20261018/protected_ids.json').read_text()))
  assert not self.markets & self.protected
  self.verify_locks()
  self.out=BASE/'runs'/uuid.uuid4().hex;self.out.mkdir(parents=True);(self.out/'objects').mkdir()
  self.head=None;self.count=0;self.receipts=[];self.streams={};self.created=iso();self.rate_locks={k:asyncio.Lock() for k in ['lumid','public']}
  self.last={k:0. for k in self.rate_locks};self.blocked={k:0. for k in self.rate_locks}
  settings=ApiSettings.from_env();self.lumid=httpx.AsyncClient(base_url=settings.base_url,headers={'Authorization':'Bearer '+settings.token},timeout=35)
  self.public=httpx.AsyncClient(timeout=35)
  write(self.out/'run_contract.json',{'started_at':self.created,'plan_sha256':sha(RELEASE/'plan.json'),
   'sample_sha256':sha(RELEASE/'sample.jsonl'),'scope':'bounded source diagnosis only','model_fits_or_scores':False})
  for tag,p in [('market',REPO_ROOT/'data/v7/market_cohort_capture_20261018/live/status.json'),
                ('original_source',REPO_ROOT/'data/v7/official_source_capture_20261018/live/status.json')]:
   (self.out/(tag+'_status_before.json')).write_bytes(p.read_bytes())
 def verify_locks(self):
  for rel in ['eventx/release/v7/source_verification_20261018/implementation_manifest.json',
   'eventx/release/v7/market_capture_20261018/implementation_manifest.json',
   'eventx/release/v7/original_source_capture_20261018_v02/implementation_manifest.json']:
   for p,h in json.loads((REPO_ROOT/rel).read_text())['locked_files'].items():assert sha(REPO_ROOT/p)==h,p
  assert sha(REPO_ROOT/self.cfg['model_path'])==self.cfg['model_sha256']
 def store(self,body):
  h=hashlib.sha256(body).hexdigest();p=self.out/'objects'/h
  if not p.exists():
   with p.open('xb') as f:f.write(body);f.flush();os.fsync(f.fileno())
  return h
 def log(self,r):
  r=dict(r,previous_sha256=self.head)
  r['record_sha256']=hashlib.sha256(json.dumps(r,sort_keys=True,separators=(',',':')).encode()).hexdigest()
  with (self.out/'journal.jsonl').open('a') as f:f.write(json.dumps(r,sort_keys=True)+'\n');f.flush();os.fsync(f.fileno())
  self.head=r['record_sha256'];self.count+=1
 def heartbeat(self):
  p=self.out/'status.json';tmp=p.with_suffix('.tmp')
  tmp.write_text(json.dumps({'at':iso(),'pid':os.getpid(),'journal_records':self.count,'head_sha256':self.head,
   'rest_requests_completed':len(self.receipts),'streams':self.streams,'models_scored':False},indent=2)+'\n');os.replace(tmp,p)
 def validate(self,value):
  if isinstance(value,list):
   for v in value:self.validate(v)
  elif isinstance(value,dict):
   for k in ['condition_id','conditionId','market']:
    v=value.get(k)
    if isinstance(v,str) and v.startswith('0x') and len(v)==66:
     if v not in self.markets:raise ValueError('Unexpected market outside diagnostic allowlist')
   for k in ['asset_id','assetId','token_id','asset']:
    v=value.get(k)
    if v is not None and isinstance(v,(str,int)) and str(v).isdigit() and str(v) not in self.assets:
     raise ValueError('Unexpected asset outside diagnostic allowlist')
   for v in value.values():
    if isinstance(v,(dict,list)):self.validate(v)
 async def request(self,r,kind,round_no,path,params,lumid=False):
  assert r['market_id'] in self.markets and r['market_id'] not in self.protected
  group='lumid' if lumid else 'public';receipt={'kind':'rest','endpoint_kind':kind,'round':round_no,'market_id':r['market_id'],
   'source':group,'path':path,'params':params,'requested_at':iso()};body=None
  try:
   async with self.rate_locks[group]:
    delay=max(self.cfg['lumid_min_request_seconds'] if lumid else self.cfg['public_min_request_seconds'],0)-(time.monotonic()-self.last[group])
    if delay>0:await asyncio.sleep(delay)
    if time.monotonic()<self.blocked[group]:
     receipt.update(status='deferred_retry_after',finished_at=iso());self.receipts.append(receipt);self.log(receipt);return
    self.last[group]=time.monotonic()
   response=await (self.lumid if lumid else self.public).get(path,params=params)
   receipt.update(http_status=response.status_code,response_received_at=iso())
   body=response.content
   # All requests were scoped in advance. Check server scope before retaining/analysing payloads.
   if response.status_code==200:
    value=response.json();self.validate(value)
    receipt.update(status='observed',response_type=type(value).__name__)
    if isinstance(value,list):receipt['rows']=len(value)
    elif isinstance(value,dict):
     receipt['keys']=list(value)
     if isinstance(value.get('history'),list):receipt['rows']=len(value['history'])
   else:receipt['status']='failed_http'
   receipt['payload_sha256']=self.store(body);receipt['available_at']=iso()
   receipt['request_id']=response.headers.get('x-request-id')
   if response.status_code==429:
    try:seconds=max(60,float(response.headers.get('Retry-After','60')))
    except ValueError:seconds=60
    self.blocked[group]=time.monotonic()+seconds;receipt['retry_after_seconds']=seconds
  except Exception as e:
   receipt.update(status='failed',error_type=type(e).__name__)
   if isinstance(e,ValueError) and body is not None:receipt['rejected_payload_sha256']=hashlib.sha256(body).hexdigest()
  receipt['finished_at']=iso();self.receipts.append(receipt);self.log(receipt);self.heartbeat()
 async def rest_round(self,index):
  end=now();start=end-timedelta(hours=self.cfg['history_hours']);tasks=[]
  for r in self.rows:
   cid=r['market_id'];asset=r['yes_asset_id'];window={'from':start.isoformat(),'to':end.isoformat()}
   specs=[('lumid_trades',f'/prediction-markets/trades/polymarket/{cid}',dict(window,limit=1000),True),
    ('lumid_quotes',f'/prediction-markets/orderbook/polymarket/{asset}',{'limit':1},True),
    ('lumid_candles',f'/prediction-markets/candles/polymarket/{cid}',dict(window,interval='1m',limit=1000),True),
    ('venue_trades','https://data-api.polymarket.com/trades',{'market':cid,'limit':1000,'takerOnly':'false','start':int(start.timestamp()),'end':int(end.timestamp())},False),
    ('venue_book','https://clob.polymarket.com/book',{'token_id':asset},False),
    ('venue_no_book','https://clob.polymarket.com/book',{'token_id':r['no_asset_id']},False),
    ('venue_history','https://clob.polymarket.com/prices-history',{'market':asset,'startTs':int(start.timestamp()),'endTs':int(end.timestamp()),'fidelity':1},False)]
   for kind,path,params,is_lumid in specs:tasks.append(self.request(r,kind,index,path,params,is_lumid))
  await asyncio.gather(*tasks)
 async def ws(self):
  key='venue_ws';state={'status':'connecting','started_at':iso(),'frames':0,'messages':0,'pongs':0};self.streams[key]=state
  url=self.cfg['sources']['polymarket_websocket'];deadline=time.monotonic()+self.cfg['stream_seconds']
  try:
   async with websockets.connect(url,open_timeout=20,close_timeout=5,max_size=4*1024*1024,ping_interval=None) as ws:
    sub={'assets_ids':sorted(self.assets),'type':'market'};await ws.send(json.dumps(sub));state.update(status='subscribed',connected_at=iso())
    self.log({'kind':'ws_subscribed','at':iso(),'url':url,'subscription':sub});last_ping=time.monotonic()
    while time.monotonic()<deadline:
     if time.monotonic()-last_ping>=10:await ws.send('PING');last_ping=time.monotonic();self.log({'kind':'ws_ping_sent','at':iso()})
     try:message=await asyncio.wait_for(ws.recv(),timeout=min(2,max(.01,deadline-time.monotonic())))
     except asyncio.TimeoutError:self.heartbeat();continue
     state['frames']+=1
     if message=='PONG':state['pongs']+=1;self.log({'kind':'ws_pong','at':iso()});continue
     body=message.encode() if isinstance(message,str) else message;value=json.loads(body);self.validate(value)
     h=self.store(body);clock=iso();self.log({'kind':'ws_frame','payload_sha256':h,'available_at':clock})
     state['messages']+=len(value) if isinstance(value,list) else 1;state['last_frame_at']=clock;self.heartbeat()
     if state['frames']>=self.cfg['stream_max_frames']:state['status']='frame_cap';break
    else:state['status']='bounded_window_complete'
  except Exception as e:state.update(status='failed',error_type=type(e).__name__)
  state['finished_at']=iso();self.log({'kind':'ws_finished','state':state});self.heartbeat()
 async def sse(self):
  key='lumid_sse';state={'status':'connecting','started_at':iso(),'frames':0};self.streams[key]=state
  params={'condition_ids':','.join(sorted(self.markets)),'asset_ids':','.join(sorted(self.assets))}
  deadline=time.monotonic()+self.cfg['stream_seconds']
  try:
   async with self.lumid.stream('GET','/prediction-markets/stream',params=params,timeout=httpx.Timeout(25,read=20)) as response:
    state['http_status']=response.status_code;self.log({'kind':'sse_connected','at':iso(),'params':params,'http_status':response.status_code})
    if response.status_code!=200:
     body=await response.aread();state.update(status='failed_http',payload_sha256=self.store(body));return
    state['status']='observing';lines=[];it=response.aiter_lines().__aiter__()
    while time.monotonic()<deadline:
     try:line=await asyncio.wait_for(it.__anext__(),timeout=max(.01,deadline-time.monotonic()))
     except StopAsyncIteration:state['status']='server_closed';break
     if not line:
      if lines:
       data='\n'.join(x[5:].strip() for x in lines if x.startswith('data:'))
       if data:self.validate(json.loads(data))
       body=('\n'.join(lines)+'\n\n').encode();h=self.store(body)
       self.log({'kind':'sse_frame','payload_sha256':h,'available_at':iso()});state['frames']+=1;lines=[];self.heartbeat()
      if state['frames']>=self.cfg['stream_max_frames']:state['status']='frame_cap';break
     else:lines.append(line)
    else:state['status']='bounded_window_complete'
  except asyncio.TimeoutError:state['status']='bounded_deadline_timeout_no_final_frame'
  except Exception as e:state.update(status='failed',error_type=type(e).__name__)
  finally:
   state['finished_at']=iso();self.log({'kind':'sse_finished','state':state});self.heartbeat()
 async def run(self):
  self.heartbeat()
  # Capture live streams alongside the first fixed-window REST comparison.
  streams=[asyncio.create_task(self.ws()),asyncio.create_task(self.sse())]
  await self.rest_round(1)
  self.log({'kind':'round_complete','round':1,'at':iso()});self.heartbeat()
  await asyncio.gather(*streams)
  await self.rest_round(2)
  self.log({'kind':'round_complete','round':2,'at':iso()})
  await self.lumid.aclose();await self.public.aclose();self.verify_locks()
  for tag,p in [('market',REPO_ROOT/'data/v7/market_cohort_capture_20261018/live/status.json'),
                ('original_source',REPO_ROOT/'data/v7/official_source_capture_20261018/live/status.json')]:
   (self.out/(tag+'_status_after.json')).write_bytes(p.read_bytes())
  report={'started_at':self.created,'finished_at':iso(),'rest_requests':len(self.receipts),
   'streams':self.streams,'journal_records':self.count,'journal_head_sha256':self.head,'v4_exact_overlap':0,
   'production_locks_and_model_match':True,'forecasts_or_labels_computed':False,'predictive_admissions':0}
  write(self.out/'receipts.json',self.receipts);write(self.out/'report.json',report);self.heartbeat()
  write(self.out/'manifest.json',{'files':{str(p.relative_to(REPO_ROOT)):sha(p) for p in self.out.iterdir() if p.is_file()},
   'payloads':{p.name:sha(p) for p in (self.out/'objects').iterdir() if p.is_file()}})
  print(json.dumps({'directory':str(self.out.relative_to(REPO_ROOT)),'report':report},indent=2))
def main():asyncio.run(Diagnostic().run())
if __name__=='__main__':main()
