"""Consolidate input diagnostics, literature and a separately proposed quote study."""
import json
from pathlib import Path
from eventx.tasks.discover_v7_direct_pilot_20261022 import REPO_ROOT,now,sha,write,verify_originals

OUT=REPO_ROOT/'data/v7/alternative_methods_report_20261024'
SRC=REPO_ROOT/'data/v7/alternative_inputs_20261024'
PAIR=REPO_ROOT/'data/v7/paired_token_overlap_20261024_v03'

def main():
    for manifest in [SRC/'manifest.json',PAIR/'manifest.json']:
        for p,h in json.loads(manifest.read_text())['files'].items():
            if sha(REPO_ROOT/p)!=h:raise RuntimeError('Evidence hash mismatch')
    report=json.loads((SRC/'report.json').read_text());pair=json.loads((PAIR/'report.json').read_text())
    grids=[json.loads(l) for l in (SRC/'grids.jsonl').read_text().splitlines()]
    mainrows=[r for r in grids if r['source']=='completed_v03' and r['role']=='prospective_macro_candidate']
    matched=[r for r in mainrows if r['trade_window_current']]
    stats={'at':now().isoformat(),'macro_grids':len(mainrows),'matched_grids':len(matched),
        'matched_yes_activity_pass':sum(r['trade_features']['yes']['raw_activity_screen'] for r in matched),
        'matched_pooled_raw_activity_pass':sum(r['trade_features']['pooled']['raw_activity_screen'] for r in matched),
        **{k:sum(r[k] for r in matched) for k in ['yes_book_available','yes_book_quality','quote_history240_quality','positive_quote_sigma240']},
        'positive_quote_history_markets':len({r['market_id'] for r in mainrows if r['positive_quote_sigma240']}),
        'payloads_read_and_verified':report['payloads_read_and_verified'],
        'fixed_model_changed':False,'new_models_fitted':False,'predictive_admissions':0,'tests_added_or_run':False,
        'original_locks_verified':verify_originals()}
    allgroup=next(r for r in report['groups'] if r['source']=='completed_v03' and r['role']=='prospective_macro_candidate')
    sources=[
        {'title':'Polymarket positions and tokens','url':'https://docs.polymarket.com/concepts/positions-tokens','use':'Complementary payout and complete-set mechanics; not equality of asynchronous trade prices'},
        {'title':'Gould and Bonart: Queue Imbalance as a One-Tick-Ahead Price Predictor','url':'https://arxiv.org/abs/1512.03492','use':'Logistic queue-imbalance reference on10Nasdaq stocks, not a30minute prediction-market performance baseline'},
        {'title':'Cont, Kukanov and Stoikov: The Price Impact of Order Book Events','url':'https://arxiv.org/abs/1011.6402','use':'Order-flow-imbalance/depth relationship on50NYSE stocks; largely contemporaneous impact, not automatic forecasting evidence'},
        {'title':'Stoikov: The Micro-Price','url':'https://papers.ssrn.com/sol3/papers.cfm?abstract_id=2970694','use':'Search-index abstract available; direct page403; fitted estimator differs from simple weighted midpoint'},
        {'title':'Author microprice repository','url':'https://github.com/sstoikov/microprice','use':'Author-hosted method implementation and paper link; no code downloaded or run'},
        {'title':'Engle and Russell: Autoregressive Conditional Duration','url':'https://papers.ssrn.com/sol3/papers.cfm?abstract_id=6809','use':'Search-index abstract available; direct page403; models irregular inter-event durations'},
        {'title':'Statsmodels: SARIMAX model selection and missing data','url':'https://www.statsmodels.org/stable/examples/notebooks/generated/statespace_sarimax_internet.html','use':'Official missing-observation state-space example, not a prediction-market performance result'},
    ]
    OUT.mkdir(parents=True,exist_ok=False);write(OUT/'report.json',stats);write(OUT/'literature_sources.json',sources)
    plan={
        'status':'proposed separate quote-feasibility branch; not activated or confirmatory-frozen',
        'target_candidate':'30minute future YES-book midpoint, with current midpoint persistence as the primary baseline',
        'secondary_target':'Direction or large quote movement only after a tick/spread-aware threshold is frozen; no direct comparison with old trade-target LL',
        'baseline_ladder':['current midpoint persistence','spread/depth weighted midpoint','regularized linear quote-change model','logistic imbalance for a separately defined direction target','small booster only after enough valid training episodes'],
        'initial_inputs':['midpoint','spread','best-level sizes','queue imbalance','trailing midpoint changes','quote age','trade age','feed status'],
        'feature_guards':['durable availability by decision','no smoother using future observations','no double-counted complementary liquidity','unsequenced websocket deltas cannot be called complete order flow'],
        'new_training_required':True,'reuse_selected_trade_booster_as_quote_model':False,
        'evaluation':['Chronological development then untouched prospective block','same decision keys and endpoint rules for all baselines','MAE/RMSE for midpoint forecasts','log loss/Brier only for a separately defined probabilistic label','report abstentions and missing endpoints','uncertainty by release episode and calendar dependence'],
        'before_model_fitting':['verify quote temporal continuity and market status','freeze target and quality rules','prepare training/validation split without opening protected studies','resolve labels and independent event yield'],
        'news_extension':'Add exposure/timing controls before relevance/signed evidence; no incremental-news claim yet',
    }
    write(OUT/'quote_study_proposal.json',plan)
    doc=REPO_ROOT/'EVENTX_ALTERNATIVE_FORECASTING_METHODS_20261024.md'
    text=f'''# EventX: alternative ways to use the data for forecasting

24 October2026. **Recommendation: investigate a separately versioned order-book forecasting study first.** Both-token accounting is worth fixing, but naive pooling does not solve the observed sparsity. The running collector and selected trade-based booster are unchanged.

## 1. Work actually completed

I reviewed primary research and official documentation, then ran a coverage diagnostic on **{stats['payloads_read_and_verified']:,}hash-verified payloads**. Sources were the completed22-market V03rehearsal and a separately frozen58.99-minute snapshot of the two-market expansion pilot. No model was fitted or scored, and no forward returns or labels were computed.

The diagnostic uses five-minute decision grids and only receipts durably available by each grid. Quote availability requires a received two-sided, uncrossed book no more than120seconds old. The exploratory quality screen additionally requires a spread no greater than0.05probability units and at least10tokens at each best level. These are diagnostic choices, not optimized thresholds. A fresh receipt can describe an unchanged quote; source timestamp recency is tracked separately.

### Coverage on the14macro candidates

|Measurement|Observed grid points|
|---|---:|
|Scheduled five-minute grids|{len(mainrows):,}|
|Recently received valid YES books|{allgroup['yes_book_available']:,}|
|Books passing spread/depth screen|{allgroup['yes_book_quality']:,}|
|Continuous241-minute sampled quote path passing that screen|{allgroup['quote_history240_quality']:,}|
|Those paths with positive trailing quote volatility|{allgroup['positive_quote_sigma240']:,}|

The positive-volatility quote histories cover **{stats['positive_quote_history_markets']}contracts**. Repeated rows, persistent books and overlapping histories are not independent news events. These counts do not include verified future endpoints, resolved predicate issues or release evidence, and are not forecast admissions.

### A fairer matched input comparison

The trade diagnostic uses only complete single-page six-hour receipts that were available by a grid and at most120seconds old. It deliberately does not merge the intervening shorter trade windows while execution identities remain unresolved, so it can undercount fresh trading. This leaves **{len(matched)}matched market/grid points**, rather than all4032.

|On exactly those{len(matched)}points|Count|
|---|---:|
|Canonical YES raw activity passes|{stats['matched_yes_activity_pass']}|
|Naively pooled YES+NO raw activity passes|{stats['matched_pooled_raw_activity_pass']}|
|Recently received valid YES book|{stats['yes_book_available']}|
|Book passes spread/depth screen|{stats['yes_book_quality']}|
|Four-hour quote history passes the screen|{stats['quote_history240_quality']}|
|Four-hour quote history also has positive volatility|{stats['positive_quote_sigma240']}|

This comparison supports greater **input coverage** for quotes, not superior predictive accuracy. There is no new log-loss, Brier or average-precision result.

The two new candidates had quality-screened books at all24sampled grids in their first58.99minutes; this is too short for a four-hour prospective history. Their trade-snapshot freshness screen had no qualifying grid, partly because polling and grid times do not align; do not interpret that result as proof of no trading.

## 2. Method A — Use both outcome tokens carefully

For a binary contract, a NO-side price can be expressed in YES coordinates as `1 − p_NO`. Complementary payout mechanics motivate that transformation; they do not imply that asynchronous last YES and NO trades are identical contemporaneous prices. [Official positions documentation](https://docs.polymarket.com/concepts/positions-tokens).

For quotes, a NO book implies the YES-oriented interval:

`bid_Y_from_NO = 1 − ask_NO`; `ask_Y_from_NO = 1 − bid_NO`.

A diagnostic composite uses `max(bid_Y,1−ask_NO)` and `min(ask_Y,1−bid_NO)`, only with synchronized receipts; crossed or conflicting results remain unavailable. It is a synthetic indication, not a guaranteed executable net-of-cost price. Do not sum depths that may reflect the same economic liquidity.

**What our records revealed:** the sole naive pooled activity pass was CPI>4.5% at23October17:45UTC. Each side contributed2records in the last hour; pooling produced4and crossed the minimum3screen. The two YES records and two NO records form **{pair['transaction_time_size_complement_price_pairs60m']}complementary pairs** sharing transaction,time,quantity and complemented price. Collapsing just those paired groups returns2and removes the apparent pass. Across four hours,{pair['transaction_time_size_complement_price_pairs240m']}pairs match under recorded rounding among10YES/10NOrecords in10transactions.

These rows have opposite YES-oriented directions, not identical directional actions. Exact execution deduplication still requires fill-role identity. We cannot claim that simply adding NO rows generates valid new observations. V03of the overlap report supersedes two earlier prose errors, both preserved with their original numerical results.

**Use next:** improve price measurement and signed-flow accounting; keep YES/NO availability, age and side as explicit fields. A pooled representation needs a new dataset version and compatible training.

## 3. Method B — Forecast changes in the order book

This is the strongest immediate option given measured coverage.

For best bid `b`, ask `a`, and sizes `Qb`,`Qa`, compute:

- Midpoint: `m = (a+b)/2`.
- Spread: `s = a−b`.
- Queue imbalance: `I = (Qb−Qa)/(Qb+Qa)`.
- Weighted midpoint: `w = (a·Qb+b·Qa)/(Qb+Qa)`.

Start with a **30-minute midpoint forecast**, using current midpoint persistence as baseline. Compare a regularized linear model of future midpoint change using imbalance, spread, depth and trailing quote changes. A small booster is a later candidate after valid training episodes exist. This is a new quote target; feeding midpoints into the old trade-trained booster would not be a valid substitution.

For a separate directional task, queue-imbalance logistic regression is a recognized reference: Gould and Bonart study the next midpoint move in10liquid Nasdaq stocks. Their market and horizon differ from our sparse prediction markets and30-minute task, so their reported performance is not directly comparable. [Original paper](https://arxiv.org/abs/1512.03492).

The simple weighted midpoint above is **not** Stoikov's full learned micro-price estimator, which uses order-book transition information. It is a useful low-complexity comparator before that model. [Author's implementation and paper](https://github.com/sstoikov/microprice).

Order-flow imbalance is another later feature. Cont,Kukanov and Stoikov relate price changes to supply/demand imbalance and depth in50NYSE stocks. Their impact result does not establish our forecasting gain. Full order-flow reconstruction requires sequenced additions,cancellations and executions; periodic snapshots or unverified websocket deltas cannot silently stand in for all events. [Original paper](https://arxiv.org/abs/1011.6402).

**Remaining obstacles:** quote-quality thresholds, nonexecuted/cancelled liquidity, potentially stale orders, endpoint observability, terminal status and the small number of independent events. Continuous receipt coverage is still needed even if trade activity is relaxed in a new quote study.

## 4. Method C — Model event arrivals and movement separately

An irregular market naturally has two questions: when will another observation arrive, and what will its price be? Use a duration or survival model for the next trade/quote update, then model movement conditional on an update. The Autoregressive Conditional Duration framework was designed for irregular inter-event durations. [Engle and Russell](https://papers.ssrn.com/sol3/papers.cfm?abstract_id=6809).

For a new observed-update task, write `P(update and move)=P(update)×P(move|update)`. This does not equate an unobserved price to no movement. Connection outages must be censored or flagged separately from genuine inactivity. Predicting the next event changes the horizon; use an arrival model if the final question must remain30minutes.

**Use next:** time-to-next-trade baseline, abstention/endpoint-availability forecasting, or a separately defined event-time target. Data coverage alone cannot fit or validate a dependable duration model.

## 5. Method D — State-space estimation with uncertainty

A latent log-odds process can evolve between observations while trades and quotes are noisy measurements. A Kalman-style filter can skip missing observations and propagate uncertainty. Let process variance depend on elapsed time, and measurement variance reflect spread/measurement type; estimate parameters only on training periods. Official state-space tooling supports missing observations. [Statsmodels example](https://www.statsmodels.org/stable/examples/notebooks/generated/statespace_sarimax_internet.html).

This produces an estimate with uncertainty, not an authenticated missing price. Use causal filtering, never a full-sample smoother for decision-time inputs. Preserve outage masks, and do not use imputed values as evaluation ground truth. It cannot retrospectively repair capture gaps for the frozen study.

**Use next:** estimate latent price with uncertainty after quote quality and source semantics are established. Compare against persistence before adding complexity.

## 6. Method E — Change aggregation or horizon explicitly

Trade/event/volume bars can reduce meaningless forward-filled rows. Longer60/120-minute targets may yield more observations, but they change the forecasting question, increase terminal risk and do not fix missing sources. Shortening the required history, pooling contracts hierarchically, or shrinking volatility toward a family estimate also changes training inputs. These need separate prespecification and training, with calendar/episode grouping to avoid leakage across related contracts.

I would rank these below the quote study because we already observe usable book measurements. No horizon was selected using outcome performance here.

## 7. Recommended next experiment

1. Preserve the running trade-source pilot and collect both token books with durable timestamps.
2. Freeze a separate quote task, input-quality rules, terminal checks and endpoint clock. The proposal is saved, not activated.
3. Start with midpoint persistence, weighted midpoint and regularized linear quote-change prediction. Use logistic imbalance only for a separately defined directional label.
4. Evaluate chronological held-out predictions on identical keys. Report MAE/RMSE for midpoint forecasts; use log loss/Brier only for probabilistic labels. Report coverage, missing endpoints and episode counts alongside accuracy.
5. Add exposure/timing controls and verified news only after market-only quote forecasting is viable. No incremental news value is established yet.

**Claim supported now:** our captured books provide substantially more usable *input histories* than the strict trade representation in these diagnostic windows. **Claim still untested:** whether any alternative beats persistence or the appropriate baseline prospectively.

## Evidence and integrity

- `data/v7/alternative_inputs_20261024/`: contract,4032macro-grid diagnostic,other roles,per-market statistics and payload hashes.
- `data/v7/paired_token_overlap_20261024_v03/`: corrected complementary-leg accounting interpretation.
- `data/v7/alternative_methods_report_20261024/`: matched counts,literature register and proposed quote-study design.
- Snapshot of ongoing pilot: `data/v7/expansion_source_pilot_20261024/audits/20261024T082628Z_598812/`.

Protected holdouts were not read. Existing models,collectors and manifests remain unchanged. No test suite was added or run. No outcome/performance evaluation was performed.
'''
    doc.write_text(text)
    state=REPO_ROOT/'CURRENT_STATE.md';old=state.read_text()
    (REPO_ROOT/'docs/progress/CURRENT_STATE_ARCHIVE_20261024_ALTERNATIVES.md').write_text(old)
    section=f'''## Alternative-input research (24October)

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

'''
    updated=old.replace('## Selected market model: retain raw condition_120k',section+'## Selected market model: retain raw condition_120k')
    updated=updated.replace('3. Review the new two-market six-hour capture after24Oct21:27SGT; retain failures.',
        '3. Review the new two-market capture after24Oct21:27SGT; consider separate quote-study proposal.')
    state.write_text(updated)
    with (REPO_ROOT/'docs/progress/2026-10.md').open('a') as f:f.write('\n\n## 2026-10-24 — Alternative data representations and forecasting methods\n\n'+text+'\n')
    files=list(OUT.iterdir())+[doc,Path(__file__).resolve(),SRC/'manifest.json',PAIR/'manifest.json']
    write(OUT/'manifest.json',{'files':{str(p.relative_to(REPO_ROOT)):sha(p) for p in files}})
    print(json.dumps(stats,indent=2))

if __name__=='__main__':main()
