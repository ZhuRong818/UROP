# EventX macro review results and recommended next steps

Date: 10 October 2026. Scope: the two corrected 120-pair V7 response files. This is a development diagnosis of assistant annotations, with user-attested distinct reviewers. It creates no adjudicated labels, independent gold benchmark or forecast result.

## Assessment

The reviews identify a small set of plausible contract-specific statements, but the packet does not yet provide a diverse, timely information-shock dataset. The most useful next step is to repair evidence-role and episode definitions, inspect a bounded diagnostic queue, and measure how many actual information events remain usable before another forecasting experiment.

The identity correction succeeded: the files use `Reviewer_A` and `Reviewer_B`. Both retain their recorded assistant type. The existing human-review intake therefore remains incomplete. This does not prevent descriptive development analysis; it limits what these annotations can establish for a paper.

## 1. What the reviews agree on

| Field | Same answer | Agreement | Interpretation |
|---|---:|---:|---|
| Applicability | 98/120 | 81.7% | Useful broad agreement, with 22 relevance-boundary disagreements |
| Direction | 109/120 | 90.8% | Includes many non-applicable/ambiguous cases; only five jointly signed pairs |
| Evidence role | 13/120 | 10.8% | Definitions and annotation scope are inconsistent |
| Novelty | 120/120 | 100% | Every answer is `unknown`; no novelty signal has been established |
| Prediction-market odds content | 112/120 | 93.3% | Eight differences come from two articles about traders' expectations |
| Episode key | 78/120 | 65.0% | Raw strings compare descriptions of different kinds of events |
| Duplicate reference | 120/120 | 100% | Every answer is null; this does not establish absence of duplicated reporting |
| Public surprise | 120/120 | 100% | Every answer is `unknown`; no timestamped independent expectation was supplied |

Every pair differs on at least one of these fields. This is driven chiefly by role and episode fields, and does not mean every relevance judgment is disputed. These are descriptive agreement counts, not accuracy estimates or statistically independent observations.

### Applicability counts

| Label | Reviewer A | Reviewer B |
|---|---:|---:|
| Exact predicate | 5 | 5 |
| Material context | 27 | 33 |
| Topic only | 56 | 43 |
| Incompatible | 31 | 39 |
| Unknown | 1 | 0 |

Both reviewers mark the same five pairs exact. Their combined exact-or-material intersection is 30 pairs, drawn from 14 articles and 22 contracts. At least one reviewer marks 40 pairs material or exact, from 17 articles and 29 contracts. Ten pairs cross the material/nonmaterial boundary; this binary boundary agrees on 110/120 pairs. Another 12 applicability differences concern topic-only versus incompatible.

Among the 30 jointly material pairs, direction agrees on 29 and evidence role on only nine. The five jointly signed pairs all belong to the exact-predicate set. Fourteen articles are not fourteen verified independent information episodes.

## 2. The five exact matches become much smaller after timing checks

| Article | Jointly exact pairs | Supplied evidence | Timing diagnosis |
|---|---:|---|---|
| `173603179`: strong jobs data | 1 | Reports May payrolls of 172,000 against a 100,000 threshold | Conservative feed availability is after nominal contract close |
| `184027675`: bank stocks ahead of Fed meeting | 2 | Reports an expectation of an unchanged 3.50%–3.75% target range | Both pairs arrive after nominal contract close |
| `189435511`: Bank of America rate-path forecast | 2 | Forecasts a first 25 bp hike in September, relevant to June/September predicates | Both fit nominal landmark/horizon bounds; one contract snapshot follows article availability |

Thus five signed pairs collapse to three articles; only two pairs fit the nominal prediction window, and both reuse one analyst forecast article. One of those two has an earlier descriptive metadata snapshot. These are feasibility checks, not historical activity/version verification or independent information-event validation. All three articles are associated with failed source runs; this requires delivery reconciliation and does not by itself prove their content invalid.

The strongest completed-data statement is therefore that some supplied texts can be linked to exact predicates. It is not evidence that new, usable news predicts subsequent prices. Across the whole pilot, publication-to-conservative-feed lag has a median of 226.000252 minutes, and all 30 articles have lag above 90 minutes. This packet is poorly suited to measuring immediate reaction at the first public release. It could inform a narrower study of remaining adjustment after observed feed access.

## 3. Main review-quality gaps

### A. Role combines different questions

Reviewer A assigns an article-level role even to unrelated pairs. Reviewer B records `unknown` on all 82 pairs it marks nonmaterial, and tends to use `attributed_reporting` for material reports. A report can simultaneously describe an official measurement, attribute it to a source, and include commentary. The current single-choice categories mix the nature of the information with how it was reported.

Example: the Bank of America forecast is `opinion_or_forecast` for A and `attributed_reporting` for B. Both descriptions can apply to the same sentence. Similarly, a payroll measurement repeated in a news report can be official data and attributed reporting.

**Proposed new schema:** separate claim kind (measurement/action, forecast, commentary, expectation), source identity/type, and article-to-contract applicability. Define whether a role describes the entire article or the selected contract evidence. Preserve the existing responses and rubric as version 0.1; a revised schema is a new development version.

### B. Market expectations are being treated as prediction-market odds

Reviewer B marks eight pairs from articles `171511251` and `184027675` as market-odds content; A marks none. The supplied texts describe traders bracing for hikes or expecting unchanged rates. They do not explicitly quote Polymarket/Kalshi odds or a prediction-market probability.

**Recommendation:** distinguish general market expectations from explicit prediction-market-derived reporting. Require a supporting quotation and identified market/probability before flagging the latter. This is an analyst diagnosis, not an adopted correction to either review.

### C. Structured predicate coverage differs sharply

A supplies 646 nonnull predicate-component spans; all match the supplied contract bytes. B leaves all predicate components null on all 120 pairs. Null is permitted, so these are not malformed records, but B has not provided the structured predicate coverage needed for a component-level linking benchmark. A's exact span matches also do not prove its component assignments are semantically correct; some metric/action spans cover the entire question.

**Recommendation:** define when a missing component is genuinely unavailable and when explicit contract text must be annotated. Score component completeness separately from span validity. Require a reason for null fields on exact/material cases, with a consistent minimal-span policy.

### D. Episode keys often identify the contract outcome rather than the news event

A describes a Bank of America forecast episode; B assigns June and September FOMC outcome dates to its two exact links. Those are different objects. The supplied forecast publication and the eventual target decision cannot be used interchangeably as the unit of independent information.

**Recommendation:** retain separate `contract_event_id` and `information_episode_id`, with source, action/release, reference period, information timestamp and duplicate lineage. Unknown timestamps remain unknown. Normalize formatting only after establishing that two descriptions refer to the same information event. Do not interpret 42 raw-string disagreements as 42 distinct substantive episode disagreements.

### E. Broad keyword routing still admits unrelated material

Examples include payroll-software companies and sports sponsorships, a company named CPI FIM, and Fed stress-test/capital-return reporting. The packet also includes a Mexico unemployment contract despite its intended U.S. macro scope. These expose routing/domain gaps, and provide useful development negatives. They must remain in the current packet; removing difficult cases retrospectively would change its population.

**Recommendation:** implement a separately versioned domain/claim router based on entity, institution, metric and reference period. Compare its retention and abstention with the unchanged BM25 baseline on future event-disjoint development samples. Do not claim improvement merely from discarding errors in this reviewed sample.

## 4. What retrieval counts suggest

| Sampled stratum | Pairs | Both material/exact | Both exact |
|---|---:|---:|---:|
| BM25 top one | 30 | 10 | 3 |
| Ranks 2–10 alternative | 30 | 8 | 2 |
| Ranks 11–20, rejected by top-one policy | 30 | 8 | 0 |
| Outside top 20 | 30 | 4 | 0 |

The alternative sample contains two jointly exact matches and several context links. This supports comparing candidate retention plus predicate checks against unconditional top-one selection. Outside-top-20 context matches suggest potential retrieval misses under the broader material-context definition; no sampled outside pair is jointly exact.

These are unweighted counts in four deliberately enriched strata, not production precision, global recall or evidence of improvement over the old V6 audit. Different packets, criteria and reviewer provenance prevent that comparison.

## 5. Recommended execution order

1. **Inspect the prepared 32-pair diagnostic queue across 13 articles.** It contains all 22 applicability differences, the signed-direction difference, eight odds-content differences, and the five jointly exact pairs, with overlap removed. Prioritize the five exact pairs and two odds-disputed articles. This is a diagnostic queue, not an official adjudication packet or replacement for the full review requirements.
2. **Publish rubric/schema version 0.2 with explicit examples and null rules.** Separate claim role, source attribution, prediction-market quotation, information episode and contract event. Preserve v0.1 labels. Obtain any required independent review/adjudication before presenting final benchmark accuracy or gold labels.
3. **Build a source-clock and episode ledger on opened development evidence.** First enumerate the two timely exact links and the 20 jointly material pairs fitting nominal landmark/horizon bounds. Record shared articles, release times, analyst forecasts, duplicated coverage, contract versions and trade freshness. Do not count overlapping five-minute rows as extra news events. Unresolved source cells remain uncertainty fields for exploratory analysis.
4. **Run one small exploratory forecasting contrast after automatic features exist.** Use the stronger market model with neutral exposure/timing controls, then add verified signed evidence. Compare the same observation keys and include stale-price/liquidity diagnostics. Human explanatory annotations may support an explicitly labeled oracle diagnostic; they are not automatically deployable features. Novelty and public surprise need actual prior information before being modeled as measured features.
5. **Only then select a confirmatory V7 design.** Establish actual event yield and empirical paired-loss scale; repair dependence-aware coverage/power before choosing an untouched evaluation interval. Keep the frozen V4 task unchanged through its 30 October close.

The immediate intended result is a defensible estimate of usable distinct information-event yield and a clear extraction specification. A subsequent exploratory result should show whether signed contract evidence improves matched log loss beyond market history, exposure and timing. No forecasting gain can be inferred from the present agreement statistics.

## Artifacts and method

- [Machine-readable comparison](data/v7/macro_review_diagnostic_20261010/report.json)
- [All 120 evidence/response comparisons](data/v7/macro_review_diagnostic_20261010/comparison_cases.jsonl)
- [32-pair priority diagnostic queue](data/v7/macro_review_diagnostic_20261010/priority_diagnostic_cases.jsonl)
- [Analysis implementation](eventx/tasks/review_v7_macro_responses_20261010.py)
- [Official intake result](data/v7/macro_review_intake_20261010_distinct_ids/report.json)
- [Frozen development rubric](eventx/release/v7/pilot_20261010/ANNOTATION_RUBRIC.md)

Method: join both corrected files to unchanged pair IDs; count agreement and label distributions; describe strata using the prespecified selection ledger; inspect joint exact matches against the existing source/nominal-window diagnostics; check structured predicate spans against supplied text. Input manifests and output hashes are recorded. Semantic examples above are evidence-visible assistant analysis, not a third independent review. No responses were merged or overwritten, and no protected outcome, forecasting evaluator or software test was opened or run.
