# EventX V5-R protocol v1.1 — label-blind revision

Date: 2026-09-10. Status: **design revision and synthetic implementation only**.
No dataset admitted, dates selected, model frozen, or new outcomes authorized.
This supersedes method-v1 for the next V5 research freeze, not its historical
evidence. V4 and every consumed holdout remain unchanged. The failed v1 uncertainty
screen is retained in `data/v5/experiment_implementation_20260910/`.

## 1. Question, estimand and limits

Does a fixed, recent joint relevance–novelty representation improve 30-minute
executed-price repricing forecasts beyond a prespecified nonlinear market model
and exposure-conditioned timing/recalibration controls?

Primary population: eligible rows of source-admitted, verified event families not
used to fit their predictions, evaluated at later calendar times. Mean per-row
log-loss improvement is primary; equal-family and exposed-row means are mandatory
secondary results. This is restricted-cohort predictive generalization, not causal
mechanism identification, novelty alone, market-universe representativeness, or
proof that the nonlinear baseline captures all market information.

Final confirmation must be both later in time and family-disjoint from development,
including semantic corpus fitting. If that scope is infeasible, report incomplete;
do not silently substitute later observations from training families. Reserve it
before development labels. Historical windows qualify if genuinely unopened and
source-certified; no rule requires future collection rather than valid history.
V4 `[2026-09-06,2026-10-30)` and all opened/consumed scopes remain unavailable.

## 2. Source admission and exact target

Sole official observational source: Lumid Findata, including its documented
read-only warehouse export. Retain request/SQL, source/run IDs, exact payload hashes,
schema, receipts and half-open UTC coverage. A warehouse receipt is not upstream
completeness. Define the intended feeds and acquisition semantics in the admission
manifest; do not claim coverage of all public news.

Required datasets/evidence:

| Input | Evidence needed before admission |
|---|---|
| Canonical trades | Venue/market/token identity, execution ID/time, price, positive size, source availability, dedup and complete bounded retrieval |
| Metadata versions | Exact question and named outcome semantics, category, canonical YES mapping, scheduled terminal and trading status, availability and validity intervals |
| News versions | Stable first-version identity, exact headline/summary bytes, publication, first-seen and exact-version availability, source/run lineage |
| Stream reconciliation | Feed/window contract, committed counts, failed/partial runs and retries, unresolved gaps and exclusions, seven-day novelty warm-up |
| Event-family graph | Reviewed dependencies, evidence and reviewer per edge, final components and exclusion ledger; venue event IDs alone do not qualify |

Accepted historical-version evidence is either archived versioned payloads with
lineage or an authoritative source immutability guarantee tied to the exact rows.
Do not infer immutability from a current export hash. Failed ingestion batches may
contain valid committed rows: reconcile, do not automatically delete or accept them.

News availability is `max(publication, first_seen, exact_version_available)`.
Market features use only trades available by the decision time; metadata must be
both available and valid then. Missing proof is exclusion/incomplete, not zero news.

Target recipe (explicitly follows the V4-style executed-trade definition, not the
older umbrella's freshness-only sensitivity wording):

1. Stable `(venue, market, canonical YES token)` identity; no mixture of midpoint
   and trade prices. Valid prices in [0,1], positive executed size; deduplicate by
   execution ID, rejecting conflicting duplicates. Freeze deterministic ordering
   of tied executions in the source adapter before any labels.
2. UTC five-minute decision grid. At each minute carry the most recent canonical
   YES execution. Clip probability to [0.0001,0.9999], then take log odds.
3. `sigma_1m_240` is population standard deviation (`ddof=0`) of up to 240 trailing
   one-minute log-odds changes; use only available history, requiring at least 30
   changes. Numerical negative variance from roundoff is clamped to zero. The
   start of usable history and all warm-up exclusions are manifested.
4. At t require at least 3 executions and at least 100 YES-price-times-size notional
   in `(t-240m,t]`, latest execution age <=60 minutes, finite sigma, certified open
   status and complete required causal history. Known scheduled terminal must be
   no earlier than `t+30m`; unknown terminal is not an inferred eventual resolution.
5. Forward endpoint uses canonical executed price as of `t+30m`, not a later trade.
   Label is `sigma>0 AND abs(logodds(t+30m)-logodds(t)) >= 4*sigma`.
   Zero sigma explicitly gives false, preserving lineage. No forward execution
   implies unchanged carried price, not missing data, ONLY if coverage is complete.
   An unreconciled forward stream is missing, never an automatic negative label.
6. Admit a scored row only if its label endpoint is strictly before the scored
   interval end; training label endpoints are strictly before validation start.

`4*sigma_1m_240` is an inherited heuristic, NOT four 30-minute Gaussian sigmas.
Do not change the rule after looking at prevalence. Freeze the production source
adapter and boundary tests before generating real labels; the definition above
does not certify an adapter that has not been built.

Mandatory diagnostics: price-age <=30 minutes, age strata, trade arrival in
`(t,t+30m]`, arrival-conditioned repricing, source lag and availability quality.
Age <=60 is the primary filter, not an additional informative sensitivity.
Unsigned jump probabilities do not authorize directional P&L claims.

## 3. Unchanged model architecture and fitting

Retain the named 15 market columns and nine nonlinear columns in
`eventx.features.v5_market`. Linear B0 and spline B0-v5N receive identical inputs,
including as-of terminal time and its missingness indicator. Spline degree 2,
four quantile knots, linear extrapolation, no spline intercept. Base logistic
inverse penalties C=[0.001,0.01,0.1], max iterations 2000, tolerance 1e-8;
convergence warnings fail the fit. Choose C by pooled inner LL, smaller C on ties.
Shallow trees are market-only exploratory reporting, never a replacement selected
from new outcomes.

Let `Z=[M,p0,logit(p0)]`, `a=latest valid article age/30`,
`c=log1p(min(count_30m, training all-row linear-interpolated p99 cap))`,
`qmax=max(relevance*novelty)`, `qlast=latest relevance*novelty`, and
`u=log1p(as-of minutes to scheduled terminal)`; unknown u=0 with missingness flag.
E30 is article presence in `(t-30m,t]`, using the frozen association/dedup rule.

| Arm | Residual inputs | Role |
|---|---|---|
| Context | Z | Gated recalibration diagnostic |
| Timing | Z,a,c | Nested-feature diagnostic comparator |
| Timing-matched | Z,a,c,a²,c²,a*c | Primary equal-width attribution comparator |
| V5-R | Z,a,c,qmax,qlast,qmax*u | Sole promotable news candidate |

All use `sigmoid(logit(p0)+E30*kappa*delta)`. Fit residuals only on exposed rows,
with training-exposed standardization and unpenalized intercept. Elastic-net mean
NLL penalty is `lambda*alpha*L1 + .5*lambda*(1-alpha)*L2²`;
lambda=[.01,.1,1], alpha=[0,.5], kappa=[0,.25,.5,1]. Same 24 configurations per arm.
Pooled inner all-row LL selects; ties prefer smaller kappa, larger lambda, larger
alpha. KKT tolerance 1e-7, 20000 iterations; nonconvergence/nonfinite or required
single-class training fails execution. No post-hoc calibration or grid change.

Timing-matched versus news substitutes three features; it is not a nested content
addition. Report news versus simpler Timing as a prespecified nested-feature
contrast too, without a new candidate or rescue gate. Equal width is nominal, not
equal effective capacity. The gate itself uses semantic association, so controls
lack quality scores, not all news-derived information. Report rank/constants/norms.

Retain first-available dedup, seven-day backward novelty, deterministic association,
64-component TF-IDF/LSA (training-family-only pre-window corpus), and stable article
identity tie-breaking from the corrected implementation. Fit all vocabularies,
IDF/SVD, knots, caps and scalers inside their permitted training scope. Hash exact
association implementation and metadata-input semantics; unresolved title/subtitle
mapping prevents admission rather than silently changing associations.

Base scores for residual training are strictly forward, family-disjoint OOF. Select
base C inside each OOF training scope. Repeat the entire nesting inside residual
tuning folds; never reuse global OOF scores across parent boundaries. Record and
omit rows without honest OOF support, never substitute in-sample probabilities.
All arms share row IDs/base scores; unexposed probabilities equal B0 bitwise.

## 4. Development, final fit and confirmation

Freeze five forward development blocks crossed with five hash/round-robin family
groups (`v5r-family-v1|family_id`), retaining method-v1 split semantics. Verify every
outer/inner/OOF row ledger before labels. Final families are reviewed connected
components of same/nested event, multi-leg and cross-venue dependency edges; common
sector alone is not a link. Exclude unresolved bridges; never split a verified giant
component to inflate sample size. Calendar shocks can still correlate families.

Minimum development breadth remains 30 verified families, 28 scored UTC days,
20 exposed families and >=5 exposed families per outer block. These are NOT power
or uncertainty certification. Inference may require substantially longer support.

After development passes, select final hyperparameters using ONE prespecified
pooled forward/family-disjoint tuning schedule entirely inside development, with
the same nested procedure and tie rules. Do not choose the best outer fold or average
its fitted coefficients/hyperparameters. Generate final honest OOF base scores on
permitted development rows and fit final residuals on those scores. Refit deployment
base on permitted full development; retain OOF scores for residual fitting.
Serialize all six fitted arms, exact feature/semantic transforms, configuration,
environment, row/family/split and input hashes. Never fit on confirmation families.

Confirmation is one later, untouched, family-disjoint interval with FIXED models;
no retraining or hyperparameter selection. It is not another nested five-fold fit.
Freeze its support requirement and uncertainty method before development labels;
at least 30 verified families, 28 scored days and 20 exposed families are necessary,
not sufficient. Date boundaries cannot be filled in until source/support pass.
Receipt claiming the exact scope is created exclusively BEFORE label access;
write success or failure evidence and refuse a second attempt. A crash consumes
the attempt; recovery needs explicit reviewed authority, not automatic rerunning.

## 5. Uncertainty amendment and certification

Method-v1 one-day-within-fold bootstrap is NOT permitted for the next freeze.
Implement fixed diagnostic candidates with 3,7,14-day contiguous moving blocks,
drawn synchronously across all families across the complete calendar sequence,
paired across contrasts. Optional global family multiplicities target restricted
family resampling. Preserve actual calendar gaps; never turn nonadjacent dates into
adjacent days. Do not wrap the last date to the first. Reject insufficient block
support or empty-weight draws rather than silently redrawing them.

These are candidates, NOT a selected or certified primary method. Nonstationarity,
fold-specific learning and short persistent series may defeat all candidates.
Report development uncertainty as conditional on the realized fitted-fold pipeline;
do not describe it as full training-algorithm uncertainty. Fixed-model confirmation
has its own later-period/family sampling assumptions. Retain family-only/calendar-only
sensitivity reporting; neither rescues a failed primary gate.

Development screen: synthetic loss processes only; IID, crossed shocks, AR(0.5),
AR(0.9), regime changes and sparse/unbalanced exposure, at short and longer calendars.
No automatic method winner. After choosing a justified method, a separately frozen
validation script/seed suite must use >=1000 trials and 5000 draws per trial, report
Monte Carlo intervals, and require a 95% Wilson lower bound for null coverage >=.925
and upper bound for false positive lower intervals <=.05 in every required scenario.
No repeated validation-seed shopping. Scope-specific full decision-hierarchy power,
Brier/subgroup guardrails and exposure concentration are separate required audits;
single-loss-contrast simulations are not that audit. Certification remains false
until all artifacts are reviewed and a new executable freeze binds them.

## 6. Decisions and reporting

LL uses natural logs and identical probability clipping [1e-12,1-1e-12]. AP and Brier
are secondary/calibration outputs; undefined secondary AP is not zero. Required
undefined metrics or fits prevent promotion.

**Revision from v1:** nonlinear-versus-linear replication is reported first and
separately, using point improvement >=.001 and lower 95% bound >0. It no longer
automatically vetoes a valid incremental-news finding. Never describe failed
replication as an established stronger baseline or substitute the tree baseline.

News promotion is the conjunction of:

1. Source, family, numerical, split and uncertainty certification pass.
2. B0-v5N minus V5-R LL point improvement >=.001 and lower 95% bound >0.
3. Timing-matched minus V5-R LL lower 95% bound >0.
4. B0-v5N minus V5-R Brier lower 95% bound >-.0005.
5. In each predeclared venue/category with >=20 exposed families and >=1000 exposed
   rows, all-row LL improvement lower one-sided Bonferroni .05/K bound >-.001.
   No qualifying subgroup means not assessable and pooled-only claims, not evidence
   of subgroup safety. Report exposed effects to disclose dilution.

Use the same news gates once at confirmation, with certified confirmation inference.
The .001 point rule plus LB>0 is NOT a confidence claim that benefit exceeds .001.
Since E=0 gives identical predictions, delta_LL_all=exposure_rate*delta_LL_exposed.
Simulate the complete hierarchy across prespecified effects/exposure rates before
labels; do not lower thresholds because exposure is sparse.

Branch decision and scientific interpretation are separate. Failed news gates stop
this candidate with no window/feature/semantic/diffusion rescue. For each contrast
report: evidence of harm if UB<0; useful gain excluded if UB<the specified useful
margin (and not harm); positive but below policy threshold if applicable; otherwise
inconclusive when both zero and useful gain remain compatible. Success follows all
gates, not one interval. Missing data/numerics/inference give incomplete, not no-signal.
No universally negative news conclusion is licensed by a failed promotion.

## 7. Required release and current status

Before real labels: source certification with hashed evidence, reviewed families,
admissible unopened scope, exact target/source adapter, complete split/warm-up ledger,
selected and independently certified inference, full-hierarchy power, final-fit
serialization and one-shot runner rehearsal, dependencies/code/config hashes.

As of this revision: metadata and membership recovery succeeded but historical
versions/status and news coverage remain unproven; final approved families=0.
No dates, candidate, or production inference method are invented to bypass these
gates. New numerical functions and synthetic receipts do not constitute production
authorization. See `REVISION_IMPLEMENTATION_20260910.md` for executed work and limits.

Methodological references: block-length choice materially affects moving-block
bootstrap accuracy ([Nordman and Lahiri](https://arxiv.org/abs/1403.3275)); product
factor reweighting has results under specified crossed random-effects conditions,
not arbitrary serial/calendar dependence ([Owen and Eckles](https://arxiv.org/abs/1106.2125)).
Neither reference certifies this project's candidate procedure or finite sample.
