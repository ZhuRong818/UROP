# EventX final report review

Reviewed 28 October 2026: `EVENTX_FINAL_REPORT_DRAFT_20261101.md` and `report/build_report.js`.

The report has a credible research contribution and a clear two-track structure, but is not yet ready for submission. The central June gains are supported by the stored results. The main weaknesses are inaccurate method descriptions, overinterpretation of descriptive analyses, and a reproduction workflow that does not validate the actual report text. These can be corrected without fitting models or opening any additional evaluation block.

This was a source and stored-artifact review. Consumption receipts were checked before reading completed evaluation summaries. No evaluation, capture, model fitting, bootstrap recomputation, live process change, or full reproducibility run was performed. The existing DOCX was inspected structurally and an existing render contact sheet was inspected visually; those outputs are older than the current builder, so this is not final layout approval. External literature citations and institutional formatting requirements were not independently audited.

## Findings requiring correction

### 1. The news bootstrap sample size is wrong

Locations: draft line 47; builder line 218.

Both say that the bootstrap resamples 4,651 markets. The canonical `data/v3_1_historical/news_bound_20261027/result.json` records **2,290 market clusters**, 1,460,454 OOF rows and 2,000 draws. The 4,651 figure describes the wider study cohort, not the number of contributing bootstrap clusters. Report both denominators explicitly.

The stored upper Brier-improvement bound is correctly rounded: -0.00019586714212149262 to -0.000196. However, “even the most favourable value the data allow” is too absolute for a confidence bound. Use “the one-sided 95% market-cluster bootstrap upper bound is below zero, conditional on this cohort and resampling design.” The 9% skill-loss statement divides this bound by a point-estimated skill denominator; it is not a joint confidence interval for a skill-loss ratio. Describe it as a scale comparison.

The moderate-effect simulated promotion probability is 0.8553, not certainty. Replace “would have been found” with the actual simulated detection probability. The bootstrap is post hoc on development predictions and does not establish a general absence of news value. Shared events and dates can also induce dependence across market clusters.

### 2. The permutation analysis does not identify the source of the performance gap

Locations: draft lines 94–98; builder lines 283–285 and 337.

The stored result does show that jointly permuting booster-only inputs increases log loss by 0.012636484627481381, equivalent to 21.363% of the original booster–logistic gap. But this is a sensitivity calculation for an already-fitted booster, not an additive decomposition into feature access and nonlinearity. Permutation also breaks relationships with unpermuted features, including deterministic relationships between midpoint and logit midpoint, and between signed and absolute changes.

Replace “most of the advantage therefore comes from ... nonlinearly” with “the fitted booster remains better than the activity-logistic baseline under this perturbation; the experiment does not isolate the contribution of nonlinearity.” A matched-feature learner comparison belongs in a separately designed development study, not a refit on consumed June blocks.

Likewise, a wider range of predicted probabilities demonstrates sharpness, not by itself statistical resolution or the source of the score gain. ECE 0.046 versus 0.052 does not establish that calibration contributes nothing to the advantage. Describe the reliability plots and prediction spread without claiming a score decomposition.

Low importance of numerical age features does not reduce the need for accurate clocks: eligibility, as-of input selection and emission deadlines still depend on time. The V01 failure was a runtime readiness failure, not evidence that age features harmed prediction.

### 3. The report changes the historical pass rule in its description

Location: builder lines 252–257.

Section 5.5 presents one common four-condition pass rule, including a positive contract-bootstrap lower bound. The frozen June 1–7 protocol instead makes that interval **secondary, analysis-only**; its pass rule is lower LL than activity logistic and global rate, with no higher Brier. The June 8–14 protocol does include the positive bootstrap lower bound.

Evidence: `eventx/release/v7/june_replication_20261026/protocol.json` versus `eventx/release/v7/new_identity_test_20261026/protocol.json`. Describe the rules separately. Both results can remain favourable; the distinction matters because the report makes preregistration a central contribution.

### 4. Baseline and feature definitions need correction

Locations: builder lines 243–251 and 388–398; draft lines 13–19 and 67.

The implemented activity-logistic indices are `[0,2,7,10,11,13,14,16,17]` in `eventx/tasks/research_v7_change_probability_20261025.py:28`. They select midpoint, **spread**, log valid updates, and absolute changes plus missing flags at 5/15/30 minutes. Appendix A incorrectly lists **source age** instead of spread.

The same source, lines 58–59, computes `valid_state_fraction30` as the count of valid states divided by the count of states in the trailing window. It is **not the fraction of elapsed time covered by valid states**, as Appendix A says.

The primary June evaluators list five models: global rate, market rate, activity logistic, row_hgb7 and legacy_hgb7. They do not include an 18-feature full logistic model. V03 has a separate full-logistic comparator. Give each table row an explicit model and comparator identifier rather than “activity/full-feature logistic.” Do not describe every baseline as fitted on identical training rows: the legacy booster is loaded from a different, earlier bundle.

### 5. Cohorts and metric signs are mixed

Locations: draft lines 10, 42, 49–53 and 71–76; builder lines 212, 229 and 264–269.

The draft combines the all-cohort June count (20 contracts, 18,677 outcomes) with development50 scores (18 contracts, 16,453 outcomes). The canonical result distinguishes:

| June 1–7 cohort | Contracts | Known | Booster LL | Logistic LL |
|---|---:|---:|---:|---:|
| development50 | 18 | 16,453 | 0.2930988249673845 | 0.3522500571887579 |
| all | 20 | 18,677 | 0.29476444702877586 | 0.3527238030835776 |

The Word table correctly uses development50, but the surrounding 17/20 wins and nonoverlap/strict results refer to the all cohort. Label that transition. Similarly, the development missing-outcome bound and all-cohort bound differ. A worst-case lower bound below zero does not prove that *every* missing label must be adverse to reverse the result.

Define improvements explicitly: Brier improvement = Brier(B0) minus Brier(B1); LL improvement = LL(baseline) minus LL(candidate); AP change = AP(candidate) minus AP(baseline). The table heading “B1 minus B0” cannot govern all three. A negative Brier improvement means the raw Brier score increased. The V5 -0.000871 quantity is described in the cited research report as a **log-loss improvement**, so calling it a negative raw LL change reverses its apparent interpretation.

Evidence: `data/v7/june_replication_20261026/evaluation/result.json`; `MARKET_NEWS_RESEARCH_PROGRESS_20261007.md:91`.

### 6. Several summary claims exceed their stated scope

Locations: draft lines 11 and 66; builder lines 165, 197–203 and 348.

- The target compares the endpoint midpoint at t+30 minutes with the midpoint at t. “Changes within 30 minutes” is different: a quote can move and return to its starting value, giving target zero. Use “differs 30 minutes later.”
- “Every model was frozen before any evaluation block” cannot include May 9 development, which is explicitly repeatedly used and part of refitting. Separate development from frozen-model evaluations.
- Quote freshness and spread rules are Track B rules, not rules shared by every news/trade experiment. Scope Section 3.2 accordingly.
- “15–20%” applies approximately to the two headline activity-logistic comparisons; it does not describe gains against every rate and legacy baseline. For example, June 1–7 gain versus legacy HGB is about 10.8%.
- Treat “beats every baseline in every evaluation block” as a narrowly scoped matched primary-score claim, not a universal result across subgroups, robustness subsets, pending runs or statistical intervals.
- The introduction promises every test was frozen and consumed exactly once. State this as the intended protocol with explicitly disclosed exceptions, not a universal historical fact.

### 7. The claimed reproduction guarantee is stronger than the checker

Locations: builder line 422; draft final paragraph; `eventx/tasks/verify_report_reproducibility_20261027.py:142` and `:207`.

`check_claims()` compares a hard-coded list of 14 numbers against artifacts. It never reads either reviewed report source or the generated DOCX. A changed report number, sample size, method description or baseline name can therefore leave this check passing.

The overall `pass` expression checks mismatches but **does not check `with_missing`**. Missing manifest files can be listed without making the overall result fail. Figure comparison also iterates names in the after-state, so a removed figure is not necessarily detected as changed.

Describe the current checker as selected artifact consistency and hash checks. A stronger checker should require all referenced files, compare both figure-name sets, and validate report content or generate its claims from one shared artifact-backed data source. No full checker run was made in this review because it includes rendering and optional analysis work during the protected live window.

### 8. The appendix gives the wrong live evaluator

Location: builder line 428.

The report names V02b as the live result and says V02 is unevaluable, but Appendix C still directs the reader to V02 health and evaluation entry points. Update those entries to V02b and distinguish reproduction of stored results from irreversible once-only evaluation. Previously consumed June evaluation commands should not look like generic commands a reader may rerun.

The abstract and conclusion also use completed-three-day-run language while the results remain pending. Keep a clear as-of date until close-out supplies an actual result or failure. Resolve the project-number and acknowledgement placeholders before submission; retain explicit pending outcomes until the authorized close sequence completes.

### 9. The document pipeline has already drifted

`build_report.js` embeds an independent full narrative; it does not parse the Markdown draft. The current DOCX contains no “V02b”, whereas the current builder does. The existing DOCX/PDF are dated 27 October and the builder was edited on 28 October. Earlier render sheets are also stale. Final layout cannot be certified from them.

The static TOC requires the pagination workflow; `node build_report.js` alone reads existing page labels and can produce an outdated TOC after edits. Automatic table numbering coexists with manually written in-text references such as “Table 5,” creating another drift risk. A final pass should build, paginate to convergence, render and inspect the actual submission artifact.

The builder uses 10-point table text despite its introductory comment describing an at-least-11-point requirement. Confirm whether that minimum applies to tables. Page dimensions in the existing DOCX are A4; no page-size defect was found.

## Research and writing assessment

The strongest parts are the explicit research questions, separation of news increment from quote activity, the held-out new-identity evidence, preserved operational failures, and the refusal to equate forecasting scores with trading profits. The endpoint target, fixed baselines and stored receipts support an assessable research result. Algorithmic novelty is appropriately not claimed.

For an academic reader, strengthen the explanation of why predicting quote activity is useful even without direction or profit. Describe target discovery honestly as exploratory and the June studies as subsequent checks. Add a compact study table with training dates, evaluation dates, model version, comparator, contributing cohort, known/unknown counts, primary rule and deviations. Include definitions of LL, Brier and the sign of a gain. This will be more useful than repeating the full operational incident narrative in the body, lessons table and appendix.

The related-work section is a reasonable foundation but broad. The report needs a sharper comparison with closely related quote-activity forecasting and prediction-market news studies to establish what is new about this application and evidence. This review did not verify bibliography details or claim the literature coverage is complete.

The defensible central conclusion is: **simple news-count augmentation failed the specified development promotion gates; a frozen quote-change booster improved matched historical scores against the specified baselines on two June blocks, including a new-contract cohort; prospective performance remains pending.** That conclusion is sufficient for a substantive UROP report without the stronger attribution claims.

## Completion order

1. Correct counts, feature definitions, metric signs, cohort labels, and per-study pass rules.
2. Narrow the permutation, calibration, news-bound and universal-integrity language.
3. Correct V02b reproduction instructions and the checker's claimed scope.
4. Insert authorized close-out results or explicitly report failure/insufficient data when available.
5. Synchronize the two narratives, resolve administrative placeholders, rebuild/paginate and inspect the final DOCX/PDF.

No report source, frozen model, protocol, or evaluation artifact was edited as part of this review.

## Follow-up review of the revised report

Rechecked the draft and builder modified on 28 October at 10:47 local time. Most substantive findings above
are now addressed: cluster count, metric signs, cohort denominators, block-specific pass rules, logistic
feature list, valid-state fraction, baseline training provenance, permutation/calibration qualifications,
V02b commands, once-only command labels and the stated scope of the consistency checker.

Lightweight verification: all 24 literal claim values in the revised checker agree with their stored JSON
artifacts within its stated tolerances. This comparison used Python AST extraction and JSON reads only,
after checking completed consumption receipts; it did not import/run the checker or recompute any score.
`node --check report/build_report.js` passed. Source inspection confirms missing files now fail the checker
and added/removed figures are compared using the union of names. The full checker was not run.

Remaining corrections are chiefly wording and finalization:

1. **Residual attribution claim (builder line 336).** “The permutation analysis shows that its advantage
   does not rest mainly on inputs unavailable to logistic regression” still draws an attribution conclusion.
   Replace with “The perturbed booster retained lower log loss than the activity-logistic baseline; this
   sensitivity check does not partition the causes of the original performance gap.” This matches §6.4.
2. **Summary scope (draft line 11).** “18 ... features ... activity-logistic ... every evaluation block below”
   still includes the 14-feature V03/full-logistic rows and unevaluated pending rows. State that the completed
   frozen-model evaluations improved matched LL against their specified comparators; distinguish V03.
3. **Target and motivation (builder line 233).** “Whether the quote will change at all” still suggests an
   any-movement-within-window target. Use “whether its midpoint will differ 30 minutes later.” A failed
   point-forecast model on a narrow cohort does not establish that “point accuracy was the wrong question”;
   describe the unsuccessful model and subsequent exploratory change of target without that generalization.
4. **Category interpretation (draft category introduction; builder line 286).** Positive category-level
   gains support “gains appear across all observed categories,” but do not establish that no category
   dominates the aggregate weighted gain. Use the narrower descriptive statement.

The DOCX and PDF are still dated 27 October 13:41, before the revised sources. The DOCX contains neither
“V02b” nor “2,290”; it does not represent these corrections. Final build, pagination, visual inspection,
authorized pending outcomes, administrative placeholders and the full consistency check remain outstanding.
No rebuild was attempted during the protected live window. Source revision date should also be updated
from “written 27 Oct” to include the 28 October revision.

Assessment: the revised source is substantially more defensible, with the principal factual/methodological
errors corrected. It remains a draft; the generated submission artifact is not yet current. This follow-up
changed only this review and project handoff/log, not the report, checker, models or evaluation artifacts.
