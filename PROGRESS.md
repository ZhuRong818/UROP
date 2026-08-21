# EventX detailed progress archive

> Legacy detailed ledger through 21 August 2026. Routine startup now reads
> [`CURRENT_STATE.md`](CURRENT_STATE.md); consult this file only when historical detail
> is required. Frozen JSON and protocol artifacts remain authoritative.

Archived: **2026-08-21 15:33 Asia/Singapore**

## Current status

- **Current stable release:** v1 frozen pilot/reference release completed.
- **Active research cycle:** v2.3 prospectively preregistered as
  `eventx-v2.3-news-availability-clarifications-20260817`; its 16-artifact manifest
  verifies with no failures, and no v2/v2.1/v2.2/v2.3 development or holdout labels
  have been created or inspected. v2.2 was superseded label-blindly and remains
  immutable lineage alongside v2.1.
- **Deadline:** complete the scientific result and internal artifact package by
  2026-10-31. The original November-holdout v2 protocol remains sealed but was
  superseded before selection and labels.
- **Consolidated research plan:** the new
  [complete research and experiment plan](COMPLETE_RESEARCH_PLAN.md) unifies the
  program goals, required data, methods, experiment matrix, execution gates,
  deliverables, and full-benchmark extension. Its August 17 v2.3 revision locks all
  external observational inputs to valid Lumid endpoints, makes B1-versus-B0 the
  confirmatory pilot, fixes the September 28 cutoff/72-hour buffer, uses uniform
  last-trade primary prices, clarifies the label threshold, adds price-age robustness,
  removes directional P&L from the unsigned-jump target, and freezes news censoring,
  point-in-time availability, undefined-fold, and execution-order rules.
  It is a non-frozen coordination document; sealed protocols and manifests remain
  controlling.
- **Supervisor progress report (August 21):** a self-contained submission-ready
  [research progress report](PROGRESS_REPORT.md) now records the proposal,
  methodology, verified historical results, active data inventory, current collection
  state, bottlenecks, mitigations and October schedule. It changes no frozen scientific
  decision and reports no new labels or model outcomes.
- **Reference model:** B0 market-only standardized logistic SGD.
- **News/KOL status:** core news, rich news, KOL, gated KOL, and combined
  news+KOL candidates were all rejected on purged development folds.
- **Final evaluation:** completed once on a new July 23–30 out-of-time holdout.
- **Holdout state:** **consumed**. The receipt prohibits rerunning the evaluator.
- **Release package:** complete and verified; see
  [the v1 release index](eventx/release/v1/README.md).
- **Publication documentation:** editorial audit and datasheet complete.
  Public redistribution remains **NO-GO** pending the controlling readiness checklist.
- **Active EventX work:** the label-blind prospective collector continues to refresh
  its health ledger. Lumid's required REST data routes recovered by the August 17 check and the
  process is again recording successful trade/news requests, but the August outage
  gaps and exact-window completeness have not yet been reconciled.
- **Historical bulk fetch:** the chained process has ended. Kalshi is complete;
  Polymarket completed 175,414 of 175,423 distinct roster IDs, with nine API-error
  misses retained as an explicit 0.01% gap.
- **Corrected taxonomy:** `eventx-v2.1-taxonomy-v7` is accepted and frozen for all
  3,420 candidate markets. Its independent 250-row blind audit achieved precision
  0.9720 and recall 0.9739; all category precision values are at least 0.94.
- **v2.3 timing:** warmup and selection are closed; development runs August
  8–September 27 UTC, a fixed label-blind reconciliation/evaluation/freeze buffer runs
  September 28–30, the one-shot holdout runs October 1–21, and finalization runs
  October 22–31 UTC.
- **Lumid API audit (August 12):** the live contract exposes 169 paths, 171 HTTP
  operations, and 90 MCP tools. Authentication and control-plane routes work, but
  representative prediction-market, news, KOL, and wider warehouse routes returned
  HTTP 500. Lumid's usage telemetry reports 133,925 5xx responses out of 136,625
  calls (98.0238%) since August 10, with zero 429s. `/health` and `/status` are green
  while `/freshness` fails, so status is not data-health proof. See the
  [August 12 Lumid audit](data/v2_1/planning/LUMID_API_AUDIT_20260812.md).
- **Current source gap:** at the August 17 05:13 UTC health snapshot, the collector's
  newest recorded events were KOL July 25 12:34 UTC, news August 14 23:20 UTC, Kalshi
  trades August 10 03:33 UTC, and Polymarket trades August 13 06:53 UTC. Successful
  requests had resumed, but exact bounded recovery remains mandatory before
  development labels because request success and rotating-candidate cursors do not
  prove complete history for the frozen 14 markets.
- **Lumid incident recheck (August 14):** the same critical prediction-market,
  news, KOL, catalog-source, and freshness routes still return HTTP 500. Current
  telemetry shows 169,002 5xx responses out of 171,717 calls (98.4189%) and zero
  429s. PID `94663` remains alive but unchanged in usable event coverage; see the
  provider-ready [broken-parts report](data/v2_1/planning/LUMID_BROKEN_PARTS_20260814.md).
- **Lumid recovery/contract check (August 17):** the live OpenAPI contract still
  exposes 169 paths and 171 operations. Read-only authenticated probes returned HTTP
  200 for the required LQT, event, venue-detail, Polymarket/Kalshi trade, news,
  KOL-search, freshness, usage, and catalog-source route families. Optional candles,
  orderbook, open-interest, matched-pair, symbol-news/sentiment, KOL history, and KOL
  archive-stat routes were also documented and returned HTTP 200, although several
  examined market/window queries were empty. This establishes route recovery, not
  complete EventX coverage; the exact data gate remains closed.
- **v2.2 label-blind Lumid rehearsal (August 17):** the exact August 8–17 drill passed
  all 14 market-detail canonical mappings and all 14 venue-trade integrity checks,
  retaining 5,817 canonical-YES trades with no zero-record market. It is frozen as
  `incomplete`, not passed: `/news/latest` returned exactly 200 rows despite
  `limit=5000` and provides no cursor or upper-time parameter, leaving unresolved
  truncation risk; two post-cutoff news rows were quarantined. All 21 frozen
  `/news/search` requests avoided the cap. `/news/stats` reports 10,861 `company` rows
  in the last seven days, so category partitioning alone cannot prove broad-feed
  completeness. No labels, prevalence, folds, predictions, or model metrics were read.
- **v2.3 news contract freeze (August 17):** a separate label-blind collector and
  offline verifier now implement a 60-second polling interval, a 200-row censoring
  alarm, a maximum five-minute successful-request gap, no checkpoint advance on a
  capped or failed response, append-only first-seen provenance, and primary feature
  availability at `max(published_at, first_seen_at)`. The same rules apply in
  development and holdout. Synthetic cap, gap, recovery, and backfill fixtures pass.
  The existing PID `94663` remains alive and was deliberately not restarted; it is
  legacy evidence collection and does not satisfy the v2.3 news contract.
- **Live collector check (August 21):** PID `94663` remains alive and label-blind. At
  `2026-08-21T06:46:59Z` it had recorded 147,146 market-event snapshots, 4,196 news
  rows, 17,707 Kalshi trades, 61,919 Polymarket trades and 1,853 KOL rows. Recent
  requests were succeeding, but the process still identifies the v2.1 protocol and
  does not prove v2.3 news completeness. Pre-launch code review also found that the
  frozen v2.3 news record key combines stable identity with the full-row content hash;
  article revisions may therefore evade same-article timestamp-conflict detection. A
  new label-blind implementation version and synthetic revision tests are required
  before that collector is launched.
- **Post-selection reconciliation:** complete and verified for all 3,420 candidate
  endpoints with zero endpoint errors. The exact half-open window contains 30,862
  Polymarket and 5,171 Kalshi records; 353 records were recovered beyond the
  prospective seed.
- **Frozen v2.1 cohort:** 14 markets passed every preregistered threshold: four Kalshi
  politics, five Polymarket politics, four Polymarket other, and one Polymarket sports.
  There are no selected crypto or macro markets; do not relax thresholds or refill
  strata after observing this label-blind result.
- **Association audit v1 candidate:** independently reviewed, failed, and sealed as
  opened development material. Overall
  precision was 0.8867 but hard-candidate recall was 0.8418, below the fixed 0.90
  gate. News passed (0.9733 precision, 0.9605 recall); KOL failed (0.8000 precision,
  0.7317 recall). All 300 reviewed pairs are excluded from later validation by
  `(market_id, content_hash)` and `pair_id`; the accepted news logic remains unchanged.
- **KOL association v2 candidate:** independently reviewed and failed its fresh
  audit. The 150-row unopened sample produced 62 TP, 12 FP, 36 FN, and 38 TN across
  148 decided rows, with two uncertain rows. Precision was 0.8378 and hard-candidate
  recall was 0.6327, below both fixed gates; F1 was 0.7209. The earlier
  0.9756/0.9756 opened-development diagnostic did not generalize and remains
  non-validating.
- **KOL-v2 audit disposition:** frozen as failed opened development material. Its 150
  pairs join the prior 300 in a cumulative 450-pair exclusion ledger and cannot be
  reused to validate another revision.
- **Next allowed research work:** do not use KOL-v2 for features. Proceed under v2.3
  with B1 versus B0. Make and record an explicit collector-migration decision before
  replacing or supplementing PID `94663`, resolve the historical broad-news
  truncation blocker using only valid Lumid mechanisms, pass the full label-blind data
  gate, and then complete and freeze the synthetic 14-market power simulation. No
  development or holdout outcomes have been inspected.
- **Not allowed:** tune features, eligibility, association rules, models, or
  hyperparameters using the consumed v1 out-of-time results; build v2.3 labels before
  the data-sufficiency gate and frozen power simulation pass; or inspect the reserved
  v2.3 holdout early.

## Frozen v1 research contract

- Task: 30-minute prediction-market jump classification.
- Unit: canonical YES outcome at a 5-minute evaluation cadence.
- Frozen cohort: 20 Polymarket binary outcomes selected from training-period
  information only.
- Primary metric: average precision.
- Calibration metric: Brier score.
- Validation: five-fold purged expanding-window evaluation with a 30-minute purge.
- Reference learner: standardized logistic SGD.
- Fixed hyperparameters: 8 epochs, learning rate 0.02, L2 0.0001, shuffle seed 11.
- Market features: 11 locked price, momentum, volatility, trading-activity, notional,
  and recency features.
- Transform: `log1p` for trade-count and notional feature families; identity otherwise.

## Dataset versions and integrity

| Version | Dataset ID | Window | Role | State |
|---|---|---|---|---|
| v1 toy | `eventx-toy-ceea70842baa88753929` | 2026-05-22–2026-07-22 | Development and original split | Frozen; original test was previously exposed by a noncanonical B0 |
| v1 OOT | `eventx-oot-7c4fd487edb3928b9253` | 2026-07-23–2026-07-30 | Replacement confirmatory holdout | Frozen, evaluated once, consumed |
| v2 prospective | `eventx-v2-preregistered-20260731` | 2026-08-01–2026-11-30 | Superseded November schedule | Sealed; superseded before selection/labels |
| v2.1 prospective | `eventx-v2.1-october-deadline-20260731` | 2026-08-01–2026-10-21 | Prior October schedule | Sealed; superseded label-blindly by v2.2 |
| v2.2 prospective | `eventx-v2.2-october-pilot-fixes-20260817` | 2026-08-01–2026-10-21 | Superseded timing and measurement protocol | Sealed; superseded label-blindly by v2.3 |
| v2.3 prospective | `eventx-v2.3-news-availability-clarifications-20260817` | 2026-08-01–2026-10-21 | Active B1-versus-B0 protocol-validation pilot | Preregistered; all labels unavailable/uninspected |

Important dataset facts:

- v1 toy contains 20 selected outcomes.
- Development OOF comparison uses 17,540 rows and 2,027 jumps.
- Canonical final B0 training uses 20,702 eligible pre-holdout rows.
- OOT snapshot contains 2,080 fresh trades.
- OOT evaluation contains 1,410 eligible 5-minute rows, 13 markets, and 130 jumps.

Frozen-manifest hashes:

| Artifact | SHA-256 |
|---|---|
| `data/v1/toy/frozen_manifest.json` | `db076d3b9bd48897c590bb933c9b619657201a2c168f954e76ef346af28c4f88` |
| `data/v1/toy/final_baseline_freeze_manifest.json` | `0d0f93b6f50c60381a38f19daf64123a5efccc9bfa5c6c36d7f99ad550ee37e4` |
| `data/v1_oot_20260723_20260730/frozen_holdout_manifest.json` | `737624dffdaac0b65ca78700c35a116235efb74d4032818ef1f7320345db4e17` |
| `data/v1_oot_20260723_20260730/b0_oot_final_result.json` | `18306a8b814cec48f2acdce3fe93e06f33ee5c0d3cf41344d11339bb5e102a6a` |
| `eventx/release/v1/release_manifest.json` | `ec53fc2813c7eeb56f4a3dddbb9d66154668deb83941eb1b41a477028ce49c85` |
| `eventx/release/v2/preregistration_manifest.json` | `ded459721e4b13252c653edff2a4290c89619b4b4770852a0227011308525df5` |
| `eventx/release/v2_1/preregistration_manifest.json` | `5bb2eee34360fc4a85be73d183f835aff36837b78011bc8c863eb981e1c02597` |
| `eventx/release/v2_2/preregistration_manifest.json` | `d7de971665f4a8db9d6b8963fcd1433dc0ddd81b16cff0ffaacdb0b90b58bb58` |
| `eventx/release/v2_3/preregistration_manifest.json` | `03b2ecb8493882c0c4a6b3dc6caad8f96ce155beda9a774527c75e0340b4ec35` |
| `eventx/release/v2_3/news_collection_contract.json` | `32cd7ca0ada2f94f827f3ecc87997244cf856ba0acebfb1c45e2533fd4510489` |
| `data/v2_2/planning/lumid_subwindow_20260808_20260817/audit_manifest.json` | `230b825286b364fac51f332182d2ba85222f2765f5d1fa461a1df8914cdce5b7` |
| `data/v2_2/planning/NEWS_TRUNCATION_DIAGNOSIS_20260817.md` | `ded393ed16709df4344a59cde9f78a784b4ffc3bcb47c64111220dea25a94549` |

## Version and experiment history

All development metrics below are aggregate out-of-fold metrics on the same 17,540
rows. “Brier improvement” is reference Brier minus candidate Brier, so positive is
better.

| Stage | Candidate | AP | Brier | Incremental result | Decision |
|---|---|---:|---:|---|---|
| v1.0 | B0 market-only | 0.140883 | 0.102669 | Reference | Retain |
| v1.1 | B2 market + KOL | 0.130623 | 0.105419 | AP −0.010260; Brier improvement −0.002750 vs B0 | Reject |
| v1.2 | Nested gated KOL | 0.136126 | 0.102895 | AP −0.004757; Brier improvement −0.000227 vs B0 | Reject |
| v1.3 | Market + rich news | 0.121761 | 0.107002 | AP −0.019122; Brier improvement −0.004334 vs B0 | Reject |
| v1.4 | B1 market + core news | 0.142310 | 0.103441 | AP +0.001427; Brier improvement −0.000772 vs B0 | Reject |
| v1.5 | B3 market + core news + KOL | 0.133268 | 0.105973 | AP −0.009042; Brier improvement −0.002533 vs B1 | Reject |
| v1.6 | B0 on new OOT holdout | 0.135527 | 0.084190 | AP +0.043328; Brier improvement +0.000121 vs constant training prevalence | Final one-shot result |
| v1.7 | Frozen pilot release package | — | — | Final report, evidence manifest, and verifier | Complete |
| v1.8 | Editorial audit + datasheet | — | — | Claim audit passed; category defect disclosed; public release NO-GO | Complete |
| v2.0 | Prospective protocol + temporal seals | — | — | Protocol, taxonomy guide, label-blind coverage monitor, and cohort freezer | Preregistered before labels |
| v2.1 | October-deadline schedule | — | — | Shortened selection/development and moved one-shot holdout into October; scientific contract otherwise unchanged | Preregistered before selection/labels |
| v2.1a | Prospective collector | — | — | REST news/KOL/metadata plus 3,420-market round-robin trade capture; content-keyed provenance and health ledger | Running, label-blind |
| v2.1b | Corrected category taxonomy v7 | 0.9720 precision | 0.9739 recall | 250-row stratified blind audit; 99.6% inter-reviewer agreement; all category precision values ≥0.94 | Accepted and frozen before labels |
| v2.1c | Exact-window trade reconciliation | — | — | 3,420/3,420 endpoints done; 36,033 records; 353 recovered beyond the prospective seed; hashes verified | Complete, label-blind |
| v2.1d | Frozen activity-selected cohort | — | — | 1,167 activity rows; 14 markets passed all fixed thresholds; all cohort/reconciliation hashes verified | Frozen, label-blind |
| v2.1e | Association rule v1 candidate audit | 0.8867 precision | 0.8418 recall | News 0.9733/0.9605 passed; KOL 0.8000/0.7317 failed; 17 FP and 25 FN overall | Rejected; not frozen |
| v2.1f | KOL-v1 error analysis + KOL-v2 candidate | 0.9756 precision | 0.9756 recall | Opened 150-row KOL development diagnostic only: 80 TP, 2 FP, 2 FN, 66 TN; source/spec frozen before resampling | Candidate frozen; not validated |
| v2.1g | Fresh KOL-v2 blind audit | — | — | 150 unopened KOL pairs, 75 matched/75 hard-unmatched, all 14 markets, zero opened-pair leakage | Frozen; awaiting independent review |
| v2.1h | Fresh KOL-v2 audit result | 0.8378 precision | 0.6327 recall | 62 TP, 12 FP, 36 FN, 38 TN on 148 decided rows; two uncertain; F1 0.7209 | Rejected and frozen as opened development material |
| v2.1i | Lumid API/data availability audit | — | — | 169 paths/171 operations/90 MCP tools inventoried; authenticated cross-domain probes; 98.0238% service-telemetry 5xx share; collector gaps recorded | Data-plane incident; B1/B0 conditionally feasible pending exact recovery |
| v2.1j | Lumid incident recheck and broken-parts report | — | — | Critical routes still HTTP 500 on August 14; 169,002/171,717 calls were 5xx; current collector errors and exact recovery IDs recorded | Incident ongoing; no label pipeline authorized |
| v2.1k | Lumid endpoint-locked plan and recovery check | — | — | 169-path/171-operation contract revalidated; required and optional EventX REST families returned HTTP 200; complete data/field/procedure registry added without changing frozen design | Service routes recovered; B1/B0 conditionally feasible pending exact-window gate |
| v2.2 | Option-A timing and measurement amendment | — | — | Development ends Sep 28; 72-hour freeze buffer; B1 vs B0 confirmatory; uniform last-trade primary; threshold semantics and price-age robustness fixed; directional P&L removed | Preregistered and verified label-blindly |
| v2.2a | Aug 8–17 Lumid subwindow drill | — | — | 14/14 detail and trade checks passed; 5,817 YES trades; 21 frozen searches uncapped; `/news/latest` silently capped at 200; two post-cutoff rows quarantined | Frozen incomplete; broad-news recovery blocker remains |
| v2.3 | News-availability clarification amendment | — | — | Explicit B1/B0 hypotheses and undefined-fold disposition; 60-second/200-row/300-second news contract; first-seen availability; data-gate → power → labels order; news-pilot positioning | Preregistered and verified label-blindly; v2.2 preserved as superseded lineage |
| v2.3a | News-contract implementation rehearsal | — | — | Synthetic capped, request-gap, recovery, and publication/backfill cases exercise the frozen collector semantics without fetching labels | Offline checks pass; live v2.3 collector not yet launched |
| v2.3b | Supervisor progress report and pre-launch implementation review | — | — | Self-contained proposal/progress report created; live collector rechecked; article identity/version-key edge recorded without opening labels | Report complete; corrected collector version still required before launch |
| v2.3c | Compact handoff migration | — | — | `CURRENT_STATE.md` made canonical startup context; this file retained as legacy archive; future details routed to monthly logs | Complete; no scientific or integrity state changed |

Fold and uncertainty notes:

- Full KOL improved AP and Brier in only 1 of 5 development folds.
- Nested KOL gates selected `360m, off, off, off, off`; gating did not rescue it.
- Core news improved AP in 3 of 5 folds and Brier in 2 of 5 folds.
- Core-news Brier bootstrap 95% interval: `[-0.001769, 0.000113]`.
- Combined B3 versus B1 improved AP and Brier in only 1 of 5 folds.
- Combined B3-versus-B1 Brier bootstrap 95% interval:
  `[-0.003883, -0.001163]`.

## Association-rule versions

### KOL rule v3

- Rule ID: `eventx-kol-rule-v3-6b5ad3cb2938abeb0ec1`
- Blind adjudication: precision 0.8850, recall 0.9365, F1 0.9100.
- Associations: 3,394 across the frozen 20-market cohort.
- Rule quality passed its audit threshold, but predictive KOL features failed model
  promotion because their temporal signal was unstable.
- Freeze: [KOL rule manifest](data/v1/curated/kol_rule_v3_frozen_manifest.json)

### News rule v1

- Rule ID: `eventx-news-rule-v1-563b717565788d102198`
- Blind review: precision 0.9286, hard-candidate recall 0.9701, F1 0.9489.
- Retrieval: 543 rows, 465 unique in-window articles, 149 associations, 8 markets.
- Rule quality passed its audit threshold, but neither rich nor core news passed the
  predictive freeze gate.
- Freeze: [news rule manifest](data/v1/curated/news_rule_v1_frozen_manifest.json)

### v2.1 association rule v1 candidate

- Rule ID: `eventx-v2.1-association-rule-v1-candidate`.
- Independent blind review: 300/300 rows complete, no uncertain labels.
- Overall: precision 0.8867, hard-candidate recall 0.8418, F1 0.8636.
- News: precision 0.9733, recall 0.9605, F1 0.9669 — source gate passed.
- KOL: precision 0.8000, recall 0.7317, F1 0.7643 — both source gates failed.
- Decision: reject and do not freeze. All 300 rows are now rule-development data and
  must be excluded from any fresh validation audit.
- Evidence: [v2.1 association audit report](data/v2_1/association/v1_audit/association_audit_report.json).

### v2.1 KOL association rule v2 candidate

- Rule ID: `eventx-v2.1-kol-association-rule-v2-candidate`.
- Scope: KOL only. The accepted news-v1 source path and hash are unchanged.
- Error taxonomy: all 15 KOL false positives and 22 KOL false negatives were assigned
  one counted primary mode. Dominant misses were Portuguese election language (7) and
  indirect geopolitical capacity/escalation evidence (7); dominant false matches were
  wrong person/event (5), generic/polysemous overlap (4), and cross-topic aggregation (3).
- Opened development diagnostic: 80 TP, 2 FP, 2 FN, 66 TN; precision, recall, and F1
  all 0.9756. This is not a validation result because all 150 rows were opened during
  v1 review.
- Candidate source SHA-256:
  `c8431cb32f859ad457f99128ac3e5b1455f7d032ebd588d7f721f4265e7ca5ef`.
- Lexical-spec SHA-256:
  `fef65090aeea2895cf8ea043f5fbd7f51298754679007af2f12c5aa6cb7ffdfa`.
- Fresh validation result: 62 TP, 12 FP, 36 FN, 38 TN on 148 decided rows, plus two
  uncertain rows; precision 0.8378, hard-candidate recall 0.6327, F1 0.7209. The
  candidate failed both fixed gates and the no-uncertain requirement.
- Decision: reject. The full 150-row sample is opened development material and joins
  the cumulative 450-pair exclusion ledger.
- Evidence: [KOL error analysis](data/v2_1/association/v1_audit/KOL_ERROR_ANALYSIS.md),
  [candidate freeze](data/v2_1/association/kol_v2_candidate/candidate_freeze_manifest.json),
  [fresh audit freeze](data/v2_1/association/kol_v2_audit/kol_v2_audit_freeze_manifest.json),
  [failed audit report](data/v2_1/association/kol_v2_audit/kol_v2_audit_report.json),
  [failed-result manifest](data/v2_1/association/kol_v2_audit/kol_v2_failed_audit_result_manifest.json),
  and [blind-review guide](eventx/release/v2_1/KOL_V2_BLIND_REVIEW_GUIDE.md).

## KOL failure diagnosis

- B3 versus B1 aggregate AP change: −0.009042.
- B3 versus B1 aggregate Brier improvement: −0.002533.
- Removing any single market or any single fold did not make Brier improvement positive.
- Eleven of 14 KOL coefficients changed sign across folds.
- Five of 14 KOL feature-label correlations reversed in fold 3.
- Hormuz contributed 84.2% of the net Brier loss. Removing it made AP slightly positive
  (+0.001756) but Brier remained worse (−0.000460).
- On fold-3 rows with KOL activity in the prior 30 minutes, B3 raised mean prediction
  from 0.145 to 0.188 against 0.144 prevalence; Brier improvement was −0.037041.
- Conclusion: ranking damage was concentrated, but calibration damage was broader.
  Do not select another KOL candidate on these development folds.

Detailed evidence:

- [failure diagnosis memo](data/v1/toy/combined_b3_failure_diagnostic.md)
- [failure diagnostic JSON](data/v1/toy/combined_b3_failure_diagnostic.json)

## Test and holdout history

### Original v1 test block — descriptive only

The original test was already evaluated on 2026-07-29 by an earlier noncanonical B0.
It is not an untouched confirmatory result.

- Rows: 2,276.
- AP: 0.131630.
- Brier: 0.112597.
- Differences from canonical B0: trained only on 17,538 original train rows rather
  than all 20,702 pretest rows, and did not log-transform trade-count features.
- Disclosure:
  [final baseline freeze memo](data/v1/toy/final_baseline_freeze_manifest.md)

### Replacement OOT holdout — final

- Dataset ID: `eventx-oot-7c4fd487edb3928b9253`.
- Window: 2026-07-23 through 2026-07-30.
- Frozen before label outcomes, prevalence, or metrics were inspected.
- Evaluated exactly once with canonical B0.
- B0: AP 0.135527; Brier 0.084190; mean prediction 0.119406.
- Constant training-prevalence baseline: AP 0.092199; Brier 0.084310.
- Holdout prevalence: 0.092199.
- Interpretation: useful ranking discrimination; only marginal calibration
  improvement; mean prediction exceeded prevalence by 2.72 percentage points.
- Consumption time: `2026-07-31T03:31:03.495303Z`.
- Rerun permitted: **false**.

Final artifacts:

- [final evaluation report](data/v1_oot_20260723_20260730/final_evaluation_report.md)
- [final result JSON](data/v1_oot_20260723_20260730/b0_oot_final_result.json)
- [frozen holdout manifest](data/v1_oot_20260723_20260730/frozen_holdout_manifest.json)
- [consumption receipt](data/v1_oot_20260723_20260730/holdout_consumption_receipt.json)

## v1 release package

The v1 pilot is packaged without duplicating the multi-gigabyte frozen extract:

- [release index](eventx/release/v1/README.md)
- [final research report](eventx/release/v1/FINAL_RESEARCH_REPORT.md)
- [dataset datasheet](eventx/release/v1/DATASHEET.md)
- [editorial audit](eventx/release/v1/EDITORIAL_REVIEW.md)
- [public-release readiness checklist](eventx/release/v1/PUBLIC_RELEASE_CHECKLIST.md)
- [machine-readable release manifest](eventx/release/v1/release_manifest.json)
- [release verifier](eventx/release/verify_v1_release.py)

Verification command:

```bash
python -m eventx.release.verify_v1_release
```

Verified at this update: 25 artifacts checked, no failures, OOT state `consumed`.
The package is explicitly scoped as a 20-market, one-horizon Polymarket pilot, not
the completed multi-venue EventX benchmark described by the full research plan.

Editorial review found no mismatch in the reported metrics, model decision, dataset
IDs, or holdout state. It found one frozen metadata defect: the Karen Bass mayoral
market is incorrectly tagged `sports`. The frozen cohort remains unchanged for hash
integrity; category-stratified claims are prohibited until corrected metadata are
versioned.

## Active v2.3 prospective cycle

The October completion constraint was first recorded in v2.1 before selection and
labels. On August 17, while all development and holdout labels still remained
uncreated and uninspected, v2.2 superseded—not edited—the sealed v2.1 schedule, and
v2.3 then superseded—not edited—v2.2 to freeze the remaining news-availability and
decision-rule ambiguities. Active protocol
`eventx-v2.3-news-availability-clarifications-20260817` tests B1 market + core news
versus B0 market only as a prospective protocol-validation pilot. It does not test
KOL incremental information; no failed KOL candidate may be rescued post hoc.

Frozen protocol decisions include:

- Polymarket and Kalshi binary canonical-YES markets;
- label-blind activity selection, with at most 40 markets per venue/category cell;
- corrected categories `politics`, `crypto`, `sports`, `macro`, and `other`;
- 5-minute cadence and horizons 5, 30, 120, 360, and 1,440 minutes, with 30 minutes
  primary;
- B0's locked market family plus venue and the four accepted core-news features for
  B1; KOL features are ineligible in this cycle;
- uniform latest canonical-YES trade at or before each grid time as the primary price,
  with recorded price age and separately reported midpoint robustness only;
- the inherited threshold formula as a heuristic 30-minute anchor in one-minute sigma
  units, not four horizon sigmas;
- explicit active H1–H5 definitions for B1 versus B0, with any undefined required
  fold metric counting as non-positive and any undefined aggregate or venue condition
  failing its corresponding promotion requirement;
- a 60-second news poll, 200-row censoring alarm, five-minute maximum successful-
  request gap, no checkpoint advance after capped/failed retrieval, and unresolved
  intervals classified as B1 incomplete rather than zero news;
- primary point-in-time news availability at
  `max(published_at, first_seen_at)`, with both raw timestamps retained;
- descriptive price-age ≤30/≤60-minute and trade-arrival robustness checks;
- five purged expanding time folds with held-out market groups;
- average precision primary and Brier calibration, 5,000 blocked bootstraps, and
  fixed promotion gates;
- the label-blind data gate and frozen synthetic market-cluster power simulation must
  precede label creation; and
- one future October holdout evaluation with a consumption receipt and no reruns.

The v2.3 study/report is positioned as **a prospective protocol-validation study of
incremental news information in prediction-market repricing**. The wider EventX KOL
hypothesis remains deferred.

Windows are half-open UTC:

| Stage | Start | End (exclusive) | State at this update |
|---|---|---|---|
| Warmup | 2026-07-31 | 2026-08-01 | Closed |
| Selection | 2026-08-01 | 2026-08-08 | Closed; reconciled, activity built, cohort frozen and verified |
| Development | 2026-08-08 | 2026-09-28 | Open; labels remain unavailable/uninspected pending data freeze |
| Reconciliation/evaluation/freeze | 2026-09-28 | 2026-10-01 | Fixed 72-hour buffer; candidate must freeze before holdout access |
| Holdout | 2026-10-01 | 2026-10-22 | Reserved; labels unavailable/uninspected |
| Finalization | 2026-10-22 | 2026-11-01 | Final report and internal artifact package |

Artifacts:

- [complete research and experiment plan](COMPLETE_RESEARCH_PLAN.md)
- [supervisor research progress report](PROGRESS_REPORT.md)
- [v2.3 news-availability amendment](eventx/release/v2_3/PREREGISTRATION_AMENDMENT.md)
- [active v2.3 machine-readable protocol](eventx/release/v2_3/protocol.json)
- [active v2.3 locked manifest](eventx/release/v2_3/preregistration_manifest.json)
- [frozen v2.3 news collection contract](eventx/release/v2_3/news_collection_contract.json)
- `eventx/tasks/collect_v2_3_news.py`
- `eventx/tasks/verify_v2_3_news_contract.py`
- `eventx/tasks/verify_v2_3_preregistration.py`
- [v2.2 Option-A amendment](eventx/release/v2_2/PREREGISTRATION_AMENDMENT.md)
- [superseded v2.2 machine-readable protocol](eventx/release/v2_2/protocol.json)
- [superseded v2.2 locked manifest](eventx/release/v2_2/preregistration_manifest.json)
- [frozen label-blind Lumid drill report](data/v2_2/planning/lumid_subwindow_20260808_20260817/AUDIT_REPORT.md)
- [frozen label-blind Lumid drill manifest](data/v2_2/planning/lumid_subwindow_20260808_20260817/audit_manifest.json)
- [Lumid news-truncation diagnosis](data/v2_2/planning/NEWS_TRUNCATION_DIAGNOSIS_20260817.md)
- `eventx/tasks/verify_v2_2_preregistration.py`
- `eventx/tasks/audit_v2_2_lumid_subwindow.py`
- [October-deadline amendment](eventx/release/v2_1/PREREGISTRATION_AMENDMENT.md)
- [superseded v2.1 machine-readable protocol](eventx/release/v2_1/protocol.json)
- [superseded v2.1 locked manifest](eventx/release/v2_1/preregistration_manifest.json)
- [corrected taxonomy guide](eventx/release/v2/TAXONOMY_GUIDE.md)
- [accepted taxonomy audit](data/v2_1/taxonomy/audit_report.json)
- [taxonomy freeze manifest](data/v2_1/taxonomy/taxonomy_freeze_manifest.json)
- [accepted 3,420-market category mapping](data/v2_1/taxonomy/market_categories.jsonl)
- [v2.1 cohort-freeze procedure](eventx/release/v2_1/COHORT_FREEZE_PROCEDURE.md)
- [reconciliation coverage report](data/v2_1/selection/reconciled/coverage_report.json)
- [reconciliation manifest](data/v2_1/selection/reconciled/reconciliation_manifest.json)
- [activity report](data/v2_1/selection/activity_report.json)
- [frozen cohort manifest](data/v2_1/cohort/cohort_freeze_manifest.json)
- [frozen 14-market cohort](data/v2_1/cohort/selected_markets.jsonl)
- [association audit plan](eventx/release/v2_1/ASSOCIATION_AUDIT_PLAN.md)
- [association audit preparation report](data/v2_1/association/v1_audit/association_audit_preparation_report.json)
- [association blind-review packet](data/v2_1/association/v1_audit/association_blind_review.jsonl)
- [completed independent association review](eventx/release/v2_1/eventx_v2_1_blind_review_completed.jsonl)
- [failed association audit report](data/v2_1/association/v1_audit/association_audit_report.json)
- [failed-audit freeze manifest](data/v2_1/association/v1_audit/audit_freeze_manifest.json)
- [opened-pair exclusion ledger](data/v2_1/association/v1_audit/opened_pair_content_exclusions.jsonl)
- [KOL-v1 error analysis](data/v2_1/association/v1_audit/KOL_ERROR_ANALYSIS.md)
- [KOL-v2 candidate freeze](data/v2_1/association/kol_v2_candidate/candidate_freeze_manifest.json)
- [fresh KOL-v2 audit preparation](data/v2_1/association/kol_v2_audit/kol_v2_audit_preparation_report.json)
- [fresh KOL-v2 audit freeze](data/v2_1/association/kol_v2_audit/kol_v2_audit_freeze_manifest.json)
- [fresh KOL-v2 blind packet](eventx/release/v2_1/eventx_v2_1_kol_v2_blind_review.jsonl)
- [KOL-v2 blind-review guide](eventx/release/v2_1/KOL_V2_BLIND_REVIEW_GUIDE.md)
- [KOL-v2 scoring contract](data/v2_1/association/kol_v2_audit/kol_v2_scoring_contract.json)
- [completed KOL-v2 review](eventx/release/v2_1/eventx_v2_1_kol_v2_blind_review_completed.jsonl)
- [failed KOL-v2 audit report](data/v2_1/association/kol_v2_audit/kol_v2_audit_report.json)
- [failed KOL-v2 result manifest](data/v2_1/association/kol_v2_audit/kol_v2_failed_audit_result_manifest.json)
- [cumulative 450-pair exclusion ledger](data/v2_1/association/kol_v2_audit/opened_pair_content_exclusions_through_kol_v2.jsonl)
- [active label-blind coverage snapshot](data/v2_1/planning/coverage_snapshot.md)
- [August 12 Lumid API/data audit](data/v2_1/planning/LUMID_API_AUDIT_20260812.md)
- [August 14 Lumid broken-parts report](data/v2_1/planning/LUMID_BROKEN_PARTS_20260814.md)
- `eventx/tasks/verify_v2_1_preregistration.py`
- `eventx/tasks/build_v2_coverage.py`
- `eventx/tasks/build_v2_selection_activity.py`
- `eventx/tasks/reconcile_v2_1_selection.py`
- `eventx/tasks/verify_v2_1_cohort.py`
- `eventx/tasks/fetch_v2_1_association_candidates.py`
- `eventx/tasks/build_v2_1_association_audit.py`
- `eventx/tasks/score_v2_1_association_audit.py`
- `eventx/tasks/freeze_v2_cohort.py`
- `eventx/tasks/collect_v2_1_prospective.py`
- `eventx/tasks/launch_v2_1_collector.py`
- `eventx/tasks/build_v2_1_taxonomy.py`
- `eventx/tasks/audit_v2_1_taxonomy.py`
- `eventx/tasks/freeze_v2_1_taxonomy.py`
- [prospective collector health](data/v2_1/prospective/health.json)

Verification at this update checked four sealed preregistration artifacts with no
failures and preserved the original v2 protocol hash and consumed v1 holdout state.
The activity builder and cohort freezer both correctly refused an attempted
pre-August-8 run at their revised temporal seals. Historical data reuse is explicitly
permitted for warmup, integrity, coverage, and descriptive robustness, but it cannot
replace the prospective windows or provide tuning inputs from exposed v1 labels.
The corrected mapping and independent taxonomy audit were completed without prices,
trades, labels, or performance inputs before development labels were built.

Taxonomy v7 assigns 1,501 politics, 402 crypto, 545 sports, 110 macro, and 862
other markets. Two reviewers independently labelled a frozen 250-row sample
stratified as 50 proposed rows per category; they agreed on 249 rows, and a third
blind reviewer adjudicated the sole disagreement. The accepted audit reports macro
precision/recall 0.9720/0.9739, with category precision of 1.00 politics, 0.98
crypto, 1.00 sports, 0.94 macro, and 0.94 other. The canonical mapping SHA-256 is
`8f53375466ed78dfe7ffd7809fc919c3a8251ca76b3e6c01bed4739f63d763ac`;
the accepted audit SHA-256 is
`2911311c7c942936567887f0dbc787a490b86b2ce1b56fd69ce53a279638341d`.
Superseded pre-audit attempts and the original description-boilerplate defect are
retained under `data/v2_1/taxonomy/` and were never scored or accepted.

The closed-window reconciliation verified collector cursors at or beyond the cutoff
for all 3,420 candidates and separately completed all 3,420 bounded history endpoints.
It retained 30,862 Polymarket and 5,171 Kalshi records across 1,690 and 9 markets,
respectively. Relative to the append-only prospective prefixes, bounded retrieval
added 76 Polymarket and 277 Kalshi records. Exact prospective-prefix hashes, canonical
trade hashes, retrieval provenance, and zero-trade counts are in the reconciliation
manifest. The activity builder retained 17,060 canonical-YES Polymarket rows and all
5,171 Kalshi rows, producing 1,167 market activity rows.

Fourteen markets passed the fixed minimums of 100 trades, 1,000 notional, three active
days, and 72-hour staleness, plus the scheduled-close/resolution rules. The other
candidate drops were 2,253 with no canonical selection activity, 1,152 below minimum
trades, and one below minimum notional. No cap was binding. The cohort verifier checked
all reconciliation outputs, input/output hashes, row counts, group counts, label seals,
and the preregistered maximum with zero failures. Selected-market SHA-256 is
`932b995f8a589065db2c841789121d6de7f22c6b7a22f1dc70b4b8bef07d553c`.

The initial association candidate pool was too sparse to support an audit, so no one
reviewed or scored it. A label-blind targeted search then retrieved 215 news and 991 KOL
rows with zero query errors. The rebuilt pool has 3,025 candidate pairs: news 135
matched/526 hard-unmatched and KOL 484 matched/1,880 hard-unmatched. Deterministic seed
83 produced exactly 300 unique blind rows, balanced 75 per source/prediction cell, with
zero prediction/key fields in the reviewer file. The completed independent review had
158 relevant and 142 not-relevant rows, with no uncertain labels. The v1 candidate
produced 133 true positives, 17 false positives, 25 false negatives, and 125 true
negatives: overall precision 0.8867 passed but recall 0.8418 failed. News passed both
gates (73 TP, 2 FP, 3 FN, 72 TN); KOL failed both (60 TP, 15 FP, 22 FN, 53 TN).
Audit report SHA-256 is
`d024d787a2ab5808943de93b87f3c0948830827fdeaebbcd203bea635f674d53`.
The rule was not frozen, and development and holdout labels remain uncreated and
uninspected.

The failed v1 audit is now sealed with its original 300 rows, hidden key, completed
review, report, matcher source, and hashes unchanged. A redundant exclusion ledger
records every opened pair by `(market_id, content_hash)` and `pair_id`. KOL-only error
analysis assigned all 37 KOL errors to counted modes and informed a separate v2 source
path; the accepted news matcher was not edited. The frozen KOL-v2 source hash is
`c8431cb32f859ad457f99128ac3e5b1455f7d032ebd588d7f721f4265e7ca5ef`
and lexical-spec hash is
`fef65090aeea2895cf8ea043f5fbd7f51298754679007af2f12c5aa6cb7ffdfa`.
Its 150-row opened development diagnostic is 80 TP, 2 FP, 2 FN, and 66 TN, but is
explicitly non-validating.

The fresh KOL-v2 audit drew from 2,172 unopened broad-retrieval candidates after
checking all 150 prior KOL pairs at the full market-document universe level and
excluding the 121 that still qualified under v2 retrieval. Seed 211 produced 75
predicted matches and 75 hard-unmatched candidates, with all 14 markets represented
and no opened-pair leakage. The blind packet SHA-256 is
`9059561d854975ca7298b916284555ba6c692d9a10a3625824a39f8af3e25b61`;
the hidden key SHA-256 is
`cedc0e87f8f09e9811d2410b919062375e3f8b99aace4c449b1feb640d6536ff`.
The completed independent review has SHA-256
`64581a298d64a71d23fa4de2d21bf2c955ea789aee822946346cdb5befd9442a`.
Scoring produced 62 TP, 12 FP, 36 FN, and 38 TN on 148 decided rows, plus two
uncertain rows: precision 0.8378, hard-candidate recall 0.6327, and F1 0.7209.
The candidate failed both fixed performance gates and the no-uncertain requirement.
The failed result and exact completed review are frozen, and all 150 pairs were added
to the cumulative 450-pair exclusion ledger. Development and holdout outcome labels
remain uncreated and uninspected.

The prospective collector was launched at `2026-08-01T11:55:25Z`. It records event
and retrieval timestamps, protocol/source provenance, global content keys, SQLite
checkpoints, and append-only JSONL. At the 11:59 UTC health snapshot it had written
7,339 open-event snapshots, 1,000 KOL cache rows, 200 news rows, 802 Kalshi trades,
and 243 Polymarket trades while advancing through the first 166 of 3,420 candidates.
The KOL cache was approximately 6.8 days stale and the newest accepted news timestamp
was approximately 9.4 hours old; these are provider-coverage limitations, not silently
treated as fresh data. The documented WebSocket and SSE transports were disabled
after bounded probes returned HTTP 400 or failed to complete a handshake. REST
polling and post-window bounded history pulls are the declared fallback.
At the `2026-08-02T07:36:43Z` health snapshot the collector remained label-blind,
reported zero source errors, and had written 14,888 Polymarket trades, 1,019 Kalshi
trades, 261 news rows, 1,853 KOL rows, and 22,015 event snapshots. The newest news,
Polymarket-trade, and Kalshi-trade events were approximately 3.4, 2.7, and 4.5 hours
old; the KOL cache remained approximately 7.8 days stale. These limitations remain
explicitly recorded for post-selection bounded reconciliation.

At the `2026-08-12T13:30:47Z` snapshot PID `94663` was still alive, but the source
health ledger showed a service-wide data-plane incident. It retained 3,780 news,
1,853 KOL, 6,224 Kalshi-trade, and 37,928 Polymarket-trade rows. Last usable event
times were `2026-08-09T23:56:38Z` news, `2026-07-25T12:34:58Z` KOL,
`2026-08-10T00:09:05Z` Kalshi, and `2026-08-10T01:26:51Z` Polymarket. Error counts
had reached 2,159 news, 2,159 KOL, 798 Kalshi, and 127,785 Polymarket. Authenticated
cross-domain probes confirmed that this was not a local crash or rate limit: Lumid's
usage telemetry showed 98.0238% 5xx responses and zero 429s. The incident and complete
endpoint/data inventory are frozen in the
[August 12 Lumid audit](data/v2_1/planning/LUMID_API_AUDIT_20260812.md). No retry is
treated as coverage, and no label pipeline may start until exact bounded recovery and
the source-sufficiency gate pass.

The `2026-08-14T07:48:50Z` recheck confirmed that the incident remained active.
Representative prediction-market discovery/detail/trade, news latest/search, KOL
recent/search, catalog-source, and freshness requests all returned HTTP 500. Lumid's
public telemetry had reached 169,002 5xx responses out of 171,717 total calls
(98.4189%), with zero 429s, while `/status` still displayed `ALL OK` and zero populated
freshness classifications. PID `94663` was alive, but usable event timestamps were
unchanged; error counts had risen to 2,724 news, 2,724 KOL, 987 Kalshi, and 160,127
Polymarket. The exact reproduction commands, affected surfaces, research impact,
requested provider actions, and all 14 frozen market IDs are in the
[August 14 broken-parts report](data/v2_1/planning/LUMID_BROKEN_PARTS_20260814.md).

On 2026-08-17 the same read-only controls showed route recovery. The live OpenAPI
remained at 169 paths/171 operations, `/freshness` reported populated green/amber/red/
gray counts, and authenticated required market-detail, trade, news, KOL-search and
catalog-source probes returned HTTP 200. Optional candles, orderbook, open-interest,
matched-pair, symbol-news/sentiment and KOL archive/history routes were also reachable,
although several example market/window requests were empty. PID `94663` was alive and
its 05:13 UTC health file was label-blind with no labels read. Latest recorded events
had advanced to news August 14 and Polymarket August 13, while KOL remained July 25 and
Kalshi August 10. The outage is therefore no longer an availability blocker, but its
coverage gaps and the collector's rotating 3,420-market scan still prevent the
data-sufficiency gate from passing without focused exact-window reconciliation.

## Historical bulk-fetch status

This archive is outside the frozen v1 pilot evidence and is available only for the
restricted historical-reuse roles inherited by v2.3.

- The former parent/subprocess chain has exited.
- Polymarket: 175,414 of 175,423 distinct roster IDs marked `done` (99.99%);
  7,251,246 checkpoint rows and 114,989 markets with nonzero rows.
- Nine Polymarket IDs remain absent after API errors; they are recorded as missing
  rather than implied complete.
- Kalshi: 2,535 of 2,535 roster IDs marked `done` (100%);
  21,155,401 checkpoint rows and 2,443 markets with nonzero rows.
- Raw trade files are approximately 3.0 GB Polymarket and 5.8 GB Kalshi.
- Total local `data/` directory is approximately 16 GB.
- The active label-blind snapshot is
  [data/v2_1/planning/coverage_snapshot.md](data/v2_1/planning/coverage_snapshot.md).

## Current decisions

1. Retain B0 market-only as the reference benchmark.
2. Do not promote B1 core news, B2 KOL, gated KOL, rich news, or B3 combined.
3. Treat the original v1 test result as descriptive prior exposure only.
4. Treat the replacement OOT result as final and consumed.
5. Do not use either test result for new tuning.
6. Archive the negative KOL/news findings rather than hiding them.
7. Treat the v1 frozen pilot/report as closed; publication-only edits must not change
   the frozen metrics, decisions, or holdout state.
8. Do not make category-stratified v1 claims from the defective frozen category tags.
9. Keep public redistribution at NO-GO until every blocker in
   [the readiness checklist](eventx/release/v1/PUBLIC_RELEASE_CHECKLIST.md) is resolved.
10. Preserve v2.1 and v2.2 as sealed superseded lineage. Treat v2.3 as the active
    prospective cycle; its protocol is locked and cannot be changed in response to
    later model performance.
11. Preserve the original v2 protocol as superseded evidence; do not edit or delete
    its sealed files.
12. Do not reuse the v1 holdout in v2.3, open development labels before the upstream
    and data-sufficiency freezes, or consume the October holdout more than once.
13. Use corrected v2.1 categories only after their metadata-only independent audit
    passes; never inherit the defective v1 category as ground truth.
14. Reuse historical records only under the inherited provenance policy; prospective
    records remain mandatory for selection, development, and holdout windows.
15. Treat `eventx-v2.1-taxonomy-v7` as the accepted corrected taxonomy. Do not tune
    or replace it after opening development labels; use its frozen canonical mapping
    and audit manifest for cohort selection.
16. Treat the verified 14-market v2.1 cohort as frozen. Its sparse category coverage is
    a result to disclose, not a reason to relax selection thresholds.
17. Do not create KOL development features from a matcher that failed its association
    gate. The accepted news-v1 path may support only the preregistered B1-versus-B0
    fallback after its source-specific freeze is verified.
18. Reject `eventx-v2.1-association-rule-v1-candidate`. Do not weaken the audit gates;
    use its opened rows only to develop a new version and validate that version on a
    fresh sample excluding all prior audit pairs and content hashes.
19. Reject `eventx-v2.1-kol-association-rule-v2-candidate`. Its fresh audit failed;
    preserve its frozen source, completed review, report, and 150 opened pairs. Any
    KOL-v3 validation must exclude all 450 cumulative opened pairs.
20. Treat `COMPLETE_RESEARCH_PLAN.md` as the umbrella coordination plan, not a
    replacement for any sealed protocol, manifest, cohort, rule, split, or temporal
    gate. If it conflicts with a frozen artifact, the frozen artifact controls.
21. Treat B3 as currently ineligible because the fresh KOL-v2 audit failed. Do not
    lower its gates after review. Only a genuinely new KOL-v3 rule with a fresh audit
    excluding all 450 opened pairs could reopen B3; given the October deadline, the
    accepted-news B1-versus-B0 fallback is the lower-risk route.
22. Treat the August 10–17 Lumid failures as a recorded data-plane incident. `/health`
    or `ALL OK` status is not evidence of usable data. Preserve retry/gap provenance
    and require exact-window Lumid REST recovery or a Lumid-provided endpoint-equivalent
    warehouse/bulk export before the label-blind data-sufficiency gate can pass.
23. Under the August 17 umbrella-plan revision, every external observational input for
    the active experiment must map to a valid route in Lumid's saved OpenAPI contract.
    The current HTTP 200 recovery proves route availability, not historical
    completeness; do not substitute direct venue or other-vendor data without a new
    label-blind datasource decision/protocol.
24. Preserve the dates and measurement corrections sealed by
    `eventx-v2.2-october-pilot-fixes-20260817`. Development ends at
    `2026-09-28T00:00:00Z`; September 28–30 is the fixed reconciliation, evaluation,
    and freeze buffer; the holdout remains October 1–22 half-open UTC.
25. Use uniform canonical-YES last trade as the primary price and record price age.
    Keep midpoint and candles separate; run the fixed ≤30/≤60-minute price-age and
    trade-arrival robustness diagnostics without using them to rescue a failed gate.
26. Interpret the unchanged threshold formula as a heuristic 30-minute anchor in
    one-minute sigma units. It is not four 30-minute sigmas and cannot be revised after
    labels.
27. Do not run directional P&L for the unsigned absolute-jump target. E15 is limited to
    alert rate, lead time, calibration, and a development-frozen decision-curve output.
28. Freeze the August 8–17 Lumid rehearsal as `incomplete`. Do not call 14/14 trade
    integrity a complete data pass while the `/news/latest` 200-row cap remains
    unresolved; preserve the audit files and hash manifest unchanged.
29. Treat `eventx-v2.3-news-availability-clarifications-20260817` as controlling. It
    preserves v2.2's dates, cohort, target, prices, features, learner, and holdout while
    freezing the remaining news-availability and decision-rule ambiguities.
30. Poll the broad Lumid news feed every 60 seconds. Any response with at least 200
    rows is potentially censored; do not advance its checkpoint. A successful-request
    gap over 300 seconds triggers reconciliation. Any unresolved censored interval
    makes B1 incomplete rather than a zero-news observation. Apply the same contract
    during development and holdout.
31. Set primary news feature availability to
    `max(published_at, first_seen_at)`, retaining both timestamps. This prevents a
    historically backfilled article from becoming available before Lumid first
    exposed it to the prospective pipeline.
32. Use the explicit v2.3 H1–H5 B1-versus-B0 hypotheses. An undefined required fold
    metric does not count as positive; an undefined required aggregate or venue metric
    fails that promotion condition. Descriptive reporting may continue, but undefined
    confirmatory evidence cannot promote B1.
33. Complete and freeze the label-blind data gate first, then the synthetic 14-market
    cluster-power simulation, and only then generate labels. Position the October
    report as a prospective incremental-news protocol-validation pilot, not a KOL
    information result.
34. PID `94663` is a preserved legacy label-blind collector, not a v2.3-compliant news
    collector. Do not silently restart, replace, or present it as satisfying v2.3.
    Record an explicit migration or parallel-launch decision before changing the live
    collection topology.
35. Do not launch the frozen v2.3 news implementation as the controlling collector
    without a new label-blind version that separates stable article identity from
    content-version hashing and verifies same-article revision/timestamp-conflict
    behavior. Preserve the frozen v2.3 files and their hashes as lineage.

## Next steps

### Current v1

1. Resolve the public-release blockers: explicit code/data licenses, upstream-rights
   review, privacy/dual-use review, maintainer, archive, DOI, and citation metadata.
2. Version corrected category metadata without modifying the frozen cohort file.
3. Build an ID/feature-only public export, run a complete secret scan, and reproduce
   it in a clean environment without credentials or private raw corpora.
4. Re-run `python -m eventx.release.verify_v1_release` after any release-document edit
   and update the document hashes in the release manifest.
5. Monitor the separate bulk-fetch chain if that collection remains wanted; do not
   mix its changing files into the frozen v1 release.
6. Do not run another model-selection or holdout experiment under v1.

### Active v2.3

1. Keep PID `94663` and its append-only state preserved. It remains useful legacy
   evidence collection but is not v2.3 news-contract compliant. Inspect
   `data/v2_1/prospective/health.json` at least daily, retain the August error/gap
   history, and do not inspect the reserved holdout.
2. Preserve the completed reconciliation, activity, and 14-market cohort manifests;
   do not rerun selection or relax sparse strata after labels.
3. Preserve the accepted taxonomy-v7 mapping and audit. Do not revise it using
   later labels, trades, model performance, or holdout information.
4. Preserve the failed KOL-v1 and KOL-v2 audits and cumulative 450-pair exclusion
   ledger. Do not use either failed rule for development features.
5. Treat B3/KOL as ineligible and run only the active B1-versus-B0 confirmatory branch.
   Never weaken the fixed association thresholds or put KOL-v3 on this cycle's critical
   path.
6. Before replacing or supplementing PID `94663`, create and verify a new label-blind
   collector version that separates stable article identity from content-version hash
   and tests article/timestamp revisions. Then record an explicit collector-migration
   decision. The frozen v2.3 implementation passed its original offline contract
   fixtures but has not been launched; do not change the live topology silently.
7. Resolve the `/news/latest` 200-row truncation blocker through a documented Lumid
   cursor/time partition or a Lumid-provided endpoint-equivalent export with
   schema/key/lineage reconciliation. The current OpenAPI has no cursor or upper bound,
   and category partitioning alone is insufficient at the observed volume.
8. Continue focused exact bounded Lumid recovery for the frozen 14-market trade windows
   and 21 accepted frozen news queries. Preserve the August 8–17 incomplete audit and
   its hash manifest; any new attempt requires a new audit ID/output path.
9. After recovery, reconcile every development endpoint over `[2026-08-08,
   2026-09-28)`, quantify gaps/errors/duplicates/freshness, verify canonical YES and
   source timestamps, and freeze the accepted news source path. The gate must enforce
   the 60-second/200-row/300-second contract and `max(published_at, first_seen_at)`
   availability rule.
10. After the data gate passes, run and freeze the label-blind synthetic 14-market
    cluster-power simulation. Do not create labels before both upstream steps finish.
11. Build the uniform last-trade development labels/features and run the preregistered
   five-fold B0/B1 comparison. Run fixed price-age and trade-arrival robustness only as
   descriptive diagnostics.
12. Apply the explicit v2.3 H1–H5 and undefined-metric rules. Freeze at most one
   promoted candidate—or B0 if none promotes—before October 1. If
   required inputs cannot be frozen in time, report the cycle incomplete rather than
   changing the schedule.
13. Keep the October 1–21 holdout sealed; after it closes, reconcile it and evaluate
    exactly once, write the consumption receipt, and prohibit reruns.
14. From October 22–31, finish the report, datasheet, evidence manifests,
    reproducibility package, and missingness/deviation disclosures.

## Archive status

This file is no longer the mandatory startup handoff and receives no new routine
updates after 21 August 2026. Use:

- [`CURRENT_STATE.md`](CURRENT_STATE.md) for compact current context;
- [`docs/progress/README.md`](docs/progress/README.md) for history routing; and
- `docs/progress/YYYY-MM.md` for detailed subsequent updates.

The historical results above remain part of the audit trail. Do not erase failed
experiments or reinterpret consumed holdouts. Never rerun
`python -m eventx.tasks.run_frozen_b0_oot_final`.
