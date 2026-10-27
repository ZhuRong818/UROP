# EventX completed live point-forecast audit

The October 24–25 live run delivered forecasts on time, but **none of its candidates beat persistence on the prespecified primary metric, MAE**. This is a separate point-midpoint experiment; it does not test the historical quote-change probability classifier. The full frozen audit passed and no model was promoted.

## What operated successfully

- Scheduled decisions: 562 across two metadata-selected contracts.
- Timely forecasts: 269; abstentions: 293; missed decisions: zero.
- Observed endpoints: 257; unavailable endpoints: 12.
- Every issued forecast came from **US recession by end of 2026?**; **Negative GDP growth in 2026?** supplied none.
- The service stopped normally at its frozen stop time. Its last displayed forecasts are expired.

All 269 forecast feature/prediction replays and 269 endpoint/status replays matched. We checked 36,267 source, 1,102 base-forecast and 797 segment journal records, plus 1,815 input payload hashes. The maximum forecast commitment delay was 23.314 seconds against a 30-second deadline. No labels or forecasts were altered.

## Matched point-forecast results

Errors below are in probability units; multiply by 100 for percentage points. Each row compares models on the same observations within its panel.

| Panel | Model | Observations | MAE | RMSE |
|---|---|---:|---:|---:|
| short | persistence | 240 | 0.000250000 | 0.001118034 |
| short | short_ridge | 240 | 0.000299243 | 0.001120612 |
| short | snapshot_ridge | 240 | 0.000326778 | 0.001107666 |
| short | weighted_midpoint | 240 | 0.003144920 | 0.003279207 |
| snapshot | persistence | 257 | 0.000233463 | 0.001080424 |
| snapshot | snapshot_ridge | 257 | 0.000305545 | 0.001070406 |
| snapshot | weighted_midpoint | 257 | 0.003098702 | 0.003230823 |

Snapshot ridge had 30.88% higher MAE than persistence; short-history ridge had 19.70% higher MAE on its matched panel. Snapshot ridge slightly improved RMSE (about 0.93%), but that does not overturn the prespecified MAE result.

Only twelve observed endpoints differed from the initial midpoint. Their overlapping forecast intervals form two components of six rows each; these components are not independently validated information events. The remaining 245 observed endpoints were unchanged. A single contributing contract and sparse movement cannot support a broad forecasting claim.

## Segment hypothesis

The separately frozen segment observer emitted 265 timely forecasts, of which 253 had observed endpoints. Its momentum/imbalance gate activated six times, all with known outcomes. On those six rows persistence had zero error; the candidate MAE was 0.000802599. Across all 253 rows, fallback-plus-candidate MAE was 0.000256188 versus persistence 0.000237154, an 8.03% deterioration. The earlier posthoc development gain did not carry into this live run.

## Availability and source-clock findings

All 293 abstentions included an unavailable, old or quality-failing current book under the frozen receipt-based policy. Twenty-two also failed metadata/status checks. Twelve issued forecasts lacked valid forward outcomes; reasons overlap and must not be summed as separate forecasts.

The live policy constrains quote **receipt age**, not the elapsed age of the book message itself. Maximum receipt age was 52.303 seconds. Message-source age had median 143.012 and maximum 644.126 seconds; 163 of 269 forecasts had source age above 120 seconds. The frozen live policy allowed this. An old timestamp alone does not prove the returned book was incorrect; this audit reports the measurement without changing eligibility afterward.

This distinction prevents pooling the live results with the historical classifier, whose gates constrain both source and receipt age. The historical classifier also counts archive quote updates, whereas this live feature set uses polled books, depth and different history requirements. Target and feature compatibility must be established before using that classifier in a live service.

## Research decision

Preserve the historical classification gains and this negative live point-forecast result separately. The next useful experiment is a live quote-change probability test with audited feature/time semantics and metadata-defined active contracts, compared with the fixed baselines. It needs a new freeze and future outcomes. Further point-regression tuning on these 257 outcomes is not a validation step. No news-value, profit, independent-event or general market-efficiency claim is supported.

- [Canonical live audit](data/v7/live_memory_completion_20261026/report.json)
- [All timely forecasts and missing outcomes](data/v7/live_memory_completion_20261026/matched_rows.json)
- [Segment predictions and outcomes](data/v7/live_memory_completion_20261026/segment_rows.json)
- [Audit manifest](data/v7/live_memory_completion_20261026/manifest.json)
- [Separate seven-day classifier report](EVENTX_SEVEN_DAY_REPLICATION_20261025.md)
