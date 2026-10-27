# V6 remaining confirmation and split-policy proposal

## Files to review

- `data/v6/boundary_confirmation_20260916/family_confirmation_packet.jsonl`:40 cases.
- `data/v6/boundary_confirmation_20260916/story_confirmation_packet.jsonl`:2 cases.

These are exact subsets of the original score-blinded evidence packets. Earlier
decisions, rationales and reviewer identities are absent. Fill `reviewer`, `decision`
and `rationale` in a separately named copy; leave evidence and IDs unchanged.
Family decisions: `must_link`, `no_direct_link_established`, `unresolved`.
Story decisions: `same_story`, `related_update`, `distinct_story`, `unresolved`.

Use a reviewer who has not seen these cases' earlier judgments if claiming blind
confirmation. The files omit judgments, but their selection from proposed positives
is itself informative. This targeted confirmation is not a representative accuracy,
recall or whole-boundary certification audit; negative cases still require the
existing broader review contract. A reviewer already exposed to judgments can
provide adjudication, but must not be reported as blinded.

## Rules

For families, cite contract predicates, scheduled release/state, tracking period,
or explicit stage/leg dependency. Broad subject overlap alone is insufficient.
Different payout predicates can share a leakage-isolation family. Missing material
resolution rules warrant unresolved, not a guessed negative. For stories, distinguish
the same report, updates about the same underlying event, and genuinely distinct
events; wording difference alone does not establish separation. No price/outcome
evidence may be consulted for these judgments.

## Proposed repeated-series treatment — not yet a frozen policy

Keep semantic event identity separate from split-isolation blocks:

1. Date-specific leaderboard observations can retain distinct event IDs.
2. For an unseen-family/series transfer audit, observations of the same defined
   leaderboard series must stay on one side of the split. Do not merge their semantic
   identities just to implement that constraint.
3. For a temporal within-series experiment, later snapshots may be evaluated only
   under a separately frozen chronological design with training cutoffs, purged
   overlapping targets/features, an explicit embargo and story-overlap controls.
   That is not evidence of unseen-series generalization. No embargo duration is
   selected here and none is asserted to guarantee independence.
4. Different leaderboards still need common-story checks. The user's coding/overall
   no-direct-link judgment does not automatically clear the common-story gate.

Until that policy is approved and implemented consistently across the cohort,
retain the existing adjacent-date risk flag. No automatic refill, quarantine release
or graph adoption is authorized by this proposal.

## Current evidence

The 15 user adjudications are now structured in `user_adjudications.jsonl` within
the confirmation directory, with provenance and links to the original evidence.
Eleven must-links concern9 reserved groups containing204 of600 reserved pairs.
Retaining all prior flags leaves265 risk-flagged pairs and335 unflagged preview
pairs; the latter are NOT an admitted or certified test set. Both unresolved cases
(LeBron next-team/announcement and Treasury observation convention) remain blocked.

Once reviews return: validate IDs/evidence and actual review provenance; adjudicate
disagreement; publish a new graph/story mapping and sampling manifest; rerun boundary
checks; complete the separate article–contract relevance audit. Source availability,
coverage and inference certification remain separate gates before prediction tests.
