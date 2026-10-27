# V5 implementation, source recovery and uncertainty check

Date: 2026-09-10. Status: **implementation advanced; real-data freeze/evaluation
blocked**. No new-development labels or protected V4 outcomes opened.

## 1. Implemented and tested

Added separate method-v1 modules without editing the frozen V4 or earlier repair
files:

- `eventx/v5_corrected/experiment_v1.py`: canonical named-market adapter; all four
  residual arms; identical base predictions across arms; 24 residual configurations;
  nested base-C selection **inside each OOF training scope**; strict forward/family
  partitions; OOF-only residual offsets; final base refitting; exact unexposed equality;
  training-rank, coefficient and numerical-convergence diagnostics.
- `eventx/v5_corrected/evaluation_v1.py`: LL/Brier/AP and all-row/exposed/family-balanced/
  time-fold reporting, paired crossed family/calendar bootstrap and sensitivities,
  support gates, subgroup correction, calibration floor, and no-rescue decisions.
  Source/software gates fail before label conversion. These are pure-array functions,
  not permission to run on uncertified data; no autonomous real-data evaluator exists.

The integrated synthetic suite passed **44/44 tests**. The additional variable-content
test passed **1/1**: altering only semantic quality changes the news expert while
leaving the fitted baseline and all three controls exactly unchanged. The initial
integration fixture has constant news inputs; this additional test explicitly covers
the variable-content path rather than relying on that trivial case.

Integration evidence: 320 synthetic rows, 16 outer rows, 48 honest base-OOF rows.
Held-family labels were replaced with NaNs and remained unread. All residual solvers
converged; unexposed predictions equal the shared baseline. No research performance
is inferred from synthetic inner losses or coefficients.

Evidence: `data/v5/experiment_implementation_20260910/` contains test log, fit ledger,
report, bootstrap screen and hashes. Supplemental test:
`eventx/tasks/test_v5_content_integration.py`.

## 2. Important failed uncertainty test — stop before freezing

The method-v1 daily-block rule was tested on **100 synthetic datasets per scenario**,
each with 30 families and 35 days. Each screen used 1,000 bootstrap draws, versus
5,000 specified for the eventual evaluator. Nominal 95% interval coverage of the
known zero mean was:

| Synthetic loss-difference process | Zero covered | Lower bound falsely positive |
|---|---:|---:|
| Independent cell noise | 100/100 | 0/100 |
| Shared family and daily shocks | 99/100 | 0/100 |
| Strong multi-day common shock, AR coefficient 0.9 | **30/100** | **37/100** |

These are Monte Carlo screening results, not EventX outcomes or a proof of behaviour
under every dependence process. In particular, 100/100 is not a claim of certain
coverage. The shifted-effect tests are single-contrast power screens, **not power of
the complete model-selection/promotion procedure** or of the eventual cohort.

Nevertheless, the strong multi-day failure is sufficient to withhold uncertainty
certification. Passing deterministic software tests does not validate confidence
interval coverage. Daily resampling within short fixed outer time blocks cannot
represent arbitrary cross-day/common-regime uncertainty.

**Decision:** method-v1 software gate remains false. Do not freeze an executable
research candidate or generate/open new labels. Keep this failed screen intact.
The next methodological task is a separately versioned, label-blind uncertainty
amendment: clarify the time-conditioned versus repeated-calendar estimand, test
longer/synchronous blocks or dependence-robust alternatives, and include persistence
and sparse/unbalanced exposure scenarios. Do not select the variant that produces a
favourable EventX result, lower the promotion bar, or quietly rewrite method-v1.

## 3. Source recovery succeeded, but source certification did not

Lumid `/retrieve` and materialized downloads now work for the bounded requests.
Recovered **819/819 unique metadata targets**, in 17 batches; exactly one snapshot
per target, no cap hit. Two sandbox connection failures were retained and retried
with approval. Overall recovery evidence: **40 successful / 2 failed attempts**;
an attempt includes its retrieval/download workflow, not a count of HTTP requests.

The originally proposed event-table join is unusable for this slice: all **499,511**
pre-July-22 event-table rows have null normalized `market_ids`. The first event-link
batch returned zero; the other 16 identical-route batches were not needlessly run.

A label-blind raw-key probe identified an alternative within the same Lumid source:
`polymarket_markets.raw.events`. Retrieved **only** condition/market IDs, embedded
event ID/title, contract subtitle and provenance—never full raw blobs, prices or
resolution outcomes. All 17 embedded-membership batches succeeded:

- **819 markets → 321 candidate Polymarket event groups**;
- one candidate event ID per target; no missing/multiple mappings in these results;
- combined queue now covers **4,651 markets / 1,551 venue-event candidates**;
- **zero missing candidate memberships**, but **zero approved independent families**.

This closes the missing candidate-ID problem, not the cross-event/cross-venue
dependency problem. For example, the Polymarket World Cup winner group contains
41 contracts and the Golden Boot group 11; their relationship with fixture and
Kalshi tournament groups still needs review. Do not approve venue events wholesale.

The recovered records are snapshots, not certified metadata/content-version histories.
A bounded accessible-schema inventory found no matching article/market version-history
fields under the searched naming patterns; this does not prove private archives do
not exist. News completeness remains unreconciled. Historical ingestion timestamps
and downloaded hashes alone do not establish earlier availability of the exact bytes.

Evidence:

- `data/v5/embedded_membership_recovery_20260910/`: projected SQL, memberships,
  report and manifest;
- `data/v5/recovery_summary_20260910/`: reconciled receipt report, refreshed candidate
  family queue and hashes;
- dated attempts in `data/v5/provenance_recovery_20260908/`: all receipts, failed
  attempts and projected downloads, including the version-evidence inventory.

The previous provider draft's HTTP-500/missing-ID descriptions are now historical.
The remaining provider need is exact-version availability, metadata status histories
and committed-row/retry/interval-completeness evidence. No request was sent externally.

## 4. V4 health and integrity

At **2026-09-10 02:03:04 UTC**, collector 72506 and caffeinate child 72517 were alive.
The September 9 partitions advanced: **11 news days / 4 trade days**, with all
**51 expected receipts** present and no closed-day backlog. The broken-pipe logging
warning persists after successful checkpoint writes; no restart was necessary for
this catch-up check and none was performed.

All 15 frozen implementation hashes still match. Consumption receipt, examples,
evaluation attempt, predictions and result files are absent (existence checks only).
No sealed payload contents read. Receipt presence still does not replace the frozen
post-close completeness gate.

Evidence: `data/v4/health_checks/20260910T020304Z/report.json`.

## 5. What remains before a real V5 run

1. Validate and version the uncertainty procedure after the failed persistence screen.
2. Certify historical metadata and exact article versions; reconcile news coverage.
3. Finish semantic dependency/cross-venue family review and label-blind exclusions.
4. Select admissible unopened historical scope if available; freeze exact data,
   row/split ledgers, warm-up, evaluator, numerical/environment hashes and confirmation
   boundaries. Never reuse opened history or the protected V4 interval.
5. Only then open development labels and run the fixed hierarchy once.

No final cohort, dates or candidate were invented to bypass these gates. No new V5
research result, candidate promotion, confirmation receipt or final evaluation exists.
