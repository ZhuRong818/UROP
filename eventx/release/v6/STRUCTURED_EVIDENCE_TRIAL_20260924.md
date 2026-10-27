# Structured evidence: schema implemented, grammar feasibility failed

Date: 24 September 2026. Development only; no independent audit or forecasting.

## Deliverables

- Separate `eventx/v6/structured_evidence.py`: actor, speaker, object, predicate,
  proposition, epistemic status, polarity, voice, time/stage mentions and explicit
  unknown identity/episode fields, each candidate backed by exact source offsets.
- `eventx.tasks.trial_v6_structured_evidence`: fixed-input comparison with prior
  binder outputs preserved alongside structured records.
- `data/v6/structured_evidence_trial_20260924/`: 27 synthetic cases and 70 opened
  articles covering the same 185 candidate pairs, report and manifest.
- Nine new unit tests; 46 combined tests pass. All emitted evidence spans checked
  against source text; input/output hashes verified. These tests check software
  behavior, not field correctness. Earlier matchers and their artifacts unchanged.

No dependency parser was installed locally; cached models are embedding/reranking
models, not structured extractors. This first extraction backend uses a small
domain-independent active/passive clause grammar, without contract-name or headline
exceptions. It is a diagnostic backend, **not a usable general semantic parser**.
No model downloaded, external API used, protected outcome opened or link admitted.

## Results: extraction coverage, not relevance accuracy

| Input | Documents with predicate candidate | Interpretation |
| --- | ---: | --- |
| Synthetic actions | 9/9 | Includes relevant and irrelevant examples; not nine correct links |
| Synthetic opinions | 8/9 | Speaker/proposition represented; embedded object stays unknown |
| Synthetic event stages | 8/9 | Includes wrong-episode examples |
| Opened articles | 20/70 | Low real-text grammar coverage |

Opened text produces 197 sentence/clause records: 27 have predicate/proposition
candidates, 170 have unknown epistemic status. Candidate roles: 12 actor, 15 speaker,
11 object. Synthetic grammar coverage does not measure extraction correctness;
the examples were already opened during design.

Year diagnostics: synthetic 18 unknown / 7 overlapping / 2 disjoint; opened pairs
168 unknown / 15 overlapping / 2 disjoint. These compare explicit year mentions,
not actual event dates. No agreement certifies an episode; no disjointness alone
proves irrelevance. Source arrival timestamps are never invented as event dates.
All relevance remains unassessed; **zero predictive admissions**.

## Inspection of every opened predicate candidate

All 27 predicate-bearing records inspected. Serious failure modes remain:

- Article 102500031: “Bitcoin Bull Thesis ... Says Gemini Founder” reverses the
  speaker/proposition, treating the preceding thesis as speaker.
- 188829679: “Won’t Matter” is incorrectly parsed as a `Won` predicate (in both
  headline and summary). Word-boundary matching is not grammatical tokenization.
- 189689909: nominal “Sell-Off” becomes a sale predicate.
- 212074812 and 214193749: nominal regulatory/design “wins” becomes a verb.
- 190263905: postposed attribution “..., Apple CEO Tim Cook said in April” absorbs
  the earlier proposition into the speaker span.
- 168034724: “Strategy ... has sold” leaves the auxiliary in the actor candidate.
- Quoted, compound and indirect headlines often yield long, noncanonical role spans.

The schema correctly avoids calling a whole opinion complement the canonical
object; that object remains unknown. Passive purchase and simple subject-first
forecasts work in unit examples, but cannot compensate for the real-text errors.
Exact quoted spans prove provenance, **not semantic truth**.

## Decision

Keep the evidence schema, validator and fixed comparison harness. Do **not** promote
the grammar backend, convert these candidates into accepted features, or patch each
headline until the comparison looks better. Existing relevance decisions unchanged.

Next meaningful implementation: plug a pinned dependency/semantic-role parser or
schema-constrained local extractor into this same schema, with its model provenance,
license and historical-availability limits recorded. Evaluate subject/object heads,
attribution, negation, passive voice and episode binding separately. This requires
acquiring a suitable extraction model; the current reranker cannot supply roles.
Validate on fresh synthetic variations plus opened real text before any independent
audit. Keep uncertain/coreferential objects unknown. No new reviewer queue is needed
for the present failed feasibility backend.
