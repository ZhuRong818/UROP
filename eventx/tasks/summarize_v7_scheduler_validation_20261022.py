"""Summarize bounded V02 source receipts without forecasting or changing eligibility."""
from collections import Counter, defaultdict
from pathlib import Path
import json
from eventx.tasks.discover_v7_direct_pilot_20261022 import now, sha, write, REPO_ROOT, verify_originals
from eventx.tasks.audit_v7_direct_pilot_20261022 import stamp

BASE=REPO_ROOT/'data/v7/direct_source_pilot_20261022_v02'
RELEASE=REPO_ROOT/'eventx/release/v7/direct_source_pilot_20261022_v02'
RUN=BASE/'smoke/bee696bb6c9743f89e9ac442786c5d2b'
OLD=REPO_ROOT/'data/v7/direct_source_pilot_20261022/audits/20261022T105137Z_f62ac0'

def main():
    for p,h in json.loads((RELEASE/'implementation_manifest.json').read_text())['locked_files'].items():
        if sha(REPO_ROOT/p)!=h: raise RuntimeError('Implementation mismatch: '+p)
    candidates=[]
    for p in (BASE/'audits').iterdir():
        r=json.loads((p/'report.json').read_text())
        if r['run']==str(RUN.relative_to(REPO_ROOT)): candidates.append(p)
    if len(candidates)!=1: raise RuntimeError('Require exactly one completed-run audit')
    audit=candidates[0]
    for p,h in json.loads((audit/'manifest.json').read_text())['files'].items():
        if sha(REPO_ROOT/p)!=h: raise RuntimeError('Audit mismatch: '+p)
    records=[json.loads(l) for l in (audit/'journal.jsonl').read_text().splitlines()]
    if not any(r['kind']=='process_stopped' for r in records): raise RuntimeError('Run not stopped')
    report=json.loads((audit/'report.json').read_text())
    rest=[r for r in records if r['kind']=='rest']
    cfg=json.loads((RELEASE/'spec.json').read_text())
    pacing={}
    for key,interval in cfg['endpoint_intervals_seconds'].items():
        rows=sorted([r for r in rest if r['scheduler_bucket']==key and 'requested_at' in r],key=lambda r:r['requested_at'])
        deltas=[stamp(b['requested_at'])-stamp(a['requested_at']) for a,b in zip(rows,rows[1:])]
        overlap=[(a,b) for a,b in zip(rows,rows[1:]) if stamp(b['requested_at'])<stamp(a.get('response_received_at',a['finished_at']))]
        short_backoff=[(a,b) for a,b in zip(rows,rows[1:]) if a.get('backoff_seconds') and stamp(b['requested_at'])-stamp(a['response_received_at'])<a['backoff_seconds']-.01]
        pacing[key]={'requests_dispatched':len(rows),'configured_interval_seconds':interval,
                     'min_dispatch_interval_seconds':min(deltas,default=None),
                     'pacing_violations_with_10ms_clock_tolerance':sum(d<interval-.01 for d in deltas),
                     'overlapping_network_requests':len(overlap),'backoff_responses':sum('backoff_seconds' in r for r in rows),
                     'observed_backoff_violations':len(short_backoff),
                     'maximum_queue_wait_seconds':max((stamp(r['requested_at'])-stamp(r['queued_at']) for r in rows),default=None)}
    comparisons=[json.loads(l) for l in (audit/'market_comparison.jsonl').read_text().splitlines()]
    macro=[r for r in comparisons if r['role']=='prospective_macro_candidate']
    old_report=json.loads((OLD/'report.json').read_text())
    old_macro=[json.loads(l) for l in (OLD/'market_comparison.jsonl').read_text().splitlines()]
    old_macro=[r for r in old_macro if r['role']=='prospective_macro_candidate']
    old_gaps=json.loads((OLD/'trade_receipt_gaps.json').read_text())
    gaps=json.loads((audit/'trade_receipt_gaps.json').read_text())
    old_records=[json.loads(l) for l in (OLD/'journal.jsonl').read_text().splitlines()]
    gap_events=[]
    by_market=defaultdict(list)
    for row in old_records:
        if row['kind']=='rest' and row.get('source')=='venue' and row.get('endpoint_kind')=='trades' and row.get('status')=='observed':
            by_market[row['market_id']].append(row['available_at'])
    for market,times in by_market.items():
        times.sort()
        for a,b in zip(times,times[1:]):
            duration=stamp(b)-stamp(a)
            if duration>300:
                gap_events.append({'market_id':market,'previous_success_available_at':a,'next_success_available_at':b,'gap_seconds':duration,'cause':'unresolved'})
    result={'created_at':now().isoformat(),'scope':'operational source validation; not model evaluation',
            'run':str(RUN.relative_to(REPO_ROOT)),'audit':str(audit.relative_to(REPO_ROOT)),
            'original_interim_audit':str(OLD.relative_to(REPO_ROOT)),
            'frozen_files_verified':len(json.loads((RELEASE/'implementation_manifest.json').read_text())['locked_files']),
            'production_locks_verified':verify_originals(),
            'identical_fixed_sample':(RELEASE/'sample.jsonl').read_bytes()==(REPO_ROOT/'eventx/release/v7/direct_source_pilot_20261022/sample.jsonl').read_bytes(),
            'pacing':pacing,'source_run_report':report,
            'completed_cycles':[r for r in records if r['kind']=='cycle_finished'],
            'candidate_comparable_windows':sum(r['status']=='comparable_single_page_window' for r in macro),
            'candidate_activity_pass_windows':sum(r.get('observed_activity_screen',False) for r in macro),
            'candidate_markets_with_any_activity_pass':len({r['market_id'] for r in macro if r.get('observed_activity_screen')}),
            'candidate_markets_with_matching_mapping_and_rules':len({r['market_id'] for r in macro if r.get('current_mapping_matches') and r.get('current_rules_equal_metadata')}),
            'max_successful_trade_receipt_gap_seconds':max((r['max_between_receipts_seconds'] or 0 for r in gaps),default=None),
            'original_interim':{'report':old_report,'candidate_comparable_windows':sum(r['status']=='comparable_single_page_window' for r in old_macro),
                'candidate_activity_pass_windows':sum(r.get('observed_activity_screen',False) for r in old_macro),
                'max_successful_trade_receipt_gap_seconds':max(r['max_between_receipts_seconds'] or 0 for r in old_gaps)},
            'original_gaps_over_five_minutes':len(gap_events),'original_markets_with_gaps_over_five_minutes':len({r['market_id'] for r in gap_events}),'event_activation_enabled':False,'predictive_admissions':0,'models_scored':False,
            'limits':['Five minutes cannot establish 240-minute timely capture or 24-hour reliability.',
                      'Concurrent runs and different periods preclude causal before/after claims.',
                      'HTTP429 behavior is unexercised if no 429 observed; prior scheduler component checks are not a live retry test.',
                      'Per-endpoint pacing does not remove the outer cycle barrier: slow trades/provider calls still delay the next full REST cycle.',
                      'Stream updates are not executions; matched print fingerprints are not unique execution counts.',
                      'No valid news event observation or predictive improvement is established.']}
    out=BASE/'validation_v01';out.mkdir(exist_ok=False)
    write(out/'report.json',result)
    write(out/'original_trade_receipt_gap_events.json',sorted(gap_events,key=lambda r:r['gap_seconds'],reverse=True))
    r=report; o=result['original_interim']; mins=o['max_successful_trade_receipt_gap_seconds']/60
    text=f'''# EventX: collector V02 integration and source validation

Report timestamp: {result['created_at']}. **Source study only; no prediction evaluation.**

## Completed

- Created and froze a separate V02 collector and audit; retained the exact 22-market sample (14 prospective macro candidates, three legacy diagnostics, five controls).
- Integrated independent fixed endpoint queues: trades every 2 seconds, books every 0.5 seconds, metadata every 1 second, provider REST every 2 seconds. Each queue stays locked through its response and backoff update.
- Recorded queue, actual dispatch, response and durable availability clocks. Added a bounded shutdown with explicit cancellation records and numeric/HTTP-date Retry-After parsing.
- Finished the five-minute live validation. Verified {r['journal_records']:,} journal records and {r['verified_payloads']:,} payloads. All {result['frozen_files_verified']} frozen files and {result['production_locks_verified']} original production locks matched.
- Preserved the failed sandbox DNS attempt and its audit. Original services and frozen market model were not changed. No test suite was added or rerun; prior component tests remain separate evidence.

## Live validation result

| Measure | Result |
|---|---|
| HTTP responses | {json.dumps(r['rest_http_counts'],sort_keys=True)} |
| Request statuses | {json.dumps(r['rest_status_counts'],sort_keys=True)} |
| Stream disconnect records | {json.dumps(r['stream_disconnects'],sort_keys=True)} |
| Candidate mappings and rules matched | {result['candidate_markets_with_matching_mapping_and_rules']}/14 |
| Comparable macro windows | {result['candidate_comparable_windows']} |
| Candidate activity passes | {result['candidate_activity_pass_windows']} windows; {result['candidate_markets_with_any_activity_pass']}/14 markets |
| Predictive admissions | 0 |

Pacing and in-flight overlap diagnostics are in `report.json`. These examine actual receipts; they do not establish source completeness. Queue cancellation at the deadline is distinct from a failed HTTP response. The full REST cycle can exceed 60 seconds because it waits for all endpoint groups; configured cadence must not be reported as achieved cadence.

## Original 24-hour rehearsal: still incomplete

The frozen interim audit at {old_report['created_at']} verified {old_report['verified_payloads']:,} payloads. It recorded seven HTTP429 responses, 77 HTTP502 responses, 746 deferred requests, 271 other request failures, 15 WebSocket disconnects and 16 SSE disconnects. The largest successful trade receipt gap was **{mins:.2f} minutes**. Causes are unresolved; local/network/provider interruptions must not be assigned from heartbeat alone.

There were {o['candidate_comparable_windows']} comparable macro windows and {o['candidate_activity_pass_windows']} activity passes. These windows overlap and are not independent events. A 240-minute elapsed run does not demonstrate 240 minutes of timely, complete data.

## Interpretation

The implementation is now concrete and the bounded capture has run. A clean five-minute interval, if observed, would not prove the scheduler cured the original interruptions or rate limits. The original collector ran concurrently, and the observation periods differ. No forecast was scored and no metric was adjusted.

The remaining bottlenecks are source continuity, sparse eligible trades, and the absence of a complete prospectively captured release observation. Keep the selected market model frozen and event activation disabled.

## Next execution gates

1. Review the original rehearsal's automatic final audit after **23 October 05:58 UTC / 13:58 Singapore**. Separate DNS/connection failures, HTTP failures, stream gaps and genuine zero-trade responses.
2. Resolve continuity and source-field compatibility, then freeze and run a longer V02 source rehearsal before activating event capture. The five-minute run does not replace the original 24-hour criterion.
3. Prespecify forward-price freshness and receipt latency, verify actual terminal conditions, and assemble one full event dossier: original evidence availability, valid trailing 240-minute history, fresh decision price and valid 30-minute forward price.
4. First reserved release is **29 October 12:30 UTC**; the staged six-hour warmup starts **06:30 UTC**, conditional on readiness. Six reserved episodes remain a feasibility sample, not a powered confirmation.
5. If verified feeds still yield no trade-based eligible observations, record that feasibility result and design a separately frozen quote-based study; do not silently substitute quotes into the current target.

## Evidence

- New source audit: `{audit.relative_to(REPO_ROOT)}`
- Original interim audit: `{OLD.relative_to(REPO_ROOT)}`
- V02 freeze: `{RELEASE.relative_to(REPO_ROOT)}/implementation_manifest.json`
- Machine-readable validation: `{out.relative_to(REPO_ROOT)}/report.json`
'''
    (out/'REPORT.md').write_text(text)
    report_path=REPO_ROOT/'EVENTX_COLLECTOR_V02_VALIDATION_20261022.md';report_path.write_text(text)
    files=[out/'original_trade_receipt_gap_events.json',out/'report.json',out/'REPORT.md',report_path,Path(__file__).resolve(),audit/'manifest.json',OLD/'manifest.json',RELEASE/'implementation_manifest.json']
    write(out/'manifest.json',{'files':{str(p.relative_to(REPO_ROOT)):sha(p) for p in files}})
    print(json.dumps({'report':str(report_path),'result':{k:result[k] for k in ['pacing','candidate_comparable_windows','candidate_activity_pass_windows','max_successful_trade_receipt_gap_seconds']}}))

if __name__=='__main__':main()
