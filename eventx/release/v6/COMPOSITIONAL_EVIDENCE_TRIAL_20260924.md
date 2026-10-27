# Compositional evidence trial 0.1

Implemented separately in `eventx/v6/compositional_evidence.py`; grammar and
dependency predecessors remain unchanged. Runner:
`eventx.tasks.trial_v6_compositional_evidence`, using `.venv-parser`.

## Algorithm

Extend a syntactic role head through nominal modifiers and attached `of` complements.
Reject noncontiguous expansions; do not traverse relative clauses, coordination or
other prepositional adjuncts. Preserve previous spans and the expansion rule.
Record speaker/epistemic/negation evidence along `ccomp`/`xcomp` parent chains.
These are syntactic attribution hypotheses, not speaker-identity certification.
Do not propagate speech negation into an embedded event's polarity or truth.
Entity identity, episode identity and assertion commitment remain unknown.

## Execution and results

Inputs, predecessor outputs and pinned model hashes checked before inference;
run receipt written before the trial. Same 12 assistant-authored synthetic cases
and 70 opened development articles, no new labels or protected outcomes.

| Fixed field | Previous dependency | Compositional 0.1 |
| --- | ---: | ---: |
| Actor | 9/9 | 9/9 |
| Object | 5/6 | 6/6 |
| Speaker | 4/4 | 4/4 |
| Proposition | 4/4 | 4/4 |
| Forecast/opinion status | 2/2 | 2/2 |
| Negation detection | 2/2 | 2/2 |
| Year mentions | 1/1 | 1/1 |
| Specified false-predicate rejection | 2/2 | 2/2 |

This is a known development suite, not independent accuracy. Five new structural
tests cover partitives, time-adjunct exclusion, forecast attribution, nonpropagation
of speech negation and unresolved pronouns. Combined regression suite: **50 pass**.

Opened articles retain all 332 prior predicate candidates. There are 25 role
expansions and 17 predicates with attribution chains, affecting 24 articles.
All output spans validate. Zero predictive admissions. Full records and manifest:
`data/v6/compositional_evidence_trial_20260924/`.

## Inspection: useful changes and retained failures

Inspected every change record; these are assistant diagnostics, not human gold.
Useful candidates include `some of its Bitcoin`, `a portion of CHIPS Act support`,
`Bank of America`, and attribution to JPMorgan, Peter Schiff and Tim Cook.

The general expansion is still unsafe when the parse is wrong or attachment is
ambiguous. Article212074812 expands `the company` to `the company of his resignation`
under `notified`: the resignation phrase should not be part of the recipient entity.
Article207132501 yields `4 of Bank of America’s` as an actor. Article189518836
retains an HTML-entity-contaminated phrase. Attribution chains can inherit bogus
speakers such as `Is` (article189563389) or a share order (176196569); metaphorical
`History` is not a verified speaker either. Existing spurious predicates are not
removed by this version. None of these counts demonstrates improved link precision.

## Decision and next step

**Do not promote 0.1.** Retain it and its failures as a completed development trial.
Next separate the nominal role head from optional complement candidates rather
than unconditionally replacing the entity span. Add attachment uncertainty and
speaker-type checks, then test partitive versus verb-selected-complement contrasts
and headline fragments. Preserve uncertainty instead of headline-specific fixes.
The fixed suite must grow to cover these newly discovered failure classes, with
any later gains explicitly labelled development gains, not fresh validation.

This does not change research eligibility, source/family/inference gates, any
predictive model, or any frozen experiment. No data fetch or new review requested.
