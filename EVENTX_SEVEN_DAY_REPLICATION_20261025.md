# EventX seven-day fixed-model replication

This extends the fixed-model historical test to May 13–19. The current booster, earlier booster and three baselines were frozen before retrieval. There was no model selection, fitting, recalibration or contract replacement. All sixty existing contracts were retained. The ten training-excluded contracts had already appeared in the preceding evaluation; this is temporal replication, not a new-identity test.

The fixed model retained a **20.80% log-loss improvement over activity logistic regression** on the development cohort and **3.48%** on the training-excluded cohort. It improved on the earlier booster by **16.35%** and **23.71%**, respectively. These are matched, known-outcome historical scores; the smaller transfer gain is not robust across every sensitivity check.

![Conditional model comparison](data/v7/week_replication_20261025/figures/conditional_comparison.png)

| Cohort | Issued / scheduled | Known outcomes | Contributing contracts | Current HGB LL | Logistic LL | Legacy HGB LL |
|---|---:|---:|---:|---:|---:|---:|
| development50 | 32,477 / 96,600 | 27,924 | 30 | 0.358321 | 0.452409 | 0.428349 |
| training_excluded10 | 2,694 / 19,320 | 2,033 | 6 | 0.255472 | 0.264693 | 0.334865 |

Lower log loss is better. The binary target is whether the recorded midpoint at t+30 minutes differs from the midpoint at t by more than 1e-12. It does not measure direction, economically meaningful movement, a move that reverses by the endpoint, market resolution or trading profit. This is a quote-change activity task, distinct from the original large-log-odds-movement news study; these results do not transfer to that task.

## Paired comparison

| Cohort | Baseline | Current-model log-loss reduction |
|---|---|---:|
| development50 | global_rate | 26.949945% |
| development50 | market_rate | 23.681586% |
| development50 | activity_logit | 20.797033% |
| development50 | legacy_hgb7 | 16.348346% |
| training_excluded10 | global_rate | 34.442654% |
| training_excluded10 | market_rate | 34.442654% |
| training_excluded10 | activity_logit | 3.483729% |
| training_excluded10 | legacy_hgb7 | 23.709085% |

Positive reductions favor the current booster; negative values are losses. The earlier booster remains a fixed comparator and does not become a newly selected winner after inspection. Global and market-rate forecasts are identical on the training-excluded contracts.

## Forecast coverage and missing outcomes

Unlike the preceding delivery, this report saves a probability for every decision with a valid current quote before selecting rows with known endpoints. The inference function never reads the label or endpoint-eligibility flag. This is retrospective replay, not evidence that forecasts were issued live in May. Decisions without valid current quotes abstain. No missing outcome is labeled zero.

| Cohort | Current-valid forecast coverage | Outcome coverage among issued | Missing outcomes |
|---|---:|---:|---:|
| development50 | 33.62% | 85.98% | 4,553 |
| training_excluded10 | 13.94% | 75.46% | 661 |

For each unknown outcome, we consider both possible labels and calculate the minimum and maximum baseline-minus-current log-loss difference. Combining these with observed losses bounds the average difference across all current-valid forecasts. These are deterministic missing-label bounds, not confidence intervals; they do not address invalid sources, quotes or unobserved contracts. A range spanning zero means the observed advantage is not guaranteed for all issued forecasts. These bounds assume a comparable binary target exists for each missing endpoint. If a market is closed or no meaningful quote exists, forecasting accuracy there is undefined; assigning hypothetical labels does not establish tradability or target validity.

| Cohort | Comparator | Lower mean LL improvement | Upper mean LL improvement |
|---|---|---:|---:|
| development50 | activity_logit | 0.033498 | 0.130679 |
| development50 | global_rate | 0.038647 | 0.158264 |
| development50 | legacy_hgb7 | 0.011970 | 0.134444 |
| development50 | market_rate | 0.028739 | 0.190978 |
| training_excluded10 | activity_logit | -0.043437 | 0.115017 |
| training_excluded10 | global_rate | -0.009803 | 0.179495 |
| training_excluded10 | legacy_hgb7 | -0.030188 | 0.126444 |
| training_excluded10 | market_rate | -0.009803 | 0.179495 |

## All metrics and sensitivity

| Cohort | Model | Rows / positives | Log loss | Brier | AP | AUC | Family-macro LL |
|---|---|---:|---:|---:|---:|---:|---:|
| development50 | activity_logit | 27924 / 5355 | 0.452409 | 0.139480 | 0.415974 | 0.718538 | 0.450828 |
| development50 | global_rate | 27924 / 5355 | 0.490515 | 0.155499 | 0.191771 | 0.500000 | 0.497471 |
| development50 | legacy_hgb7 | 27924 / 5355 | 0.428349 | 0.131121 | 0.473424 | 0.752467 | 0.430118 |
| development50 | market_rate | 27924 / 5355 | 0.469508 | 0.153597 | 0.301273 | 0.681229 | 0.492170 |
| development50 | row_hgb7 | 27924 / 5355 | 0.358321 | 0.109561 | 0.600582 | 0.836588 | 0.379193 |
| training_excluded10 | activity_logit | 2033 / 261 | 0.264693 | 0.071678 | 0.663774 | 0.898821 | 0.610460 |
| training_excluded10 | global_rate | 2033 / 261 | 0.389692 | 0.113575 | 0.128382 | 0.500000 | 0.869140 |
| training_excluded10 | legacy_hgb7 | 2033 / 261 | 0.334865 | 0.094235 | 0.475247 | 0.790387 | 0.654351 |
| training_excluded10 | market_rate | 2033 / 261 | 0.389692 | 0.113575 | 0.128382 | 0.500000 | 0.869140 |
| training_excluded10 | row_hgb7 | 2033 / 261 | 0.255472 | 0.067833 | 0.697193 | 0.882503 | 0.554044 |

| Cohort | Population | Observations | Current HGB LL | Logistic LL | Legacy HGB LL |
|---|---|---:|---:|---:|---:|
| development50 | strict | 6931 | 0.209317 | 0.295849 | 0.277467 |
| development50 | nonoverlap | 4748 | 0.355172 | 0.451494 | 0.422459 |
| training_excluded10 | strict | 101 | 0.104892 | 0.139818 | 0.186871 |
| training_excluded10 | nonoverlap | 328 | 0.246622 | 0.244983 | 0.322907 |

| Date | Cohort | Issued / observed | Current HGB LL | Logistic LL | Legacy HGB LL |
|---|---|---:|---:|---:|---:|
| 2026-05-13 | development50 | 4860 / 4062 | 0.364808 | 0.467753 | 0.510875 |
| 2026-05-14 | development50 | 4560 / 3822 | 0.368254 | 0.454969 | 0.453978 |
| 2026-05-15 | development50 | 4832 / 4213 | 0.380277 | 0.465844 | 0.491030 |
| 2026-05-16 | development50 | 5312 / 4751 | 0.366474 | 0.467920 | 0.411719 |
| 2026-05-17 | development50 | 4559 / 4014 | 0.343541 | 0.436166 | 0.379659 |
| 2026-05-18 | development50 | 4356 / 3759 | 0.353870 | 0.465105 | 0.407446 |
| 2026-05-19 | development50 | 3998 / 3303 | 0.322147 | 0.396420 | 0.324137 |
| 2026-05-13 | training_excluded10 | 389 / 217 | 0.314091 | 0.306193 | 0.353428 |
| 2026-05-14 | training_excluded10 | 386 / 214 | 0.472911 | 0.479852 | 0.480916 |
| 2026-05-15 | training_excluded10 | 461 / 390 | 0.127610 | 0.114938 | 0.177784 |
| 2026-05-16 | training_excluded10 | 479 / 425 | 0.276768 | 0.285852 | 0.280559 |
| 2026-05-17 | training_excluded10 | 306 / 202 | 0.268184 | 0.258065 | 0.419942 |
| 2026-05-18 | training_excluded10 | 288 / 256 | 0.172962 | 0.175958 | 0.292634 |
| 2026-05-19 | training_excluded10 | 385 / 329 | 0.255829 | 0.320674 | 0.464607 |

## Source and validity limits

Capture completed 168/168 hourly files through 171 attempts. Failed attempts: 3; recovered hours: 3; final missing hours: []. Recorded completed-range bytes: 1,659,517,394; retained YES events: 5,982,429. All retry receipts remain preserved. Successful retrieval verifies requested archive chunks, not completeness relative to all exchange events. Mixed pre-holdout chunks decoded 6,558,429 excluded-cohort rows before filtering; protected evaluation periods were not read.

Current metadata lists six development contracts with scheduled end dates before this test; nine development and two training-excluded contracts end during it. They remain in every scheduled-grid denominator. These dates are diagnostic metadata, not proof of actual historical closure or a posthoc exclusion rule.

The cohort is a convenience sample selected with current metadata, not a representative market universe or verified historical-status panel. Contracts remain counted after scheduled expiry and when coverage vanishes; retained valid quotes alone do not prove tradability. Adjacent thirty-minute targets overlap, and contracts share calendar conditions. Seven dates and event IDs do not establish independence. No statistical-significance, causal training-breadth, incremental-news or live-promotion claim follows.

Verification passed: 9,579 hash entries across 438 manifests; 45 metric sets recomputed from 35,171 unique issued predictions; 5,214 null outcomes preserved. Missing-label bounds were independently recomputed. Preflight matched the prior predictions exactly for all five models and confirmed inference does not read labels.

## Interpretation and next step

The development-cohort gain is the strongest result: the current booster beat logistic regression and the earlier booster on each of seven dates, under strict quote continuity, and on the nonoverlapping grid. The missing-label lower bound remains positive: at least 0.033498 nats versus logistic and 0.011970 versus the earlier booster across all 32,477 current-valid forecasts, conditional on a comparable binary target existing for the missing endpoints. These bounds address unknown labels, not source validity or live tradability.

Transfer remains less stable. Only six of ten training-excluded contracts supplied known outcomes. The current booster beat logistic on four of seven dates, while losing on May 13, 15 and 17. On the nonoverlapping grid its log loss was 0.246622 versus logistic 0.244983, reversing the small primary advantage. Its AUC was also lower than logistic (0.882503 versus 0.898821), although Brier and average precision improved. The missing-label improvement interval versus logistic, [-0.043437, 0.115017] nats, spans both loss and gain. The earlier booster was worse on all seven days of this cohort, but that does not make the comparison independent or prospective.

![Missing outcome bounds](data/v7/week_replication_20261025/figures/missing_outcome_bounds.png)

Across both cohorts, 35,171 historical forecasts were possible on 115,920 scheduled decisions; 29,957 had known outcomes and 5,214 remained unknown. The next priority is decision-time source/status validity and independent contract coverage, followed by a live paired test of the fixed probability models. Further model or eligibility choices need a new development block and another frozen evaluation period. May 13–19 is now consumed. The separate existing live point-price experiment evaluates different models and a different target; it cannot validate this quote-change classifier.

## Artifacts

- [Frozen protocol](eventx/release/v7/week_replication_20261025/protocol.json)
- [Canonical results](data/v7/week_replication_20261025/evaluation/result.json)
- [Issued predictions, including null outcomes](data/v7/week_replication_20261025/evaluation/issued_predictions.parquet)
- [Full scheduled grid](data/v7/week_replication_20261025/evaluation/grid_ledger.parquet)
- [Day/contract results](data/v7/week_replication_20261025/evaluation/groups.json)
- [Calibration bins](data/v7/week_replication_20261025/evaluation/calibration_bins.json)
- [QA and zero-coverage contracts](data/v7/week_replication_20261025/quality_assurance.json)
