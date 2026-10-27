# EventX current state

> Canonical startup handoff. Frozen artifacts govern conflicts. Detailed preceding state:
> `docs/progress/CURRENT_STATE_ARCHIVE_20261024_BEFORE_MEMORY_FORECAST.md`.
> Append history to `docs/progress/2026-10.md`,not legacy PROGRESS.md.

Last updated: **2026-10-27 Asia/Singapore** (report draft `EVENTX_FINAL_REPORT_DRAFT_20261101.md`); V03 emitter/evaluator frozen; fresh inputgate FAIL; no prospective test.

## Active objective and locked decisions

User authorized autonomous LOCAL research and separately versioned quote forecasting;SSH unavailable.
Produce timely forecasts and evaluate actual endpoints; do not equate operation with predictive superiority.
Original raw condition_120k trade classifier stays frozen:zero current prospective admissions.
Active quote study predicts probability of observed30m midpoint change;old point-regression result stays fixed.
Existing cohorts remain fixed. User explicitly authorized separate development segment/model discovery.
No protected early evaluation, external messages or trading; segment discovery is not confirmation.

## Completed live point-forecast experiment (audited26October)

- `EVENTX_LIVE_POINT_FORECAST_AUDIT_20261026.md`;`data/v7/live_memory_completion_20261026/`.
- Source/base/segment stopped normally25Oct14:03–14:04UTC;PIDsabsent26Oct01:00UTC.
  No active quote-forecast service;lastdisplayedpredictions expired. Original release jobs separate.
- Base562decisions,269timely,293abstentions,0missed;257observed/12unavailable outcomes.
  OnlyUSrecessioncontractcontributed;GDPcontractzero.12changedrows(twooverlapcomponents,notindependentevents).
- Snapshot257:MAEpersistence0.0002334630350194548,ridge0.00030554478497860934(+30.87501623250457%).
  Short240:MAEpersistence0.0002499999999999995,ridge0.00029924255872(+19.69702348800024%).
- Segment265timely/253observed/12unavailable;6activeobserved,referenceMAE0,candidate0.0008025987158923308.
  All253:referenceMAE0.00023715415019762802,candidate0.00025618811183934336(+8.025987158923309%).
- Auditpassed269feature/prediction+269endpointreplays,1815payloadhashes,chains/deadlines/frozenmodels.
  No primaryMAEwin or promotion;minor snapshotRMSEgain retained assecondary. No news/independentclaim.
- Live gate limits RECEIPT age,not source-message age:163/269sourceages>120s,median143.01200008392334s.
  Historical classifier hasdifferent18features/source-agegates;these aredifferenttasks,do notpoolclaims.
- Previouszero-forecast shadow/development/history preserved in
  `docs/progress/CURRENT_STATE_BEFORE_LIVE_COMPLETION_20261026.md`;oldmodels remainfrozen.

## Earlier quote experiments
- April25–30,May4–6 andMay10–12opened;no retuning. Oldpointfailure and18featuremodels preserved.
- Fullhistory:`docs/progress/CURRENT_STATE_BEFORE_CLOCK_CORRECTION_20261026.md`;frozenreportsgovern.

## Seven-day fixed-model replication (25October)

- COMPLETED:`EVENTX_SEVEN_DAY_REPLICATION_20261025.md`;`data/v7/week_replication_20261025/`.
- May13–19,all60existingIDs;current/legacy boosters+3baselines unchanged,no fit/newidentities.
- Developmentcohort:27924known/32477issued/96600grids,30contracts;
  LLcurrent0.3583213732070323,logistic0.4524090254527762,legacy0.4283494185894651.
- Training-excluded:2033known/2694issued/19320grids,6contracts;
  LLcurrent0.255471891359488,logistic0.2646930812520174,legacy0.3348654193966712.
- Sources168/168hours,3failedattempts/3recovered;5982429YES events.
- Allcurrent-validforecasts retained;missing-label bounds(notCIs),strict/nonoverlap/date/contract metricsreported.
  QA9579hashentries/45metricsets passed. Historical only,no news/livepromotion.
- LLgainvslogistic20.797032541864066%development/3.4837290982115996%excluded;excludednonoverlapreverses.
  Developmentmissing-labelboundspositive;excludedboundscrosszero. No unconditionaltransferclaim.
- May13–19nowconsumed;no retuning. Same60conveniencecontracts;historicalstatus/expiry/independence unresolved.

## Frozen classifier runtime (26October)

- COMPLETED:`EVENTX_FROZEN_FORECAST_RUNTIME_20261026_REV2.md`;release`forecast_runtime_20261026_v01`.
- Emitter/evaluator+41dependenciesfrozen;51checks+syntheticintegrationPASS;model/target/cohortunchanged.
- Sourceprefix/durabledeadline receipts;onlinepacketvalidation;closed-windowonce-onlyevaluator.
- Capturedeadline event reached;wallstop117.089msearly=>normalcheckFAIL;ready0/16,gateFAIL.
- Nativepacketsvalid6/24;clocksteps1;diagnosis`data/v7/forecast_runtime_20261026_v01/readiness_diagnosis.json`.
- Delivery:`eventx/release/v7/forecast_runtime_20261026_v01/delivery_addendum_manifest.json`;no activation/forecasts/labels/test.
- ActivationBLOCKEDbyfreshgate;preservefailureandrepairinnewversion,nothresholdrelaxation.
- Root cause = host clock (see `EVENTX_JUNE_OUT_OF_TIME_TEST_20261026.md`): macOS sntp returned all-zero selected
  packets while host ~287ms fast; OS stepped wall clock -110ms at11:51:08 (warmup reset, stop117ms early);
  afterwards host ~+0.11s slow > 100ms budget. Fix needs disciplined host or new monotonic+validated-offset version.

## ACTIVE: V02 three-day prospective test (activated 26Oct 17:53:53Z; activations 1-2 superseded, 0 forecasts) — do not disturb

- `EVENTX_NEW_IDENTITY_AND_RUNTIME_V02_20261026.md`; release `eventx/release/v7/forecast_runtime_20261026_v02/`.
- Grids 27Oct00:30–29Oct23:25 UTC, 30 metadata-selected contracts, frozen V03 model; source+emitter running (caffeinate).
- Evaluate EXACTLY ONCE after 29Oct23:57:30Z: `python -m eventx.tasks.evaluate_v7_forecast_runtime_20261026_v02`.
  Health (label-free): `python -m eventx.tasks.status_v7_forecast_runtime_20261026_v02`. No restart of source into same dir.
- 27Oct01:08Z live: 181/240 ready over 8 grids, 0 emitter restarts. Known defect: grid 00:30 all-abstained
  (primed-input handoff not refreshed -> pong >35s; fail-closed, 30/24840 decisions); later grids normal; not patched.
- Readiness (fixed collector) PASS 156/180 ready/27 markets; V01 runtime stays frozen/failed. Report deadline 1 Nov.
- New-identity June8–14 PASS: row_hgb7 -14.9% LL vs logistic, CI[0.033,0.119]; V03 -19.7%, CI[0.066,0.147].
  June8–14 consumed for both models; June15–28 still unopened.

## June out-of-time test of frozen quote-change booster (26October) — PASS

- `EVENTX_JUNE_OUT_OF_TIME_TEST_20261026.md`;`data/v7/june_replication_20261026/`;release`eventx/release/v7/june_replication_20261026/`.
- June1–7 unopened (no prior June quote reads; before OOT/V3.1/V4). Same60IDs, frozen row_hgb7 + 4 baselines, no fit.
- 168/168 hours, 0 protected rows; 20/60 contracts active; 22034 issued, 18677 known/2468 positive, 3357 unknown.
- development50 LL row_hgb7 0.2930988249673845 vs logistic 0.35225 (-16.79%), legacy 0.328517, global 0.385413;
  Brier 0.08483 vs 0.10027. Contract-clustered 95% CI of gain vs logistic [0.0391,0.0805] nats (18 contracts).
- 7/7 dates and 17/20 contracts beat logistic; nonoverlap/strict agree. Excluded10 only 2 contracts (-13.80%).
- Missing-label bounds vs logistic [-0.0010,0.0998] (dev50). Historical replay, not live; June now CONSUMED for this model.

## Clock correction (26October)

- COMPLETED:`EVENTX_CLOCK_ALIGNMENT_AND_READINESS_20261026.md`;canonical`source_time_study_20261026_v03`.
- IndependentGoogleSNTPoffset+58.124..61ms;officialWSformatmilliseconds,/timeonlyseconds. No systemtimechanges.
- V03leadcap250ms;BOTHsourceandavailability<=decision;rawtimesunchanged;as-ofclockhealth andstepguards.
- Refit41400gridrows/3688predictions identicalV02;38checksPASS;old15.986910020304176%developmentgain unchanged.
- Fresh40mincapture completed;strictready4→V03ready4,contributing2contracts;inputgatePASS.
- Clockrounds8,passing7;detectedsteps0;sourcelead>250ms:0/100.
- QA16as-offeatures+16clockchecks;allpotentiallyadmittingnativepacketsvalid.
- Release:`eventx/release/v7/source_time_study_20261026_v03/delivery_manifest.json`;no activeforecastservice/test.

## Source-time preparation history
- V01day-reset defect repaired inV02;V02strict-clock inputgate failed. All failures preserved.
- Development:May7–8fit6304;May9known3102/535positive;refit9406/20contracts;unknown586/3688.
- All-issuedlogisticgainbounds[-0.08159266365256779,0.10053014535673122],notCIs.
- Full history:`docs/progress/CURRENT_STATE_BEFORE_RUNTIME_FREEZE_20261026.md`;V02/V03frozenreportsgovern.

## Live-input compatibility (26October)

- COMPLETED input audit:`EVENTX_LIVE_INPUT_COMPATIBILITY_20261026.md`;
  `data/v7/live_input_compatibility_20261026/`;21unit checks passed,no labels/models/test.
- Original18feature arithmetic:10969development vectors matched exactly,maxerror0.
- Live projection zero errors;old model BLOCKED:archive receipt grouping/clock/dedup equivalence unverified.
  Published31Julycollector is not verified May deployment. Raw WS cannot silently substitute.
- Separate14feature source-time contract frozen;requiresNEWfit andtarget/validation protocol.
  Drops numerical ages/receipt-group counts,retains120s freshness/availability gates.
- New replay:11084/41400development inputs;286/562live inputs,211mechanically ready.
  Wire/durable clocks still change2eligibility decisions and some lags;coverage is not accuracy.
- Release:`eventx/release/v7/live_input_compatibility_20261026/delivery_manifest.json`.
  No forecast admissions,new test orservice restart;frozen18featuremodel unchanged.

## Other source evidence retained
- Detailed source/provider/release evidence:`docs/progress/CURRENT_STATE_CHANGE_PROB_DETAIL_20261025.md`.
- Six release episodes29Oct–4Dec and12provisional links retained;exact evidence/terminal gates unresolved.
- Provider52records map52fills/29transactions;47late-unrecovered records chainmatched. No general parity fix.
- Quote/source redesign does not repair original trade-model eligibility,news timestamps or historical status.

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

- Canonical ledger:`data/v7/verified_event_ledger_20261015_v02/`;report`EVENTX_VERIFIED_EVENT_LEDGER_AND_COVERAGE_20261015.md`.
- Two assistant reviewers agreed32material-context links/12articles;78pairs64agreements/14disagreements.
  Not independent human gold;zero exact-predicate links.95fresh rows,27movements,fourcontracts/fivedates;
  allJulyFOMC,fold5zero. Source/rule/independent-episode problems remain. Full detail in archived handoff.
- Release/article lags min80.868757/median180.344525minutes;zero<=60m. Hypothetical windows are not gains.
- Earlier matched5388-row M/E/T/C fold5:LL M0.24272243956157083,E0.24232437076003854(best),
  T0.24239546292985711,C0.24238825908649334;C-T gain0.000007203843363788398nats,belowE.
- Signedextractorv0.3.3:11links/twoarticles,zeroOOFcoverage;relaxed144articles/1056rows,fold5six/17.
  147377deduplicated documents/479179legacy associations processed. No demonstrated incremental news gain.
  `MARKET_NEWS_CONTINUATION_20261014.md`;new change-probability study contains no news features.

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
- 27Oct01:09Z label-blind check PASS: collector+guard alive, news58/58, trades51/51 receipts, 0 pending,
  15/15 hashes, no protected outputs. `data/v4/health_checks/20261027T010946Z/report.json`.
  Collector seals Oct29 just after 30Oct00:00Z, then status=sealed_collection_complete_pending_data_gate and exits.
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
  authorizes V7 sources and a separate quote-forecast experiment.
- KOL deferred after association failures. EventXBenchT2 validation/test labels sealed;
  do not open/bulk-download silver data without a new gate.
- PORTEND is separate portfolio work; not part of the market-news research task.
- Paper A: `MARKET_NEWS_PAPER_A_DRAFT_20261010_REV2.md`; human scientific review,
  author/venue details/release rights remain. Slides:`eventx/release/presentation_20261012/rev6/`,
  through12October only; later research not automatically incorporated.

## Next actions

1. Preserve closed live point-forecast failure and historical classifier gains as separate evidence.
2. Resolve fresh runtimeinputfailure fromreadinessdiagnosis inaseparatelyfrozenversion.
   Do notactivateusingtheearlierV03pass;freshgatefailed.No prospective teststarted.
3. Continue original release capture and reserved29Oct–4Dec episodes; exact evidence/terminal gates remain.
4. Preserve seven-day replication;May13–19opened. Address missing outcomes and historical status
   before claiming usable live accuracy. New model/eligibility choices require new evaluation blocks.
5. Keep V4 operational checks separate; follow its frozen close/consumption sequence exactly once.
6. June1–7 confirmed booster out-of-time. Next: metadata-selected larger live cohort and new-identity test on an
   unopened later June week (June8–28 unopened); live service needs a disciplined clock first.

## Authoritative references

V4:`eventx/release/v4/{protocol.json,holdout_implementation_manifest.json,model_freeze_manifest.json}`.
V3.1:`eventx/release/v3_1_historical_primary/`; consumed result
`data/v3_1_historical/primary/holdout/evaluation_result.json`.
V5:`eventx/release/v5/{PROTOCOL_V1_1.md,REVISION_IMPLEMENTATION_20260910.md}`.
Detailed handoff:`docs/progress/CURRENT_STATE_ARCHIVE_20261023_ELIGIBILITY.md`;
monthly evidence:`docs/progress/2026-10.md`;legacy PROGRESS.md ends21August.
