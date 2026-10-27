# Direct-source rehearsal and prospective study handoff

This is a separate V7 feasibility branch. Existing original-release and Lumid collectors retain their code, cohorts, services and journals. The selected market model remains fixed. No forecast evaluation is enabled by this rehearsal.

## Frozen package

`eventx/release/v7/direct_source_pilot_20261022/implementation_manifest.json` locks the sample, capture specification, scripts and operational configuration. The metadata inventory returned 177 macro records, of which 14 match the new exact longer-lived US predicates: six annual GDP, five any-month annual CPI thresholds, three any-month annual U3 thresholds. The remaining 163 records have explicit exclusion reasons. No market was selected from subsequent prices or outcomes.

The source rehearsal includes those 14 candidates, three earlier macro diagnostic samples and five new Bitcoin control candidates: 22 markets in total. Controls are outside the research population. All 470 protected V4 IDs are excluded.

The inventory is bounded by its metadata query and its source coverage; it is not the entire venue universe. Metadata age, current mapping, rules and accepting-orders flags must be checked against the captured venue response. The threshold markets may resolve early; a distant end date does not imply a valid forward target.

## Operation

The separately registered service is `com.eventx.direct-source-pilot.20261022`. Its data go to `data/v7/direct_source_pilot_20261022/live/`. The run contract fixes a 24-hour deadline at first live launch, subject to the frozen outer deadline. Restarts retain that deadline and are recorded as gaps. The process stops at the deadline and attempts a final source audit automatically.

Capture includes venue YES/NO books and trade windows every nominal 60 seconds, venue metadata and matched six-hour Lumid comparisons initially/every fifth cycle, plus concurrent scoped venue WS and Lumid SSE streams. Actual cycle duration and receipt timing determine coverage. Rate backoffs, caps, failures and reconnects remain in the append-only journal.

`status.json` is a live checkpoint, not a certificate of continuous capture. `objects/` retains raw successful scoped responses by SHA256. `journal.jsonl` has a linked hash chain and source/receipt/durable-availability clocks. A STOP file in this new service's live directory requests a clean stop. Do not put STOP files into either old collector's directory as part of this task.

Manual source audit, when needed:

```sh
.venv/bin/python -m eventx.tasks.audit_v7_direct_pilot_20261022
```

Each audit creates a new dated directory under `data/v7/direct_source_pilot_20261022/audits/`, preserving journal/status snapshots, paired source comparisons, per-market receipt gaps and an artifact manifest. Final automatic audit does not send a message or establish research eligibility. The host still needs power, network and availability; caffeinate cannot certify uninterrupted operation.

## Six reserved feasibility episodes

|Episode|Scheduled UTC|Components|
|---|---|---|
|1|29 October 2026, 12:30|Q3 advance GDP and September PCE|
|2|6 November 2026, 13:30|October employment|
|3|10 November 2026, 13:30|October CPI and simultaneous real earnings|
|4|13 November 2026, 13:30|October PPI|
|5|25 November 2026, 13:30|Q3 second GDP/corporate profits and October PCE|
|6|4 December 2026, 13:30|November employment|

Schedules checked on 22 October against the official [BEA calendar](https://www.bea.gov/news/schedule), [BLS November calendar](https://www.bls.gov/schedule/2026/11_sched.htm), and [BLS December calendar](https://www.bls.gov/schedule/2026/12_sched.htm). These are planned clocks, not observed first publication. Preserve rescheduling evidence. Simultaneous components count as one episode, and six separate dates do not establish statistical independence or power. Administrative end: 5 December 2026, 00:00 UTC.

This reservation does not automatically activate event-period market collection. Readiness needs review after the source rehearsal. The first episode needs at least six hours of actual prospective market capture before 29 October 12:30 UTC. The bounded 24-hour rehearsal alone does not provide that future history. Once ready, create a separately frozen event-collection version covering the reserved dates; do not silently extend the rehearsal or old collectors.

`evidence_link_plan.jsonl` retains all 84 candidate-episode pairings. Direct components, contextual hypotheses and pairs with no prespecified content link remain distinguishable. It is a single-assistant metadata assessment, not human gold or a completed release-evidence review. CPI and U3 threshold crossings invalidate post-release forward targets. PPI/PCE are different price indices from CPI and are only contextual hypotheses for those contracts.

## Next admission decision

Use `observation_dossier_template.json` to record the first actual event. Require raw release evidence, extractor completion before the fixed first decision anchor, current rules/mapping, verified source availability, the inherited fresh-trade/activity screen, valid as-of 240-minute history, a separately frozen forward-availability policy and actual tradability through the 30-minute endpoint. Reconstructing history later does not backdate availability.

The first reserved release has not occurred at preparation time. No complete event observation can be claimed now. At the end of the rehearsal, inspect source discrepancies, per-market gaps, actual activity and feature compatibility, then freeze the forward latency policy and the event-collection implementation. Failed or quiet reserved episodes remain in the coverage denominator; do not replace them based on outcomes.

Later model fitting remains conditional on sufficient usable development episodes. Confirmation needs a separate future window, frozen models, validated dependence-aware inference and a consumption rule. Protected V4 and previously consumed holdouts remain outside this pilot.

## Interface reference correction

The frozen specification contains an inaccessible documentation alias ending in `get-markets`. The verified current documentation is [List markets](https://docs.polymarket.com/api-reference/markets/list-markets); the implemented Gamma endpoint is the documented `/markets` with an exact `condition_ids` filter. This documentation correction does not change the frozen request or implementation.
