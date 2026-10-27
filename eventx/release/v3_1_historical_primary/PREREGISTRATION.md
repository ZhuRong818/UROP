# EventX v3.1 historical primary study

Protocol ID: `eventx-v3.1-historical-primary-20260902`

This is a transparent pre-outcome revision of the EventX v3 historical protocol.
The original v3 cohort was frozen before development trades were retrieved, and its
independent data gate subsequently failed because Lumid contained 204,069 Kalshi
rows with zero executed contracts. After excluding those non-executions, 19 of
4,670 frozen markets no longer satisfied the original activity rule: two had fewer
than 100 valid executions, and 17 had fewer than 10 valid active UTC days.

No label, forward price change, model result, historical-holdout covariate, or
historical-holdout outcome was inspected. The failed v3 protocol and gate remain
immutable. V3.1 removes exactly those 19 activity-invalid markets, updates the
stored development activity counts for the retained markets, and changes nothing
else in the confirmatory design.

The corrected cohort contains 4,651 markets: 3,832 Kalshi and 819 Polymarket.
Every retained market has at least 100 positive-notional canonical-YES development
executions on at least 10 UTC days. Zero-notional records remain preserved in the
raw Lumid export but are excluded before all price, liquidity, feature, volatility,
and label calculations.

The research question, point-in-time news clock, development and holdout windows,
canonical-YES price definition, 30-minute label, B0 and B1 features, fixed learner,
five purged folds, H1–H5 promotion gate, bootstrap, and one-shot holdout rule are
unchanged. The prospective EventX v2.3 study also remains unchanged as the secondary
replication. The machine-readable `protocol.json` controls.
