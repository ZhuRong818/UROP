# Dependency-parser evidence trial

Development only. Installed spaCy 3.8.7 and `en_core_web_sm` 3.8.0 in a separate
`.venv-parser`; the original `.venv` and frozen experiments are unchanged. Added the
isolated environment to `.gitignore`. Initial sandbox install failed DNS; approved
network retry succeeded. A missing Click import was repaired with Click 8.1.8;
`pip check` now passes. No research text was sent to an external service.

Model source: [official release](https://github.com/explosion/spacy-models/releases/tag/en_core_web_sm-3.8.0).
Model metadata records MIT licensing. Runtime packages, full model metadata and file
hashes are in `data/v6/dependency_evidence_trial_20260924/provenance.json`.
Historical availability remains uncertified; this run is retrospective development.
The [spaCy dependency documentation](https://spacy.io/usage/linguistic-features#dependency-parse)
describes syntactic annotations, not a guarantee of semantic role correctness.

## Implemented and run

Separate adapter: `eventx/v6/dependency_evidence.py`; runner:
`eventx.tasks.trial_v6_dependency_evidence`. Run with `.venv-parser/bin/python`.
Uses predicted part of speech, subject/object/passive-agent dependencies and noun
chunks rather than headline-specific string matches. Exports raw token/head records
alongside quoted candidate roles in the existing evidence schema. Forecast/speech
lemmas distinguish speaker from actor; embedded clauses remain status-unknown.
Missing objects, entity IDs, coreference, episode identity and relevance stay unknown.

Same 27 synthetic cases and 70 opened articles used. Prior input/output manifests
checked before execution; new input/output/model hashes checked after execution.
All emitted token/role spans checked against source text. No forecast training,
reserved labels, new association audit, source admission or protected outcomes.

| Measure | Grammar | Dependency parser |
| --- | ---: | ---: |
| Synthetic documents with predicate | 25/27 | 26/27 |
| Opened articles with predicate | 20/70 | 65/70 |
| Opened predicate candidates | 27 | 332 |
| Predictive admissions | 0 | 0 |

The parser emits multiple predicates per sentence; 332 versus 27 is **not** a
like-for-like precision gain or 332 validated claims. Coverage is not correctness.
Six targeted synthetic field checks pass: passive actor/object, postposed speaker,
no contraction-as-win, no nominal-win predicate, and forecast classification.
The existing 46 software tests also pass. These are development checks, not an
independent accuracy estimate.

## Inspection of prior real failure cases

Inspected parser output on all seven previously highlighted problematic article IDs:
102500031, 188829679, 189689909, 212074812, 214193749, 190263905 and 168034724.

- Correct speaker candidates now include Gemini Founder, JPMorgan and Apple CEO
  Tim Cook instead of the preceding proposition.
- “Won’t” no longer becomes “won”; sell-off and design/regulatory wins no longer
  produce the previous nominal-action mistakes in inspected cases.
- Strategy is separated from the auxiliary “has” in the sale summary.
- Remaining failures: `Coinbase` incorrectly tagged VERB in one headline; a WeRide
  compound yields spurious `co` and `-` predicates; partitive object “some of its
  Bitcoin holdings” reduces to “some”. The title-case Strategy sale headline has
  no extracted verb even though its summary does.
- Pronouns, reported-speech scope, nested propositions and temporal attachment are
  not resolved. Noun chunks are not canonical entities, and direct objects need
  not be the financially relevant asset.

## Decision / next step

Keep this as a more capable **candidate backend**, not a promoted linking algorithm.
Preserve the grammar failure and all parser errors. Next inspect extracted role
heads/complements systematically, retaining partitives, typed objects and attribution
scope with source evidence. Establish a fixed field-level development scorecard
(actor, object, speaker, proposition, negation and episode) before choosing backend
or acceptance policy. No independent annotation campaign is ready yet.

The broader retrieval/support ledger and source/family/inference gates remain
outstanding; this experiment does not unblock predictive training by itself.
