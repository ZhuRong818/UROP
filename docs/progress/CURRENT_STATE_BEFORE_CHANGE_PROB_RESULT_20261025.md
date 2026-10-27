# EventX current state

> Canonical startup handoff. Frozen artifacts govern conflicts. Detailed preceding state:
> `docs/progress/CURRENT_STATE_ARCHIVE_20261024_BEFORE_MEMORY_FORECAST.md`.
> Append history to `docs/progress/2026-10.md`,not legacy PROGRESS.md.

Last updated: **2026-10-25 Asia/Singapore**; full-day observational development completed;live operational counts remain timestamped below.

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
  Verified25Oct07:28UTC:196timely forecasts,178observed/12unavailable endpoints;PIDs5099/8023 alive.
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
  Latest25Oct07:28UTC:192timely/6segment-active/174observed/12unavailable endpoints;PID21055 alive.
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

## New change-probability cycle (25October)

- User authorized next iteration;protocol:`eventx/release/v7/change_probability_20261025/protocol.json`.
- Development COMPLETED onApril21–24only;April25–27excluded from tuning. Primary fresh-endpoint
  eligibility;missing lag quotes explicit,old continuous-history+forward retained as secondary.
- Target=any observed midpoint change30m ahead. Global/market/activity baselines plus5challengers;
  select log loss24April,refit21–24,freeze before retrieving new28–30April test block.
- 5980train/1988selection rows,831/237positives. SelectedHGB7leaves;selectionLL0.2717681949578039
  versusglobal0.3670781318612201,market0.30769291079626054,activity0.3277890776713946.
- Models frozen;April28–30source COMPLETED;one-shot evaluation RUNNING:`data/v7/archive_change_test_20261025/`,72hours.
  New historical block is not prospective;no original-study tradability/news claims or live changes.

## Other source evidence retained

- Original/revised22-market rehearsals completed:588233/380142records;0/3159 and0/2016activitypasses.
  Different periods,not controlled improvement. Revised maxgap26627.861848s;host sleep overlaps.
- Price-blind metadata expansion204records ->2new candidates,470protected IDs excluded.
  GDP full-year/annualized rule and recession dual GDP/NBER early-terminal caveats remain;not human gold.
- Provider52records map52orderfills/29transactions,mixedmaker/taker schema;16/63omissions recovered late,
  remaining47chainmatched. No general accounting fix or old-model feature parity. Request remains unsent.
- Cross-token overlap V03:8roundedcomplementarypairs in240m,0same-directionpairs;last60m naivecount4->2ifcollapsed.
  PriorV01/V02prose errors preserved/superseded;not general executiondeduplication.
- Alternative methods report:`EVENTX_ALTERNATIVE_FORECASTING_METHODS_20261024.md`;later frozen quote studies
  supersede its unactivated-proposal status. Original source/frozen-trade rules remain unchanged.
- Six original release episodes29Oct–4Dec retained;12new metadata links provisional. No news-event service
  activated,exact-predicate and independent episode/power requirements unresolved.

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
4. Complete the frozen change-probability iteration:21–24development,28–30new time-block evaluation;
   preserve all baselines and missingness. No April25–27retuning or automatic live promotion.
5. Keep V4 operational checks separate; follow its frozen close/consumption sequence exactly once.

## Authoritative references

V4:`eventx/release/v4/{protocol.json,holdout_implementation_manifest.json,model_freeze_manifest.json}`.
V3.1:`eventx/release/v3_1_historical_primary/`; consumed result
`data/v3_1_historical/primary/holdout/evaluation_result.json`.
V5:`eventx/release/v5/{PROTOCOL_V1_1.md,REVISION_IMPLEMENTATION_20260910.md}`.
Detailed handoff:`docs/progress/CURRENT_STATE_ARCHIVE_20261023_ELIGIBILITY.md`;
monthly evidence:`docs/progress/2026-10.md`;legacy PROGRESS.md ends21August.
