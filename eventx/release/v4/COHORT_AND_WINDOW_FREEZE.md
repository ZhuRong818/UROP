# EventX v4 cohort and window freeze

Freeze ID: `eventx-v4-cohort-window-20260902`

The label-blind cohort gate passed before the holdout. The primary confirmatory
cohort contains all 470 Polymarket conditions that met the frozen rule:

- present in Lumid `/api/v1/lqt/markets?venue=polymarket` at
  `2026-09-02T10:23:03Z`;
- positive roster-reported 24-hour volume;
- a pre-`2026-09-02T00:00:00Z` Lumid warehouse metadata record;
- a nonempty market question and exactly one canonical YES asset; and
- `end_date >= 2026-10-30T00:00:00Z`.

The cohort has 470 condition-level event clusters and all five deterministic market
groups are nonempty. The confirmatory window is
`[2026-09-06T00:00:00Z, 2026-10-30T00:00:00Z)`, leaving more than three days between
roster enumeration and outcome collection.

Kalshi is not included in the primary future confirmation. Lumid's active roster
returned 4,797 Kalshi identifiers, but only 48 reconciled to bounded pre-cutoff
warehouse metadata, the highest-volume roster item tested returned 404 from the
market-detail endpoint, and the bounded activity aggregation exceeded the fixed
30-second `/retrieve` statement timeout even after batching. Missing Kalshi metadata
is not interpreted as inactivity and thresholds were not relaxed. Kalshi can be a
separately preregistered external replication after the source is repaired.

This freeze resolves only the fields explicitly left pending in `DESIGN.md`. It does
not alter the research question, outcome, features, learner, metrics, minimum effect,
uncertainty procedure, decision rule, or claim boundaries.

