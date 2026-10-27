# EventX: 10-minute progress presentation

Prepared 12 October 2026. Results through 10 October 2026.

**Structure:** 9 main slides, 3 backup slides. **Time budget:** 10:00. **Spoken script:** 1149 words, plus pauses and transitions. Rehearse once; timing is a planned budget, not a measured delivery time.

Present measured improvements first. Discuss the bottlenecks on the final main slide. Keep the evidence-status subtitles visible: exploratory results have not been independently confirmed.

## Timing

| Slide | Title | Talk time |
|---|---|---|
| 1 | EventX: market-news research progress | 0:00–0:30 |
| 2 | Predicting large price movements over the next 30 minutes | 0:30–1:35 |
| 3 | A sequence of controlled model comparisons | 1:35–2:50 |
| 4 | Nonlinear market modeling reduces log loss by 9.68% | 2:50–4:30 |
| 5 | Exposure correction outperforms added news features | 4:30–6:00 |
| 6 | Selected news timing trails the stronger market model | 6:00–7:15 |
| 7 | The contribution is a controlled test of incremental information | 7:15–8:25 |
| 8 | The next cycle targets informative events and delayed adjustment | 8:25–9:20 |
| 9 | The bottleneck is usable information at decision time | 9:20–10:00 |

## Full speaker script

### Slide 1 — EventX: market-news research progress

**0:00–0:30 (30 seconds)**

Today I will present three pieces of progress in EventX. First, we substantially improved the market-only forecasting baseline. Second, we designed comparisons that separate news exposure from the information in news. Third, these experiments give us a more precise research direction: identifying when contract-specific information adds value beyond prices. I will show the results first, then finish with the bottlenecks and how we plan to address them.

**Delivery cue:** Speak the reasoning; let the audience read the shorter slide text.

**Sources:** [eventx/release/paper_a_20261010/TABLES.md](/Users/zhurong/UROP/eventx/release/paper_a_20261010/TABLES.md)

### Slide 2 — Predicting large price movements over the next 30 minutes

**0:30–1:35 (65 seconds)**

Our task is to forecast short-term movement in prediction markets. Every five minutes, the model estimates the probability of a large absolute change in a contract’s YES price over the following thirty minutes. We express the price change in log odds and scale the movement threshold using recent volatility. This is different from forecasting the eventual YES or NO outcome. A contract can experience a large movement and still resolve either way. The inputs are market history and, when available, external news. We use conservative availability clocks so an article cannot enter a prediction before our pipeline could access it. Our main metric is log loss, which evaluates the quality of predicted probabilities. Brier score and average precision provide complementary checks.

**Delivery cue:** Speak the reasoning; let the audience read the shorter slide text.

**Sources:** [eventx/release/v5/PROTOCOL_V1_1.md](/Users/zhurong/UROP/eventx/release/v5/PROTOCOL_V1_1.md)

### Slide 3 — A sequence of controlled model comparisons

**1:35–2:50 (75 seconds)**

The research has progressed through a sequence of comparisons. We started with a linear market baseline and simple news counts. We then tested richer news representations, including relevance, novelty and publisher diffusion, while strengthening the market model itself. An important methodological step was introducing exposure and timing controls. News-covered observations can differ from other observations even if article content provides no new predictive information. That means a gain associated with news availability should not automatically be attributed to semantic content. We therefore compare increasingly informative models on matched observations. We also train on earlier periods and evaluate on later folds. The results I will show come from development data that has already been opened, so they establish measured progress and research hypotheses. Independent confirmation remains a separate stage.

**Delivery cue:** Speak the reasoning; let the audience read the shorter slide text.

**Sources:** [eventx/release/paper_a_20261010/TABLES.md](/Users/zhurong/UROP/eventx/release/paper_a_20261010/TABLES.md); [data/v5/opened_news_offset_trial_20261009/report.json](/Users/zhurong/UROP/data/v5/opened_news_offset_trial_20261009/report.json); [data/v5/method_screen_observed_row_join_20261009/report.json](/Users/zhurong/UROP/data/v5/method_screen_observed_row_join_20261009/report.json)

### Slide 4 — Nonlinear market modeling reduces log loss by 9.68%

**2:50–4:30 (100 seconds)**

The strongest numerical result is the improvement in the market-only baseline. On the same three hundred and sixty-four thousand nine hundred and three observations across one thousand one hundred and thirty-five markets, the linear model has log loss of approximately zero point four five one. The nonlinear tree model reduces this to zero point four zero seven. That is a nine point six eight percent relative reduction. The improvement is also visible in the other metrics: Brier score falls from zero point one four one to zero point one three one, and average precision increases from zero point two two seven to zero point three three five. Importantly, the log-loss gain is positive in all three forward folds. This supports a consistent development finding rather than a gain isolated to one fold. The scientific value is that market history contains useful nonlinear structure, and news should be tested against this stronger benchmark. These are exploratory results after model development; the nine point six eight percent is a measured development gain, not a confirmed out-of-sample improvement or an algorithmic novelty claim.

**Delivery cue:** Pause on the 9.68% result. Point to the three metrics; do not read every decimal.

**Sources:** [data/v5/no_terminal_baseline_diagnostic_20261009/report.json](/Users/zhurong/UROP/data/v5/no_terminal_baseline_diagnostic_20261009/report.json)

### Slide 5 — Exposure correction outperforms added news features

**4:30–6:00 (90 seconds)**

The next result is valuable because it changes how we interpret apparent news gains. On nine thousand nine hundred and sixty-five matched news-exposed observations, the original market forecast has log loss of zero point three three zero five nine one. Adding an exposure-context correction improves this to zero point three two seven five three three. Timing features also improve on the original market arm, but perform slightly worse than the exposure correction. Semantic news features reach zero point three two eight seven eight seven, which is worse than the exposure-context arm. So the best result in this comparison comes from correcting the context of news-covered observations. This is a useful finding: some apparent news benefit can arise from distribution or calibration differences rather than article meaning. It also gives us a stricter benchmark for the next experiment. To demonstrate information value, a news model should improve beyond exposure and timing controls, as well as improve against a strong market model on the same eligible population.

**Delivery cue:** Explain the ranking of the four arms before discussing the interpretation.

**Sources:** [data/v5/opened_news_offset_trial_20261009/report.json](/Users/zhurong/UROP/data/v5/opened_news_offset_trial_20261009/report.json)

### Slide 6 — Selected news timing trails the stronger market model

**6:00–7:15 (75 seconds)**

We then asked whether the selected news model could beat the stronger market model on exactly the same observations. We joined the predictions by market and decision time, giving five thousand three hundred and eighty-eight observations across ninety-nine markets in fold five. The selected market model has log loss of zero point two four three seven two seven. The selected news arm, which uses timing and an offset correction, has log loss of zero point two four four five seven six. Its Brier score and average precision are also slightly worse. The estimated news improvement is therefore negative by approximately zero point zero zero zero eight four nine nats per row. This does not establish that news can never help: uncertainty still allows both improvement and deterioration, and this is an opened development comparison. It does show that the tested timing arm has not earned an incremental-performance claim against the stronger baseline.

**Delivery cue:** Point out that both forecasts use identical observations.

**Sources:** [data/v5/method_screen_observed_row_join_20261009/report.json](/Users/zhurong/UROP/data/v5/method_screen_observed_row_join_20261009/report.json)

### Slide 7 — The contribution is a controlled test of incremental information

**7:15–8:25 (70 seconds)**

The related literature helps us identify the contribution. Research on prediction-market dynamics motivates structural volatility and GARCH-style baselines. News-assisted language-model forecasting studies show that retrieval can improve eventual-outcome forecasts. For example, Halawi and colleagues report a Brier score of zero point one four nine for the crowd and zero point one four six for a crowd-system blend in their Table Three. Those numbers are not directly comparable with our scores because the target, horizon, event population and aggregation differ. We therefore do not claim to outperform those papers. Our contribution is a controlled short-horizon evaluation: how much information does external news add once a strong market forecast, article exposure and timing are already accounted for? That question can support a useful empirical paper even if the broad news features remain unhelpful.

**Delivery cue:** Speak the reasoning; let the audience read the shorter slide text.

**Sources:** [eventx/release/literature_baselines_20261010/evidence.json](/Users/zhurong/UROP/eventx/release/literature_baselines_20261010/evidence.json); [https://pages.stern.nyu.edu/~narchak/acm_ec_paper.pdf](https://pages.stern.nyu.edu/~narchak/acm_ec_paper.pdf); [https://arxiv.org/html/2402.18563v1](https://arxiv.org/html/2402.18563v1)

### Slide 8 — The next cycle targets informative events and delayed adjustment

**8:25–9:20 (55 seconds)**

The next cycle has four steps. First, add economically motivated market benchmarks, especially structural volatility and EWMA or GARCH, rather than relying only on another generic learner. Second, build a focused set of contract-relevant events with evidence that is new and supports a clear YES or NO direction. Third, examine price adjustment after those events at five, fifteen, thirty and sixty minutes, including differences by liquidity and trade age. Fourth, freeze a separate study only after feature coverage and dependence-aware power checks. The existing V4 protocol remains unchanged, with its observation window ending on October thirtieth and its own prescribed audit sequence. That study evaluates its original news ladder; it does not independently confirm every later model we developed.

**Delivery cue:** Speak the reasoning; let the audience read the shorter slide text.

**Sources:** [eventx/release/literature_baselines_20261010/evidence.json](/Users/zhurong/UROP/eventx/release/literature_baselines_20261010/evidence.json); [eventx/release/v4/protocol.json](/Users/zhurong/UROP/eventx/release/v4/protocol.json); [data/v7/signed_evidence_exploration_20261010/report.json](/Users/zhurong/UROP/data/v7/signed_evidence_exploration_20261010/report.json)

### Slide 9 — The bottleneck is usable information at decision time

**9:20–10:00 (40 seconds)**

The main bottleneck is usable information at decision time. Our latest signed-evidence features occur in twenty-one fitting rows and zero evaluation rows, so that experiment cannot demonstrate their predictive value. Exact links are also sparse and reuse articles, while independent human review remains outstanding. Finally, shared events and overlapping targets require stronger inference before confirmation. We have improved the market benchmark and clarified the news comparison. The next step is to turn verified, timely contract evidence into measurable coverage, then test whether it predicts delayed adjustment.

**Delivery cue:** End here. Use the remaining slides only for questions.

**Sources:** [data/v7/signed_evidence_exploration_20261010/report.json](/Users/zhurong/UROP/data/v7/signed_evidence_exploration_20261010/report.json); [data/v7/macro_review_intake_20261010_distinct_ids/report.json](/Users/zhurong/UROP/data/v7/macro_review_intake_20261010_distinct_ids/report.json)

## Backup slides and question responses

### Slide 10 — Backup: methods, features and target definition

If asked about the algorithmic contribution: the current contribution is empirical evaluation and evidence diagnosis, rather than inventing gradient boosting. If asked about the label: the inherited threshold is four times a trailing one-minute standard deviation, not four thirty-minute Gaussian standard deviations. Eligibility differs by research version; the 9.68% panel deliberately uses the no-terminal development diagnostic, and should not be described as a certified active-contract population. Learned semantic representations fitted across a full discovery period are an exploratory limitation; a future study should fit them inside each forward training window.

**Sources:** [eventx/release/v5/PROTOCOL_V1_1.md](/Users/zhurong/UROP/eventx/release/v5/PROTOCOL_V1_1.md); [data/v5/no_terminal_baseline_diagnostic_20261009/report.json](/Users/zhurong/UROP/data/v5/no_terminal_baseline_diagnostic_20261009/report.json); [eventx/release/paper_a_20261010/TABLES.md](/Users/zhurong/UROP/eventx/release/paper_a_20261010/TABLES.md)

### Slide 11 — Backup: published performance is task-specific

These values are from the primary-source versions recorded in our literature review. They use different event selection, aggregation, horizons and targets. The Prophet Arena intervals do not by themselves establish paired significance. Hindcast's retrieval improvement is against its zero-shot model, not a demonstrated advantage over contemporaneous market prices, and its outcome-based selection needs qualification. Halawi Table Three is used consistently because other table captions in that version differ. No external study in our reviewed set provides a directly matched replication of EventX's thirty-minute movement task.

**Sources:** [eventx/release/literature_baselines_20261010/evidence.json](/Users/zhurong/UROP/eventx/release/literature_baselines_20261010/evidence.json); [https://arxiv.org/html/2402.18563v1](https://arxiv.org/html/2402.18563v1); [https://arxiv.org/html/2510.17638v1](https://arxiv.org/html/2510.17638v1); [https://arxiv.org/html/2607.14051v1](https://arxiv.org/html/2607.14051v1)

### Slide 12 — Backup: evidence status and confirmation

If asked whether the latest signed-evidence model improved: control log loss was 0.242828416 and augmented log loss 0.242823935, a difference of about 0.000004481 nats per row. There were zero evaluation rows with signed evidence, so the difference comes from jointly refitting control coefficients and is not evidence of a signed-news benefit. If asked about V4: its primary contrast remains B3 versus B0, with a 0.001-nat minimum improvement, a positive lower uncertainty bound and the frozen Brier guardrail. Source completeness can fail and make confirmation incomplete. The consumed OOT holdout must not be rerun; the original v1 test was also previously exposed.

**Sources:** [data/v7/signed_evidence_exploration_20261010/report.json](/Users/zhurong/UROP/data/v7/signed_evidence_exploration_20261010/report.json); [eventx/release/v4/protocol.json](/Users/zhurong/UROP/eventx/release/v4/protocol.json); [eventx/release/paper_a_20261010/TABLES.md](/Users/zhurong/UROP/eventx/release/paper_a_20261010/TABLES.md)

## Practical presentation notes

- Present slides 1–9 for the ten-minute talk; slides 10–12 are backup.
- Say “9.68% lower development log loss,” not “9.68% better accuracy.”
- Compare scores only within a matched panel. The 364,903-row, 9,965-row and 5,388-row panels describe different populations.
- The selected news arm on slide 6 is a timing arm; do not describe it as a validated signed-surprise model.
- Do not present reviewer agreement as linker accuracy or independent human validation. The recorded reviewer kind remains assistant.
- Do not present zero feature coverage as proof that contract-specific evidence cannot work.
- The proposed event study is predictive/observational; it does not establish a causal effect of news or trading profitability.

