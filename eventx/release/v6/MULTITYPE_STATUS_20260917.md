# Multi-type extraction routing 0.1

Implemented separate `eventx/v6/multitype.py`:11 lexical type routes, subject spans,
outcome subtitle, predicate cue, time and threshold mentions, deadline relation cues,
and named ranking-source mentions. Every extracted span retains source field and
character offsets; supplied rules retain provenance. No normalization of ambiguous
dates, entities or resolution semantics is invented. Multiple matching type patterns
are retained even though a deterministic priority selects a routing hypothesis.

Six synthetic test methods pass, including11 type-routing subcases, exact offsets,
unknown dates/types, subtitle preservation and no automatic acceptance.
Opened40-case debug routes all40 across11 types;25 have subject spans and29 have
explicit time mentions. Outputs:`data/v6/multitype_debug_20260917/`.
These are extraction counts, NOT verified type accuracy, relevant-link coverage,
improved precision or a repeated audit. All comparisons abstain; zero admissions.

Remaining substantive work: canonical entity resolution, distinguishing observation
time from deadline/rule examples, complete type-specific predicate interpretation,
and binding article claims to those predicates. Lexical pattern routing alone cannot
provide a valid semantic matcher. The broad method remains unfinished, and the new
audit must not be frozen or opened on the basis of these counts. No original research
artifact or protected labels/outcomes were modified/read by the debug run.
