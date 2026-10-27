"""Freeze metadata-based source sample and future feasibility reservation."""
import hashlib
import json
import plistlib
from datetime import timedelta
from collections import Counter
from eventx.settings import REPO_ROOT
from eventx.tasks.discover_v7_direct_pilot_20261022 import (
    BASE, RELEASE, PROTECTED, MODEL, MODEL_HASH, now, sha, write, verify_originals)

DISCOVERY = BASE/'discovery/62630a35cf47405aa74f3544ac4e1fc3'
LABEL = 'com.eventx.direct-source-pilot.20261022'

def classify(row):
    q, d = row['question'], row.get('description') or ''
    if q.startswith('Will US GDP growth in 2026 ') and 'full-year real GDP growth rate' in d and 'Q4 of 2026' in d:
        return 'US_GDP_FULL_YEAR_2026'
    if q.startswith('Will inflation reach more than ') and 'in 2026?' in q and 'Bureau of Labor Statistics' in d and 'any month in 2026' in d:
        return 'US_CPI_ANY_MONTH_2026'
    if q.startswith('Will US unemployment reach at least ') and 'in 2026?' in q and 'U-3' in d and 'reference month in 2026' in d:
        return 'US_UNEMPLOYMENT_ANY_MONTH_2026'
    return None

def convert(r, role, family=None, rank=None):
    assert r['outcomes'] == ['Yes', 'No'] and len(r['clob_token_ids']) == 2
    d = r.get('description') or ''
    return {'market_id': r['condition_id'], 'question': r['question'], 'yes_asset_id': str(r['clob_token_ids'][0]),
            'no_asset_id': str(r['clob_token_ids'][1]), 'diagnostic_role': role, 'family': family,
            'metadata_rank': rank, 'end_date': r['end_date'], 'rules': d,
            'rules_sha256': hashlib.sha256(d.encode()).hexdigest(), 'metadata_ingest_ts': r['ingest_ts'],
            'terminal_caveat': 'Any-month threshold contracts can resolve early; end_date does not establish survival.',
            'predictive_admitted': False}

def main():
    if RELEASE.exists():
        raise RuntimeError('Preserve prepared release')
    verify_originals()
    forbidden = set(json.loads(PROTECTED.read_text()))
    macro = [json.loads(l) for l in (DISCOVERY/'macro.jsonl').read_text().splitlines()]
    controls = [json.loads(l) for l in (DISCOVERY/'controls.jsonl').read_text().splitlines()]
    candidates, excluded = [], []
    for r in macro:
        family = classify(r)
        reason = None
        if r['condition_id'] in forbidden:
            reason = 'protected'
        elif family is None:
            reason = 'outside_exact_longer_lived_US_predicates_or_ambiguous_rules'
        elif r['outcomes'] != ['Yes', 'No'] or len(r['clob_token_ids']) != 2:
            reason = 'unverified_yes_mapping'
        if reason:
            excluded.append({'market_id': r['condition_id'], 'question': r['question'], 'reason': reason})
        else:
            candidates.append(convert(r, 'prospective_macro_candidate', family))
    sample = list(candidates)
    old = [json.loads(l) for l in (REPO_ROOT/'eventx/release/v7/source_verification_20261018/sample.jsonl').read_text().splitlines()]
    sample += [{**r, 'diagnostic_role': 'legacy_macro_source_comparison_only'} for r in old if r['diagnostic_role']=='macro_sample_by_question_only']
    for rank, r in enumerate(controls, 1):
        sample.append(convert(r, 'activity_control_candidate', rank=rank))
    assert len(candidates)==14 and len(sample)==22
    assert not forbidden.intersection(r['market_id'] for r in sample)
    assert len({r['market_id'] for r in sample})==len(sample)
    RELEASE.mkdir(parents=True)
    for name, rows in [('sample', sample), ('prospective_candidates', candidates), ('excluded_metadata', excluded)]:
        (RELEASE/(name+'.jsonl')).write_text(''.join(json.dumps(r, sort_keys=True)+'\n' for r in rows))
    at = now()
    write(RELEASE/'spec.json', {
        'created_at': at.isoformat(), 'scope': 'Phase A source rehearsal only; no forecast scores, targets or predictive admissions',
        'selection': 'All exact longer-lived US annual GDP / any-month CPI / any-month U3 metadata predicates; three prior macro diagnostics; first five BTC controls by pre-price metadata liquidity.',
        'rehearsal_stop_at': (at+timedelta(hours=25)).isoformat(),
        'live_duration_seconds': 86400, 'poll_seconds': 60, 'max_pages': 10,
        'websocket_url': 'wss://ws-subscriptions-clob.polymarket.com/ws/market',
        'model_path': str(MODEL.relative_to(REPO_ROOT)), 'model_sha256': MODEL_HASH,
        'protected_ids_sha256': sha(PROTECTED), 'v4_overlap': 0,
        'sample_counts': dict(Counter(r['diagnostic_role'] for r in sample)),
        'candidate_family_counts': dict(Counter(r['family'] for r in candidates)),
        'trade_windows': 'first/every fifth cycle matched six-hour source window; other venue cycles thirty-minute overlap; endpoint coverage is not exchange completeness',
        'receipt_clocks': 'requested_at, response_received_at, durable available_at, finished_at; source timestamps preserved in raw bodies',
        'scope_rule': 'exact market/token allowlists; reject unexpected response scopes before raw storage; no broad market streams',
        'gap_rule': 'journal/reconnect gaps unknown; REST backfill receives current availability and cannot restore timely capture',
        'dedup_rule': 'preserve raw prints; compare multiset normalized asset/second/price/size/side; never treat identical prints as proven unique transactions',
        'restart_rule': 'flock single process, validate append journal chain, same absolute deadline; a restart is a continuity gap',
        'control_rule': 'first pre-ranked candidate with fresh two-sided uncrossed book and >=3 YES prints60m; only a dated activity check',
        'rehearsal_criteria': 'finish elapsed24h with reconciled source windows, documented all reconnect/cap/errors and per-market gaps; no automatic eligibility or cohort promotion',
        'dependencies': 'original release collector unchanged; no newly captured release currently documented; forward-latency and terminal gate still need validation',
        'documentation': ['https://docs.polymarket.com/api-reference/core/get-trades-for-a-user-or-markets',
                          'https://docs.polymarket.com/market-data/realtime-data',
                          'https://docs.polymarket.com/api-reference/markets/get-markets']})
    dates = [('2026-10-29T12:30:00+00:00', ['GDP advance Q3', 'PCE September'], 'bea'),
             ('2026-11-06T13:30:00+00:00', ['Employment October'], 'bls_nov'),
             ('2026-11-10T13:30:00+00:00', ['CPI October', 'Real Earnings October'], 'bls_nov'),
             ('2026-11-13T13:30:00+00:00', ['PPI October'], 'bls_nov'),
             ('2026-11-25T13:30:00+00:00', ['GDP second Q3 and corporate profits', 'PCE October'], 'bea'),
             ('2026-12-04T13:30:00+00:00', ['Employment November'], 'bls_dec')]
    calendar_urls = {'bea': 'https://www.bea.gov/news/schedule', 'bls_nov': 'https://www.bls.gov/schedule/2026/11_sched.htm',
                     'bls_dec': 'https://www.bls.gov/schedule/2026/12_sched.htm'}
    episodes = []
    for dt, names, src in dates:
        episodes.append({'episode_id': 'US_RELEASE_'+dt[:10], 'scheduled_at': dt, 'components': names,
                         'calendar_source': calendar_urls[src], 'verified_on': '2026-10-22',
                         'status': 'reserved_future_feasibility_episode; collection_activation_pending_source_readiness',
                         'independence_certified': False, 'predictive_admissions': 0})
    write(RELEASE/'episode_reservation.json', {'episodes': episodes, 'administrative_end': '2026-12-05T00:00:00+00:00',
        'status': 'fixed feasibility reservation; not confirmation or asserted source readiness',
        'no_replacement_rule': 'Failed capture, quiet markets, premature resolution or absent relevant evidence remain zero-yield episodes. Reschedules retained with original identity and receipts; do not replace based on returns.',
        'activation_deadline_first_episode': '2026-10-29T06:30:00+00:00',
        'six_episode_budget_is_not_power': True})
    links = []
    for event in episodes:
        for r in candidates:
            family = r['family']
            components = ' '.join(event['components'])
            if family=='US_GDP_FULL_YEAR_2026' and 'GDP' in components:
                role, rationale = 'component_evidence', 'Q3 output and revisions contribute to the annual GDP measure; Q4 advance resolves later.'
            elif family=='US_CPI_ANY_MONTH_2026' and 'CPI' in components:
                role, rationale = 'direct_component_with_terminal_risk', 'A newly reported month updates an any-month annual threshold; crossing it terminates the contract and excludes the forward target.'
            elif family=='US_UNEMPLOYMENT_ANY_MONTH_2026' and 'Employment' in components:
                role, rationale = 'direct_component_with_terminal_risk', 'A U3 month updates the annual threshold; crossing it terminates the contract.'
            elif family=='US_CPI_ANY_MONTH_2026' and ('PPI' in components or 'PCE' in components):
                role, rationale = 'context_hypothesis_only', 'Producer or PCE prices may inform later CPI; these are different indices and no exact-predicate claim is made.'
            else:
                role, rationale = 'no_prespecified_content_link', 'Retain in exposure/timing panel; no semantic value assumed.'
            links.append({'episode_id': event['episode_id'], 'market_id': r['market_id'], 'role': role,
                          'rationale': rationale, 'review_provenance': 'single assistant metadata assessment',
                          'actual_release_evidence_review': 'pending', 'direction': None, 'novelty': 'unknown'})
    (RELEASE/'evidence_link_plan.jsonl').write_text(''.join(json.dumps(x, sort_keys=True)+'\n' for x in links))
    write(RELEASE/'observation_dossier_template.json', {
        'status': 'template_only; no observation yet', 'episode_id': None, 'market_id': None,
        'release_body_sha256': None, 'release_durable_available_at': None, 'evidence_ready_at': None,
        'first_grid_anchor': None, 'input_receipt_hashes': [], 'decision_price': None, 'forward_price': None,
        'gate_results': {k: 'pending' for k in ['source_coverage', 'contract_mapping_rules', 'evidence_relevance',
            'novelty', 'decision_trade_freshness', 'activity_screen', 'asof_240m_history',
            'prespecified_forward_availability', 'actual_terminal_status', 'feature_semantics_compatibility']},
        'predictive_admitted': False, 'model_scored': False})
    live = BASE/'live'
    live.mkdir(parents=True, exist_ok=True)
    plist = {'Label': LABEL, 'ProgramArguments': ['/usr/bin/caffeinate', '-i', '-s', str(REPO_ROOT/'.venv/bin/python'),
             '-m', 'eventx.tasks.collect_v7_direct_pilot_20261022'], 'WorkingDirectory': str(REPO_ROOT),
             'RunAtLoad': True, 'KeepAlive': {'SuccessfulExit': False}, 'ThrottleInterval': 60,
             'EnvironmentVariables': {'PYTHONUNBUFFERED': '1'},
             'StandardOutPath': str(live/'stdout.log'), 'StandardErrorPath': str(live/'stderr.log')}
    (RELEASE/(LABEL+'.plist')).write_bytes(plistlib.dumps(plist))
    paths = [p for p in RELEASE.iterdir() if p.is_file()]
    paths += [DISCOVERY/'manifest.json', PROTECTED]
    paths += [REPO_ROOT/'eventx/tasks'/name for name in [
        'discover_v7_direct_pilot_20261022.py', 'prepare_v7_direct_pilot_20261022.py',
        'collect_v7_direct_pilot_20261022.py', 'audit_v7_direct_pilot_20261022.py',
        'launch_v7_direct_pilot_20261022.py', 'test_v7_direct_pilot_20261022.py']]
    write(RELEASE/'implementation_manifest.json', {'locked_files': {str(p.relative_to(REPO_ROOT)): sha(p) for p in paths}})
    print(json.dumps({'sample': len(sample), 'prospective_candidates': len(candidates), 'excluded_metadata': len(excluded),
                      'families': dict(Counter(r['family'] for r in candidates)), 'episodes_reserved': len(episodes),
                      'directory': str(RELEASE.relative_to(REPO_ROOT))}, indent=2))

if __name__=='__main__':
    main()
