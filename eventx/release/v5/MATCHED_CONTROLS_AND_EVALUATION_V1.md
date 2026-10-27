# V5-R matched controls and evaluation contract v1

Date: 2026-09-09. Status: **method decisions finalized label-blind; dataset and
executable evaluator NOT frozen; no new-development test authorized by this file**.

This prospectively supersedes the unresolved control, tuning and decision-rule
sections of `REDUCED_NEWS_CANDIDATE.md`. It does not change V4, its protected interval,
any opened historical result, the inherited 30-minute target, or its eligibility
definition. All earlier negative results remain in the research record.

## 1. Question and comparison

Does the prespecified recent relevance–novelty representation improve prediction
after nonlinear market state **and news timing** are accounted for?

| Model | Role |
|---|---|
| Linear B0 | Market-baseline replication comparator |
| B0-v5N | Primary nonlinear market baseline |
| C-context | Exposure-gated market recalibration diagnostic |
| C-timing | Timing/count diagnostic without semantic scores |
| C-timing-matched | Primary content-free attribution comparator |
| V5-R | The only promotable news candidate |

Shallow trees remain a separately reported market-only exploratory benchmark. They
cannot replace B0-v5N after seeing the new interval. No tree/news model search.

## 2. Point-in-time definition and exact feature contract

`available = max(published_at, first_seen_at, exact_content_version_available_at)`.
Missing version evidence or incomplete streams fail admission; no imputed zero news.
`E30 = 1` iff at least one valid associated article is available in `(t-30m,t]`.
Use the existing deterministic association definition, first-available dedup policy,
seven-day backward novelty history and frozen 64-component TF-IDF/LSA architecture
from the corrected reference implementation. Semantic corpus fitting uses only
pre-window text associated exclusively with permitted training families. Later text
and validation-family corpus rows cannot fit vocabulary, IDF or SVD. Unknown terminal
time is zero plus an explicit missingness indicator, never eventual resolution time.

All models receive the same row identities and the same **named** 15 market columns
from `eventx.features.v5_market.MARKET_FEATURE_NAMES`. A source adapter must explicitly
reorder by name; the current generic PIT adapter's appended terminal columns are
not automatically in this order. Verify this before production integration.

Let `M` be those 15 inputs, `p0` the corresponding honest base probability, and
`Z = [M, p0, logit(p0)]` (17 columns). Define:

- `a = minutes_since_latest_available_article / 30` on exposed rows, zero otherwise;
- `c = log1p(min(valid_article_count_30m, cap))`, where `cap` is the training-only
  all-eligible-row 99th percentile, using linear quantile interpolation;
- `qmax = max(relevance * novelty)` over those articles;
- `qlast = relevance * novelty` for the last available article;
- `u = log1p(minutes_to_scheduled_terminal)`, point-in-time only.

Ties in article availability use stable first-version article identity ordering.
The following matrices are fixed, with a separately fitted unpenalized intercept:

```text
C-context         = [Z]                              17 columns
C-timing          = [Z, a, c]                        19 columns
C-timing-matched  = [Z, a, c, a*a, c*c, a*c]          22 columns
V5-R              = [Z, a, c, qmax, qlast, qmax*u]    22 columns
```

Both primary residuals have the same common context, timing inputs, three additional
coefficient slots, exposed training rows, solver and search budget. Timing-polynomial
slots give the control useful content-free flexibility; zero padding would not.
Equal width is **nominal capacity matching**, not proof of equal effective complexity:
record constant columns, rank and fitted coefficient norms on training data. Do not
add replacement features for rank-deficient columns. C-context and C-timing are
diagnostics, not alternative candidates selected after results.

No content shuffling across future times or family boundaries. The primary result
attributes the **joint relevance–novelty representation**, not novelty independently
of relevance, causality, social virality or publisher independence.

## 3. Fitting and tuning

All residual models use `sigmoid(logit(p0) + E30*kappa*delta)`, with a fixed offset
coefficient of one. Fit the elastic-net residual on exposed training rows only;
evaluate on all eligible rows. No standalone expert mixture. Fit standardization
on exposed training rows, not validation rows. The loss is mean exposed-row NLL plus
`lambda*alpha*L1 + 0.5*lambda*(1-alpha)*L2_squared`; intercept is unpenalized.

- Residual grid: `lambda = [0.01, 0.1, 1.0]`, `alpha = [0, 0.5]`,
  `kappa = [0, 0.25, 0.5, 1]`: 24 combinations per residual, identical for controls.
- Select minimum pooled inner-validation all-row log loss. Exact ties: smaller kappa,
  then larger lambda, then larger alpha. No separate post-hoc calibration.
- Fixed solver tolerance: proximal KKT residual <= `1e-7`, maximum 20,000 iterations.
  Nonconvergence or nonfinite output fails the execution gate; do not discard bad fits
  selectively or change the grid after results. A single-class required training
  partition fails rather than silently switching to a constant model.
- B0-v5N retains degree-2, four-quantile-knot splines with linear extrapolation and
  no spline intercept on the nine named nonlinear columns in the inherited model
  specification. Linear B0 receives the same underlying market inputs.
- Base L2 logistic `C = [0.001, 0.01, 0.1]` (these are **inverse regularization**
  values); training-only inner validation chooses C, with smaller C breaking ties.
  Base fitting uses convergence warnings as errors, maximum 2,000 iterations,
  tolerance `1e-8`. Standardization and spline knots are fit inside each training scope.

For every outer training partition: generate base OOF scores using forward-time,
family-disjoint subfolds **inside that partition**; base-C selection must itself use
only each subfold's training data. Residual hyperparameter tuning repeats this entire
stack inside its permitted inner training scope. Never reuse global OOF predictions
across outer boundaries. Omit and record warm-up rows with no honest OOF base score;
do not substitute in-sample scores. All model arms share the same base scores and
eligible scored row IDs. Refitting the base on full permitted training data is for
deployment only; final residual fitting still uses OOF base scores.

The zero-news invariant is bitwise equality `p_R[E30==0] == p0[E30==0]`, likewise for
controls. This is a software test, not statistical evidence of news value.

## 4. Families, time folds and admission

An event family is the connected component of verified same-event, nested-event,
multi-leg dependency and cross-venue-equivalence links. Membership is for split
isolation, not a logical equivalence assertion. Generic question text is not enough:
retain named YES/NO contract subtitles and historical semantics. Do not declare
different venue event tickers independent. Unresolved multi-leg bridges and missing
membership are excluded **before labels**, with an exclusion ledger; they cannot
be quietly treated as singleton families. Do not split a giant verified component to
increase the apparent sample size. Shared sector alone does not imply one component.

Freeze a label-blind dataset/split manifest specifying exact UTC windows, source and
feature hashes, family membership, all outer/inner/base-OOF fold row IDs and exclusions.
Use five forward outer time blocks, crossed with five deterministic family groups;
for each time block score all five held-family slices exactly once, pooling them into
one reported outer time fold. Family groups are formed by sorting SHA256 of
`v5r-family-v1|family_id` and assigning round-robin. Training is strictly earlier than
the validation block and excludes its entire held-family group. Require training
label endpoints `< validation_start` and validation endpoints `< validation_end`.
No future-training reverse folds. Inner/base-OOF partitions obey the same constraints
inside their parent; freeze their concrete schedule before labels. A family is never
in training for its own held-out prediction even if it occurs in another time block.

Label-blind feasibility minimums: at least 30 verified families and 28 UTC days in
the pooled outer scored sample; at least 20 families with E30 exposure overall; each
of the five outer time folds contains >=5 exposed families. These are minimum breadth
safeguards, **not a guarantee of power**. Report concentration and synthetic clustered
power across effect sizes before labels. If infeasible, do not relax thresholds under
this version or open labels: report insufficient scope and version any redesign.

Exact dates cannot yet be chosen honestly: source provenance and family gates have
not passed. Historical dates are acceptable if their outcomes are genuinely unopened,
PIT evidence passes, and the scope avoids consumed/opened intervals and protected V4.
No instruction here requires live data in preference to valid untouched history.

## 5. Metrics and uncertainty

Primary estimand: mean per-eligible-row log-loss improvement on the admitted cohort,
with positive difference meaning the candidate is better. Natural logarithms;
evaluation-only clipping to `[1e-12,1-1e-12]`, same for every arm. Report Brier, AP,
exposed-row effects, per-family equal-weight effects and five time-fold effects as
secondary diagnostics. AP with no positives is explicitly undefined, not zero.
Undefined secondary AP does not invalidate a defined LL contrast; any **required**
undefined LL/Brier metric or failed required fit makes promotion impossible. Missing
source evidence is `incomplete`, not a negative scientific result.

Use paired bootstrap draws shared by all model contrasts: 5,000 replicates, seed
`20260909`. Resample verified families with replacement and independently resample
synchronous one-UTC-day calendar blocks with replacement within each outer time fold;
draw the original number of families and the original number of dates in each fold.
Multiply family and date multiplicities for each row. All markets on a sampled date
receive the same date multiplicity; do not independently shuffle their clocks. Report
2.5th/97.5th percentiles. Empty-weight replicates or insufficient support fail the
uncertainty gate; do not silently drop/redraw replicates. Also report family-only and
calendar-only sensitivity intervals without using them to rescue promotion. Daily
blocks preserve intraday serial dependence, not arbitrary multi-day dependence;
include multi-day dependence scenarios in the required synthetic coverage audit.

This is a prespecified approximate crossed-cluster/block uncertainty procedure, not
proof of independence or population-wide coverage. Synthetic coverage checks remain
required before production freeze. The family and temporal dependence assumptions,
finite-cluster limitations and restricted cohort must be disclosed.

## 6. Fixed decision hierarchy

1. **Source/software gate:** complete certified sources, verified families, required
   breadth, PIT tests and synthetic numerical/uncertainty checks pass.
2. **Market replication:** `LL(linear_B0)-LL(B0-v5N) >= 0.001` and paired lower
   95% bound >0. The 0.001 margin is a design requirement, not an estimate from new
   outcomes. Failure is reported; no v5 news candidate advances under this hierarchy.
3. **News versus market:** `LL(B0-v5N)-LL(V5-R) >= 0.001` and lower 95% bound >0.
4. **Content attribution:** `LL(C-timing-matched)-LL(V5-R)` lower 95% bound >0.
5. **Calibration floor:** lower 95% bound of `Brier(B0-v5N)-Brier(V5-R) > -0.0005`.
6. **Subgroup guardrail:** predeclare venue and inherited broad-category groups.
   A group is testable only with >=20 verified exposed families and >=1,000 E30 rows,
   determined label-blind. For K qualifying groups, require the one-sided
   Bonferroni-adjusted lower percentile bound at `0.05/K` of
   `LL(B0-v5N)-LL(V5-R)` to exceed `-0.001` for every group. No qualifying groups:
   record guardrail not assessable and restrict claims to pooled cohort; this alone
   does not veto otherwise valid pooled promotion. Do not select subgroup claims
   from favorable results. Margins are fixed policy tolerances, not power guarantees.

All required gates must pass; there is no selection among several news hypotheses.
The primary success statement is a conjunction, not a menu of significant contrasts.
Do not require positive signs in four of five folds in addition to these gates.
Time-fold and market-balanced effects remain mandatory reported robustness results.

Any failed news/attribution gate closes this V5-R branch: no larger exposure window,
relevance cutoff, diffusion, semantic replacement, category variant or new interaction
as a rescue. Numerical/data failures yield `incomplete`; a completed well-defined
failure yields `negative`. At most one news candidate can be frozen for a separately
reserved, untouched confirmation scope disjoint from V4. Apply the same news gates
there once, against the frozen corresponding base/control bundles, with a prior
consumption receipt. Do not reselect from confirmation results.

## 7. Implementation and freeze checklist

`eventx/v5_corrected/matched_controls_v1.py` tests the named matrix contract without
labels. The existing reference pipeline still needs the production adapter, matched
matrix integration, nested base-C selection, concrete split ledger and this evaluator.
It must not be described as implementing this entire contract already.

Before opening new development labels, publish a manifest hashing this document,
implementation, dependencies, data/cohort, warm-up scope, splits, synthetic tests and
planned confirmation boundaries. Freeze date/support choices label-blind. The present
document finalizes method choices; it is **not** that complete preregistration and
does not unblock missing historical metadata/content-version/completeness evidence.
