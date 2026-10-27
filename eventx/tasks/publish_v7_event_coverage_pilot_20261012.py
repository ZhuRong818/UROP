"""Supplement earliest-report sensitivity and publish artifact consistency checks."""
from collections import Counter
import json
from pathlib import Path

import numpy as np

from eventx.tasks.analyze_v7_event_coverage_pilot_20261012 import (
    OUT, OBSERVED, TRADES, coverage, counts, stamp,
)
from eventx.tasks.diagnose_v7_signed_evidence_coverage_20261012 import write_json, write_jsonl
from eventx.tasks.run_v5_residual_feasibility import REPO_ROOT, MARKETS, EXAMPLES, read_jsonl, sha256_file
from eventx.tasks.prepare_v3_1_historical_development_arrays import TRADE_DTYPE
from eventx.tasks.build_v4_discovery_examples import EXAMPLE_DTYPE


def main():
    if (OUT/'supplement.json').exists():
        raise SystemExit('Supplement already published; preserve it')
    manifest=json.loads((OUT/'analysis_manifest.json').read_text())
    for e in manifest['artifacts']:
        if sha256_file(REPO_ROOT/e['path'])!=e['sha256']:
            raise RuntimeError(f"Artifact changed: {e['path']}")
    code=Path(__file__).resolve()
    write_json(OUT/'supplement_receipt.json',{'analysis_manifest_sha256':sha256_file(OUT/'analysis_manifest.json'),
        'code_sha256':sha256_file(code),'role':'earliest undated report sensitivity; same rules/horizon/contract pool; no price-guided selection',
        'sigma_positive': 'Separately count positive past volatility; zero-volatility targets remain degenerate under the original recipe.',
        'software_tests_run':False,'forecast_fits':0})
    census=list(read_jsonl(OUT/'policy_headline_census.jsonl'))
    selected=min((a for a in census if a['article_id'] in OBSERVED),key=lambda a:(stamp(a['available_at']),a['article_id']))
    fed=list(read_jsonl(OUT/'fed_contracts.jsonl'))
    markets={int(m['market_index']):m for m in read_jsonl(MARKETS)}
    trades=np.memmap(TRADES,mode='r',dtype=TRADE_DTYPE)
    examples=np.memmap(EXAMPLES,mode='r',dtype=EXAMPLE_DTYPE)
    to=np.searchsorted(trades['market'],np.arange(len(markets)+1,dtype=np.uint32))
    eo=np.searchsorted(examples['market'],np.arange(len(markets)+1,dtype=np.uint32))
    sensitivity=[]
    for m in fed:
        mi=int(m['market_index'])
        sensitivity.append({**coverage(selected,m,trades[to[mi]:to[mi+1]],examples[eo[mi]:eo[mi+1]]),
            'episode_key':'assumed_reported_fomc_hold_20260617','assumption':'Undated hold headline is assumed to concern June 17; event identity is not verified.',
            'direction':0,'evidence_kind':'context_only'})
    ledger=list(read_jsonl(OUT/'episode_contract_ledger.jsonl'))
    arrivals=list(read_jsonl(OUT/'arrival_contract_ledger.jsonl'))
    report=json.loads((OUT/'report.json').read_text())
    signed=[r for r in ledger if r['direction']]
    eligible=[r for r in ledger if r['eligible_under_cached_30m_proxy']]
    observable=[r for r in eligible if r['usable_observation_proxy']]
    sens_eligible=[r for r in sensitivity if r['eligible_under_cached_30m_proxy']]
    sens_observed=[r for r in sens_eligible if r['usable_observation_proxy']]
    supplement={
        'primary_positive_volatility_observation_proxies':counts([r for r in observable if r['past_sigma_240m']>0]),
        'primary_zero_volatility_observation_proxies':counts([r for r in observable if r['past_sigma_240m']==0]),
        'signed_landmarks_60m_freshness_eligible':counts([r for r in signed if r['eligible_under_cached_60m_proxy']]),
        'all_signed_arrivals_30m_eligible':counts([r for r in arrivals if r['direction'] and r['eligible_under_cached_30m_proxy']]),
        'signed_overlapping_loss_counts':dict(Counter(x for r in signed for x in r['eligibility_losses'])),
        'undated_headline_sensitivity':{'article_id':selected['article_id'],'available_at':selected['available_at'],
            'distinct_episode_hypotheses':1,'candidate_contracts':len(sensitivity),'eligible':len(sens_eligible),
            'observed_endpoint_proxies':len(sens_observed),
            'positive_volatility_observation_proxies':sum(r['past_sigma_240m']>0 for r in sens_observed),
            'automatic_signed_features':0,'independent_episode_claim':False,
            'cannot_replace_primary_after_observing_coverage':True},
        'future_prices_or_labels_read':False,'forecast_models_fit':0}
    review=list(read_jsonl(OUT/'selected_packet_assistant_review.jsonl'))
    misses=list(read_jsonl(OUT/'extraction_miss_trace.jsonl'))
    source_packets={r['pair_id']:r for r in read_jsonl(REPO_ROOT/'data/v7/signed_evidence_v03_3_development_20261012/review_packet.jsonl')}
    checks={
        'analysis_artifact_hashes_verified':len(manifest['artifacts']),
        'selected_review_ids_unique_and_complete':len(review)==len({r['pair_id'] for r in review})==len(source_packets)==17,
        'selected_review_evidence_spans_match':all(r['evidence_span'] in '\n'.join(x for x in (source_packets[r['pair_id']]['headline'],source_packets[r['pair_id']].get('summary')) if x) for r in review),
        'all_reviews_correctly_identified_as_assistant':all(r['reviewer_kind']=='assistant' for r in review),
        'all_11_missed_associations_were_legacy_retrieved':len(misses)==11 and all(r['legacy_retrieved'] for r in misses),
        'episode_contract_keys_unique':len(ledger)==len({(r['episode_key'],r['market_index']) for r in ledger}),
        'landmarks_preserve_available_plus_5m_and_30m_horizon':all(stamp(r['decision_at'])-stamp(r['available_at'])==300_000_000 and stamp(r['endpoint_at'])-stamp(r['decision_at'])==1_800_000_000 for r in ledger+sensitivity),
        'all_landmarks_inside_opened_development':all(stamp('2026-05-17T00:00:00Z')<=stamp(r['available_at']) and stamp(r['endpoint_at'])<stamp('2026-07-22T00:00:00Z') for r in ledger+sensitivity),
        'signed_original_training_evaluation_coverage_zero':all(x['usable_signed_observation_proxies']['pairs']==0 for x in report['original_date_blocks'].values()),
        'no_forecasting_fit':report['comparison_gate']['models_fit']==0,
        'software_tests_run':False,
    }
    required=[value for key,value in checks.items() if key not in ('analysis_artifact_hashes_verified','software_tests_run')]
    if not all(required):
        raise RuntimeError('Publication consistency failure')
    write_jsonl(OUT/'undated_report_sensitivity_ledger.jsonl',sensitivity)
    write_json(OUT/'supplement.json',supplement)
    write_json(OUT/'publication_checks.json',checks)
    write_json(OUT/'supplement_manifest.json',{'artifacts':[{'path':str(p.relative_to(REPO_ROOT)),'sha256':sha256_file(p)} for p in [OUT/'supplement_receipt.json',OUT/'supplement.json',OUT/'publication_checks.json',OUT/'undated_report_sensitivity_ledger.jsonl',code]]})
    print(json.dumps(supplement,indent=2))


if __name__=='__main__':
    main()
