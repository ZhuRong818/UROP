# EventX v2.2 Option-A October pilot amendment

**Protocol ID:** `eventx-v2.2-october-pilot-fixes-20260817`  
**Created:** `2026-08-17T05:50:49Z`  
**Deadline:** `2026-10-31T23:59:59Z`  
**Status:** preregistered before any v2/v2.1/v2.2 development or holdout labels  
**Prospectively supersedes:** `eventx-v2.1-october-deadline-20260731`

## Reason for this version

The v2.1 coordination plan exposed a zero-buffer timing conflict: its development
window ended at the exact instant the holdout began, although exact reconciliation,
label construction, evaluation, and candidate freezing were still required afterward.
A label-blind review also identified three measurement/claim issues before any
development labels, prevalence, predictions, or metrics existed:

1. the executable fallback is B1 market plus news versus B0 market-only because the
   independent KOL-v2 association audit failed its fixed gates;
2. midpoint-first pricing would mix price measurement methods across venues given
   uneven point-in-time orderbook coverage; and
3. absolute-jump probability supplies no trading direction, so a directional P&L
   claim is not defined.

This amendment resolves those issues prospectively. The user explicitly authorized
Option A and this new protocol on 2026-08-17. The sealed v2 and v2.1 files remain
unchanged evidence.

## Scientific positioning

The October result is an **EventX prospective protocol-validation pilot**. Its active
question is:

> Does point-in-time news improve prediction of future absolute prediction-market
> repricing beyond market history on the frozen 14-market cohort?

The confirmatory comparison is B1 market plus core news versus B0 market-only.
KOL-v2 is ineligible because its fresh association audit achieved precision 0.8378
and hard-candidate recall 0.6327, below the fixed 0.85 and 0.90 gates. No KOL-v3,
B2, B3, KOL null, or T5 work is on the October critical path. This pilot cannot
support the claim that KOL activity adds information beyond market history and news;
that question is reserved for a later, freshly preregistered benchmark.

## Revised half-open UTC schedule

| Period | Start | End exclusive | Permitted use |
|---|---|---|---|
| Warmup | 2026-07-31 | 2026-08-01 | Retained from v2.1; trailing inputs and collector validation |
| Selection | 2026-08-01 | 2026-08-08 | Retained completed label-blind selection; cohort is not rerun |
| Development | 2026-08-08 | 2026-09-28 | B0/B1 labels, folds, model comparison, bootstrap and robustness |
| Reconciliation/freeze buffer | 2026-09-28 | 2026-10-01 | Exact data reconciliation, integrity checks, candidate/evaluator freeze; no holdout access |
| Confirmatory holdout | 2026-10-01 | 2026-10-22 | Sealed collection; one frozen candidate evaluated after closure |
| Finalization | 2026-10-22 | 2026-11-01 | One-shot result, receipt, report, datasheet and evidence package |

The development cutoff is now `2026-09-28T00:00:00Z`, leaving a 72-hour buffer.
The candidate, transforms, training cutoff, input hashes and evaluator must freeze no
later than `2026-10-01T00:00:00Z`. If that deadline cannot be met, the cycle is
`incomplete_due_to_timing`; holdout data remain sealed and are not used to finish
model selection.

## Inherited frozen artifacts

The following label-blind results are reused unchanged:

- the verified 14-market v2.1 cohort and its exact selected-market hash;
- accepted `eventx-v2.1-taxonomy-v7` categories;
- the accepted news-v1 association path from the source-specific v2.1 audit;
- the failed KOL-v1/KOL-v2 dispositions and cumulative 450 opened-pair exclusions;
- Lumid-only external observational sourcing;
- the B0/B1 feature definitions, standardized logistic SGD learner, training-only
  transformations, five purged expanding folds, metrics, bootstrap and promotion gates;
- the October 1–21 holdout, one-candidate limit, one-shot evaluator and receipt; and
- the prohibition on v1 OOT reuse or tuning.

The cohort and taxonomy are not reselected because of the shorter development cutoff.

## Price construction

The primary price is uniform across venues:

1. use the latest canonical-YES trade price at or before prediction time `t`;
2. carry it forward on the evaluation grid while recording `price_age_minutes`; and
3. clip to `[0.0001, 0.9999]` before converting to log-odds.

The primary labels and B0/B1 comparison never switch between midpoint and last trade.
Contemporaneous Lumid L2 midpoint is a separately named robustness/measurement ceiling
only when timestamped coverage is valid. Candle close remains a separate fallback
diagnostic and cannot enter the confirmatory dataset silently.

## Label threshold semantics

For horizon `h` minutes:

```text
fwd_dy_h(t) = price_logodds(t + h) - price_logodds(t)
threshold_h(t) = 4 * sigma_1m_240(t) * sqrt(h / 30)
y_jump_h(t) = 1[abs(fwd_dy_h(t)) >= threshold_h(t)]
```

`sigma_1m_240(t)` is the trailing standard deviation of one-minute log-odds changes
using only values at or before `t`, with at least 30 changes. The coefficient `4` is
an inherited **30-minute anchor expressed in units of trailing one-minute volatility**.
It is not four standard deviations of a 30-minute return. Equivalently, under an
independent-increment scaling comparison, the 30-minute threshold is approximately
`4 / sqrt(30) = 0.7303` horizon standard deviations. This amendment clarifies the
estimand; it does not change the frozen threshold formula in response to prevalence.

No label prevalence may be inspected to choose another coefficient or scaling rule.
A future four-horizon-sigma target would be a different experiment using
`4 * sigma_1m_240(t) * sqrt(h)` and would require a new protocol and power analysis.

## Eligibility and price-freshness robustness

The v2.1 primary pre-`t` eligibility rule is retained: at least three trades and 100
notional in the trailing 240 minutes, valid price/volatility, and terminal/public-
resolution exclusions. Forward liquidity remains prohibited.

Two robustness subsets are now fixed before labels:

- `price_age_minutes <= 30`; and
- `price_age_minutes <= 60`.

Report their row/market/venue/positive counts and B0/B1 paired metrics. These subsets
cannot rescue a failed primary gate or become the holdout candidate definition.
Also report performance on rows with a canonical-YES trade in the current five-minute
bucket as a descriptive trade-arrival diagnostic.

## Power and uncertainty interpretation

The relevant independent breadth is 14 markets, not the potential count of five-minute
rows. Before labels, run synthetic market-cluster simulations across plausible event
rates and intra-market dependence. They may diagnose power and interval width but may
not tune labels, features, gates, or learners.

The existing within-market moving-block bootstrap estimates uncertainty conditional
on the frozen cohort. It does not support population-wide prediction-market claims.
Market-cluster or hierarchical uncertainty is deferred to Stage C when enough markets
exist.

## Economic-significance disposition

The v2.2 target predicts absolute movement, not direction. Therefore the v2.1
directional fee/spread P&L exercise is removed from the October scientific completion
criteria. If B1 promotes, v2.2 may report non-trading quantities such as alert rate,
lead time, calibration and decision-curve/net-benefit summaries under thresholds
frozen on development data. It may not report directional trading profitability.

A later signed-return or direction-classification experiment must be separately
preregistered before its labels are inspected.

## Lumid data gate and rehearsal

All external observations must originate from valid Lumid endpoints recorded in the
umbrella plan. Before generating labels, run the complete reconciliation machinery on
an already elapsed development subwindow. The rehearsal must test all 14 markets,
canonical-YES mappings, endpoint pagination/truncation, duplicates, malformed and
future timestamps, zero-record markets, per-day gaps, news-query truncation, hashes,
and provenance. A rehearsal pass does not waive the final exact-window gate.

## Integrity and confirmatory status

This amendment was authorized before development and holdout labels, prevalence,
predictions, or metrics were created or inspected. Changes were motivated by calendar
logic, upstream association validity, measurement consistency and target/action
alignment—not by v2.2 outcomes. Any later change to dates, price source, label
definition, eligibility, comparison, model, gate, or holdout requires another protocol
ID before the affected labels are inspected.

