# EventX current state

> Compact canonical startup handoff. Read this file before EventX work. Read the
> detailed historical archive only when the task requires history.

Last updated: **2026-08-21 15:33 Asia/Singapore**

## Active objective

- **Programme:** EventX — incremental external information in prediction-market
  repricing.
- **Active study:** prospective protocol-validation pilot of B1 market + news versus
  B0 market-only.
- **Primary question:** does point-in-time market-relevant news improve prediction and
  calibration of 30-minute absolute canonical-YES log-odds jumps beyond market
  history?
- **Protocol:** `eventx-v2.3-news-availability-clarifications-20260817`.
- **Deadline:** 2026-10-31.
- **KOL status:** deferred. KOL-v1 and KOL-v2 association candidates failed their
  fixed audits and are ineligible for this cycle.

## Integrity state

- v2.3 verifier: **16 artifacts, zero failures**.
- v2.3 development labels: **uncreated and uninspected**.
- October holdout: **future, reserved and uninspected**.
- v1 replacement OOT holdout: **consumed; rerun prohibited**.
- Original v1 test: previously exposed by a noncanonical B0; descriptive only.
- Frozen artifacts must never be edited. Legitimate changes require a new version and
  manifest before affected labels or metrics are inspected.

Before any evaluation action, verify the consumption receipt at
`data/v1_oot_20260723_20260730/holdout_consumption_receipt.json`.

## Frozen scope and dates

| Item | Current value |
|---|---|
| Venues | Polymarket and Kalshi |
| Cohort | 14 frozen binary canonical-YES markets |
| Composition | 4 Kalshi politics, 5 Polymarket politics, 4 Polymarket other, 1 Polymarket sports |
| Development | `[2026-08-08, 2026-09-28)` UTC |
| Reconciliation/evaluation/freeze | `[2026-09-28, 2026-10-01)` UTC |
| Holdout | `[2026-10-01, 2026-10-22)` UTC |
| Finalization | `[2026-10-22, 2026-11-01)` UTC |
| Primary horizon | 30 minutes |
| Reference | B0 market-only logistic SGD |
| Candidate | B1 B0 + four core-news features |
| External observations | Valid Lumid endpoints only |

No selection threshold, sparse category, feature family, learner, metric, promotion
gate, date, candidate limit or holdout rule may be changed in response to labels.

## Current status

- Corrected taxonomy `eventx-v2.1-taxonomy-v7` passed its 250-row blind audit at
  precision 0.9720 and recall 0.9739.
- All 3,420 candidate endpoints were reconciled for selection; the selection window
  contains 30,862 Polymarket and 5,171 Kalshi records.
- The 14-market cohort is frozen and verified.
- The accepted news matcher passed at precision 0.9733 and recall 0.9605.
- KOL-v2 failed its fresh audit at precision 0.8378 and recall 0.6327. Preserve the
  cumulative 450-pair opened-content exclusion ledger.
- The August 8–17 Lumid rehearsal passed 14/14 market-detail mappings and 14/14 trade
  integrity checks, retaining 5,817 canonical-YES trades.
- The same rehearsal is frozen as **incomplete for news**: `/news/latest` returned
  exactly 200 rows, has no cursor or upper-time bound, and did not recover August 8–13.
- All 21 frozen targeted `/news/search` requests stayed below the cap.
- No development or holdout outcomes were inspected during these activities.

## Main blocker

The confirmatory B1 branch lacks provably complete point-in-time news coverage.
Lumid's `/news/latest` exposes `since`, optional category and limit, but no documented
cursor, offset or upper-time parameter. Repeated calls can return the newest capped
suffix without proving that older rows were recovered.

Acceptable recovery paths are:

1. a documented Lumid cursor or bounded-time partition;
2. a Lumid endpoint-equivalent bulk/warehouse export with schema, key and lineage
   evidence; or
3. complete prospective capture plus exact reconciliation showing no missed interval.

If news remains incomplete, B1 is `incomplete_due_to_source_coverage`, never a
zero-news or negative scientific result. B0 remains executable if its trade gate
passes.

## Collector state

- Legacy label-blind collector PID: `94663`.
- Last verified alive: `2026-08-21T06:46:59Z`.
- Protocol reported by process: v2.1, not v2.3.
- Snapshot counts: 147,146 market events; 4,196 news rows; 17,707 Kalshi trades;
  61,919 Polymarket trades; 1,853 KOL rows.
- Recent requests were succeeding, but success does not prove interval completeness.
- The frozen v2.3 news implementation has not been launched.
- Pre-launch review found that its news key combines stable identity with a full-row
  hash; same-article content/timestamp revisions may evade conflict detection.

Do not silently stop, replace or call PID `94663` v2.3-compliant. Before launch,
create a new label-blind implementation version that separates entity identity from
content-version hash and tests article revisions and timestamp conflicts. Record an
explicit parallel-launch or migration receipt.

For any current fetch-status question, re-read
`data/v2_1/prospective/health.json` and verify the process rather than relying on the
snapshot above.

## Locked decision rules

- Primary price: latest canonical-YES executed trade at or before each grid time.
- Record `price_age_minutes`; midpoint is separate robustness only.
- News availability: `max(published_at, first_seen_at)`.
- News contract: poll every 60 seconds; `rows >= 200` is censored; no checkpoint
  advance on capped/failed responses; gaps over 300 seconds require reconciliation.
- Primary metrics: average precision and Brier score.
- Validation: five purged expanding-time folds with held-out market groups.
- Uncertainty: 5,000 paired 360-minute moving-block bootstrap replicates by market.
- B1 promotes only if all explicit v2.3 H1–H5 conditions pass.
- Undefined required metrics cannot be interpreted in B1's favour.
- The unsigned jump target authorizes no directional P&L claim.
- Data gate → synthetic market-cluster power simulation → labels is the mandatory
  order.

## Next actions

1. Preserve and monitor PID `94663`; do not inspect protected outcomes.
2. Version-fix stable article identity/content revisions and add synthetic tests.
3. Record and execute an explicit parallel launch of the corrected news collector.
4. Obtain a valid Lumid cursor, time partition or endpoint-equivalent export for the
   unresolved news interval.
5. Continue focused bounded recovery for the 14 frozen markets and 21 news queries.
6. At development close, reconcile `[2026-08-08, 2026-09-28)` and freeze the
   data-sufficiency report.
7. After the gate passes, freeze the label-blind 14-market power simulation.
8. Only then build labels/features/folds and run B0/B1 once.
9. Freeze at most one candidate before October 1 and keep the holdout sealed.

## Prohibited actions

- Never rerun `python -m eventx.tasks.run_frozen_b0_oot_final`.
- Do not use v1 OOT results for tuning.
- Do not create v2.3 labels before the data gate and frozen power simulation.
- Do not inspect or use the October holdout for model selection.
- Do not modify hash-locked manifests or protocol files.
- Do not relax cohort, taxonomy, association or promotion gates post hoc.
- Do not use failed KOL rules or refill missing category strata.
- Do not substitute a non-Lumid datasource without a new label-blind protocol.

## Verification commands

```bash
python -m eventx.tasks.verify_v2_3_preregistration
python -m eventx.release.verify_v1_release
python -m eventx.tasks.launch_v2_1_collector --status
```

Never run the consumed v1 final evaluator.

## Authoritative references

- Active amendment: `eventx/release/v2_3/PREREGISTRATION_AMENDMENT.md`
- Active protocol: `eventx/release/v2_3/protocol.json`
- Active manifest: `eventx/release/v2_3/preregistration_manifest.json`
- News contract: `eventx/release/v2_3/news_collection_contract.json`
- Frozen cohort: `data/v2_1/cohort/selected_markets.jsonl`
- News audit: `data/v2_2/planning/lumid_subwindow_20260808_20260817/audit_manifest.json`
- News diagnosis: `data/v2_2/planning/NEWS_TRUNCATION_DIAGNOSIS_20260817.md`
- Full coordination plan: `COMPLETE_RESEARCH_PLAN.md`
- Supervisor report: `PROGRESS_REPORT.md`
- Detailed legacy archive: `PROGRESS.md`
- New dated logs: `docs/progress/`

If this handoff conflicts with a frozen artifact, the frozen artifact controls. Stop
the conflicting action and correct this file.

## History routing and maintenance

- Read `PROGRESS.md` only for pre-21-August history or detailed historical metrics.
- Read `docs/progress/YYYY-MM.md` only for later history relevant to the task.
- After material work, update this file's current facts and next actions.
- Append detailed evidence to the current monthly log; do not grow this file with
  historical narrative.
- Keep this file below 200 lines where practical. Move stale detail to the monthly
  log while preserving links and integrity state.
- Record exact values from canonical artifacts and never include secrets.
