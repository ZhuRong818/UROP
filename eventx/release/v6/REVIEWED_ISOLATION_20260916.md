# V6 reviewed isolation mapping and remaining certification work

## Completed

New version: `data/v6/reviewed_isolation_20260916/`.

- Preserved all prior component memberships and incorporated51 reviewed family
  edges:40 with two agreeing submitted reviews and11 user-adjudicated links.
- Provisional components decreased from1,197 to1,149; all4,651 market mappings
  retained. These are isolation families, not assertions of identical payouts.
- All51 deliberate split-rejection tests pass. Added2 story co-isolation constraints;
  SK Hynix same-story/related-update disagreement is retained, not silently resolved.
- Kept the adjacent AI-date exclusion separate from semantic family merging.
  Cohort-wide repeated-series policy is still not frozen. The user's distinct-date
  judgment is preserved; no previously quarantined row is released.
-265/600 pairs remain excluded.335 preview pairs span129 original groups and97
  articles and have zero known family overlap with development after remapping.
- Original graph, packets and sampling remain untouched. This new mapping is
  provisional; it neither changes V4/V5 nor admits any forecast data.

## Why certification still fails

The42-case confirmation completed the targeted positive queue. It did not provide
a second review of the negative boundary decisions. The existing boundary protocol
requires two reviews, and nearest-neighbour candidates alone are not exhaustive.

To avoid re-reviewing excluded cases, the outstanding review package now covers only
boundaries relevant to the335 retained preview pairs:

- `data/v6/retained_boundary_review_20260916/family_second_review_packet.jsonl`:551 cases.
- `data/v6/retained_boundary_review_20260916/story_second_review_packet.jsonl`:433 cases.

These are NOT new discovered conflicts or another review of the confirmed42 cases.
They are existing first-review negatives that still lack a second judgment. Packets
preserve original evidence and blank reviewer/decision/rationale fields; selection
is informative, so do not overstate blinding. Use separate completed copies and the
decision vocabulary in `BOUNDARY_CONFIRMATION_NEXT_20260916.md`.

Whole-boundary checks for missed aliases, stages and story bridges beyond top-three
similarity candidates remain required. Completion certifies only the declared
review scope, not all public news, statistical independence or retrieval recall.
Do not claim that the retained335 pairs are certified or representative of the corpus.

## Next work

1. Obtain actual remaining boundary judgments and adjudicate disagreements. Never
   generate substitute human labels automatically. LeBron and Treasury remain excluded.
2. Finalize repeated-series restrictions and the broader boundary-search scope; then
   freeze a new sampling/weighting design before reserved association evaluation.
3. In parallel, the2,063-pair development article–contract relevance packet can be
   annotated now (`data/v6/hybrid_development_reviews_20260916/packet.jsonl`). It is
   development-only and does not require opening reserved relevance labels.
4. Historical source/version admission, model eligibility, source completeness and
   inference remain separate prerequisites for predictive confirmation.

No outcomes, reserved relevance labels or predictive performance were inspected.
