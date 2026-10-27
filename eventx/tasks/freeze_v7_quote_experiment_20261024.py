"""Freeze the new quote target and one exploratory comparison before labels."""
import json
from pathlib import Path
from eventx.tasks.discover_v7_direct_pilot_20261022 import REPO_ROOT,now,sha,write,verify_originals
from eventx.v7.quote_experiment_20261024 import FEATURES

RELEASE=REPO_ROOT/'eventx/release/v7/quote_experiment_20261024'
BASE=REPO_ROOT/'data/v7/quote_experiment_20261024'
AUDIT=REPO_ROOT/'data/v7/direct_source_pilot_20261022_v03/audits/20261024T060327Z_808a25'

def main():
    verify_originals();RELEASE.mkdir(parents=True,exist_ok=False)
    source=REPO_ROOT/'eventx/release/v7/direct_source_pilot_20261022_v03/sample.jsonl'
    samples=[json.loads(l) for l in source.read_text().splitlines()]
    samples=[r for r in samples if r['diagnostic_role']=='prospective_macro_candidate']
    protected=set(json.loads((REPO_ROOT/'eventx/release/v7/market_capture_20261018/protected_ids.json').read_text()))
    if len(samples)!=14 or protected.intersection(r['market_id'] for r in samples):raise RuntimeError('Cohort scope mismatch')
    (RELEASE/'development_cohort.jsonl').write_text(''.join(json.dumps(r,sort_keys=True)+'\n' for r in samples))
    forward=REPO_ROOT/'eventx/release/v7/expansion_source_pilot_20261024/sample.jsonl'
    (RELEASE/'forward_cohort.jsonl').write_bytes(forward.read_bytes())
    policy={'at':now().isoformat(),'authorization':'User approved recommended separately evaluated quote-based experiment',
        'status':'exploratory quote-model study; no claim of confirmatory evidence or release effect',
        'old_trade_model_and_gates_unchanged':True,'target':'Last durably received quality-screened YES-book midpoint as of t+30min',
        'grid_seconds':300,'horizon_seconds':1800,'book_max_age_seconds':120,'status_max_age_seconds':360,
        'max_spread':.05,'min_best_size':10,'history_minutes':240,'positive_volatility_required':False,
        'zero_volatility_reason':'Continuous point forecasting includes unchanged markets; no positive-movement selection',
        'measurement':'Receipt-clock sampled quotes, not latent continuous exchange price, executed trades or outcome probabilities',
        'mapping':'Exact YES token, condition and rules; current active/acceptingOrders true, closed false; resolution status posed and no dispute/resolved_at',
        'forward_status':'Sampled status continuity, no gaps>360s from decision to horizon; scheduled_end alone never suffices; cannot exclude unobserved intrapoll status changes',
        'forward_quotes':'No gaps>120s or failed quality receipts from decision through target; endpoint receipt must predate target',
        'status_cadence_note':'360s is a separately specified tolerance for the original five-minute metadata cadence; does not relax the older trade-study policy',
        'features':FEATURES,'models':['persistence','weighted_midpoint','ridge'],
        'ridge_alpha':100.,'ridge_intercept':True,'standardization':'Training-only population mean/std; zero std replaced by1',
        'ridge_response':'midpoint(t+30)-midpoint(t)','ridge_forecast_clip':[0,1],
        'training':'decision+30min <2026-10-24T00:00:00Z',
        'validation':'decision >=2026-10-24T00:30:00Z and endpoint within fixed completed source snapshot',
        'validation_designation':'Source-exposed retrospective development split, NOT untouched holdout',
        'minimum_training_rows':100,'minimum_training_markets':3,
        'primary_metric':'MAE','secondary_metrics':['RMSE','mean_error','per-market MAE','coverage and missing endpoints'],
        'no_significance_claim':'One short shared calendar period and overlapping targets; no independent news episodes',
        'no_hyperparameter_search':True,'promotion':'None from retrospective result; forward shadow compares all fixed models',
        'forward_start':'First future five-minute grid after activation; no missed grid backfill',
        'forward_cohort':'Two source-pilot markets, selected from metadata; different cohort, no generalization guarantee',
        'forward_emission_seconds':30,'forward_adjudication_delay_seconds':120,
        'forward_collector_stop':'2026-10-24T13:27:27.713863+00:00',
        'news_effect_evaluation':False,'market_resolution_prediction':False,'trading_enabled':False,
        'source_reference':str(AUDIT.relative_to(REPO_ROOT)),
        'resolution_documentation':'https://docs.polymarket.com/api-reference/markets/get-resolution-state',
    }
    write(RELEASE/'policy.json',policy)
    files=list(RELEASE.iterdir())+[Path(__file__).resolve(),source,forward,AUDIT/'manifest.json',
        REPO_ROOT/'eventx/v7/quote_experiment_20261024.py',REPO_ROOT/'eventx/tasks/run_v7_quote_experiment_20261024.py']
    write(RELEASE/'implementation_manifest.json',{'locked_files':{str(p.relative_to(REPO_ROOT)):sha(p) for p in files}})
    print(json.dumps({'release':str(RELEASE.relative_to(REPO_ROOT)),'development_markets':len(samples),'outcomes_opened':False}))

if __name__=='__main__':main()
