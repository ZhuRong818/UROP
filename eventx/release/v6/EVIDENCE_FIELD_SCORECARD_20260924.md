# Evidence-field development scorecard

Compared the unchanged grammar and dependency backends on 12 fixed synthetic
cases. References are assistant-authored and informed by previously opened
development errors, **not independent gold labels or an accuracy audit**.
The specification and hash receipt were written before inference; both backends,
predecessor outputs and pinned parser weights were verified against their manifests.

Artifacts: `data/v6/evidence_field_scorecard_20260924/`.
Runner: `eventx.tasks.score_v6_evidence_fields` (isolated `.venv-parser`).

## Results

| Field/check | Grammar correct | Dependency correct |
| --- | ---: | ---: |
| Actor (including required unknown for speech) | 8/9 | 9/9 |
| Object | 4/6 | 5/6 |
| Speaker | 2/4 | 4/4 |
| Proposition | 2/4 | 4/4 |
| Forecast/opinion status | 2/2 | 2/2 |
| Negation detection at selected predicate | 0/2 | 2/2 |
| Exact year mention | 1/1 | 1/1 |
| Reject specified nominal/contraction predicate | 0/2 | 2/2 |

Denominators are individual field checks, not independent observations. No pooled
accuracy is reported. Predicate alignment uses exact source offsets, not the
best-scoring extracted claim. Text scoring ignores only terminal punctuation and
whitespace. Missing predicates, missing fields and incorrect values are separate
in `scores.jsonl`; all outputs are retained in `extractions.jsonl`.

Dependency's object failure is `some` instead of `some of its copper holdings`.
Grammar reverses postposed speaker/proposition, misses selected negated predicates,
includes the time adjunct in the quarterfinal object, and mistakes nominal wins
and the beginning of won't for predicates. No backend was changed after scoring.

All 24 backend/case span-and-abstention checks pass. Six evaluator tests pass;
a combined run of evaluator, structured-evidence, document-role, field-aware and
clean-speech modules passes 45 tests. Zero predictive admissions.

## Limits and next implementation step

These checks support retaining dependency parsing as a development candidate,
not deploying it as a relevance classifier. Negation detection is not scope
resolution; a year mention is not event identity. Pronoun surface extraction is
not coreference. Two targeted false-predicate checks do not measure all spurious
predicate errors. Entity and episode identity remain unknown throughout.

Next implement a **separate version** of compositional role-span extraction:
retain noun heads together with evidence-backed partitive/complement structure,
while separating time adjuncts and attributing embedded propositions. Compare it
against these unchanged backends, with general structural contrast cases and the
same opened real articles. Do not add headline-specific exceptions or treat this
known failure suite as independent validation. Complete the broader retrieval and
source-support comparison before requesting another bounded independent audit.

No new data fetch, human annotation, training, protected outcome access, holdout
consumption or source/family certification occurred. Existing research gates stand.
