# EventX next-cycle study specification (DRAFT, not frozen)

28 October 2026. A proposal for a separately authorized research cycle, written after the post hoc
robustness checks (`data/v7/dependence_coverage_20261028/result.json`) and the research-gap assessment
(`EVENTX_RESEARCH_GAP_ASSESSMENT_20261028.md`). Nothing here is frozen, no data has been collected for it,
and it does not alter the V02b, V4 or late-June evaluations. Freezing it (with hashes and a manifest) would
start the new cycle, which needs the user's explicit authorization.

## 1. Primary question

When does information pooled across contracts add value beyond each contract's own available history?
Operationally:

On contracts and dates never used before, does a learned quote-state model forecast whether the 30-minute
midpoint differs **beyond an online contract-rate reference** that uses only outcomes already matured at
decision time?

Motivation: on 8–14 June the frozen booster had log loss 0.4208 against 0.4231 for that online rate
(gain 0.002 nats, contract CI [−0.028, 0.033], contract × date CI [−0.040, 0.041]; AUC 0.827 vs 0.824).
This is consistent with, but does not establish, persistent contract-level activity explaining much of its
14.9% gain over activity logistic regression; nor does it show equivalence. This is now the sharpest open
question, and the current cohorts cannot answer it.

## 2. Hypotheses (one primary, registered in advance)

- **H1 (primary).** A booster that receives the online rate as an input (`hgb+rate`) has lower matched log
  loss than the online rate alone; pass requires a contract × date two-way bootstrap 95% lower bound > 0.
- H2 (secondary). Attribution: in a learner × input factorial (below), nonlinearity adds to the matched-input
  logistic model on the same inputs.
- H3 (secondary). Cold start: the gain over the online rate (which starts at its global prior) is largest in a
  contract's first hours, when the rate has little contract-specific history (stratified by matured-outcome count: 0, 1–11, 12–47, ≥48).

## 3. Models and baselines (all fitted on development data only)

| Role | Model | Inputs |
|---|---|---|
| Reference | global rate; frozen-style shrunk contract rate | none |
| Reference | **online contract rate** (pseudocount 20 toward global rate; maturity lag 35 min) | own matured outcomes |
| Reference | **recency-weighted contract rate** (half-life or window prespecified on new development data only) | own matured outcomes |
| Factorial | logistic (L2), spline/GAM, HGB | (a) the 9 activity inputs; (b) the full point-in-time set |
| Factorial | each of the three above | (a) or (b) plus the online rate(s) and matured-outcome count, consistently in every arm |
| Candidate | `hgb+rate` = HGB on (b) plus rate | as above |

Matched tuning: each learner gets the same number of configurations (e.g. 20), chosen on purged, embargoed
forward folds over development dates, with identical rows and preprocessing. The pseudocount and lag of the
online rate are fixed at 20 and 35 minutes (not tuned), as in the post hoc analysis.

Calibration: one prespecified variant (isotonic or Platt on a dedicated last development fold) is scored as a
secondary arm, never replacing the uncalibrated primary.

## 4. Data and cohorts

- New event families and dates after the live window. Contracts selected from metadata only, as of selection
  time (recorded snapshot), before any price is read; one contract per event in the primary cohort.
- Development: at least four weeks; test: at least four further weeks, never opened during development.
- Prespecified strata: category (keyword rule frozen in advance), time to listed end, liquidity tertile.
- Report coverage alongside every score: issued/scheduled, decomposed as in the post hoc analysis
  (after listed end; inactive contract-day; within active contract-day).

## 5. Sample size (cluster-level precision planning)

From 8–14 June, the contract-clustered standard error of the booster-minus-online-rate gain is about
0.0156 nats with 35 contracts (CI half-width 0.031). Assuming similar between-contract heterogeneity,
the standard error scales roughly as 1/sqrt(contracts):

| Target | Required SE | Contracts (approx.) |
|---|---:|---:|
| CI half-width 0.01 nats | 0.0051 | ~330 |
| 80% power for a 0.01-nat gain (two-sided α 0.05) | 0.0036 | ~660 |
| 80% power for a 0.02-nat gain | 0.0071 | ~170 |

These are **preliminary** numbers: they scale contract-only uncertainty from one week, whereas the primary
test uses a contract × date two-way bootstrap, so date dependence will widen them. Before freezing, plan
jointly for contributing contracts (after inactive-contract losses: 5 of 40 never issued on 8–14 June and
32 of 50 on 1–7 June), the number of dates/weeks, and the between-date variance, re-estimated on development
data. Adding rows per contract helps far less than adding contracts and dates.

## 6. Evaluation

- Primary: matched row-weighted log loss of `hgb+rate` vs online rate, two-way (contract × date) bootstrap,
  5,000 draws; Brier no worse; worst-case missing-outcome bounds; evaluate once, with a consumption receipt.
- Warm-stratum equivalence (optional secondary): two one-sided tests against a margin justified before freezing
  (from a practical-use criterion) with adequate planned power. It can show the difference is smaller than the
  margin, not that it is zero; an inconclusive result remains possible (Lakens 2017, *Soc. Psychol. Personal.
  Sci.* 8(4):355–362).
- Secondary: factorial contrasts (H2), early-history strata (H3; history restarts only at true listing or a
  documented gap, not at an analysis-block boundary), per-contract and per-date wins, the
  nonoverlapping 30-minute subset, calibration arm, and strata from §4.
- All results reported whatever the sign; no refit or retuning after the test opens.

## 7. Out of scope for this cycle

Directional or size targets, trading claims, news features (pending independently reviewed links and
first-availability evidence), sequence models (only if H2 shows a reason), a second venue.
