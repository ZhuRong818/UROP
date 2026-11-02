# Final PDF review — 2 November 2026

Reviewed: `report/EventX_UROP_Report_preview.pdf`, 67 pages, SHA-256
`d86090d878a3860b719525f0616c10e3837f960447cb6e11d551148149e55bd0`.
Page references below are PDF viewer page numbers; printed main-text page = PDF page minus 10.

## Overall assessment

The report contains substantial, credible UROP research and a stronger empirical contribution than the earlier June-only version. The history-stack confirmation, independently tested segment hypotheses, and subsequent segment-aware stack test materially improve its value. It is suitable for final submission after a focused correction and presentation pass. I would not submit this exact PDF unchanged.

Its strongest contribution is an auditable investigation of when pooled quote forecasts improve on each contract's own activity history, under realistic availability and missingness constraints. Its main weaknesses are inconsistent summaries, incomplete isolation of the source of predictive gains, and limited external and operational validation. The work supports an applied empirical paper direction; the present evidence does not establish a broadly superior learning algorithm or readiness for a top-tier general ML methods paper.

| Dimension | Assessment | What matters most |
|---|---|---|
| Evaluation integrity | Strong, with disclosed exceptions | Preserve failures, receipts, uncertainty and deviations; make global claims agree with those exceptions. |
| Predictive evidence | Substantial within the specified populations | Later tests beat the online rate; the final stack improvement is smaller and conditional on observed endpoints. |
| Baseline strength | Much improved, still incomplete | Recent default learners help contextualise performance; matched tuning and stronger history-only controls remain missing. |
| Novelty | Useful empirical and evaluation contribution | State-dependent incremental predictability is more defensible than algorithmic novelty. |
| Practical value | Plausible, untested | Predicting any midpoint change does not demonstrate useful monitoring, actionable direction or profit. |
| Literature positioning | Broad enough for UROP | Synthesis and precise distinctions will add more than another long list of models. |
| Writing and presentation | Readable but insufficiently consolidated | Correct stale statements, simplify repeated evidence and remove visible unfinished material. |

## What is scientifically strong

1. The simple online contract rate genuinely challenged the original interpretation, and the report preserves that result. It correctly says an interval crossing zero is not evidence of equivalence.
2. The new-cycle history stack answers the resulting operational comparison on later dates and new contracts: 13.3% lower log loss on 51 contributing contracts, followed by 10.5% on 78 more. These are stronger primary evidence than the retrospective modern-baseline benchmark.
3. Segment discovery was followed by a separately frozen confirmation. Both recent-move and wide-spread interactions passed the reported Holm adjustment. A later segment-aware stack improved log loss from 0.3083 to 0.3006, approximately 2.5%, with a positive contract-by-date interval on known endpoints.
4. Coverage, unavailable endpoints, failed runtime versions, calendar reuse and the V4 audit amendment are disclosed. The report distinguishes issued-forecast accuracy from overall coverage.
5. The v8 section explicitly admits that six LOBO folds train on later dates and that the remaining forward fold had already been opened. It presents e2e_hx as a development candidate. Preserve this qualification everywhere.
6. The news result is useful when restricted to the actual representations, availability rules and populations tested. The poor transfer of all V4 models is an important limit on interpretation, appropriately stated in the body.

## Corrections before submission

### 1. Align the central contribution and summaries with the experiments

**Pages 1–3, 11–12, 51, 54.** The official title still promises “Novel Information versus Social Amplification,” but this distinction is not established by the completed experiments. If the official project title must remain, clearly distinguish it from the report's actual research scope. A suitable research subtitle is “Auditable Prediction of Short-Horizon Quote Activity: Contract History, Market State and News Baselines.”

Lead the contributions with the evaluation framework and the confirmed market-state/history findings. Describe the news result as a scoped negative finding. The introduction calls the news work a historical test over 4,651 markets; clarify that the B1-versus-B0 promotion comparison is development out-of-fold evidence and that the V3.1 final holdout evaluated B0 only. The later conclusion already makes this distinction better.

The abstract's attribution that “pooled quote information added value” needs qualification. The full stack beats the raw online rate, but it also introduces fitted calibration and history length. A matched fitted history-only control is needed to isolate the incremental contribution of the quote-model input. This does not invalidate the stack-versus-rate result; it limits the mechanism that can be inferred from it.

Suggested defensible sentence: “A frozen combination of the quote forecast, online rate and history length improved on the online-rate reference in two subsequent tests on new contracts.”

### 2. Correct the universal modern-baseline conclusion

**Pages 3, 12, 43–44 and 51.** “Recent learners did not provide a stronger reference” is too broad. Sundial improves on the online rate in all seven evaluated blocks, with positive intervals in four. The stack is better on the three blocks where it was available. Tier A, B and C do not establish one universal ranking under identical inputs, training resources and evaluation grids.

Suggested replacement: “Under the specified default configurations, the four tabular comparators did not beat row_hgb7. Sundial improved the history-only reference across all seven blocks, while the frozen stack remained better on their three shared evaluation blocks. These retrospective comparisons do not establish superiority over tuned alternatives.”

Remove the implication that Sundial's useful information is already captured by the online rate. Its improvement over that rate demonstrates a stronger history forecast; whether it contributes to a stack has not been tested. Preserve the disclosed random internal validation, 100,000-row Tier C limit and binary-series adaptation caveats.

### 3. Fix the sample-size label

**Page 20, both benchmark and v8 rows of Table 1.** The seven stored Tier A prediction files contain **268 distinct market IDs**, **285 contract–block appearances**, and **506,723 scored rows**. “285 contracts” incorrectly suggests unique contracts. The May and first-June cohorts overlap.

Use “268 distinct contracts; 285 contract–block appearances; 506,723 known-outcome rows.” The modern benchmark and v8 text also calls these “issued rows”; distinguish scored known-endpoint rows from all issued forecasts. In v8 each fold trains on six blocks, not all 506,723 rows simultaneously.

### 4. Reconcile the safeguards and threats with the completed study

**Page 17, §3.2.** The absolute statement that protected calendar windows prevent any Track B experiment reading them conflicts with the expressly authorized V3.1 calendar-period reuse in §6.9. State the exception here and point to Appendix B. Define evaluate-once per frozen confirmatory evaluation; later disclosed analyses of already-opened forecasts do not make a block untouched again.

**Pages 52–53, §8.2.** “1 June–12 July in four blocks,” “18–35” contracts and “seven dates per block” describe earlier evidence. The historical series now includes seven blocks spanning 13 May–8 August, with as many as 78 contributing contracts and 18 dates in a block. Retain limits on one venue, one era, correlated decisions and small numbers of independent periods. Distinguish unseen event IDs from transfer to new thematic families or regimes. Add the V4 audit change and calendar reuse to the deviation summary.

### 5. Correct method details that disagree with code

**Page 63, Appendix A; page 17.** The quote-state implementation examined permits `0 < bid <= ask < 1`; the report says strict `bid < ask`. Describe the actual rule, including allowed locked quotes, or document any model-specific difference. Do not silently change code to match prose.

**Page 63.** `hour_sin` and `hour_cos` are included in the 14-feature V03 list but lack the asterisk. Clarify that all three features in each lag group carry the designation.

**Page 63.** “All logistic models standardise inputs and use C = 0.1” is false for `stack_lin`: its source uses `LogisticRegression(C=1.0, max_iter=2000)` directly on logit predictions and log-history, without StandardScaler. Restrict the existing statement to the baselines it actually describes and add the stack settings.

**Page 45.** The frozen features include 5-, **15-**, and 30-minute differences. The text omits 15 minutes. Add a compact model-specification table containing transformations, fixed settings, training population, validation scheme and calibration for the original models, stacks and v8 candidates.

### 6. Tighten claims about missingness and mechanisms

**Pages 35 and 52.** Coverage-stratified gains among issued forecasts cannot rule out selection bias. “No issued forecast on a contract-day” is not equivalent to “no valid quote at all.” Current end-date metadata and absent forecasts do not conclusively distinguish inactivity from capture failure. Say that the issued-row diagnostics found no attenuation with lower coverage; performance on never-issued decisions remains unidentified.

**Page 46.** Replace “the per-contract offset mostly adds noise” with “the chosen offset worsened mean development log loss relative to its own base model.” One fixed prior/drift configuration does not identify why it failed or establish redundancy.

**Page 41.** Statements about the moments that matter most for monitoring should be framed as motivation. No fixed-budget monitoring experiment has demonstrated operational value.

**Page 34.** “Nothing was refit or regenerated” should refer specifically to frozen model predictions. New online-reference predictions and diagnostics were computed.

### 7. Clarify numerical semantics and checker scope

**Table 4.** Its “B3 − B0 … improvement” labels conflict with the declared comparator-minus-candidate convention. The reported negative gains correspond to **B0 minus B3**. Correct labels rather than changing the values.

The V4 sample log-loss improvement is **−0.0007820175801352969**; the bootstrap distribution mean is **−0.0010648107136676324**. They are distinct valid fields, not contradictory results. Use the sample estimate as the reported point gain and identify the bootstrap mean if shown. The existing interval is [−0.005220399678695418, 0.0012149741050878856].

**Appendix C.** The checker reads completed holdout result JSON files, so “reads no holdout” should mean no unopened holdout inputs or new evaluation. Its 105 numeric/source checks do not certify every table, cohort label, mechanism or rendered-PDF statement. Expand checks to important counts and semantic labels when editing the report, without rerunning consumed studies.

## Presentation fixes

- **Page 5:** remove the highlighted “Add further acknowledgements if any.” instruction.
- **Pages 1–2:** resolve `[Department of Computer Science]` brackets if they are placeholders. Project number and supervisor are already populated.
- **Pages 3–4:** the abstract body is approximately 338 whitespace-delimited words. The software/hardware heading spills onto an otherwise almost empty second page. Shorten and reflow; confirm any institutional word limit rather than assuming one.
- **Table 1, pages 18–20:** legible but dense. Separate cohort/evidence status from long pass-rule text; move exact rules to the methods or appendix.
- **Table 9, pages 36–37:** keep the two model rows together if possible. Check Table 15 across pages 43–44 and the orphan incident row on page 50.
- **Pages 34, 36, 41 and 45:** long code/path strings and full justification create excessive spaces. Put implementation references in compact nonjustified blocks or the reproducibility appendix.
- Avoid splitting individual bibliography entries, such as the Gorishniy entry across pages 58–59. Reduce nearly empty spillover pages where practical.
- Add page numbers to lists of tables and figures if the template permits.
- The six figures emphasise older news/June evidence. Add one central evidence timeline and a paired-effect plot for the later stack tests. Use within-block gains and intervals; do not imply model progress by comparing raw log losses from different cohorts.
- Visual inspection found no obvious clipped text, overlapping table cells or missing glyphs. Targeted larger renders of pages 19, 35 and 44 were readable. The main problem is density and pagination rather than broken rendering.

## Comparison with stronger published research

The comparison is about the contribution and evidence structure, not a prediction of acceptance.

- **General ML methods papers:** TabM introduces a specific architectural technique and supports it with broad performance/efficiency evaluation and empirical analysis. EventX uses established models and offers a narrower domain finding. Beating defaults on one application does not substitute for a new general method or broad evaluation. [TabM, ICLR 2025](https://proceedings.iclr.cc/paper_files/paper/2025/hash/c1ba41c694834aeef91ae161711d4939-Abstract-Conference.html).
- **Baseline methodology:** RealMLP explicitly studies strong pretrained/default hyperparameter choices. This makes the default baseline exercise relevant, while also making exact implementation, preprocessing and resource parity important. The remaining gap is a controlled comparison of inputs, adaptive history and model class, selected using forward development splits. [Better by Default, NeurIPS 2024](https://proceedings.neurips.cc/paper_files/paper/2024/hash/2ee1c87245956e3eaa71aaba5f5753eb-Abstract.html).
- **Benchmark papers:** ForecastBench's future-question design and continuing evaluation illustrate the value of a reusable prospective evaluation resource. Its outcome-forecasting task differs from EventX's short-horizon quote-activity task. EventX's benchmark route would require documented data access, stable tasks/splits, usable release artifacts and external reproducibility beyond a local hash check. [ForecastBench, ICLR 2025](https://proceedings.iclr.cc/paper_files/paper/2025/hash/ea74e45a229dac70b5b63b28d8934db6-Abstract-Conference.html).

The best near-term positioning is an empirical market-microstructure/evaluation study: strong simple history references narrow apparent ML gains, and additional value depends on market state. That could support a focused applied paper after broader prospective and decision-level validation. A top-tier benchmark submission would need a substantial reusable resource; a methods submission would need additional methodological novelty and broader evidence.

## Highest-value future research, in order

1. **One clean prospective confirmation of e2e_hx**, frozen before new outcomes, with enough independent contracts and dates, robust capture, reported abstention and endpoint coverage. Its retrospective 4.0% gain is promising but not confirmation.
2. **Matched history-only and input/model controls:** rate plus history-length logistic/GAM, a prespecified recency-weighted rate, then the same fitted comparator with quote-model information. Match training data, temporal validation and tuning budgets. This isolates adaptation, calibration, added information and flexibility. Sundial is another useful history-only comparator, not a required ingredient of every future model.
3. **Fixed-budget monitoring utility**, with stale observations and refresh costs represented correctly. Measure distinct movements captured or latency, not repeatedly counted overlapping labels. This tests the practical value of the chosen target.
4. **Broader transfer:** more periods, liquidity regimes, event families and eventually venues. Plan precision using clusters and dates, not the 506,723 row count.
5. **Reproducible release and off-host backup:** manifests protect integrity, but an off-host verified copy protects availability. Release a usable harness and a data-access recipe within source permissions.
6. **News only after measurement improves:** independently reviewed event–contract links and evidenced first-availability times, before richer text models. Separate the news branch from the primary quote-forecast contribution if preparing a shorter paper.

More literature review can help, but another large bibliography is not the current bottleneck. Add a compact positioning table covering target, information set, temporal safeguards, history baseline, transfer design and decision utility. Explicitly distinguish short-horizon quote activity from eventual-event probability, trade-price jumps and equity-order-book direction. Keep Hawkes-inspired counts and approximate dynamic-logistic offsets labelled as adaptations of established ideas.

For the submission deadline, the best return comes from correcting and consolidating existing evidence. New model searches would add risk and clutter without repairing the present writing or establishing new confirmation.

## Review scope and verification

- Read the extracted text across all 67 pages; visually inspected all-page contact sheets and selected larger page renders.
- Read the canonical handoff and relevant protocols/source sections; checked consumption receipts before inspecting completed evaluation artifacts.
- Independently checked all **105** registered claim values against stored JSON and their literal presence in both Markdown and builder: **105/105 passed**. Exact-string matching to PDF extraction found 79; the remaining strings include layout/format differences and are not counted as factual failures. This is not a complete automated PDF semantic audit.
- Counted distinct IDs from the seven existing Tier A TabM output files, reading only the identifier column: 268 distinct IDs, 285 block appearances, 506,723 rows. No labels were scored and no forecasts were generated.
- Inspected the completed benchmark flags/results and V4 sample versus bootstrap values. No frozen evaluation, bootstrap, fitting, capture, model selection or full figure-regeneration checker was rerun.
- Sources and PDF were not edited. This review and the handoff/history record are the only intended durable changes from the review.
