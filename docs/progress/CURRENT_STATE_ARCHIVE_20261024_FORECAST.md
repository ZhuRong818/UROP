# EventX current state

> Canonical startup handoff. Frozen artifacts govern conflicts. Detailed prior state:
> `docs/progress/CURRENT_STATE_ARCHIVE_20261023_ELIGIBILITY.md`.
> Append history to `docs/progress/2026-10.md`,not legacy PROGRESS.md.

Last updated: **2026-10-23 Asia/Singapore** (compatibility measured; current eligibility zero)

## Active objective and locked decisions

User authorized local autonomous research until human review is needed;SSH unavailable
and no longer a dependency. Complete source rehearsals,resolve accounting/coverage,
then assess prospective observations. **Keep raw condition_120k fixed until one complete
observation passes source/history/freshness/forward/terminal/evidence gates. Zero admissions.**
No outcome-driven cohort replacement,no early protected evaluations,no provider messages sent.

## Latest completed research

Canonical report:**`EVENTX_INPUT_COMPATIBILITY_AND_ELIGIBILITY_20261023.md`**.
Evidence:`data/v7/input_eligibility_20261023/`,`data/v7/missing_receipt_analysis_20261023/`,
`data/v7/eligibility_report_20261023/`;all manifests verified. No scores/labels/tests.

- Interim audit02:36:46UTC23Oct:501235journalrecords,414444verifiedpayloads,20original
  locks match. Maximum candidate receiptgap7267.666361s(121.13min);cause not established.
- Fixed02:35UTCgrid:14/14candidate mappings/rules match;0freshYES;all14failcount60,
  count240,quantity240.13lackseeded240mpath;onecomputablepathhaszero volatility.
 0/2696overlapping candidatewindows pass quantityactivity;not independent observations.
  Selectedvenue/providerreceipts and completed-window summaries all predategrid14/14:
  `data/v7/eligibility_asof_receipt_check_20261023.json`.
- Historical feature semantics:token quantity,notcash;trailingwindows(t-window,t].
  `EVENTX_FEATURE_SEMANTICS_20261022.md`;fourhistoricalcodehashes verified.
  Original/V03inclusivewindow diagnostics are not exact model eligibility.
- Accounting:verifiedidentitymapping preserves sampledprovider counts/quantities.
  Directmaker-inclusive→taker-only changes240mcount/quantity4/5controls;
  original→lateprovider changes3/4controls. No source convention promoted.
-52providerrows map uniquely to52order-fill events in29successful transactions:
 36IDs=transactionHash:orderHash,taker=eventtaker;16bareIDs,taker=eventmaker.
  Directwallet=eventmaker52/52,outersenderagreement0/52. Fourambiguitiesresolved via
  logindices564/566/568/576. Order-fill legs are not necessarily independent executions.
- Fourhistoricalwindows re-fetched~14.68hafterend:45→138rows(45unchanged+93added).
 16/63missing records recovered;47remain(45in$80kBTCcontrol),no backdating.
- All47remainingrecords now uniquely matchsuccessful chain taker-orderfills,same
  exchangeas captured,44BUY/3SELL.29participants previouslyseen;only1sender overlaps
  prior29transactions. No causalfilterclaim. SingleRPC,notindependentfinalityproof.
- Chainlookups retained only44allowlisted-tokenfilllogs;no broadscan. Earlier
  historicaleth_getCode403and sandbox failures preserved;zeroaddresscodechecks.
  Settlementordering is not CLOBmatching/arrivalordering;monotonicprices prove neither.
- Narrowedunsent request:`data/v7/eligibility_report_20261023/PROVIDER_RECONCILIATION_DRAFT.md`:
  reconcile47omissions,confirmmixedID/countingcontract,provideingestion/backfillclocks.
  Earlierbroadreviewquestions superseded where sampledchainfindings apply.

## Local source jobs and next gates

Allfourprocesses verified23Oct03:30UTC. Heartbeats do not certify continuity.
- Officialreleases:PID600,service`com.eventx.original-releases.20261018.v02`;
  `data/v7/official_source_capture_20261018/live/`;freeze
  `eventx/release/v7/original_source_capture_20261018_v02/`.79baselineversions,
 0admittednewpredictivereleases;14targets/11dates,stops1Jan2027. BLS403 persists.
- Original37markets:PID23793,`com.eventx.market-capture.20261018`;
  `data/v7/market_cohort_capture_20261018/live/`;freeze
  `eventx/release/v7/market_capture_20261018/`;stops12Nov00UTC.
- Original22-marketdirectrehearsal:PID39643,`com.eventx.direct-source-pilot.20261022`;
  `data/v7/direct_source_pilot_20261022/live/`;freeze
  `eventx/release/v7/direct_source_pilot_20261022/`.Stop23Oct05:58:25UTC(13:58SGT).
  Latest03:30UTClivecheckpoint525314records;distinctfromfrozensnapshotabove.
- ControllerPID74338,`com.eventx.source-workflow.20261022`;41-filefreeze
  `eventx/release/v7/source_workflow_20261022/`;waitsoriginalcompleted-auditreceipt,
  runsseparate24hV03andfinalaudit,thenstopsbeforeeventactivation/scoring.
  Administrativestop25Oct12UTC. Originalcollectors unchanged;live/STOP stops each.
<!-- V7_SOURCE_WORKFLOW_STATUS_START -->
- Autonomous source phase: **finished_source_review**, at2026-10-24T06:06:48.061042+00:00.
- Live status/evidence: `data/v7/source_workflow_20261022/status.json`.
- Event activation disabled; model frozen; zero admissions.
<!-- V7_SOURCE_WORKFLOW_STATUS_END -->
- Revisedfreeze:`eventx/release/v7/direct_source_pilot_20261022_v03/`;replacement
  APIusescondition/cursor/localtimefiltering andresolutioncapture. Legacyretirement
  notice24Oct. Short5minsmoke454HTTP200/10HTTP404/0HTTP429doesnotcertifyreliability.
- Fixedsample14annualmacro+3legacymacrodiagnostics+5BTCcontrols;all470V4IDsexcluded,
  Feddecisionfamilies quarantined. Controlsare not researchcohort admissions.
- Sixfutureepisodes29Oct–4Dec;84metadata-linkplans,singleassistantassessment,
  nothumangold. Reservation:`eventx/release/v7/direct_source_pilot_20261022/episode_reservation.json`.
  Firstwarmup29Oct06:30UTCconditionalonreadiness;noeventserviceactivated.
- Remaininggates:coverage/canonicalaccounting,validasof240mhistory,prespecifiedfresh
 30mendpoint/acquisitionlatency,actualterminalproof,relevantnovelreleaseevidence,
  episodeindependence/power,newunseenconfirmationfreeze. End_date is not terminalproof.
- KeepMacpowered/awake/connected. Earlier41.38mingapoverlappedlidsleep;
  nooperationguarantee. Backfillneverrestorestimelyavailability. Missingfeeds≠zeronews.

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
3. Resolve measured source gaps; version a longer-lived cohort across more releases.
   Model stays frozen until one complete gated observation.
4. Local source workflow reviews the original final24h audit after23Oct05:58UTC,
   then runs/audits V03 for24h. Resolve trade identity/feature compatibility using
   local receipts; six future episodes remain reserved, activation gated.
5. Keep V4 receipt/checkpoint checks separate and follow its frozen close sequence.

## Authoritative references

V4:`eventx/release/v4/{protocol.json,holdout_implementation_manifest.json,model_freeze_manifest.json}`.
V3.1:`eventx/release/v3_1_historical_primary/`; consumed result
`data/v3_1_historical/primary/holdout/evaluation_result.json`.
V5:`eventx/release/v5/{PROTOCOL_V1_1.md,REVISION_IMPLEMENTATION_20260910.md}`.
Detailed handoff:`docs/progress/CURRENT_STATE_ARCHIVE_20261023_ELIGIBILITY.md`;
monthly evidence:`docs/progress/2026-10.md`;legacy PROGRESS.md ends21August.
