# EventX: segment-specific forecasting research

Updated 2026-10-24T14:30:26.239676+00:00. This is an exploratory result and a frozen hypothesis for future testing.

## What we found

We tested **16 forecast variants**, including persistence, on **28 segments** defined using information available at forecast time. There were **420 nominal nonbaseline model–segment comparisons**, of which 405 had observations. Every result is retained.

One combination had a positive outer development result: a three-state hurdle model when **30-minute price momentum and current book imbalance have the same sign**.

| Measure | Persistence | Conditional model |
|---|---:|---:|
| Segment MAE | 0.000111111111 | 0.000104142605 |
| Segment RMSE | 0.000235702260 | 0.000214400221 |
| Full-population MAE, persistence outside segment | 0.000065476190 | 0.000065369530 |

The segment MAE reduction is **6.2717%**. Coverage is **9 of 588 rows (1.5306%)**, across three markets. With persistence outside the segment, the population MAE reduction is **0.1629%**.

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

A separate local observer, PID **21055**, reads the existing forecast stream. It does not change the collector, base forecasts, old trade classifier or protected evaluations. First eligible grid: **2026-10-24T14:30:00+00:00**. Scheduled stop: **2026-10-25T14:04:00+00:00**.

At the status checkpoint 2026-10-24T14:30:19.010486+00:00, the observer was running: 1 timely forecasts, 0 segment-active forecasts and 0 observed endpoints. These counts will change; current status is `data/v7/segment_candidate_20261024/status.json`.

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
