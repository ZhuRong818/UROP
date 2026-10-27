"""Publish exploratory gains with selection history, coverage and forward status."""
import json
from pathlib import Path
from eventx.tasks.discover_v7_direct_pilot_20261022 import REPO_ROOT,now,sha,write,verify_originals

def main():
    verify_originals();base=REPO_ROOT/'data/v7/segment_research_20261024';live=REPO_ROOT/'data/v7/segment_candidate_20261024'
    out=base/'delivery';out.mkdir(exist_ok=False)
    manifests=[base/'manifest.json',REPO_ROOT/'eventx/release/v7/segment_candidate_20261024/implementation_manifest.json']
    for path in manifests:
        m=json.loads(path.read_text())
        for p,h in m.get('locked_files',m.get('files',{})).items():
            if sha(REPO_ROOT/p)!=h:raise RuntimeError('Result lock mismatch')
    report=json.loads((base/'report.json').read_text());ledger=[json.loads(l) for l in (base/'outer_discovery_search.jsonl').read_text().splitlines()]
    positive=[r for r in ledger if r['outer']['mae_gain']>1e-15]
    winner=next(r for r in positive if r['model']=='hurdle_mean' and r['segment']=='momentum_imbalance_aligned');w=winner['outer']
    pred=[json.loads(l) for l in (base/'outer_predictions.jsonl').read_text().splitlines()]
    segment=[r for r in pred if 'momentum_imbalance_aligned' in r['segments']]
    changes=[r for r in segment if abs(r['target_midpoint']-r['current_midpoint'])>1e-12]
    all_mae=report['outer_full_baseline']['mae'];pop=w['whole_population_with_persistence_elsewhere']['mae'];pop_gain=(all_mae-pop)/all_mae
    status=json.loads((live/'status.json').read_text());contract=json.loads((live/'run_contract.json').read_text());at=now().isoformat()
    for name,value in [('forward_status',status),('forward_contract',contract),('segment_rows',segment),('winner',winner)]:write(out/(name+'.json'),value)
    summary={'at':at,'model_variants':16,'segments':28,'nominal_comparisons':420,'nonempty_comparisons':405,
        'inner_selected':'persistence','positive_outer_pairs_any_support':len(positive),'winner':winner,
        'whole_population_relative_mae_reduction':pop_gain,'changed_rows_markets':len({r['market_id'] for r in changes}),
        'changed_row_grids':[r['grid_at'] for r in changes],'forward_status':status,
        'claim':'Exploratory conditional gain only; post-selected9rows; not independent confirmation'}
    write(out/'summary.json',summary)
    path=REPO_ROOT/'EVENTX_SEGMENT_FORECAST_RESEARCH_20261024.md'
    text=f'''# EventX: segment-specific forecasting research

Updated {at}. This is an exploratory result and a frozen hypothesis for future testing.

## What we found

We tested **16 forecast variants**, including persistence, on **28 segments** defined using information available at forecast time. There were **420 nominal nonbaseline model–segment comparisons**, of which 405 had observations. Every result is retained.

One combination had a positive outer development result: a three-state hurdle model when **30-minute price momentum and current book imbalance have the same sign**.

| Measure | Persistence | Conditional model |
|---|---:|---:|
| Segment MAE | {w['baseline']['mae']:.12f} | {w['candidate']['mae']:.12f} |
| Segment RMSE | {w['baseline']['rmse']:.12f} | {w['candidate']['rmse']:.12f} |
| Full-population MAE, persistence outside segment | {all_mae:.12f} | {pop:.12f} |

The segment MAE reduction is **{100*w['relative_mae_reduction']:.4f}%**. Coverage is **9 of 588 rows ({100*w['coverage']:.4f}%)**, across three markets. With persistence outside the segment, the population MAE reduction is **{100*pop_gain:.4f}%**.

This is **not a validated baseline-beating method**. The rule was selected after examining already-exposed development results. Only two of the nine target midpoints changed; both are the same market, with decisions five minutes apart and overlapping target windows. They are not two independent events. The seven unchanged rows also remain in the segment score.

## What the stronger selection check said

The training data contain 605 complete short-history observations. We generated 365 forward predictions using three expanding training windows, with training endpoints separated from each subsequent prediction window by a 30-minute embargo. Model fitting and feature scaling use each window's training rows only.

Before computing this run's outer rankings, the selection rule required at least 50 inner rows, three markets, 10% coverage and positive gains in at least two inner windows with sufficient support. **No candidate passed. The selected policy remained persistence.** These underlying data were already exposed in earlier work, so even the chronological check is exploratory rather than a fresh holdout.

The 6.27% discovery fails that stability check and the descriptive 20-row support screen. It is retained as a hypothesis because it has a deployable, pre-outcome rule. The screens were not weakened to promote it.

## Models and segments tried

- Five weighted-midpoint adjustment strengths: 0.01, 0.05, 0.1, 0.25 and 1.
- Five- and 30-minute momentum and reversion rules.
- Standardized ridge regression with penalties 10, 100 and 1000.
- Small histogram boosters with squared-error and absolute-error objectives.
- A three-state hurdle model, plus persistence as the common reference.

Segments include spread, depth, imbalance strength, price level, source-message age, recent volatility, recent momentum and fixed combinations of these states. No segment is defined by a future price change, eventual correctness or market identity. Metrics use identical rows for the candidate and persistence. Poorly performing segments remain in the complete search ledger.

## The retained candidate

Let m be the current midpoint, I the best-level size imbalance, and M the midpoint change over the previous 30 minutes. The candidate applies only when M × I > 10⁻¹² and the frozen short-history input requirements pass.

The model uses standardized current-book and short-history features to estimate probabilities of DOWN, UNCHANGED and UP with regularized multinomial logistic regression (C = 0.1). It multiplies those probabilities by the mean price change for each class learned from training data:

`predicted midpoint = clip(m + Σ P(class | features) × training_mean_change(class), 0, 1)`

Outside the segment, or without a valid 30-minute feature history, the policy returns persistence. Existing current-book and status checks still apply. This is a conventional conditional forecasting approach, not a claim of a new learning algorithm.

The exact 605-row fitted model is serialized. Its exported predictor reproduces the discovered policy on all 588 development rows with maximum absolute difference **0.0**. This is an export check, not another validation result.

## Forward check already started

A separate local observer, PID **{status['pid']}**, reads the existing forecast stream. It does not change the collector, base forecasts, old trade classifier or protected evaluations. First eligible grid: **{contract['first_grid_at']}**. Scheduled stop: **{contract['stop_at']}**.

At the status checkpoint {status['at']}, the observer was {status['phase']}: {status['timely_forecasts']} timely forecasts, {status['segment_active_forecasts']} segment-active forecasts and {status['observed_endpoints']} observed endpoints. These counts will change; current status is `data/v7/segment_candidate_20261024/status.json`.

Both the original forecast and the new candidate must be committed by decision time + 30 seconds. The observer only consumes endpoints belonging to its own timely forecasts. There is no backdated selection or live tuning. At completion it reports both the segment comparison and the population policy with persistence elsewhere. If the segment never occurs, that is zero usable segment evidence, not a win.

The current forward source covers only two markets. It can check operation and yield, but may not reproduce the historical segment; more independent market dates and event episodes remain necessary for a robust result.

## How to present this accurately

> We explored conditional forecasting across 28 observable market states. One momentum–imbalance segment showed a 6.27% development MAE reduction versus persistence, but it covered only nine observations and did not pass our temporal stability screen. We have frozen the rule for a prospective check. Reliable baseline superiority remains unconfirmed.

Do not describe the 6.27% result as an overall forecasting improvement, statistical significance, independent validation or an effect of news. Its full-population development gain is only about 0.16%, before accounting for selection optimism.

Searching segments is legitimate model development. Selecting favorable evaluation segments and then treating those same scores as independent evidence introduces selection bias; the distinction is illustrated in the [scikit-learn model-selection documentation](https://scikit-learn.org/1.7/auto_examples/model_selection/plot_nested_cross_validation_iris.html).

## Reproducible evidence

- Frozen search policy and implementation: `eventx/release/v7/segment_research_20261024/`.
- Every inner and outer comparison, fold definitions and predictions: `data/v7/segment_research_20261024/`.
- Selection recorded before outer scoring: `data/v7/segment_research_20261024/selection_before_outer.json`.
- Nine selected rows and checkpoint: `data/v7/segment_research_20261024/delivery/`.
- Exact prospective hypothesis and model: `eventx/release/v7/segment_candidate_20261024/`.
- Forward journal, status and eventual completion report: `data/v7/segment_candidate_20261024/`.
'''
    path.write_text(text)
    state=REPO_ROOT/'CURRENT_STATE.md';s=state.read_text()
    s=s.replace('- Exact candidate exported with588-row parity; separate future observer being activated.',
        f'- Exact candidate exported with588-row parity (maxdifference0);future observerPID{status["pid"]} RUNNING.\n  Firstgrid24Oct14:30UTC,stop25Oct14:04UTC;checkpoint{status["at"]}:\n  {status["timely_forecasts"]}timely/{status["segment_active_forecasts"]}segment-active/{status["observed_endpoints"]}observed endpoints.\n  Report:`EVENTX_SEGMENT_FORECAST_RESEARCH_20261024.md`;delivery in segment_research_20261024/delivery/.')
    s=s.replace('1. Monitor current source and memory-tier forecast jobs; use the freshness-checking CLI below.',
        '1. Monitor source, memory-tier forecast and separate fixed segment-candidate observer; no live retuning.')
    state.write_text(s)
    with (REPO_ROOT/'docs/progress/2026-10.md').open('a') as f:
        f.write(f'\n\n### 2026-10-24 — segment hypothesis forward activation and report\n\nObserverPID{status["pid"]} registered14:28UTC;firstgrid14:30UTC,stop25Oct14:04UTC. Source5099/base8023 verified alive14:28UTC. No existing service changes. Frozen hypothesis selected post hoc from420nominal comparisons;9rows/3markets,2changed rows on same market at02:20/02:25UTC with overlapping targets. Segment baseline MAE{w["baseline"]["mae"]},candidate{w["candidate"]["mae"]};relative reduction{w["relative_mae_reduction"]};coverage{w["coverage"]}. Whole588-row fallback MAE{pop} vs baseline{all_mae};relative reduction{pop_gain}. No stable inner selection;not confirmation. Export parity588rows,maxdifference0. Status at{status["at"]}:{status["timely_forecasts"]}timely/{status["segment_active_forecasts"]}active/{status["observed_endpoints"]}endpoints. Full report `EVENTX_SEGMENT_FORECAST_RESEARCH_20261024.md`,all outcomes retained.\n')
    paths=list(out.iterdir())+manifests+[path,Path(__file__).resolve()];write(out/'manifest.json',{'files':{str(p.relative_to(REPO_ROOT)):sha(p) for p in paths}})
    print(json.dumps({'report':str(path.relative_to(REPO_ROOT)),'relative_segment_gain':w['relative_mae_reduction'],'population_gain':pop_gain,'forward_status':status},indent=2))

if __name__=='__main__':main()
