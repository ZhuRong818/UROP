# V5 v1.1 implementation and remaining gates

Completed: 2026-09-10. **Design revision implemented; real-data experiment blocked.**
No new research labels, protected V4 payloads or consumed outcomes opened. No research
data fetched, collector restarted, external request sent, commit or push performed.

## Work completed

- Published `PROTOCOL_V1_1.md`, preserving method-v1 and its failed screen unchanged.
  The new contract specifies source/target semantics, later-time and family-disjoint
  confirmation, unchanged reduced offset architecture, matched-width versus nested
  Timing diagnostics, separate market replication, fixed final training and precise
  decision/claim boundaries. Umbrella routing now separates old v2.3 instructions.
- Added `uncertainty_v1_1.py`: paired synchronous non-wrapping 3/7/14-day moving-block
  candidates, calendar-gap/support rejection, Monte Carlo Wilson intervals and
  policy/interpretation helpers. These do not certify inference or authorize a run.
- Added `final_fit_v1_1.py`: final tuning on permitted development followed by OOF
  residual fitting/full-training base, returning all six fixed prediction arms.
  It uses the preserved nested trainer, not winning outer-fold parameters.
- Added `rehearsal_v1_1.py`: required evidence-role/hash checks and exclusively
  synthetic one-shot receipt workflow. Receipts precede label callbacks; reruns and
  post-failure retries are refused. Real mode is explicitly unsupported. Hash
  verification is integrity evidence, not scientific source certification.
- **57/57 tests passed**: 45 preserved regression tests plus 12 new tests. New tests
  cover paired/deterministic/common-calendar draws, gaps/short support, interpretation,
  baseline/news separation, hash tampering, pre-label receipts, failed attempts,
  real-mode rejection, and final-fit family/label isolation with held labels NaN.
- **115 prior manifest records verified, zero mismatches** (implementation-v1,
  recovery-summary and frozen V4 implementation manifests). This is a specific
  subset, not a claim to have rerun the earlier 169-record verification.

## Uncertainty screen: none of the candidates is certified

Fixed development screen: six processes × two calendar lengths × three block
lengths = **36 cells**, 100 datasets per cell, 1,000 paired draws per dataset.
Candidates share synthetic data per scenario/trial. This is not an independent
validation suite, fitted-model simulation, or complete decision-hierarchy power.

Nominal 95% null coverage:

| Process / calendar days | 3-day blocks | 7-day blocks | 14-day blocks |
|---|---:|---:|---:|
| IID / 35 | 100% | 100% | 100% |
| Family + daily shocks / 35 | 94% | 94% | 89% |
| AR(0.5) common shock / 35 | 85% | 83% | 75% |
| AR(0.9) common shock / 35 | **52%** | **54%** | **53%** |
| Regime shifts / 35 | 63% | 67% | 62% |
| Sparse/unbalanced / 35 | 84% | 83% | 81% |
| AR(0.9) common shock / 140 | **65%** | **74%** | **75%** |
| Regime shifts / 140 | **37%** | **45%** | **60%** |

False positive lower-bound rates for AR(0.9) were 21% for all three short-calendar
candidates, and 23%/17%/18% respectively at 140 days. See JSON for all scenarios,
Monte Carlo intervals, widths and sparse-exposure rates. Even the longer calendar
does not automatically solve inference. This new simulation uses different seeds
and crossed-family components from the old v1 screen; differences from old coverage
are NOT a controlled estimate of how much changing the method helped.

**Decision: stop certification of this candidate family under the tested broad
dependence envelope.** No automatic winner, threshold relaxation, confidence claim,
or real-data evaluation. Do not spend the independent validation suite on methods
already failing development screens. Next statistical work must justify narrower
sampling assumptions or a materially different dependence treatment, still before
new outcomes. Arbitrary common regime shifts cannot be solved merely by counting
more market rows. Required independent coverage and full-hierarchy power remain open.

Canonical evidence: `data/v5/revision_v1_1_20260910/uncertainty_screen.json`.

## Source and family admission: checked, not passed

Re-read source-only candidate queue and current recovery report:

- 4,651 market entries, 1,551 venue-event candidates, zero missing candidate IDs.
- **Zero approved final event families.** Candidate memberships are not approvals.
- Historical exact-version/status evidence remains uncertified.
- Recovery report has zero reconciled news intervals for V5 certification.

No new provider response or version archive was obtained this turn. The recovered
IDs/snapshots belong to opened historical discovery and cannot create an untouched
confirmation interval. Existing scoped tournament merges remain evidence requiring
cross-venue/season/multi-leg closure, not final independent-family approvals.

### Focused evidence request, prepared but not sent

Ask Lumid for the following, tied to the exact staged IDs/run IDs (not another bulk
article-count export):

1. Versioned market question/outcome-subtitle/category/token/status/scheduled-terminal
   history, with availability and validity, or authoritative row-immutability evidence.
2. Exact article-content versions with availability, or an immutable-content guarantee
   and lineage covering the headline/summary hashes used by EventX.
3. Requested/committed/retried coverage for partial, failed and aborted ingestion runs;
   reconcile the declared feed/window universe without deleting valid committed rows.
4. Endpoint/table mappings and accessible export paths for those proofs.

The old HTTP-500/missing-event-ID provider draft must not be sent as current status.

## Execution-step status

| Requested step | Result |
|---|---|
| Version and consolidate protocol | Completed as v1.1, not executable freeze |
| Repair/validate inference | Candidates implemented and screened; validation FAILED/uncertified |
| Certify data and review families | Current evidence rechecked; certification/approvals blocked |
| Select dates and freeze splits | Not attempted: upstream gates failed |
| Rehearse pipeline | Final-fit/receipt/guard components pass synthetic tests; full production adapter/serialization runner remains unfinished |
| Freeze and run new development | Not authorized by failed gates; no labels opened |
| Promote/confirm | Not attempted |

Next concrete deliverables are a defensible revised inference design, provider
version/completeness evidence, final reviewed family components, and then an
admissible unopened scope. No additional algorithm search is justified by this screen.

Evidence release: `data/v5/revision_v1_1_20260910/{report.json,tests.txt,
uncertainty_screen.json,manifest.json}`. Reproduce only in a new versioned output
directory; the task refuses to overwrite the existing release.
