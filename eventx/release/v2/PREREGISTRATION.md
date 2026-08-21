# EventX v2 prospective preregistration

**Protocol ID:** `eventx-v2-preregistered-20260731`  
**Created:** 2026-07-31T06:30:00Z  
**Status:** preregistered before v2 label inspection  
**Prior study:** EventX v1 frozen pilot, closed and holdout consumed

## 1. Research objective

EventX v2 tests whether point-in-time KOL activity contains stable incremental
information about future prediction-market repricing after conditioning on
observable market history and news.

The primary confirmatory question is:

> Does B3 (market + news + sparse residualized KOL) improve both average precision
> and Brier score over B1 (market + news) for 30-minute jump prediction?

Secondary tasks are:

- **T1:** jump/early-warning prediction at 5, 30, 120, 360, and 1,440 minutes;
- **T3:** incremental news and KOL information under the fixed B0–B3 ladder;
- **T5:** per-KOL out-of-sample lift with false-discovery-rate control, only if the
  primary B3 promotion gate passes; and
- a conservative economic-significance check, only for a promoted candidate.

The study estimates predictive value, not causal influence.

## 2. Separation from v1

The following v1 evidence may motivate this protocol:

- KOL association rule v3 passed its relevance audit;
- aggregate KOL features were temporally unstable;
- 11 of 14 KOL coefficients changed sign across v1 folds;
- core news produced a small AP gain but worse Brier score; and
- v1 B0 showed out-of-time ranking discrimination but only marginal Brier
  improvement.

The following uses are prohibited:

- reusing either v1 test block for model selection;
- changing a v2 choice because of v1 OOT row-level outcomes;
- rerunning the consumed v1 OOT evaluator;
- treating the current bulk fetch as a labeled v2 experiment before this
  preregistration; or
- modifying any v1 frozen artifact in place.

No v2 labels, prevalence, jump counts, model metrics, or candidate comparisons were
inspected before this protocol was written.

## 3. Prospective windows

All boundaries are UTC and half-open.

| Period | Start | End exclusive | Permitted use |
|---|---|---|---|
| Warmup | 2026-07-31 | 2026-08-01 | Trailing features only; no labels |
| Selection | 2026-08-01 | 2026-08-15 | Activity/coverage and cohort selection; no outcome labels |
| Development | 2026-08-15 | 2026-11-01 | Labels, folds, model development, nulls |
| Confirmatory holdout | 2026-11-01 | 2026-12-01 | One frozen candidate, exactly once |

The holdout must remain inaccessible until a candidate and evaluator are frozen. If
the required data are not complete by the stated boundary, v2 is reported as
incomplete; the dates are not moved after label inspection.

## 4. Scope and cohort selection

### Venues and outcomes

- Venues: Polymarket and Kalshi.
- Outcomes: binary contracts only, one canonical YES outcome per market.
- Primary pooled model includes a venue indicator.
- Venue-stratified results are mandatory; a venue is not silently dropped.
- A metric that is undefined because a stratum contains one label class is reported
  as unavailable, not replaced with another sample.

### Label-blind selection

Cohort selection uses only activity observed during the selection window:

- at least 100 canonical-YES trades;
- at least 1,000 units of price-times-size/count notional;
- at least three active UTC days;
- last trade no more than 72 hours before the selection cutoff;
- scheduled close at or after 2026-11-01; and
- no known resolution before the selection cutoff.

Eligible markets receive the fixed density score:

```text
log1p(trades) + log1p(notional) + 0.1 * active_hours
```

Within each `(venue, corrected_category)` stratum, select the top 40 markets by
descending density score, breaking ties by ascending market ID. Do not refill a
short stratum from another category. The maximum cohort is 400 markets:
2 venues × 5 categories × 40.

The frozen categories are `politics`, `crypto`, `sports`, `macro`, and `other`.
They are produced under `TAXONOMY_GUIDE.md`. Category correction may use market
question/metadata but never prices, future outcomes, labels, or model performance.

## 5. Prediction unit, price, labels, and eligibility

The prediction unit is `(venue, market_id, canonical_yes_outcome_id, t)` at a
5-minute cadence.

Price priority is:

1. contemporaneous L2 midpoint when a timestamped snapshot exists;
2. last trade price otherwise; or
3. candle close only in a separately reported historical robustness track.

Every row records `price_source`. Prices are clipped to `[0.0001, 0.9999]` before
conversion to log-odds.

For horizon \(h\), define:

```text
fwd_dy_h(t) = logodds_price(t+h) - logodds_price(t)
threshold_h(t) = 4 * sigma_1m_240(t) * sqrt(h / 30)
y_jump_h(t) = 1[abs(fwd_dy_h(t)) >= threshold_h(t)]
```

`sigma_1m_240(t)` is the trailing standard deviation of one-minute log-odds
changes using only observations at or before \(t\), with at least 30 changes.
The primary horizon is 30 minutes; all other horizons are secondary.

Eligibility is determined at \(t\):

- at least three trades in the trailing 240 minutes;
- at least 100 units of notional in the trailing 240 minutes;
- a valid price and volatility estimate;
- not mechanically settled or publicly resolved; and
- not a boundary-price row near scheduled close or at/after a known resolution.

Forward liquidity must not determine eligibility. `resolution_ts` may filter rows
at or after resolution but is never a feature.

## 6. Feature and model ladder

All time-varying features use information timestamped at or before \(t\).

### B0 — market-only reference

The reference retains the 11 v1 families:

- price log-odds;
- momentum over 5, 30, and 120 minutes;
- realized volatility over 30 and 240 minutes;
- trade counts over 60 and 240 minutes;
- notional over 60 and 240 minutes; and
- minutes since the latest trade.

Timestamped spread, depth, order-flow imbalance, open interest, and a venue flag may
be added only as a separately named B0+microstructure ceiling. They are not added
to the confirmatory B0/B1/B3 comparison unless availability exceeds 90% in every
venue during the label-blind selection window and that decision is frozen before
development labels are opened.

### B1 — market + core news

B1 adds four fixed news features:

- `news_article_count_60m`;
- `news_article_count_360m`;
- `news_article_count_1440m`; and
- `news_symbol_mapped`.

### B2 — market + sparse KOL diagnostic

B2 adds exactly six KOL features:

- `kol_tweet_count_30m`;
- `kol_tweet_count_360m`;
- `kol_unique_handles_30m`;
- `kol_unique_handles_360m`;
- `kol_handle_entropy_24h`; and
- `kol_minutes_since_latest`.

B2 is diagnostic and is not the primary T3 comparison.

### B3 — market + news + residualized sparse KOL

For each outer fold, each of the six KOL features is residualized using a ridge
linear model fitted only on that fold's training rows, with B0 and B1 predictors as
inputs and fixed ridge penalty 1.0. The fitted transformation is applied to the
validation rows. The final model includes B0, B1, and the six residualized KOL
features.

No activity gate, market exclusion, feature deletion, or alternate time window may
be selected after development results are observed.

### Learners

The confirmatory learner is standardized logistic SGD:

- `log1p` transform for count and notional families;
- identity transform otherwise;
- 8 epochs;
- learning rate 0.02;
- L2 penalty 0.0001; and
- shuffle seeds 11, 23, and 47.

Predictions are averaged across the three fixed seeds. Standardization and
residualization are fitted on training rows only.

A fixed LightGBM ceiling may be reported as exploratory but cannot become the
one-shot confirmatory candidate.

## 7. Development splits

Use five expanding-window outer folds over the development period.

- Purge each fold by the evaluated horizon.
- Divide markets into five deterministic groups by
  `sha256(venue + ":" + market_id) mod 5`.
- In outer fold \(k\), validate only on the later time block and market group \(k\).
- Training uses earlier eligible rows from the other four groups.
- Report a temporal-only robustness result using all markets, but do not use it for
  promotion.

All models in a comparison use identical validation keys. Prevalence, feature
scalers, residualizers, and model parameters are learned within the training side
of each fold.

## 8. Metrics, uncertainty, and promotion

Primary metric: average precision (AP).  
Calibration metric: Brier score.  
Secondary metrics: ECE with 10 equal-frequency bins, ROC-AUC, lead time, and
calibration slope/intercept.

For candidate \(C\) over reference \(R\):

```text
delta_ap = AP(C) - AP(R)
brier_improvement = Brier(R) - Brier(C)
```

Use 5,000 paired circular moving-block bootstrap samples, stratified by market,
with 360-minute blocks and seed 61.

B3 passes the primary promotion gate only if all conditions hold versus B1:

1. aggregate `delta_ap > 0`;
2. aggregate `brier_improvement > 0`;
3. both deltas are positive in at least four of five outer folds;
4. the 95% bootstrap lower bound for Brier improvement is above zero; and
5. Brier improvement is not negative in either venue stratum.

If B3 fails, it is rejected and no alternative KOL specification is selected from
the same development results. B1 may replace B0 only under the same gate versus B0.
Exactly one candidate—or B0 if none passes—is frozen for the holdout.

## 9. Null tests

Run 500 fixed-seed permutations for each promoted KOL comparison:

- shuffle tweet-to-market assignments within corrected category, venue, and UTC
  calendar day; and
- shift KOL timestamps by a market-specific offset drawn from ±1–7 days while
  preserving within-market activity patterns.

The observed B3-over-B1 deltas must exceed the 95th percentile of both null
distributions. Null tests are development-only.

## 10. T5 and economic significance

T5 runs only if B3 passes the primary promotion gate.

- Estimate per-KOL out-of-fold lift by ablating that KOL's associated activity.
- Use market-stratified block bootstrap/permutation p-values.
- Apply Benjamini–Hochberg correction across all tested handles at FDR `q=0.05`.
- Report fold stability and corrected-category/venue coverage.

The economic-significance check runs only for a promoted candidate. It charges
venue fees plus half-spread, prohibits better-than-mid fills, reports turnover and
capacity assumptions, and is explicitly not a deployable-strategy claim. Cost
scenarios must be fixed before the confirmatory holdout is opened.

## 11. Confirmatory holdout

Before 2026-11-01:

1. freeze the selected cohort;
2. freeze association rules and audits;
3. freeze features, transforms, learner, seed ensemble, and evaluator;
4. freeze the final training cutoff and expected input hashes; and
5. create a manifest stating that holdout labels and prevalence are uninspected.

The holdout evaluator may create one result and one consumption receipt. It must
refuse if a result or receipt already exists. No post-holdout tuning, alternative
candidate, threshold change, subgroup rescue, or rerun is permitted.

## 12. Planned release

The Feature Track will contain precomputed features, identifiers, labels, frozen
split indices, association tables, evaluation code, and a leaderboard contract.
The Rehydration Track will contain permitted document IDs and a simple text
baseline, subject to upstream rights.

All public distribution remains conditional on licensing, privacy, dual-use,
secret-scan, clean-room reproduction, maintenance, and archival review. Raw
social-media/news text is excluded unless redistribution rights are documented.

## 13. Deviations

Any deviation must be recorded before examining the affected labels or metrics,
must state whether it changes confirmatory status, and must create a new protocol
version. The current protocol intentionally uses a prospective three-month cycle
rather than the research plan's aspirational 12–18-month window because uniformly
retained trade-level Polymarket data are unavailable that far back. Results must be
described as prospective v2, not the completed deep-historical benchmark.
