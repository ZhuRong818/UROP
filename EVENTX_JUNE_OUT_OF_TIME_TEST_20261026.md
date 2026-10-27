# EventX: June out-of-time test of the frozen quote-change forecaster

26 October 2026. Version `june_replication_20261026`. Also records the failed fresh readiness rehearsal of the same day.

**The frozen booster beats every baseline on an unopened week, June 1–7, three weeks after its May 7–9 training data. Its log loss is 16.79% lower than the full-feature logistic baseline on the development cohort. The 95% contract-clustered bootstrap interval for the gain excludes zero. Separately, the live readiness rehearsal failed because the host clock is poorly disciplined; activation remains blocked.**

## What was tested

- **Target:** whether the recorded Polymarket YES midpoint differs 30 minutes later (`> 1e-12`). Same 18 features, freshness gates and endpoint rules as the 25 October replication. The target does not cover direction, movement size, resolution or profit.
- **Models:** `row_hgb7` (selected; May 7–9 refit), `activity_logit`, `legacy_hgb7`, `global_rate`, `market_rate`. These are byte-identical to the frozen bundles: preflight reproduced earlier predictions with maximum error below 1e-12, and all 12 inherited hashes matched. No fit, calibration, threshold or eligibility change.
- **Data:** 168 hourly pmxt Polymarket order-book files, 2026-06-01T00 to 06-07T23. All 168 completed; three transport failures were recovered on the single permitted retry. 3,989,357 YES-token events were retained. The 1,231 protected IDs were filtered at decode, and 0 protected-period rows were read.
- **Why June is unopened:** no prior quote study read June prices. The window precedes the consumed OOT (July 23–30), V3.1 (July 22–August 8) and V4 (from September 6).
- **Cohort:** the same 60 fixed IDs, with no replacement. Only 20 contracts had current-valid quotes in June. The others had expired or were inactive. Coverage is therefore 19% of scheduled grids, with 3,357 issued forecasts missing outcomes.
- **Order:** the protocol, preflight and implementation manifest were frozen before capture. The clustered-bootstrap script was written before evaluation. The evaluation ran once.

## Result (matched known outcomes; lower log loss is better)

| Cohort | Known / positives | Booster LL | Logistic LL | Legacy HGB LL | Global LL | Booster Brier | Logistic Brier | Booster AUC |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| development50 (18 contracts) | 16,453 / 2,068 | **0.29310** | 0.35225 | 0.32852 | 0.38541 | **0.08483** | 0.10027 | 0.835 |
| training_excluded10 (2 contracts) | 2,224 / 400 | **0.30709** | 0.35623 | 0.42895 | 0.47156 | **0.08587** | 0.10648 | 0.911 |
| all (20 contracts) | 18,677 / 2,468 | **0.29476** | 0.35272 | 0.34048 | 0.39567 | **0.08496** | 0.10101 | 0.846 |

Log-loss reduction for the booster, by comparator:

| Cohort | vs logistic | vs legacy HGB | vs global rate | vs contract rate |
|---|---:|---:|---:|---:|
| development50 | 16.79% | 10.78% | 23.95% | 28.74% |
| training_excluded10 | 13.80% | 28.41% | 34.88% | 34.88% |

The prespecified pass condition is met. On development50 the booster has lower log loss than both logistic and global rate, and no higher Brier.

**Uncertainty.** These are 95% intervals for the mean baseline-minus-booster log loss in nats, from 5,000 resamples; positive values favor the booster. Resampling uses whole contracts or whole dates.

| Cohort | Comparator | Gain | By contract | By date |
|---|---|---:|---|---|
| development50 | logistic | 0.0592 | [0.0391, 0.0805] (18) | [0.0472, 0.0726] (7) |
| development50 | legacy HGB | 0.0354 | [0.0037, 0.0697] | [0.0149, 0.0586] |
| all | logistic | 0.0580 | [0.0354, 0.0815] (20) | [0.0480, 0.0662] (7) |
| training_excluded10 | logistic | 0.0491 | [-0.014, 0.163] (2 contracts; uninformative) | [0.0094, 0.0860] |

**Robustness.** The booster beats logistic on **7/7 dates** and **17/20 contracts**. The nonoverlapping 30-minute subset agrees: all-cohort LL 0.2922 versus 0.3471 (3,119 rows). So does the strict continuous-path subset: 0.1554 versus 0.2270.

**Missing outcomes.** Deterministic all-issued bounds on the gain over logistic are [-0.0010, 0.0998] for development50 and [-0.0040, 0.1037] for all. The lower bound is barely below zero, and only if every one of the 3,357 unknown endpoints went against the booster. These bounds are not confidence intervals.

## How this changes the evidence

| Block | Weeks after training | Development50 LL gain vs logistic |
|---|---:|---:|
| May 9 (development, repeated use) | 0 | 15.99% (V03 14-feature variant) |
| May 13–19 replication | 1 | 20.80% |
| **June 1–7 (unopened)** | **3** | **16.79%** |

This is the first clean, outcome-blind confirmation that the quote-change forecaster beats its baselines out of time. Earlier blocks had been opened or reused.

**Limits:**
- This is historical replay, not live issuance.
- Observations within a contract are dependent; the cohort is a convenience sample, and only 20 of 60 contracts were active.
- The training-excluded cohort has two contracts, so it does not establish transfer to new identities.
- Metadata are current, not as-of-June.
- The task predicts quote activity. That differs from the original large-movement or news task, which is unaffected.

## Fresh live readiness rehearsal (11:26–12:06 UTC): FAILED

Result: `data/v7/forecast_runtime_20261026_v01/readiness_audit/report.json`. Zero of 16 decisions were ready, `normal_completion=false`, and the readiness gate failed. No forecasts were made and no labels constructed.

The root cause is the host clock, not the market feed or the model:

1. From 11:26 to 11:46, macOS `sntp` returned empty all-zero "selected" packets for all three servers. The summaries showed the host about **287 ms fast** with ±0.57 s uncertainty. The validator correctly rejected them as `invalid_server_header_or_stratum`.
2. At 11:51:08 the OS **stepped the wall clock back by 110 ms**. The collector correctly logged `clock_step` and `operational_cycle_gap`, which restarted the 30-minute transport warmup. As a result, no decision ever left warmup inside the 40-minute window.
3. After the step, Google and Cloudflare reported the host about **+0.10 to +0.12 s slow**, which exceeds the 100 ms budget. Apple's packets stayed invalid.
4. The step also made the wall-clock stop land at 12:06:11.716, earlier than the contracted 12:06:11.833. That is why `normal_completion` is false.

On this laptop, a run whose gates depend on wall-clock time cannot pass reliably. The frozen gates did their job. The failure is retained, and no gate was relaxed.

## Recommended next steps

1. **Fix the clock, not the gates.** Either run the live service on a host with a disciplined clock (chrony/ptp, under 10 ms), or freeze a new runtime version. The new version would anchor decisions to the monotonic clock and correct wall time using the validated median SNTP offset. The current V01 runtime stays frozen.
2. **Enlarge the live cohort.** The frozen live cohort is two illiquid macro contracts, so even a passing seven-day test would be underpowered. Choose a new versioned cohort using metadata only (for example, volume or liquidity rank and end date), never price outcomes. The booster's features are contract-agnostic.
3. **Test transfer to unseen contracts.** Repeat this frozen-model protocol on a later unopened week (June 8–28 remains unopened) with a metadata-selected cohort of new contracts. That would test transfer to new identities, which the two-contract excluded cohort cannot.

## Files

- Protocol and preflight: `eventx/release/v7/june_replication_20261026/{protocol.json,preflight.json,implementation_manifest.json}`
- Runner: `eventx/tasks/run_v7_june_replication_20261026.py`; bootstrap: `eventx/tasks/analyze_v7_june_replication_bootstrap_20261026.py`
- Source receipts: `data/v7/june_replication_20261026/source/capture_report.json`
- Results: `data/v7/june_replication_20261026/evaluation/{result.json,groups.json,calibration_bins.json,issued_predictions.parquet,manifest.json}`, `data/v7/june_replication_20261026/bootstrap.json`
