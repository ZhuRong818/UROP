# EventX V6: revised data and experiment plan

Date: 21 September 2026. Status: working revision requested by the user; **not a
research freeze or authorization to open protected evaluation data**. This is a
separate successor design, not an edit to the failed audit or earlier protocols.
V4, V5 v1.1, V2.3 and consumed evaluations retain their existing scope.

## 1. Research question and changes

Does source-available, market-relevant news improve prediction of the next
30-minute absolute canonical-YES executed-price movement beyond a strong market
baseline and the timing of news exposure?

The contribution is a controlled measurement and forecasting study, not a causal
effect of news, universal news coverage, or a newly invented retrieval architecture.
Novelty means novelty within the observed source history; publisher diffusion is
not social virality. KOL and social virality remain outside this revision.

Retain executed-trade prices, the existing target definition pending an exact
implementation/hash reference in the new freeze, honest cross-fitting, true offset
learning, common evaluation rows, provenance and one-shot confirmation. Do not
choose a new label definition after seeing its prevalence or performance.

Change these components:

| Earlier approach/problem | Revised approach |
| --- | --- |
| Strict direct/YES-proposition evidence dominates acceptance | Separate predictive relevance from settlement evidence; validate a new taxonomy independently |
| Article forced onto one threshold contract | Multi-label event/asset retrieval with explicit contract applicability and abstention |
| Rules concatenated into one similarity vector | Field-aware operative predicate, exclusions, source boilerplate and typed entities |
| More pair rows interpreted as coverage | Count unique articles, stories, event groups, exposed contract-days and concentration |
| Repeated local grammar repairs | One bounded comparison of complete linking pipelines with a declared stop decision |
| Broad historical download before feasibility | Target missing versions and overlapping event/news windows first |

This is a changed relevance endpoint, not a reinterpretation of the failed old
audit as successful. Existing reference judgments remain unchanged.

## 2. Evidence motivating revision

- The completed bounded audit had 39/40 conservative errors under its strict
  contract-specific criterion; family separation was inconclusive. Its cycle is closed.
- The latest development comparison has 134 cards, 128 with rules, and 185 screened
  pairs from 70 articles. Snapshot-before-article is not historical-version certification.
- Nine exact top-ID changes include three numerical near-ties. Inspection found
  one plausible Argentina topical repair, four Bitcoin-context switches without
  contract-specific justification, and four inapplicable Norway/Trump matches.
- No links from this comparison are admitted. These diagnostics neither establish
  predictive relevance accuracy nor show that news lacks incremental information.

Evidence: [bounded audit](BOUNDED_AUDIT_RESULT_20260917.md),
[comparison](ENRICHED_RULE_COMPARISON_20260921.md),
[nine-case inspection](RANK_CHANGE_INSPECTION_20260921.md),
[queue windows](QUEUE_WINDOW_AUDIT_20260921.md).
Canonical comparison: `data/v6/enriched_rule_comparison_20260921/report.json`.

## 3. Data plan: existing cache first, Lumid recovery second

Routes below are recorded in prior local source audits, not newly probed today.
Before fetching, verify the live schema/auth/query contract and archive the exact
request. No alternative source substitution, external LLM upload, or bulk fetch is
authorized by this planning document alone.

| Data | Source / route | Fields and intended use | Admission requirement |
| --- | --- | --- | --- |
| Contract versions | Lumid `/retrieve`, `prediction_markets.kalshi_markets` and `prediction_markets.polymarket_markets` | IDs, YES/NO subtitles, token mapping, question, rules, event/leg IDs, open/close/status, version/ingest lineage | Text/version and status applicable at decision time, not merely a current description |
| Event metadata | Lumid catalog then `polymarket_events` or recorded embedded event fields | Subject, fixture/release, metric, period, stage and source evidence | No invented IDs or unverified event table assumptions |
| News versions | Lumid `/retrieve` over `news.articles` | ID, headline, summary, publisher, URL, publication and availability clocks, source/run, symbols | Exact text availability under accepted assurance; explicit revision mapping and retained provenance |
| Trades | Lumid `/prediction-markets/trades/{venue}/{market_id}` or verified warehouse projection | Execution ID/time, YES/token mapping, price, size, arrival lineage | Complete bounded extraction, duplicates resolved, invalid/stale intervals identified |
| Coverage evidence | Lumid catalog/lineage routes and batch receipts | Feed/time counts, runs, page boundaries, failures and retention | Reconciled export of defined recorded feed, not a claim of all public news |
| Labels, links, stories, splits | Locally derived from the above | Evidence spans, versions, membership and split constraints | Separate algorithm output, reviewer reference and eligibility decisions |

Do not require L2, wallet data, tweets, or article bodies for this primary study.
Bodies are optional only after their content-version availability is established;
the headline/summary assurance does not automatically cover them.

### Recovery order and bounded scope

1. Build a contract-by-day support ledger from cached metadata, trades and news.
   Record supported, missing, retrospective-only and uncertain separately.
2. Reuse the 134-card recovery. Six rules and four end fields remain missing;
   fetch again only if a different field/version/query has a defensible chance of
   resolving the gap. Otherwise quarantine affected uses with a recorded reason.
3. Choose development event windows by data availability and topic/activity coverage,
   never jump outcomes. Report the selection bias of the current retrieval-selected
   sample. A broader coverage sample must include low/no-news and unretrieved events.
4. Recover full news windows for chosen support, not just articles returned by the
   current matcher. Search identifiers and typed aliases, retaining nonmatches.
   Preserve a seven-day source-history warm-up for the planned novelty feature.
5. Export bounded date partitions with stable keyset pagination, counts, hashes and
   source-run reconciliation. Failed/capped intervals are unknown, not zero news.
   Do not treat `/news/latest` as proof of complete historical coverage.
6. Fetch additional trades only for otherwise supportable windows. Publish unique
   event/story counts and usable exposure before scaling collection.

Use historical data wherever legitimate. Older publication dates do not establish
older availability, and opened history is development rather than confirmation.
No new confirmation interval is certified by this revision. Future collection is
needed only if the access/coverage ledger finds no suitable untouched history;
development work does not need to wait for that decision.

## 4. Structured data products

Every product carries schema version, input manifest hashes, code/config hash and
explicit development/eligible/reserved status. Raw evidence remains immutable.

- `contract_versions`: contract/event IDs; entity ID/type; named outcome; metric,
  comparator, unit, threshold; observation period, stage and deadline; operative
  predicate; exclusions; source boilerplate; quoted evidence offsets; availability
  and validity intervals. Unknown fields stay unknown.
- `article_versions`: raw and cleaned text hashes; masked sidebar spans; attributed
  speaker; typed entities; claim type (action, measurement, forecast, opinion);
  event time versus source availability. Opinions are not automatically unrelated.
- `article_event_links`: retrieval channels/scores; evidence; relation class;
  conflict/uncertainty flags; all supported event candidates, not forced top-one.
- `event_contract_applicability`: temporal eligibility, typed mechanism, period and
  metric compatibility; direct versus shared-context applicability with evidence.
- `coverage_ledger`: feed/day/export/status/version support and missingness reasons.
- `story_history`: online cluster state, first available report, update/repetition
  distinction, publisher identity and history sufficiency.

Entity/asset group, semantic event identity and evaluation split group are distinct.
All Bitcoin contracts need not be one semantic event. Shared articles create correlated
features, not proof of identical settlement events or independent forecast errors.

## 5. Linking algorithm and revised relevance endpoint

### Classify relevance before settlement support

Use these reference classes with explicit evidence:

1. **Event update:** information about the specified event, stage or measurement.
2. **Mechanism-relevant context:** a stated, predeclared connection to the contract
   subject/outcome, without claiming the settlement predicate has occurred.
3. **Incidental/unrelated:** only a shared name, generic topic or boilerplate term.
4. **Uncertain:** missing entity, event, rules or material timing evidence.

Store settlement evidence as a separate flag. A forecast-relevant article need not
prove YES. A Strategy Bitcoin sale can qualify as asset context for applicable price
contracts; it does not uniquely identify a $150k strike. An Argentina match update
may relate to a tournament outcome without proving tournament victory. Norway power
contracts do not describe its football team. A Trump mention does not establish a
target-word utterance; a separately evidenced speech/appearance mechanism would
require its own predefined rule, not a generic actor association.

Primary revised exposure may include classes 1 and 2 only after the **new** policy
passes validation; keep their features separate and report a class-1-only sensitivity.
Do not lower the old audit threshold or relabel its failures to obtain a pass.

### Compare exactly three development pipelines

| Candidate | Implementation | Purpose |
| --- | --- | --- |
| L0 | Preserve original lexical baseline; reproduce full-rule concatenation diagnostic | Quantify incumbent behavior |
| L1 | Typed subject/event retrieval plus separate operative fields and explicit compatibility rules | Interpretable field-aware baseline |
| L2 | Same typed candidate union plus pinned local dense retrieval/cross-encoder and evidence checks | Test added semantic ranking value |

Use identical cached articles, eligible candidate universe and reporting definitions.
L2 retrieval expansion must be reported separately from reranking gains. Similarity
is not a relevance probability. No model-generated references count as human gold.
Preserve negative/exclusion clauses for logical checking, but exclude generic
resolution boilerplate from positive lexical scoring. Unknown extraction abstains.
Use absolute score tolerance 1e-12 for numerical ties in normalized similarity;
this is not a semantic confidence threshold. Multi-label applicability is allowed.

Test invariance to boilerplate duplication/reordering, plus wrong entity type,
stock-versus-asset metric, absent target utterance, figurative/literal words, period
mismatch, expired contracts and missing metadata. Add unseen synthetic variants,
but never report synthetic success as real-data precision.

## 6. Bounded validation, not continuous annotation

First compare L0–L2 on opened development material and all candidate changes, not
only favorable cases. Publish accepted precision where references exist, abstention,
article/event coverage, uncertainty, and independent-example counts. Existing strict
labels cannot score the new context endpoint without new references; any relabeling
of opened examples is development-only and preserves the original record.

Before a fresh audit, freeze one pipeline, taxonomy, sample frame, sampling weights,
acceptance threshold, stopping rule and reviewer budget. Sample accepted links by
event/story clusters and probability-sample rejected/nonretrieved cases for misses.
Include wrong-type and same-asset/different-contract cases, but weight enriched
sampling correctly. Report recall only against the audited search frame.

Proposed acceptance policy: lower 95% precision bound at least 0.90 for admitted
links, with class-specific counts and conservative handling of unresolved judgments.
The sample size and simultaneous class-bound policy must be calculated from the
fixed frame/design before labels, not copied from the previous 40-case audit.
Use two independent score/outcome-blind reviewers and one adjudication round.
One fresh audit cycle; no redraw or expansion after failure to rescue the result.
If coverage/power is inadequate or the budget cannot support a valid audit, stop
before requesting reviews and report linkage feasibility, not forecast readiness.

Reserved old packets are not automatically valid new audit sets: recheck access,
story and family isolation without opening labels. Family uncertainty can be
co-isolated for splits but not represented as established semantic equivalence.

## 7. Predictive experiment after data/link gates

Retain the 30-minute target and strong market-only benchmark comparison (regularized
logistic, low-complexity splines, shallow trees). Select a single baseline architecture
using only admitted development market data and nested forward validation.

Fit news arms as true offset learners:

`p_A = sigmoid(logit(p_M) + E * clip(kappa * g_A, -1, 1))`.

All arms share rows, market base and exposure E; E=0 must give exact baseline
predictions within numerical tolerance. Residual training uses fold-local OOF base
predictions, never in-sample scores from the final full-development base model.
Tune regularization/shrinkage only within the training hierarchy. Refit the base
for deployment while retaining cross-fitted scores for residual training.

| Arm | Information | Contrast |
| --- | --- | --- |
| M | Market history/state only | Strong baseline |
| T | M plus validated exposure/count/age and matched market-context correction | Timing-conditioned recalibration |
| R | T plus validated relevance/claim-type features | R–T relevance beyond timing |
| N | R plus corpus-relative novelty/update/history-sufficiency | N–R novelty beyond relevance |

The common semantic gate already conveys content, so T is not a pure no-content
control. Interpret N–T as content features beyond gate and timing. Match fitting
budgets and contextual terms; content permutation is diagnostic, not an automatic
valid hypothesis test. At most N advances; T/R are prespecified controls, not fallback
candidates selected after N fails. Diffusion stays exploratory and cannot rescue N.

Novelty uses only prior available story history, with online clustering and no
retrospective reassignment of earlier features. Unknown warm-up is unknown novelty,
not novelty one. Deduplicate updates/syndication without deleting provenance.

## 8. Evaluation, strata and stopping

- Primary: later-time prediction on the declared supported cohort. Secondary:
  unseen-family transfer. Do not call the temporal test unseen-event generalization.
- Purge label horizons at every boundary and isolate shared story/family material
  where required. Freeze embargo and series policies before evaluation access.
- Primary loss: paired log-loss improvement on common rows; Brier/calibration and
  AP secondary. Report all-row and exposed-row effects with exact exposure weights.
- Topics and trailing trade-activity bands are prespecified secondary strata, using
  training-only cutpoints and pooled models. Do not search category-specific models
  or omit weak cells. Report independent event support and concentration per cell.
- Publish market/event-balanced robustness alongside row-weighted results. Neither
  many rows nor semantic group review establishes statistical independence.
- Existing failed dependence screens still block a confirmatory uncertainty claim.
  The predecessor's synchronized-round sequential inference is only a candidate:
  complete theorem/feedback/missingness checks and synthetic coverage/power tests
  before freezing it. Do not silently replace failed methods with ordinary bootstrap.
- Freeze alpha allocation across N–M, N–T and N–R. Joint content claims require the
  first two; novelty specifically requires N–R. Retain proposed 0.001 nats/row useful
  gain for N–M, distinguishing a point estimate from a lower-bound guarantee.
- If source, association, power or inference readiness fails, no predictive
  confirmation. If N fails development gates, stop this news branch; no new window,
  feature family or subgroup rescue within the same version.

V4 `[2026-09-06,2026-10-30)` remains protected. Consumed holdouts cannot confirm or
tune this revision. No labels, outcomes or receipt-controlled evaluations are opened
by this plan. A data-quality/methodology report remains possible if no supported
confirmation exists; a broad negative-news claim does not.

## 9. Execution order and deliverables

| Stage | Deliverable | Exit condition |
| --- | --- | --- |
| 1 — local, now | Typed/field-aware card and link schema; tie/invariance tests | Evidence-preserving extraction with explicit unknowns |
| 2 — local development | L0/L1/L2 comparison on fixed opened data; support ledger | Traceable improvements and adequate distinct exposure, not pair inflation |
| 3 — bounded recovery | Missing historical versions and full overlapping news windows | Reconciled source support; publish unresolved gaps |
| 4 — freeze audit once | Sampling protocol, executable evaluator and reviewer budget | Version-stable method and feasible audit before new judgments |
| 5 — audit | Held-out relevance/missed-link and boundary evidence | Prespecified acceptance; otherwise stop |
| 6 — modeling | M/T/R/N nested development and novelty diagnostics | Source, model, inference and power readiness |
| 7 — confirmation | Full manifest, access ledger, receipt and one-shot report | One untouched eligible scope; no post-result redesign |

Immediate priority is stages 1–2, not another broad annotation request, larger
forecast model, or unbounded download. Stage 3 can proceed on demonstrated gaps
without waiting for forecast outcomes. This revision creates no new dataset/model
version by itself; implementation and a new freeze remain outstanding.
