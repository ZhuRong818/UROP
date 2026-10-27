"""Publish completed source/compatibility diagnostics and prospective gate report."""
from datetime import datetime,timezone
from pathlib import Path
import json
from eventx.tasks.diagnose_v7_execution_accounting_20261022 import ROOT,lines,sha,write,verify_manifest
OUT=ROOT/'data/v7/eligibility_report_20261023'
INPUT=ROOT/'data/v7/input_eligibility_20261023'
MISSING=ROOT/'data/v7/missing_receipt_analysis_20261023'

def main():
    OUT.mkdir(exist_ok=False)
    manifests=[INPUT/'manifest.json',MISSING/'manifest.json',ROOT/'data/v7/missing_chain_20261023/e8cab0bb379b4169aa42d1e41a22c7a1/manifest.json']
    for p in manifests:verify_manifest(p)
    r=json.loads((INPUT/'report.json').read_text());m=json.loads((MISSING/'report.json').read_text())
    candidates=lines(INPUT/'candidate_eligibility.jsonl');comp=lines(INPUT/'accounting_compatibility.jsonl')
    state_path=ROOT/'data/v7/source_workflow_20261022/status.json'
    workflow=json.loads(state_path.read_text());write(OUT/'workflow_status_snapshot.json',workflow)
    live=json.loads((ROOT/'data/v7/direct_source_pilot_20261022/live/status.json').read_text())
    write(OUT/'original_collector_status_snapshot.json',live)
    grid=datetime.fromisoformat(r['asof_grid']).astimezone(__import__('zoneinfo').ZoneInfo('Asia/Singapore')).isoformat()
    table=[]
    for c in candidates:
        f=c['observed_features'];age='No retained YES trade' if f is None or f['price_age_minutes'] is None else f"{f['price_age_minutes']:.2f} min"
        table.append('|'+c['question'].replace('|','/')+'|'+str(f['count60'] if f else 'unknown')+'|'+str(f['count240'] if f else 'unknown')+'|'+str(round(f['quantity240'],6) if f else 'unknown')+'|'+age+'|')
    control=next(c for c in comp if '$80,000' in c['question'])
    v=control['variants']
    controls=[]
    for name,label in [('provider_original','Original provider'),('provider_late','Provider after delayed re-fetch'),('direct_inclusive','Direct maker-inclusive'),('direct_taker_only','Direct taker-only')]:
        f=v[name];price='Ambiguous at last second' if f['latest_price'] is None else str(f['latest_price'])
        controls.append(f"|{label}|{f['count240']}|{f['quantity240']:.6f}|{f['price_age_minutes']:.2f}|{price}|")
    md=f'''# EventX: input compatibility and prospective eligibility

23 October 2026. Source diagnostics completed; prospective forecasting remains gated.

## Decision

**The current14-contract candidate cohort has no demonstrated eligible prediction observation.** The immediate bottlenecks are sparse YES trading, incomplete source coverage, and an unconfirmed counting convention. Keep the selected market model fixed. Preserve all14metadata-selected candidates and all six reserved episodes; do not replace quiet episodes after seeing price behavior.

This report completes the requested missing-trade investigation, accounting-sensitivity analysis and eligibility report. The24hcollector sequence continues in the background; its final audits are not yet available.

## 1. Remaining47missing trades are real sampled settlement events

A bounded read-only Polygon lookup returned47successful receipts containing179allowlisted order-fill logs. All47direct taker-side records have a unique match on transaction, token, side, quantity, price and participant to an exchange-facing taker-order fill. All were still absent from the provider's previous delayed re-fetch.

- All47use the same CTF exchange address already present in captured records. A whole-exchange exclusion does not explain these omissions.
-44are BUY and3SELL.29participants also appear in captured fill logs.
- Only1transaction sender overlaps the earlier captured29transactions;both groups have many distinct senders. This descriptive difference does not establish sender-based filtering.
-45of47omissions remain concentrated in the $80,000 BTC control. These controls are not research-cohort admissions.
- Receipt evidence is from one public RPC provider; no independent finality or full-exchange completeness claim is made.

The initial sandbox connection failure is preserved separately. The network run completed48RPC requests with no address-code calls. The previous address-code403is not silently reclassified as success.

## 2. Accounting choices materially change model inputs

We compared22markets at fixed five-minute grids within the earlier common source windows. Comparisons use canonical YES tokens and historical open-left trailing windows `(t−window,t]`. The field historically named notional is **token quantity**, not cash value. The selected model consumes log counts,log quantities and count/size-rate ratios; no predictor was loaded.

Mapping the original provider rows to their verified order-fill identities preserves their sampled count and quantity features. Filtering those events to taker-order roles changes the observation population. Replacing provider rows with direct taker-only data also combines a role change with a coverage change.

Across the five controls:

- Direct maker-inclusive → taker-only changes four-hour count and quantity in4markets,60-minute count/quantity in2,and the size-rate ratio in2.
- Original provider → direct taker-only changes four-hour count/quantity and latest-trade time in4markets.
- Delayed provider re-fetch changes four-hour count/quantity and latest-trade time in3of4re-fetched controls.

### Example: $80,000 BTC control

This comparison uses the older **22October11:10UTC** diagnostic grid and is retrospective. It is separate from the current candidate eligibility snapshot below.

|Representation|YES records240m|YES token quantity240m|Last-trade age,min|Last YES price|
|---|---:|---:|---:|---|
{chr(10).join(controls)}

The provider's stale price and much smaller quantity are material input differences. The direct maker-inclusive last second contains different prices,so the diagnostic leaves its last price unresolved. We did not select a preferred source because it produces a better forecast. No LL,Brier,AP,labels or prediction comparisons were generated.

The14macro candidates show no accounting-driven activity promotion in these older windows; their sparsity dominates. Neither this observation nor the unchanged mapped-provider counts proves global feature equivalence. Full22-feature compatibility still requires complete histories and documented source selection.

## 3. Current prospective eligibility

Frozen audit cutoff:{r['audit_snapshot_at']}. Fixed as-of grid:**{grid}**,equivalent to02:35UTC. Only receipts durably available by that grid were used in current feature diagnostics. Later receipts and the retrospective chain joins were excluded from that as-of input selection.

|Requirement|Observed status|
|---|---|
|Candidate mapping and rules match captured metadata|14/14|
|Fresh YES trade,age≤5minutes|0/14|
|At least3YES records60m|0/14|
|At least3YES records240m|0/14|
|At least100YES tokens240m|0/14|
|Mathematically constructible240-minute price path from retained records|1/14;its volatility is zero|
|Source-complete,compatible240-minute history|Not established|
|Valid30-minute endpoint under frozen receipt policy|Pending policy;not computed|
|Tradable/unresolved through target|Not established by current metadata alone|
|Captured and reviewed reserved release evidence|0episodes;reserved releases are future|
|Predictive admissions|0|

In total,**0/{r['candidate_comparable_windows']:,}comparable candidate-window checks** passed the quantity-based activity screen. These repeated overlapping windows are diagnostics,not independent events. The latest snapshot shows one CPI candidate with2YES records/89.25tokens in240minutes and a154.37-minute-old trade;the rest also fail the combined activity screen.

### Contract-level observed activity

|Candidate|YES count60m|YES count240m|YES quantity240m|Latest retained YES age|
|---|---:|---:|---:|---|
{chr(10).join(table)}

“No retained YES trade” means none in the selected bounded receipt window. It does not assert the contract has never traded. A numerical price path from sparse records is not proof that no missing executions occurred.

## 4. Source coverage and automatic continuation

The interim audit verified**{r['source_audit_journal_records']:,}journal records/{r['source_audit_payloads']:,}payloads** and all20original production locks. Its maximum candidate trade-receipt gap is**{r['largest_candidate_receipt_gap_seconds']:.6f}seconds**,about{r['largest_candidate_receipt_gap_seconds']/60:.2f}minutes. Backfill cannot restore timely capture across this gap. Cause of this particular maximum gap is not established by this report.

All four local processes were verified present during this task. Workflow snapshot:{workflow['at']},phase`{workflow['phase']}`. The original collector's later live checkpoint is{live['at']}with{live['journal_records']:,}records;that newer count is not part of the frozen audit above.

The original run is scheduled to stop **23October13:58:25Singapore**. The controller then checks its completed audit and runs the separately frozen revised collector for24hours. It stops after that source review,before event activation/scoring. Local power,network and an awake Mac remain necessary;no uninterrupted-operation guarantee is made.

## 5. What follows

1. Let the automatic original/revised source sequence finish and inspect its completed audits. The current report is interim.
2. Obtain provider reconciliation for the exact47confirmed missing events and a general mixed-schema/counting specification. The narrowed evidence-backed request is prepared,unsent.
3. Reassess the same metadata-defined cohort before the first reserved29October episode;retain zero-yield episodes. Today's quiet markets do not establish future release-time activity.
4. Freeze fresh endpoint/acquisition-latency and terminal/evidence rules before constructing prospective labels. Do not use delayed source retrieval as timely evidence.
5. If prospective source-complete episodes still lack trades,document a trade-target feasibility limit and propose a separately specified cohort or quote-based study. Such a branch needs its own target,baseline and review;it is not activated here.

## Evidence

- `data/v7/input_eligibility_20261023/`:per-market accounting variants,2,696activity checks,14candidate gate records,receipt hashes and frozen report.
- `data/v7/missing_receipt_analysis_20261023/`:47event mappings and source-role comparisons.
- `data/v7/direct_source_pilot_20261022/audits/20261023T023646Z_d2af4c/`:new interim source audit.
- `data/v7/eligibility_report_20261023/`:this report,live-status snapshots and narrowed provider request.

Original collectors,selected model and protected studies remain unchanged. No tests were added/run,no model fit/scoring and no forward targets/labels were computed.
'''
    public=ROOT/'EVENTX_INPUT_COMPATIBILITY_AND_ELIGIBILITY_20261023.md';public.write_text(md);(OUT/'REPORT.md').write_text(md)
    request='''# Provider reconciliation request — prepared,not sent

We have narrowed the EventX V7 source discrepancy to47specific trade records absent from a repeat fetch of the same four historical control windows about14.68hours after the endpoints. Each now matches a successful Polygon transaction and an allowlisted CTF exchange taker-order fill,including exact token,side,quantity,price and participant.45records belong to the $80,000 BTC control.

Please reconcile the47identities in data/v7/missing_receipt_analysis_20261023/missing_event_mapping.jsonl against your upstream source and indexing/selection rules. All47use the same exchange as captured trades;29participants also occur in captured logs. We cannot infer filtering from the small sample. Identify omitted partitions,outages,filters or late-ingestion state using your internal receipts.

For the earlier sampled52provider rows,we verified36transactionHash:orderHash IDs with event-taker semantics and16bare IDs with event-maker semantics. Confirm the documented rule for each shape,canonical counting/deduplication,partial fills,and how repeated same-order fills within one transaction are represented. Do not treat all order-fill legs as independent economic trades.

Please supply first-ingestion/revision timestamps,chain/exchange/order IDs,block hash/number,transaction/log index and removal/reorg state. The four original and late responses show45unchanged records and93late additions;16of63initial missing direct records recovered,47remain. Do not backdate those late records.

Research evidence:EVENTX_INPUT_COMPATIBILITY_AND_ELIGIBILITY_20261023.md;data/v7/input_eligibility_20261023/;data/v7/missing_receipt_analysis_20261023/. No credentials or protected evaluation data should be attached. The current forecasting model remains fixed.
'''
    (OUT/'PROVIDER_RECONCILIATION_DRAFT.md').write_text(request)
    result={'at':datetime.now(timezone.utc).isoformat(),'input_report':str((INPUT/'report.json').relative_to(ROOT)),'missing_report':str((MISSING/'report.json').relative_to(ROOT)),
            'workflow_phase':workflow['phase'],'current_candidate_activity_passes':0,'predictive_admissions':0,'provider_message_sent':False,
            'decision':'No current eligibility or accounting promotion;complete automatic source rehearsals,then source-readiness review.'}
    write(OUT/'report.json',result)
    files=list(OUT.iterdir())+[public,Path(__file__).resolve()]+manifests
    write(OUT/'manifest.json',{'files':{str(p.relative_to(ROOT)):sha(p) for p in files}})
    state=ROOT/'CURRENT_STATE.md';s=state.read_text();mark='### Prior source diagnosis and remaining gates'
    new='''### Input compatibility and eligibility,23October11:30SGT

- Latest:`EVENTX_INPUT_COMPATIBILITY_AND_ELIGIBILITY_20261023.md`;frozen
  `data/v7/input_eligibility_20261023/` and `data/v7/missing_receipt_analysis_20261023/`.
-47/47still-missing records now match successful chain taker-order fills;all same
  exchange as captured records,44BUY/3SELL,29participants previously observed.
  Only1sender overlaps prior29transactions;no sender-filter causality established.
- Old common-grid controls:maker-inclusive→taker-only changes240mcount/quantity
  in4/5markets. Original→late provider changes these in3/4. Verified identity mapping
  alone preserves sampled provider quantities;source/counting substitution does not.
- Fixed as-of23Oct02:35UTC:14/14metadata mappings/rules match;0/14freshYES;
  all failcount60/count240/quantity240. One mathematical240mpath haszerosigma.
  0/2696comparable overlapping candidatewindows pass quantityactivity;0admissions.
- Interim audit02:36UTC:501235journalrecords/414444verifiedpayloads;20locks match;
  largest candidate receiptgap7267.666361s(121.13min),cause not established here.
- Workflow/PIDs600,23793,39643,74338verified23Oct03:30UTC;original525314live records,
  still running until05:58UTC. Then separate24hV03/audit;no forecast activation.
- Narrowed unsent request:`data/v7/eligibility_report_20261023/PROVIDER_RECONCILIATION_DRAFT.md`.
  Complete rehearsals;review source accounting/coverage and endpoint rules before
  future episode eligibility. No model,cohort,protected evaluation or label changes.

'''
    s=s.replace(mark,new+mark).replace('(sampled chain identities resolved; partial delayed recovery)','(compatibility measured; current candidate eligibility zero)');state.write_text(s)
    with (ROOT/'docs/progress/2026-10.md').open('a') as f:
        f.write('\n### Requested next steps completed: compatibility and eligibility diagnostics — '+result['at']+'\n\n')
        f.write('New interim audit20261023T023646Z_d2af4c:501235journalrecords/414444payloads,20productionlocks verified,24hdeadline not reached. Macro maxreceiptgap7267.666361093521seconds. Frozen collector continues. Bounded47missing-transaction probe:initial sandboxConnectError preserved;network48RPCrequests returned47receipts/179scopedfilllogs,all47uniquematches/successful. Sameexchange47/47,priorparticipant29/47,priorsender1/47,BUY44/SELL3;nofiltercausalityclaim.\n\n')
        f.write('Accounting sensitivity:22oldcommon-gridmarkets;provideridentitymappingpreservescount/quantity. Directinclusive→taker-only changes240mcount/quantity4/5controls;original→lateprovider3/4controls. Fixedasof23Oct02:35UTC:14mappings/rules match;0freshYES;all14failcount60/count240/quantity240.13lackseeded240mpath;onecomputablepathhaszerosigma.0/2696overlappingcandidatewindowsactivitypass;0admissions. Forwardlabelsnotcomputed;coverage/endpoint/terminal/evidencegatesremainpending.\n\n')
        f.write('Report EVENTX_INPUT_COMPATIBILITY_AND_ELIGIBILITY_20261023.md;rawpermarketdetails in data/v7/input_eligibility_20261023/;47mappingdetails in data/v7/missing_receipt_analysis_20261023/. Latestproviderrequestdata/v7/eligibility_report_20261023/PROVIDER_RECONCILIATION_DRAFT.md unsent. Allfourprocessesverified03:30UTC;workflowwaitingfororiginalend05:58UTCthen24hV03. No tests,modelscoring,cohortchanges,protectedreads,or externalmessages.\n')
    print(json.dumps({'report':str(public.relative_to(ROOT)),'evidence':str(OUT.relative_to(ROOT)),'workflow':workflow['phase']},indent=2))
if __name__=='__main__':main()
