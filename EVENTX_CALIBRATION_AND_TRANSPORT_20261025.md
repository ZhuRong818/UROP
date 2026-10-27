# EventX calibration and transport validation — 25 October 2026

**Temporal performance held up; new-contract transfer failed.** On the original cohort the frozen booster beat activity logistic regression and the updated global-rate control. On the new cohort it lost to both, with ROC AUC 0.519699. Calibration selection retained identity; no calibration improvement was established.

The fixed HGB7 model was tested on May 4–6 after a separate May 1–3 calibration cycle. **identity** was selected for calibration. Results below separate later-period performance on the original markets from performance on ten newly selected contracts. The base model was not retrained, and earlier evaluation blocks were not reused.

| Evaluation population | Eligible rows / markets | Raw HGB log loss | Calibrated HGB log loss | Updated constant-rate log loss | Calibration LL reduction |
|---|---:|---:|---:|---:|---:|
| original | 3,617 / 10 | 0.496530 | 0.496530 | 0.536579 | 0.000000 |
| transport | 2,006 / 4 | 0.812621 | 0.812621 | 0.734010 | 0.000000 |

Positive reduction favors calibration; negative reduction means calibration made predictions worse. Comparing against the updated constant-rate control tests whether performance exceeds simply learning the more recent event rate. These are historical observational results, not live tradability, profitability or news-value evidence.

Calibration selection retained identity: neither intercept nor sigmoid correction improved May 3 log loss. The calibrated column therefore represents the unchanged raw model, not an additional improvement.

## Design and safeguards

The original twenty contracts remain fixed, including those that cease yielding eligible quotes. Ten additional contracts were selected using cached identity availability and current metadata, before new price retrieval. Their contract IDs and ten current event-family IDs do not overlap the original cohort. Selection used a deterministic order, exact YES/NO mapping and start/end/rules checks. There were 54 metadata lookups, and no replacement based on forecast accuracy or price changes.

Event-family separation strengthens the transfer test, but it does not make calendar shocks independent. Selection uses present metadata and an availability-conditioned part of the archive, so the new cohort is not a representative sample of all markets. Historical rule versions, tradability and message completeness remain unresolved.

The target and eighteen features are unchanged: probability of an observed midpoint change over thirty minutes, using fresh valid current/endpoint quotes, with missing historical lags flagged. The new implementation exactly matches the previous feature and eligibility builder apart from accepting a cohort parameter. All scheduled grids and missing endpoints are retained in the ledger. The strict continuity population and non-overlapping grid remain prespecified secondary checks.

Calibration uses original markets only: fit on May 1–2, select on May 3, then refit the chosen map on May 1–3. The newly selected contracts supply no calibration labels. Candidates are identity, an intercept-only log-odds adjustment, and a monotone sigmoid adjustment. The objective adds a small fixed penalty toward identity; the sigmoid slope stays positive. The mapping corrects probabilities rather than learning new ranking features.

Calibration used 3,101 fit rows/511 positives and 1,078 selection rows/170 positives. The data gate passed: True. Final map: sigmoid(1.000000 × logit(raw probability) + 0.000000). Original-model hash remained fixed throughout.

| Calibration candidate | May 3 log loss | Brier | Status |
|---|---:|---:|---|
| identity | 0.369738 | 0.110913 | scored |
| intercept | 0.370620 | 0.111162 | scored |
| sigmoid | 0.369860 | 0.111479 | scored |

## New-block results

Source capture completed 72/72 calibration files and 72/72 test files, downloading 577,223,596 archive bytes. Calibration retained 428,091 events; test capture retained 652,722. Test scope was 24,840 scheduled grids: 16,560 original-cohort and 8,280 new-cohort. Eligible results are conditional on valid observed endpoints.

| Cohort | Model | Rows / positives | Log loss ↓ | Brier ↓ | AP ↑ | AUC ↑ |
|---|---|---:|---:|---:|---:|
| original | activity_logit | 3617 / 793 | 0.532835 | 0.172189 | 0.304648 | 0.605112 |
| original | calibrated_hgb7 | 3617 / 793 | 0.496530 | 0.152235 | 0.474849 | 0.752449 |
| original | global_rate | 3617 / 793 | 0.552893 | 0.178420 | 0.219242 | 0.500000 |
| original | hgb7 | 3617 / 793 | 0.496530 | 0.152235 | 0.474849 | 0.752449 |
| original | market_rate | 3617 / 793 | 0.737787 | 0.190303 | 0.265870 | 0.569988 |
| original | updated_global_rate | 3617 / 793 | 0.536579 | 0.174325 | 0.219242 | 0.500000 |
| transport | activity_logit | 2006 / 682 | 0.740916 | 0.258879 | 0.380241 | 0.508877 |
| transport | calibrated_hgb7 | 2006 / 682 | 0.812621 | 0.259381 | 0.385730 | 0.519699 |
| transport | global_rate | 2006 / 682 | 0.778061 | 0.266769 | 0.339980 | 0.500000 |
| transport | hgb7 | 2006 / 682 | 0.812621 | 0.259381 | 0.385730 | 0.519699 |
| transport | market_rate | 2006 / 682 | 0.778061 | 0.266769 | 0.339980 | 0.500000 |
| transport | updated_global_rate | 2006 / 682 | 0.734010 | 0.255673 | 0.339980 | 0.500000 |

The frozen market-rate baseline falls back to its original global rate on unseen contracts. It is therefore not a separately adapted market-history baseline for the new cohort. The updated global control uses May 1–3 original-cohort labels, exactly the additional period available to calibration; no test labels enter any forecast.

| Date | Cohort | Rows | Raw LL | Calibrated LL | Updated constant LL |
|---|---|---:|---:|---:|---:|
| 2026-05-04 | original | 1147 | 0.499291 | 0.499291 | 0.582953 |
| 2026-05-04 | transport | 777 | 1.176981 | 1.176981 | 1.000936 |
| 2026-05-05 | original | 1267 | 0.575315 | 0.575315 | 0.598812 |
| 2026-05-05 | transport | 695 | 0.617979 | 0.617979 | 0.606285 |
| 2026-05-06 | original | 1203 | 0.410919 | 0.410919 | 0.426820 |
| 2026-05-06 | transport | 534 | 0.535784 | 0.535784 | 0.511851 |

## Prespecified secondary checks

| Cohort | Population | Rows / positives | Raw LL | Calibrated LL | Updated constant LL |
|---|---|---:|---:|---:|---:|
| original | strict_secondary | 500 / 50 | 0.212930 | 0.212930 | 0.341594 |
| original | nonoverlap | 609 / 135 | 0.511792 | 0.511792 | 0.540557 |
| transport | strict_secondary | 196 / 8 | 0.376754 | 0.376754 | 0.244816 |
| transport | nonoverlap | 310 / 105 | 0.810989 | 0.810989 | 0.731932 |

All secondary, per-market and fixed-bin calibration results are preserved. No cohort, day or model was chosen after seeing the test to retain a positive headline. A three-date study cannot establish reliable statistical significance; even the non-overlapping grid remains dependent within markets and calendar periods.

## Interpretation and next step

The new-cohort results contain only four eligible contracts out of ten selected: three political contracts and one crypto contract. Six contracts contributed no eligible endpoints; all remain in coverage accounting. This is a small, concentrated transfer test. Calibration performance and cross-market transfer are distinct findings. A mapping that helps the original cohort can fail on new markets because the relationship between raw scores and outcomes changes. Likewise, improvement over a stale prior can disappear against an updated prior. The full comparison is required before deciding whether any forecasting advantage is portable.

The loss of new-contract discrimination (AUC about0.520 versus0.752 on the original cohort) points to a transfer limitation beyond a simple probability offset. Positive-slope calibration cannot repair ordering. The next research option is broader, family-balanced development data and a frozen cross-family evaluation, using new periods. Keep May 4–6 fixed as an opened evaluation. Do not tune calibration, filters or markets on these outcomes. Any repair should use new development data and another untouched block. Before stronger paper claims or deployment, broaden metadata-defined market/calendar coverage, assess calibration by domain and source availability, and preserve missingness as an explicit limitation. The current experiment makes no news contribution claim and does not revise the original exact-price MAE result.

## New cohort

| Contract | Event-family ID |
|---|---|
| Will Michelle Bolsonaro qualify for Brazil's presidential runoff? | 45925 |
| Will FK Dinamo Makhachkala win on 2026-05-10? | 372093 |
| Will Perena launch a token by June 30, 2026? | 127107 |
| CR Brasil vs. Fortaleza EC: Both Teams to Score | 391216 |
| Will Vitória de Guimarães place 16th for the 2025-26 Primeira Liga season? | 337498 |
| Will Daddy Yankee perform at the 2026 FIFA World Cup Final halftime show? | 385789 |
| Will David Williams be the Republican nominee for Senate in Virginia? | 91333 |
| Club Aurora vs. CDT Real Oruro: Both Teams to Score | 385093 |
| Will Jennifer Sundt be the Republican Nominee for TX-38? | 200774 |
| Will Newcastle Red Bulls win? | 374012 |

A V01 output-save failure (NumPy boolean JSON serialization) was preserved. V02 changed only that serialization and wrote a separate calibration package. The saved map, updated rate and model/cohort hashes matched V01 exactly before any test retrieval. No method or candidate changed.

## Reproducibility

Verified 182 manifest entries. Original model weights, completed evaluation results and live services were unchanged. Identity-calibration invariance, positive-slope monotonicity, bounded probabilities and synthetic underprediction correction passed. The source pipeline filtered 2,948,579 excluded-cohort May rows after physical decoding and before retained economic analysis. No protected evaluation-period data was read.

- [Frozen protocol](eventx/release/v7/calibration_transport_20261025_v02/protocol.json)
- [Frozen cohorts](data/v7/calibration_transport_20261025/cohort/cohorts.json)
- [Calibration selection](data/v7/calibration_transport_20261025/calibration_v02/selection.json)
- [Frozen probability mapping](data/v7/calibration_transport_20261025/calibration_v02/frozen_calibration.json)
- [Canonical test result](data/v7/calibration_transport_20261025/evaluation/result.json)
- [Per-market/day results](data/v7/calibration_transport_20261025/evaluation/groups.json)
- [Calibration bins](data/v7/calibration_transport_20261025/evaluation/calibration_bins.json)
- [All matched predictions](data/v7/calibration_transport_20261025/evaluation/predictions.parquet)
- [Grid ledger and missingness](data/v7/calibration_transport_20261025/evaluation/grid_ledger.parquet)
- [Delivery manifest](data/v7/calibration_transport_20261025/delivery_manifest.json)
