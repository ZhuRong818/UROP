"""Prepare a metadata-defined capture pilot, without inspecting market prices."""
import collections
import hashlib
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from eventx.settings import REPO_ROOT

BASE=REPO_ROOT/'data/v7/market_cohort_capture_20261018'
RELEASE=REPO_ROOT/'eventx/release/v7/market_capture_20261018'
MODEL=REPO_ROOT/'data/v5/market_condition_tuning_20261012/selected_model.joblib'
MODEL_HASH='d5d5a8c12fd999674f687c712e14f3a4406e7ab5ec34774baf1828f644f73a3c'
V4=REPO_ROOT/'data/v4/confirmatory/cohort_gate/cohort.jsonl'
SOURCE=BASE/'discovery/1a872b9ecec242109d9383e5554e5a36/polymarket.jsonl'
def sha(p):
 with p.open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()
def write(p,x):p.write_text(json.dumps(x,indent=2,sort_keys=True)+'\n')
def main():
 if RELEASE.exists():raise RuntimeError('Preserve prepared version')
 assert sha(MODEL)==MODEL_HASH
 assert sha(V4)=='30a7a861a566c28365f871cfb4594272adc85c058b9f13ed70a77a9be1e80d05'
 assert sha(SOURCE)=='062078dbe08b687b4de7911fcfec16bff0460fe560dfe2abd81a12e7f56cfdf0'
 protected=[json.loads(l) for l in V4.read_text().splitlines() if l]
 ids={r['market_id'] for r in protected}
 rows=[json.loads(l) for l in SOURCE.read_text().splitlines() if l]
 selected=[];excluded=[]
 for r in rows:
  q=r['question'];d=r.get('description') or '';family=None
  if re.match(r'Will (annual|monthly) inflation ',q) and 'October 2026' in d and 'Bureau of Labor Statistics' in d:
   family='US_CPI_2026_10';event='2026-11-10T13:30:00Z'
  elif q.startswith('Will the October 2026 unemployment rate ') and 'U-3' in d and 'October 2026' in d:
   family='US_EMPLOYMENT_2026_10';event='2026-11-06T13:30:00Z'
  elif q.startswith('Will US GDP growth in Q3 2026 ') and 'Advance Estimate' in d and 'bea.gov' in d:
   family='US_GDP_2026_Q3_ADVANCE';event='2026-10-29T12:30:00Z'
  reason=None
  if r['condition_id'] in ids:reason='protected_v4_exact_id'
  elif family is None:reason='outside_three_exact_US_measurement_predicates; Fed_family_quarantined'
  elif not r['active'] or r['closed'] or r.get('archived'):reason='metadata_not_active'
  elif r['outcomes']!=['Yes','No'] or len(r['clob_token_ids'])!=2:reason='unverified_canonical_yes'
  if reason:excluded.append({'market_id':r['condition_id'],'question':q,'reason':reason});continue
  selected.append({'venue':'polymarket','market_id':r['condition_id'],'yes_asset_id':str(r['clob_token_ids'][0]),
   'no_asset_id':str(r['clob_token_ids'][1]),'question':q,'episode_id':family,'scheduled_release_at':event,
   'end_date':r['end_date'],'metadata_ingest_ts':r['ingest_ts'],'rules':d,'rules_sha256':hashlib.sha256(d.encode()).hexdigest(),
   'canonical_yes_basis':'parallel outcomes and clob_token_ids, outcomes exactly [Yes,No]',
   'v4_exact_id_overlap':False,'v4_resolution_predicate_overlap':'none identified; US measurement, not US Fed policy or Brazil inflation',
   'independence_certified':False,'metadata_freshness':'warehouse snapshot, not proof of current venue state'})
 assert len(selected)==37 and len({r['market_id'] for r in selected})==37
 assert not ids.intersection(r['market_id'] for r in selected)
 RELEASE.mkdir(parents=True)
 for name,rs in [('cohort',selected),('excluded',excluded)]:
  (RELEASE/(name+'.jsonl')).write_text(''.join(json.dumps(r,sort_keys=True)+'\n' for r in rs))
 write(RELEASE/'protected_ids.json',sorted(ids))
 macro=[{'market_id':r['market_id'],'question':r['question']} for r in protected if re.search(r'(CPI|inflation|unemployment|payroll|GDP|gross domestic|Fed |Federal Reserve|interest rate)',r.get('question',''),re.I)]
 write(RELEASE/'v4_metadata_separation.json',{'protected_count':len(ids),'protected_macro_questions':macro,
  'scope':'all470 exact IDs excluded; all Fed decision contracts quarantined; only three direct US measurement predicates admitted',
  'remaining_dependency':'Different predicates still share macro/calendar shocks. This pilot is not a statistically independent confirmation.',
  'protected_payloads_read':False})
 config={'created_at':datetime.now(timezone.utc).isoformat(),'scope':'V7 source/market feasibility capture only; no scoring, fits or labels',
  'source':'Lumid documented Polymarket trades and YES-asset orderbook endpoints',
  'model_path':str(MODEL.relative_to(REPO_ROOT)),'model_sha256':MODEL_HASH,
  'cohort_file':str((RELEASE/'cohort.jsonl').relative_to(REPO_ROOT)),
  'protected_ids_file':str((RELEASE/'protected_ids.json').relative_to(REPO_ROOT)),
  'source_metadata_sha256':sha(SOURCE),'v4_cohort_sha256':sha(V4),
  'cohort_counts':dict(collections.Counter(r['episode_id'] for r in selected)),
  'stop_at':'2026-11-12T00:00:00Z','poll_seconds':120,'request_min_seconds':1.0,
  'warmup_hours':6,'page_limit':1000,'max_pages':10,'overlap_minutes':30,
  'rules':'Capture all37 regardless of observed liquidity. No outcome/price-based cohort changes. Endpoints exact allowlist only.',
  'availability_clock':'local durable response observation; execution/source timestamps retained separately',
  'coverage':'bounded windows only; caps, stalled cursors, failures and schema errors remain unknown, never zero activity',
  'target_reference':'unchanged: 30min absolute YES logodds move >=4 times trailing240min population SD of1min increments; future labels disabled',
  'post_resolution':'Declared end_date upper bound only, not proof of actual tradability. No resolution endpoint is requested.',
  'confirmation':'No confirmatory admission. A later unseen study requires separate protocol/inference/power/consumption freeze.'}
 write(RELEASE/'capture_spec.json',config)
 print(json.dumps({'release':str(RELEASE.relative_to(REPO_ROOT)),'selected':len(selected),'excluded':len(excluded),'episodes':config['cohort_counts']},indent=2))
if __name__=='__main__':main()
