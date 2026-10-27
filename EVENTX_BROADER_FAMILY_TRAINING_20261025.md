# EventX broader-family training and fresh transfer test

Completed the frozen broader-training iteration. **row_hgb7** was selected on May 9 before any May 10–12 evaluation data was retrieved. The test reports the fifty development contracts separately from ten unseen contracts. All model comparisons below use matched eligible rows, and the test winner was not substituted for the selected model.

The selected booster reduced test log loss by **22.67% versus activity logistic regression in the development cohort**, and by **9.62% in the reserved unseen cohort**. It also beat the fresh global-rate baseline in both. However, its unseen-cohort log loss was **0.36% worse than the earlier frozen booster**. This is evidence of baseline-beating forecasts in this sample, not proof that broader training improved transfer.

| Population | Eligible rows / markets | Selected LL | Fresh global LL | Fresh activity-logistic LL | Frozen legacy HGB LL |
|---|---:|---:|---:|---:|---:|
| development50 | 10,314 / 29 | 0.362424 | 0.498238 | 0.468667 | 0.452969 |
| unseen10 | 1,145 / 5 | 0.462057 | 0.566115 | 0.511220 | 0.460419 |

The binary target is one when the recorded midpoint at t+30 minutes differs from the midpoint at t by more than 1e-12. A move that reverses before the endpoint is labeled zero; very small endpoint differences count as changes.

![Matched model comparison](data/v7/family_training_20261025_v02/figures/matched_model_comparison.png)

Log loss is lower-is-better. The target remains probability of any observed thirty-minute midpoint change; this is not an exact-price, resolution, news-value or trading-profit result. Historical source completeness and tradability remain unverified.

Primary scoring conditions on future endpoint availability. That availability is unknown at forecast time, so these scores do not establish performance on every live decision or on missing endpoints. The strict-path and coverage diagnostics must be read alongside accuracy.

## What changed

The preceding model transferred across time on its original cohort but failed on newly selected contracts. This iteration tests whether training on more event families, with less dominance by busy families, improves transfer. The eighteen input features, endpoint eligibility and target definition remain unchanged.

The thirty existing contracts were retained. Thirty new contract/event-family-disjoint IDs were selected using identity availability and metadata before any new development prices: the first twenty joined development and the next ten were reserved for the final unseen-family test. No market was replaced after its returns, labels or forecasting errors were observed.

The first screening version exhausted 167 candidates and found only eighteen eligible families. It stopped before economic data collection. V02 preserved those eighteen in order and expanded the April 21 identity-only sample to two adjacent row groups. The extension downloaded 11,211,222 identity/clock/event bytes and made 75 supplementary metadata lookups. All initial failures remain preserved. Eligibility dates, model candidates and train/test allocations were unchanged. The broader ID range required an explicitly versioned eight-group/32-MiB per-hour retrieval cap.

The resulting sample is still an availability-conditioned convenience sample using current metadata. Event IDs are not proof of independent economic shocks or historically unchanged contract rules. Expired and zero-coverage contracts remain in the population accounting.

Development coverage: {"added20": {"contracts": 20, "eligible": 3064, "positives": 516, "with_eligible_rows": 8, "with_valid_current": 8}, "prior30": {"contracts": 30, "eligible": 6148, "positives": 1043, "with_eligible_rows": 12, "with_valid_current": 12}}. All fifty selected contracts remain in the ledger, including zero-coverage contracts.

## Frozen model comparison

May 7–8 supplied 6,143 eligible fit rows with 1,035 changes across 19 observed families. May 9 supplied 3,069 selection rows with 524 changes. After selection, all prespecified models were refit on 9,212 May 7–9 rows across 20 observed families and frozen. The ten final test families supplied no training or selection labels.

Fresh baselines are smoothed global prevalence, shrunk per-market prevalence and regularized activity logistic regression. Challengers are an ordinary row-weighted histogram booster, a partially family-balanced booster, and their fixed 50:50 probability blend. Both boosters use the same 100 iterations, learning rate 0.05, seven leaves, minimum leaf size 100 and L2=10. The earlier frozen HGB7 is an additional test anchor.

Family weights are `clip(sqrt(N / (F * n_family)), 0.25, 4)`, then normalized to mean one. Counts are computed only on eligible fitting rows. This reduces—but does not eliminate—domination by large families. It is not class balancing; it does not force equal positive/negative prevalence. Because weights change the training population, calibration must also be assessed on the intended evaluation population.

| Candidate | May 9 row log loss | Family-macro log loss | Brier | AP |
|---|---:|---:|---:|---:|
| global_rate | 0.457073 | 0.561460 | 0.141592 | 0.170740 |
| market_rate | 0.428682 | 0.561970 | 0.140655 | 0.286399 |
| activity_logit | 0.429713 | 0.530318 | 0.132132 | 0.363533 |
| row_hgb7 | 0.357099 | 0.406323 | 0.110720 | 0.527724 |
| family_hgb7 | 0.358585 | 0.398829 | 0.111207 | 0.528638 |
| blend_hgb7 | 0.357479 | 0.401934 | 0.110835 | 0.530563 |

Selection used row log loss, including the simple baselines, with ties favoring listed simpler methods. Family-macro loss is a prespecified secondary metric. Final normalized weights ranged from 0.797817 to 4.237202; mean 1.000000. Neither calibration nor model parameters were adjusted using May 10–12.

## New evaluation block: May 10–12

The development cohort is an assignment, not a claim that every test contract supplied fitting rows. Of its 29 contributing test contracts, nineteen supplied development labels and ten supplied none (1,552 test rows). The ten explicitly reserved contracts remained excluded from all fitting and selection.

Source capture completed 72/72 development files and 71/72 test files. It downloaded 1,311,239,258 economic-column bytes, retaining 1,416,544 development and 2,092,256 test events. The identity audit is separate. Test grids total 49,680: 41,400 for development contracts and 8,280 for unseen contracts. Errors are conditional on valid observed endpoints, not every scheduled decision.

| Cohort | Model | Rows / positives | LL ↓ | Brier ↓ | AP ↑ | AUC ↑ | Family-macro LL ↓ |
|---|---|---:|---:|---:|---:|---:|
| development50 | activity_logit | 10314 / 2028 | 0.468667 | 0.144380 | 0.398105 | 0.694979 | 0.507563 |
| development50 | blend_hgb7 | 10314 / 2028 | 0.362574 | 0.114811 | 0.591538 | 0.846158 | 0.418612 |
| development50 | family_hgb7 | 10314 / 2028 | 0.363497 | 0.114966 | 0.591767 | 0.845153 | 0.419237 |
| development50 | global_rate | 10314 / 2028 | 0.498238 | 0.158710 | 0.196626 | 0.500000 | 0.549572 |
| development50 | legacy_hgb7 | 10314 / 2028 | 0.452969 | 0.140992 | 0.437244 | 0.729486 | 0.506623 |
| development50 | market_rate | 10314 / 2028 | 0.450459 | 0.143468 | 0.370627 | 0.706422 | 0.537485 |
| development50 | row_hgb7 | 10314 / 2028 | 0.362424 | 0.114904 | 0.587869 | 0.846198 | 0.418779 |
| unseen10 | activity_logit | 1145 / 274 | 0.511220 | 0.170431 | 0.459651 | 0.789712 | 0.482044 |
| unseen10 | blend_hgb7 | 1145 / 274 | 0.467316 | 0.153598 | 0.532861 | 0.802792 | 0.414398 |
| unseen10 | family_hgb7 | 1145 / 274 | 0.474108 | 0.156284 | 0.526770 | 0.798063 | 0.418874 |
| unseen10 | global_rate | 1145 / 274 | 0.566115 | 0.186935 | 0.239301 | 0.500000 | 0.492649 |
| unseen10 | legacy_hgb7 | 1145 / 274 | 0.460419 | 0.149763 | 0.477921 | 0.786607 | 0.493180 |
| unseen10 | market_rate | 1145 / 274 | 0.566115 | 0.186935 | 0.239301 | 0.500000 | 0.492649 |
| unseen10 | row_hgb7 | 1145 / 274 | 0.462057 | 0.151208 | 0.535258 | 0.803536 | 0.411133 |

| Population | Selected versus | LL reduction | Relative reduction |
|---|---|---:|---:|
| development50 | global_rate | 0.135814 | 27.258888% |
| development50 | market_rate | 0.088035 | 19.543434% |
| development50 | activity_logit | 0.106243 | 22.669287% |
| development50 | legacy_hgb7 | 0.090546 | 19.989353% |
| unseen10 | global_rate | 0.104057 | 18.380942% |
| unseen10 | market_rate | 0.104057 | 18.380942% |
| unseen10 | activity_logit | 0.049163 | 9.616808% |
| unseen10 | legacy_hgb7 | -0.001638 | -0.355868% |

Positive reductions favor the selected model; negative values are losses. All six candidates are shown for the prespecified weighting ablation, not to pick a new winner after the test. On unseen markets, the fresh market-rate baseline falls back to the fresh global rate; these are not independent baselines there.

| Date | Cohort | Rows | Selected LL | Activity LL | Legacy LL |
|---|---|---:|---:|---:|---:|
| 2026-05-10 | development50 | 3323 | 0.350588 | 0.467702 | 0.425306 |
| 2026-05-10 | unseen10 | 379 | 0.444132 | 0.462129 | 0.406641 |
| 2026-05-11 | development50 | 3803 | 0.360546 | 0.468225 | 0.447025 |
| 2026-05-11 | unseen10 | 443 | 0.470591 | 0.543969 | 0.464617 |
| 2026-05-12 | development50 | 3188 | 0.377000 | 0.470201 | 0.488894 |
| 2026-05-12 | unseen10 | 323 | 0.471387 | 0.523907 | 0.517763 |

## Sensitivity and limitations

One test source hour, May 12 at 09:00 UTC, failed with a ReadTimeout. Its receipt is retained. It was not retried or substituted in this evaluation; decisions whose current or endpoint falls in that hour are not scored. Missingness can be informative, so conditional results cannot be extended to all decisions.

| Cohort | Population | Rows / positives | Selected LL | Activity LL | Legacy LL |
|---|---|---:|---:|---:|---:|
| development50 | strict_secondary | 2192 / 124 | 0.185786 | 0.289668 | 0.337394 |
| development50 | nonoverlap | 1707 / 337 | 0.368538 | 0.494985 | 0.457440 |
| unseen10 | strict_secondary | 109 / 41 | 0.595016 | 0.680000 | 0.546684 |
| unseen10 | nonoverlap | 189 / 47 | 0.431853 | 0.496628 | 0.428751 |

Selection still used a later date within the development cohort. The unseen-family evaluation is a genuine additional check within this workflow, but it does not make the three calendar dates independent or prospective. All old evaluation periods remain fixed. Any new selection strategy motivated by these results requires another evaluation block.

The architecture and weighting scheme are established methods; the research contribution, if supported by broader replication, is the controlled measurement of transfer, source coverage and calibration under distribution changes. Full date/market, calibration-bin, zero-coverage and secondary results must accompany any headline. No automatic model promotion follows.

## Interpretation and next step

The gains versus fresh global and activity-logistic controls persist on each of the three dates, on the nonoverlapping grid, and under strict continuous-path eligibility. Family weighting did not improve primary log loss over the selected row booster in either cohort. The fixed blend has a marginal Brier advantage within the development cohort but is not promoted after test inspection.

The unseen result is concentrated: five of ten contracts contribute rows, and the Cannes contract supplies 208 of 274 positive labels. The selected model beats activity logistic on four of five contributing contracts, but loses on AR-02. It has lower equal-family mean loss than the legacy booster while slightly worse row-weighted loss. These metrics answer different population questions; the frozen row-weighted primary remains authoritative.

The new model changes both training dates and training breadth relative to the legacy anchor. Consequently, the approximately 20% development-cohort improvement over that anchor cannot be attributed to breadth alone. A same-date, prior-30 versus expanded-50 training ablation is needed in a new development/evaluation cycle to identify that mechanism.

Next, retain both frozen boosters and the fresh baselines for a longer, prospectively specified paired evaluation across more dates and contributing contracts. Preserve all scheduled decisions and unavailable outcomes, and measure performance and coverage separately. Do not tune on May 10–12 or declare a transfer improvement from this single cohort. The immediate evidence supports the forecasting task; broader generalization, uncertainty under dependence and live validity remain open.

## Artifacts and verification

Verified 6852 entries across 338 recursively linked manifests and recomputed 105 model/population metric sets from saved predictions. Target/endpoint parity, unique grid keys, missing-target handling, model selection identity, disjoint cohort IDs and weight calculations passed. Synthetic checks confirm positive normalized weights independent of class labels and equal-family macro averaging. The feature/eligibility builder is inherited unchanged. Original models and protected holdouts remain untouched. Mixed pre-holdout chunks decoded 5,043,047 excluded-cohort rows, filtered before retained analysis.

- [Frozen V02 protocol](eventx/release/v7/family_training_20261025_v02/protocol.json)
- [Cohort assignments](data/v7/family_training_20261025_v02/cohort/cohorts.json)
- [All development selections](data/v7/family_training_20261025_v02/development/selection_before_test.json)
- [Training weights](data/v7/family_training_20261025_v02/development/weight_audit.json)
- [Frozen models](data/v7/family_training_20261025_v02/development/frozen_models.joblib)
- [Canonical test result](data/v7/family_training_20261025_v02/evaluation/result.json)
- [Per-market/date results](data/v7/family_training_20261025_v02/evaluation/groups.json)
- [Calibration bins](data/v7/family_training_20261025_v02/evaluation/calibration_bins.json)
- [Matched predictions](data/v7/family_training_20261025_v02/evaluation/predictions.parquet)
- [All grids and missingness](data/v7/family_training_20261025_v02/evaluation/grid_ledger.parquet)
- [Quality assurance and contract coverage](data/v7/family_training_20261025_v02/quality_assurance.json)
- [Delivery manifest](data/v7/family_training_20261025_v02/delivery_manifest.json)
