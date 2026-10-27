# Topic-review receipt and identifier correction

On 15 September 2026 the user confirmed that the submitted reviews are real
reviews and authorized renaming the misleading `simulated_` reviewer identifiers.
This is a user-attested provenance correction, not independent verification of
reviewer identity or blinding. No identities were invented.

In `data/v5/review_followup_20260915/packet_independent_topic_review.jsonl`,
`simulated_independent_reviewer_A/B/C` were renamed to
`independent_reviewer_A/B/C` respectively. All 30 records retain their original
topics, rationales, confidence, context and insufficient-context flags. The
unaltered submission is preserved beside it as
`packet_independent_topic_review.original_submission.jsonl`.

SHA-256:

- Original: `b1c55e06e34f44111b892e754555f474ede24be0be895d8d72dcc63b011e0711`
- Renamed: `9e5ff208629909fd4fd2afd36b31123e2093710383736c3117121e25b2ddaf36`

Validation: 30 unique market IDs; all seven context fields match the blinded
packet; only reviewer identifiers changed. Comparison with the first review,
including its Belgium addendum, finds 29/30 agreements (96.7%). This is a small
purposive packet, not a population accuracy estimate. A/B/C contribute one
review per contract, not three independent reviews per contract.

One disagreement remains: “MicroStrategy sells any Bitcoin by June 30, 2026?”
(`0x8e7a03cb1970e2ad6533b01892403516b6b3f5b5fa90ed7d104c28b27e40ba00`).
First review: `crypto`; submitted review: `corporate_traditional_financial`.
The submitted rationale classifies the company's sale as a corporate action,
rather than classifying by the asset. This is consistent with the actual-outcome
rubric, but final adjudication remains pending; neither label was overwritten.

Next: adjudicate this boundary and record the decision before approving the packet.
This receipt does not certify the full market taxonomy, event-family independence,
historical metadata or source coverage. No prediction outcomes, protected holdouts,
model fits or frozen protocols were accessed or changed.
