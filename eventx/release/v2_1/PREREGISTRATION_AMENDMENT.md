# EventX v2.1 October-deadline preregistration amendment

**Protocol ID:** `eventx-v2.1-october-deadline-20260731`  
**Created:** `2026-07-31T07:22:07Z`  
**Deadline:** `2026-10-31T23:59:59Z`  
**Status:** preregistered before v2 selection and before any v2 labels  
**Supersedes prospectively:** `eventx-v2-preregistered-20260731`

## Reason for this version

The project must finish by the end of October 2026. The earlier v2 protocol reserved
November as its holdout, so it cannot meet that constraint. This amendment is made
before the August selection window opens and before any v2 development or holdout
labels, prevalence, predictions, or metrics exist or have been inspected.

The original v2 files remain immutable evidence. This is a new protocol version, not
an edit to the sealed v2 record.

## Scientific contract retained unchanged

Except for the dates and the corresponding minimum scheduled-close date, this
protocol incorporates the scientific contract in
`eventx/release/v2/PREREGISTRATION.md` without alteration:

- T1 jump prediction at 5, 30, 120, 360, and 1,440 minutes, with 30 minutes primary;
- T3 as the confirmatory spine, comparing B3 market + core news + residualized sparse
  KOL against B1 market + core news;
- conditional T5 only if B3 promotes;
- binary canonical-YES outcomes from Polymarket and Kalshi;
- fixed label-blind density selection within corrected venue/category strata;
- the frozen B0/B1/B2/B3 features, learner, transformations, folds, nulls, metrics,
  bootstrap, and promotion gates;
- no future-liquidity eligibility filter and no use of actual resolution time as a
  feature; and
- one candidate at most, one holdout evaluation, one consumption receipt, and no
  reruns.

The base protocol SHA-256 is
`07882cda7c552fc1abc613f75de9079b16c1ce62fe2593a69c6d62494379c89c`.

## Revised half-open UTC schedule

| Period | Start | End exclusive | Permitted use |
|---|---|---|---|
| Warmup | 2026-07-31 | 2026-08-01 | Trailing inputs and collector validation; no labels |
| Selection | 2026-08-01 | 2026-08-08 | Activity, coverage, taxonomy, and cohort selection; no outcome labels |
| Development | 2026-08-08 | 2026-10-01 | Labels, folds, models, diagnostics, and null tests |
| Confirmatory holdout | 2026-10-01 | 2026-10-22 | One frozen candidate, evaluated exactly once after the window closes |
| Finalization | 2026-10-22 | 2026-11-01 | Final report, datasheet, evidence package, and internal release |

The label-blind cohort threshold requiring a scheduled close at or after the holdout
start changes mechanically from `2026-11-01T00:00:00Z` to
`2026-10-01T00:00:00Z`. All other thresholds and the 400-market maximum are
unchanged.

If a venue or category has inadequate label support, its metric is reported as
unavailable or underpowered. The window is not extended and the cohort, model, label,
or threshold is not changed after inspecting labels.

## Historical-data reuse policy

The existing archive may be reused; it is not discarded or downloaded again.

Permitted uses are:

- trade-derived historical bars and trailing-feature warmup;
- ingestion, normalization, deduplication, and point-in-time tests;
- coverage and missingness analysis; and
- a separately identified descriptive robustness track.

The archive does not replace records from the revised selection, development, or
holdout windows. A prospective incremental extract supplies those records. The merge
must:

1. retain source event time, retrieval time, venue, market, outcome, and extract
   version;
2. deduplicate trades, news, and KOL documents on their frozen natural keys;
3. never represent a current metadata snapshot as historical as-of metadata;
4. never use actual `resolution_ts`, revised future metadata, v1 labels, or v1
   holdout results as v2 features or tuning inputs; and
5. freeze content hashes before labels or evaluation consume an extract.

Markets already marked complete by the archival backfill are not assumed to contain
later prospective events. Incremental capture is therefore required even when
historical coverage is complete.

## October completion criterion

By `2026-10-31T23:59:59Z`, the project must have:

1. frozen and verified the cohort, association rules, features, and splits;
2. completed the preregistered development comparisons and null tests;
3. frozen no more than one holdout candidate;
4. evaluated the October holdout exactly once and written its receipt;
5. produced the final research report, datasheet, manifests, and reproducibility
   package; and
6. disclosed missingness, limited duration, underpowered strata, negative results,
   and every protocol deviation.

Public redistribution may remain gated by licensing, privacy, and upstream-rights
review; those governance gates do not authorize changing or rerunning the scientific
result.

## Confirmatory status

This amendment preserves prospective confirmatory status because it was created
before the affected data windows and before any affected labels or metrics. Any
further change to a frozen date or scientific decision requires another protocol ID
and must occur before inspecting the affected labels.
