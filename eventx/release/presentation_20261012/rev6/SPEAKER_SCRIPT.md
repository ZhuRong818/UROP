# EventX progress presentation: revision 6 speaker script

Results through 12 October 2026. Eleven main slides and three backups. Planned duration: 600 seconds. Rehearse to adjust delivery speed.

[Open the offline presentation](EVENTX_PROGRESS_PRESENTATION.html)

## Timed script

### Slide 1: EventX: market-news research progress

**0:00–0:20 (20 seconds)**

EventX asks whether external news improves short-horizon prediction-market forecasting. I will explain the rationale, our methodology and its contribution, then show the measured baseline improvements. I will finish with the remaining bottlenecks and the next research step.

Sources (not spoken):

eventx/release/paper_a_20261010/TABLES.md

### Slide 2: Why study news beyond prediction-market prices?

**0:20–0:55 (35 seconds)**

Market prices express information through trading, but the chance of a large movement also depends on recent volatility and activity. News may help when it provides new evidence before adjustment is complete. A report about a specific Federal Reserve meeting could matter; a generic Fed mention might not. That is our hypothesis. To test it convincingly, we first need a strong market model. Otherwise, news could appear useful simply because the baseline fails to represent information already visible in trading.

Sources (not spoken):

eventx/release/v5/PROTOCOL_V1_1.md

### Slide 3: Research aims and the forecast target

**0:55–1:30 (35 seconds)**

We forecast large absolute changes in canonical YES log odds over the next thirty minutes, at five-minute decision intervals. The inherited movement threshold uses trailing volatility. Our practical aim is better probability forecasts. Our scientific aim is to measure incremental information: does news add something beyond market history, article exposure and timing? Our intended paper contribution is a controlled empirical account of that question. A reliable negative result would also be informative, provided the evidence and evaluation are sufficiently strong.

Sources (not spoken):

eventx/release/v5/PROTOCOL_V1_1.md

### Slide 4: Methodology: a controlled forecast comparison

**1:30–2:25 (55 seconds)**

The method has three parts. First, construct market features from trailing prices and executions: momentum, volatility, trade activity, notional and trade age. Compare transparent logistic regression with nonlinear trees and boosting. Boosting sequentially adds small trees that correct prediction errors and capture interactions between these conditions.

Second, introduce news in stages. Start with a market forecast, add exposure-context correction, then article timing, then relevance and content features. Compare predictions on identical market and decision-time keys. This helps distinguish improved calibration for news-exposed observations from added information in the text. The existing exposure gate uses semantic routing, so the content contrast is conditional on that selected population.

Third, train on earlier periods and score later periods with a thirty-minute purge and held-market separation. Evaluate log loss and Brier, where lower is better, and average precision, where higher is better. These development folds were previously opened, so this is research evidence rather than independent confirmation.

Sources (not spoken):

eventx/release/v5/PROTOCOL_V1_1.md
data/v5/opened_news_offset_trial_20261009/report.json
data/v5/market_condition_tuning_20261012/MODEL_CARD.md

### Slide 5: Where our methodological contribution lies

**2:25–3:25 (60 seconds)**

Our contribution lies in the evaluation design and the treatment of contract-specific evidence. The learner itself uses established algorithms.

The first contribution is making news compete against strong market and exposure controls. This directly tests whether an apparent gain survives a more demanding comparison. Second, we move beyond topical similarity. For a contract asking about a July rate cut of fifty basis points or more, an article must bind the relevant agency, action, quantity and period. The extractor records quoted evidence, distinguishes claim roles and abstains when binding is uncertain. This is currently a development prototype.

Third, we use conservative system availability rather than treating publication time as immediate access. Fourth, we trace articles through signed evidence, episodes and eligible forecast decisions. That funnel explains whether a failed news experiment reflects poor linking, late delivery or absent observable markets. Together these form our proposed methodological contribution; we do not claim the first framework of its kind.

Sources (not spoken):

eventx/release/v7/pilot_20261010/SIGNED_EVIDENCE_V03_REPAIR_20261012.md
eventx/release/v7/pilot_20261010/EVENT_COVERAGE_AND_MISSED_EVIDENCE_20261012.md
data/v5/opened_news_offset_trial_20261009/report.json

### Slide 6: How our selected market model works

**3:25–4:30 (65 seconds)**

Our selected market model uses histogram gradient boosting, an established learning algorithm. Every five minutes, we construct thirteen base market features from trailing execution history and add nine condition features. Examples include volatility ratios, momentum divided by volatility, trading-intensity ratios and a trade-age interaction. These describe the state of the market when we make the decision.

The learner groups numerical values into bins to find efficient tree splits. It adds small decision trees sequentially, correcting the errors of its current combined forecast. This allows feature interactions: the effect of momentum can depend on volatility or activity. Our configuration has six hundred boosting iterations and at most seven leaves per tree, trained on one hundred and twenty thousand earlier observations.

The output is the probability of a large absolute log-odds movement within thirty minutes. It does not predict movement direction or final contract resolution. Our work adapts the features, settings and evaluation. We selected the configuration using fold four.

Sources (not spoken):

data/v5/market_condition_tuning_20261012/MODEL_CARD.md
eventx/tasks/tune_v5_market_conditions_20261012.py
data/v5/market_condition_tuning_20261012/report.json

### Slide 7: Market model: 9.68% lower log loss than logistic

**4:30–5:30 (60 seconds)**

Our clearest completed result is the stronger market reference. On three hundred and sixty-four thousand nine hundred and three matched development rows, logistic regression has log loss of zero point four five one zero seven zero. The nonlinear tree scores zero point four zero seven three nine one. That is a nine point six eight percent reduction in probability-forecast loss. Brier also improves, and average precision rises from about zero point two two seven to zero point three three five.

The log-loss gain appears in all three forward folds. A plausible explanation is better representation of interactions among volatility, momentum and trading activity, although we have not isolated which feature causes the gain. The main implication for our research is that news now has a substantially stronger benchmark to beat. These are development results, not trading returns or classification accuracy.

Sources (not spoken):

data/v5/no_terminal_baseline_diagnostic_20261009/report.json

### Slide 8: Latest market tuning: another 0.54% lower loss

**5:30–6:35 (65 seconds)**

The latest tuning improves the already selected booster. We added nine deterministic trailing condition features, including volatility ratios, scaled momentum, trading-intensity ratios and an age-volatility interaction, and expanded the training sample to one hundred and twenty thousand rows. Nine configurations were examined. Selection used fold four and was recorded before the new fold-five fits.

On the same one hundred and twelve thousand six hundred and sixteen fold-five observations, loss falls from zero point three four four eight one six to zero point three four two nine four nine: another zero point five four percent reduction. Brier and average precision improve too. The latest model is one point seven zero percent below the earlier tree; the previous booster had been one point one seven percent below it. These percentages are separate from the previous slide and should not be added. October performance remains unmeasured.

Sources (not spoken):

data/v5/market_condition_tuning_20261012/report.json
data/v5/market_condition_tuning_20261012/selection_receipt.json
data/v5/market_learner_screen_20261009/report.json

### Slide 9: Measured market and news performance

**6:35–8:20 (105 seconds)**

The evaluated news model is a regularized correction to an earlier market tree's probability, not a language model. It starts with the tree forecast, converts it to log odds, adds a learned correction from recent articles and converts the result back to a probability.

Its selected timing tier uses article counts over five, fifteen and thirty minutes, time since the latest available article, distinct publishers and publisher diffusion. It does not read whether the story supports YES or NO. We trained candidate corrections on earlier observations, compared linear offsets with several penalty strengths and nonlinear methods, then selected the lowest log-loss news candidate using fold four. The selected model is a linear logistic offset with an L2 penalty of zero point one. The feature scaling is fitted on training rows.

This table scores that selected model against the previously selected market booster on five thousand three hundred and eighty-eight identical fold-five rows. News log loss is zero point two four four five seven six versus zero point two four three seven two seven for market only: about zero point zero zero zero eight four nine worse. Brier and average precision also favor the market booster. This is an exploratory comparison with uncertainty spanning improvement and deterioration.

The news correction was built on an earlier tree, while the stronger booster was joined afterward for comparison. Our latest condition model has not yet been combined with news. The newer contract-specific and relaxed context features have not produced a new forecasting result.

Sources (not spoken):

eventx/tasks/screen_v5_observed_news_methods_20261009.py
data/v5/observed_news_method_screen_20261009/report.json
data/v5/method_screen_observed_row_join_20261009/report.json
data/v5/opened_news_offset_trial_20261009/report.json
data/v7/relaxed_policy_context_v04_1_20261012/report.json

### Slide 10: What we have achieved so far

**8:20–9:00 (40 seconds)**

Our nonlinear market model reduced development log loss by 9.68% relative to a logistic baseline. A further selected booster improved on an earlier tree by 1.17% in a separate comparison. Independent confirmation and incremental news gains remain outstanding.

The latest market tuning adds a further zero point five four percent improvement against that booster. Beyond performance, we have established matched comparison machinery, exposure controls and a traceable contract-evidence pipeline. We have also consolidated the empirical results into a manuscript draft. The value of this progress is a stronger forecasting benchmark and a clearer diagnosis of what external news must contribute.

Sources (not spoken):

data/v5/no_terminal_baseline_diagnostic_20261009/report.json
data/v5/market_learner_screen_20261009/report.json
data/v5/market_condition_tuning_20261012/report.json

### Slide 11: Bottlenecks and the next research step

**9:00–10:00 (60 seconds)**

The market-model priority is generalization. Our gains come from opened May-to-July observations, so we need calibration and feature ablations, followed by a separately frozen evaluation of current conditions.

For news, the strict repaired extractor still yields zero eligible signed-evidence observations. A separate relaxed policy-context version now reaches one hundred and forty-four distinct articles and one thousand and fifty-six existing decision rows within thirty minutes of system availability. We prepared one hundred articles for review. This is unsigned contextual coverage, not demonstrated predictive information.

Most coverage lies in earlier folds. The latest fold has only six articles covering seventeen rows. Next we must review material relevance, distinguish commentary and repeated expectations, identify event episodes and compare contextual features against strong market and exposure-timing controls. The original V4 protocol remains frozen. Our established progress is improved historical market forecasts and a clearer evidence pipeline.

Sources (not spoken):

data/v7/relaxed_policy_context_v04_1_20261012/report.json
eventx/release/v7/pilot_20261010/SIGNED_EVIDENCE_V03_REPAIR_20261012.md
eventx/release/v4/protocol.json

### Backup slide 12: Backup: methods, features and target definition

Backup — outside the timed talk.

If asked how the evaluated news model works: its offset equation is sigmoid(logit(earlier market-tree probability) + intercept + weighted article features). The six article features are 30-minute count, latest article age, 5- and 15-minute counts, distinct publishers and maximum diffusion. Linear coefficients minimize log loss with L2 penalty 0.1. The selected arm uses timing and coverage, not semantic content or signed direction. Fold 4 selected the method; fold 5 reports performance on matched rows. Feature scaling is fitted on earlier training rows. Candidate families also included quadratic offset, splines, histogram boosting, bagged trees and a small neural network. These are established algorithms.

If asked about semantic news: relevance, novelty and their combinations were screened separately. The repaired exact-predicate extractor and the relaxed unsigned policy-context version are later development work. Neither has shown forecasting lift. The latest condition_120k market booster has not been paired with these news features on the reported rows.

Sources (not spoken):
eventx/tasks/screen_v5_observed_news_methods_20261009.py
data/v5/observed_news_method_screen_20261009/report.json
data/v5/method_screen_observed_row_join_20261009/report.json
eventx/release/v7/pilot_20261010/RELAXED_POLICY_CONTEXT_20261012.md

### Backup slide 13: Backup: published performance is task-specific

Backup • outside the 10-minute talk

These values are from the primary-source versions recorded in our literature review. They use different event selection, aggregation, horizons and targets. The Prophet Arena intervals do not by themselves establish paired significance. Hindcast's retrieval improvement is against its zero-shot model, not a demonstrated advantage over contemporaneous market prices, and its outcome-based selection needs qualification. Halawi Table Three is used consistently because other table captions in that version differ. No external study in our reviewed set provides a directly matched replication of EventX's thirty-minute movement task.

Sources (not spoken):
/Users/zhurong/UROP/eventx/release/literature_baselines_20261010/evidence.json
https://arxiv.org/html/2402.18563v1
https://arxiv.org/html/2510.17638v1
https://arxiv.org/html/2607.14051v1

### Backup slide 14: Backup: evidence status and confirmation

Backup — outside main talk. The tiny score difference in the original signed-evidence trial arose with zero evaluation evidence coverage and reflects refitted controls. The repaired v0.3.3 extractor has 11 links, two articles and zero eligible observations; no new news forecast was fit. V4 remains the original frozen B3-versus-B0 study, separate from the current condition_120k market model. No confirmation or news gain is established.
