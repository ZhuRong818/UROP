"""Assistant evidence inspection and exact-landmark coverage, development only.

No software tests, forecasting fit, protected data or outcome labels are used.
"""
from collections import Counter, defaultdict
from datetime import datetime, timezone
import json
from pathlib import Path

import numpy as np

from eventx.tasks.prepare_v7_event_coverage_pilot_20261012 import OUT, PRIOR
from eventx.tasks.diagnose_v7_signed_evidence_coverage_20261012 import write_json, write_jsonl, utc
from eventx.tasks.run_v5_residual_feasibility import REPO_ROOT, MARKETS, EXAMPLES, read_jsonl, sha256_file, START_US
from eventx.tasks.prepare_v3_1_historical_development_arrays import TRADE_DTYPE
from eventx.tasks.build_v4_discovery_examples import EXAMPLE_DTYPE

MINUTE = 60_000_000
END = int(datetime(2026,7,22,tzinfo=timezone.utc).timestamp()*1e6)
TRADES = REPO_ROOT/'data/v3_1_historical/primary/development/prepared/trades.bin'
AUTHOR = 'codex_development_inspection_20261012'

# Human-readable judgments follow inspection of every supplied candidate text.
# These are case annotations, not a new production extraction algorithm.
MISSES = {
 '188711118': ('bofa_rate_path_20260622', 'now forecasting three interest rate hikes totaling 75 basis points this year', 'Full-year hike forecast in summary; institutional forecast expressed without a direct Fed subject in that clause.'),
 '188933024': ('bofa_rate_path_20260622', 'will bring down the hammer with a series of rate hikes this year', 'Attributed BofA annual-hike forecast is rejected by the bounded actor/action grammar.'),
 '189264702': ('bofa_rate_path_20260622', 'forecast 3 Fed rate hikes in 2026', 'Explicit 2026 Fed hike forecast with nominal rather than finite-verb action.'),
 '189679092': ('bofa_rate_path_20260622', 'expecting three quarter-point rate hikes starting in September', 'Attributed rate path has action, first month and size; actor inheritance is absent. This is repeated reporting of the BofA revision, not a new independent shock.'),
 '192165998': ('kashkari_hike_forecast_20260627', "projects one interest-rate hike this year", 'Fed official supplies the forecast; the official is not the institution action subject expected by the grammar.'),
 '192166050': ('kashkari_hike_forecast_20260627', 'Sees One Rate Hike This Year', 'Named Fed official annual-hike forecast expressed nominally.'),
 '192166054': ('kashkari_hike_forecast_20260627', 'expects a rate hike this year', 'Named Fed official annual-hike forecast; agency/action attribution is indirect.'),
}
OBSERVED = {'184052667','184121848','185200793','185276472','185666251','188301954',
            '188378636','188362517','188704824','188816247','188768405','188828950',
            '189330702','194246827','194310050'}
# Only these two reports state the June meeting/date in the supplied text.
DATED_OBSERVED = {'184121848','188816247'}
AMBIGUOUS_REPORT = {'184033063','190310229','217089786','215664745'}
FORECAST = set(MISSES) | {'63696548','72414713','83423736','171578688','173201321','173736511',
            '174810303','176148147','179235720','179327807','190338995','191753179',
            '192165927','192166017','192166032','196166028','211098890'}
OFFICIAL_COMMENT = {'81785645','90842024','154236977','155036250','155846176',
                  '192198569','197854955','199659218','199986882','200258607','202147088',
                  '210970800','211002660','211098899','211389109'}
ODDS = {'171406426','192198383','206565193','206673730','207107265'}
COLLISIONS = {'219077107','209028511','168190029','216421525','211877377','210581112',
             '126608675','216958493','215528656','180705904','66434216'}
FOREIGN = {'182897122','195874771'}
MEASUREMENT_CONTEXT = {'171427460','206782116'}


def source(a):
    return '\n'.join(x for x in (a['headline'],a.get('summary')) if x)


def stamp(text):
    return int(round(datetime.fromisoformat(text.replace('Z','+00:00')).timestamp()*1e6))


def packet_review(packet):
    rows = []
    for p in packet:
        aid,q = p['article_id'],p['question']
        if aid=='189435511':
            span='the first 25-basis-point hike in September'
            direction = 'supports_yes' if ('increase' in q or q=='Fed rate hike in 2026?') else 'supports_no'
            applicable,claim = 'exact_predicate','forecast'
            reason='Attributed BofA path supports the annual/September hike and opposes earlier-first-hike and September cut/hold scenarios, conditional on year and meeting interpretation.'
        elif aid=='63696548':
            span='The Fed will have to raise interest rates in July'
            direction = 'supports_yes' if q=='Fed rate hike in 2026?' else 'supports_no'
            applicable,claim = ('unresolved' if 'Hike rates by 0bps' in q else 'exact_predicate'),'forecast'
            reason='Yardeni forecast supplies July hike direction, without magnitude. Calendar year is anchored to availability. The 0bps Hike wording needs contract rules before treating it as a hold bucket.'
        else:
            span = {'211002653':'futures traders cut risk','197135093':'lower courts',
                    '202999082':'Fed rate cut bets ease','201331696':'Fed rate cut odds',
                    '199965294':'Fed has cut its target rate to 3.75%'}[aid]
            applicable,direction,claim='material_context','not_applicable','background_or_expectations'
            reason='The supplied wording does not bind the exact action, period and required size/count. The current abstention is supported for this selected debugging example.'
        if span not in source(p):
            raise RuntimeError(f'Review span missing: {aid}')
        rows.append({'pair_id':p['pair_id'],'article_id':aid,'reviewer_id':AUTHOR,'reviewer_kind':'assistant',
            'applicability':applicable,'direction':direction,'claim_type':claim,'evidence_span':span,
            'rationale':reason,'outcome_blind':True,'independent_review':False,
            'prior_algorithm_exposure':True,'meeting_identity_verified':False,
            'public_surprise':'unknown','source_certified':False})
    return rows


def evidence_review(a, census=False):
    aid = a['article_id']
    if aid in MISSES:
        episode,span,note=MISSES[aid]
        role='attributed_forecast_extraction_miss'
    elif aid in AMBIGUOUS_REPORT:
        episode,span,note=None,a['headline'],'Undated/contradictory reported action or headline/summary conflict; not independently verified. Do not promote to an official release.'
        role='unresolved_or_conflicting_report'
    elif aid in OBSERVED:
        episode,span,note='reported_fomc_hold_20260617',a['headline'],'Reports a hold; repeated coverage. Only explicit June meeting/date cases enter the primary report-based event pilot.'
        role='reported_policy_action'
    elif aid in ODDS:
        episode,span,note=None,a['headline'],'Repeats prediction-market odds; not an independently new official decision or signed policy-path assertion.'
        role='prediction_market_odds_reporting'
    elif aid in OFFICIAL_COMMENT:
        episode,span,note=None,a['headline'],'Reported official comment/minutes/opinion does not establish the exact subsequent meeting action. Timing and episode identity remain unresolved.'
        role='official_comment_or_minutes'
    elif aid in FORECAST:
        episode,span,note=None,a['headline'],'Forecast/expectation. Exact full-year counts, negation, past versus remaining-year actions or episode binding require further review; no automatic exact promotion.'
        role='forecast_or_expectation_requires_binding'
    elif aid in COLLISIONS:
        episode,span,note=None,a['headline'],'Keyword refers to a company, corporate payroll, tax or banking stress test; not the intended U.S. macro release.'
        role='keyword_collision'
    elif aid in FOREIGN:
        episode,span,note=None,a['headline'],'Foreign inflation/context does not bind a U.S. release predicate.'
        role='foreign_macro_context'
    elif aid in MEASUREMENT_CONTEXT:
        episode,span,note=None,a['headline'],'Describes a jobs-report market reaction, but omits exact measurement/source/period fields required for a signed threshold.'
        role='measurement_reaction_without_exact_fields'
    else:
        episode,span,note=None,a['headline'],'Preview, generic macro context, odds/bets, hypothetical policy or asset reaction; supplied text lacks an exact dated policy/measurement implication.'
        role='preview_context_or_market_reaction'
    if span not in source(a):
        raise RuntimeError(f'Evidence substring absent: {aid}')
    return {'article_id':aid,'reviewer_id':AUTHOR,'reviewer_kind':'assistant','role':role,
            'episode_key_hypothesis':episode,'evidence_span':span,'rationale':note,
            'primary_dated_report_candidate':aid in DATED_OBSERVED,
            'independent_episode_certified':False,'public_surprise':'unknown'}


def coverage(a,m,trade_rows,examples):
    t0=stamp(a['available_at']); decision=t0+5*MINUTE; endpoint=decision+30*MINUTE
    ts=trade_rows['timestamp_us']; right=int(np.searchsorted(ts,decision,side='right'))
    left=int(np.searchsorted(ts,decision-240*MINUTE,side='right'))
    count=right-left; size=float(trade_rows['notional'][left:right].sum())
    last=int(ts[right-1]) if right else None
    age=(decision-last)/MINUTE if last is not None else None
    terminal=stamp(m['terminal_time']) if m.get('terminal_time') else None
    first=int(ts[0]) if len(ts) else None
    minute_clock=decision//MINUTE*MINUTE
    clocks=np.arange(minute_clock-240*MINUTE,minute_clock+1,MINUTE,dtype=np.int64)
    prior_indices=np.searchsorted(ts,clocks,side='right')-1
    valid=prior_indices>=0
    prior_indices=prior_indices[valid]
    sigma=None
    if len(prior_indices)>=31:
        past_prices=np.clip(trade_rows['price'][prior_indices],0.0001,0.9999)
        sigma=float(np.std(np.diff(np.log(past_prices/(1-past_prices))),ddof=0))
    loss=[]
    if endpoint>=END: loss.append('outside_opened_development_horizon')
    if terminal is None: loss.append('unknown_cached_terminal')
    elif endpoint>terminal: loss.append('at_or_beyond_cached_terminal')
    if first is None or decision<first: loss.append('no_prior_execution')
    if count<3: loss.append('under_three_trailing_executions')
    if size<100: loss.append('under_100_prepared_size_units')
    if age is None or age>30: loss.append('price_age_over_30m_or_missing')
    if sigma is None: loss.append('under_30_one_minute_differences')
    future_right=int(np.searchsorted(ts,endpoint,side='right'))
    future_count=future_right-right
    endpoint_age=(endpoint-int(ts[future_right-1]))/MINUTE if future_right else None
    # Endpoint timestamps are diagnostic denominator losses, never feature eligibility.
    endpoint_observed = future_count>0 and endpoint_age is not None and endpoint_age<=30
    ex_minutes=examples['minute']
    grid_us=START_US+ex_minutes.astype(np.int64)*MINUTE
    lo,hi=np.searchsorted(grid_us,[decision,decision+5*MINUTE],side='left')
    return {'article_id':a['article_id'],'market_index':m['market_index'],'market_id':m['market_id'],
        'question':m['question'],'market_group':m['market_group'], 'available_at':a['available_at'],
        'decision_at':utc(decision),'endpoint_at':utc(endpoint),'last_prior_trade_at':utc(last) if last else None,
        'price_age_minutes':age,'trailing_execution_count_240m':count,'trailing_prepared_size_240m':size,
        'past_sigma_240m':sigma,'cached_terminal_at':m.get('terminal_time'),
        'eligibility_losses':loss,'eligible_under_cached_30m_proxy':not loss,
        'eligible_under_cached_60m_proxy':not [x for x in loss if x!='price_age_over_30m_or_missing'] and age is not None and age<=60,
        'observed_execution_in_future_30m':future_count,'endpoint_last_trade_age_minutes':endpoint_age,
        'endpoint_observed_proxy':endpoint_observed,'stream_complete_at_endpoint':'unknown',
        'usable_observation_proxy':not loss and endpoint_observed,
        'original_grid_rows_next_5m':int(hi-lo),'historical_active_status_verified':False,
        'trade_arrival_clock_verified':False,'contract_rule_version_verified':False,
        'future_outcome_or_price_read':False}


def counts(rows):
    return {'pairs':len(rows),'articles':len({r['article_id'] for r in rows}),
            'markets':len({r['market_id'] for r in rows}),
            'episode_hypotheses':len({r['episode_key'] for r in rows})}


def main():
    if (OUT/'report.json').exists():
        raise SystemExit('Preserve existing analysis; create new version')
    verified={}
    for path in (OUT/'preparation_manifest.json',REPO_ROOT/'data/v3_1_historical/primary/development/prepared/manifest.json'):
        for e in json.loads(path.read_text())['artifacts']:
            verified[e['path']]=e['sha256']
    for p,h in verified.items():
        if sha256_file(REPO_ROOT/p)!=h:
            raise RuntimeError(f'Locked hash mismatch: {p}')
    code=Path(__file__).resolve()
    write_json(OUT/'analysis_receipt.json',{'created_at':datetime.now(timezone.utc).isoformat(),
        'inputs':[{'path':p,'sha256':h} for p,h in sorted(verified.items())],
        'code':{'path':str(code.relative_to(REPO_ROOT)),'sha256':sha256_file(code)},
        'outcome_labels_read':False,'future_price_values_read':False,'protected_holdout_read':False,
        'review_kind':'single assistant development inspection with prior algorithm exposure; not semantic gold'})
    packet=list(read_jsonl(PRIOR/'review_packet.jsonl'))
    reviewed=packet_review(packet)
    sample=list(read_jsonl(OUT/'miss_sample.jsonl'))
    census=list(read_jsonl(OUT/'policy_headline_census.jsonl'))
    sample_review=[evidence_review(a) for a in sample]
    census_review=[evidence_review(a,True) for a in census]
    articles={a['article_id']:a for a in sample+census+packet}
    markets={int(m['market_index']):m for m in read_jsonl(MARKETS)}
    by_id={m['market_id']:m for m in markets.values()}
    automatic={(r['article_id'],r['market_index']):r for r in read_jsonl(OUT/'candidate_decisions.jsonl')}
    candidates=[]
    for p,r in zip(packet,reviewed):
        if r['applicability']!='exact_predicate': continue
        candidates.append({'article_id':p['article_id'],'market_index':by_id[p['market_id']]['market_index'],
            'episode_key':'bofa_rate_path_20260622' if p['article_id']=='189435511' else 'yardeni_july_hike_20260518',
            'evidence_kind':'signed_forecast','direction':1 if r['direction']=='supports_yes' else -1,
            'automatic_exact':True,'source':'selected_packet_assistant_review',
            'evidence_span':r['evidence_span'],'assumptions':['availability-year anchor','same-month meeting bucket interpretation']})
    missed=[]
    for aid,(episode,span,note) in MISSES.items():
        signs={4260:1}
        if aid=='189679092': signs.update({0:-1,4287:1,4376:-1,4406:-1})
        for mi,direction in signs.items():
            record={'article_id':aid,'market_index':mi,'episode_key':episode,
                'evidence_kind':'signed_forecast','direction':direction,'automatic_exact':False,
                'source':'assistant_census_inspection_oracle_only','evidence_span':span,
                'assumptions':['availability-year anchor' if '2026' not in source(articles[aid]) else 'explicit 2026',
                               'same-month meeting interpretation; earlier deadline implied by first September action' if aid=='189679092' else 'annual hike includes forecast future hike'],
                'legacy_retrieved':bool(automatic.get((aid,mi),{}).get('legacy_retrieved',False)),
                'miss_reason':note}
            missed.append({**record,'market_id':markets[mi]['market_id'],'question':markets[mi]['question']})
            candidates.append(record)
    fed=list(read_jsonl(OUT/'fed_contracts.jsonl'))
    for aid in sorted(DATED_OBSERVED):
        for m in fed:
            candidates.append({'article_id':aid,'market_index':int(m['market_index']),
                'episode_key':'reported_fomc_hold_20260617','evidence_kind':'reported_decision_context',
                'direction':0,'automatic_exact':False,'source':'assistant_explicit_date_report_census',
                'evidence_span':source(articles[aid]),
                'assumptions':['reported action not independently official-source verified','broad policy context is not exact relevance or signed evidence for downstream contracts']})
    needed={r['market_index'] for r in candidates}
    raw=np.memmap(TRADES,mode='r',dtype=TRADE_DTYPE)
    trade_offsets=np.searchsorted(raw['market'],np.arange(len(markets)+1,dtype=np.uint32))
    ex=np.memmap(EXAMPLES,mode='r',dtype=EXAMPLE_DTYPE)
    ex_offsets=np.searchsorted(ex['market'],np.arange(len(markets)+1,dtype=np.uint32))
    ledger=[]
    for r in candidates:
        mi=r['market_index']
        trace=coverage(articles[r['article_id']],markets[mi],raw[trade_offsets[mi]:trade_offsets[mi+1]],ex[ex_offsets[mi]:ex_offsets[mi+1]])
        ledger.append({**r,**trace})
    # Earliest evidence arrival chosen irrespective of whether later articles have better coverage.
    episode_pairs={}
    for r in sorted(ledger,key=lambda r:(stamp(r['available_at']),r['article_id'],r['market_index'])):
        episode_pairs.setdefault((r['episode_key'],r['market_index']),r)
    dedup=list(episode_pairs.values())
    signed=[r for r in dedup if r['direction']]
    observed=[r for r in dedup if r['evidence_kind']=='reported_decision_context']
    blocks={}
    for name,start,end in [('original_training_dates','2026-06-30T00:00:00Z','2026-07-11T00:00:00Z'),('original_evaluation_dates','2026-07-11T00:00:00Z','2026-07-22T00:00:00Z')]:
        rows=[r for r in signed if stamp(start)<=stamp(r['decision_at'])<stamp(end)]
        blocks[name]={'signed':counts(rows),'usable_signed_observation_proxies':counts([r for r in rows if r['usable_observation_proxy']])}
    episode_summary=[]
    for episode in sorted({r['episode_key'] for r in ledger}):
        arrival=[r for r in ledger if r['episode_key']==episode]
        selected=[r for r in dedup if r['episode_key']==episode]
        episode_summary.append({'episode_key_hypothesis':episode,'arrival_level':counts(arrival),'earliest_contract_landmarks':counts(selected),
            'eligible':counts([r for r in selected if r['eligible_under_cached_30m_proxy']]),
            'usable_observation_proxies':counts([r for r in selected if r['usable_observation_proxy']]),
            'earliest_available_at':min(r['available_at'] for r in arrival),'certified_independent':False})
    report={'status':'completed_development_diagnosis_no_forecast_fit',
        'selected_review':{'pairs':len(reviewed),'articles':len({r['article_id'] for r in reviewed}),
            'applicability':dict(Counter(r['applicability'] for r in reviewed)), 'human_reviews':0,'independent_accuracy_estimate':False},
        'miss_sample':{'articles':len(sample),'dates':len({r['date_bucket'] for r in sample}),
            'roles':dict(Counter(r['role'] for r in sample_review)),'population_recall_estimate':False},
        'policy_census':{'articles':len(census),'roles':dict(Counter(r['role'] for r in census_review)),
            'reported_action_articles':len(OBSERVED),'explicit_date_primary_reports':len(DATED_OBSERVED),
            'independently_verified_official_events':0},
        'assistant_identified_extraction_misses':{'associations':len(missed),'articles':len(MISSES),
            'episode_hypotheses':len({r['episode_key'] for r in missed}),'legacy_retrieved_associations':sum(r['legacy_retrieved'] for r in missed),
            'validating_gold_or_auto_features':False},
        'all_arrival_level_ledger':counts(ledger),'episode_contract_landmarks':counts(dedup),
        'signed_forecast_landmarks':{'all':counts(signed),'eligible':counts([r for r in signed if r['eligible_under_cached_30m_proxy']]),
            'usable_observation_proxies':counts([r for r in signed if r['usable_observation_proxy']])},
        'reported_decision_context_landmarks':{'all':counts(observed),'eligible':counts([r for r in observed if r['eligible_under_cached_30m_proxy']]),
            'usable_observation_proxies':counts([r for r in observed if r['usable_observation_proxy']])},
        'overlapping_eligibility_losses':dict(Counter(x for r in dedup for x in r['eligibility_losses'])),
        'episode_summary':episode_summary,'original_date_blocks':blocks,
        'comparison_gate':{'decision':'no_fit','reason':'No signed event landmarks reach the original fitting/evaluation date blocks; repeated reports do not supply independent episodes. No replacement split or horizon selected.',
            'models_fit':0,'log_loss':None,'brier':None,'average_precision':None,'predictive_improvement_established':False},
        'checks':{'locked_hashes_verified':len(verified),'exact_review_evidence_substrings':True,'outcome_labels_read':False,
            'future_price_values_read':False,'past_trade_prices_used_for_history_only':True,'protected_holdouts_accessed':False,'software_tests_run':False},
        'limits':['Single assistant review with prior exposure is not independent gold.',
            'Official-source event, first-public clock, historical rule/status and trade-arrival certification remain unknown.',
            'Observed future execution supports an observation proxy, not feed completeness or a certified target.',
            'Prepared size/count units are not proved dollar notional; current historical eligibility is a descriptive proxy.',
            'One decision per episode-contract is chosen at earliest available supported report, without optimizing against price coverage.',
            'The targeted census misses headlines outside its policy-action regex; no population recall estimate.',
            'Reported June decisions cannot provide signed forecasts of already closed June contracts. Downstream links are context-only.']}
    for name,rows in [('selected_packet_assistant_review',reviewed),('miss_sample_assistant_review',sample_review),
            ('policy_census_assistant_review',census_review),('extraction_miss_trace',missed),('arrival_contract_ledger',ledger),('episode_contract_ledger',dedup)]:
        write_jsonl(OUT/(name+'.jsonl'),rows)
    write_json(OUT/'report.json',report)
    paths=sorted(p for p in OUT.iterdir() if p.is_file())+[code]
    write_json(OUT/'analysis_manifest.json',{'artifacts':[{'path':str(p.relative_to(REPO_ROOT)),'sha256':sha256_file(p)} for p in paths]})
    print(json.dumps(report,indent=2))


if __name__=='__main__':
    main()
