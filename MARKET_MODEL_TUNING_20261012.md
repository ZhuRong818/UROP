# Market-only condition tuning: 12 October 2026

The user authorized tuning the market model first. The selected development candidate beats the previous selected booster, the earlier tree and logistic regression on identical later-fold rows. This uses already opened May–July data, not October market conditions or an untouched confirmation interval.

## Selected result

Selected on fold 4: **condition_120k**. It uses 120,000 earlier training rows, the existing seven-leaf histogram booster (600 iterations), and nine deterministic market-state features. Fold-4 selection applied a Brier guardrail and was receipted before new fold-5 fits.

| Model, same 112,616 fold-5 observations | Log loss | Brier | Average precision |
|---|---:|---:|---:|
| L2 logistic | 0.402488896 | 0.121762457 | 0.205412788 |
| Earlier tree | 0.348884308 | 0.110879519 | 0.327323039 |
| Previous selected booster | 0.344816319 | 0.109676555 | 0.337805095 |
| **Selected condition model** | **0.342948930** | **0.109059765** | **0.346248526** |

Relative log-loss reductions on these rows: **0.541560% versus the previous booster**, **1.701245% versus the earlier tree**, and **14.792946% versus logistic**. These are this panel’s comparisons. The older 9.68% claim uses a different population and must not be combined with these percentages.

The selected model also improves fold 4: log loss 0.439301216 to 0.435498221, Brier 0.142374586 to 0.141000340, and AP 0.330999598 to 0.346893713. Fold 5 Brier improves by 0.000616790 and AP rises by 0.008443431 versus the previous booster.

## Changes examined

The nine added features describe short/long volatility ratios, volatility-scaled momentum, a momentum reversal proxy, recent activity and size-rate ratios, trade age interacting with volatility, and price uncertainty. They use only existing trailing features. Ratio denominators use a fixed 1e-6 stabilizer and bounded clipping, without fitting later-fold statistics. Training caps, recency weights and tree complexity vary in a fixed nine-candidate grid. All eighteen new fold fits completed.

| Candidate | Fold-4 log loss | Fold-5 log loss |
|---|---:|---:|
| condition_120k | 0.435498221 | 0.342948930 |
| condition_120k_15leaf | 0.435932541 | 0.342882028 |
| condition_60k | 0.436555843 | 0.342852476 |
| larger_120k | 0.438413131 | 0.344624989 |
| larger_120k_15leaf | 0.438071990 | 0.343888198 |
| larger_200k | 0.438302609 | 0.344509674 |
| recent_120k_14d | 0.438330847 | 0.344630447 |
| recent_condition_120k_14d | 0.435824260 | 0.342975435 |
| recent_condition_120k_30d | 0.435552488 | 0.342652113 |
| retained_hgb_7_600 | 0.439301216 | 0.344816319 |

The 30-day recency-weighted condition model has the smallest later-fold score, 0.342652113, but it was not selected by fold 4. It remains a post-hoc observation. The selected model is unchanged. Increasing data alone produces smaller gains than adding condition features in this screen.

## Remaining error groups

Below are prespecified trade-age diagnostics for the selected candidate versus the previous booster. These do not redefine eligibility or select a subset for the headline result.

| Last trade age, minutes | Rows | Previous booster log loss | Selected log loss |
|---|---:|---:|---:|
| 0–5 | 46,519 | 0.327682 | 0.324234 |
| 5–15 | 35,448 | 0.358548 | 0.357283 |
| 15–30 | 30,648 | 0.354949 | 0.354784 |
| 30–60 | 1 | 0.103758 | 0.119634 |

## Interpretation and limits

The descriptive market-cluster interval for the gain versus the previous booster is [0.000610594, 0.003026140] nats per row. It does not adjust for this adaptive search, linked event families or common calendar shocks, and is not confirmatory significance. Forward dates, market-ID disjointness and the 30-minute purge were checked; eligibility and target stayed fixed. Historical status/coverage uncertainty remains. News was excluded from this screen. No consumed holdout or frozen future payload was read, and no model was promoted into V4.

The next useful step is probability-calibration and market-state robustness diagnosis of this selected candidate, followed by a separately frozen untouched evaluation. Further later-fold optimization should be reported as development search.

## Deliverables

- [Canonical report](data/v5/market_condition_tuning_20261012/report.json)
- [Grid and source contract](data/v5/market_condition_tuning_20261012/contract.json)
- [Selection receipt](data/v5/market_condition_tuning_20261012/selection_receipt.json)
- [Saved development model](data/v5/market_condition_tuning_20261012/selected_model.joblib)
- [Delivery checks](data/v5/market_condition_tuning_20261012/delivery_checks.json)
- [Implementation](eventx/tasks/tune_v5_market_conditions_20261012.py)
