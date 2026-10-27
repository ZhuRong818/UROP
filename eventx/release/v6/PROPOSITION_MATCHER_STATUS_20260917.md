# Proposition matching development implementation

Implemented separate versions preserving all previous code, labels and audit artifacts.
Latest: `eventx/v6/proposition_matcher_v02.py`, using existing traceable parsing helpers.
There are bounded matching paths for same-period measurements, current-price evidence
for future thresholds, named AI rankings, music-chart observations, leadership and
tweet counts. Exact mention keys remain local typed hypotheses, not a verified entity
knowledge graph. Unresolved aliases do not silently become entity matches.

Candidate decisions distinguish direct evidence, background, mismatch/contradiction
and insufficient evidence. A contradiction means mismatch with this association, not
evidence that the market should settle NO. Negative-direction information can still
be directly relevant. Threshold entailment is not required for current-price evidence.
Rules remain lexical and incomplete: local subject/predicate/time binding is stronger
than global co-occurrence, but is not general semantic understanding or validated
relevance. Mentioning an observation date does not establish that the date has the
intended semantic role; future independent checks must test such failures explicitly.

## Results and integrity

82 synthetic/existing unit tests pass. First implementation debug is preserved at
`data/v6/proposition_matcher_debug_20260917/`:0 direct candidates because timing checks
also stopped semantic inspection. Twelve inputs lacked close_time; inspected Polymarket
cards use end_date. This field is not automatically a certified trading-close timestamp.

Version0.2 separates semantic inspection and temporal eligibility, without relaxing
predictive admission. `data/v6/proposition_v02_debug_20260917/` records40 opened cases:

| Semantic diagnostic | Count |
|---|---:|
| Direct candidate | 1 |
| Background | 2 |
| Metric contradiction | 1 |
| Insufficient evidence | 36 |

Nineteen abstentions lack a supported proposition adapter,16 lack resolved subjects,
and1 lacks complete binding. Eligibility:11 after recorded close,29 uncertified.
Zero predictive admissions or supported production links. The1 direct candidate is
the already-opened Bitcoin example; **do not call this100% precision or independent
validation**. The40 cases informed the redesign and remain development material.

No reference labels were loaded by these debug runners. Prior audit remains failed;
no holdout, reserved review labels, source collection, model fitting or external API
was used. Source certification is never synthesized from a semantic match.

## Next substantive work

The code now makes testable candidate decisions but is not ready for a fresh audit.
Entity aliases and19 unsupported cases remain the main semantic coverage gaps.
Expand exact entity evidence and explicit per-type predicates on opened development
metadata, then check generalization on development examples beyond these40. Do not
keep targeting just the known positive. No new annotation batch is requested here.

Before independent evaluation, freeze eligible corpus, text/version admission,
acceptance rules, useful coverage/yield target, precision target and fixed budget.
Retain unaccepted articles in coverage denominators and include no-match cases. The
335 reserved preview pairs remain unadmitted and cannot be used as convenient gold.
