# EventX current state

> Canonical startup handoff. Frozen artifacts govern conflicts. Detailed preceding state:
> `docs/progress/CURRENT_STATE_ARCHIVE_20261024_BEFORE_MEMORY_FORECAST.md`.
> Append history to `docs/progress/2026-10.md`,not legacy PROGRESS.md.

Last updated: **2026-10-25 Asia/Singapore**; seven-day replication frozen;source capture running;live counts timestamped below.

## Active objective and locked decisions

User authorized autonomous LOCAL research and separately versioned quote forecasting;SSH unavailable.
Produce timely forecasts and evaluate actual endpoints; do not equate operation with predictive superiority.
Original raw condition_120k trade classifier stays frozen:zero current prospective admissions.
Active quote study predicts probability of observed30m midpoint change;old point-regression result stays fixed.
Existing cohorts remain fixed. User explicitly authorized separate development segment/model discovery.
No protected early evaluation, external messages or trading; segment discovery is not confirmation.

## Current quote forecast result and jobs

Report:`EVENTX_USABLE_FORECAST_PROGRESS_20261024_REV2.md`;checkpoint:`data/v7/usable_forecast_progress_20261024/`.
- Historical quote development details:`docs/progress/CURRENT_STATE_TRANSPORT_DETAIL_20261025.md`.
  First240m-history shadow closed:100decisions/44abstentions/56missed,zero forecasts. Not rescored.
- Memory-tier development:`data/v7/memory_quote_20261024/development/`:1418complete snapshot rows;
  snapshot614validation,MAEpersist0.0000627035830618893/ridge0.00015594596290242812;
  short588validation,MAEpersist0.00006547619047619052/ridge0.0001106744869564291.
  Outcome-exposed,overlapping horizons,no improvement/promotion/independent confirmation.
- Snapshot reference needs fresh valid book/current status;short-ridge needs continuous30m history.
  Current book<=120s,spread<=.05,best-side depth>=10;mapping/status<=360s,active/unresolved;
  full30m forward quote/status continuity still required. Missing data stay unknown.
- NEW sourcePID5099,`data/v7/quote_source_20261024_v02/live/`,same2metadata-defined markets.
  Started24Oct14:04UTC,scheduledstop25Oct14:04UTC(22:04SGT);separate24h source run.
- NEW forecastPID8023,`data/v7/memory_quote_20261024/shadow/`;firstgrid24Oct14:10UTC;
  lastgrid25Oct13:30UTC,stop14:03UTC(22:03SGT). Code/models frozen in memory_shadow_20261024.
  Verified25Oct12:47UTC:260timely forecasts,242observed/12unavailable endpoints;PIDs5099/8023 alive.
  Reference=persistence;fixed weighted/snapshot-ridge/short-ridge candidates;no proven predictive edge.
  Reader:`.venv/bin/python -m eventx.tasks.show_v7_quote_forecasts_20261024`;rejects stale heartbeat/grid.
- Original releasePID600 and37-marketPID23793 verified alive at checkpoint. Last source audit79documentversions;
  zero newly admitted release evidence;BLS403 historically unresolved. No current V4 health claim.
- KeepMacpowered/awake/networked/lid-open. Sleep/receipt gaps invalidate affected windows;
  service cannot forecast while host suspended. Raw backfills never restore earlier availability.

## Segment-model discovery (24October)

- Frozen discovery:`data/v7/segment_research_20261024/`:420comparisons;zero stability-screen winners.
  Posthoc hurdle_mean6.271655917640395%MAEgain on9exposed rows/3markets,not validated.
- Fixed observerPID21055;stop25Oct14:04UTC. Last12:47UTC:256timely/6active/238observed/12unavailable,alive.
  `eventx/release/v7/segment_candidate_20261024/`;no live retuning or model promotion.

## Prior quote experiments (25October)

- Full-day point-regression:`EVENTX_FULL_DAY_FORECAST_STUDY_20261025.md`;persistence selected.
  Apr25–27 evaluation1414rows/11markets,MAE0.00035183875530410234;no gain,no retuning.
- Change probability:`EVENTX_CHANGE_PROBABILITY_ITERATION_20261025.md`;frozenhgb7.
  Apr28–30:3729rows/903positives/11markets;LL0.4954911669183289 vs global0.5956253658332185,
  activity0.6052349794047419;Brier0.15757754754470057,AP0.5233644517078284.
  LLgain16.811607540389442%global/18.13243057999519%activity;strict-subset loss remains.
- Target:endpoint midpoint differs30m later;fresh current+endpoint,no full-path primary gate.
  Missing lag flags;no news/depth/tradability claim. Historical same-cohort test,no live promotion.
- Apr25–30opened;no retuning. Source/QA/earlierfit detail archived in
  `docs/progress/CURRENT_STATE_FAMILY_RESULT_DETAIL_20261025.md`;frozen artifacts govern.

## Calibration and transport iteration (25October)

- COMPLETED:`EVENTX_CALIBRATION_AND_TRANSPORT_20261025.md`;`data/v7/calibration_transport_20261025/`.
- OriginalHGB7unchanged;10newcontract/event-family-disjoint IDs frozen before prices(54metadata lookups).
- Calibrationoriginal20:May1–2fit3101rows,May3select1078;chosenidentity.
  RefitMay1–3;mapa=1.0,b=0.0;frozen before newMay4–6test. Updated-globalcontrolincluded.
- Originalcohorttest:3617rows/10markets;LLraw0.49652958373600004,
  calibrated0.49652958373600004,updatedglobal0.5365791410562563.
- Newcohorttest:2006rows/4markets;LLraw0.8126213299352547,
  calibrated0.8126213299352547,updatedglobal0.7340095964891371.
- Bothsourcephases72/72and72/72files;strict/nonoverlap/per-day/market/calibration diagnostics retained.
- Temporal gain retained;new-contract transfer FAILED vs activity/updatedglobal,newAUC0.5196989262077948.
  Only4/10newcontractseligible(3politics,1crypto);no posthoc replacements. Calibrationselectedidentity.
- Samefeatures,target,endpointeligibility;noold25–30Aprilreuse. May4–6nowconsumed,no retuning.
  Historical/observational,notprospective;familyIDsnotindependentshocks. No deployment/news/tradabilityclaim.

## Broader-family training iteration (25October)

- COMPLETED:`EVENTX_BROADER_FAMILY_TRAINING_20261025.md`;artifacts`data/v7/family_training_20261025_v02/`.
- V01metadata exhausted167candidates/18qualified;V02preserved18,extendedidentitygroups1/2,
  11211222identitybytes+75newlookups =>30newfamilies.50development/10unseenIDs frozen beforeprices.
- May7–8fit6143rows/19families;May9select3069;chosenrow_hgb7.
  RefitMay7–9:9212rows/20families. Samefeatures/gates,weightingablationprespecified.
- TestMay10–12:developmentcohort10314rows/29markets;LLselected0.36242358010716824,
  activity0.468667061709134,legacy0.45296919182121015.
- Unseen1145rows/5markets;LLselected0.46205740072128865,
  activity0.5112204942953479,global0.566114599172508,legacy0.46041891573554555.
- 72/72dev,71/72testfiles;allmodels/strict/nonoverlap/calibration/per-market results retained.
  May12T09ReadTimeout:affected endpoints missing,notimputed;failure preserved.
  Historical observational test,notprospective/independentshocks. No automaticpromotion or news/tradabilityclaim.
- LLgainvsactivity22.66928706585807%development/9.616808035410294%unseen;unseen0.355868303787111%worselegacy.
  WeightingdidnotimproveLL;fiveunseencontracts,208/274positivesfromonecontract. No broadtransferclaim.
- May10–12nowopened;do not retune onit. Older failed attempts and tests preserved.

## Seven-day fixed-model replication (25October)

- CAPTURE COMPLETE;evaluation starting:`eventx/release/v7/week_replication_20261025/protocol.json`.
- May13–19,all60existingIDs;current/legacy boosters+3baselines unchanged. No newcontractidentities.
- Saveallcurrent-validforecasts/nullendpoints;reportconditionalmetrics+missing-label bounds(notCIs).
- Source168/168hours,171attempts,3recoveredfailures,1659517394bytes,5982429YES events.
- Preflight11459-row predictionparity exact;labelindependence/bounds/retry-recovery checks passed.
  Metadata:6developmentcontracts scheduledendbeforetest,11allcohortduring;allretained.
  `data/v7/week_replication_20261025/`;May13–19once-onlyevaluation starting. No prospective/promotionclaim.

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

1. Monitor source, memory-tier forecast and separate fixed segment-candidate observer; no live retuning.
2. At completion audit matched endpoints and missingness, report MAE/RMSE and per-market results.
   No candidate promotion or retuning from interim results; two markets are not independent event yield.
3. Continue original release capture and reserved29Oct–4Dec episodes; exact evidence/terminal gates remain.
4. Freeze paired current/legacy/baseline evaluation across more new dates/contracts;record coverage.
   May10–12opened;new selection needs new blocks. Same-date breadth ablation remains untested.
5. Keep V4 operational checks separate; follow its frozen close/consumption sequence exactly once.

## Authoritative references

V4:`eventx/release/v4/{protocol.json,holdout_implementation_manifest.json,model_freeze_manifest.json}`.
V3.1:`eventx/release/v3_1_historical_primary/`; consumed result
`data/v3_1_historical/primary/holdout/evaluation_result.json`.
V5:`eventx/release/v5/{PROTOCOL_V1_1.md,REVISION_IMPLEMENTATION_20260910.md}`.
Detailed handoff:`docs/progress/CURRENT_STATE_ARCHIVE_20261023_ELIGIBILITY.md`;
monthly evidence:`docs/progress/2026-10.md`;legacy PROGRESS.md ends21August.
