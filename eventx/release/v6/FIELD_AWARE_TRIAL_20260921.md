# Field-aware plan: first local trial

Implemented separate `eventx/v6/field_aware.py` and reproducible task
`eventx.tasks.trial_v6_field_aware`. Original matchers and frozen artifacts unchanged.
Scope: first-pass stages 1–2, not the complete revised plan or predictive experiment.

## Execution and evidence

Fixed opened input: 185 pairs / 70 articles, 134 enriched cards. Prior comparison
output hashes and pinned local reranker weights verified before inference. New
manifest inputs/outputs verified afterward. Twelve new unit tests pass; 25 combined
field-aware/clean-speech/relation tests pass. No API calls, protected labels, audit
sampling or predictive training. Offline CPU reranker run completed.

Canonical outputs: `data/v6/field_aware_trial_20260921/` contains receipt, cards,
scores, tie-aware ranking sets, report and manifest.

## What was actually implemented

- Evidence-offset rule segmentation: 334 operative candidates, 105 exclusion spans,
  176 source-boilerplate spans, 315 unclassified spans. These are heuristic roles,
  not verified propositions. Full source evidence retained.
- Typed grammar hypotheses: 40 person-utterance, 27 sports-team, 10 asset-price cards;
  57 unknown. No automatic type certification.
- L0 retains full-rule lexical scores. L1 uses question/subtitle scores with typed
  context checks. L2 is the pinned neural reranker on the same candidate set/checks.
  Dense retrieval expansion was **not** run; this is only the L2 reranking component.
- Rule prose is removed entirely from positive ranking in this initial ablation;
  operative-rule semantic extraction remains unfinished. Exclusion segmentation is
  not a general logical-negation engine.
- Absolute 1e-12 tie handling; no forced unique winner on numerical ties. No score
  threshold is presented as a calibrated acceptance probability.

## Results (hypotheses, not accuracy)

| Quantity | Result |
| --- | ---: |
| Asset-context hypotheses | 32 pairs |
| Event-context hypotheses | 2 pairs |
| Abstentions | 151 pairs |
| Unique articles with hypotheses | 8 |
| Unique contracts with hypotheses | 12 |
| Unsupported adapter abstentions | 53 |
| Subject/relation-unverified abstentions | 35 |
| Target utterance absent abstentions | 63 |
| L0 articles with numerical top ties | 4 |
| L1 versus L2 different top sets | 4 |
| Predictive admissions | 0 |

No reference labels exist here for the revised context endpoint. More candidates
or different rankings do not establish improvement. Eight articles are not eight
independent events or sufficient forecast support.

## Inspected limitations and failures

All eight hypothesis-bearing article evidence spans were inspected after the run.
Bitcoin reports/commentary remain shared context, not strike-specific evidence.
Article 201756152 still yields context from “Buying Time ... New Bitcoin Playbook”:
the broad buy cue is vulnerable to figurative language. It never becomes a Bitcoin
price measurement, but this is a remaining context false-positive risk.

Article 152232532 produces Mexico and Iran World Cup hypotheses. The sentence says
Mexico will let Iran's team use Tijuana as a base. Country mention plus football
vocabulary is insufficient to distinguish host-country action from team evidence.
These two hypotheses are not certified relevant links.

Article 211869183's Argentina tournament match abstains because the team and World
Cup context occur across headline/summary rather than in the same sentence. Its
final/semifinal contracts are unsupported by the narrow grammar. This is a recall
failure of the implementation, not evidence that the article is irrelevant.

The new tests establish software behavior only. Their simplified stock-target
example does not catch the real figurative “Buying Time” headline above. Preserve
this failed generalization explicitly; do not describe all diagnosed errors as fixed.

## Next bounded work

Implement document-level entity-role binding with evidence spans: team versus host
country, asset versus company, and literal action versus figurative phrase. Permit
headline/summary coreference only with supported identity, not blanket concatenation.
Add these observed failures as development regression cases and separately test
unseen variants. Then complete the operative-field/dense-retrieval comparison and
support ledger before any new annotation or predictive training. No fresh audit is
ready from this first pass; data/version/family/inference gates remain unchanged.
