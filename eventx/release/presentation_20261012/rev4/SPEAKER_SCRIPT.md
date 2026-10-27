# EventX: 10-minute progress presentation — revision 4

Prepared 12 October 2026; results through 12 October. Present slides 1–10; slides 11–13 are backup. Planned duration: 600 seconds. Rehearse to adjust delivery speed.

[Open the offline presentation](EVENTX_PROGRESS_PRESENTATION.html)

## Timed script

### Slide 1: EventX: market-news research progress

**0:00–0:20 (20 seconds)**

EventX asks whether external news improves short-horizon prediction-market forecasting. I will explain the rationale, our methodology and its contribution, then show the measured baseline improvements. I will finish with the remaining bottlenecks and the next research step.

Sources: [eventx/release/paper_a_20261010/TABLES.md](/Users/zhurong/UROP/eventx/release/paper_a_20261010/TABLES.md)

### Slide 2: Why study news beyond prediction-market prices?

**0:20–1:05 (45 seconds)**

Market prices express information through trading, but the chance of a large movement also depends on recent volatility and activity. News may help when it provides new evidence before adjustment is complete. A report about a specific Federal Reserve meeting could matter; a generic Fed mention might not. That is our hypothesis. To test it convincingly, we first need a strong market model. Otherwise, news could appear useful simply because the baseline fails to represent information already visible in trading.

Sources: [eventx/release/v5/PROTOCOL_V1_1.md](/Users/zhurong/UROP/eventx/release/v5/PROTOCOL_V1_1.md)

### Slide 3: Research aims and the forecast target

**1:05–1:50 (45 seconds)**

We forecast large absolute changes in canonical YES log odds over the next thirty minutes, at five-minute decision intervals. The inherited movement threshold uses trailing volatility. Our practical aim is better probability forecasts. Our scientific aim is to measure incremental information: does news add something beyond market history, article exposure and timing? Our intended paper contribution is a controlled empirical account of that question. A reliable negative result would also be informative, provided the evidence and evaluation are sufficiently strong.

Sources: [eventx/release/v5/PROTOCOL_V1_1.md](/Users/zhurong/UROP/eventx/release/v5/PROTOCOL_V1_1.md)

### Slide 4: Methodology: a controlled forecast comparison

**1:50–3:20 (90 seconds)**

The method has three parts. First, construct market features from trailing prices and executions: momentum, volatility, trade activity, notional and trade age. Compare transparent logistic regression with nonlinear trees and boosting. Boosting sequentially adds small trees that correct prediction errors and capture interactions between these conditions.

Second, introduce news in stages. Start with a market forecast, add exposure-context correction, then article timing, then relevance and content features. Compare predictions on identical market and decision-time keys. This helps distinguish improved calibration for news-exposed observations from added information in the text. The existing exposure gate uses semantic routing, so the content contrast is conditional on that selected population.

Third, train on earlier periods and score later periods with a thirty-minute purge and held-market separation. Evaluate log loss and Brier, where lower is better, and average precision, where higher is better. These development folds were previously opened, so this is research evidence rather than independent confirmation.

Sources: [eventx/release/v5/PROTOCOL_V1_1.md](/Users/zhurong/UROP/eventx/release/v5/PROTOCOL_V1_1.md), [data/v5/opened_news_offset_trial_20261009/report.json](/Users/zhurong/UROP/data/v5/opened_news_offset_trial_20261009/report.json), [data/v5/market_condition_tuning_20261012/MODEL_CARD.md](/Users/zhurong/UROP/data/v5/market_condition_tuning_20261012/MODEL_CARD.md)

### Slide 5: Where our methodological contribution lies

**3:20–4:35 (75 seconds)**

Our contribution lies in the evaluation design and the treatment of contract-specific evidence. The learner itself uses established algorithms.

The first contribution is making news compete against strong market and exposure controls. This directly tests whether an apparent gain survives a more demanding comparison. Second, we move beyond topical similarity. For a contract asking about a July rate cut of fifty basis points or more, an article must bind the relevant agency, action, quantity and period. The extractor records quoted evidence, distinguishes claim roles and abstains when binding is uncertain. This is currently a development prototype.

Third, we use conservative system availability rather than treating publication time as immediate access. Fourth, we trace articles through signed evidence, episodes and eligible forecast decisions. That funnel explains whether a failed news experiment reflects poor linking, late delivery or absent observable markets. Together these form our proposed methodological contribution; we do not claim the first framework of its kind.

Sources: [eventx/release/v7/pilot_20261010/SIGNED_EVIDENCE_V03_REPAIR_20261012.md](/Users/zhurong/UROP/eventx/release/v7/pilot_20261010/SIGNED_EVIDENCE_V03_REPAIR_20261012.md), [eventx/release/v7/pilot_20261010/EVENT_COVERAGE_AND_MISSED_EVIDENCE_20261012.md](/Users/zhurong/UROP/eventx/release/v7/pilot_20261010/EVENT_COVERAGE_AND_MISSED_EVIDENCE_20261012.md), [data/v5/opened_news_offset_trial_20261009/report.json](/Users/zhurong/UROP/data/v5/opened_news_offset_trial_20261009/report.json)

### Slide 6: Market model: 9.68% lower log loss than logistic

**4:35–5:50 (75 seconds)**

Our clearest completed result is the stronger market reference. On three hundred and sixty-four thousand nine hundred and three matched development rows, logistic regression has log loss of zero point four five one zero seven zero. The nonlinear tree scores zero point four zero seven three nine one. That is a nine point six eight percent reduction in probability-forecast loss. Brier also improves, and average precision rises from about zero point two two seven to zero point three three five.

The log-loss gain appears in all three forward folds. A plausible explanation is better representation of interactions among volatility, momentum and trading activity, although we have not isolated which feature causes the gain. The main implication for our research is that news now has a substantially stronger benchmark to beat. These are development results, not trading returns or classification accuracy.

Sources: [data/v5/no_terminal_baseline_diagnostic_20261009/report.json](/Users/zhurong/UROP/data/v5/no_terminal_baseline_diagnostic_20261009/report.json)

### Slide 7: Latest market tuning: another 0.54% lower loss

**5:50–6:55 (65 seconds)**

The latest tuning improves the already selected booster. We added nine deterministic trailing condition features, including volatility ratios, scaled momentum, trading-intensity ratios and an age-volatility interaction, and expanded the training sample to one hundred and twenty thousand rows. Nine configurations were examined. Selection used fold four and was recorded before the new fold-five fits.

On the same one hundred and twelve thousand six hundred and sixteen fold-five observations, loss falls from zero point three four four eight one six to zero point three four two nine four nine: another zero point five four percent reduction. Brier and average precision improve too. The latest model is one point seven zero percent below the earlier tree; the previous booster had been one point one seven percent below it. These percentages are separate from the previous slide and should not be added. October performance remains unmeasured.

Sources: [data/v5/market_condition_tuning_20261012/report.json](/Users/zhurong/UROP/data/v5/market_condition_tuning_20261012/report.json), [data/v5/market_condition_tuning_20261012/selection_receipt.json](/Users/zhurong/UROP/data/v5/market_condition_tuning_20261012/selection_receipt.json), [data/v5/market_learner_screen_20261009/report.json](/Users/zhurong/UROP/data/v5/market_learner_screen_20261009/report.json)

### Slide 8: Exposure correction gives the best score in this news trial

**6:55–8:10 (75 seconds)**

The news comparison demonstrates why our controls matter. On nine thousand nine hundred and sixty-five matched article-exposed rows, the market reference has log loss of zero point three three zero five nine one. Exposure-context correction lowers it to zero point three two seven five three three. Timing and semantic features improve over the original reference, but neither beats that exposure control. Semantic features are about zero point zero zero one two five four nats worse.

Comparing only against the original reference could therefore overstate the contribution of content. In another matched comparison on five thousand three hundred and eighty-eight rows, the previous selected market booster also beats the news timing model. The new condition model has not yet been compared with news on those rows. Our finding is narrow: the tested news representations have not demonstrated incremental gains against the stronger controls.

Sources: [data/v5/opened_news_offset_trial_20261009/report.json](/Users/zhurong/UROP/data/v5/opened_news_offset_trial_20261009/report.json), [data/v5/method_screen_observed_row_join_20261009/report.json](/Users/zhurong/UROP/data/v5/method_screen_observed_row_join_20261009/report.json)

### Slide 9: What we have achieved so far

**8:10–9:00 (50 seconds)**

Our nonlinear market model reduced development log loss by 9.68% relative to a logistic baseline. A further selected booster improved on an earlier tree by 1.17% in a separate comparison. Independent confirmation and incremental news gains remain outstanding.

The latest market tuning adds a further zero point five four percent improvement against that booster. Beyond performance, we have established matched comparison machinery, exposure controls and a traceable contract-evidence pipeline. We have also consolidated the empirical results into a manuscript draft. The value of this progress is a stronger forecasting benchmark and a clearer diagnosis of what external news must contribute.

Sources: [data/v5/no_terminal_baseline_diagnostic_20261009/report.json](/Users/zhurong/UROP/data/v5/no_terminal_baseline_diagnostic_20261009/report.json), [data/v5/market_learner_screen_20261009/report.json](/Users/zhurong/UROP/data/v5/market_learner_screen_20261009/report.json), [data/v5/market_condition_tuning_20261012/report.json](/Users/zhurong/UROP/data/v5/market_condition_tuning_20261012/report.json)

### Slide 10: Bottlenecks and the next research step

**9:00–10:00 (60 seconds)**

The largest market-model bottleneck is generalization. The tuning result comes from opened May-to-July data; it does not establish performance under October conditions. Next we should examine calibration, feature ablations and robustness across market states, then freeze the selected model before a separately defined confirmation.

For news, the repaired extractor retains eleven signed links from two articles, but none yields an eligible forecast observation. Better binding has removed known errors, yet usable evidence coverage remains insufficient. We need timely distinct events overlapping observable trading, followed by independent evidence review and dependence-aware inference. The existing V4 study retains its original protocol and does not confirm this newly selected model. Our progress is measured market improvement and a more informative method for testing news.

Sources: [data/v5/market_condition_tuning_20261012/report.json](/Users/zhurong/UROP/data/v5/market_condition_tuning_20261012/report.json), [eventx/release/v7/pilot_20261010/EVENT_COVERAGE_AND_MISSED_EVIDENCE_20261012.md](/Users/zhurong/UROP/eventx/release/v7/pilot_20261010/EVENT_COVERAGE_AND_MISSED_EVIDENCE_20261012.md), [eventx/release/v4/protocol.json](/Users/zhurong/UROP/eventx/release/v4/protocol.json)

### Backup slide 11: Backup: methods, features and target definition

Backup • outside the 10-minute talk

If asked about the algorithmic contribution: the current contribution is empirical evaluation and evidence diagnosis, rather than inventing gradient boosting. If asked about the label: the inherited threshold is four times a trailing one-minute standard deviation, not four thirty-minute Gaussian standard deviations. Eligibility differs by research version; the 9.68% panel deliberately uses the no-terminal development diagnostic, and should not be described as a certified active-contract population. Learned semantic representations fitted across a full discovery period are an exploratory limitation; a future study should fit them inside each forward training window.

Sources (not spoken):
/Users/zhurong/UROP/eventx/release/v5/PROTOCOL_V1_1.md
/Users/zhurong/UROP/data/v5/no_terminal_baseline_diagnostic_20261009/report.json
/Users/zhurong/UROP/eventx/release/paper_a_20261010/TABLES.md
Additional method-screen source:
/Users/zhurong/UROP/eventx/release/v5/OPENED_METHOD_SURVEY_20261009.md
LightGBM and XGBoost did not fit because the local libomp runtime was absent; report them as dependency failures, not evaluated methods.

### Backup slide 12: Backup: published performance is task-specific

Backup • outside the 10-minute talk

These values are from the primary-source versions recorded in our literature review. They use different event selection, aggregation, horizons and targets. The Prophet Arena intervals do not by themselves establish paired significance. Hindcast's retrieval improvement is against its zero-shot model, not a demonstrated advantage over contemporaneous market prices, and its outcome-based selection needs qualification. Halawi Table Three is used consistently because other table captions in that version differ. No external study in our reviewed set provides a directly matched replication of EventX's thirty-minute movement task.

Sources (not spoken):
/Users/zhurong/UROP/eventx/release/literature_baselines_20261010/evidence.json
https://arxiv.org/html/2402.18563v1
https://arxiv.org/html/2510.17638v1
https://arxiv.org/html/2607.14051v1

### Backup slide 13: Backup: evidence status and confirmation

Backup — outside main talk. The tiny score difference in the original signed-evidence trial arose with zero evaluation evidence coverage and reflects refitted controls. The repaired v0.3.3 extractor has 11 links, two articles and zero eligible observations; no new news forecast was fit. V4 remains the original frozen B3-versus-B0 study, separate from the current condition_120k market model. No confirmation or news gain is established.
