# V6 opened-development context review guide

Date: 27 September 2026. **Development calibration only.** This packet is not a new audit, independent accuracy estimate, historical source certificate, or predictive admission. The old strict direct-proposition audit remains closed and failed.

## Packet and sampling frame

`data/v6/context_development_review_20260927/` contains the fixed `spec.json`, presampling receipt, 102-row score-blinded `semantic_packet.jsonl`, two blank response copies, private `selection_ledger.jsonl`, separate `source_context.jsonl`, a nine-article/15-contract `provider_scope.json`, report and manifest. Input/output hashes verify. It uses only the fixed 70 opened articles × 134 retrospective cards (9,380 possible pairs). The 669 candidate pairs contain 54 pairs typed by either the field-aware or document-role heuristic. All 54 are in the packet; a fixed-seed simple random sample adds 24/615 candidate abstentions and 24/8,711 nonretrieved pairs. The packet spans 40 articles and 54 contracts. “Typed” means a heuristic hypothesis, never an accepted human link.

This frame can diagnose misses within these 70 articles and 134 cards. It does not estimate recall over all news or all 4,651 development contracts. The selection ledger records stratum membership and inclusion probabilities, but must not be shown to reviewers before labeling. No model scores, prior labels or source clocks appear in the semantic packet.

## Semantic rubric

Judge only the supplied headline/summary and contract question/subtitle/rules. A missing summary or rule is **unknown evidence**, not a negative fact about the full article or market. Cite exact text spans for a positive relation and for decisive exclusions. Do not infer a contract's observed result, price, or post-article outcome.

| Response field | Allowed labels | Decision rule |
| --- | --- | --- |
| `semantic_relation` | `same_event_update`, `shared_mechanism_context`, `generic_topic_only`, `incompatible`, `unknown` | Same-event update needs the specified subject and event/episode. Shared context needs a stated action, measurement or mechanism tied to the contract subject. A common name, country, company or asset alone is generic. Wrong team/actor/stage/episode is incompatible. Missing identity or material text is unknown. |
| `contract_applicability` | `direct_proposition`, `shared_context_only`, `not_applicable`, `unknown` | Direct requires evidence about the contract's entity, predicate and relevant period/stage/metric; explicit strike/deadline when a strike/deadline claim is made. Shared context can apply to several contracts but does not select a strike or prove YES. Wrong identity/period/type is not applicable. Missing rule/status evidence is unknown. |
| `claim_role` | `observed_action_or_measurement`, `attributed_report`, `opinion_or_forecast`, `quotation`, `unknown` | Label the **cited article span**, not the whole story. State in rationale if multiple roles occur. An opinion or reported speech can be contextual but must not become an observed action or settlement fact. |
| `settlement_evidence` | `yes`, `no`, `neither`, `unknown` | A separate flag about what the cited text directly says for the precise proposition. This is not a resolution label or a forecast. Shared asset context normally has `neither`. |
| `identity_problem` | free text or null | Name company-versus-asset, team-versus-host, ambiguous alias, episode/year, stage, quoted speaker or other identity problem. |
| `uncertain_reason` | free text or null | Explain what missing supplied text, rule, identity or period prevents judgment. |
| `article_evidence_spans`, `contract_evidence_spans` | arrays | Each span should name the field, exact quote and character offsets in that field. Quoted presence does not alone prove semantic binding. |

Examples: “Mexico hosts Iran's team” is not evidence that Mexico's team wins. A story about Strategy stock receiving a Buy rating is not a Bitcoin purchase. “Bitcoin holdings/redemptions” may be shared Bitcoin-price context but does not identify which threshold contract applies. “Argentina's late win” with no match or stage may be World Cup context but cannot establish a semifinal or tournament-win proposition. Reviewers should preserve uncertainty rather than guess.

## Independent procedure

1. Give one reviewer `semantic_packet.jsonl` plus `reviewer_A_blank.jsonl`, and another the same packet plus `reviewer_B_blank.jsonl`. Do not share the selection ledger, source worksheet, ranker outputs, earlier answers or forecast outcomes. Record actual distinct reviewer IDs; automated suggestions do not count as independent human reference.
2. Each reviewer fills every pair once, retaining IDs and embedded article/contract text. Label meaning on the retrospective supplied text **before** inspecting source clocks. An article can be semantically related yet historically ineligible.
3. Validate IDs, enumerated labels, exact quoted spans, hashes and completeness. Preserve both original response files. One adjudicator may review disagreements once, with reason and evidence; unresolved remains unknown. Do not force agreement or replace sampled cases.
4. After semantic review, join `source_context.jsonl` to classify article text version/availability, contract rule/version/status and feed completeness as verified, retrospective/unknown or invalid. Those axes are distinct from semantic relevance. No source field is certified by this packet.
5. Report pair-level labels plus unique articles/stories/provisional groups, class-specific errors, abstentions, reviewer disagreement and selection-frame limits. Inclusion weights may describe this fixed 70×134 frame if judgments are complete; they cannot create corpus-wide recall or independent-event power. Do not choose a favorable model threshold or freeze a new audit from these labels without a separately versioned plan.

## Audit and forecast gate

The **next independent audit is not sampled** by this packet. Before any such draw, freeze one stable linker, exact endpoint and class mapping, source-eligible population, accepted/rejected/nonretrieved inclusion probabilities, family/story isolation, reviewer budget, lower-bound target, stopping rule and prewritten evaluator. Currently zero V6 contract-days are certified for prediction, so no audit pass, forecast fit or power claim follows from packet preparation.
