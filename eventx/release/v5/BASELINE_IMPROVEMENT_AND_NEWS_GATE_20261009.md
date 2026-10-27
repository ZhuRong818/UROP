# V5 opened-data baseline improvement and news gate — 9 October 2026

## Measured result

The frozen V5 algorithm audit compared models on the same 364,903 opened
development rows from 1,135 contracts, with the same capped training and tuning
indices across model families. Its shallow boosted tree improves materially over
the matched L2 logistic market-only baseline. A new paired diagnostic uses only
the audit's frozen predictions and excludes terminal metadata from both models:

| No-terminal market model | Log loss | Brier | Average precision |
|---|---:|---:|---:|
| L2 logistic | 0.451070 | 0.140952 | 0.226649 |
| Shallow boosted tree | 0.407391 | 0.131106 | 0.334964 |

The paired log-loss improvement is **0.043679 nats/row (9.68%)**; Brier improves
by 0.009845 and average precision rises by 0.108315. Log-loss gains in forward
folds 3, 4 and 5 are 0.041469, 0.035980 and 0.053605. A 1,000-resample
market-cluster bootstrap gives a descriptive interval of [0.039575, 0.047682].
This is stronger evidence for market-model nonlinearity than for news value.

The original audit's terminal-including market comparison also favored the tree:
log loss 0.405075 versus 0.448075 for matched linear, improvement 0.043000,
descriptive interval [0.039091, 0.046615]. The no-terminal result shows that
the principal gain survives removal of the terminal predictor. It does not prove
that upstream eligibility or associations were point-in-time clean.

## News increment against the stronger baseline

In that same audit, adding exposure/count/age to the tree market model changed
log loss by **-0.00002347** nats/row in the improvement direction (slightly
worse); the descriptive interval includes zero. Adding relevance–novelty to
the timing model produced exactly identical tree predictions. Linear and spline
semantic increments were also negative overall. The V3.1 historical B1
news-count candidate had previously failed its five development hypotheses.
Thus there is **no demonstrated news-added improvement over a market-only
baseline**. A positive market-only algorithm gain cannot be reported as news lift.

## Method and decision

The new diagnostic computes rowwise paired log loss from the frozen
`predictions.npz`, then subtracts tree loss from linear loss. It resamples
1,135 market IDs with replacement 1,000 times using NumPy seed 907, summing
loss differences and row counts within sampled markets; the 2.5th and 97.5th
percentiles form the interval. Fold results use the frozen fold IDs. Source
hashes were checked against the frozen manifest. Exact output is in
`data/v5/no_terminal_baseline_diagnostic_20261009/report.json`; the parent
audit is `data/v5/algorithm_audit_20260907/report.json` and
`eventx/release/v5/ALGORITHM_AUDIT_20260907.md`.

This is an opened-data, post-selection descriptive diagnostic. The market
bootstrap does not account for model search, related event families or shared
calendar shocks. The original comparison used 60,000-row training/tuning caps;
its historical semantic representation used later development text. No model
was refit or promoted, and the controlling V5 protocol and frozen V4
prospective study are unchanged.

For a credible news gain, certify historical source windows and point-in-time
article/market versions, validate article-to-contract links and family
boundaries, then freeze one news candidate and compare it with a strong
market-only control on an untouched interval. V6 currently has zero certified
predictive contract-days out of 8,844, so its opened semantic labels cannot
support that fit. The V4 prospective holdout closes 30 October and remains
sealed until its prescribed audit, receipt and one-shot evaluation sequence.
