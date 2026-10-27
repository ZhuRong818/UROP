# EventX presentation: rationale, aims, achievements and baseline improvements

Revision 2, 12 October 2026. Results through 10 October.

[Updated deck](https://slidesgpt.com/view/feec53a53350)  
[Timed speaker script](SPEAKER_SCRIPT.md)

## 1. Rationale

Prediction-market prices provide the natural reference for information already reflected in trading. EventX forecasts the probability of a large movement over the next 30 minutes. Recent market behaviour may predict that movement. News might contribute if it supplies relevant evidence before prices finish adjusting.

The key question is therefore: **When does external news add predictive information beyond an effective model of market history?**

Three distinctions motivate the design:

- **Mention versus evidence.** An article mentioning the Federal Reserve can be topically related without changing the probability of a particular rate decision. A useful link must match the contract’s predicate, period and outcome definition.
- **Information versus exposure context.** Rows with recent news may have different movement rates or calibration needs. A model can improve on those rows without understanding article content.
- **Publication versus system access.** An article’s publication timestamp does not show when our pipeline could use it. Conservative availability clocks keep the forecast tied to the information accessible at decision time.

The project tests these mechanisms. It does not assume that every relevant article produces a surprise or that markets necessarily underreact.

## 2. Aims and intended result

| Aim | Research question | Intended evidence |
|---|---|---|
| Improve forecasting | Can market history support better probability forecasts than a linear baseline? | Matched loss and ranking comparisons across forward periods |
| Measure incremental news | Does news improve beyond a strong market model and exposure/timing controls? | Same-row contrasts that isolate the extra feature block |
| Understand conditions | Could verified information events predict delayed adjustment in particular market states? | A separately frozen event study with liquidity and price-freshness checks |

The intended paper is an empirical evaluation of incremental information in short-horizon prediction markets. A positive result would show a practically meaningful improvement with valid independent evidence. A negative result would need defensible uncertainty and a clear account of which representations, sources and populations it covers.

The forecast target is a large **absolute 30-minute change in canonical YES log odds**, scored at five-minute decision points. The inherited label compares the movement with four times trailing one-minute volatility. This is a movement forecast, rather than the eventual contract-resolution probability.

## 3. Methods we have tried

Market methods include L2 logistic regression, spline logistic regression, shallow histogram boosting, additional histogram-booster configurations, random forest, Extra Trees, a small MLP and CatBoost.

Logistic regression gives a transparent linear reference. Splines allow smooth nonlinear responses. Boosted trees can represent thresholds and interactions between market conditions. Histogram boosting builds successive small trees to improve the probability estimates efficiently.

Market features include price log odds, momentum over several windows, realized volatility, trading counts and notional, and trade/price age. The main 9.68% diagnostic deliberately removes scheduled-terminal inputs from both compared models.

News representations include counts, article timing, relevance, market-relative novelty, publisher diversity, cross-publisher diffusion and deterministic contract-specific signed evidence. Signed evidence supports YES or NO relative to the contract wording. It is not a measured surprise without a timestamped prior and realization.

The earlier audit completed 108 fits, including tuning and final fits. A later screen attempted 50 additional configurations, of which 45 completed both forward folds. These counts use different units and should not be added as a single model count. LightGBM and XGBoost failed to load the local OpenMP runtime and produced no fits.

The screen compares earlier training periods with later evaluation periods, purges the target horizon at boundaries and aligns predictions by market and decision time. The later choice used fold 4, but its reporting fold 5 had already been opened by earlier work. All presented gains remain exploratory.

## 4. Main achievement: a stronger market forecast

### Comparison A: linear versus nonlinear market model

**364,903 identical development rows, 1,135 markets, three forward folds.**

| Metric | Logistic reference | Nonlinear tree | Improvement |
|---|---:|---:|---:|
| Log loss, lower is better | 0.451070 | 0.407391 | 0.043679 nats per row, or 9.68% lower |
| Brier, lower is better | 0.140952 | 0.131106 | 0.009845 lower, or 6.98% lower |
| Average precision, higher is better | 0.226649 | 0.334964 | +0.108315 absolute |

Relative loss reduction is `(baseline loss − new loss) / baseline loss × 100`.

Log loss assesses the probability assigned to the observed outcome and penalizes confident errors. Brier measures squared probability error. Average precision summarizes the ranking of movement events. Improvement across all three supports progress in probability forecasting and event ranking.

Log-loss gains in folds 3, 4 and 5 are 0.041469, 0.035980 and 0.053605 nats per row. The market-balanced gain is also positive at 0.043822. This supports consistency within the development sample.

The descriptive market-cluster interval is [0.039575, 0.047682]. It does not adjust for model search, related event families or shared calendar shocks. It must not be presented as independent confirmatory significance.

**Interpretation:** nonlinear modeling improves the market reference materially on the observed development population. The experiment does not identify which feature interaction caused the gain, establish a new algorithm, or measure trading profitability.

### Comparison B: selected booster versus the earlier tree

**112,616 identical fold-5 rows; configuration selected using fold 4.**

| Metric | Earlier tree | Selected seven-leaf, 600-iteration booster | Improvement |
|---|---:|---:|---:|
| Log loss | 0.348884 | 0.344816 | 0.004068 nats per row, or 1.17% lower |
| Brier | 0.110880 | 0.109677 | 0.001203 lower |
| Average precision | 0.327323 | 0.337805 | +0.010482 absolute |

The selected configuration also improves fold-4 log loss from 0.441017 to 0.439301. Selection follows the earlier fold, but both periods belong to already opened development.

These comparisons use different samples and reference models. **Do not add 9.68% and 1.17%, or compare their absolute loss levels as a common experiment.**

## 5. News results: stronger controls change the interpretation

### Exposure, timing and semantic trial

**9,965 matched article-exposed rows across forward folds 4–5.**

| Arm | Log loss | Improvement over original market reference |
|---|---:|---:|
| Market reference | 0.330591 | — |
| Exposure-context correction | 0.327533 | +0.003058 |
| Added article timing | 0.327942 | +0.002649 |
| Timing plus semantic features | 0.328787 | +0.001804 |

The semantic arm improves over the original market reference but is **0.001254 nats worse than exposure context**. This is why the additional control matters: the original comparison alone would give a more favorable impression of content value.

The exposure correction recalibrates the market prediction within the existing news-exposed population. That population is selected by the existing association pipeline, so this does not establish a completely content-neutral selection procedure. Future exposure and timing controls should avoid using the semantic relevance decision being tested.

### Selected market versus selected news timing

**5,388 exactly matched fold-5 observations across 99 markets.**

| Metric | Selected market booster | Selected news timing arm |
|---|---:|---:|
| Log loss | 0.243727 | 0.244576 |
| Brier | 0.078230 | 0.078265 |
| Average precision | 0.355478 | 0.350656 |

The primary mean-per-row news improvement is −0.000849 nats. The descriptive interval [−0.004221, 0.002996] permits both harm and benefit. The market-balanced estimate has a different sign, emphasizing weighting sensitivity. No reliable incremental forecasting gain is demonstrated.

These results support a bounded conclusion about the tested models on opened data. They do not establish that all public information is already incorporated or that every news representation must fail.

## 6. Additional completed progress

- Built a more demanding benchmark through broad standard-method comparisons, preserving failures.
- Prepared a 120-pair macro evidence packet covering 30 articles and 66 contracts.
- Recovered resolution text for 64 of those 66 contracts and 116 of 120 review pairs, compared with none supplied by the original domain cards.
- Introduced schema v0.2 distinctions for claims, attribution, expectations and information events.
- Consolidated seven result panels in Paper A revision 2 and prepared the review package.

Rule-text coverage improves evidence preparation. It does not measure linker accuracy, establish historical metadata validity or close the human-review gate.

## 7. Bottlenecks and next steps

This discussion belongs at the end of the main presentation.

| Bottleneck | Current evidence | Next research action |
|---|---|---|
| Usable signed signal | 21/4,577 fitting rows and 0/5,388 evaluation rows contain signed evidence | Diagnose feature transport and coverage before another performance claim |
| Timeliness | Macro-pilot median publication-to-derived-availability lag is 226 minutes | Establish genuinely timely event capture; study remaining adjustment after system access |
| Contract evidence quality | Exact links are sparse and reuse articles; independent human intake remains incomplete | Obtain independent predicate/evidence review with hard negatives and episode diversity |
| Valid confirmation | Opened folds, overlapping horizons and common shocks limit inference | Repair dependence/power design and freeze a separate untouched evaluation |

The next study should examine verified information events and delayed repricing at 5, 15, 30 and 60 minutes, stratified by liquidity and trade age. Structural volatility and EWMA/GARCH are proposed benchmarks, not completed results.

V4 keeps its original B3-versus-B0 protocol and its 30 October close. Its one-shot audit/consumption sequence remains unchanged. It will not confirm every later market-model selection.

## Sources

- [Market diagnostic](/Users/zhurong/UROP/data/v5/no_terminal_baseline_diagnostic_20261009/report.json)
- [Market learner screen](/Users/zhurong/UROP/data/v5/market_learner_screen_20261009/report.json)
- [Method survey](/Users/zhurong/UROP/eventx/release/v5/OPENED_METHOD_SURVEY_20261009.md)
- [Exposure/timing/semantic trial](/Users/zhurong/UROP/data/v5/opened_news_offset_trial_20261009/report.json)
- [Exact matched news comparison](/Users/zhurong/UROP/data/v5/method_screen_observed_row_join_20261009/report.json)
- [Signed-evidence trial](/Users/zhurong/UROP/data/v7/signed_evidence_exploration_20261010/report.json)
- [Macro preparation](/Users/zhurong/UROP/eventx/release/v7/pilot_20261010/PREPARATION_RESULTS_REV2.md)
- [V5 target and design](/Users/zhurong/UROP/eventx/release/v5/PROTOCOL_V1_1.md)
- [V5 market features](/Users/zhurong/UROP/eventx/features/v5_market.py)
- [Frozen V4 protocol](/Users/zhurong/UROP/eventx/release/v4/protocol.json)

