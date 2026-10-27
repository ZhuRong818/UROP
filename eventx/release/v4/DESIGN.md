# EventX v4 confirmatory design freeze

Design ID: `eventx-v4-confirmatory-20260902`

Status: **analysis and feature design frozen before any v4 result; future cohort and
calendar window remain pending a label-blind Lumid feasibility gate.** The completed
v3.1 results are known and are treated only as discovery evidence. No future v4
price, label, prediction, or metric has been inspected.

## Research question

Does conservatively point-in-time, market-relevant news quality—measured by semantic
relevance, market-relative novelty, and cross-publisher diffusion—provide incremental
information about 30-minute absolute prediction-market repricing beyond executed
market history?

This is a predictive incremental-information question. It is not a causal claim.
Lumid contains no article engagement, sharing, repost, or view counts in the validated
export, so v4 does **not** claim to measure social virality. KOL evidence remains
deferred after the earlier frozen KOL association audit failed.

## Study roles and leakage boundary

- `[2026-05-17, 2026-07-22)` is outcome-opened discovery/training data.
- The completed v3.1 historical holdout is consumed and is never reused for v4
  confirmation.
- A new, strictly later, fixed future interval will be the sole confirmatory holdout.
- Its exact market cohort, start, and end will be frozen only after a label-blind
  source-feasibility audit. The audit may inspect market identity, question, venue,
  source timestamps, activity counts, and scheduled terminal time; it may not inspect
  prices, forward returns, labels, predictions, prevalence, or metrics.
- A consumption receipt must be written before any confirmatory label summary or
  performance metric. Confirmatory evaluation is one shot.

## Data source and point-in-time policy

External observations must come from valid Lumid FinData endpoints. The primary
warehouse source is `/retrieve` over `news.articles`, `provenance.runs`,
`prediction_markets.kalshi_markets`, `prediction_markets.kalshi_trades`,
`prediction_markets.polymarket_markets`, and
`prediction_markets.polymarket_trades`. The valid `/api/v1/lqt/markets` roster may
be used only for label-blind enumeration; warehouse/detail reconciliation is required
before a market enters the confirmatory cohort.

News availability is
`max(published_at, ingest_ts, joined run.started_at, joined run.ended_at when present)`.
Rows with missing run start, inconsistent run ordering, conflicting publication
timestamps for the same normalized URL, or availability lag over 24 hours are excluded
from the primary analysis. Duplicate identities count once at their earliest valid
conservative availability. The feature window is `(t-window, t]`. Appending future
articles must not alter any earlier feature.

## Outcome and eligibility

The primary price is the latest canonical-YES executed trade at or before each
five-minute UTC grid time. Prices are clipped to `[0.0001, 0.9999]` before log-odds.
Candles and order-book midpoints are excluded from the primary construction.

The inherited 30-minute target is retained for comparability:

`Y(t) = 1[abs(logodds(p(t+30m)) - logodds(p(t))) >= 4 * sigma_1m,240(t)]`.

This is a preregistered heuristic in one-minute sigma units, not a Gaussian
four-horizon-standard-deviation event. Eligibility requires at least three
positive-notional executions and payout notional 100 in the trailing 240 minutes,
at least 30 volatility observations, a known source/terminal window, and current
price age at most 30 minutes. A 60-minute freshness analysis and a separate
trade-arrival diagnostic are robustness analyses and cannot rescue the primary result.

## Frozen news construction

Association membership is the unchanged, previously audited
`eventx-v2.1-news-v1-source-path` lexical rule. The input text is headline plus
summary. Full article body is unavailable in the source-valid export.

The semantic model is fitted only on discovery news: word unigram/bigram TF-IDF,
lowercase, Unicode accent stripping, `min_df=3`, `max_df=0.995`, at most 50,000
features, sublinear term frequency, followed by 64-component randomized truncated
SVD (`random_state=73`, five iterations) and row L2 normalization.

- Relevance is clipped cosine similarity between a market question and an associated
  article in the frozen LSA space.
- Novelty is one minus the maximum clipped cosine similarity to the 20 preceding
  associated articles for that market within seven days. With no prior article it is 1.
- Cross-publisher diffusion is present when at least two case/whitespace-normalized
  publishers have reported the same token-normalized exact headline within the prior
  24 hours as of the article's conservative availability time.
- Publisher diversity is the exact number of distinct normalized publishers in the
  feature window. Subjective publisher-entity merges are not allowed.

## Nested models

All four models use the same rows, folds, outcome, and standardized logistic-SGD
learner. Count, notional, relevance-mass, publisher-count, and diffusion-count
features receive `log1p`; other features use identity transformation. Standardization
is fitted on training rows only.

- **B0:** 12 inherited market-history features.
- **B1:** B0 plus associated article counts over 60, 360, and 1,440 minutes and the
  inherited symbol-mapped indicator.
- **B2:** B1 plus relevance mass and relevance-times-novelty mass over the same windows.
- **B3:** B2 plus distinct publishers and cross-publisher report counts over the same
  windows.

The learner uses unweighted logistic loss, L2 `0.0001`, constant learning rate `0.02`,
five epochs, batch size 65,536, and seeds 11, 23, and 47. Predictions are the arithmetic
mean of the three seed probabilities. Historical exploration uses the inherited five
purged expanding-time/disjoint-market-group folds. After exploration, all four models
are fitted on all eligible discovery rows and hash-frozen before the future holdout.

## Confirmatory estimand and decision rule

The sole primary contrast is B3 versus B0 on identical future rows. The primary
estimand is mean per-row information gain:

`mean(log_loss(B0) - log_loss(B3))`.

A positive scientific result requires all of:

1. point estimate at least `0.001` nats per eligible row;
2. lower bound of the paired 95% event-cluster/time-block bootstrap interval above 0;
3. Brier improvement `Brier(B0)-Brier(B3) >= -0.0005`;
4. no eligible venue with at least 30 event clusters and both outcome classes has a
   negative point estimate.

The bootstrap resamples market event clusters and circular 360-minute within-market
blocks with 5,000 replicates and seed 61. If an input needed for a required criterion
is undefined, the positive decision is not supported. B1 and B2 contrasts explain the
incremental contribution of volume and quality/diffusion but are secondary and do not
create additional primary claims. Average precision, ROC AUC, calibration, alert rate,
category results, the 60-minute freshness set, and publication-time-only features are
secondary or robustness analyses and cannot reverse the primary decision.

## Claim boundary

A passing result supports only prospective incremental prediction for the frozen
cohort, time interval, source, target, and model family. A null result is a valid
finding and does not prove that all news is uninformative. Neither result supports a
causal claim, a KOL claim, a social-virality claim, or generalization to all prediction
markets.

