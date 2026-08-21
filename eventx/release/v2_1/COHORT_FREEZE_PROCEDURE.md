# EventX v2.1 October-deadline cohort-freeze procedure

This procedure operationalizes `eventx-v2.1-october-deadline-20260731`. It inherits
the scientific rules in the v2 cohort procedure but uses the revised v2.1 dates and
the isolated `data/v2_1/` namespace.

## Temporal gates

1. Warmup ends at `2026-08-01T00:00:00Z`.
2. Selection is the half-open interval
   `[2026-08-01T00:00:00Z, 2026-08-08T00:00:00Z)`.
3. Activity and cohort artifacts cannot be finalized before
   `2026-08-08T00:00:00Z`; the supplied programs enforce this.
4. The corrected taxonomy, cohort, and association rules must be frozen before any
   development labels are created or inspected.
5. Development ends at `2026-10-01T00:00:00Z`.
6. The sealed holdout is
   `[2026-10-01T00:00:00Z, 2026-10-22T00:00:00Z)` and is evaluated exactly once
   after it closes.

## Historical plus prospective inputs

Existing historical trades may supply warmup and descriptive history. A prospective
incremental extract must supply the complete selection, development, and holdout
windows. Preserve event and retrieval timestamps, deduplicate on frozen natural
keys, and never treat current metadata as historical as-of metadata.

No v1 labels, v1 holdout results, future outcomes, predictions, or performance
metrics may enter taxonomy, activity, or cohort construction.

## Taxonomy artifacts

Create:

- `data/v2_1/taxonomy/market_categories.jsonl`; and
- `data/v2_1/taxonomy/audit_report.json`.

Use `eventx/release/v2/TAXONOMY_GUIDE.md`. The independent audit requires at least
200 adjudicated rows, overall precision and recall of at least 0.90, and precision
of at least 0.80 for every category with at least 20 reviewed rows.

## Freeze commands

After the selection window and only when both venues cover it completely:

```bash
python -m eventx.tasks.verify_v2_1_preregistration
python -m eventx.tasks.build_v2_selection_activity
python -m eventx.tasks.freeze_v2_cohort
```

The fixed thresholds remain at least 100 canonical-YES trades, 1,000 notional, three
active UTC days, and a last trade no more than 72 hours before selection close. A
market must be unresolved and scheduled to close at or after
`2026-10-01T00:00:00Z`.

Rank within each `(venue, corrected_category)` cell by
`log1p(trades) + log1p(notional) + 0.1 * active_hours`, break ties by ascending
market ID, and retain at most 40 per cell and 400 total.

Required outputs are:

- `data/v2_1/selection/market_activity.jsonl`;
- `data/v2_1/selection/activity_report.json`;
- `data/v2_1/cohort/selected_markets.jsonl`; and
- `data/v2_1/cohort/cohort_freeze_manifest.json`.

Before labels, verify all hashes, confirm `label_blind: true`, confirm every
`labels_read` list is empty, and record the freeze in `PROGRESS.md`.
