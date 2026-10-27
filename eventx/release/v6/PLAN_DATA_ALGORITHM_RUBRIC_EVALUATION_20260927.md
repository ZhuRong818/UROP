# EventX V6: experiment, data, algorithm and rubric evaluation

Date: 27 September 2026. This is a read-only review of the current V6 working revision and opened development artifacts. It makes no change to frozen protocols, audit decisions, model weights, source records or admission status. No protected outcome, reserved review label or consumed holdout was accessed.

## Executive decision

**V6 is a coherent research direction but is not ready for a predictive freeze or incremental-news result.** Its strongest elements are the point-in-time question, strong market baseline, shared-row M/T/R/N contrasts, one-shot confirmation discipline and explicit abstention. Its limiting elements are absent certified exposure, no revised-context reference labels, incomplete event/story boundaries, no demonstrated useful link yield and an unvalidated dependence method. The fixed 70-article/134-card comparison is a candidate diagnostic, not a complete L1/L2 link evaluation.

| Gate | Current judgment | Evidence / consequence |
| --- | --- | --- |
| Scientific estimand | **Needs one decision** | The broad question asks if relevant news adds value beyond market history/timing, while N (novelty) is the only advanceable arm. T shares a semantic exposure gate, so R–T/N–T isolate features beyond that gate, not all content beyond timing. Prespecify the exact primary contrast and claim before a new evaluation. |
| Point-in-time source support | **Fail for admission** | 0/8,844 contract-days certified; 4,023 have only later metadata snapshots, all 66 days lack complete news-feed reconciliation, and historical market status/version validity is missing. |
| Revised link reference | **Missing** | No human gold for the new context endpoint; strict direct-proposition audit failed 39/40 under its old criterion and is consumed. |
| Retrieval coverage | **Unknown** | 70 articles were preselected through an earlier screen, candidate search uses only 134 cards, and nonretrieved articles/contract alternatives lack a probability-sampled reference. |
| Algorithm readiness | **Component diagnostic only** | 52 field-aware or 38 document-role typed hypotheses, zero admissions; dense adds no hypothesis-bearing article; ranking changes lack gold. |
| Independent-event support | **Unknown/inadequate demonstrated yield** | Original 52 hypotheses reuse 8 articles/13 contracts/7 provisional groups; group identity and clustering are uncertified. |
| Forecast/inference readiness | **Not ready** | No V6 fit, confirmed supported cohort, power calculation, untouched confirmation scope or dependence procedure that passed synthetic coverage screens. |
| Research integrity | **Strong separation, with disclosed legacy deviation** | Receipts/hashes and protected-data boundaries are maintained. The old bounded evaluator was implemented after annotations; its fixed mathematical rule and deviation are preserved. |

## 1. Experiment plan

### What is well designed

- The target is a 30-minute absolute canonical-YES executed-price movement beyond a market-only benchmark, not a causal effect claim. Development and confirmation are separated; consumed evaluations and the protected V4 interval are excluded.
- The proposed `p_A = sigmoid(logit(p_M) + E * clip(kappa*g_A,-1,1))` makes the news correction zero when validated exposure `E=0`. Fold-local out-of-fold market predictions for residual training, common rows, nested forward selection and label-horizon purging directly address leakage.
- M/T/R/N separates exposure timing, relevance and novelty more clearly than a single news-vs-no-news fit. The plan correctly discloses that T inherits a content-derived exposure gate. Reporting both all-row and exposed-row losses plus market/event-balanced robustness is necessary because news is sparse and rows share events.
- The plan states stop gates for source, links, power and inference and does not treat V4 or consumed holdouts as a rescue set.

### What must change before a freeze

1. **Choose the primary estimand.** The headline question is broad incremental news value, but section 7 permits only N to advance and section 8 emphasizes N–M/N–T/N–R. This makes a novelty-dependent system the de facto primary even if a simpler relevance signal is viable. Because T shares a semantic gate, R–T measures added relevance features conditional on that gate, not all content beyond news timing. For a clean beyond-timing estimand, define a source-certified exposure-only T without relevance filtering; otherwise state the narrower conditional estimand. Then choose in a new development-only revision whether relevance or novelty is primary. Never choose using a protected result.
2. **Define the supported population before performance.** Specify contract eligibility, verified feed universe, active-status interval, event/story split unit, decision-time grid, missingness policy and source exclusions. A result conditional on well-supported news windows is legitimate, but its population and selection bias must be explicit; a retrospective retrieval-selected cohort cannot define the target after outcomes are seen.
3. **Finalize the executable target and confirmation scope.** The revision defers an exact target implementation/hash reference. Freeze trade mapping, horizon, label construction, common evaluation rows, embargo and series blocking. Identify a genuinely untouched V6 confirmation interval separate from V4 and consumed tests; no such scope is certified now.
4. **Prove inference before testing.** Prior grouped-t and block candidates undercovered synthetic persistent/regime-shift data (reported 84.0–92.3% coverage in the handoff versus nominal 95%). Complete feedback/missingness assumptions and simulation coverage/power for a synchronized event/time design. Many trades do not supply independent news events.
5. **Set a feasibility stop before model fitting.** After certified sources and links, calculate distinct exposed stories, event episodes, supported contract-days, exposure concentration and detectable paired log-loss gain. The proposed 0.001 nats/row useful-gain threshold is a meaningful-gain target, not evidence that the supported cohort can detect it.

## 2. Data and source evaluation

The support ledger covers 134 retrospective cards × 66 UTC days = 8,844 contract-days. It finds 3,803 days with recorded trades and 1,441,723 trades, but only 169 days with a screened article pair and zero certified V6 support days. There are 2,505 days with legacy associations; these are unvalidated proxies, not V6 relevance. Two zero-export news days are not proven source-empty. The 134-card subset does not establish coverage of the 4,651-market development universe.

The latest 52 typed hypotheses concentrate in eight old articles. Sixteen pairs use a contract snapshot/rule ingested after the article. Two articles follow the paired contract's recorded nominal terminal. Only 28/52 pair rows have an observed trade on their article day; these are reused article/contract observations, not 28 independent exposures. Five of eight source runs are marked failed; retained rows are not thereby invalid, but complete feed capture is unproven. The user-relayed administrator assurance provisionally covers exact headline/summary at ingestion or updated revision time; its actual revision-availability field is unmapped, and it does not certify market metadata/status or feed completeness.

**Required data product:** versioned article and contract snapshots with exact text hash, first-seen/revision clock, validity interval, active/suspended/closed status, token/YES mapping, event/leg identity, source-run lineage and bounded feed reconciliation. Keep semantic review labels separate from source eligibility: a retrospectively meaningful article–contract relation may still be ineligible for historical prediction. If historical versions/status cannot be established, use opened history for development and capture a new prospective V6 panel with immutable at-arrival snapshots and receipts. Do not equate a later snapshot, publication time or zero export with usable historical exposure.

For any bounded news recovery, select event windows across topic/activity and low/no-news strata before viewing forecast results; retrieve the complete declared overlapping feed plus seven-day novelty warm-up, retaining nonmatches, duplicate/update lineage, failed pages and zero-row proofs. The current screened 70-article sample cannot estimate corpus prevalence or missed-link recall.

## 3. Linking and evidence algorithms

### What the current comparison actually tests

- **L0:** full-rule TF-IDF rank on the 669-pair union, with no acceptance gate. Long rules/boilerplate can dominate similarity; rank is not relevance.
- **L1:** question/subtitle TF-IDF on pairs where `field_aware.hypothesis` returns a typed status. The typing supports a few regex question patterns (speech, World Cup win, Bitcoin/Ethereum threshold) and article subject-plus-cue matches. Rule spans are recorded, but operative predicates, exclusions, thresholds and periods are not semantically checked in the L1 acceptance step. It is therefore narrower than the planned field-aware semantic linker.
- **L2:** the same typed union reranked by a pinned generic cross-encoder; no calibrated no-match decision or verified evidence binding. Dense retrieval adds 201 candidate pairs/11 typed hypotheses but no newly covered article or L2 top-set change. Five L1/L2 top changes are mostly Bitcoin strike/deadline switches unsupported by the article text. Historical model-cutoff eligibility is unverified.
- **Document-role v0.2:** a separate regex role diagnostic, not the fixed L1/L2 scorer. It removes 16 old statuses and adds two Argentina contexts, reducing 52 to 38 typed hypotheses. Seven dropped Bitcoin-thesis pairs may be recall losses; two Argentina additions have stage/year ambiguity. No gold says this is an improvement.
- **Other semantic components:** the NLI probe falsely accepted 3/10 unsupported assistant-authored cases; the structured-span run produced 0/10 valid records; constrained candidate IDs were 0/10 wholly correct and changed value under rotation in 19/30 groups. These are known regression probes, not real-world error estimates. None is a safe admission gate.

The algorithms are valuable as generators of **auditable candidates and reasons to abstain**. They cannot currently claim precision, recall or a forecasting feature. `selective_vnext` is explicitly a compatibility foundation for same-period measurements and returns no supported links; it does not complete the promised multi-type contract linker.

### Recommended algorithm sequence

1. Keep candidate generation separate from semantic classification and source eligibility. Search beyond the 134-card fixed subset for a probability-sampled development frame; retain all retrieval channel/score provenance and sample misses outside top five.
2. Use a typed article–event layer: identity, actor/subject, reported action or measurement, epistemic role (fact, forecast, opinion, quotation), episode/period and exact text spans. Map an event to possibly several contracts only through a predeclared applicability policy. A generic Bitcoin article can be shared asset context, never evidence for a specific strike or deadline without explicit support.
3. Implement deterministic hard rejections for verified wrong entity/type, impossible period, expired status and rule contradiction; make missing source/semantic facts abstentions. Treat reranker score as prioritization, not permission to accept. A final no-match decision needs a separately calibrated policy on development references.
4. Evaluate pipeline stages on the **same opportunity frame**: candidate recall, class-specific precision/coverage, false promotion, missed supported relations, abstention and unique article/story/event exposure. L0 versus L1 mixes representation and eligibility filtering, so top-rank counts alone do not isolate why one version changed.
5. Stop changing extractor architectures until human-reviewed development failures show which field or relation actually limits useful coverage. Preserve current failed trials as regression cases.

## 4. Rubric and audit design

The previous audit's success label required `direct` plus `yes_proposition` for a precise entity/event/period. It produced 39/40 conservative errors, including two unresolved disputes, on a fixed top-one development frame; this is a failure of that strict criterion **within that frame**, not a 97.5% universal false-link rate and not an evaluation of the newly proposed context endpoint. The revised plan permits event updates and mechanism-relevant context but has no completed human reference rubric or independent labels for those classes. “Mechanism-relevant” is presently too open to judge consistently across broad asset and sports news.

A new rubric should record independent axes, not one overloaded relevance word:

| Axis | Required judgment and evidence |
| --- | --- |
| Identity/episode | Same canonical subject/event, different event, or unknown; note team versus host country, company versus held asset, and syndicated story/update identity. |
| Claim role | Observed update/measurement, attributed report, opinion/forecast, quotation, or insufficient text. No automatic rejection of opinion; do not turn it into an observed event. |
| Relation | Direct contract-proposition evidence; explicitly stated event update; predeclared shared mechanism/asset context; generic topic only; incompatible; unknown. Require exact supporting spans and, for context, the stated mechanism connecting article to contract subject. |
| Contract applicability | Correct event, period, stage, metric, token side and threshold where claimed; shared-context applicability is distinct from a contract-specific claim. Multi-label is allowed with one shared article/story unit retained. |
| Settlement evidence | Separate `yes`, `no`, `neither`, `unknown` proposition evidence flag; no settlement inference from contextual relevance. |
| Timing/source eligibility | Separate verified, retrospective/unknown or invalid article/contract versions and active window. Semantic labels can be judged development-only even when source certification fails; predictive admission requires both gates. |
| Reviewer trace | Exact article/rule spans, text/version hashes, reason code, reviewer identity, independent answer and one recorded adjudication; missing summaries/rules produce unknown, not negative. |

For the development calibration packet, include all 18 changed statuses, the five L1/L2 top switches, unchanged accepted candidates, rejected same-subject alternatives, and probability-sampled nonretrieved articles/contracts across topics. Reviewers should not see ranker scores or each other's answers. Label units at article–event first, then contract applicability; keep article/story/event clustering in estimates. Report both human disagreement and unresolved counts.

After the policy is stable, freeze a **new** audit with inclusion probabilities for accepted, rejected and nonretrieved strata; two independent outcome-blind reviewers and one adjudication; prewritten evaluator; precision bound, missed-link search frame, coverage and stop rule. Compute sample size for the declared class-specific lower-bound target and independent clusters before labels. The old finite-frame family/story results do not certify the new relevance endpoint or all split boundaries. Do not redraw or relabel the failed audit into success.

## 5. Go/no-go sequence

1. **Now:** map provider revision field; seek bounded historical market version/status and feed-run proofs using the prepared local source request. In parallel, freeze the development-only two-axis rubric and sampling frame. No provider message was sent in this review.
2. **Next:** conduct bounded development review, estimate errors/misses by class and unique event/story yield, then implement only evidenced algorithm repairs. Keep the 40 old strict cases as opened development history.
3. **Then:** certify representative event windows and complete news capture; verify independent exposure and power. If historical proof fails, start a separate prospective V6 capture version with immutable snapshots instead of backdating current rows.
4. **Only if those pass:** freeze a new link/boundary audit and the exact M/T/R/N estimand, including whether T has content-neutral exposure or a shared semantic gate, plus target, split, model eligibility, inference and untouched confirmation scope. If the audit or power fails, stop predictive confirmation and write the feasible data-quality/methods result.

This evaluation changes no current acceptance or frozen outcome. The immediate bottleneck is **certified, independently reviewed exposure**, not additional trade rows or another neural ranker.

## Evidence inspected

- `CURRENT_STATE.md`; `eventx/release/v6/DATA_EXPERIMENT_REVISION_20260921.md`; `eventx/release/v6/BOUNDED_AUDIT_REVIEW_GUIDE_20260917.md`; `eventx/release/v6/V6_BOUNDED_AUDIT_AMENDMENT.md` (historical proposal, later approved and consumed via recorded adoption).
- Frozen old audit: `data/v6/bounded_final_audit_20260917/report.json` and `consumption_receipt.json`.
- Current data: `data/v6/support_ledger_20260926/report.json`, `data/v6/fixed_pipeline_comparison_20260926/report.json`, `data/v6/source_role_diagnostic_20260926/report.json` and linked manifests/receipts; release reports of the same names.
- Implementation: `eventx/v6/field_aware.py`, `document_roles.py`, `selective_vnext.py`; `eventx/tasks/compare_v6_fixed_pipelines_20260926.py`.
- Semantic feasibility: NLI, structured-span, candidate-ID and order-rotation trial reports; provisional news-content assurance; historical inference screen recorded in the handoff.
