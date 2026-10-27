"""Freeze a diagnostic sample and source-comparison plan before fetching prices."""
import json
from datetime import datetime,timezone
from eventx.settings import REPO_ROOT
from eventx.tasks.discover_v7_source_control_20261018 import BASE,sha,write

RELEASE=REPO_ROOT/'eventx/release/v7/source_verification_20261018'
def main():
 if RELEASE.exists():raise RuntimeError('Preserve diagnostic version')
 cohort=REPO_ROOT/'eventx/release/v7/market_capture_20261018/cohort.jsonl'
 controls=BASE/'control_discovery/b4c7dbd8a97943ac850ae7f38b609063/candidates.jsonl'
 protected=REPO_ROOT/'eventx/release/v7/market_capture_20261018/protected_ids.json'
 forbidden=set(json.loads(protected.read_text()))
 rs=[json.loads(l) for l in cohort.read_text().splitlines()]
 questions=['Will monthly inflation increase by 0.3% in October?',
  'Will the October 2026 unemployment rate be 4.2%?',
  'Will US GDP growth in Q3 2026 be between 2.0% and 2.5%?']
 selected=[]
 for q in questions:
  r=next(x for x in rs if x['question']==q)
  selected.append({**r,'diagnostic_role':'macro_sample_by_question_only'})
 for i,line in enumerate(controls.read_text().splitlines()):
  r=json.loads(line)
  if r['outcomes']!=['Yes','No'] or len(r['clob_token_ids'])!=2:continue
  selected.append({'market_id':r['condition_id'],'question':r['question'],
   'yes_asset_id':str(r['clob_token_ids'][0]),'no_asset_id':str(r['clob_token_ids'][1]),
   'diagnostic_role':'control_candidate','metadata_rank':i+1,'metadata_liquidity':r['liquidity_num'],
   'metadata_reported_volume24hr':r['reported_volume24hr'],'metadata_ingest_ts':r['ingest_ts'],
   'independently_liquid_verified':False})
 assert len(selected)==8 and not forbidden.intersection(r['market_id'] for r in selected)
 RELEASE.mkdir(parents=True)
 (RELEASE/'sample.jsonl').write_text(''.join(json.dumps(r,sort_keys=True)+'\n' for r in selected))
 plan={'created_at':datetime.now(timezone.utc).isoformat(),'purpose':'Step1 source verification only; no predictive admission or research-cohort expansion',
  'selection':'three fixed macro predicates plus all five pre-price liquidity-ranked control candidates; current liquidity must be verified independently',
  'v4_exact_id_intersection':0,'source_metadata_hashes':{str(p.relative_to(REPO_ROOT)):sha(p) for p in [cohort,controls,protected]},
  'model_path':'data/v5/market_condition_tuning_20261012/selected_model.joblib',
  'model_sha256':'d5d5a8c12fd999674f687c712e14f3a4406e7ab5ec34774baf1828f644f73a3c',
  'rest_rounds':2,'history_hours':6,'stream_seconds':180,'stream_max_frames':50000,
  'lumid_min_request_seconds':2,'public_min_request_seconds':0.5,
  'sources':{'lumid':'https://lum.id/findata','polymarket_clob':'https://clob.polymarket.com',
   'polymarket_trades':'https://data-api.polymarket.com','polymarket_websocket':'wss://ws-subscriptions-clob.polymarket.com/ws/market'},
  'documentation':[
   'https://docs.polymarket.com/market-data/prices-order-books',
   'https://docs.polymarket.com/api-reference/core/get-trades-for-a-user-or-markets',
   'https://docs.polymarket.com/api-reference/markets/get-prices-history',
   'https://docs.polymarket.com/market-data/realtime-data',
   'data/v7/market_cohort_capture_20261018/probes/c116b6a48bf64e7fb98a6eecdbc91f37/openapi.json'],
  'comparison':'same absolute trade window per REST round; direct takerOnly=false. Store caps and per-request clocks. Do not assume matching rows/semantics.',
  'price_history_limitation':'Lumid candles mix trade prints and quote mids; direct YES history is not assumed equivalent or evidence of executed-trade freshness.',
  'liquid_control_rule':'first metadata-ranked candidate with fresh two-sided direct book AND >=3 canonical YES fills in preceding60m; otherwise no liquid control established',
  'failure_rule':'HTTP errors, inaccessible endpoints, incomplete streams and empty lists do not prove inactivity. No silent source substitution.',
  'protected_protocol':'check exact allowlist before requests; subscribe only sample YES/NO assets; no custom lifecycle/new-market stream; abort unexpected market IDs',
  'model_development':'blocked until at least one complete prospectively captured observation passes source,240m history,freshness,30m forward,terminal and relevance gates',
  'collectors':'preserve both existing services, frozen code, configuration and live journals unchanged by diagnostic',
  'stream_interpretation':'finite diagnostic intervals only; lack of updates is not proof of long-run inactivity or source completeness'}
 write(RELEASE/'plan.json',plan)
 paths=[RELEASE/'sample.jsonl',RELEASE/'plan.json',REPO_ROOT/'eventx/tasks/prepare_v7_source_verification_20261018.py',
  REPO_ROOT/'eventx/tasks/run_v7_source_verification_20261018.py']
 for rel in ['eventx/release/v7/market_capture_20261018/implementation_manifest.json',
  'eventx/release/v7/original_source_capture_20261018_v02/implementation_manifest.json']:
  m=json.loads((REPO_ROOT/rel).read_text())
  for p,h in m['locked_files'].items():assert sha(REPO_ROOT/p)==h
  paths.append(REPO_ROOT/rel)
 assert sha(REPO_ROOT/plan['model_path'])==plan['model_sha256']
 write(RELEASE/'implementation_manifest.json',{'locked_files':{str(p.relative_to(REPO_ROOT)):sha(p) for p in paths}})
 print(json.dumps({'release':str(RELEASE.relative_to(REPO_ROOT)),'markets':len(selected),'control_candidates':5}))
if __name__=='__main__':main()
