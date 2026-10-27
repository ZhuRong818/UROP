# V5 family review — first additional batch

Reviewed cached contract questions, YES subtitles and candidate event membership,
without querying Lumid or opening prices, prediction labels or holdouts.

Three explicit scopes now have additional must-link constraints:

- **2026 Colombian presidential election:** first round, runoff margin and final
  winner across Kalshi and Polymarket.
- **2026 Los Angeles mayoral election:** primary ranks, vote shares, turnout,
  qualification/matchup, concession and final winner across both venues.
- **2026 basketball finals:** championship winner, series length/spread/score,
  player statistics and Finals MVP across both venues.

These are split-isolation dependencies, not assertions that contracts have the
same payout, that source metadata is historically certified, or that a news item
can be associated with every contract in a family.

## Results

38 candidate event IDs and 137 contracts reviewed in these scopes; 35 must-links
recorded. Prior 1,522 provisional components become **1,487**. All previous links
are preserved. All 35 deliberately split dependencies were rejected by the graph
validator; graph order-invariance also passed. **Zero final families certified.**

The missing named YES identity on `KXMAYORLA-26-KBAS` is still unresolved; identifying
its election family does not recover its exact outcome semantics. The 2027
basketball season and Trump-attendance-at-Finals event were flagged for additional
review, not automatically merged or declared independent. Multi-leg bridges,
adjacent events and common shocks still prevent final boundary certification.

## Evidence and next batch

- Task: `eventx/tasks/review_v5_family_batch_20260915.py`.
- Evidence: `data/v5/family_review_batch_20260915/reviewed_scopes.json`.
- Current provisional graph: `data/v5/family_review_batch_20260915/candidate_components.json`.
- Open flags, test results and hashes are in the same directory.

The older family review queue is retained as historical evidence; use this graph
for subsequent review. Next prioritize multi-leg contracts referencing these three
scopes and remaining tournament/season boundaries. Final certification requires
the full relevant boundaries and semantics, not just additional graph merges.

Provider contact is deferred per user direction. Source/inference gates remain
unchanged; no V5 freeze, cohort exclusion, split assignment or model evaluation.
