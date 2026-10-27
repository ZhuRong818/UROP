# EventX current state

> Canonical startup handoff. Read completely before EventX work. Frozen artifacts
> control any conflict. Detailed prior handoff is preserved in
> `docs/progress/CURRENT_STATE_ARCHIVE_20261018.md`; append routine history to
> `docs/progress/2026-10.md`, not the legacy PROGRESS.md.

Last updated: **2026-10-18 Asia/Singapore**

## Active objective: original-source and market capture with fixed model

User authorized timely original releases across additional event dates, keeping
`condition_120k` fixed. **V7 source-feasibility collector is running**, started
18 October 03:49:00.908014 UTC. User LaunchAgent
`com.eventx.original-releases.20261018.v02`, collector PID600 verified via ps.
Report: `EVENTX_ORIGINAL_RELEASE_CAPTURE_20261018.md`.

- Current contract/code lock: `eventx/release/v7/original_source_capture_20261018_v02/`.
- Live status/journal/objects/text: `data/v7/official_source_capture_20261018/live/`.
- Latest frozen health snapshot: `data/v7/official_source_capture_20261018/health/20261018T035026Z/report.json`.
- At 03:50:26 UTC:338 journal records/83 unique payload hashes verified;
  79 document versions, all historical baseline imports; zero prospective candidates.
  All three Fed/BEA feeds polled twice, latest304; implementation/model hashes match.
- Fed monetary-policy and speeches/testimony RSS + BEA RSS poll60s; official
  dated release targets15s for first15m,60s through1h,hourly through24h.
  Feed burst15s from2m before to15m after schedule; failures back off/Retry-After.
- BLS pages403; official DOL-hosted original CPI/PPI/employment PDFs200.
  Future DOL paths are naming hypotheses, not guaranteed published endpoints.
  One old2021 BEA item redirects outside allowlist; refused and logged unknown.
- Fourteen scheduled release targets on11 dates, Oct28–Dec23, plus unscheduled
  items in declared feeds. Stops2027-01-01 00:00UTC. Dates can change; inspect
  retained calendars. Scheduled times are not actual first-public clocks.
- This is an explicit new official-source branch, not substitution into Lumid or
  any frozen dataset. First local observation/versions preserved; no backdating,
  provider-completeness, independent-event or predictive-gain claim.
- No market endpoint, V4 sealed payload, labels, model fits, calibration or scoring.
  Source pilot admits no forecasting confirmation cohort. New market cohort/time/
  family separation and price freshness must be defined separately before scoring.
- LaunchAgent restarts after failures/at login. Caffeinate inhibits idle sleep;
  local power/network/awake machine required. Create live/STOP to stop cleanly.
- V1 prepared but never launched; V2 fixes pending-discovery restart recovery and
  bounded official redirects. Both preserved. No software tests added/run.

### New market-source pilot:37 contracts, no predictive admissions

User authorized continuation to market-cohort/capture work. Current report:
`EVENTX_MARKET_CAPTURE_AND_COHORT_20261018_REV2.md`. Locked cohort/spec/code:
`eventx/release/v7/market_capture_20261018/`; live:
`data/v7/market_cohort_capture_20261018/live/`. Service
`com.eventx.market-capture.20261018`, PID23793, network capture began10:10:17UTC.
- Metadata-only discovery178 records;37 retained:21 October US CPI,9 October
  unemployment,7 Q3 GDP advance;141 excluded. All470 V4 exact IDs excluded;
  Fed decision families quarantined. Different predicates still share macro shocks.
- Snapshot `data/v7/market_cohort_capture_20261018/health/20261018T101247Z/report.json`:
  233 journal records/7 unique payloads/10 implementation locks verified; latest
  all37 trades/quotes HTTP200,59 returned trades/26 YES trades,zero quote snapshots.
  One earlier quote500 recovered;74 sandbox DNS failures retained separately.
- Same-clock `freshness/20261018T101247Z/report.json` under that pilot:26 unique
  valid YES trades/five markets;zero pass observed activity screen; minimum trade
  age28.597245100000002m. No eligible forecasting sample or predictive gain claimed.
- Each contract settles on its own release: do not use later metadata end_date
  to admit a post-release30m target. Calendar-only later-resolving candidates:
  Oct29 GDP/PCE30, Nov6 employment21, Nov10 CPI0. GDP/PCE simultaneous.
- Model unchanged; no labels/scoring/fits/protected payloads. Poll target120s,
  six-hour warmup/30m overlap; slow endpoints extend cycles. Stops12Nov00:00UTC.
  Source completeness/freshness unresolved; Kalshi narrow metadata queries empty.
  Provider diagnostic drafted, NOT sent. Original-source PID600 remains separate.

## Selected market model: retain raw condition_120k

Canonical: `data/v5/market_condition_tuning_20261012/`, selected_model.joblib SHA256
`d5d5a8c12fd999674f687c712e14f3a4406e7ab5ec34774baf1828f644f73a3c`.
Standard histogram gradient booster,13 base +9 trailing market-state features;
600 iterations, learning rate0.05,7 leaves,depth3,minleaf100,L2=10,120k fit rows.
Task: probability of a large **absolute** canonical-YES log-odds movement over30m;
not direction, exact magnitude or final resolution. Every5m decision grid.

- Opened fold5:112,616 matched rows, LL0.3429489298145635,
  Brier0.10905976503729453, AP0.3462485264100695.
- LL reduction0.5415604842619057% versus previous HGB;1.7012452641439602%
  versus earlier tree. Older9.68% logistic comparison is a separate364,903-row panel.
- Five condition-group ablations worsen both folds; retain full features.
  Fold4-selected Platt calibration worsens fold5 LL to0.3434057612588951;
  do not promote it or tune from these already-open results.
- Evidence: `MARKET_MODEL_TUNING_20261012.md`, `MARKET_MODEL_NEXT_STEP_20261014.md`;
  `data/v5/market_ablation_calibration_20261014/`. No independent/current-regime
  confirmation. The current capture task leaves all these artifacts unchanged.

## Latest news evidence and bottlenecks

Report `EVENTX_VERIFIED_EVENT_LEDGER_AND_COVERAGE_20261015.md`; current package
`data/v7/verified_event_ledger_20261015_v02/`. Two separate assistant reviewers
agreed on32 material-context links/12 articles. Their78-pair relevance agreement
64/78;14 disagreements/seven articles remain unresolved. Not independent human gold;
zero exact-predicate links, original reviewer novelty unknown/direction null.

- Agreed links:95 unique opened fresh rows (27movements/68nonmovements),four
  contracts/five dates. Originalfold5 has zero. Excluding ambiguous Kalshi H0:
  48rows(11/37); also excluding flagged PPI summary:44rows(11/33).
- Seven referenced identities, six official documents/programme, three exact release
  clocks. Several mappings contextual, four originals unavailable, no historical
  text authentication. Four conservative co-isolation components are NOT four
  independent draws. All contracts concern the same July FOMC decision.
- Earliest component-contract arrivals:14rows(6/8),10(4/6) excludingH0.
  Publication lag minimum80.86875741666667/median180.34452538333335minutes;
  zero within60m. Seven CPI/PPI-linked articles lag latest release >=120.25209075m.
- PPI cached summary incorrectly scopes decline to annual5.5%; original/BLS +5.5%.
  Preserve cached text. H0 official metadata GET404; missing rules unresolved.
- Hypothetical timely CPI/PPI windows:17(5/12) and11(5/6) fresh rows across five
  inventory contracts, not historical news-feature access or predictive gains.
- V01 arrival counts correct but four-contract source diagnostic mislabeledALL_FIVE;
  V02 includes fifth contract, CPI16/4→17/5. Both versions retained.
- No effective sample size, adopted inference or empirical power established.
  Source capture alone does not close relevance/novelty or independence gaps.

Earlier fixed M/E/T/C development comparison on5,388 exposed fold5 rows:
M LL0.24272243956157083; exposure E0.24232437076003854(best);
T timing0.24239546292985711; unsigned context C0.24238825908649334.
C versus T gain0.000007203843363788398nats is tiny, below E; context on17rows,
all negative. No demonstrated incremental news gain. `MARKET_NEWS_CONTINUATION_20261014.md`.
Strict repaired signed extractor v0.3.3:11 associations/two articles,zero eligible
OOF coverage. Relaxed unsigned context:144 articles/1,056 rows; fold5 six/17.
147,377 deduplicated historical documents/479,179 legacy associations processed.

## Frozen evaluations and integrity

- **Consumed OOT** `eventx-oot-7c4fd487edb3928b9253`: never rerun
  `eventx.tasks.run_frozen_b0_oot_final`; never tune from it.
- **Consumed V3.1 holdout** `[2026-07-22,2026-08-08)`: never rerun
  `eventx.tasks.evaluate_v3_1_historical_holdout` or evaluate B1 there.
  B0-only211,718rows/300markets,AP0.171628/Brier0.107107; documented prevalence
  disclosure deviation. Historical holdout did not test news.
- Original v1 test was exposed by a noncanonical B0; do not call it untouched.
- **V4 frozen**:470 Polymarket contracts; confirmation `[2026-09-06,2026-10-30)`.
  B3 versus B0 primary, minimum0.001nats paired-bootstrap/Brier/venue guards.
  It does not independently confirm condition_120k. Frozen files unchanged.
- Do not read V4 future prices/outcomes, create examples/labels/predictions or report
  prevalence/metrics before close and consumption receipt. No early evaluation.
- Last V4 label-blind operational check was **14 October08:01:46UTC**, not a current
  process claim:425receiptsets,45news/38tradedays through13October,zero backlog,
  all15 frozen hashes matched. `data/v4/health_checks/20261014T080146Z/report.json`.
  This did not certify source completeness or sealed payload integrity.
- After close, exactly once: audit_v4_confirmatory_collection →
  consume_v4_confirmatory_holdout → prepare_v4_confirmatory_inputs →
  build_v4_confirmatory_examples → evaluate_v4_confirmatory. Stop at failed gate.
- Never modify hash-locked files in place; create a new version/manifest.
  Preserve all failed experiments, original reviews and unrelated dirty changes.
- Keep secrets in .env; never print credentials. Missing/failed feeds remain unknown,
  not zero news. No silent non-Lumid substitution into existing studies.

## Other research branches / remaining gates

- V5/V7 historical development is outcome-open; cannot confirm redesigned models.
  Learned representations need forward-training-only fitting in a new cycle.
  Existing dependence/coverage simulations failed; no inference candidate adopted.
- V5 PROTOCOL_V1_1 is a working design, not a completed research freeze.
  Historical feed reconciliation, metadata/version/status and family boundaries
  remain unresolved. Lumid has no PIT ingestion before17May; older rows are backfills.
- V6 strict audit failed39/40 conservative relevance errors; cycle closed, no rerun/
  resample. Relaxed reviewed positives reuse five articles; no certified predictive
  admissions. Unsent nine-article/15-contract source request remains in
  `portfolio/LUMID_EVENTX_V6_SINGLE_FILE_REQUEST_20261002.md`.
- V2.3 remains a separate unchanged14-market pilot. Verify its source and consumption
  receipts before more evaluation; do not start v2 collection/model selection without
  explicit authorization for that cycle. This task authorizes V7 sources only.
- KOL remains deferred after failed association audits. EventXBenchT2 validation/test
  labels sealed; do not open them or bulk-download silver data without a new gate.
- PORTEND is separate portfolio work; not part of the market-news research task.
- Paper A revision2: `MARKET_NEWS_PAPER_A_DRAFT_20261010_REV2.md`; independent human
  scientific review, author/venue details and release rights remain before submission.
- Latest presentation: `eventx/release/presentation_20261012/rev6/`; results/notes
  through12October, not automatically updated with14–18October research.

## Next actions

1. Monitor the new collector label-blind: process, status freshness, receipt hashes,
   first versions, failed endpoints, reschedules and actual arrival delays.
2. Audit first new release captures. Count distinct event dates/episodes; do not count
   old baseline imports as new events or schedule targets as achieved captures.
3. Diagnose pilot trade/quote coverage, then version a longer-lived market cohort
   across more release dates; retain V4 separation and the current raw model.
4. Before any later confirmation, freeze source/cohort, M/E/T/R/S definitions,
   episode isolation, inference/power, unseen evaluation window and consumption rule.
   Exact evidence direction is optional for the absolute-movement development target.
5. Keep V4 receipt/checkpoint checks separate and follow its frozen close sequence.

## Authoritative references

- V4 protocol: `eventx/release/v4/protocol.json`; implementation:
  `eventx/release/v4/holdout_implementation_manifest.json`; model freeze:
  `eventx/release/v4/model_freeze_manifest.json`.
- V3.1: `eventx/release/v3_1_historical_primary/protocol.json`,
  `data/v3_1_historical/primary/holdout/evaluation_result.json`,
  `eventx/release/v3_1_historical_primary/HOLDOUT_PROTOCOL_DEVIATION.md`.
- V5: `eventx/release/v5/PROTOCOL_V1_1.md` and
  `eventx/release/v5/REVISION_IMPLEMENTATION_20260910.md`.
- Current capture lock: `eventx/release/v7/original_source_capture_20261018_v02/implementation_manifest.json`.
- Prior full handoff: `docs/progress/CURRENT_STATE_ARCHIVE_20261018.md`.
- Detailed current history: `docs/progress/2026-10.md`; legacy PROGRESS.md ends21August.
