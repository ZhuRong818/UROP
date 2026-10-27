"""Freeze a prospective feasibility policy before fetching expansion metadata.

This is an operational feasibility branch, not a confirmatory evaluation freeze.
No model is loaded and no outcome data are opened.
"""
import json
from pathlib import Path
from eventx.tasks.discover_v7_direct_pilot_20261022 import (
    REPO_ROOT, PROTECTED, MODEL_HASH, now, sha, write, verify_originals,
)

RELEASE = REPO_ROOT / 'eventx/release/v7/forecast_path_20261023'

def main():
    locks = verify_originals()
    RELEASE.mkdir(parents=True, exist_ok=False)
    at = now().isoformat()
    write(RELEASE/'policy.json', {
        'version': 'v7_prospective_feasibility_20261023', 'frozen_at': at,
        'authorization': 'User: follow your plan continue the research to produce usable forecasting',
        'scope': 'Prospective feasibility and staged shadow forecasting; not confirmation, trading, or a replacement of earlier studies',
        'model_sha256': MODEL_HASH, 'model_scoring_enabled': False,
        'source_convention': 'unselected; provider/direct compatibility review must precede activation',
        'target': {'horizon_seconds': 1800, 'grid_seconds': 300,
                   'definition': 'abs(logit(pYES(t+30m))-logit(pYES(t))) >= 4*sigma240(t)',
                   'price_clip': [0.0001, 0.9999], 'sigma_ddof': 0,
                   'sigma_window_one_minute_increments': 240, 'positive_sigma_required': True},
        'decision': {
            'input_available_by': 't, using durable local receipt time; no post-t information',
            'issued_by': 't+30 seconds; log late computation as missed, never backdate',
            'latest_yes_trade_max_age_seconds': 300,
            'min_yes_count60': 3, 'min_yes_count240': 3, 'min_yes_quantity240': 100,
            'trailing_window': '(t-window,t]', 'quantity_unit': 'YES token quantity, not cash',
            'warmup': '241 seeded minute prices ending at t; no unresolved receipt gaps in the four-hour input interval',
            'same_timestamp': 'abstain if prices differ at a sampled minute and source-consistent execution order is unresolved',
            'status': 'authenticated current mapping/rules and accepting-orders status received by t, at most120s old; scheduled end alone is insufficient',
            'news_readiness': 'original release and defensible evidence link durably available by t; record unknown novelty/direction instead of inventing them',
            'receipt_gap_limit_seconds': 120,
            'gap_limit_caveat': 'Necessary operational bound, not proof of completeness; require uncapped, scope-valid reconciliation and documented counting semantics',
        },
        'endpoint': {
            'target_time': 't+1800 seconds', 'latest_trade_not_after_target': True,
            'latest_yes_trade_max_age_seconds': 300,
            'receipt_deadline_seconds_after_target': 120,
            'selection': 'latest unambiguous canonical YES execution at or before target among receipts durable by target+120s',
            'no_future_nearest_trade': True,
            'status': 'resolution/status evidence covers decision through target, with no unresolved gap >120s; conflicting or incomplete evidence makes outcome unavailable',
            'missing': 'retain issued forecast, mark outcome unavailable with reason; never silently remove from coverage denominator',
            'late_backfill': 'diagnostic only; never repair the primary endpoint after its deadline',
        },
        'stages': [
            'Record source-feasibility dossiers; model scoring stays disabled.',
            'One full prospective episode observation passes all decision and endpoint gates, plus feature/source compatibility.',
            'Freeze an activation receipt for later five-minute grids; do not score the first observation retrospectively as a live forecast.',
            'Issue fixed-model shadow probabilities and abstentions before outcomes; append outcomes separately.',
            'Freeze comparator artifacts, unseen evaluation window and dependence-aware analysis before a confirmatory comparison.',
        ],
        'measurement_choices': '300s freshness inherited;120s receipt/status bounds and30s emission budget are new operational design choices, not optimized or empirically validated thresholds',
        'no_outcome_based_retuning': True, 'controls_are_not_news_cohort': True,
        'first_reserved_episode': '2026-10-29T12:30:00+00:00',
        'activation_remains_gated': True, 'predictive_admissions': 0,
    })
    write(RELEASE/'expansion_policy.json', {
        'frozen_at': at, 'venue': 'polymarket', 'maximum_rows': 1000,
        'end_after': at, 'end_before': '2027-03-01T00:00:00Z',
        'question_pattern': '(consumer price|inflation|unemployment|payroll|gross domestic|GDP|personal consumption|PCE|recession|job openings|retail sales|personal income|consumer spending)',
        'quarantine_pattern': '(federal reserve|fomc|fed rate|fed cut|fed hike|interest rate)',
        'protected_ids_path': str(PROTECTED.relative_to(REPO_ROOT)), 'protected_ids_sha256': sha(PROTECTED),
        'projection': ['condition_id','question','outcomes','clob_token_ids','active','closed','archived','start_date','end_date','ingest_ts','source','source_run_id','description','resolution_source'],
        'prohibited': ['prices','outcome prices','results','labels','trade histories','volume/liquidity ranking'],
        'ordering': 'condition_id ascending; cap reached means incomplete universe, no automatic enrollment',
        'selection': 'retain all metadata records and exclusions; separate existing14 from new US official-statistic rule candidates; ambiguous rules require adjudication',
        'release_links': 'Reuse reserved episodes only for metadata feasibility; later releases require calendar verification and new reservation',
        'survival': 'end_date > release+90min is necessary screening only; early resolution requires separate rule/status review',
        'activity_screen_plan': 'For a separately enrolled cohort, freeze IDs before collecting a24h pre-event activity window. Retain all members and all failures; issue only on valid decision grids. Do not rank by subsequent returns.',
        'automatic_predictive_admission': False,
    })
    write(RELEASE/'ledger_schema.json', {
        'decision_required': ['study_version','cohort_version','episode_id','market_id','grid_at','recorded_at','source_convention_sha256','model_sha256','input_receipt_hashes','feature_vector_sha256','decision_gates','status','probability_or_null','abstention_reasons'],
        'decision_statuses': ['feasibility_only','abstained','issued_shadow','missed_emission_deadline'],
        'outcome_required': ['decision_record_sha256','target_at','adjudicated_at','endpoint_receipt_hashes','endpoint_gates','outcome_status','label_or_null','missing_reasons'],
        'outcome_statuses': ['pending','observed','unavailable'],
        'append_only': True, 'no_current_forecast_rows_created': True,
        'primary_reporting': ['scheduled_grids','issued_forecasts','abstentions_by_reason','outcomes_observed','outcomes_unavailable','distinct_release_episodes','matched_baseline_metrics_when_frozen'],
        'comparators': 'Frozen logistic and training-prevalence artifacts still need preparation; no historical scores reused as current forecasts',
    })
    paths = list(RELEASE.iterdir()) + [Path(__file__).resolve(), PROTECTED]
    write(RELEASE/'manifest.json', {'created_at': at,'original_locks_verified': locks,
        'files': {str(p.relative_to(REPO_ROOT)): sha(p) for p in paths}})
    print(json.dumps({'release':str(RELEASE.relative_to(REPO_ROOT)), 'original_locks_verified':locks, 'scoring_enabled':False}))

if __name__ == '__main__':
    main()
