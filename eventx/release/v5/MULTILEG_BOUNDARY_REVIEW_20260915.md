# Multi-leg and adjacent-event boundary review

## Completed checks

Screened all **397 flagged multi-leg contracts** in the cached review queue:
104 cross-category and 293 sports multi-game contracts, spanning 194 provisional
components. Preserved per-contract text, display fragments, missing evidence and
review status in `data/v5/multileg_boundary_review_20260915/unresolved_multileg.jsonl`.
Display fragments are not authoritative leg parsing or resolved underlying IDs.

The projected queue does not contain underlying market IDs or dated per-leg
resolution semantics. Thus **zero underlying mappings were resolved**. This is a
limitation of the reviewed projection, not proof that Lumid or other cached raw
metadata lacks those fields. No speculative entity-name links were added.

A literal scan for the named candidates/teams/players in the previous three scopes
found zero hits. This is only a search result: aliases and omitted context mean it
does not certify the absence of cross-family bridges.

## Explicit adjacent decisions

- **2026 versus 2027 basketball championship:** retain distinct event identities.
  All 22 reviewed 2027 contracts explicitly name 2027. Shared teams alone do not
  make them the same settlement event. Cross-season dependence and embargo rules
  remain unresolved; this is not a certified independent split or negative edge.
- **Trump attendance at NBA Finals:** unresolved. The cached question does not
  specify year/game/date. Do not assign it to the 2026 series based on phrase alone.

## Updated map and admission status

No additional supported must-links in this pass; the **1,487-component map is
unchanged** and copied into the new version with input/output hashes. Prior links
are retained. `component_review_status.jsonl` records all components as unapproved
and identifies the 194 containing flagged multi-leg contracts. No component is
currently admitted to V5; this is not a permanent exclusion decision.

Zero final families certified. No inference design, source gate, cohort, split,
protocol or model changed. No provider contact, prices, outcomes or holdout access.

## Next actionable evidence

Inspect available cached metadata projections for explicit per-leg market IDs,
polarity, event dates and resolution/cancellation rules before considering another
family merge. If not locally available, either retain these contracts as unresolved
or propose a separately approved, label-blind exclusion rule. Merely extracting
names from the display text cannot resolve this blocker. Broader tournament and
season boundaries outside the two reviewed pairs remain unreviewed.

Task: `eventx/tasks/review_v5_multileg_boundaries_20260915.py`.
Evidence, decisions, map, report and manifest:
`data/v5/multileg_boundary_review_20260915/`.
