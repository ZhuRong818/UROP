"""Consolidate actual source evidence; never fit models or construct target labels."""
import collections
from datetime import datetime,timedelta,timezone
from decimal import Decimal
import hashlib
import json
from pathlib import Path
from eventx.settings import REPO_ROOT
from eventx.tasks.discover_v7_source_control_20261018 import BASE,sha,write

RUN=BASE/'runs/7386a2e9c114494281a4040874253dc3'
SSE=BASE/'runs/39bf148e147b4a4da51fd91ed3edb9f4'
FOLLOW=BASE/'followup/da4cfefa28c5464c9131393899afc77a'
RELEASE=REPO_ROOT/'eventx/release/v7/source_verification_20261018'
OUT=BASE/'analysis_v01'
def dt(s):return datetime.fromisoformat(s.replace('Z','+00:00'))
def stamp(v):
 if isinstance(v,(float,int)) or str(v).replace('.','',1).isdigit():
  x=float(v);return datetime.fromtimestamp(x/(1000 if x>1e11 else 1),timezone.utc)
 return dt(v)
def payload(r):return json.loads((RUN/'objects'/r['payload_sha256']).read_text())
def fp(x):
 return (str(x.get('token_id',x.get('asset'))),int(stamp(x.get('ts',x.get('timestamp'))).timestamp()),
  str(Decimal(str(x['price'])).normalize()),str(Decimal(str(x['size'])).normalize()),x['side'].upper())
def verify_run(path):
 manifest=json.loads((path/'manifest.json').read_text());count=0
 for rel,h in manifest['files'].items():assert sha(REPO_ROOT/rel)==h;count+=1
 for name,h in manifest.get('payloads',{}).items():assert sha(path/'objects'/name)==h;count+=1
 if (path/'journal.jsonl').exists():
  head=None
  for line in (path/'journal.jsonl').read_text().splitlines():
   r=json.loads(line);h=r.pop('record_sha256');assert r['previous_sha256']==head
   assert hashlib.sha256(json.dumps(r,sort_keys=True,separators=(',',':')).encode()).hexdigest()==h;head=h
 return count
def main():
 if OUT.exists():raise RuntimeError('Preserve version')
 OUT.mkdir(parents=True)
 verified=sum(verify_run(p) for p in [RUN,SSE,FOLLOW])
 sample=[json.loads(l) for l in (RELEASE/'sample.jsonl').read_text().splitlines()]
 receipt=json.loads((RUN/'receipts.json').read_text());index={(r['market_id'],r['round'],r['endpoint_kind']):r for r in receipt}
 comparisons=[];selected_control=None
 for s in sample:
  for rnd in [1,2]:
   get=lambda kind:index[s['market_id'],rnd,kind]
   lr=get('lumid_trades');vr=get('venue_trades');bookr=get('venue_book');book=payload(bookr)
   start=max(dt(lr['params']['from']),stamp(vr['params']['start']));end=min(dt(lr['params']['to']),stamp(vr['params']['end']))
   a=[r for r in payload(vr) if start<=stamp(r['timestamp'])<=end]
   b=[r for r in payload(lr) if start<=stamp(r['ts'])<=end]
   ac=collections.Counter(fp(r) for r in a);bc=collections.Counter(fp(r) for r in b)
   yes=lambda x:str(x.get('token_id',x.get('asset')))==s['yes_asset_id']
   ys=[x for x in a if yes(x)];yb=[x for x in b if yes(x)]
   yes60=[x for x in ys if stamp(x['timestamp'])>=end-timedelta(hours=1)]
   latest=max((stamp(x['timestamp']) for x in ys),default=None)
   latest_lumid=max((stamp(x['ts']) for x in yb),default=None)
   age=(dt(bookr['response_received_at'])-stamp(book['timestamp'])).total_seconds() if bookr['http_status']==200 and book.get('timestamp') else None
   two_sided=bool(book.get('bids')) and bool(book.get('asks'))
   qualifies=bookr['http_status']==200 and two_sided and age is not None and 0<=age<=300 and len(yes60)>=3
   if qualifies and s['diagnostic_role']=='control_candidate' and selected_control is None:selected_control={'market_id':s['market_id'],'metadata_rank':s['metadata_rank'],'round':rnd,'question':s['question']}
   history=payload(get('venue_history')).get('history',[])
   c={'market_id':s['market_id'],'question':s['question'],'diagnostic_role':s['diagnostic_role'],'metadata_rank':s.get('metadata_rank'),
    'round':rnd,'common_window_from':start.isoformat(),'common_window_to':end.isoformat(),
    'venue_trade_rows':len(a),'lumid_trade_rows':len(b),'venue_yes_rows':len(ys),'lumid_yes_rows':len(yb),
    'venue_only_print_fingerprints':sum((ac-bc).values()),'lumid_only_print_fingerprints':sum((bc-ac).values()),
    'matching_print_fingerprints':sum((ac&bc).values()),'trade_response_cap_reached':len(payload(vr))>=1000 or len(payload(lr))>=1000,
    'venue_yes_trades60m':len(yes60),'latest_venue_yes_trade_ts':latest.isoformat() if latest else None,
    'latest_lumid_yes_trade_ts':latest_lumid.isoformat() if latest_lumid else None,
    'venue_yes_trade_age_minutes':(end-latest).total_seconds()/60 if latest else None,
    'venue_book_http_status':bookr['http_status'],'venue_bid_levels':len(book.get('bids',[])),
    'venue_ask_levels':len(book.get('asks',[])),'venue_book_two_sided':two_sided,'venue_book_age_seconds':age,
    'independent_activity_control_screen':qualifies,'lumid_quote_rows':len(payload(get('lumid_quotes'))),
    'lumid_candle_rows':len(payload(get('lumid_candles'))),'venue_price_history_points':len(history),
    'history_unique_price_values':len({str(Decimal(str(x['p'])).normalize()) for x in history}),
    'predictive_eligible':False}
   comparisons.append(c)
 ws_counts=collections.defaultdict(collections.Counter);common=collections.Counter();messages=0
 first=json.loads((RUN/'report.json').read_text());sse_end=dt(first['streams']['lumid_sse']['finished_at'])
 for line in (RUN/'journal.jsonl').read_text().splitlines():
  r=json.loads(line)
  if r['kind']!='ws_frame':continue
  v=payload(r)
  for x in v if isinstance(v,list) else [v]:
   event=x.get('event_type','unknown');ws_counts[x.get('market','unknown')][event]+=1;messages+=1
   if dt(r['available_at'])<=sse_end:common[event]+=1
 sse_counts=collections.Counter()
 for line in (SSE/'journal.jsonl').read_text().splitlines():
  r=json.loads(line)
  if r['kind']!='sse_frame':continue
  body=(SSE/'objects'/r['payload_sha256']).read_text()
  event=next((x[6:].strip() for x in body.splitlines() if x.startswith('event:')),'unspecified');sse_counts[event]+=1
 warehouse=[json.loads(l) for l in (FOLLOW/'warehouse.jsonl').read_text().splitlines()]
 counts=collections.Counter()
 for r in warehouse:counts[r['condition_id']]+=int(r['rows'])
 follow=json.loads((FOLLOW/'report.json').read_text())
 filter_counts=[{'market_id':r['market_id'],'takerOnly':r['params']['takerOnly'],'rows':r['rows']} for r in follow if r['kind']=='venue_taker_filter']
 (OUT/'market_comparison.jsonl').write_text(''.join(json.dumps(r,sort_keys=True)+'\n' for r in comparisons))
 cfg=json.loads((RELEASE/'plan.json').read_text());assert sha(REPO_ROOT/cfg['model_path'])==cfg['model_sha256']
 production_verified=0
 for rel in ['eventx/release/v7/market_capture_20261018/implementation_manifest.json',
  'eventx/release/v7/original_source_capture_20261018_v02/implementation_manifest.json']:
  for p,h in json.loads((REPO_ROOT/rel).read_text())['locked_files'].items():assert sha(REPO_ROOT/p)==h;production_verified+=1
 report={'created_at':datetime.now(timezone.utc).isoformat(),'primary_run':str(RUN.relative_to(REPO_ROOT)),
  'primary_window_start':first['started_at'],'primary_window_end':first['finished_at'],'rest_requests':len(receipt),
  'rest_http_counts':dict(collections.Counter(str(r.get('http_status')) for r in receipt)),
  'markets':len(sample),'macro_samples':3,'control_candidates':5,'selected_activity_control':selected_control,
  'control_caveat':'Metadata rank4 passes first-round activity screen (3 YES fills60m) but second-round only2; book activity is stronger than trade activity. Not a stable high-frequency liquidity certification.',
  'websocket_state':first['streams']['venue_ws'],'websocket_events':messages,
  'websocket_type_counts':dict(sum(ws_counts.values(),collections.Counter())),
  'websocket_per_market':{k:dict(v) for k,v in ws_counts.items()},'concurrent_first_sse_interval_ws_types':dict(common),
  'first_sse_limitation':'Client20s idle timeout; preserved as diagnostic failure, not a source outage.',
  'sse_v02_state':json.loads((SSE/'report.json').read_text())['state'],'sse_v02_event_types':dict(sse_counts),
  'sse_comparison_limitation':'180s recheck not simultaneous with first venue WS. Earlier20s common interval retained; heartbeat-only does not certify data coverage.',
  'warehouse_rows_by_market':dict(counts),'taker_filter_counts':filter_counts,
  'fingerprint_method':'Multiset of asset,epoch-second,Decimal-normalized price,size,side within exact common interval; not a globally unique economic fill ID.',
  'interpretation':'Both source gaps and genuinely sparse sampled macro trading are present. Direct books exist despite empty Lumid quote archive; control trade rows differ also in warehouse.',
  'verified_artifact_hashes':verified,'production_locked_files_verified':production_verified,'model_sha256':cfg['model_sha256'],
  'forecasts_or_target_labels_computed':False,'predictive_admissions':0,'source_substitution_into_frozen_studies':False,
  'next':'Resolve exact-cohort quote/trade source coverage, then version a longer-lived prospectively selected market cohort; no further model development before a complete gated observation.'}
 write(OUT/'report.json',report)
 write(OUT/'observation_gate_contract.json',{'status':'required_gates_only; no observations constructed or admitted','model_fixed':cfg['model_sha256'],
  'all_required':['authenticated market/YES mapping and rules/version known at decision time',
   'source coverage and durable availability clocks verified; gaps not encoded as zero',
   'canonical YES trade age<=5m,count60>=3,count240>=3,notional240>=100 under inherited screen',
   'valid240min trailing1min logodds-increment population SD, with complete as-of warmup and no retrospective availability',
   'valid canonical YES forward price at decision+30min, with prespecified freshness/no-stale-forward policy frozen before use',
   'verified market remains tradable/unresolved through target end; use actual terminal evidence, not merely end_date',
   'defensible event-to-market evidence available by decision time; novelty/context distinguished',
   'episode ID and simultaneous/shared-release grouping; count episodes not dependent observations',
   'separately frozen unseen cohort/window and consumption rules before confirmatory scoring'],
  'history_warning':'dense chart points/quote changes are not executed trades and do not establish240min eligibility',
  'forward_policy_status':'requires separate prespecification; not silently added to the frozen historical model/eligibility rules'})
 write(OUT/'manifest.json',{'files':{str(p.relative_to(REPO_ROOT)):sha(p) for p in OUT.iterdir() if p.is_file()},
  'inputs':{str(p.relative_to(REPO_ROOT)):sha(p) for p in [RUN/'manifest.json',SSE/'manifest.json',FOLLOW/'manifest.json',RELEASE/'implementation_manifest.json']}})
 print(json.dumps(report,indent=2))
if __name__=='__main__':main()
