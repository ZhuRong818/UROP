# EventX v2 cohort-freeze procedure

This procedure operationalizes protocol `eventx-v2-preregistered-20260731`. It is
label-blind: no jump labels, forward returns, model features, predictions, metrics, or
v1 holdout results may be opened or joined while constructing the v2 cohort.

## Temporal gates

1. During the warmup window, ending `2026-08-01T00:00:00Z`, verify ingestion only.
2. Collect prospective market metadata, trades, order-book snapshots, news, and KOL
   messages during the half-open selection window
   `[2026-08-01T00:00:00Z, 2026-08-15T00:00:00Z)`.
3. Do not finalize activity or freeze a cohort before
   `2026-08-15T00:00:00Z`. Both supplied programs refuse to do so.
4. Freeze the accepted taxonomy and cohort before any development-window labels are
   built or inspected.

The current archival bulk backfill may continue, but its completeness does not change
the prospective selection dates.

## Required taxonomy artifacts

Create `data/v2/taxonomy/market_categories.jsonl`, one canonical YES row per binary
market, with:

`venue`, `market_id`, `outcome_id`, `canonical_side:true`, `is_binary:true`,
`question`, `scheduled_close_ts`, `resolution_ts`, `status`, `category`,
`taxonomy_version`, `review_status`, and provenance.

Apply `TAXONOMY_GUIDE.md` using metadata only. Then independently audit at least 200
stratified markets with two reviewers and a third adjudicator. Store
`data/v2/taxonomy/audit_report.json` with this minimum shape:

```json
{
  "taxonomy_version": "eventx-v2-taxonomy-v1",
  "status": "accepted",
  "review_rows": 200,
  "overall": {"precision": 0.90, "recall": 0.90},
  "by_category": {
    "politics": {"review_rows": 20, "precision": 0.80, "recall": 0.80}
  }
}
```

The numbers above are schema examples, not achieved results. The audit is accepted
only when actual overall precision and recall are each at least 0.90 and every
category with at least 20 reviewed rows has precision at least 0.80. A failed audit
requires a new taxonomy version and a repeated label-blind audit.

## Freeze commands

After the selection window closes and both venues' retained trade files contain the
complete window:

```bash
python -m eventx.tasks.verify_v2_preregistration
python -m eventx.tasks.build_v2_selection_activity
python -m eventx.tasks.freeze_v2_cohort
```

The activity builder:

- keeps only canonical-YES trades in the selection window;
- removes duplicate trade IDs;
- computes trade count, notional, active UTC days/hours, and last-trade time; and
- hashes every input and its output.

The cohort freezer then applies the frozen thresholds exactly: at least 100 trades,
1,000 notional, three active days, last trade no more than 72 hours before selection
close, unresolved status, and scheduled close at or after
`2026-11-01T00:00:00Z`. It ranks by
`log1p(trades) + log1p(notional) + 0.1 * active_hours`, breaks ties by ascending market
ID, and keeps at most 40 markets per venue/category cell (400 total).

## Required outputs and review

The commands must produce:

- `data/v2/selection/market_activity.jsonl`;
- `data/v2/selection/activity_report.json`;
- `data/v2/cohort/selected_markets.jsonl`; and
- `data/v2/cohort/cohort_freeze_manifest.json`.

Before opening development labels, a reviewer must confirm:

1. the preregistration verifier reports `status: ok`;
2. every input/output hash in the two reports matches;
3. `label_blind` is `true` and every `labels_read` list is empty;
4. the taxonomy audit passes the stated thresholds;
5. no selected market is terminal or closes before the holdout starts;
6. every selected row satisfies all activity thresholds;
7. no venue/category cell exceeds 40 and the cohort does not exceed 400; and
8. the manifest is copied into the v2 release record before label construction.

Any deviation is recorded prospectively. It must not be chosen in response to model
performance, and it requires a new protocol ID if it changes a frozen research
decision.
