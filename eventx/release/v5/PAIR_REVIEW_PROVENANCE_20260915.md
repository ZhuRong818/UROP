# Pair-review provenance clarification

On 15 September 2026 the user confirmed that the reviewers of
`data/v5/full_family_review_20260915/pair_responses_reviewed_20260915.jsonl`
are real reviewers. Record the submission as human review on user attestation,
despite the misleading `simulated_model_reviewer_A/B` identifiers. The identifiers,
annotations and original validation report remain unchanged for provenance.

This clarification supersedes the validation report's pending reviewer-origin
question only. It does not independently verify identity or blinding, certify the
evidence behind each decision, or establish a second review of each pair.

Counts remain 3,849 responses: 154 proposed must-links, 3,636 no direct link
established, 59 unresolved. Independent second review of proposed merges and
whole-family boundary review remain pending. No graph changes or approvals.

Next packet:
`data/v5/pair_submission_validation_20260915/second_review_proposed_links.jsonl`.
Use the existing family-review rules and a reviewer independent of the first
decision on each pair; do not share first decisions/rationales before that review.
