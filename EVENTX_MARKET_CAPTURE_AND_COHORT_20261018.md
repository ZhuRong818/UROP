# EventX: market cohort and capture progress

Operational snapshot: **2026-10-18T10:12:47.834706+00:00**. This continues the original-release feasibility pilot with the existing market model fixed.

## Completed

- Retrieved178 Polymarket metadata records without prices/results. Selected37 contracts from explicit US measurement rules;141 outside scope excluded. Full rules, canonical YES asset IDs and metadata timestamps retained.
- Locked the cohort/specification/implementation before service launch. All470 V4 market IDs are excluded; Fed decision contracts quarantined. Metadata comparison found no shared resolution predicate in the three admitted US measurement families. Shared economic shocks remain possible; statistical independence is not established.
- Started local service `com.eventx.market-capture.20261018`, registered18October10:10:17UTC. It polls exact-cohort trades and YES-asset quote observations, with a120s requested cycle, six-hour initial warmup and30-minute overlapping retrieval windows. Slow endpoints may extend cycles.
- Saved raw response hashes, request/receipt clocks, execution/source clocks and append-only journal. First local durable receipt is the availability clock. Historical timestamps do not establish historical availability.
- Preserved raw `condition_120k`; SHA256 `d5d5a8c12fd999674f687c712e14f3a4406e7ab5ec34774baf1828f644f73a3c`. No model load, training, calibration, scoring or target labels.

| Contract family | Contracts | Scheduled resolving release (UTC) |
|---|---:|---|
| US Q3 GDP advance estimate |7|29October12:30|
| US October unemployment (U-3) |9|6November13:30|
| US October CPI, annual/monthly |21|10November13:30|

These are **three resolving release dates**, not37 independent information events. Warehouse active-state snapshots are not proof of current venue tradability. Schedules can change.

## What the actual collection shows

At this snapshot: **40 completed network window summaries**; latest per-market trade HTTP statuses `{'200': 37}`; quote statuses `{'200': 37}`.

Latest observed windows contain **59 returned trades / 26 canonical-YES trades**; **0 markets** have a nonempty quote response. **0 windows** are currently incomplete/unknown. Overlapping windows must not be added together as independent observations.

Separate latest-observation probes, with no lower timestamp bound, found:

| Sampled contract family | Latest trade returned by source (UTC) |
|---|---|
| US_CPI_2026_10 | 2026-10-15T08:52:56Z |
| US_GDP_2026_Q3_ADVANCE | 2026-10-16T12:25:04Z |
| US_EMPLOYMENT_2026_10 | 2026-10-11T22:55:54Z |

All three sampled YES-quote probes returned empty lists. These are observations about the queried endpoints, not proof of inactivity or a complete source. Thin trading and source recording delays remain unresolved alternatives. Initial quote requests using limit1000 failed422; corrected to the documented limit1 for latest-snapshot capture. Any500 response remains recorded, including its request ID.

The initial sandbox-only collector cycle failed74 requests with DNS ConnectError and ended08:44:06UTC. It is preserved in the journal. The checkpoint's initial started_at08:42:53 describes that attempt; the first real service request is **2026-10-18T10:10:17.786646+00:00**. Do not count the failed cycle as source coverage.

Narrow Kalshi CPI/unemployment/GDP ticker queries succeeded but returned zero metadata records; the earlier broad query failed400. This does not establish that Kalshi has no relevant contracts. No Kalshi market capture is claimed.

## Target compatibility: the main scientific constraint

The unchanged target predicts a large absolute YES log-odds movement over30minutes, with a threshold based on trailing240-minute volatility. Each selected contract resolves on its own data release; a later metadata end_date is not evidence of a usable post-release30-minute target.

- At29October GDP/PCE:30 later-resolving contracts pass the calendar-only screen; seven GDP contracts excluded. GDP and PCE are simultaneous, not two independent shocks.
- At6November employment:21 CPI contracts pass that screen;16 already/then resolving contracts excluded.
- At10November CPI:none of this initial cohort remains available under the expected-terminal screen.

These are **calendar possibilities, not eligible forecast observations**. Cross-release material relevance, novelty, actual terminal clocks, freshness and sufficient activity still require verification. No predictive rows are admitted. Original-release collection continues beyond these dates, but this first market cohort does not cover every original-source target.

## Next work

1. Establish whether empty trade/quote responses reflect genuine sparse activity or feed gaps. An unsent provider diagnostic is linked below; it requests coverage/latency facts rather than assuming completeness.
2. Build a separately versioned metadata-defined cohort with contracts remaining open after future releases, across more dates. Preserve the current37-contract pilot; do not select replacements using forecast outcomes.
3. Verify actual source arrivals, exact evidence/context and trade/quote freshness. Count distinct episode dates; preserve simultaneous-release groups.
4. Before predictive confirmation, freeze the new cohort, source clock, M/E/T/R/S comparisons, terminal exclusions, inference/power and unseen evaluation window. Continue to keep the market model fixed.

## Artifacts and service operation

- Cohort/rules/specification/lock: [eventx/release/v7/market_capture_20261018](eventx/release/v7/market_capture_20261018/).
- Immutable health snapshot: [data/v7/market_cohort_capture_20261018/health/20261018T101247Z/report.json](data/v7/market_cohort_capture_20261018/health/20261018T101247Z/report.json). 233 journal records, 7 unique payload hashes and10 locked implementation files verified. V4 exact-ID intersection0; model hash matches.
- Event/market terminal diagnosis: [data/v7/market_cohort_capture_20261018/target_scope/report.json](data/v7/market_cohort_capture_20261018/target_scope/report.json).
- Provider request draft: [EVENTX_MARKET_SOURCE_DIAGNOSTIC_REQUEST_20261018.md](EVENTX_MARKET_SOURCE_DIAGNOSTIC_REQUEST_20261018.md).
- Live observations: `data/v7/market_cohort_capture_20261018/live`. Runs through12November00:00UTC; local awake power/network required. Create `live/STOP` to stop cleanly. LaunchAgent restarts after failures/at login; registration does not guarantee feed coverage.
- Original-release collector remains separate and active: snapshot heartbeat `2026-10-18T10:12:44.596121+00:00`, PID600, 79 document versions; its source-only status still reports no market reads.

No protected V4 prices/outcomes were opened; no holdout consumed; no model performance improvement or incremental news gain is claimed. Artifact checks and actual capture operations were performed; no software tests were added/run.
