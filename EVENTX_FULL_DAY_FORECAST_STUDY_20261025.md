# EventX full-day observational forecasting study — 25 October 2026

The frozen selection procedure did not produce a model that beat persistence on the development evaluation. This is a chronological **development result**, not independent confirmation, tradable execution performance or evidence that news helps.

## Data expansion

The same 20-market cohort was extended to all 24 hours on April 21–27: 168/168 hourly files completed, including 14 reused files. The extension downloaded 595,574,310 new archive bytes and retained 1,458,500 YES-token events. No market was replaced based on coverage or performance.

Across 38,640 scheduled five-minute decision points, 4,086 had valid 30-minute history and 2,457 also had continuous valid forward coverage. There were 14,330 fresh endpoint pairs. Missing-file windows: 0. Complete-case accuracy applies to the observed eligible subset, not every scheduled decision.

The grid runs 00:30–23:25 UTC each day; cross-midnight history/target windows are excluded by the frozen design. Direct best bid/ask, unique receive-time pairs, 120-second source/receive freshness and a 0.05 spread cap remain unchanged. Ambiguous and invalid states interrupt coverage. No depth is reconstructed.

## What the model predicts

The target is the archive-observed YES midpoint 30 minutes after a decision. This is a new price-only regression task. It does not predict contract resolution and is different from the original classifier for large absolute log-odds movements.

Historical tradable/active status and exchange-message completeness remain unverified. The new task explicitly measures the observed quote series; it does not relax the original live/depth/trade study gates. Original-study admissions remain zero. Current metadata was used for identity/cohort description, not forecasting features.

Features available by decision time are midpoint, spread, changes over 5/15/30 minutes, volatility, minimum/maximum prices over the trailing half-hour, source/receive age, recent quote-group count and UTC time. Learned models predict the future midpoint change, added to the current midpoint and clipped to [0,1]. No text or news features enter this experiment.

## Frozen development comparison

April 21–23 supplied 782 complete training rows; April 24 supplied 261 selection rows. The minimum-data gate passed: True. Selection used lowest MAE including persistence, with ties favoring persistence. The chosen candidate was **persistence**. Learned preprocessing was fit on training data only; the chosen model was then refit on April 21–24 before April 25–27 evaluation.

| Candidate | April 24 selection MAE | Status |
|---|---:|---|
| persistence | 0.0001992337 | scored |
| drift_0.1 | 0.0002093870 | scored |
| drift_0.25 | 0.0002246169 | scored |
| ridge_1 | 0.0004177739 | scored |
| ridge_100 | 0.0003819158 | scored |
| hgb_absolute | 0.0001992337 | scored |

The final comparison uses **1,414 identical rows**, 11 markets and 3 evaluation dates. All unchanged endpoints and all eligible domains are retained.

| Model | MAE (probability units; lower is better) | RMSE (lower is better) |
|---|---:|---:|
| Persistence | 0.0003518388 | 0.0016644316 |
| Selected: persistence | 0.0003518388 | 0.0016644316 |

MAE reduction: 0.0000000000; relative reduction: 0.000000%.

| Evaluation date | Matched rows | Persistence MAE | Selected MAE |
|---|---:|---:|---:|
| 2026-04-25 | 414 | 0.0000157005 | 0.0000157005 |
| 2026-04-26 | 593 | 0.0003372681 | 0.0003372681 |
| 2026-04-27 | 407 | 0.0007149877 | 0.0007149877 |

Changed endpoints: 102; unchanged endpoints: 1,312. The changed/unchanged diagnostics are reported separately in the result artifact and were not used to keep winning evaluation rows. Full per-market errors are retained.

## Interpretation and next decision

No model is promoted to the live service from this result. The initial two-hour source audit already exposed coverage across these dates, and the cohort was selected using present-day metadata and April availability. The full-day protocol was frozen before new full-day prices, but the result is still development evidence. Overlapping 30-minute targets and common market/calendar shocks mean row counts are not independent sample size. No naive row-level significance intervals are reported.

Keep this result fixed. The next confirmatory step needs an untouched disjoint period, fixed cohort/eligibility/features and enough market-day diversity; do not retune on April 25–27 or keep only its winning segments. Audit whether gains, if any, persist across market families and changed/unchanged regimes using the saved descriptive tables. Broader news claims still require separately verified release evidence.

For research usability, this run now provides auditable matched predictions, explicit missingness, a reproducible selected model and a persistence comparison. It does not by itself establish a deployable advantage.

## Verification and artifacts

Verified 188 manifest entries. The implementation reproduced all 140 prior market-day coverage checks and passed synthetic future-feature isolation, failed-hour and ambiguous-tie tests. All protected holdouts, frozen original models and live forecast services remain unchanged. New mixed April reads decoded 3,369,323 excluded-cohort rows and filtered them before retained economic analysis; no protected-period rows were read.

- [Frozen observational protocol](eventx/release/v7/archive_fullweek_20261025/observational_protocol.json)
- [Capture report](data/v7/archive_fullweek_20261025/capture_report.json)
- [Coverage](data/v7/observational_quote_development_20261025/coverage.json)
- [All candidate selection results](data/v7/observational_quote_development_20261025/selection_before_evaluation.json)
- [Canonical evaluation result](data/v7/observational_quote_development_20261025/result.json)
- [Per-date and per-market results](data/v7/observational_quote_development_20261025/evaluation_groups.json)
- [Matched predictions](data/v7/observational_quote_development_20261025/evaluation_predictions.parquet)
- [All scheduled grids and missingness](data/v7/observational_quote_development_20261025/grid_ledger.parquet)
- [Selected model](data/v7/observational_quote_development_20261025/selected_model.joblib)
- [Frozen result manifest](data/v7/observational_quote_development_20261025/manifest.json)
