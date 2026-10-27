# EventX: diagnosing shortcomings and testing change probabilities

The new iteration selected **hgb7** and evaluated it once on April 28–30, after freezing the model. It reduced log loss against **3 of the three prespecified baselines** on 3,729 matched rows. This is a **different target** from exact-price regression: the probability of any recorded midpoint change over 30 minutes. It is not evidence that exact-price MAE, tradability or news prediction improved.

**Important limitation:** the selected model loses to global and per-market rate baselines on the original strict-continuity subset. It also slightly loses to the global rate on April 30. The aggregate improvement does not establish uniform performance or reliable calibration.

## Shortcomings addressed

| Shortcoming | Change in this iteration | What remains unresolved |
|---|---|---|
| MAE favored unchanged-price predictions in the previous task | Predict a probability of change; evaluate log loss and Brier instead of rewarding only a point forecast | No direction, magnitude or trading-performance claim |
| Full-path continuity discarded endpoint observations | Require fresh, valid current and 30-minute endpoint quotes; preserve the old strict population as a secondary analysis | Errors remain conditional on observed endpoints; missing targets are unknown |
| Missing history made feature rows unusable | Use explicit missing flags for unavailable 5/15/30-minute changes; keep source age and observed-update activity | Missing source data can differ from genuine market inactivity |
| Weak baseline could exaggerate improvements | Compare against global prevalence, shrunk per-market prevalence and activity logistic regression | All use the same fixed, nonrepresentative cohort |
| Repeated overlapping rows inflated apparent sample size | Retain per-day/per-market results and a fixed non-overlapping-grid sensitivity check | Three dates do not support strong inference or effective-sample-size claims |
| Reusing opened evaluation data could overfit the research | Use April 21–24 only for development; leave April 25–27 fixed; freeze before retrieving April 28–30 | New historical time block, not prospective or independent-market replication |

## Frozen method

An event is an absolute difference greater than 1e-12 between the archived YES midpoints at decision time and 30 minutes later. The tolerance distinguishes unchanged recorded prices from floating-point noise; it is not a profitability or economically material movement threshold. Both endpoints require a unique receive-time quote pair, source/receive freshness at most 120 seconds, noncrossed interior prices and spread at most 0.05. No target is assigned to missing endpoints.

The model uses 18 price/availability features: midpoint and logit midpoint; spread; source and receive age; UTC time; count and fraction of valid observed quote states in the last half-hour; and signed/absolute changes over 5, 15 and 30 minutes with explicit missing indicators. Missing lag values are encoded as zero plus a flag. All features use observations received by decision time. There are no news or depth features.

Eight models were prespecified: a smoothed global event rate; a per-market event rate shrunk toward the global rate with 20 pseudo-observations; an activity logistic baseline; three full logistic regularization settings; and histogram gradient boosters with three or seven leaves. The boosters use 100 iterations, learning rate 0.05, minimum leaf size 100 and L2=10. There is no class balancing or oversampling that would distort probabilities. The algorithm families are established methods, not an algorithmic novelty claim.

Development expanded from **1,043 strict rows to 7,968 endpoint-eligible rows** on the same April 21–24 dates. These are different eligibility populations, so this is increased coverage rather than a controlled accuracy improvement. Training used 5,980 rows/831 positives on April 21–23; selection used 1,988/237 on April 24. The chosen model and all three baselines were refit on April 21–24 and frozen before test retrieval.

| Candidate | April 24 log loss | Brier | Average precision |
|---|---:|---:|---:|
| global_rate | 0.367078 | 0.105398 | 0.119215 |
| market_rate | 0.307693 | 0.096613 | 0.248832 |
| activity_logit | 0.327789 | 0.092017 | 0.398321 |
| full_logit_0.01 | 0.334131 | 0.094832 | 0.363630 |
| full_logit_0.1 | 0.337233 | 0.095689 | 0.339861 |
| full_logit_1 | 0.338795 | 0.096150 | 0.330758 |
| hgb3 | 0.282027 | 0.083723 | 0.463495 |
| hgb7 | 0.271768 | 0.083196 | 0.450525 |

## New-time-block results

All 72/72 hourly files completed, downloading 263,008,006 bytes and retaining 609,180 YES events. Same 20 IDs; no replacements. Among 16,560 scheduled grids, 4,392 had a fresh valid current quote and 3,729 had an eligible endpoint. Evaluation covers 11 markets/3 dates with 903 positive events.

| Model | Log loss ↓ | Brier ↓ | Average precision ↑ | ROC AUC ↑ |
|---|---:|---:|---:|---:|
| activity_logit | 0.605235 | 0.190210 | 0.364941 | 0.554435 |
| global_rate | 0.595625 | 0.195187 | 0.242156 | 0.500000 |
| hgb7 | 0.495491 | 0.157578 | 0.523364 | 0.752000 |
| market_rate | 0.715401 | 0.188429 | 0.338055 | 0.618657 |

| Selected model versus baseline | Log-loss reduction | Relative reduction | Brier reduction |
|---|---:|---:|---:|
| activity_logit | 0.109744 | 18.132431% | 0.032633 |
| global_rate | 0.100134 | 16.811608% | 0.037609 |
| market_rate | 0.219910 | 30.739368% | 0.030852 |

Positive reductions favor the selected model. Negative reductions mean it performed worse. All comparisons use identical eligible rows; no winning segment was retained after evaluation.

| Date | Rows / positives | Global-rate LL | Market-rate LL | Activity-logistic LL | Selected LL |
|---|---:|---:|---:|---:|---:|
| 2026-04-28 | 1139 / 318 | 0.664696 | 0.839328 | 0.611575 | 0.503967 |
| 2026-04-29 | 1444 / 479 | 0.762652 | 0.917884 | 0.773731 | 0.630731 |
| 2026-04-30 | 1146 / 106 | 0.316517 | 0.337095 | 0.386623 | 0.316660 |

## Prespecified sensitivity checks

| Population | Model | Rows | Positives | Log loss | Brier |
|---|---|---:|---:|---:|
| Strict continuity subset | activity_logit | 896 | 17 | 0.282162 | 0.078031 |
| Strict continuity subset | global_rate | 896 | 17 | 0.179402 | 0.031874 |
| Strict continuity subset | hgb7 | 896 | 17 | 0.236843 | 0.063597 |
| Strict continuity subset | market_rate | 896 | 17 | 0.190338 | 0.034618 |
| Non-overlapping 30-minute grid | activity_logit | 595 | 136 | 0.574188 | 0.179140 |
| Non-overlapping 30-minute grid | global_rate | 595 | 136 | 0.570291 | 0.185246 |
| Non-overlapping 30-minute grid | hgb7 | 595 | 136 | 0.481878 | 0.153767 |
| Non-overlapping 30-minute grid | market_rate | 595 | 136 | 0.679415 | 0.180819 |

The stricter population is a secondary analysis using the already selected endpoint-trained model. The 30-minute grid reduces overlapping targets but does not remove common-market/day dependence. Neither was used to choose models or retain a favorable result. Fixed-bin calibration and all per-market errors are included in the artifacts.

## Remaining shortcomings and next decision

Calibration remains imperfect: in the selected model’s lowest probability bin, mean predicted risk is about 2.19% versus an observed 8.01%. These are descriptive test diagnostics, not data for recalibrating this frozen model. Any calibration repair needs separate development data and a new test. Only three new evaluation dates and the same 20-market convenience cohort were tested. Current metadata/rule versions may differ historically; active tradability and source completeness are not established. Some contract end dates precede the new block, so attrition is retained rather than replaced. Global headline gains can conceal day, family or calibration failures; the complete tables must accompany any presentation.

The training positive labels form 94 groups of overlapping target windows within markets, rather than 831 independent events; the selection positives form 35 groups rather than 237 independent events. Even those groups can share calendar information, so they are not effective sample-size estimates. No naive row-level significance interval is reported.

Keep this model and result fixed. The next iteration should test transport to additional metadata-selected contracts and more independent calendar periods, with a frozen calibration/selection protocol and explicit source-coverage reporting. Any redesign prompted by April 28–30 must use a new evaluation block. No automatic deployment, news-value claim or revision of the previous persistence result follows from this study.

## Audit and files

Verified 93 manifest entries. QA reproduced the original fresh endpoint pair counts and all 1,043 strict rows/labels, checked explicit missing features and unlabeled missing endpoints, and excluded April 25–27 from development. New source reads decoded 1,668,312 excluded-cohort April rows and filtered them before retained analysis. No protected evaluation-period rows were read; existing live services and frozen original models are unchanged.

- [Frozen protocol](eventx/release/v7/change_probability_20261025/protocol.json)
- [Development selection](data/v7/change_probability_20261025/development/selection.json)
- [Frozen models](data/v7/change_probability_20261025/development/frozen_models.joblib)
- [New-block result](data/v7/change_probability_20261025/evaluation/result.json)
- [All date and market results](data/v7/change_probability_20261025/evaluation/groups.json)
- [Calibration](data/v7/change_probability_20261025/evaluation/calibration.json)
- [Matched predictions](data/v7/change_probability_20261025/evaluation/predictions.parquet)
- [All decision grids and missingness](data/v7/change_probability_20261025/evaluation/grid_ledger.parquet)
- [Development QA](data/v7/change_probability_20261025/qa.json)
- [Delivery manifest](data/v7/change_probability_20261025/delivery_manifest.json)
