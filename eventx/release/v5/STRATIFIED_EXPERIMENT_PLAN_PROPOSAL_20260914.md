# EventX V5: incremental news value across topics and trading activity

Date: 2026-09-14. Status: **separate proposal for review; not adopted, frozen or executable**.

This document proposes a layered evaluation of the V5 news model. It does not
supersede or edit [PROTOCOL_V1_1.md](PROTOCOL_V1_1.md),
[REDUCED_NEWS_CANDIDATE.md](REDUCED_NEWS_CANDIDATE.md), or the
[complete research plan](../../../COMPLETE_RESEARCH_PLAN.md).
V4 and consumed evaluation scopes remain protected. This document authorizes no
new label access, model selection, data collection, or confirmation run.

## 1. Research objective and intended contribution

Primary question:

> Does recent, point-in-time news relevance and corpus-relative semantic novelty
> improve 30-minute executed-price repricing forecasts beyond nonlinear market
> history and matched news-timing controls?

Secondary question:

> How does incremental predictive value vary with contract topic and trading
> activity observed before the forecast?

The intended contribution is empirical evidence about incremental prediction and
its heterogeneity. Improvement is relative to specified fitted baselines; it does
not prove that information is absent from prices, establish causality, or establish
trading profitability. Novelty is relative to observed Lumid coverage, not first
disclosure anywhere. V5 tests relevance and novelty jointly. Publisher diffusion,
social virality, KOL information and category-specific model search are outside
this proposed cycle.

## 2. Proposed changes and retained decisions

| Component | Proposed treatment |
|---|---|
| Outcome and eligibility | Retain V5 v1.1 target and filters |
| News architecture | Retain sole V5-R candidate and its fixed-offset learner |
| Primary baseline | Retain spline logistic B0-v5N |
| Standard comparisons | Retain linear logistic; add training-frequency sanity baseline and one specified boosted-tree comparison |
| Topic analysis | Prespecified secondary estimates using semantic category assignments |
| Activity analysis | Prespecified secondary estimates using trailing 24-hour executed notional |
| Topic × activity | Descriptive/exploratory estimates only where support permits |
| Model training | Pooled models, evaluated on shared subgroup rows |
| Novelty validation | Add blinded measurement audit and reference-history diagnostics |
| Confirmation | Later, unseen event families with fixed models and frozen subgroup rules |
| Overall failure | Subgroup success cannot rescue the primary candidate |

The proposed tree comparison is an addition to reporting, not an automatic
replacement of B0-v5N. No claim of improvement beyond tree models follows unless
the prespecified direct comparison supports it. A residual-news experiment built
on a tree offset would require a further explicit candidate specification.

## 3. Data requirements and source admission

The observational source remains Lumid Findata and its read-only warehouse exports.
The route families below describe acquisition paths already used by the project;
their present availability and exact filter/pagination contracts must be checked
and saved before acquisition. An endpoint response alone does not certify history.

| Data | Lumid acquisition path | Required content and evidence | Use |
|---|---|---|---|
| Executed trades | `/prediction-markets/trades/{venue}/{market_id}` or documented warehouse export through `/retrieve` | Execution ID/time, venue, market/token, canonical YES price, positive size, source availability, bounded completeness and dedup evidence | Features, 24-hour activity, executed-price labels |
| Historical contract metadata | `/prediction-markets/markets/{venue}/{market_id}` plus certified historical warehouse versions | Question, named outcomes, IDs, category, scheduled terminal, status, validity and availability | Mapping, topic labels, eligibility, associations |
| Event membership | `/prediction-markets/events` and warehouse metadata including embedded event references | Contract membership with historical semantics and provenance | Candidate family graph; semantic review still required |
| News versions | `/news/latest`, `/news/search`, and bounded `/retrieve` export of `news.articles` | Exact headline/summary version, stable identity, publication, first-seen/version availability, publisher, source/run IDs | Association, timing, relevance and novelty |
| Source lineage | `/catalog/lineage/run/{run_id}` and warehouse ingestion evidence | Intended feeds/windows, committed counts, retries, failed/partial runs, exclusions | Completeness and availability certification |
| Derived annotations | Local derivation from admitted Lumid records | Reviewer, rule version, evidence pointers, timestamp intervals and hashes | Topic labels, event-family approval, novelty audit |

Require at least seven days of certified news warm-up and 24 hours of complete
trade history before a scored decision. For a newly created market, a complete
creation-to-decision record can establish that its earlier 24-hour portion had no
market; missing history cannot be filled with zero. Include the forward 30-minute
trade endpoint for labels after authorized access.

Availability of news is `max(publication, first_seen, exact_version_available)`.
Trade features require execution and availability by the decision. Historical
metadata must be valid and available at the relevant instant. A current payload
hash does not establish historical immutability. Resolve intended-feed completeness,
not completeness of all public news. Capped or unresolved windows fail admission.

Older history is acceptable only if unopened and certified. Older publication dates
on recently ingested backfills do not establish earlier availability. Dates and
venue coverage remain unset pending admission; no fixed end-of-September collection
requirement is introduced here.

## 4. Target and analysis population

Retain the v1.1 recipe: canonical YES last executed price on a five-minute UTC grid;
minute carry-forward prices clipped to [0.0001, 0.9999] before log odds. Define
`sigma` as trailing one-minute log-odds population standard deviation over up to
240 changes, requiring at least 30 changes.

```text
Y(t) = 1[sigma(t) > 0 AND
         abs(logodds_price(t+30m) - logodds_price(t)) >= 4*sigma(t)]
```

At t require at least three executions and 100 canonical YES price-times-size
notional in `(t-240m,t]`, latest execution age at most 60 minutes, certified open
status, finite sigma and complete required history. Known scheduled terminal must
be at or after t+30m. Unknown terminal remains unknown. Endpoint must be strictly
before the scored interval end. No forward execution yields unchanged price only
when trade coverage is complete. This threshold is an inherited heuristic, not
four 30-minute Gaussian standard deviations.

Primary population: source-admitted, eligible observations of verified unseen event
families at later times. This excludes very inactive markets under the inherited
eligibility rule; the low-activity group is low *among eligible observations*.

Use a common cohort with certified topic/activity inputs for every model comparison.
Record exclusions and their topic/venue distribution before outcomes are opened.

## 5. Topic assignment

Use these mutually exclusive primary topics:

| Topic | Contract subject |
|---|---|
| Politics and public policy | Elections, appointments, legislation and geopolitical decisions |
| Macroeconomics | Inflation, employment, growth and central-bank policy indicators/decisions |
| Corporate and traditional financial markets | Earnings, corporate actions, equities and conventional asset-price events |
| Crypto | Crypto asset prices, protocol events and crypto-specific outcomes |
| Sports | Match, tournament, qualification and sporting performance outcomes |
| Other/ambiguous | Subjects outside the above or unresolved cross-topic classification |

Classify from contract resolution criteria and metadata available by the decision,
never its realized outcome, news performance or subsequent price behavior. Resolve
overlap by the outcome being settled: an inflation print is macro; a Bitcoin price
threshold is crypto even if motivated by monetary policy. Unresolved cases enter
Other/ambiguous; do not force them into a favorable category.

Two reviewers independently assign topics on a fixed rubric, with disagreement
adjudication before labels. Save `market_id`, metadata version, `topic`, validity
interval, availability, rationale, reviewers and rubric hash. Topic revisions may
apply only when their evidence was available; never rewrite earlier rows.

Topic is distinct from event family. Contracts in one family may span topics but
must remain together in splits and uncertainty calculations. No automatic family
approval from common topic or venue event ID. Report overlapping family membership
across topic counts rather than summing those counts as independent families.

## 6. Trading-activity strata

For each decision define:

```text
V24(t) = sum(canonical_YES_price * executed_size)
         for executions in (t-24h,t] available by t
A24(t) = log1p(V24(t))
```

Use the inherited canonical YES stream, consistent units and deduplication. Describe
this as executed notional activity, not order-book liquidity or total venue volume.

Proposed binning: low/medium/high using training-only 1/3 and 2/3 quantiles of
`A24`, computed separately by venue across eligible training decision rows using
linear interpolation. Assign low if `A24 <= q1`, medium if `q1 < A24 <= q2`, high
otherwise. If q1=q2 or a training bin is empty, retain the degenerate status and
report supported bins only; do not split ties by identity or outcome.

Each outer fold learns cutoffs from its training partition. Inner procedures use
their own permitted training partitions if activity summaries are needed there.
Final confirmation uses cutoffs estimated once from development and serialized.
No quantile fitting on confirmation, including its unlabeled volume distribution.
Fold-relative bands estimate relative activity regimes; report each fold's numerical
cutoffs. Venue-specific bands do not imply equal absolute volume across venues.

A market may change band over time. Report both decision-row shares and unique
families; activity bands are not independent sets of markets. Topic and V24 are
evaluation stratifiers only in this proposal, not new predictive features. A
possible added-feature experiment would require an explicit versioned amendment.

## 7. News measurement and validation

Retain 64-component TF-IDF/LSA fitted on permitted training-family pre-window text.
Define relevance as clipped question/article cosine and novelty as one minus the
maximum clipped cosine to up to 20 preceding associated articles within seven days.
Use conservative availability and deterministic same-time ordering. Preserve the
existing first-available identity/dedup rule and immutable content-version evidence.

No comparison history yields the inherited novelty score of one. Report this
separately as no observed reference, not proof of new facts. Missing coverage fails
admission rather than producing this value. Log reference counts (0, 1–4, 5–19, 20),
source lag and availability quality by topic/activity. Prespecify descriptive
performance for nonempty-reference exposures; it cannot become a replacement gate.

Proposed blinded audit: 180 article–market pairs from permitted development/warm-up
text, sampled across six topics and low/middle/high score bands (10 per cell when
available). Band boundaries and random seed are fixed before sampling; declare
shortfalls without replacement from a hand-picked topic. Reviewers see the market,
article and prior reference texts, but neither scores nor price outcomes.

Two independent reviewers label market relevance and whether the article repeats
facts, updates an existing story, introduces a new fact relative to references,
or is unassessable (including empty history). Adjudicate disagreements and report
agreement, confusion tables and audited proportions with sample sizes. This audit
validates a corpus-relative proxy; it cannot establish global novelty. Audit
acceptance criteria must be frozen before annotations are opened. A failed audit
blocks a validated-novelty interpretation; redesign requires a separate version.
Do not silently introduce near-duplicate thresholds into the inherited model.

## 8. Models and fair comparisons

| Model | Inputs and role |
|---|---|
| Frequency | Smoothed training event frequency `(positives+0.5)/(n+1)`; constant-probability sanity check |
| Linear logistic B0 | Inherited 15 named market inputs; interpretable baseline |
| Spline logistic B0-v5N | Same inputs, inherited nine spline-transformed columns; primary baseline |
| Boosted trees | Same 15 inputs; prespecified additional market-only comparison |
| Context | B0-v5N offset plus exposure-gated market recalibration |
| Timing | Context plus article age and count |
| Timing-matched | Timing plus age², count² and age×count; primary attribution control |
| V5-R | Timing plus maximum quality, latest quality and maximum quality×time-to-terminal; sole promotable news model |

Fit pooled models; do not fit or select a separate model for every subgroup. All
model comparisons use identical scored IDs and targets. Frequency is fitted only
on the corresponding training partition. Market YES probability is an input, not
a directly comparable probability of the 30-minute jump target.

Retain v1.1 spline degree 2/four knots and base C=[.001,.01,.1], solver tolerance
1e-8/max iterations 2000. Residual models use an actual unit-coefficient logit offset:

```text
p = sigmoid(logit(p0) + E30 * kappa * delta)
E30 = at least one valid associated article available in (t-30m,t]
```

Retain lambda=[.01,.1,1], alpha=[0,.5], kappa=[0,.25,.5,1], exposed-row fitting,
training-only scaling and nested pooled all-row LL selection with inherited tie
rules. Unexposed predictions equal p0 bitwise. No post-hoc calibration.

Proposed boosted-tree configuration: `HistGradientBoostingClassifier`, log-loss
objective, learning_rate=.05, max_iter=200, max_depth=3,
max_leaf_nodes in [7,15], min_samples_leaf in [50,200],
l2_regularization in [1,10], early_stopping=False, random_state=20260914.
Select the eight configurations by pooled inner LL; ties prefer fewer leaves,
larger minimum leaf size, then stronger penalty. Fix library version and hash the
adapter before execution. The family is a standard gradient-boosted tree method;
this exact configuration is a proposed study choice, not an established universal
benchmark. Report direct V5-R versus tree performance as secondary, without changing
the primary offset or choosing a winner from confirmation outcomes.

## 9. Split, training and confirmation procedure

1. Inventory opened, consumed and protected scopes before reserving dates. Exclude
   consumed v3.1/OOT data from confirmation and V4's protected 2026-09-06 to
   2026-10-30 interval. Previously opened data can inform development history only.
2. Admit exact source versions and approve dependency-family boundaries. Reserve
   later, family-disjoint confirmation, including semantic fitting separation.
3. Freeze five forward development blocks crossed with five deterministic family
   groups, using v1.1 hash/round-robin allocation. Never split a dependent family.
4. Within each outer training scope, perform nested forward/family-disjoint tuning
   and base OOF fitting. A training label endpoint must precede validation start.
   Omit unsupported warm-up rows; never substitute in-sample base predictions.
5. Freeze stratification, measurement-audit contract, inference and full decision
   hierarchy before new development labels. Rehearse on synthetic fixtures.
6. Fit and evaluate development once under that contract. Generate subgroup reports
   from the same pooled out-of-fold predictions, not extra subgroup fits.
7. If the primary gates pass, choose final hyperparameters through the prespecified
   development tuning schedule. Fit residuals on honest development OOF scores and
   refit the deployment base on all permitted development training data.
8. Serialize models, preprocessing, activity cutoffs and manifests. Freeze all
   requested subgroup outputs before confirmation access.
9. After collection/admission gates pass, create a scope-specific consumption
   receipt before opening confirmation outcomes, then run fixed models once.
   A crash follows the inherited reviewed-recovery contract; no automatic retry.

Historical confirmation is allowed if unopened and certified. No date is invented
to bypass source or power requirements. Baselines may be evaluated for their own
separately specified objective if the news branch stops; this is not news success.

## 10. Estimands, hierarchy and subgroup support

For each common row i and comparator C define
`d_i(C) = LL_i(C) - LL_i(V5-R)`; positive values favor news. LL uses natural logs
and probability clipping [1e-12,1-1e-12].

Primary estimates are pooled means versus B0-v5N and Timing-matched. Report separate
nonlinear-versus-linear replication first. Mandatory secondary outputs include
equal-family mean differences, exposed-row differences, Brier, AP and calibration.
Undefined AP remains undefined. Report source/exposure denominators for every result.

Secondary hierarchy:

1. Six topic estimates.
2. Three activity estimates, with per-venue estimates where supported.
3. Direct differences between topic effects and between activity effects.
4. Topic × activity cells: descriptive/exploratory only.

Proposed minimum for inferential subgroup reporting: 20 distinct exposed families,
28 scored UTC days and 1,000 exposed rows in the evaluated scope. Also disclose total
families, exposure concentration and availability by day. These are eligibility
floors, not power certification. Below-floor cells get counts and explicitly
descriptive point estimates, without a confirmatory interpretation.

Freeze a support registry from source/feature information before outcomes. If a
required metric subsequently proves undefined, report unassessable; do not rebin
or pool topics after inspecting outcomes. A family in multiple groups remains the
same resampling unit. Compare effects directly: significance in one group and
nonsignificance in another does not establish heterogeneity.

For each group g report exposure rate e_g and both all-row and exposed-row effects.
For comparisons sharing the same B0 offset and gate,
`delta_all,g = e_g * delta_exposed,g`. This separates exposure dilution from correction
quality. It does not apply to V5-R versus an independently fitted tree baseline.
Report activity composition within topics; topic differences are observational and
may reflect topic-specific coverage, activity and contract composition.

## 11. Inference, multiplicity and stopping rules

Inference is unresolved in the existing project. Previously tried daily/block and
grouped-t screens failed important dependence scenarios. This proposal does not
approve any of those methods. The final procedure must preserve shared calendar
shocks, within-family dependence, overlapping horizons and changing activity bands.
Use the same paired resampling/uncertainty construction across model and subgroup
contrasts; do not treat subgroup rows as IID or bootstrap each band independently.

Before labels, certify the chosen method under v1.1's independent synthetic
validation contract and simulate the full hierarchy with sparse/unbalanced exposure.
Add direct group-difference and multiplicity checks. If a defensible procedure or
adequate power cannot be established, the inferential study remains incomplete.

Retain primary news gates: all technical/source/family/inference gates pass;
LL improvement versus spline at least .001 nats/row with lower 95% bound >0;
LL improvement versus Timing-matched lower 95% bound >0; Brier improvement versus
spline lower 95% bound >-.0005. The two required LL successes form a conjunction;
one favorable comparison is insufficient.

Retain the v1.1 venue/topic material-harm guardrail for predeclared groups with
at least 20 exposed families and 1,000 exposed rows: all-row LL improvement lower
one-sided Bonferroni .05/K bound >-.001. New activity benefit/heterogeneity tests
are secondary and do not create additional promotion routes. With no qualifying
safety groups, report safety unassessable and limit claims to the pooled population.

For secondary benefit and heterogeneity tests, freeze the full comparison list:
topic/activity effects versus both primary comparators and supported pairwise
topic/activity effect differences. Apply Holm correction at familywise .05 across
this combined secondary list separately within development and confirmation.
Use valid p-values from the certified inference procedure. Report ordinary intervals
as pointwise; they are not simultaneous intervals. Do not remove unfavorable tests
from the correction family. Unsupported prespecified tests receive no rejection.

If either primary news gate fails development, stop the news candidate. Topic or
activity findings cannot rescue it. Any promising subgroup hypothesis requires a
new version and independent confirmation. Do not change news windows, relevance
rules, features, topics, activity cutoffs or candidate architectures to rescue results.

Distinguish positive evidence, harm, exclusion of useful gain and inconclusive
results using the inherited v1.1 interval rules. Missing data or invalid inference
is incomplete. A statistically supported positive effect below the policy threshold
does not meet promotion. Lack of significance does not establish no news value.

## 12. Required reports and artifacts

| Output | Required contents |
|---|---|
| Source admission | Feed contracts, exact versions, availability, reconciliation, hashes, exclusions |
| Topic/family ledger | Semantic rubric, reviewer decisions, dependency edges, unresolved boundaries |
| Activity manifest | Formula, training IDs, per-fold/venue cutoffs, ties and support |
| Novelty audit | Sampling seed, rubric, blinded annotations, agreement, reference-history diagnostics |
| Split/fitting ledger | All outer/inner/OOF IDs, preprocessing scopes, convergence and selected configurations |
| Overall results | Every model's LL/Brier/AP, paired effects, calibration and primary decisions |
| Layered results | Topic/activity/cell support, exposure, estimates, direct differences, corrected tests |
| Inference certification | Assumptions, independent synthetic coverage, false positives and full-hierarchy power |
| Confirmation release | Consumption receipt, input/config/code/model hashes, fixed predictions and one-shot report |

Suggested figures: workflow; topic × activity support heatmap; overall model
comparison; topic/activity effect forest plots; calibration by exposure/activity.
Mark unsupported cells explicitly. Do not color a cell as evidence of benefit from
its point estimate alone. Keep novelty measurement and predictive success separate.

## 13. Execution readiness and immediate work

Existing evidence establishes a working reference implementation and exploratory
model comparisons. It does not establish a ready V5 confirmation experiment.
The canonical handoff records unresolved historical versions/news completeness,
zero final approved families and failed inference screens. Source recovery alone
does not clear these gates. This drafting task did not recheck collector health.

Next work, before labels:

1. Review this proposal and record its adoption, if selected, in a new protocol version.
2. Resolve provider version/reconciliation evidence and finalize family boundaries.
3. Build the topic ledger and label-blind activity/support inventory from admitted data.
4. Freeze and perform the blinded novelty audit on permitted text.
5. Implement the additional baseline and subgroup reporting with synthetic checks.
6. Resolve inference and demonstrate full-hierarchy power for feasible dates/cohorts.
7. Freeze exact scopes, audit thresholds, software versions and immutable artifacts.

Tests should cover future-data exclusion in V24, fold-local cutoffs, ties, metadata
changes, first-seen/version rules, empty versus missing novelty history, family
isolation, shared model row IDs, unexposed equality and paired subgroup inference.

Open freeze decisions: exact admitted dates/venues, final reviewed family and topic
ledgers, novelty-audit acceptance criteria, certified inference method and sufficient
calendar/family support. These cannot be resolved by wording changes alone.

## 14. Paper wording

Proposed title: **Does News Add Predictive Value Beyond Market History? Evidence
Across Prediction-Market Topics and Trading Activity**.

Proposed contribution statement:

> We evaluate whether a prespecified representation of recent news relevance and
> corpus-relative semantic novelty improves short-horizon repricing forecasts beyond
> market-history and news-timing models, and assess variation across topics and
> prior trading activity using a common evaluation protocol.

Successful confirmation supports only the specified corpus, representation,
eligible population and comparisons. Cross-topic generality requires actual support
across topics. Failure cannot establish a universal news-null result. The study
does not claim global novelty, social virality, causal price impact, or executable alpha.

## 15. Local references

- [Current handoff](../../../CURRENT_STATE.md)
- [V5 v1.1 protocol](PROTOCOL_V1_1.md)
- [Matched controls](MATCHED_CONTROLS_AND_EVALUATION_V1.md)
- [Corrected implementation](CORRECTED_IMPLEMENTATION_20260908.md)
- [Certification investigation](CERTIFICATION_RESOLUTION_20260910.md)
- [Source readiness](SOURCE_READINESS_20260908.md)

This proposal is a review artifact. Its presence does not change the controlling
protocol, frozen models, existing stopping rules, or permissions on outcome access.
