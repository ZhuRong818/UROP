# Approved bounded audit — reviewer handoff

Only use the new `data/v6/bounded_audit_20260917/` packets, not the earlier bulk queues.
The one recorded random draw is frozen:74 family,72 story and40 relevance cases.
All200 development articles supplied a top-one output; this is output coverage,
not accuracy or recall. No review result has been evaluated.

## Boundary reviewer

Provide `family_review_packet.jsonl` and `story_review_packet.jsonl` to an independent
second reviewer who has not seen earlier judgments. Save separate completed copies,
filling `reviewer`, `decision`, `rationale`; preserve all IDs and evidence.

- Family: `must_link`, `no_direct_link_established`, `unresolved`.
- Story: `same_story`, `related_update`, `distinct_story`, `unresolved`.

Judge shared events, predicates, periods, stages and story updates, not vocabulary
alone. Explain decisions from supplied contract/article evidence. Missing material
evidence warrants unresolved. Never consult forecast outcomes. Earlier first reviews
are retained for later comparison but must not be supplied to this reviewer.

## Two relevance reviewers

Both receive `relevance_review_packet.jsonl`. Give one
`relevance_reviewer_A_responses.jsonl` and the other
`relevance_reviewer_B_responses.jsonl`; each saves a separate completed copy.

Fill actual `reviewer_id` and `labels`: relevance is `direct`, `background`,
`unrelated` or `abstain`; applicability is `yes_proposition`, `event_only`,
`not_applicable` or `uncertain`. Include exact article evidence spans and describe
identity problems. Direct evidence need not favor YES; it must concern the precise
contract proposition/entity/period. Missing information must not be invented.
Use the existing relevance schema/validator; preserve pair IDs. Reviewers work
independently and do not see each other's answers or ranker scores.

## Custodian rules

Do not distribute score pools, earlier answers, manifests containing selection
details or outcome data. These samples remain conditional on earlier screening;
do not promise complete blinding simply because answers are hidden.
No replacement cases, extra batches or seed redraws. Return incomplete/missing
reviews explicitly. One adjudication per disagreement; unresolved cases count
conservatively against acceptance. Bound412 total new judgments remains in force.
The approved amendment controls tests and stopping rules. A pass cannot admit the
335 reserved preview pairs or establish universal independence.
