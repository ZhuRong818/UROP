"""Freeze a label-free operational snapshot of actual capture receipts."""
import collections
import hashlib
import json
from datetime import datetime,timezone
from pathlib import Path
from eventx.settings import REPO_ROOT
from eventx.tasks.prepare_v7_market_capture_20261018 import BASE,RELEASE,sha,write

def main():
 at=datetime.now(timezone.utc);out=BASE/'health'/at.strftime('%Y%m%dT%H%M%SZ');out.mkdir(parents=True)
 live=BASE/'live';raw=(live/'journal.jsonl').read_bytes()
 if raw and not raw.endswith(b'\n'):raw=raw[:raw.rfind(b'\n')+1]
 (out/'journal_snapshot.jsonl').write_bytes(raw)
 records=[json.loads(l) for l in raw.splitlines() if l];head=None;payloads=set();request_ids=[]
 protected=set(json.loads((RELEASE/'protected_ids.json').read_text()))
 cohort=[json.loads(l) for l in (RELEASE/'cohort.jsonl').read_text().splitlines()];ids={r['market_id'] for r in cohort}
 for r in records:
  v=dict(r);digest=v.pop('record_sha256');assert v['previous_sha256']==head
  assert hashlib.sha256(json.dumps(v,sort_keys=True,separators=(',',':')).encode()).hexdigest()==digest
  head=digest
  if r.get('market_id'):assert r['market_id'] in ids and r['market_id'] not in protected
  if r.get('payload_sha256'):
   h=r['payload_sha256'];assert sha(live/'objects'/h)==h;payloads.add(h)
  if r.get('http_status')==500:
   value=json.loads((live/'objects'/r['payload_sha256']).read_text())
   request_ids.append({'market_id':r['market_id'],'kind':r['kind'],'at':r['finished_at'],'request_id':value.get('request_id')})
 statuses={}
 for name,p in [('market',live/'status.json'),('original_source',REPO_ROOT/'data/v7/official_source_capture_20261018/live/status.json')]:
  body=p.read_bytes();(out/(name+'_status.json')).write_bytes(body);s=json.loads(body)
  statuses[name]={'at':s['at'],'pid':s['pid'],'heartbeat_age_seconds':(at-datetime.fromisoformat(s['at'])).total_seconds()}
  if name=='original_source':statuses[name].update(document_versions=s['document_versions'],market_data_read=s['market_data_read'])
 market=json.loads((out/'market_status.json').read_text());values=list(market['markets'].values())
 locks=json.loads((RELEASE/'implementation_manifest.json').read_text())['locked_files']
 mismatches=[p for p,h in locks.items() if sha(REPO_ROOT/p)!=h];assert not mismatches
 cfg=json.loads((RELEASE/'capture_spec.json').read_text());assert sha(REPO_ROOT/cfg['model_path'])==cfg['model_sha256']
 # Connectivity failures from the sandbox cycle are retained separately.
 network=[r for r in records if r.get('http_status') is not None]
 real_windows=[r for r in records if r['kind']=='window_summary' and r['summary'].get('trades_http_status') is not None]
 summary={'at':at.isoformat(),'journal_records':len(records),'journal_head_sha256':head,'unique_payloads_verified':len(payloads),
  'implementation_files_verified':len(locks),'model_sha256':cfg['model_sha256'],'v4_exact_id_intersection':len(ids&protected),
  'source_metadata_candidates':178,'capture_cohort':len(cohort),'excluded_metadata_candidates':141,
  'episode_counts':dict(collections.Counter(r['episode_id'] for r in cohort)),
  'scheduled_dates':sorted({r['scheduled_release_at'] for r in cohort}),'independent_events_established':False,
  'http_observations':dict(collections.Counter(str(r['http_status']) for r in network)),
  'sandbox_connect_errors':sum(r.get('error_type')=='ConnectError' for r in records),
  'first_network_request_at':min((r['requested_at'] for r in network),default=None),
  'completed_network_window_summaries':len(real_windows),
  'latest_market_trades_http_status':dict(collections.Counter(str(v.get('trades_http_status')) for v in values)),
  'latest_market_quotes_http_status':dict(collections.Counter(str(v.get('quotes_http_status')) for v in values)),
  'latest_windows_returned_trade_rows':sum(v.get('last_window_rows',0) for v in values),
  'latest_windows_returned_yes_rows':sum(v.get('last_window_yes_rows',0) for v in values),
  'markets_with_nonempty_quote':sum(bool(v.get('latest_quote_rows')) for v in values),
  'markets_with_unknown_window':sum(v.get('last_window_status')=='unknown_incomplete' for v in values),
  'server_error_request_ids':request_ids,'process_status_snapshots':statuses,
  'coverage_interpretation':'HTTP success/empty window does not certify provider completeness or no trading. No predictive sample admitted.',
  'prices_or_outcomes_scored':False,'labels_or_predictions_computed':False,'software_tests_run':False}
 write(out/'report.json',summary)
 write(out/'manifest.json',{'files':{str(p.relative_to(REPO_ROOT)):sha(p) for p in out.iterdir() if p.is_file()}})
 print(json.dumps({'directory':str(out.relative_to(REPO_ROOT)),'report':summary},indent=2))
if __name__=='__main__':main()
