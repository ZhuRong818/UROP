# EventX current state

> Canonical startup handoff. Frozen artifacts govern conflicts. Detailed preceding state:
> `docs/progress/CURRENT_STATE_ARCHIVE_20261024_BEFORE_MEMORY_FORECAST.md`.
> Append history to `docs/progress/2026-10.md`,not legacy PROGRESS.md.

Last updated: **2026-10-25 Asia/Singapore**; change-probability iteration completed;live operational counts remain timestamped below.

## Active objective and locked decisions

User authorized autonomous LOCAL research and separately versioned quote forecasting;SSH unavailable.
Produce timely forecasts and evaluate actual endpoints; do not equate operation with predictive superiority.
Original raw condition_120k trade classifier stays frozen:zero current prospective admissions.
New quote target is received YES-book midpoint30min later,not the original absolute-movement classifier.
Existing cohorts remain fixed. User explicitly authorized separate development segment/model discovery.
No protected early evaluation, external messages or trading; segment discovery is not confirmation.

## Current quote forecast result and jobs

Report:`EVENTX_USABLE_FORECAST_PROGRESS_20261024_REV2.md`;checkpoint:`data/v7/usable_forecast_progress_20261024/`.
- First240m-history shadow CLOSED:100decisions,44abstentions,56missed,zero forecasts/endpoints.
  All44abstentions lacked240m history;source cycle gaps4473.100816s/2159.973661s.
  `data/v7/quote_shadow_diagnosis_20261024/`;closed PIDs31131/61679. No late rescoring.
- First development:686complete,168train,444validation/9markets,21changed;persist MAE0.00008445945945945952,
  ridge0.00018114435192817977. All exploratory;no candidate promoted.
- NEW frozen memory-tier development:`data/v7/memory_quote_20261024/development/`:
  4032grids,1625snapshot-eligible,1418short-history-eligible,1418complete snapshot rows.
  Snapshot684train/614validation11markets,23changed;MAE persist0.0000627035830618893,ridge0.00015594596290242812.
  Short605train/588validation11markets,23changed;MAE persist0.00006547619047619052,short-ridge0.0001106744869564291.
  Same rows within panels,not across panels. Coverage improved;accuracy did not beat persistence.
  Outcome-exposed development,overlapping horizons,no independent confirmation. No promotion/refit.
- Snapshot reference needs fresh valid book/current status;short-ridge needs continuous30m history.
  Current book<=120s,spread<=.05,best-side depth>=10;mapping/status<=360s,active/unresolved;
  full30m forward quote/status continuity still required. Missing data stay unknown.
- NEW sourcePID5099,`data/v7/quote_source_20261024_v02/live/`,same2metadata-defined markets.
  Started24Oct14:04UTC,scheduledstop25Oct14:04UTC(22:04SGT);separate24h source run.
- NEW forecastPID8023,`data/v7/memory_quote_20261024/shadow/`;firstgrid24Oct14:10UTC;
  lastgrid25Oct13:30UTC,stop14:03UTC(22:03SGT). Code/models frozen in memory_shadow_20261024.
  Verified25Oct09:17UTC:218timely forecasts,200observed/12unavailable endpoints;PIDs5099/8023 alive.
  Reference=persistence;fixed weighted/snapshot-ridge/short-ridge candidates;no proven predictive edge.
  Reader:`.venv/bin/python -m eventx.tasks.show_v7_quote_forecasts_20261024`;rejects stale heartbeat/grid.
- Original releasePID600 and37-marketPID23793 verified alive at checkpoint. Last source audit79documentversions;
  zero newly admitted release evidence;BLS403 historically unresolved. No current V4 health claim.
- KeepMacpowered/awake/networked/lid-open. Sleep/receipt gaps invalidate affected windows;
  service cannot forecast while host suspended. Raw backfills never restore earlier availability.

## Segment-model discovery (24October)

- User authorized exploring segments; forecast-time rules only, all search results retained.
- `data/v7/segment_research_20261024/`:16variants including persistence,28segments,
  420nominal nonbaseline comparisons;405nonempty. Three purged inner forward windows.
- Zero candidates passed the frozen inner stability screen; selection remained persistence.
- Post-hoc discovery: hurdle_mean on momentum*imbalance>1e-12 reduces MAE6.271655917640395%,
  but only9already-exposed rows/3markets,1.53%coverage. This is a weak hypothesis,not validated gain.
- Exact candidate exported with588-row parity (maxdifference0);future observerPID21055 RUNNING.
  Firstgrid24Oct14:30UTC,stop25Oct14:04UTC;checkpoint2026-10-24T14:30:19.010486+00:00:
  Latest25Oct09:17UTC:214timely/6segment-active/196observed/12unavailable endpoints;PID21055 alive.
  Report:`EVENTX_SEGMENT_FORECAST_RESEARCH_20261024.md`;delivery in segment_research_20261024/delivery/.
  `eventx/release/v7/segment_candidate_20261024/`;outside segment/useful history fallback=persistence.
  No changes to existing source/base-forecast services or original trade model.

## Full-day observational quote study (25October)

- Report:`EVENTX_FULL_DAY_FORECAST_STUDY_20261025.md`;results:`data/v7/observational_quote_development_20261025/`.
- Source:`data/v7/archive_fullweek_20261025/`;same20markets,April21–27all24hours,168/168files;
  14reused,595574310new archive bytes,1458500YES events. No replacements.
- 38640scheduled grids;4086history-eligible;14330fresh pairs;
  2457complete observed history+forward. No cross-midnight windows;missingness retained.
- Separate observational target=archived midpoint30m ahead,not tradability/resolution/news;original admissions0.
  Historical active status/completeness still unknown. Price-only features;no reconstruction of depth.
- Frozen21–23train:782rows;24selection:261rows;25–27evaluation:1414rows/
  11markets/3dates. Selected persistence;matched persistence MAE0.00035183875530410234,
  selected MAE0.00035183875530410234;relative reduction0.0%. Changed102/unchanged1312.
- Chronological DEVELOPMENT only;no promotion/independent confirmation. Do not retune on25–27results.
  Six prespecified candidates including persistence;all selection results and per-market/day errors retained.
- QA:140prior market-day parity checks,future-feature isolation,missing-hour and tie-reset tests passed.
  Protected periods untouched;3369323new excluded-cohort April rows decoded then filtered.
- Prior source failures and pilot evidence preserved;see`docs/progress/CURRENT_STATE_BEFORE_FULLWEEK_RESULT_20261025.md`.
  V03 snapshot/replay failures remain;new price-only study does not validate depth or news features.

## Change-probability iteration (25October)

- COMPLETED:`EVENTX_CHANGE_PROBABILITY_ITERATION_20261025.md`;artifacts:`data/v7/change_probability_20261025/`.
- New target:any observed midpoint change30m ahead;primary fresh current+endpoint,no full-path requirement.
  Missing historical lags flagged;original strict population retained as secondary. No depth/news/tradability claim.
- Development only21–24:5980train/1988selection rows,831/237positives;7968refit. April25–27not reused.
  Selectedhgb7,frozen before new28–30test capture. All8selection candidates and3named baselines retained.
- New block:72/72files,263008006bytes,609180YES events;
  3729/16560eligible grids,903positives,11markets/3dates.
- Test LL:global0.5956253658332185,market0.7154008789111274,
  activity0.6052349794047419,selected0.4954911669183289;
  selected Brier0.15757754754470057,AP0.5233644517078284.
- RelativeLL reductions vs global/market/activity:16.811607540389442%/
  30.739368440182943%/18.13243057999519%. See report for per-day/strict/nonoverlap checks.
- Limitation:selected strict-subsetLL0.23684320760569166 vs global0.17940212157674426(worse);
  Apr30also slightly worse than global. Low-probability-bin calibration underestimates risk.
- New historical time block,same cohort;not prospective/independent-market confirmation. No live promotion.
  Preserve result;no28–30retuning. 831training positives ->94overlap components,not independent events.
- Source/mapping/eligibility assumptions remain;observed endpoints only. No improvement claimed for old MAE task.

## Calibration and transport iteration (25October)

- RUNNING:`eventx/release/v7/calibration_transport_20261025/protocol.json`;baseHGB7unchanged.
- New10event-family-disjoint contracts FROZEN after54metadata lookups;original20retained.
  May1–3source COMPLETED;V02calibration COMPLETED(identity selected),V01save failure preserved:`data/v7/calibration_transport_20261025/source_cal/`.
- Original-cohort calibrationMay1–2fit/May3selection;identity/intercept/monotone-sigmoid candidates.
  May1–2fit3101rows/511positives;May3select1078/170;identityLL0.36973766234887184.
  No calibration candidate improved selection. May4–6test capture COMPLETED;one-shot evaluation RUNNING onoriginal20+new10.
- Reportraw/calibrated/frozenbaselines/updatedglobal separately fororiginal andnewcohort.
  No old evaluation reuse or claims of prospective/tradable/news validation.

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
4. Preserve change-probability results;next test fixed-model transport across metadata-defined contracts
   and more calendar periods. No Apr25–30retuning or live promotion;report all baseline/sensitivity results.
5. Keep V4 operational checks separate; follow its frozen close/consumption sequence exactly once.

## Authoritative references

V4:`eventx/release/v4/{protocol.json,holdout_implementation_manifest.json,model_freeze_manifest.json}`.
V3.1:`eventx/release/v3_1_historical_primary/`; consumed result
`data/v3_1_historical/primary/holdout/evaluation_result.json`.
V5:`eventx/release/v5/{PROTOCOL_V1_1.md,REVISION_IMPLEMENTATION_20260910.md}`.
Detailed handoff:`docs/progress/CURRENT_STATE_ARCHIVE_20261023_ELIGIBILITY.md`;
monthly evidence:`docs/progress/2026-10.md`;legacy PROGRESS.md ends21August.
