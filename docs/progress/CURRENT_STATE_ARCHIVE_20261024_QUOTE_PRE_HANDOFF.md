# EventX current state

> Canonical startup handoff. Frozen artifacts govern conflicts. Detailed prior state:
> `docs/progress/CURRENT_STATE_ARCHIVE_20261023_ELIGIBILITY.md`.
> Append history to `docs/progress/2026-10.md`,not legacy PROGRESS.md.

Last updated: **2026-10-24 Asia/Singapore** (source rehearsals complete; new two-market pilot running; zero forecasts)

## Active objective and locked decisions

User authorized local autonomous research until human review is needed;SSH unavailable
and no longer a dependency. Complete source rehearsals,resolve accounting/coverage,
then assess prospective observations. **Keep raw condition_120k fixed until one complete
observation passes source/history/freshness/forward/terminal/evidence gates. Zero admissions.**
No outcome-driven cohort replacement,no early protected evaluations,no provider messages sent.

## Latest completed research

Canonical report: `EVENTX_FORECAST_READINESS_PROGRESS_20261024.md`.
Evidence: `data/v7/forecast_progress_20261024/`;prior detail archived in
`docs/progress/CURRENT_STATE_ARCHIVE_20261024_FORECAST.md`.

- Original/revised24h source runs completed; controller finished24Oct06:06UTC.
  Original588233records/483894payloads; revised380142/317984. Revised0HTTP429,
  1441book404s;3182resolution200s. Different periods, not controlled improvement.
  Macro activity0/3159original and0/2016revised overlapping diagnostic windows.
- Revised max market trade-receipt gap26627.861848s(443.80min),23Oct10:01:38–17:25:26UTC;
  repeated sleep/dark-wake states overlap; full wake17:25UTC. Host sleep contributes,
  not an explanation for every provider omission. `data/v7/completed_rehearsal_diagnosis_20261024/`.
- New feasibility timing policy frozen23Oct before expansion: inputs available by t,
  emission by t+30s; endpoint trade<=t+30m,age<=5m,receipt<=t+32m;120s operational
  receipt/status gap limit. New design choices,not optimized/validated thresholds.
  `eventx/release/v7/forecast_path_20261023/`;scoring disabled,source convention unresolved.
- Price-blind expansion204metadata records:14existing,89own-release-terminal,99other,
  2new longer-lived US candidates. Sandbox failures and HTTP400 preserved; V02query200.
  470protected IDs excluded;no liquidity ranking. `eventx/release/v7/expansion_source_pilot_20261024/`.
- New negative-annual-GDP candidate needs exact full-year/annualized BEA binding;
  recession candidate has dual GDP/NBER rule and early-terminal risk. Not human gold.
- Full22feature reconstruction:11/114representations across2/22markets;7paired
  comparisons,3withdifferences>1e-6. Source-sensitive,not production parity; no scores.
  `data/v7/full_feature_compatibility_20261024/`.
- Prior exact as-of diagnostic23Oct02:35UTC:0/14freshYES,0/2696activitypasses,
  13unseededpaths,onezero-volatilitypath. `EVENTX_INPUT_COMPATIBILITY_AND_ELIGIBILITY_20261023.md`.
- Provider52records map52orderfills/29transactions,mixedmaker/taker schema;
  16/63omissions recovered late;remaining47chainmatched. No general coverage fix.
  Narrowed provider request remains UNSENT in `data/v7/eligibility_report_20261023/`.

## Local source jobs and next gates

Processes checked24Oct at2026-10-24T07:47:28.199602+00:00;snapshots in current evidence package.
- Original release collectorPID600 and37-market collectorPID23793 remain running.
  Original-source checkpoint79documentversions;0new release admissions.BLS403 persists.
  Services/data paths retained in archive;original20filelocks verified unchanged.
- Original22-market pilot and revisedV03 pilot completed; workflowPID74338 exited.
  `data/v7/source_workflow_20261022/status.json`:finished_source_review.
<!-- V7_SOURCE_WORKFLOW_STATUS_START -->
- Autonomous source phase: **finished_source_review**, at2026-10-24T06:06:48.061042+00:00.
- Live status/evidence: `data/v7/source_workflow_20261022/status.json`.
- Event activation disabled; model frozen; zero admissions.
<!-- V7_SOURCE_WORKFLOW_STATUS_END -->
- NEW six-hour two-market collectorPID31131,service`com.eventx.expansion-source-pilot.20261024`.
  `data/v7/expansion_source_pilot_20261024/live/`;stop24Oct13:27:27UTC(21:27SGT).
  Metadata/resolution everycycle;cycle-gaplogging;automatic final source audit.
  First57.92s:14HTTP200/18payloads,both books two-sided/mappingrules match.
  Recession12venue/12provider trade records,zeroYES;negativeGDPzero.0activitypasses.
  Initial histories retrospective;not prospective warmup. No forecast/activation code.
- KeepMacpowered/awake/networked/lid-open;recorded sleep makes this necessary.
  Receipt gaps>120s invalidate affectedwindows;latebackfill never restores availability.
- Six original episodes29Oct–4Dec retained;12new metadata-linkplans are provisional.
  First29Octwarmup06:30UTC remains conditional. No event service activated.
- Remaining:source/accounting compatibility,valid240m history,exactpredicate/terminal
  evidence,timelynewrelease,onecompleteprospectiveobservation;then separate activation
  oflater shadowgrids and baseline artifacts. No statisticalpower or forecastgain claim.

## Alternative-input research (24October)

Report: `EVENTX_ALTERNATIVE_FORECASTING_METHODS_20261024.md`;evidence
`data/v7/alternative_inputs_20261024/`,`data/v7/alternative_methods_report_20261024/`.
-19791payloads verified;14macro candidates4032grids:2200freshreceived YESbooks,
 1638spread/depthpasses,956quality240mhistories,327positivequotevolatility across5contracts.
-Matched820current6htrade-snapshotgrids:0YESactivitypasses,816books/613quality,
 347quotehistories/123positivevolatility. Tradeview omits short-windowupdates.
-Solepooledactivitypass uses2pairedcomplementaryrecords,last60mcount4→2ifcollapsed.
 V03overlapinterpretation:8roundedcross-tokenpairs240m,0same-directionpairs;
 priorV01/V02proseerrors retained/superseded. Not general executiondeduplication.
-Prefer separate quote-target study with persistence/weightedmid/linear baselines;
 duration/state-space methods secondary. Proposal not activated;no fit/labels/scores.
-Coverage is not accuracy,admission or independent event yield. Runningpilot unchanged.

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

- Agreed links95opened fresh rows(27movements),four contracts/five dates;fold5zero.
  Excluding ambiguous KalshiH0:48rows;also excluding flagged PPI summary:44rows.
- AllJulyFOMC;four co-isolation components are not four independent draws.
  Four originals unavailable;historical text authentication and H0rules unresolved.
  PPI cache misstates annual decline;preserve cached text rather than repair evidence.
- Release-to-article lags minimum80.868757/median180.344525minutes;zero within60m.
  Hypothetical timely release windows are not historical feature access or gains.
- V02corrects missing fifth-contract diagnostic;V01preserved. No established effective
  sample size,valid inference or empirical power. Full figures in linked ledger/archive.

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
3. Review the new two-market capture after24Oct21:27SGT; consider separate quote-study proposal.
   Resolve quantity/counting compatibility and exact predicate/terminal caveats.
4. Use the separately frozen timing policy for a future feasibility observation;
   keep model fixed/scoring disabled until all gates pass, then freeze later activation.
5. Keep V4 receipt/checkpoint checks separate and follow its frozen close sequence.

## Authoritative references

V4:`eventx/release/v4/{protocol.json,holdout_implementation_manifest.json,model_freeze_manifest.json}`.
V3.1:`eventx/release/v3_1_historical_primary/`; consumed result
`data/v3_1_historical/primary/holdout/evaluation_result.json`.
V5:`eventx/release/v5/{PROTOCOL_V1_1.md,REVISION_IMPLEMENTATION_20260910.md}`.
Detailed handoff:`docs/progress/CURRENT_STATE_ARCHIVE_20261023_ELIGIBILITY.md`;
monthly evidence:`docs/progress/2026-10.md`;legacy PROGRESS.md ends21August.
