# EventX current state

> Canonical startup handoff. Read completely before EventX work. Frozen artifacts
> control any conflict. Detailed prior handoff is preserved in
> `docs/progress/CURRENT_STATE_ARCHIVE_20261018.md`; append routine history to
> `docs/progress/2026-10.md`, not the legacy PROGRESS.md.

Last updated: **2026-10-23 Asia/Singapore** (local workflow active; execution accounting diagnosed)

## Active objective: verify sources before cohort expansion or model work

Execute the authorized staged study: separate direct-source rehearsal, then prospective
cohort/target eligibility; preserve both original collectors and raw condition_120k.
**No further model development until one complete prospective observation passes
source/history/freshness/forward/terminal/evidence gates. No admissions yet.**

### Existing source and37-contract pilots remain unchanged

- Original releases: `EVENTX_ORIGINAL_RELEASE_CAPTURE_20261018.md`; locked code/
  schedule `eventx/release/v7/original_source_capture_20261018_v02/`; live
  `data/v7/official_source_capture_20261018/live/`. LaunchAgent
  `com.eventx.original-releases.20261018.v02`, PID600, started03:49UTC18October.
- Fed/BEA feeds60s, scheduled bursts15s;14 planned targets/11dates through23Dec.
  BLS403; official DOL original PDFs work. Future paths remain hypotheses.
  Durable local availability differs from claimed publication/schedule clocks;
  captures are not backdated or silently substituted into frozen Lumid studies.
- Source checkpoint22Oct11:00UTC:79versions, no new admitted predictive events.
  Source-only pilot stops2027-01-01 00:00UTC.
- Market pilot: `EVENTX_MARKET_CAPTURE_AND_COHORT_20261018_REV2.md`; lock
  `eventx/release/v7/market_capture_20261018/`; live
  `data/v7/market_cohort_capture_20261018/live/`. Service
  `com.eventx.market-capture.20261018`, PID23793, network began10:10:17UTC.
  37 contracts:21US CPI/9unemployment/7GDP;141 metadata candidates excluded.
  All470 V4 IDs excluded; Fed decision families quarantined. Shared shocks remain.
- Original market pilot:poll120s/6h warmup/30m overlap;stop12Nov00:00UTC.
  Historical18Oct snapshot:26YES/five markets,zeroactivity passes;not current coverage.
- Same-release contracts settle on their news: end_date cannot admit post-release30m
  targets. Calendar-only:Oct29 GDP/PCE30,Nov6 employment21,Nov10 CPI0; simultaneous
  GDP/PCE are not independent draws.
- launchd restart/login+caffeinate require local power/network/awake machine; live/STOP
  stops cleanly. Frozen V1/V2 failures preserved; detailed schedules in reports.

### 22October continuation: local autonomous source workflow

User directed local research without SSH and continuation until human review is needed.
The earlier remote access blocker is superseded; failed host evidence/package remain
in `EVENTX_AUTONOMOUS_RESEARCH_PROGRESS_20261022.md` and its frozen evidence directory.
- Local workflow freeze: `eventx/release/v7/source_workflow_20261022/` (41 hashes
  verified before launch); status `data/v7/source_workflow_20261022/status.json`.
  It waits for original completed audit, then runs the separately frozen V03 source
  rehearsal for24h, automatically audits it and stops before event activation/scoring.
  Administrative deadline25Oct12:00UTC. Local power/network/awake machine required.
<!-- V7_SOURCE_WORKFLOW_STATUS_START -->
- Autonomous source phase: **waiting_for_original_rehearsal**, at2026-10-22T15:57:00.729749+00:00.
- Live status/evidence: `data/v7/source_workflow_20261022/status.json`.
- Event activation disabled; model frozen; zero admissions.
<!-- V7_SOURCE_WORKFLOW_STATUS_END -->
- Original22-market service PID39643 still runs unchanged; started22Oct05:58UTC,
  stop23Oct05:58UTC with automatic final audit. PID600/23793/39643 verified22Oct12:32UTC.
  Original rehearsal `data/v7/direct_source_pilot_20261022/live/` incomplete.
- Same sample14new annualmacro+3legacy+5controls;all470V4IDs excluded. Six episodes
  reserved29Oct–4Dec,84metadata link plans;single-assistant assessment,not human gold.
  Event activation disabled;first warmup29Oct06:30UTC conditional on readiness.
- API migration notice states legacy Data API retires24Oct. V03 replacement uses
  condition filter,cursor envelope,local window filtering (market bounds ignored),
  and resolution capture. Freeze `eventx/release/v7/direct_source_pilot_20261022_v03/`.
  Five-minute run22Oct11:12–11:17UTC:454HTTP200/10HTTP404/42queued cancellations;
  zero429/stream disconnects;3,271journal records/2,840payloads;23macro windows,0passes.
  All22 trade scopes/14candidate mappings verified;33implementation+20production locks.
  Short concurrent run does not establish improved reliability or exchange completeness.
- Paired maker/taker probe44HTTP200/22markets;counts differ in8markets. V03 identity
  check52provider rows:42economic matches/16exact transaction-hash IDs/42prefix matches.
  Unique-fill accounting unresolved;do not treat all maker rows as independent trades.
- **Feature semantics correction:** historical notional=token size,not price×size;
  windows(t-window,t]. `EVENTX_FEATURE_SEMANTICS_20261022.md`; four frozen code hashes
  verified. Re-audit602macro windows:0size passes,0cash passes,0changed decisions.
  V01/V02 cash diagnostics and V03 inclusive boundaries preserved,not exact feature
  eligibility. Remote version uses explicit quantity/cash and open-left boundaries.
- Prior maximum trade receipt gap2482.995746s overlaps macOS clamshell sleep17:06SGT
  and maintenance sleep17:09:23–17:46:09(2206s). Host suspension contributes;other
  network/HTTP failures remain unexplained. Targeted evidence preserved in new report.

### Local source diagnosis,23October

- `EVENTX_LOCAL_RESEARCH_CONTINUATION_20261023.md`; workflow PID74338 verified.
  Original stop23Oct13:58SGT, then separate24hV03 capture/audit; no event activation.
- Price precision explains10previously unmatched rows (maximum2.69823e-11);52/52
  provider rows have rounded economic+transaction-prefix matches,4remain ambiguous.
- Extra direct rows334:333controls/1candidate. Same-window later inclusive snapshots
  unchanged; provider52rows mix29taker keys/23maker-only keys. Controls63taker rows
  absent from provider. A taker-only switch cannot reproduce historical accounting.
- Provider taker versus venue proxy_wallet agrees16/52only; no verified join rule.
  Nine YES seconds have conflicting prices,all controls; sequence remains unresolved.
- Review package `data/v7/local_continuation_20261023/REVIEW_PACKAGE.md` prepared,
  unsent. External semantic clarification required before canonical mapping/admission.
  Source diagnostics do not change frozen features; zero new predictive results.

### Prior source diagnosis and remaining gates

`EVENTX_SOURCE_VERIFICATION_20261018_REV2.md`; canonical evidence
`data/v7/source_verification_20261018/analysis_v01/`. Both sparse macro executions
and missing source coverage:18Oct control183venue/6Lumid prints, warehouse also6.
Empty archive quotes coexist with direct books; charts/WSupdates are not trades.
Receipt gaps market13,487.463046s/source5,274.092976s; causes unknown. Fresh current
heartbeats do not certify continuity.22Oct source79versions, no new admitted release.
Required `analysis_v01/observation_gate_contract.json`: source coverage, actual terminal
clocks, fresh forward policy, execution accounting, episode independence/power and unseen confirmation freeze.
Provider request `EVENTX_SOURCE_VERIFICATION_PROVIDER_REQUEST_20261018.md` remains unsent.

## Selected market model: retain raw condition_120k

Canonical: `data/v5/market_condition_tuning_20261012/`, selected_model.joblib SHA256
`d5d5a8c12fd999674f687c712e14f3a4406e7ab5ec34774baf1828f644f73a3c`.
Histogram gradient booster,13base+9trailing features;600iterations,lr0.05,7leaves,
depth3,minleaf100,L2=10,120k fit rows. Task: probability of large **absolute** YES
log-odds movement over30m;not direction/exact magnitude/resolution. Every5m grid.

- Opened fold5:112,616 matched rows, LL0.3429489298145635,
  Brier0.10905976503729453, AP0.3462485264100695.
- LL reduction0.5415604842619057% vs previous HGB;1.7012452641439602% vs earlier
  tree. Older9.68% logistic comparison is a separate364,903-row panel.
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
- V2.3 unchanged14-market pilot; verify source/consumption receipts before evaluation.
  No v2 collection/model selection without explicit cycle authorization; current work
  authorizes V7 sources only.
- KOL deferred after association failures. EventXBenchT2 validation/test labels sealed;
  do not open/bulk-download silver data without a new gate.
- PORTEND is separate portfolio work; not part of the market-news research task.
- Paper A: `MARKET_NEWS_PAPER_A_DRAFT_20261010_REV2.md`; human scientific review,
  author/venue details/release rights remain. Slides:`eventx/release/presentation_20261012/rev6/`,
  through12October only; later research not automatically incorporated.

## Next actions

1. Monitor the new collector label-blind: process, status freshness, receipt hashes,
   first versions, failed endpoints, reschedules and actual arrival delays.
2. Audit first new release captures. Count distinct event dates/episodes; do not count
   old baseline imports as new events or schedule targets as achieved captures.
3. Resolve measured source gaps; version a longer-lived cohort across more releases.
   Model stays frozen until one complete gated observation.
4. Local source workflow reviews the original final24h audit after23Oct05:58UTC,
   then runs/audits V03 for24h. Resolve trade identity/feature compatibility using
   local receipts; six future episodes remain reserved, activation gated.
5. Keep V4 receipt/checkpoint checks separate and follow its frozen close sequence.

## Authoritative references

- V4: `eventx/release/v4/protocol.json`, `holdout_implementation_manifest.json`
  and `model_freeze_manifest.json` in that directory.
- V3.1 protocol/deviation: `eventx/release/v3_1_historical_primary/`;
  result:`data/v3_1_historical/primary/holdout/evaluation_result.json`.
- V5:`eventx/release/v5/PROTOCOL_V1_1.md`; `eventx/release/v5/REVISION_IMPLEMENTATION_20260910.md`.
- Capture locks: original-source V02 and market pilot `implementation_manifest.json`
  in their above-linked `eventx/release/v7/` directories.
- Prior handoff:`docs/progress/CURRENT_STATE_ARCHIVE_20261018.md`; history:`docs/progress/2026-10.md`; legacy ends21August.
