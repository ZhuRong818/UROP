# EventX v2.1 KOL-v2 blind review guide

Review file: `eventx_v2_1_kol_v2_blind_review.jsonl`  
Required completed file: `eventx_v2_1_kol_v2_blind_review_completed.jsonl`  
Rows: 150

## Blindness rule

Review only the supplied market question and tweet text/metadata. Do not open matcher code, the hidden key, candidate-pool files, prior reviews, error analyses, prices, trades, outcomes, or model results. The review packet does not contain the rule prediction.

## Labels

Assign exactly one label to every row:

- `relevant`: at the tweet timestamp, the tweet contains information that could reasonably update the probability of the stated market outcome.
- `not_relevant`: overlap is generic, tangential, about a different person/event/jurisdiction, or contains no prospect-bearing information.
- `uncertain`: the supplied text genuinely lacks enough context for a reliable binary decision. Use this only when the missing context cannot be resolved from the row itself.

Also fill:

- `review_confidence`: `high`, `medium`, or `low`;
- `review_rationale`: one pair-specific sentence explaining the actual connection or mismatch; and
- `reviewer`: a stable reviewer name.

## Consistency rules

Apply these rules equally to every row:

1. Evaluate each item in a multi-topic roundup locally. Do not combine a country/person from one bullet with an event word from another bullet.
2. For a candidate-specific market, a story about a different candidate is `not_relevant` unless the text explicitly connects that development to the target candidate’s prospects. An exact target mention still needs campaign, polling, legal/reputational, withdrawal, endorsement, performance, or other prospect-bearing information; purely personal or ceremonial mentions are `not_relevant`.
3. Polls, vote shares, margins, campaign spending, attack ads, endorsements, ballot access, candidacy changes, and candidate-linked investigations can be relevant even when the tweet does not repeat the full market wording or is not in English.
4. For leadership/status markets, explicit removal, deposition, succession, death, resignation, survival, or continued control is relevant when it bears on the named person’s status. Apply the same label to semantically equivalent phrases such as “removed from power” and “deposed.”
5. For invasion or territorial-advance markets, concrete changes in a belligerent’s military capacity, mobilization, troops, weapons, strikes, blockade, sanctions, operational assistance, or escalation can be relevant when the tweet provides a plausible directional mechanism. A bare country mention or an unrelated conflict involving the same country is `not_relevant`.
6. For an individual sports-award market, player performance, statistics, injury/availability, and progress in a major tournament can update award prospects without naming the award.
7. For an AND/composite outcome, evidence about one component can be `relevant` because it can update the probability of the joint outcome. It must still be concrete evidence about the correct party/component, not generic chamber vocabulary.
8. Prediction-market content is `relevant` when it reports an actual price, probability, odds move, realized wager, position, stake, or payoff that bears on the proposition. A failed/rejected/cancelled order, insufficient-balance notice, or copied market question without a realized signal is `not_relevant`.
9. Judge relevance, not truth or direction. Evidence can raise or lower the outcome probability and may be a reported claim rather than an established fact.

## File integrity

Preserve every existing field and value, including row order and `audit_id`. Change only `review_label`, `review_confidence`, `review_rationale`, and `reviewer`. Complete all 150 rows before opening any hidden material.

Acceptance is scored later using the fixed KOL gates: precision ≥ 0.85 and hard-candidate recall ≥ 0.90. Reviewers must not see rule predictions before labels are final.
