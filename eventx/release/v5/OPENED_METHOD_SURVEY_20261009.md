# Opened-data algorithm survey — 9 October 2026

## Scope and result

At the user's request, this is an adaptive search for better forecasting methods
on **already opened May–July development data**. It does not use a consumed
holdout or the frozen V4 prospective interval. Models were compared on the
same forward validation rows, with 30-minute label-horizon purges and disjoint
market IDs. Fold 4 was used for within-screen choices; fold 5 was reported
separately, but had already been opened by earlier research. All comparisons
are exploratory and post-selection.

The clearest gain is **market-only**. The fold-4-selected histogram booster
(seven leaves, 600 iterations) improved fold-5 log loss from **0.348884** for
the frozen no-terminal tree to **0.344816** on 112,616 identical rows. Brier
improved by 0.001203 and average precision rose by 0.010482. The paired
log-loss improvement was **0.004068 nats/row**; the descriptive market-cluster
interval was [0.002841, 0.005276]. It also improved fold-4 log loss from
0.441017 to 0.439301. This does not establish an independent new-data gain or
change the controlling V5 design.

The broader search still found **no stable incremental news gain**. On the
5,388 fold-5 rows with an observed recent article, the fold-4-selected
market-only booster scored 0.243727 log loss. The selected observed-news model
scored 0.244576, worse by 0.000849; the descriptive market-cluster interval
for news minus market improvement was [−0.004221, 0.002996]. Its matched
context-only correction also beat it.

## Methods screened

The existing frozen audit had already compared L2 logistic, spline logistic,
and shallow histogram boosting with market, timing, and relevance–novelty
inputs. This search added the following bounded screens. Full grids, fit
settings, failures, metrics, predictions and source hashes are retained in
the linked artifacts.

| Screen | Rows and forward split | Families and variants | Outcome |
|---|---|---|---|
| Observed-article corrections | Fold 3→4, then 3–4→5; 4,577 and 5,388 validation rows | Fixed-offset ridge at three penalties, quadratic offset, spline logistic, two histogram boosters, Extra Trees, random forest, small MLP; each with context-only, news timing, and semantic inputs | 29/30 configurations completed on both folds; the semantic quadratic arm stopped at its predeclared 150-feature budget. Selected news arm lost to selected context on fold 5. |
| Full-row market baseline | Same capped 60,000-row training rule as prior audit; 102,026 and 112,616 validation rows | Five histogram-booster configurations, Extra Trees, random forest, MLP | All eight completed; the fold-4-selected seven-leaf 600-iteration booster improved both folds over the frozen tree. |
| External market boosters | Same full-row split | Two CatBoost, two LightGBM, two XGBoost configurations | CatBoost completed. LightGBM and XGBoost could not load because the local macOS `libomp.dylib` runtime is absent; those are dependency failures, not model results. |
| CatBoost on observed articles | Same exposed-row split and context/timing/semantic tiers | Two CatBoost configurations per tier | All six completed. Timing beat context on fold 4 but lost on fold 5; neither beat the stronger selected market control. |

The method families are standard supervised tabular alternatives described in
the [scikit-learn ensemble reference](https://scikit-learn.org/stable/api/sklearn.ensemble.html),
the [XGBoost paper](https://arxiv.org/abs/1603.02754), and the
[CatBoost paper](https://arxiv.org/abs/1706.09516). This bounded screen is not
an exhaustive search over every possible learner or feature representation.

## Same-row results

The exact `(market, minute)` join between market and observed-news screens is
preserved in `data/v5/method_screen_observed_row_join_20261009/`. A preliminary
market-only key check failed because a market has many decision times; it
produced no comparison metric and was replaced by the exact two-field join.

| Fold 5, 5,388 observed-article rows | Log loss | Brier | AP |
|---|---:|---:|---:|
| Frozen no-terminal tree | 0.245673 | 0.078771 | 0.350843 |
| Selected market-only histogram booster | **0.243727** | 0.078230 | **0.355478** |
| Selected exposure-gated context offset | 0.243985 | **0.078174** | 0.350843 |
| Selected news timing offset | 0.244576 | 0.078265 | 0.350656 |

The news offset lost to context by 0.000591 log loss, with descriptive
market-cluster interval [−0.001827, 0.000731]. It lost to the new market-only
booster by 0.000849. On fold 4, it also lost to both controls: 0.428452 versus
0.426009 for context and 0.426791 for the selected market booster.

CatBoost on the full market-only frame scored 0.343900 on fold 5, the smallest
post-hoc score in that market screen. It was worse than the selected histogram
booster on fold 4 (0.440273 versus 0.439301); its fold-5 advantage of 0.000916
over that booster has a descriptive paired interval [−0.000249, 0.002110].
The post-hoc best semantic offset scored 0.243699 on observed fold-5 rows, only
0.000027 below the selected market booster, but its fold-4 log loss was 0.436313,
far worse than the 0.426009 selected context model. Neither post-hoc result
justifies promotion.

## Interpretation and next research step

The additional market-only booster appears promising on this opened historical
sample. New news timing, publisher/diffusion summaries, and relevance–novelty
features did not produce a stable gain over matched context or the stronger
market baseline. The exposure gate itself can support recalibration; that is
different from incremental article content value.

This search deliberately preserved failures and evaluated only recorded-news
rows for the news contrast, so missing source intervals were never set to zero
news. Historical feed completeness, article and market versions, event-family
independence, and the semantic representation's future-text issue remain.
Market-cluster intervals do not adjust for this adaptive model search or common
calendar shocks. No result is a V5-R freeze, independent confirmation, source
certificate, or modification of V4.

Further outcome-guided tuning on these opened folds would increase selection
bias. The next useful step is to freeze one market control and one news
comparison after source/link methods are fixed, then measure them on genuinely
unopened data. Until then, report the market-only improvement as exploratory
and the news increment as unsupported.

Primary artifacts:

- `data/v5/observed_news_method_screen_20261009/`
- `data/v5/market_learner_screen_20261009/`
- `data/v5/external_booster_screen_20261009/`
- `data/v5/catboost_observed_news_screen_20261009/`
- `data/v5/method_screen_observed_row_join_20261009/`
