# EventX source-time quote-change classifier: preparation results

26 October 2026. Canonical version: **source_time_study_20261026_v02**.

**The target and evaluation protocol are frozen, all four models are fitted and frozen, and the live input check is complete. The corrected booster passes the development gate, but the live input gate fails. No prospective test has started.**

## Target, inputs and comparison

The target is whether the recorded YES midpoint changes after 30 minutes: `abs(midpoint(t+1800)-midpoint(t)) > 1e-12`. It does not predict direction, movement size, contract resolution or trading profit. Both endpoints use the same source-time quote definition. A missing or invalid endpoint is unknown, never an unchanged-price negative.

The 14 predictors are midpoint, logit midpoint, spread, UTC hour sine/cosine, and signed change, absolute change and missingness at 5/15/30-minute lags. Direct price-change BBO messages supply quotes. Only observations available by each decision or lag clock can contribute; no later backfill repairs an earlier observation. Freshness is limited to 120 seconds, spread to 0.05, and quotes must satisfy `0 < bid <= ask < 1`. Conflicting quotes at the latest source timestamp are unknown.

The fixed learners are:

| Model | Definition |
|---|---|
| Global rate | Laplace-smoothed training prevalence |
| Contract rate | Contract prevalence shrunk toward the global rate with strength 20; unseen contracts use the global rate |
| Logistic regression | All 14 features; training-only standardization; C=0.1 |
| Histogram gradient booster | All 14 features; 100 iterations, learning rate 0.05, 7 leaves, minimum leaf size 100, L2=10 |

There was no hyperparameter sweep, calibration search or selection of successful segments. Every model predicts on the same current-valid rows, and scores use identical known-outcome keys. The primary contrast is booster versus the full-feature logistic baseline.

## Development result

The fit uses May 7–8; May 9 provides the development comparison. All four models were then refitted on May 7–9. These dates are outcome-open development data, **not an untouched holdout**. Earlier quote test periods and protected OOT/V3.1/V4 data were not used.

| Stage | Known outcomes | Positive outcomes | Contributing contracts |
|---|---:|---:|---:|
| Initial fit: May 7–8 | 6,304 | 1,137 | 19 |
| Development comparison: May 9 | 3,102 | 535 | 19 |
| Final refit: May 7–9 | 9,406 | 1,672 | 20 |

Across the 50 fixed development identities, 41,400 scheduled grids yielded 11,084 valid feature vectors. Of those, 9,406 had known endpoints and 1,678 remained unknown. No identities were dropped because of poor performance or missing data.

Corrected May 9 comparison:

| Model | Log loss ↓ | Brier ↓ | Average precision ↑ | ROC AUC ↑ |
|---|---:|---:|---:|---:|
| Global rate | 0.459999 | 0.142788 | 0.172469 | 0.500000 |
| Contract rate | 0.437085 | 0.144547 | 0.292231 | 0.706015 |
| Logistic regression | 0.426789 | 0.129403 | 0.398262 | 0.747482 |
| Histogram booster | **0.358559** | **0.111371** | **0.524780** | **0.810732** |

The booster reduces development log loss by **15.986910020304176% versus logistic regression**, **22.052196893288688% versus the global rate**, and **17.96588556361642% versus the contract rate**. It passes the prespecified development gate: lower log loss and no higher Brier than both logistic and global-rate baselines.

The fixed nonoverlapping 30-minute subset contains 534 known outcomes. Booster log loss is 0.3350209337828005 versus logistic 0.4068747666475679, a 17.659938328642205% reduction. Equal-contract mean log loss is 0.4039771824530405 versus 0.5305582379252196. These remain descriptive development comparisons; thinning does not remove shared contract or calendar dependence.

May 9 also has **586 unknown endpoints among 3,688 current-valid predictions**. The deterministic all-issued log-loss-gain bounds versus logistic regression are **[-0.08159266365256779, 0.10053014535673122] nats**. They cross zero. The observed-outcome improvement therefore does not establish improvement across every issued prediction. These bounds are not confidence intervals.

## Implementation correction retained in the record

The initial V01 development loader reset history at each UTC date. A continuous live source retains earlier observations, so the 00:30 decision's 30-minute lag can use a quote just before midnight. A boundary audit found **22 affected vectors among 100 checked May 8/9 boundary decisions**.

V02 was frozen as a mandatory consistency repair before its refit. It carries prior available development history across dates; May 7 remains left-censored because May 6 was not fetched. The correction changes only the 30-minute lag feature family on those 22 vectors. All 41,400 grid keys, current eligibility and targets are unchanged.

V01's reported 16.57% logistic improvement is preserved in its artifacts but is **superseded by the corrected 15.99% result**. V02 is retained even though its development score is slightly worse. V01 is not eligible for activation. Repeated use of May 9 is disclosed; this repair is not independent validation.

## Live input readiness: failed

The public-source-only capture ran on 26 October **03:06:42–03:46:42 UTC** (11:06:42–11:46:42 Singapore time). It is a completed capture, not a currently running forecast service.

- Two previously fixed identities: negative GDP growth in 2026 and US recession by end of 2026.
- Normal bounded completion, 529 journal records, 93 WebSocket frames and 232 application pongs.
- All 80 metadata and 80 resolution requests returned observed responses.
- YES projection: 92 price-change rows and two book rows; zero projection or scope errors.
- Eight scheduled five-minute decisions per contract, including warmup.

| Contract | Scheduled decisions | Quote-valid | Transport-ready after warmup | Fully ready |
|---|---:|---:|---:|---:|
| Negative GDP growth | 8 | 2 | 2 | **0** |
| US recession | 8 | 1 | 2 | **0** |

Both contracts passed metadata checks at all eight decisions. The gate required normal completion, no schema/scope errors, and at least two fully ready market-decisions across at least one contract after warmup. It failed: **zero fully ready decisions**.

The principal measured problem is timestamp ordering. **84/92 price-change rows have exchange source time later than local durable availability**, by up to **0.09100008010864258 seconds**. Median availability-minus-source time is **-0.06199991703033447 seconds**. The frozen `source <= availability` rule rejects those observations. At all four post-warmup market-decisions, the latest observation satisfying that rule is older than 120 seconds.

This does not establish that the markets are inactive or that the API omitted data. The stream delivered messages and metadata; the relative source/local clock interpretation is unresolved. Genuine staleness also remains in some decisions. Clock skew and exchange timestamp semantics require verification before choosing any new tolerance rule.

An initial diagnostic inspected source age without applying the ordering condition and mislabeled some rejected quotes as eligible. It is preserved as `readiness_diagnosis_incomplete_heuristic_v00.json`; the final diagnosis exactly reproduces all 16 feature-eligibility decisions.

## Frozen future evaluation

The protocol specifies seven consecutive full UTC days starting on the first full day after a separate activation receipt. No dates have been activated and no predictions have been issued. The two identities stay fixed; no outcome-driven replacement or removal is allowed.

Activation requires the model gate, live input gate, implementation QA and a frozen live emitter/evaluator. The receipt must bind their hashes, the cohort and exact first/last grids before forecasting. The current live input gate has failed, so activation is blocked.

Inputs must be available by the grid, and forecasts durably emitted within 30 seconds; late decisions abstain. Endpoint evidence must have been available by the endpoint even though adjudication runs 120 seconds later. Fresh metadata/resolution coverage and transport checks apply. Missing outcomes remain null. Performance stays unopened until the last endpoint plus 120 seconds; an audit and one-time consumption receipt precede scoring. There is no optional stopping or extension to obtain favorable results or enough positives.

Primary reporting is matched log loss; Brier, AP, AUC, per-contract results, equal-contract loss, calibration, nonoverlap and unknown-label bounds accompany it. Fewer than 100 known outcomes, 20 positives or 20 negatives makes predictive comparison insufficient. These are reporting floors, not a statistical power guarantee. Two contracts do not support broad transfer, independent-news-event or market-efficiency claims.

## Next work

1. Verify exchange-versus-host clock offset and timestamp meaning using independent clock evidence while preserving wire and durable times. Do not edit recorded timestamps to pass eligibility.
2. If a bounded timestamp-uncertainty rule is justified, freeze it as a new input version and consistently rebuild development inputs/targets and models where affected. Preserve the present strict-clock failure.
3. Repeat the label-blind readiness check under the justified contract. A new service must establish its own warmup; this closed capture cannot supply future live history.
4. Only after those gates pass, freeze the live emitter/evaluator and activate the future seven-day test. No additional model tuning is needed to address the presently observed clock bottleneck.

## Review package and verification

- [Frozen protocol](eventx/release/v7/source_time_study_20261026_v02/protocol.json)
- [Development report](data/v7/source_time_study_20261026_v02/development/report.json)
- [Fitted model bundle](data/v7/source_time_study_20261026_v02/development/frozen_models.joblib)
- [Live readiness result](data/v7/source_time_study_20261026_v02/readiness_audit/report.json)
- [Clock diagnosis](data/v7/source_time_study_20261026_v02/readiness_diagnosis.json)
- [QA receipt](data/v7/source_time_study_20261026_v02/qa.json)

Verification passed 27 unit tests, replayed all 3,688 development predictions, recomputed all four matched metric sets, checked 41,400 unique grid keys and confirmed the exact 22-vector boundary correction with zero target/eligibility changes. Existing frozen artifacts remain intact. No live labels were read, no prospective forecasts were issued, and no trading or external messaging occurred.
