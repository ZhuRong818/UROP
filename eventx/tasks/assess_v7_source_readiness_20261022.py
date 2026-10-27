"""Assess a frozen rehearsal audit; stage next-version work without activation."""
import argparse
from collections import Counter, defaultdict
from datetime import datetime, timedelta
import json
from pathlib import Path
import uuid
from eventx.settings import REPO_ROOT
from eventx.tasks.discover_v7_direct_pilot_20261022 import BASE, RELEASE, now, sha, write, verify_originals

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument('--audit',required=True)
    args=ap.parse_args()
    source=Path(args.audit).resolve()
    if source.parent != (BASE/'audits').resolve():raise ValueError('Only this pilot audit root')
    m=json.loads((source/'manifest.json').read_text())
    for rel,h in m['files'].items():
        if sha(REPO_ROOT/rel)!=h:raise RuntimeError('Audit manifest mismatch')
    for rel,h in json.loads((RELEASE/'implementation_manifest.json').read_text())['locked_files'].items():
        if sha(REPO_ROOT/rel)!=h:raise RuntimeError('Frozen implementation mismatch')
    verify_originals()
    out=BASE/'readiness'/(now().strftime('%Y%m%dT%H%M%SZ')+'_'+uuid.uuid4().hex[:6])
    out.mkdir(parents=True)
    audit=json.loads((source/'report.json').read_text())
    records=[json.loads(l) for l in (source/'journal.jsonl').read_text().splitlines()]
    comparisons=[json.loads(l) for l in (source/'market_comparison.jsonl').read_text().splitlines()]
    gaps=json.loads((source/'trade_receipt_gaps.json').read_text())
    rates=[{k:r.get(k) for k in ['source','endpoint_kind','path','requested_at','response_received_at','finished_at','backoff_seconds']}
           for r in records if r.get('http_status')==429]
    deferred=Counter((r['source'],r['endpoint_kind']) for r in records if r.get('status')=='deferred_backoff')
    per_market=[]
    for c in [json.loads(l) for l in (RELEASE/'prospective_candidates.jsonl').read_text().splitlines()]:
        rows=[r for r in comparisons if r['market_id']==c['market_id']]
        valid=[r for r in rows if r['status']=='comparable_single_page_window']
        gap=next(r for r in gaps if r['market_id']==c['market_id'])
        per_market.append({'market_id':c['market_id'],'question':c['question'],'family':c['family'],
            'attempted_comparison_windows':len(rows),'comparable_windows':len(valid),
            'observed_activity_pass_windows':sum(r.get('observed_activity_screen',False) for r in valid),
            'mapping_and_rules_matched_at_least_once':any(r.get('current_mapping_matches') and r.get('current_rules_equal_metadata') for r in rows),
            'max_trade_receipt_gap_seconds':gap['max_between_receipts_seconds'],
            'source_completeness_certified':False,'predictive_admitted':False})
    elapsed=audit['elapsed_wall_seconds']
    report={'created_at':now().isoformat(),'audit_at':audit['created_at'],'audit_source':str(source.relative_to(REPO_ROOT)),
        'rehearsal_elapsed_minutes':elapsed/60,'rehearsal_stop_at':audit['scheduled_stop_at'],
        'readiness_decision':'not_ready_for_event_activation',
        'gates':{
            '24h_observation_completed':elapsed>=86400 and audit['window_deadline_reached'],
            'fixed_model_and_original_locks':True,
            'scope_rejection_absent_in_snapshot':not any('scope_rejected' in r.get('kind','') or 'scope_rejected' in r.get('status','') for r in records),
            'all_candidate_rules_and_mapping_observed_matching':all(r['mapping_and_rules_matched_at_least_once'] for r in per_market),
            'elapsed_capture_at_least_240m_necessary_not_sufficient':elapsed>=14400,
            'source_coverage_and_feature_semantics_review_complete':False,
            'forward_receipt_policy_frozen':False,'first_release_evidence_captured_and_reviewed':False},
        'rate_limits':rates,'deferred_by_endpoint':[{'source':s,'endpoint':k,'count':v} for (s,k),v in sorted(deferred.items())],
        'largest_trade_receipt_gap_seconds':max((r['max_between_receipts_seconds'] or 0 for r in gaps),default=0),
        'macro_candidate_count':len(per_market),'macro_comparable_windows':sum(r['comparable_windows'] for r in per_market),
        'macro_activity_pass_windows':sum(r['observed_activity_pass_windows'] for r in per_market),
        'macro_markets_ever_passing_activity_screen':sum(r['observed_activity_pass_windows']>0 for r in per_market),
        'effective_sample_size':None,'predictive_admissions':0,
        'caveats':['Overlapping six-hour comparisons are repeated diagnostics, not independent events.',
                   'Elapsed240m alone never establishes a complete as-of history.',
                   'API429 cause/quota scope is not identified by these receipts.',
                   'Future admission still requires complete evidence, history, freshness, forward and terminal gates.'],
        'next':'Finish existing rehearsal; review full audit, integrate and freeze the staged scheduler in a new collector, then validate before event activation.',
        'production_changed':False,'staged_scheduler_deployed':False,'model_fit_or_score':False,'target_labels_computed':False}
    write(out/'report.json',report)
    (out/'market_readiness.jsonl').write_text(''.join(json.dumps(r,sort_keys=True)+'\n' for r in per_market))
    reservation=json.loads((RELEASE/'episode_reservation.json').read_text())
    windows=[]
    for e in reservation['episodes']:
        t=datetime.fromisoformat(e['scheduled_at'])
        windows.append({**e,'planned_capture_start':(t-timedelta(hours=6)).isoformat(),
                        'planned_capture_end':(t+timedelta(hours=3)).isoformat(),
                        'activation':'disabled_pending_source_readiness_and_new_collector_freeze',
                        'schedule_delay_rule':'Retain original episode and record reschedule/late evidence; no outcome-based replacements.',
                        'window_limitation':'A bounded operational window, not a maximum news-lag admission rule; delayed releases may require a documented schedule version.'})
    write(out/'event_capture_staging.json',{'status':'prepared_not_activated','windows':windows,
        'candidate_manifest':str((RELEASE/'prospective_candidates.jsonl').relative_to(REPO_ROOT)),
        'candidate_manifest_sha256':sha(RELEASE/'prospective_candidates.jsonl'),
        'scheduler_component':'eventx/v7/source_request_scheduler_v02.py',
        'proposed_interval_seconds':{'venue_trades':2.0,'venue_books':0.5,'venue_metadata':1.0,'lumid_rest':2.0},
        'rate_policy':'Fixed endpoint buckets; one in-flight per bucket; honor Retry-After numeric/date. Propagate genuinely server-wide restrictions. No alternate route for blocked trade requests.',
        'deployment_requirement':'Needs integration into a new collector, frozen implementation and network rehearsal; component tests do not demonstrate fewer429s or source completeness.',
        'provider_quota_diagnosis':'Unknown. Published caps do not explain observed429s by themselves.',
        'documentation':'https://docs.polymarket.com/api-reference/rate-limits'})
    text=f'''# EventX: interim readiness assessment

Audit cutoff: **{audit['created_at']}**. The rehearsal has run **{elapsed/60:.2f}minutes**, not24hours. Its fixed end remains23October2026,13:58Singapore. This report does not change its collector or deadline.

## Measured findings

- Verified{audit['verified_payloads']:,} raw payloads and the frozen implementation/source manifests.
- REST responses:2,821HTTP200,70HTTP404,twoHTTP429;209requests deferred during backoff at this snapshot.
- Both429s came from the venue trade endpoint. A shared venue backoff also deferred125book requests and22metadata requests, in addition to62trade requests.
- Largest between-receipt trade gap: **{report['largest_trade_receipt_gap_seconds']:.6f}seconds**. This is not measured continuous exchange completeness.
- All14 candidate mappings/rules matched at least once; **{report['macro_activity_pass_windows']}/{report['macro_comparable_windows']} comparable candidate-window checks passed the observed activity screen**. These overlapping windows are diagnostics, not independent forecast rows or events.
- Venue stream:54book,16,917price_change andsixlast_trade_price events; no recorded stream disconnects in this interval. Provider SSE:oneopen/77heartbeats, no market-data event. Stream connectivity does not establish complete trade history.

## Work completed next

Prepared a separate endpoint scheduler component with one in-flight request per bucket, isolated endpoint backoffs, optional global backoff propagation, and numeric/date Retry-After support. Six focused tests passed, including concurrency, cancellation and backoff isolation. **This component is staged, not integrated or deployed, and no network improvement is claimed.**

Prepared six event-capture windows from the frozen episode reservation: each starts six hours before the scheduled release and ends three hours afterward. These are operational planning windows, not a new semantic or news-lag eligibility rule. All activation flags remain disabled pending completed source review and a newly frozen collector. All14 candidates remain in the manifest.

## Decision

Event-period collection is not ready for activation. The required24-hour source rehearsal has not finished; even240minutes of prospective capture have not elapsed. Source/feature compatibility, forward receipt policy and actual release evidence remain pending. No forecasts, labels or model changes were made. Current source sparsity is still a scientific feasibility issue even if request scheduling improves.

Next, inspect the final rehearsal audit, integrate/test the staged scheduler in a separately frozen collector, and validate acquisition before activating the event windows. Preserve missing/quiet episodes in the denominator. No first complete event observation or news forecasting gain is claimed.

Official [rate-limit documentation](https://docs.polymarket.com/api-reference/rate-limits) describes endpoint limits enforced by IP. The observed429s do not identify which underlying quota or shared traffic caused them; slower pacing is a mitigation to test, not a demonstrated cure.

Evidence: `report.json`, `market_readiness.jsonl`, `event_capture_staging.json` in this directory. Source audit: `{source.relative_to(REPO_ROOT)}`.
'''
    (out/'REPORT.md').write_text(text)
    paths=[p for p in out.iterdir() if p.is_file()]+[source/'manifest.json',RELEASE/'implementation_manifest.json',
        REPO_ROOT/'eventx/v7/source_request_scheduler_v02.py',REPO_ROOT/'eventx/tasks/test_v7_source_scheduler_v02.py',
        REPO_ROOT/'eventx/tasks/assess_v7_source_readiness_20261022.py']
    write(out/'manifest.json',{'files':{str(p.relative_to(REPO_ROOT)):sha(p) for p in paths}})
    print(json.dumps({'directory':str(out.relative_to(REPO_ROOT)),'report':report},indent=2))

if __name__=='__main__':main()
