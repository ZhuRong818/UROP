# V6 relaxed development adjudication and next step

Date: 28 September 2026. This is a development sensitivity result on the fixed opened 102-pair packet. It is not the original-rubric reference, an independent audit, a source certificate, or a predictive result.

## What was adjudicated

The user attests that two distinct people completed the separate review files. Their original answers are preserved. A receipt fixed the 39 disagreement pairs, text, rubric and inputs before a single assistant adjudication pass. The assistant chose a submitted answer for each disputed field and recorded the article and contract evidence plus a reason. No agreement field was changed. There are 63 pairs with reviewer agreement, 39 assistant-adjudicated pairs and zero unresolved disagreements. This is **assistant adjudication**, not a third human review. The mechanical `reviewed.jsonl` merge differs from the adjudicated result on two retrospective-use fields only; it remains preserved.

The final relaxed labels are: relation 11 same episode/series, 36 shared mechanism, 12 generic topic, 43 incompatible; applicability 26 material predicate, 21 shared context, 55 not applicable; direction 14 supports YES, 24 supports NO, 64 mixed/neutral; retrospective use 74 usable and 28 limited. `usable` includes clear exclusions and does not mean a prediction-ready positive link.

Evidence: `data/v6/relaxed_adjudication_20260927/` (spec, predecision receipt, disagreement packet, choices, decision receipt, 39 reasoned decisions, 102 labels, report and manifests). The 102 pair IDs and 764 exact spans were verified in `data/v6/relaxed_review_intake_20260927_v2/`. The submitted relaxed fields differ from the original fixed rubric, so the original validator's 874 schema/field rejections remain applicable to the primary endpoint.

## What the labels support

The 102 pairs cover 40 articles and 54 contracts. All 54 heuristic-typed pairs were reviewed: 25 material predicate, 20 shared context and 9 not applicable. Of 24 sampled candidate abstentions, one is material, one context and 22 not applicable. All 24 sampled nonretrieved pairs are not applicable. The two latter strata are samples of 615 and 8,711 pairs respectively, so zero material labels in 24 nonretrieved examples cannot establish population recall. Repeated contracts around one article cannot be counted as independent news events.

The 26 material-predicate labels come from only five articles: 8, 8 and 7 labels from three Bitcoin stories, two from an Argentina story and one from a Musk pay story. Sixteen of the 26 also carry `shared_mechanism_context`. Those 16 are a **rubric boundary to resolve before defining positive linker gold**: an investment forecast or bull thesis may be useful context without directly measuring the contract predicate. All agreed human fields are retained as submitted; this diagnostic does not relabel them. Fourteen of 21 context-only pairs carry `supports_no`, so direction must remain distinct from settlement evidence. The reproducible cross-tab and source-status counts are in `data/v6/relaxed_adjudication_diagnostic_20260927/report.json`.

## Design decision and next action

Retain the fixed original semantic rubric as the primary planned endpoint. Use the adjudicated relaxed labels only for opened-development sensitivity and error taxonomy. Before any new linker freeze or independent audit, prospectively specify whether a relaxed `material_predicate_evidence` response is a positive link, how opinion/forecast, same-series price observation and two-leg contracts map to that endpoint, and how `shared_context_only` and unknown/missing fields are handled. Do not choose a favorable class mapping or threshold from these 102 labels. A fresh original-rubric submission would be needed to claim original-rubric reference labels.

The source gate remains separate and currently binding. In the scoped evidence, 5/9 article runs failed, no full-window feed certificate exists, and certified support remains 0/8,844 contract-days. The narrowed provider request is prepared in `eventx/release/v6/SOURCE_EVIDENCE_REQUEST_REVISED_20260927.md` and remains unsent. Obtain delivery, market activation/status, and completed-window/retry receipts; reconcile failed runs and zero-export intervals before treating zero articles as zero news. Then re-evaluate distinct eligible article/event exposure and feasibility under a frozen class map. No forecast fit, new independent audit, protected holdout access or V4 action follows from this adjudication.
