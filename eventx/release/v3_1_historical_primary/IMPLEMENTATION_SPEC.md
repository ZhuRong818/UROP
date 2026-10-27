# EventX v3.1 frozen implementation specification

Frozen before development label construction and before any model result.

This specification resolves implementation details left open by the machine-readable
protocol without changing the research question, label, features, validation folds,
learner family, or H1–H5 promotion gate.

## Source normalization and time

- Apply the three preserved v3 source amendments: composite execution identity,
  exact-duplicate collapse, and exclusion of zero-notional rows.
- Order executions by market, exact venue timestamp, then immutable source-query
  ordinal. If several executions share a timestamp, the final source-ordered
  execution supplies the last-trade price.
- Evaluate five-minute UTC grid points at their exact boundary. A trade later within
  that minute is not visible at the boundary.
- Use left-open, right-closed trailing windows `(t-window, t]`.
- Use population standard deviation (`ddof=0`) of carried-forward one-minute
  log-odds changes. A minimum of 30 changes is required. When sigma is zero, the
  inherited jump label is zero.
- A frozen terminal timestamp earlier than the first valid development execution is
  contradicted metadata and is ignored. Otherwise, require the full 30-minute label
  horizon to end no later than the known terminal time. All contradictions are
  retained in the preparation report.

## News

- Use the frozen lexical association rule on headline plus summary and the
  conservative `available_at` clock.
- Count one stable document identity once at its earliest conservative availability;
  retain the preregistered conflict-identity quarantine.
- The frozen infrastructure has no canonical event-market financial-symbol map, so
  `news_symbol_mapped` is constant zero, as in the v2.3 readiness contract. It is
  retained in B1 for schema compatibility and receives a unit scale when constant.

## Learner

- Use scikit-learn 1.7.2 `SGDClassifier` with `loss="log_loss"`, `penalty="l2"`,
  `alpha=0.0001`, constant `eta0=0.02`, intercept enabled, no class weighting, and
  no parameter averaging.
- Apply `log1p` to trade-count, notional, and news-count features; all other features
  use the identity transform. Fit population means and standard deviations only on
  each training fold; replace a zero scale by one.
- For each seed 11, 23, and 47, shuffle training indices with NumPy PCG64 at the
  start of each of eight epochs and stream them in 65,536-row blocks through
  `partial_fit`. Average the three predicted probabilities arithmetically.
- Encode venue as Kalshi = 0 and Polymarket = 1.

## Uncertainty

- The confirmatory H4 interval uses 5,000 paired circular moving-block bootstrap
  samples of the row-level Brier-loss improvement, stratified by market, with 72
  ordered eligible five-minute rows per block (nominally 360 minutes), seed 61.
- The bootstrap resamples each market back to its original eligible row count. The
  Brier interval is confirmatory; an AP bootstrap is not required for promotion and
  is omitted at this scale. Aggregate and fold AP remain confirmatory metrics.

The implementation and synthetic contract tests are hash-locked before the first
development label artifact is written.
