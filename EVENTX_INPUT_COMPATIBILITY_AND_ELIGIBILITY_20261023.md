# EventX: input compatibility and prospective eligibility

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
|Original provider|9|5759.581300|133.82|0.43|
|Provider after delayed re-fetch|9|5759.581300|133.82|0.43|
|Direct maker-inclusive|74|36569.689294|19.75|Ambiguous at last second|
|Direct taker-only|26|17235.685889|19.75|0.3699823165|

The provider's stale price and much smaller quantity are material input differences. The direct maker-inclusive last second contains different prices,so the diagnostic leaves its last price unresolved. We did not select a preferred source because it produces a better forecast. No LL,Brier,AP,labels or prediction comparisons were generated.

The14macro candidates show no accounting-driven activity promotion in these older windows; their sparsity dominates. Neither this observation nor the unchanged mapped-provider counts proves global feature equivalence. Full22-feature compatibility still requires complete histories and documented source selection.

## 3. Current prospective eligibility

Frozen audit cutoff:2026-10-23T02:36:46.920625+00:00. Fixed as-of grid:**2026-10-23T10:35:00+08:00**,equivalent to02:35UTC. Only receipts durably available by that grid were used in current feature diagnostics. Later receipts and the retrospective chain joins were excluded from that as-of input selection.

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

In total,**0/2,696comparable candidate-window checks** passed the quantity-based activity screen. These repeated overlapping windows are diagnostics,not independent events. The latest snapshot shows one CPI candidate with2YES records/89.25tokens in240minutes and a154.37-minute-old trade;the rest also fail the combined activity screen.

### Contract-level observed activity

|Candidate|YES count60m|YES count240m|YES quantity240m|Latest retained YES age|
|---|---:|---:|---:|---|
|Will inflation reach more than 10% in 2026?|0|0|0|No retained YES trade|
|Will inflation reach more than 8% in 2026?|0|0|0|No retained YES trade|
|Will US unemployment reach at least 6.0% in 2026?|0|0|0|No retained YES trade|
|Will US unemployment reach at least 5.5% in 2026?|0|0|0|No retained YES trade|
|Will US GDP growth in 2026 be between 2.0% and 2.5%?|0|0|0|No retained YES trade|
|Will US GDP growth in 2026 be greater than 2.5%?|0|0|0|No retained YES trade|
|Will US GDP growth in 2026 be less than 0.5%?|0|0|0|No retained YES trade|
|Will US GDP growth in 2026 be between 1.0% and 1.5%?|0|0|0|No retained YES trade|
|Will US GDP growth in 2026 be between 0.5% and 1.0%?|0|0|0|No retained YES trade|
|Will inflation reach more than 5% in 2026?|0|2|89.25|154.37 min|
|Will inflation reach more than 6% in 2026?|0|0|0|No retained YES trade|
|Will US GDP growth in 2026 be between 1.5% and 2.0%?|0|0|0|331.22 min|
|Will inflation reach more than 4.5% in 2026?|0|0|0|No retained YES trade|
|Will US unemployment reach at least 5.0% in 2026?|0|0|0|No retained YES trade|

“No retained YES trade” means none in the selected bounded receipt window. It does not assert the contract has never traded. A numerical price path from sparse records is not proof that no missing executions occurred.

## 4. Source coverage and automatic continuation

The interim audit verified**501,235journal records/414,444payloads** and all20original production locks. Its maximum candidate trade-receipt gap is**7267.666361seconds**,about121.13minutes. Backfill cannot restore timely capture across this gap. Cause of this particular maximum gap is not established by this report.

All four local processes were verified present during this task. Workflow snapshot:2026-10-23T03:32:39.938118+00:00,phase`waiting_for_original_rehearsal`. The original collector's later live checkpoint is2026-10-23T03:33:04.590050+00:00with526,715records;that newer count is not part of the frozen audit above.

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
