"""Snapshot live source-capture receipt integrity without reading market data."""
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
import hashlib
import json

ROOT=Path(__file__).resolve().parents[2]
BASE=ROOT/'data/v7/official_source_capture_20261018'
LIVE=BASE/'live'
RELEASE=ROOT/'eventx/release/v7/original_source_capture_20261018_v02'
def sha(p):
 with p.open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()
def canon(r):return json.dumps(r,sort_keys=True,separators=(',',':'),allow_nan=False).encode()
def main():
 state=json.loads((LIVE/'status.json').read_text());n=state['journal_records'];head=None;rows=[];payloads={}
 with (LIVE/'journal.jsonl').open() as f:
  for i,line in enumerate(f,1):
   if i>n:break
   r=json.loads(line);h=r.pop('record_sha256')
   if r['sequence']!=i or r['previous_sha256']!=head or hashlib.sha256(canon(r)).hexdigest()!=h:raise RuntimeError('Journal chain failure')
   head=h;rows.append(r)
   data=r['data']
   if data.get('payload_path'):payloads[data['payload_path']]=data['payload_sha256']
 if len(rows)!=n or head!=state['journal_head_sha256']:raise RuntimeError('State/journal mismatch')
 for rel,h in payloads.items():
  if sha(ROOT/rel)!=h:raise RuntimeError('Source body hash mismatch')
 manifest=json.loads((RELEASE/'implementation_manifest.json').read_text())
 for rel,h in manifest['locked_files'].items():
  if sha(ROOT/rel)!=h:raise RuntimeError('Implementation/model changed')
 observations=[r['data'] for r in rows if r['kind']=='observation']
 docs=[r['data'] for r in rows if r['kind']=='document_version']
 current=[r for r in docs if r.get('cohort_role')=='prospective_source_candidate_not_forecast_admission']
 critical=['https://www.federalreserve.gov/feeds/press_monetary.xml','https://www.federalreserve.gov/feeds/speeches_and_testimony.xml','https://apps.bea.gov/rss/rss.xml']
 requests=Counter(r['url'] for r in observations)
 source_counts={u:requests[u] for u in critical}
 out=BASE/'health'/datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ');out.mkdir(parents=True,exist_ok=False)
 report={'checked_at':datetime.now(timezone.utc).isoformat(),'status_timestamp':state['at'],'collector_pid':state['pid'],
  'started_at':state['started_at'],'journal_records_verified':n,'unique_source_payloads_verified':len(payloads),
  'document_versions':len(docs),'historical_baseline_versions':sum(r.get('cohort_role')=='historical_baseline_import' for r in docs),
  'prospective_source_candidate_versions':len(current),'source_candidate_timeliness_authenticated':False,
  'requests_by_critical_feed':source_counts,'feed_poll_repeats_observed':all(requests[u]>=2 for u in critical),
  'critical_feeds_last_status':{u:state['urls'].get(u,{}) for u in critical},
  'latest_http_status_counts':dict(Counter(str(r.get('http_status')) for r in state['urls'].values())),
  'latest_failed_sources':{u:r for u,r in state['urls'].items() if r['status']=='unknown_failed_request'},
  'source_failures':[{'url':r['url'],'error_type':r.get('error_type'),'error':r.get('error'),'http_status':r.get('http_status')} for r in observations if r['status']=='unknown_failed_request'],
  'implementation_and_model_hashes_match':True,'model_fixed':'condition_120k','forecast_models_fit':0,
  'market_payloads_read':False,'protected_payloads_read':False,'forecast_metrics_computed':False,
  'limits':['Receipt integrity is not provider completeness, original-publication timing or event independence.','Initial old feed items are baseline imports; future targets are scheduled, not achieved captures.','Local uptime/network required; BLS403 remains recorded, official DOL copies separate.']}
 (out/'status_snapshot.json').write_text(json.dumps(state,indent=2,sort_keys=True)+'\n')
 (out/'report.json').write_text(json.dumps(report,indent=2,sort_keys=True)+'\n')
 (out/'manifest.json').write_text(json.dumps({'artifacts':{str(p.relative_to(ROOT)):sha(p) for p in out.iterdir() if p.is_file()}},indent=2)+'\n')
 print(json.dumps({'health_directory':str(out.relative_to(ROOT)),**report},indent=2))
if __name__=='__main__':main()
