# EventX archive compatibility audit — 25 October 2026

The blocked historical lookup is repaired in a new version. A bounded five-market audit completed. Direct top quotes offer a plausible route to a larger **separate price-only study**; reconstructed depth does not yet support the existing model. No new predictive gain is established.

## Completed work

The prior default Gamma requests returned empty arrays. Eleven diagnostic requests showed that `closed=true` retrieves both historical probe markets with exact identities; native CLOB metadata independently matched both. V03 keeps the default lookup and adds that fallback only on an empty result. All failed attempts and frozen versions remain preserved. Current closure is not evidence of historical tradability.

Five binary markets were selected from sorted IDs using identity/event coverage and metadata before requesting economic columns. All five concern sports; this is a source-format sample, not a representative economic-news cohort. Two April 21 hourly files were sampled, before all protected evaluation windows. V03 downloaded 18,127,803 archive bytes, below its 96 MiB bound. This count excludes metadata HTTP response bodies.

| Audit measure | Result |
|---|---:|
| Retained YES-token events | 3,640 |
| Incremental updates | 3,628 |
| Full snapshots / snapshots passing price, spread and depth checks | 12 / 6 |
| Planned five-minute decision grids | 60 |
| Fresh snapshot endpoint pairs | 0 |
| Direct top-quote fresh current grids | 24 |
| Direct top-quote fresh 30-minute endpoint pairs | 23 |
| Direct top-quote continuous forward windows | 18 |
| Direct top-quote continuous history + forward windows | 10 |
| Fully admitted forecasting observations | 0 |

The 10 continuous windows are from **two markets on one date**, with overlapping horizons. They are potential quote-coverage windows, not independent events or completed forecasting observations. Historical status and broader feed coverage remain unresolved. Direct-quote diagnostics do not apply the existing depth threshold because depth is not established for that method; the two methods therefore have different eligibility definitions.

## Why replaying depth is not ready

The diagnostic compared stored order, reversed order within receive-time ties, and source-time order within receive-time ties. Eight of 60 grid states had different best quotes across the tested orderings. Among seven snapshot boundaries, reconstructed best quotes matched six under each ordering, while full depth matched only three, two and four respectively. There were 282 ambiguous update groups in the original replay diagnostic. Three orderings do not exhaust all possible sequences, and later agreement cannot prove intermediate correctness.

Direct best bid and ask are populated on all 3,628 updates. The separate top-quote audit found 170 receive-time groups with conflicting direct quote pairs. Such groups invalidate the price state until a later unambiguous quote. The audit uses no future event to resolve a tie and requires fresh source and receipt clocks. It finds 23 paired endpoints, but only 10 windows also retain continuous 30-minute history and forward coverage. Snapshot-only and direct-quote coverage are distinct measures, not controlled model improvements.

| Market | Fresh endpoint pairs | Continuous history + forward |
|---|---:|---:|
| Marcus Thuram — Serie A top scorer | 11 | 2 |
| Newcastle — relegation | 12 | 8 |
| Other three selected markets | 0 | 0 |

## Research decision and next pilot

Keep the current depth-based live model and the original trade classifier frozen. Continue with a separately specified price-only **source pilot**: up to 20 metadata-selected markets over seven consecutive April days. Freeze exact dates, IDs and byte limits before further retrieval. Include markets that fail coverage and report all rejection reasons; do not select on realized price moves or winning forecast results.

Before model fitting, establish mapping/status provenance, receipt-clock continuity, family/domain composition and usable market-day yield. Then freeze the price-only baseline comparison: persistence versus market-history candidates using momentum, volatility, spread and quote-update age. Use identical eligible rows, purged temporal development splits and an untouched future confirmation block. A depth feature must wait for validated reconstruction. A larger archive alone cannot establish incremental news value; that additionally requires relevant, timely news evidence and independent episodes.

The detailed next-pilot specification is [here](data/v7/archive_audit_delivery_20261025/next_pilot_specification.json). It is a proposed source pilot, not a model freeze or authorization to open protected evaluations.

## Integrity and operational status

No model was fitted or scored in these archive audits, no forecast errors were calculated, and no protected evaluation-period prices were read. Mixed April chunks physically decoded 28,558 rows belonging to excluded cohort IDs; those rows were filtered before economic analysis and were not retained in the selected panel. The raw range receipts are preserved. This distinction is explicit rather than claiming those April bytes were never read.

At approximately 01:12 UTC / 09:12 Singapore on 25 October, source PID5099, forecast PID8023 and fixed segment observer PID21055 were alive. The checkpoint had 121 timely base forecasts, 103 observed and 12 unavailable endpoints, zero missed decisions; the segment observer had 117 timely, six segment-active forecasts, 99 observed and 12 unavailable endpoints. These are operational counts, not interim accuracy results. The runs remain scheduled to finish around 22:04 Singapore time, subject to host/network availability.

## Reproducible evidence

- [Mapping diagnosis](data/v7/archive_mapping_diagnosis_20261025/probes.json)
- [Completed V03 audit](data/v7/archive_sample_20261025_v03/attempt_20261025T011030Z_66d836/report.json)
- [Per-market source audit](data/v7/archive_sample_20261025_v03/attempt_20261025T011030Z_66d836/market_metrics.json)
- [Replay sensitivity](data/v7/archive_replay_diagnosis_20261025/report.json)
- [Direct top-quote coverage](data/v7/archive_topquote_audit_20261025/report.json)
- [Frozen delivery manifest](data/v7/archive_audit_delivery_20261025/manifest.json)

Each package includes hashed source/implementation dependencies. Previous failures remain in their original versioned directories. No holdout or baseline result was altered.
