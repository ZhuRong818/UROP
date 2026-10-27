# Family review rules and full inventory

## Scope

All 1,280 current components require boundary review. They are provisional split
groups, not 1,280 certified independent events. The inventory includes 4,651 cohort
contracts, 1,587 event nodes and 3,849 semantic candidate pairs. Do not require
every pair in a component to describe the same event: multi-leg links can connect
different events transitively. Do not break a supported link merely to reduce size.

Open `data/v5/full_family_review_20260915/INDEX.md` to browse every family.
Each linked family page lists its event IDs, cached contract text and candidate
pair IDs. Machine-readable complete records are in `families.jsonl` and
`pairs.jsonl`. Fill copies of `family_responses.jsonl` and `pair_responses.jsonl`,
not source records or frozen manifests. Keep each reviewer's response separate.

## Allowed evidence and blinding

Use contract identifiers, event context, named outcomes, dates, rules and explicit
leg references. Never consult price paths, realized winners, jump labels, model
predictions or performance. Cached metadata is not proof of historical availability.
Keep retrieval timestamps and exact source references for supplemental evidence.
Similarity scores prioritize search only; they are not probabilities of a true link.
The reviewer-facing pair file omits scores to reduce anchoring.

## Pair review procedure

1. Identify the actual settlement event, named entity, year/date and stage on both
   sides. Repeated wording such as “over 2.5 goals” is insufficient.
2. Check explicit underlying IDs and exact resolution rules where available.
   Distinguish same event/different outcomes from merely shared topic or entity.
3. Check direct dependencies: primary to runoff, qualification to final, nested
   thresholds, series statistics, or parent to underlying leg. Different payout
   rules do not necessarily remove a split-isolation dependency.
4. Record `must_link`, `no_direct_link_established`, or `unresolved`.
   - `must_link`: cite concrete shared-event or structural-dependency evidence.
   - `no_direct_link_established`: explain why available similarity is insufficient
     (e.g. distinct dated fixtures). This is NOT a statistical independence certificate.
   - `unresolved`: state precisely what identity/date/rule evidence is missing.
5. Record reviewer, rationale, evidence references, relation type, missing evidence
   and review timestamp. No confidence threshold automatically authorizes a merge.

Relation types: `same_event`, `stage_dependency`, `nested_outcome`,
`explicit_leg`, `distinct_event`, `unknown`. Date disagreements require inspection,
not automatic rejection: primary and general stages naturally have different dates.

## Whole-family review procedure

Inspect all member nodes, direct edges and external referenced nodes. Review proposed
links to other components and search for missed cross-venue aliases, adjoining
stages, annual/season bridges and multi-leg references. The embedding search is
top-five/threshold-limited: no candidate pair does NOT establish no dependency.

Record `needs_evidence`, `propose_merge`, `challenge_existing_edge`, or
`ready_for_second_review`. List the relevant pair IDs or edge evidence references.
Do not approve an entire family while a material boundary remains unresolved.
Large groups need bridge-edge checks, not arbitrary splitting. A false explicit
edge can be challenged with source evidence; never silently delete it.

## Adjudication and completion

Have a second reviewer independently check proposed merges and ready-for-review
family boundaries before viewing the first decisions; adjudicate disagreements
separately. Do not count repeated automated passes as independent human review.
Review records can recommend approval, but cannot themselves waive missing source
versions or certify statistical independence. Maintain unresolved records.

After approved decisions: publish a new hashed graph version, preserve prior links
unless explicitly corrected, test every must-link against proposed splits, inspect
component sizes and document changed memberships. Freeze no research cohort or
evaluation until its separate admission gates pass.

## Priority and examples

Start with external/missing-metadata nodes, multi-leg bridges, large components,
cross-venue pairs and date conflicts. Then review remaining families, including
singletons. All families are listed; priority is not permission to skip them.

- Same election winner across venues: possible `must_link`, verify year/rules.
- Match winner and goals total for that exact fixture: possible `must_link`.
- Identical goals-total wording for different fixtures: no direct link from wording;
  inspect any tournament-stage dependencies separately.
- Team championship in 2026 versus 2027: distinct event identity, not proof of
  statistical independence or an automatically safe evaluation split.
- Parent with explicit underlying IDs: keep links even when an underlying contract
  is outside the cohort; missing cancellation rules still require evidence.
