# Contract-aware selective matcher — separate redesign proposal

Status: proposed, not adopted or evaluated. V6 audit remains closed/nonpassing;
V4/V5 and frozen source artifacts unchanged. No additional annotation requested now.

## Objective

Return supported article–contract links, or explicitly abstain, using only information
available at decision time. Separate exact-proposition evidence, event background,
unrelated text and insufficient evidence. Semantic similarity proposes candidates;
it does not certify a link. The target is supplied-feed incremental information,
not universal news novelty, settlement prediction from text alone or social virality.

## Pipeline

1. **Certify inputs.** Preserve article content version, source availability timestamp
   and provenance. A contract needs historical existence/validity evidence and an
   as-of metadata version. Today's ingestion timestamp alone cannot certify historical
   availability. Missing or conflicting admission evidence means not eligible for
   predictive use, even if retrospective matching looks correct.
2. **Represent contracts explicitly.** Store typed entities and aliases, event/action,
   outcome candidate, metric/unit/comparator/threshold, observation interval/deadline,
   location/stage and resolution source. Attach exact supporting field/spans and
   known/unknown/conflicting status to each. Preserve parent/leg semantics; exclude
   unsupported compound contracts initially. Do not fabricate missing resolution rules.
3. **Represent article claims.** Extract typed entities, action/measurement, reported
   observation period and quoted evidence. Publication, ingestion and referenced-event
   time stay separate. Abstain when supplied text cannot support a useful interpretation.
4. **Retrieve within eligible development scope.** Union lexical and dense retrieval,
   preserving channel scores and IDs. Do not access reserved families to rescue a
   development match. Record eligible-universe size and whether no candidates exist.
5. **Check compatibility.** Explicit entity/metric/event/period contradictions reject
   a candidate. Ambiguous identity or critical unknown rules trigger abstention.
   Aliases must be typed (bank versus national team; WT versus WTI). Relevance can
   support YES or NO and need not establish the final settlement outcome.
6. **Rank compatible evidence.** Retain the existing reranker as a comparison, not
   proof of compatibility. Use a compact structured contract and cited article claim;
   log token retention. Distinguish background from proposition-specific information.
7. **Selective acceptance.** Return supported links or `no_supported_match` with a
   reason. Abstention is neither zero news nor a negative market outcome. Freeze any
   score/margin/calibration rules using development only; missing candidate evidence
   cannot be repaired by forcing top-one. No cutoff selected here.

## Small implementation sequence

First implement schema validation, evidence spans, deterministic identity joins and
time-gate utilities in a new module/version. Then typed contract/article extraction
for a limited set of explicitly declared contract types. Only then implement selective
matching. Do not start with additional large models or broad parameter searches.

Keep the current 40 cases as a disclosed regression/debug set, alongside synthetic
counterexamples. Rejection of bad cases is not sufficient: include positive examples
of relevant pre-event information, negative-direction evidence and valid aliases.
No automatic revised precision claim or admission to predictive training.

Required software tests:

- Entity namespace/alias collisions; differing company, agency and sports entities.
- Question plus subtitle identity; missing and conflicting rules fail explicitly.
- Wrong reporting quarter, disjoint event windows and post-close availability.
- Pre-event reports remain eligible when otherwise relevant; no settlement leakage.
- Article amendments and metadata versions cannot travel backward in availability.
- Correct pair IDs and reproducible score ordering/ties; no empty-pool forced match.
- Token retention for contract predicates and quoted claims; long-text failure explicit.
- Relevant evidence against YES accepted as relevance; exact threshold quotation not
  required; event-only background cannot silently become direct information.
- Abstention is recorded distinctly from confirmed unrelated content and source gaps.

## Future evaluation contract — requires approval and freeze

Do not recycle the opened 40 as independent evaluation or automatically release the
335 reserved preview pairs. Establish an untouched, appropriately separated article/
event population first, including no-match articles; certify its source and split scope.

Predeclare one candidate and at most one baseline comparison (current unconditional
matcher). Freeze architecture, thresholds, code, sampling, inference and a hard review
budget before opening new annotations. Sample articles independently of acceptance
so abstention cannot hide difficult inputs. If separately sampling accepted outputs
for precision, record inclusion probabilities and use the correct sampling design.

Report together:

- Precision among accepted links, with uncertainty.
- Article output coverage and abstention reasons over **all eligible articles**.
- Correct-link yield per eligible article; for multiple outputs, also report link counts.
- Temporal eligibility violations and sufficient-evidence rate.
- Performance by predeclared contract type/text sufficiency, descriptive when small.
- Retrieval recall only on a genuinely reference-enumerated subset; otherwise unknown.

Precision alone cannot pass an abstain-on-everything model. Before evaluation, approve
a precision target, a minimum useful coverage/yield and confidence requirement, plus
the maximum review budget. These values are deliberately not reverse-engineered from
the failed 40-case sample. If insufficient accepted examples exist, report inconclusive
or incomplete, not a perfect precision claim. No post-result sample expansion.

One permitted adjudication per disagreement, unresolved treated conservatively,
original denominators preserved. Stop on nonpass; a later method is another research
version. Predictive experiments require separate source, family/split and inference
gates even after a selective matcher passes.

## Decision now

Approve this narrow implementation scope and the chosen initial contract types before
starting a new matcher version. No fresh annotation is needed for the schema, synthetic
tests or development-only engineering. The current evidence supports redesigning
association acceptance, not concluding that news itself has no predictive information.
