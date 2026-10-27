# EventX v5 design candidate

**Status:** development proposal; not preregistered or frozen  
**Prepared:** 2026-09-03  
**Updated:** 2026-09-03 after matched-base, mechanism and nonlinear-control tests  
**Permitted evidence:** previously opened historical discovery data only  
**Protected evidence:** the v4 future confirmation interval remains untouched

## 1. Research question

Does point-in-time, market-relevant news provide a sparse, state-dependent correction
to the probability of a large 30-minute prediction-market repricing after conditioning
on information already present in market prices and executed-trade history?

V5 is a new research cycle. It does not alter, replace or rescue the frozen v4
experiment. The v4 result must be evaluated once under its existing protocol after
its sealed interval closes. V5 may be frozen only after its implementation, source
gate, candidate set and a new untouched confirmation sample have been specified.

The current v5 question is mechanism identification rather than open-ended model
improvement: does a minimal recent relevance-novelty signal add information after
controlling for both nonlinear market state and exposure-conditioned recalibration?

## 2. Motivation from the opened historical data

The original additive B3 model was worse than market-only B0 by 0.006459 log-loss
units per row. Failure diagnostics localize the problem:

- on 498,214 rows with no prior-day news, B3-versus-B0 log-loss improvement was only
  -0.000029;
- on 24,315 rows with news aged 0–30 minutes it was -0.034353, although the
  relevance/novelty step B2-versus-B1 was +0.001321;
- extreme negative B3 logit corrections below -1 occurred on 13,967 rows and lost
  0.250544 log-loss units per row relative to B0;
- 13 of 16 news coefficients changed sign across five one-seed fold fits;
- on a representative fold, the fixed constant-learning-rate learner had validation
  log loss 0.407326 at epoch 3 but 0.433444 at the frozen epoch 5;
- a historical two-stage factorization did not rescue B3 features: relative to its
  B0-feature counterpart, log-loss improvement was -0.032853 for trade arrival,
  -0.045451 for repricing conditional on trade and -0.030432 for their product.
- a converged spline residual initially improved a linear B0-v5 by +0.009614, but an
  exposure-gated context-only model improved by +0.010485 and a global nonlinear
  market-only control improved by +0.018157;
- the global market-only control beat the full news model by 0.008543 log-loss units,
  with paired interval `[0.005862, 0.011342]` in the market-control direction;
- relative to the gated context-only control, adding volume/age changed log loss by
  -0.000036, quality/age by -0.000268, lifecycle/age by -0.000340 and the full news
  family by -0.000871. None supplies positive historical mechanism evidence.
- a direct nonlinear market-only implementation subsequently improved the stacked
  nonlinear control by +0.003611, paired interval `[0.001359, 0.005694]`, and the
  intermediate linear B0-v5 by +0.021768. Its fold-4 convergence repair completed in
  512/2,000 iterations and changed predictions by at most 0.00004109.

These observations first require a stronger market-only reference. The apparent
residual-news gain was primarily nonlinear market calibration, not news semantics.
Only after that market structure is absorbed is it meaningful to test the narrower
hypothesis that news is an occasional correction whose sign and magnitude depend on
age, novelty and information-lifecycle state. The evidence does not justify assuming
that cross-publisher confirmation is beneficial; its effect must be learned
conditionally and allowed to be zero or negative.

## 3. Target and point-in-time rules

The primary v5 target remains the v4 30-minute absolute canonical-YES log-odds jump,
subject to a fresh protocol review before freezing. All prices use executed
canonical-YES trades. Every feature at prediction time `t` must be reproducible from
records whose conservative availability time is at or before `t`.

For a news row, conservative availability is the maximum of valid publisher time,
Lumid ingestion time, provenance-run start/end time and EventX receipt time required
by the eventual source contract. Backfilled news cannot enter an earlier feature.
Missing or censored source intervals fail the gate; they are never encoded as zero
news.

## 4. Model architecture

### 4.1 Strengthened market baseline

Define and freeze `B0-v5N` before testing news. The opened-data architecture comparison
selects a **direct nonlinear** rather than stacked implementation. It contains the v4
market-only features plus:

- `log1p(minutes_to_scheduled_terminal)`, known at `t`;
- a missing/uncertain-terminal indicator where needed;
- prespecified, low-complexity nonlinear transformations of baseline probability,
  volatility, activity, price age and time to terminal that pass future-append and
  point-in-time tests.

Any baseline change is applied to both sides of the incremental-news comparison. The
primary comparison is V5 versus B0-v5N, not versus B0-v4 or the intermediate linear
B0-v5. The direct development specification uses four-knot degree-two quantile
splines fit on training partitions only for price log-odds, three momentum horizons,
two volatility horizons, minutes since trade, minutes to scheduled terminal and
price age. Count/notional variables remain prespecified log-linear terms. L2 logistic
regularization is selected from `C in {0.001, 0.01, 0.1}` on inner-fold log loss with
deterministic L-BFGS (`max_iter=2000`, tolerance `1e-7`). This is a development
selection, not a frozen or confirmed model.

### 4.2 Sparse residual news expert

For the already-tested broad residual family, let `p0` be the B0-v5N probability and
let

```text
E(t) = 1 if at least one valid associated article is available in (t-1440m, t]
       0 otherwise.
```

No fitted relevance threshold is used in the primary exposure gate. The combined
prediction is

```text
p(t) = sigmoid(logit(p0(t)) + E(t) * kappa * delta(t)),  0 <= kappa <= 1.
```

`delta(t)` is learned by the news residual expert and `kappa` controls correction
magnitude. The implementation must satisfy the numerical invariant

```text
max(abs(p_v5 - p_b0_v5) where E == 0) < 1e-12.
```

The residual expert is trained only on valid news-exposed rows. It is evaluated both
on exposed rows and on the complete identical B0-v5N evaluation set.

The next reduced V5-R cycle replaces this broad 1,440-minute gate with the fixed
30-minute gate in `REDUCED_NEWS_CANDIDATE.md`; it does not retest the broad family.

A context-only residual using no news quantity, quality, age or lifecycle feature is
a mandatory negative control. A news candidate is ineligible unless it improves over
both B0-v5N and that context-only control. This prevents nonlinear market calibration
from being mislabelled as incremental news information.

### 4.3 Cross-fitting and stacking

The residual learner must never receive in-sample base probabilities.

For every outer development fold:

1. split the outer training partition again using the frozen inner market/time rule;
2. produce cross-fitted B0-v5 probabilities for all residual-training rows;
3. tune the residual learner and `kappa` only within that outer training hierarchy;
4. refit the selected inner configuration on cross-fitted outer-training scores;
5. obtain B0-v5 probabilities for the untouched outer validation fold from a base
   model that did not train on that fold;
6. score B0-v5 and V5 on identical outer rows.

After architecture selection, the final residual expert is trained on out-of-fold
B0-v5 scores for all development rows. The deployment base model is separately
retrained on all development rows. In-sample scores from that full base fit never
replace the cross-fitted scores used to train the residual expert.

## 5. News representation

### 5.1 Quality and timing

Prespecified feature families should separate quantity from quality:

- article count, story count and publisher count;
- maximum and mean relevance;
- maximum relevance multiplied by novelty;
- relevance and novelty of the most recent article;
- time since first and latest associated report;
- 0–30, 30–120, 120–360 and 360–1,440 minute age states;
- prespecified exponential decays of relevance and relevance-novelty strength.

The 0–30 minute family is scientifically important because it is the only historical
age band in which B2 improved log loss over B1. This is development evidence, not a
confirmatory result.

### 5.2 Online story lifecycle

Story state must be constructed sequentially. When article `A_i` becomes available,
it may be compared only with clusters formed from articles already available. Later
articles cannot retrospectively alter earlier cluster membership or features.

Candidate lifecycle variables are:

- new-story first report;
- repeated report before a second publisher;
- first cross-publisher confirmation;
- additional publisher diversity after confirmation;
- repeated/syndicated coverage after confirmation;
- story age and time since first confirmation;
- interactions among lifecycle state, novelty and story age.

Exact normalized-headline clustering is the auditable baseline. A semantic clustering
candidate is permitted only if its embedding and thresholds are trained/frozen inside
the development hierarchy and it passes future-append invariance tests. Distinct
publisher labels must be called cross-publisher diffusion, not independent
confirmation or social virality, unless source lineage establishes independence.

### 5.3 Market-context interactions

The limited interaction set may include news state with:

- B0-v5 probability;
- recent volatility and activity;
- price age and minutes since latest execution;
- time to scheduled terminal;
- venue and broad preregistered market category.

These interactions address state dependence. They are not a license for an unlimited
feature search.

## 6. Candidate models

The broad candidates below describe the architecture search already conducted on
opened data; neither V5-A nor V5-B is eligible for freezing:

| Candidate | Definition | Role |
|---|---|---|
| V5-A | B0-v5N offset plus gated elastic-net logistic news residual and shrinkage | Interpretable candidate |
| V5-B | B0-v5N offset plus gated low-degree spline/GAM news residual and shrinkage | Nonlinear age/saturation candidate |
| V5-C | Factorized trade-arrival times conditional-repricing model using the same cross-fitting rules | Exploratory unless a fresh development implementation earns promotion |

A shallow boosted-tree residual may be reported as exploratory only. The opened
historical two-stage result is negative, so factorization is not assumed to improve
performance and cannot bypass the primary incremental-news gates.

The current opened historical implementation is a **no-go** for freezing either
V5-A or V5-B: linear news corrections were slightly harmful, and the nonlinear full
news model underperformed both its context-only gate and the global nonlinear
market-only control. Further development must simplify the news family or accept the
null rather than optimize repeatedly on the same outcomes.

The proposed next primary candidate is the separately specified `V5-R`: a 30-minute
article-presence gate with only maximum and most-recent relevance-novelty, article
age, capped article count and one time-to-terminal interaction. Publisher diffusion
and lifecycle are excluded from its primary feature family. See
`eventx/release/v5/REDUCED_NEWS_CANDIDATE.md`. V5-R must be developed on new data and
beat both direct B0-v5N and an identically gated context-only control.

V5-R receives one prespecified test on new development data. Failure against either
B0-v5N or the context-only attribution control closes the v5 news branch; no window,
feature, relevance threshold, semantic representation, interaction family or
diffusion/lifecycle rescue is permitted within v5.

## 7. Optimization

The fixed five-epoch constant-learning-rate SGD used in v4 is not reused by default.
V5 must use a deterministic solver whose convergence is checked within training data.
For the linear candidate, a small prespecified elastic-net grid and inner-fold early
stopping or a converged regularized logistic solver are acceptable. Any epoch,
penalty, regularization strength, l1 ratio and `kappa` choice is made inside nested
training folds.

The final protocol must specify seeds, coefficient averaging, standardization,
clipping, stopping tolerance and tie-breaking. Solver diagnostics are repeated across
folds and seeds before freezing.

## 8. Development and confirmation design

The May–July historical data used to motivate this design are outcome-open discovery
data. They can be used for implementation and feature-family development but cannot
confirm v5.

V5 requires:

1. a source-valid cohort with adequate news exposure and independent market breadth;
2. a new development interval that supports nested purged market/time validation;
3. selection of at most one news candidate against B0-v5;
4. implementation and hash freeze before any new confirmation label is inspected;
5. one untouched confirmation interval disjoint from v4's protected interval and
   preferably covering at least 8–12 weeks;
6. a single-use consumption receipt and one-shot final evaluator.

V5 must not use the protected `[2026-09-06, 2026-10-30)` v4 interval for feature
selection, hyperparameter selection or model selection. Exact v5 dates and cohort
remain to be set by a label-blind feasibility and power audit; they are deliberately
not frozen in this candidate document.

## 9. Proposed evaluation gates

The eventual protocol should define these before outcome inspection:

- first hierarchy level: replication of B0-v5N versus linear B0, reported before
  interpreting any news contrast;
- primary: mean per-row log-loss improvement `LL(B0-v5N) - LL(V5)`;
- minimum important improvement: 0.001 nats per row;
- paired market/event-cluster calendar-block bootstrap lower 95% bound above zero;
- Brier score non-inferiority or improvement under a fixed material-harm margin;
- market-balanced log-loss improvement as a prespecified robustness endpoint;
- news-exposed log-loss improvement as a mechanism endpoint;
- calibration intercept/slope and correction-calibration plots;
- trade-arrival and repricing-conditional-on-trade decomposition as secondary
  scientific endpoints.
- mechanism guard: the selected news model must also improve log loss over the
  frozen exposure-gated context-only negative control.

The complete three-model evaluator must be frozen before any development label is
inspected. Reporting B0-v5N replication first is an inferential ordering, not a
license to revise V5-R after viewing the baseline result.

Subgroup guardrails apply only to groups meeting a prespecified minimum independent
market count and use a material-harm margin, not the sign of a noisy point estimate.
Undefined required metrics fail their corresponding promotion gate. Equality on
unexposed rows is a software invariant, not a statistical success criterion.

## 10. Required tests before any freeze

- news and market future-append invariance;
- exact window-boundary and conservative-availability tests;
- online story clustering with no retroactive state changes;
- cross-fitting/stacking leakage test;
- `E=0` prediction-equality invariant;
- feature standardization fit only on training partitions;
- deterministic solver/convergence and tie-breaking tests;
- label and trade-arrival construction tests;
- identical-row comparison for B0-v5 and every candidate;
- bootstrap cluster/block determinism;
- source truncation, continuity, duplicate and timestamp quarantine tests;
- synthetic end-to-end consumption-receipt and one-shot-evaluation tests.

## 11. Claim boundary

A successful v5 would support only the claim that the frozen, point-in-time news
representation improves probability forecasts of short-horizon absolute repricing on
the evaluated cohort and period. It would not establish causality, directionally
tradable returns, publisher independence, social virality, KOL information or
universal prediction-market behavior.

A negative v5 would be informative: after a sparse residual architecture, correction
shrinkage, lifecycle timing and rigorous optimization, it would strengthen the case
that the tested news data add little probability information beyond market history at
the 30-minute horizon.
