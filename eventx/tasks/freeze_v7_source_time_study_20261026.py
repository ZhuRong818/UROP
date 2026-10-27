"""Freeze target, development comparison, future evaluation and source-only readiness."""
from pathlib import Path
import json
from eventx.tasks.run_v7_source_time_study_20261026 import BASE,REL,DEV,REPO_ROOT
from eventx.tasks.discover_v7_direct_pilot_20261022 import now,sha,write,verify_originals,PROTECTED
from eventx.tasks.run_v7_archive_week_pilot_20261025 import verify
from eventx.v7.source_time_quote_inputs_20261026 import FEATURES,CONTRACT

def main():
 verify_originals();parent=REPO_ROOT/'eventx/release/v7/live_input_compatibility_20261026'
 verify(parent/'delivery_manifest.json');verify(DEV/'cohort/manifest.json')
 REL.mkdir(parents=True,exist_ok=False);BASE.mkdir(parents=True,exist_ok=False)
 source=REPO_ROOT/'eventx/release/v7/memory_quote_20261024/forward_cohort.jsonl'
 (REL/'live_cohort.jsonl').write_bytes(source.read_bytes())
 rows=[json.loads(l) for l in source.read_text().splitlines()];assert len(rows)==2
 assert not {r['market_id'] for r in rows}.intersection(json.loads(PROTECTED.read_text()))
 protocol={
  'version':'source_time_study_20261026','frozen_at':now().isoformat(),'input_contract':CONTRACT,'features':FEATURES,
  'target':'1 iff abs(source-time YES midpoint(t+1800)-source-time YES midpoint(t))>1e-12; otherwise 0; missing/invalid endpoint is unknown',
  'target_interpretation':'Observed 30-minute endpoint quote change, not direction, magnitude, latent exchange movement, resolution, profit or news contribution',
  'measurement':'Frozen SourceTimeQuoteTape.at; only direct price_change BBO, decimal4, source<=availability<=decision, source age<=120s, latest source timestamp, conflicting ties unknown',
  'grid':'Every five minutes 00:30 through 23:25 UTC; endpoint no later than23:55; all scheduled grids retained',
  'historical_inputs':'Only existing May7–9 development50 source; no previous test blocks or reserved unseen10 used',
  'fit_dates':['2026-05-07','2026-05-08'],'development_validation_date':'2026-05-09','refit_dates':['2026-05-07','2026-05-08','2026-05-09'],
  'historical_limit':'Outcome-open development; historical active status not proven. Does not independently validate redesign or live transport.',
  'target_rebuild':'Rebuild labels from raw development quotes using new definition; never reuse old target arrays',
  'models':{'global_rate':'(sum(y)+1)/(n+2)', 'market_rate':'(market positives+20*global rate)/(market n+20); new identity falls back to global',
    'full_logit':{'features':'all14','standardization':'train-only mean/std','C':.1,'max_iter':2000,'random_state':20261026},
    'hgb7':{'max_iter':100,'learning_rate':.05,'max_leaf_nodes':7,'min_samples_leaf':100,'l2_regularization':10,'early_stopping':False,'random_state':20261026}},
  'probability_clip':[1e-6,1-1e-6],'primary_classifier':'hgb7','primary_baseline':'full_logit',
  'selection':'No hyperparameter search, threshold tuning, calibration or segment search. Retain every fixed model and every result; refit all on May7–9.',
  'sample_gate':'Fit>=1000 known rows,>=50 positives and50 negatives,>=8 markets; validation>=200 known rows,>=20 positives and20 negatives',
  'development_model_gate':'hgb7 has lower log loss and no higher Brier than both full_logit and global_rate on May9; failure blocks prospective activation without a new research version',
  'comparison':'Predict for all current-valid rows before filtering endpoints. Score all models on identical known-label keys; unknown endpoints retained.',
  'primary_metric':'Row-weighted log loss; positive contrast means baseline minus classifier',
  'secondary':['Brier','average precision','ROC AUC','per-contract metrics','equal-contract log loss','fixed nonoverlap30min grid','fixed calibration bins','coverage','unknown-label worst/best gain bounds'],
  'calibration_bins':[0,.05,.1,.2,.4,.6,.8,1],
  'inference':'Descriptive matched comparisons only; no IID confidence intervals, significance or independent-event claims from two contracts/seven dates. Missing-label bounds are deterministic, not CIs.',
  'future_test':{
    'status':'NOT_STARTED','cohort':'Both fixed identities in live_cohort.jsonl; no replacement or dropping based on observed prices/results',
    'activation':'Separate immutable activation receipt only after frozen model, model gate, implementation QA and label-blind live readiness pass. Receipt binds model hashes, cohort, first/last grid and evaluator implementation hash before first forecast.',
    'window':'First full UTC day after activation receipt, seven consecutive UTC dates, first00:30 and last23:25; no optional stopping or extension for results',
    'forecast_timing':'Inputs available<=grid; durable prediction emitted<=grid+30s; late/missed decisions abstain, no backfill',
    'current_live_gate':'Frozen feature validity plus connected stream,pong<=35s,30m since known interruption; current exact identity/rules,active acceptingOrders and not closed,posed and undisputed; metadata/resolution age<=360s; expiry>t+1800',
    'endpoint_live_gate':'Same source-time quote validity at t+1800; stream transport ready there; metadata and resolution cover t..t+1800 without invalid observation or gap>360s. No continuous quote path required for primary target.',
    'adjudication':'At endpoint+120s, use only evidence available by endpoint; later data cannot repair endpoint. Null endpoints remain null.',
    'opening':'No prediction performance/labels read before last endpoint+120s. Audit source/emission/model hashes, write one-time consumption receipt, then score exactly once.',
    'minimum_reporting':'Report coverage regardless. Fewer than100 known outcomes or20 positives or20 negatives makes predictive comparison insufficient; do not extend to reach counts.',
    'success':'Descriptive improvement requires hgb7 lower log loss and no higher Brier than full_logit and global_rate. Report other baselines, nonoverlap and missing-outcome bounds even if unfavorable. No automatic deployment.',
    'protected_data':'No OOT,V3.1,V4 or prior opened quote test is used to tune this study.'},
  'live_readiness':'40minute input-only capture on two fixed IDs, no model inference or targets. Gate requires zero schema/scope errors, normal bounded completion,>=2 fully-ready five-minute market-decisions total and>=1 contributing market after30m warmup. Report both identities and all failures. Operational feasibility only, not power or representativeness.',
  'prospective_test_started':False,'trading_enabled':False}
 write(REL/'protocol.json',protocol)
 write(REL/'readiness_spec.json',{'version':'source_time_readiness_20261026','duration_seconds':2400,
   'websocket_url':'wss://ws-subscriptions-clob.polymarket.com/ws/market','poll_seconds':60,
   'metadata_max_age_seconds':360,'scope':'Exact two-market public WebSocket + metadata/resolution; no trades or provider requests',
   'network_failure':'Preserve failures; stop on scope mismatch. 401/403/429 backoff inherited from frozen transport.',
   'model_inference':False,'target_construction':False,'prospective_test_started':False})
 names=['eventx/v7/source_time_study_20261026.py','eventx/tasks/run_v7_source_time_study_20261026.py',
  'eventx/tasks/check_v7_source_time_study_20261026.py','eventx/tasks/collect_v7_source_time_readiness_20261026.py',
  'eventx/tasks/collect_v7_direct_pilot_20261022_v03.py','eventx/v7/source_request_scheduler_v02.py',
  'eventx/v7/quote_experiment_20261024.py','eventx/v7/source_time_quote_inputs_20261026.py','eventx/v7/live_quote_inputs_20261026.py']
 paths=list(REL.iterdir())+[Path(__file__).resolve(),parent/'delivery_manifest.json',DEV/'source_dev/capture_manifest.json',DEV/'cohort/manifest.json',PROTECTED]+[REPO_ROOT/n for n in names]
 write(REL/'implementation_manifest.json',{'files':{str(p.relative_to(REPO_ROOT)):sha(p) for p in paths}})
 write(BASE/'state.json',{'at':now().isoformat(),'phase':'protocol_frozen_before_new_label_construction','prospective_test_started':False})
 state=REPO_ROOT/'CURRENT_STATE.md';s=state.read_text();s=s.replace('live-input audit completed; shared source-time inputs frozen, new fit/validation pending.','source-time target/evaluation protocol frozen; development and live readiness in progress.')
 s=s.replace('## Live-input compatibility (26October)','## Source-time classifier preparation (26October)\n\n- IN PROGRESS:`eventx/release/v7/source_time_study_20261026/protocol.json`;new target/fixed learners frozen before new labels.\n- DevelopmentMay7–9 only;future7daytest requires separate activation after gates. No prospective test started.\n\n## Live-input compatibility (26October)')
 state.write_text(s)
 with (REPO_ROOT/'docs/progress/2026-10.md').open('a') as f:f.write('\n## '+now().isoformat()+' — source-time study protocol frozen\n\nUser authorized target/protocol freeze,matched baseline/classifier development andcurrentinputreadiness beforeprospectivetest. Frozen '+str(REL.relative_to(REPO_ROOT))+'/protocol.json and implementation_manifest.json. Targetnewsource-timeendpointchange;fitMay7–8,validationMay9,refitMay7–9;global/market/full14logistic/fixedHGB7,no search. Sixnewtarget/prediction/boundsunitchecks passed plusnineexistinginputchecks.40min public-source-onlyreadiness planned;no forecasts/labels/model inference duringcapture. Future7daytest gatedandnotstarted.\n')
 print(json.dumps({'frozen_at':protocol['frozen_at'],'protocol_sha256':sha(REL/'protocol.json'),'prospective_test_started':False}))
if __name__=='__main__':main()
