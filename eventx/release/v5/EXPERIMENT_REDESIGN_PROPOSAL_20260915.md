# EventX reassessment and proposed next research cycle

Probes: 15 September 2026. Reassessment finalized: 16 September 2026.
Status: **separate proposal, not adopted or frozen**.
Proposed cycle name: EventX V6 — contract-aware news forecasting.
Current V5 v1.1, V4 and consumed holdout artifacts remain the controlling records
for their respective experiments. This document authorizes no evaluation on them.

## 1. Recommendation and intended contribution

Retain the question of incremental news information. Improve the measurement of
which contract an article concerns before increasing forecast-model complexity.

Proposed paper title: **Does News Add Information Beyond Prediction-Market State?
A Contract-Aware Evaluation of Relevance and Novelty.**

Primary question: among admitted single-event contracts, does information in
Lumid-observed news improve forecasts of the next 30 minutes of executed-price
repricing beyond a strong market model and the timing of associated news?

This is a forecast comparison, not a causal estimate of news impact. The proposed
primary population is the admitted cohort evaluated at later times. A separate
unseen-family test assesses transfer. Neither estimates performance over every
prediction market or every public news source.

The contribution would be an audited chain from contract meaning to article links
to predictive evaluation, with a controlled test separating relevance, novelty and
arrival timing. A benchmark release can support the paper, subject to data rights;
constructing a universal benchmark is not a prerequisite.

## 2. What the current implementation actually does

| Layer | Inspected implementation | Consequence |
|---|---|---|
| Contract-to-event identity | Provider IDs, explicit multi-leg edges, reviewed cross-event links | Good evidence of known structural links; not proof of independent components |
| Family candidate search | Word/bigram TF-IDF, 128-dimensional LSA, top five across components, cosine >=0.65 | Candidates omit some aliases and overrepresent repeated templates; this is not a neural embedding model |
| News association | `v2_1_association.market_spec(question, category)` and lexical `associate` rules | Named outcomes, fixture identities and resolution rules are not explicit matcher inputs |
| Corrected metadata adapter | `Metadata` has question/category/version/times, but no explicit named-outcome or rule fields | Richer warehouse fields cannot improve matching until the adapter changes |
| Relevance | Clipped cosine of 64-dimensional TF-IDF/LSA article and question vectors | A similarity score, not calibrated relevance probability |
| Novelty | One minus maximum cosine against at most 20 prior associated articles within seven days | A busy feed can forget older repeated stories; first observed article receives novelty one |
| V4 diffusion | Prior exact-normalized-headline reports and distinct publisher strings | Misses paraphrases and does not establish independent reporting or social virality |
| V5 residual | Actual fixed-offset elastic-net logistic learner, exposure-only fit, nested forward/family OOF | Retain this repair; the optimizer is no longer merely approximating an offset |

Static source inspection: `eventx/features/v2_1_association.py`,
`eventx/features/v4_news.py`, `eventx/v5_corrected/point_in_time.py`,
`eventx/v5_corrected/offset.py`, and
`eventx/tasks/reconcile_v5_embedded_families_20260915.py`.

In the 4,651-contract local inventory, 133 exact-question groups contain different
YES subtitles, covering 716 contracts. This measures context ambiguity, not 716
proven incorrect matches. Two same-category contracts with identical questions
produce identical default lexical specifications even when their subtitles differ.
Some shared article links are appropriate; the current representation cannot
explicitly distinguish the cases requiring different named-outcome evidence.

Historical model results remain exploratory: stronger market models performed
better in the opened audit, while adding the tested semantic features did not beat
timing controls. This does not prove that a new matcher or model will succeed.

## 3. Live Lumid reassessment: observed evidence

Read-only probes on 15 September used the live OpenAPI, authenticated catalog,
and bounded `/retrieve` SQL. Contract queries were restricted to existing IDs and
metadata ingested before 22 July. Only descriptive fields and text-length indicators
were requested; no price, settlement result or protected holdout was inspected.

| Probe | Observed result | Interpretation |
|---|---|---|
| Live OpenAPI | Retrieved successfully | Current interface contract archived locally |
| Kalshi/news/Polymarket schemas and PM table list | Four successful catalog requests | Relevant tables and column shapes accessible |
| Initial guessed `prediction_markets.markets` schema | 404 | Incorrect table name; discovered and used `polymarket_markets` |
| 200 selected Kalshi contracts | 200 returned; 173 primary rules, 128 secondary rules, 197 YES subtitles | Rule text is recoverable via raw-field projection for many sampled contracts |
| Previously enriched-packet Kalshi subset | 67 found; 43 have primary rule text | Earlier local missingness was partly extraction scope, not source absence |
| Exact rule-text recovery | 43 records across 16 events successfully downloaded | Concrete rule evidence now available for follow-up review |
| 30 selected Polymarket contracts | 30 descriptions, 29 group subtitles, 13 resolution-source strings, 30 embedded event arrays | A richer contract representation is feasible for this sample |
| Raw Polymarket token IDs | JSON strings for all 30 sampled rows | Parse nested JSON strings and validate mapping against normalized columns |
| News ingest-day quality sample | HTTP 400 after about 30 seconds | Quality/completeness not established; error cause not captured |
| Exact 100 existing article IDs retry | HTTP 400 after about 34 seconds | Smaller result size alone did not solve this query path |

These are targeted, nonrandom samples. Length >0 proves field presence, not correct
semantics or historical validity. The 43 recovered texts were inspected by event;
41 were ingested after their listed close time. These records support retrospective
semantic review but cannot be inserted into earlier predictive features without
earlier versions or an applicable immutability guarantee. A population-level
rule-quality audit was not completed.
Both news failures are retained; their timing suggests query cost may matter but
does not establish a timeout diagnosis. No new news rows were recovered this turn.

The current `/news/latest` spec declares `since`, `category`, `limit` with maximum
200; its response projection omits stable ID and ingestion lineage. It has no
documented upper time bound or cursor. It cannot be our complete historical export.
`/retrieve` documents JSONL/CSV/raw, a SELECT-only query, row-cap rejection and a
statement timeout. Parquet output is documented as unsupported; convert locally.

Catalog estimates are not counts of unique events, complete historical intervals
or usable observations. Historical L2 quality was not tested here and is unnecessary
for the inherited executed-trade target.

Evidence: `data/v5/design_reassessment_20260915/report.json`, `openapi.json`,
`queries/`, and `data/v5/provenance_recovery_20260908/reassessment_20260915_*`.
Live reference: [Lumid OpenAPI](https://lum.id/findata/openapi.json).

## 4. Data required and acquisition route

| Dataset | Lumid route/table | Required projection and next check |
|---|---|---|
| Kalshi contract versions | `/retrieve` over `prediction_markets.kalshi_markets` | ticker, event ticker, title, YES/NO subtitles, open/close/expiration, raw rules/legs, source/run/ingest; recover exact historical versions |
| Polymarket contract versions | `/retrieve` over `prediction_markets.polymarket_markets` | condition/market IDs, normalized outcomes/token IDs, question, groupItemTitle, description, resolutionSource, embedded event IDs, source/run/ingest |
| Event descriptions | Catalog then `/retrieve` over `prediction_markets.polymarket_events`; Kalshi embedded/source event fields where exposed | Verify schema first, project titles, identifiers and rules only; no assumption of Kalshi event-table availability |
| Canonical executions | `/prediction-markets/trades/kalshi/{ticker}` and `/prediction-markets/trades/polymarket/{condition_id}` or their warehouse tables | execution IDs/times, token/YES mapping, prices, sizes, source availability; exact-window retrieval and duplicate reconciliation |
| News versions | `/retrieve` over `news.articles` | ID, headline, summary, publication/ingest, publisher, URL, symbol/related_symbols, source/endpoint/run; body only if presence and version guarantee established |
| Coverage and lineage | `/catalog/lineage/run/{run_id}`, source catalog and accessible ingest-run tables | Freeze feed universe, capture semantics, source retention and export reconciliation |
| Cross-venue suggestions | `/prediction-markets/matched-pairs/{venue}/{venue_id}` | Candidate evidence only; contract-rule verification required; not newly tested |

News schema contains body, related_symbols and raw JSON, but the failing quality
probes did not establish their population or historical usability. Do not start
using body or generated summaries under an assurance covering headline/summary only.
Do not send observational text to an external LLM by default; local frozen models
are sufficient for the proposed retrieval audit.

Request a provider-supported indexed/keyset or materialized export for the known
article IDs and windows if bounded queries continue failing. Ask for query-plan or
request-ID diagnosis; do not repeat full scans or equate failures with empty data.

## 5. Separate contract meaning, event identity and split grouping

Use three distinct records:

1. **Contract:** exact YES proposition and payout rule. Store venue, contract/token
   IDs, subject entities, event type, location, event date/season, stage, metric,
   comparator, threshold, unit, deadline, resolution source, rule/version evidence.
2. **Event:** the real-world observation being forecast, such as a particular CPI
   release or a dated football fixture. Different thresholds can share an event.
3. **Split group:** contracts/events that must be kept together for evaluation
   because they share observations or have documented structural dependence.

Typed edges: identical observation, mutually exclusive outcomes, threshold relation,
stage dependency, shared resolution statistic, explicit parent/leg, and uncertain
possible dependency. Store direction where applicable, exact source spans, rule
versions, reviewer status and reason. Similarity is a retrieval score, not an edge.

Primary cohort proposal: single-event contracts with recoverable identities and
usable as-of metadata. The known 397 combo contracts are a separate extension.
An album sales threshold or CPI threshold is still a single-event contract.
Excluding combo parents removes their forecast targets and parent-specific edges;
it does not prove the retained underlying events independent. Rebuild typed groups
for the actual admitted cohort and inspect other links before assigning splits.

Use structured candidate blocks on entity/event/date/metric plus BM25 and dense
retrieval, taking the union of candidates. Dates constrain identity but do not
automatically reject related stages. Expand beyond top-five nearest neighbours.
Audit candidates missed by one retrieval method using other methods and a random
sample outside the retrieved sets. Version all new decisions; preserve prior graphs.

Conservative unions can quarantine uncertainty for splitting without changing an
edge into a verified semantic fact. Unknown critical contract identity still blocks
its features. Group review documents known dependency control, not mathematical
statistical independence of every group. Common calendar shocks remain possible.

## 6. Proposed news-link algorithm

### Retrieval and relevance

Build the market query from its event title, YES proposition, named outcome, subject,
date/stage and selected rule text available at article arrival. Exclude prices,
settlements and future metadata from this representation.

For each incoming article, retrieve candidate active events using the union of
entity/alias matching, BM25 and frozen dense embeddings. Start with top 50 per
retrieval channel for the annotation pilot; freeze final retrieval parameters from
link labels, never forecast outcomes. Apply a joint article/contract cross-encoder
to rerank, with explicit entity, date, metric and stage compatibility features.
Use local pre-cutoff model artifacts where demonstrable; otherwise describe current
pretrained encoders as retrospective methods and evaluate confirmation after their
release. Record model revision/license/training-cutoff uncertainty. A frozen model
alone does not prove historical availability or absence of pretraining contamination.

Output three relevance classes: direct event evidence, relevant background, unrelated;
plus abstain for ambiguous identity. Primary exposure uses validated direct links.
Background remains a separate feature/diagnostic. Article-to-event links can be shared
by multiple contracts, but outcome-specific applicability requires its own check.
Multi-label links are allowed; do not force each article to one market.

Calibrate score thresholds on independent article–event labels. A sigmoid-transformed
cross-encoder score is not automatically a relevance probability. Retain the existing
lexical matcher as a reproducible retrieval baseline.

The retrieve/rerank architecture is established, not itself an EventX novelty claim:
[Sentence Transformers documentation](https://www.sbert.net/examples/sentence_transformer/applications/retrieve_rerank/README.html),
[Sentence-BERT](https://aclanthology.org/D19-1410/).

### Human validation before predictive modeling

Proposed initial budget: 1,200 article–event pairs, 600 development and 600 held-out
evaluation pairs, separated by event and story. Two reviewers see contract evidence
and article text, with no market outcomes or retrieval scores; adjudicate differences.
Include direct candidates, wrong entity/date/stage examples, background mentions,
and probability-sampled nonretrieved pairs. Record sampling probabilities; raw
precision from an enriched sample is not population precision.

Add 100 sampled event–day search tasks to compare retrieval coverage against a deeper
independent pool. Report recall relative to that audited pool; no universal recall
claim. Measure precision, abstention, retrieval misses and linkage coverage by topic.
Proposed direct-link gate: held-out precision lower 95% bound >=0.90 overall, with
design-aware uncertainty for clustered/stratified samples. This is a proposed policy,
not an established universal threshold. If support is too small, enlarge a separately
planned audit batch without reusing its labels to tune the evaluated matcher.

### Novelty and diffusion

Define novelty as new information relative to the recorded Lumid corpus available
before the article, not novelty anywhere in public information. Deduplicate exact
versions and syndicated copies first, retaining their provenance.

Compare against the full prior seven-day related-story index, with approximate
retrieval validated against exact search on a sample. Replace the last-20 truncation.
Store continuous semantic distance, same-story repetition, new factual update and
history-sufficiency separately. No earlier observed story with incomplete warm-up
means unknown novelty, not maximum novelty.

Separate relevance and novelty inputs; do not rely exclusively on their product.
Validate a 300-pair story/new-fact audit from the opened corpus before using the
features. Online clustering compares only against earlier available articles and
never rewrites previous features. An embedding difference alone is not proof of
a new fact. Publisher count means dissemination across named publishers; call it
independent confirmation only with syndication/ownership evidence. Social virality
remains outside the data-supported scope. Diffusion is secondary in this proposal.

## 7. Source admission with a realistic scope

Define the primary information set as **what the frozen Lumid capture process had
recorded and made available by t**. This requires complete export and retention of
that recorded stream. It does not require collecting every public article or every
item an upstream vendor might have offered. This is an explicit change from an
upstream-complete-feed interpretation and limits the conclusion accordingly.

Maintain separate flags for warehouse-export completeness, upstream capture health,
and timestamp/semantic validity. Known provider outages describe the operational
feed regime; unknown loss of already recorded historical rows is missing evidence.
Never use current capture-health information as a historical feature unless it was
known then. Observed-feed zero can be valid only when the defined recorded stream
is completely reconstructed; it never means zero real-world news.

Use `max(publication, first_seen, exact_version_available)` for articles. Apply the
accepted administrator assurance to its documented headline/summary scope and map
the actual revision timestamp field. Keep publication-to-ingestion lag as a separate
measurement; a late backfill is newly observed by Lumid, not newly public information.

For contract versions, join on both availability and validity. An immutable contract
rule can use a provider guarantee tied to the record; scheduled close is not a full
trading-status history. Unknown critical metadata is quarantined. Reference trade
labels still need complete execution windows. News lookback gaps propagate through
the seven-day novelty warm-up; do not remove just the outage day.

Build row eligibility from a frozen information rule and retain exclusion reasons.
Forward-window gaps are discovered after decision time: report them explicitly,
do not silently select away difficult outcomes. Confirmation stops on unrecoverable
required labels, or uses a prespecified worst-case missing-score bound. It must not
report observed-only complete cases as though missingness were harmless.

## 8. Forecast models and attributable comparisons

Retain 30-minute unsigned executed-price repricing and the documented inherited
threshold `4*sigma_1m_240`; it is a heuristic. Keep freshness/trade-arrival diagnostics.
Use five-minute rows for development and operational descriptive reporting.

Proposed baselines: training-rate constant; converged regularized logistic model;
spline/GAM-style logistic market model; shallow gradient-boosted market trees.
Market price is a probability of final settlement, not a direct forecast of a
30-minute jump, so it is an input rather than a competing jump probability.

Choose the market baseline using nested chronological development only. Give spline
and tree candidates the same market inputs, deterministic training budget and
permitted calibration procedure. Do not select a baseline to make the news gain
larger. Report all prespecified baselines. The tree implementation is an established
classifier: [scikit-learn documentation](https://scikit-learn.org/stable/modules/generated/sklearn.ensemble.HistGradientBoostingClassifier.html).

Attach the existing true offset learner:

`p = sigmoid(logit(p0) + E30 * kappa * clip(g(features), -1, 1))`.

The correction bound is a new proposed guardrail, not a result-selected parameter.
Tune the existing small regularization/shrinkage grid inside nested training; use
honest forward OOF base scores at every level and for final residual training.
Full-development base fits are used for deployment, not substituted into residual
training. Unexposed predictions remain exactly equal to the base.

| Arm | Additional information beyond common base/context |
|---|---|
| M | None |
| T | Validated-link presence, article count and age |
| R | T plus calibrated relevance |
| N | R plus corpus-relative novelty/history sufficiency |
| D, secondary | N plus online story dissemination |

All content arms use the same association gate, row IDs, fitting schedule and
baseline. The gate itself contains semantic information; T is a timing control
conditional on this gate, not a pure no-news control. Compare N with M and T for
joint news-content value, and N with R to isolate the contribution of novelty.
R versus T isolates relevance scores beyond the validated association decision.
Equal feature width does not guarantee equal capacity; report nested contrasts
and identical tuning budgets. Train-only content permutation is a negative-control
diagnostic, not an exchangeability-based significance test without its assumptions.

## 9. Experiment sequence and stopping rules

| Experiment | Procedure | Data/evidence required | Decision |
|---|---|---|---|
| E0 source recovery | Project rich metadata; reconcile recorded-news export; classify missingness | Historical IDs, rules/version evidence, news/run receipts | Publish coverage and admissible support before outcome access |
| E1 identity/link audit | Compare lexical, structured lexical, hybrid/reranked matcher on held-out annotations | Contract cards, two-reviewer labels, retrieval pools | Freeze one association model if precision/coverage tradeoff passes |
| E2 novelty audit | Compare last-20 LSA with full-history story retrieval and update labels | Seven-day PIT corpus, 300 audited pairs | Freeze one novelty representation; no jump-label tuning |
| E3 market benchmark | Nested forward comparison of logistic, spline and shallow trees | Opened admitted development prices/features | Select strong base by market-only scores |
| E4 incremental news | Fit M/T/R/N with identical rows/base; report paired LL/Brier/AP | Honest OOF scores and admitted links | At most N advances; failed prespecified content gates stop branch |
| E5 stratified analysis | Pooled models; report topic, venue and trailing-activity contrasts | Reviewed topics; activity bands fitted on training history | Secondary adjusted comparisons; report unsupported cells |
| E6 confirmation | One reserved later interval, frozen models and fixed analysis | Unopened scope outside V4/consumed intervals | Apply complete frozen hierarchy once |
| E7 transfer and diffusion | Family-held-out transfer; D ablation if predeclared support | Separate support and multiplicity allocation | Secondary findings; cannot rescue failed E6 |

Discovery `[2026-05-17,2026-07-22)` is already opened: use it transparently for E1–E5
development where admission allows. Its results cannot become new confirmation.
Confirmation dates are selected from an access/coverage ledger before labels;
historical data are eligible if truly untouched. Do not reuse V4's reserved
`[2026-09-06,2026-10-30)` or consumed intervals. No specific new interval is certified
by today's probes. If none qualifies, finish the retrospective study and reserve a
later independent confirmation; further future collection is conditional on that audit.

Proposed primary confirmation asks later-time performance on the admitted population;
markets may have earlier training history. New-family transfer is separately split,
with story/semantic-training exclusions. This explicitly relaxes V5's requirement
that the sole primary confirmation be simultaneously later and family-disjoint.
The paper must not describe the temporal test as unseen-event transfer. Outcome
horizons are purged at all time boundaries; preprocessing/calibration fit locally.

## 10. Inference: a concrete candidate and its limitations

Correct two earlier conversational shortcuts: daily aggregation plus HAC is not
automatic certification; a minimum family count does not establish power. The old
failed broad-dependence simulations remain valid evidence about those methods.
Human semantic review also cannot certify statistical independence.

Propose testing a sequential forecast-comparison procedure for the time-average
conditional expected score difference along the observed experiment. This changes
the inferential target from an unconditional mean over arbitrary future regimes.
It accommodates changing conditional performance, but does not promise narrow
intervals or market-universe generalization.

Candidate confirmation schedule: score a synchronized vector of market forecasts
every 30 minutes, aggregate with weights fixed before that round's outcomes, and
treat the vector as one round. This preserves arbitrary within-round dependence.
All prior scored outcomes must be observable before the next statistical round;
if source latency prevents that, use a proved delayed-feedback construction or
fail readiness. Do not apply an ordinary one-step theorem to overlapping five-minute
30-minute labels. Five-minute results remain descriptive secondary evidence.

Use a proved variance-adaptive bounded-score confidence sequence as a candidate.
For logistic loss `l(z,y)=softplus(z)-y*z`, `|d l/d z|<=1`. Therefore a capped
logit correction of magnitude <=1 gives an M-versus-news loss difference bounded
by 1; two capped residual arms differ by at most 2. Compute loss from stable logits;
verify the bounds and common probability handling in implementation. These bounds
may allow more informative intervals than bounding absolute log loss. They are
our proposed adaptation, requiring derivation/implementation review and power tests.

Use fixed alpha allocation for N–M, N–T and N–R; nominal novelty success requires
the N–R contrast. Retain the 0.001 nats/row useful-gain policy for N–M as a proposed
point threshold, with uncertainty and Brier guardrails separately specified. A
positive lower bound is not proof the gain exceeds 0.001. Failures remain harmful,
useful-gain-excluded, or inconclusive according to interval limits.

Primary reference: [Choe and Ramdas, Comparing Sequential Forecasters](https://arxiv.org/abs/2110.00115).
It motivates bounded, time-varying forecast comparisons; it does not directly
certify our synchronized-panel, gated, delayed-outcome implementation. Its lagged
forecast extensions require care. Keep the final scoring schedule and missingness
rule in the mathematical specification. Simulate the entire selection/confirmation
hierarchy under null, sparse exposure, strong common shocks, drift, outages and
plausible alternatives before admitting new labels; retain all failed screens.

## 11. Support, generality and prospective success criteria

Publish admitted counts by contract, event, split group, topic, venue, calendar day,
recent-news exposure, unique story and concentration. Compare inclusion/exclusion
profiles without using performance to choose the cohort. Stable source quality may
select a different population; disclose it rather than extrapolating with weights
whose selection probabilities are unknown.

Prior numerical floors (30 families, 28 days, 20 exposed families) are administrative
screening thresholds, not evidence that a dataset supports a publishable claim.
Report separate support for every transfer/topic assertion. At the old diagnostic
exposure rate 3.11%, a 0.001 all-row improvement requires approximately 0.0322
improvement on exposed rows when unexposed predictions equal M. Recompute this from
admitted support; it explains why millions of unexposed rows do not solve power.

Predefine the smallest relevant effect and desired power (proposed 80%), then
simulate using the admitted feature/exposure schedule and synthetic outcomes. A
failed power check means design infeasible/inconclusive at that effect, not permission
to remove integrity requirements or claim a universal absence of news information.

## 12. Immediate deliverables and changes requiring a new freeze

1. Use the 43 recovered Kalshi rule texts to update evidence packets, and expand
   Polymarket descriptions/subtitles with bounded keyset batches. Recover earlier
   metadata versions or guarantees before using them as historical features. See
   `data/v5/design_reassessment_20260915/RULE_EVIDENCE_NOTES.md` for inspected cases.
2. Repair the metadata schema/adapter to carry named outcomes and rule evidence;
   add canonical ID normalization at joins to prevent the observed prefix mismatch.
3. Produce contract cards and typed event/group graphs for the single-event cohort.
4. Build the 1,200-pair article-link audit and 300-pair novelty audit from opened
   history, with held-out human labels and documented sampling.
5. Resolve the news query/export bottleneck; build coverage/availability and access
   ledgers. Measure the surviving support before promising an experiment date.
6. Implement a versioned structured matcher, benchmark it against the lexical rule,
   and validate the proposed inference adaptation synthetically.
7. Freeze one complete V6 configuration and reserved confirmation scope, then run.

Keep the true offset learner, cross-fitting repairs, shared scoring rows, provenance,
failure history, single confirmation and exposure equality tests. Proposed changes
requiring the new freeze are: rich metadata/association, single-event primary cohort,
novelty definition, baseline selection policy, capped correction, temporal-primary
versus transfer-secondary split, recorded-feed estimand and sequential inference.
No forecast gain, source certification or sufficient confirmation data is claimed
by this proposal. The current research plans have not been rewritten.
