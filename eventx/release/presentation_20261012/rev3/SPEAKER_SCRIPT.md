# EventX progress presentation: revised 10-minute script

Revision 3, prepared 12 October 2026. Results through 10 October. Present slides 1–9; slides 10–12 are backup. Planned talk: **600 seconds**, **1223 spoken words**. Allow pauses on the result tables and rehearse once to confirm delivery speed.

[Open the updated slide deck](https://slidesgpt.com/view/feec53a53350)

## Timing

| Slide | Topic | Talk time |
|---|---|---|
| 1 | EventX: market-news research progress | 0:00–0:20 |
| 2 | Why study news beyond prediction-market prices? | 0:20–1:25 |
| 3 | Research aims and the forecast target | 1:25–2:30 |
| 4 | Methods and baseline comparison design | 2:30–3:45 |
| 5 | Market model: 9.68% lower log loss than logistic | 3:45–5:30 |
| 6 | Selected booster: a further 1.17% lower log loss | 5:30–6:35 |
| 7 | Exposure correction gives the best score in this news trial | 6:35–8:05 |
| 8 | What we have achieved so far | 8:05–9:05 |
| 9 | Bottlenecks and the next research step | 9:05–10:00 |

## Main talk

### Slide 1: EventX: market-news research progress

**0:00–0:20 (20 seconds)**

EventX studies whether external news improves short-horizon prediction-market forecasts. Today I will explain why that question matters, what we set out to measure, and what we have achieved. Our clearest result is a stronger market baseline. I will then explain the news comparisons and finish with the remaining bottlenecks.

**What the audience should understand:** The central question is the incremental value of news beyond a strong market reference.

**Sources:** [eventx/release/paper_a_20261010/TABLES.md](/Users/zhurong/UROP/eventx/release/paper_a_20261010/TABLES.md)

### Slide 2: Why study news beyond prediction-market prices?

**0:20–1:25 (65 seconds)**

Prediction-market prices are a natural starting point because they reflect information expressed through trading. But our forecast asks about the chance of a large movement over the next thirty minutes. Recent price behaviour can help predict that movement, and external information might help if it arrives before adjustment is complete. Consider a contract about a particular Federal Reserve meeting. A report with new evidence about that meeting could matter, while an article that merely mentions the Federal Reserve may contain no useful update. That is an illustrative hypothesis, rather than a finding from our experiments. The research rationale is to measure what news adds after market history has already been used effectively. A weak baseline could make redundant news look useful. Improving the market model is therefore essential to a convincing test of incremental information.

**What the audience should understand:** The rationale depends on news containing timely, contract-specific information that prices have not yet absorbed.

**Sources:** [eventx/release/v5/PROTOCOL_V1_1.md](/Users/zhurong/UROP/eventx/release/v5/PROTOCOL_V1_1.md); [eventx/release/v5/OPENED_METHOD_SURVEY_20261009.md](/Users/zhurong/UROP/eventx/release/v5/OPENED_METHOD_SURVEY_20261009.md)

### Slide 3: Research aims and the forecast target

**1:25–2:30 (65 seconds)**

We have three aims. The first is practical: improve the forecast of large short-term movements using information available when the decision is made. The second is scientific: determine whether news contributes additional predictive information beyond a strong market model and controls for article exposure and timing. The third is to understand the conditions under which information might help, such as a genuinely new contract-relevant event or slow adjustment in a thinly traded market. The target is an absolute change in YES log odds over the next thirty minutes, evaluated every five minutes. We scale the movement threshold using recent volatility. The intended paper result is a controlled empirical account of incremental information. A well-supported finding that the tested news features add little can still answer the research question.

**What the audience should understand:** The intended contribution combines better forecasting with a controlled empirical answer about information value.

**Sources:** [eventx/release/v5/PROTOCOL_V1_1.md](/Users/zhurong/UROP/eventx/release/v5/PROTOCOL_V1_1.md); [MARKET_NEWS_PAPER_A_DRAFT_20261010_REV2.md](/Users/zhurong/UROP/MARKET_NEWS_PAPER_A_DRAFT_20261010_REV2.md)

### Slide 4: Methods and baseline comparison design

**2:30–3:45 (75 seconds)**

We began with L2 logistic regression, which gives a transparent linear reference. We then examined spline models and nonlinear tree methods. The broader screen also included random forests, Extra Trees, a small neural network and CatBoost. For news, we tried article counts, timing, relevance, novelty and publisher diffusion, then explored signed evidence tied to contract predicates. The key design choice is to compare predictions on the same market and decision time. We train on earlier periods and score later folds, with separation around the thirty-minute target horizon. Log loss measures the quality of probability forecasts and penalizes confidently wrong predictions. Brier measures squared probability error. Average precision measures how well the model ranks movement events. Lower loss together with better ranking is more persuasive than one metric alone. These are opened development comparisons, so their results guide research while independent confirmation remains separate.

**What the audience should understand:** Algorithms and controls answer different questions; metrics must use identical rows within each comparison.

**Sources:** [eventx/release/v5/OPENED_METHOD_SURVEY_20261009.md](/Users/zhurong/UROP/eventx/release/v5/OPENED_METHOD_SURVEY_20261009.md); [eventx/release/v5/PROTOCOL_V1_1.md](/Users/zhurong/UROP/eventx/release/v5/PROTOCOL_V1_1.md); [data/v5/no_terminal_baseline_diagnostic_20261009/report.json](/Users/zhurong/UROP/data/v5/no_terminal_baseline_diagnostic_20261009/report.json)

### Slide 5: Market model: 9.68% lower log loss than logistic

**3:45–5:30 (105 seconds)**

Our largest measured gain comes from improving the market model. On exactly the same three hundred and sixty-four thousand nine hundred and three development rows across one thousand one hundred and thirty-five markets, logistic regression scores about zero point four five one in log loss. The nonlinear tree model scores about zero point four zero seven. Subtracting the new loss from the baseline loss and dividing by the baseline gives a nine point six eight percent reduction. This percentage describes probability-forecast loss, rather than classification accuracy. Brier score also improves by about six point nine eight percent, while average precision rises by zero point one zero eight in absolute terms. The log-loss gain is positive in all three forward folds. That makes the pattern more convincing than a gain confined to one period. A plausible reason is that nonlinear models capture interactions between market conditions, such as volatility and recent trading, that a linear model represents less flexibly. We have not isolated a causal contribution from each feature. What we have achieved is a materially stronger development benchmark against which news must now prove useful.

**What the audience should understand:** The main measured performance gain improves probability quality and movement-event ranking across three periods.

**Sources:** [data/v5/no_terminal_baseline_diagnostic_20261009/report.json](/Users/zhurong/UROP/data/v5/no_terminal_baseline_diagnostic_20261009/report.json)

### Slide 6: Selected booster: a further 1.17% lower log loss

**5:30–6:35 (65 seconds)**

We also improved an already nonlinear baseline in the later method screen. The selected histogram gradient booster uses small seven-leaf trees and six hundred boosting iterations. It builds successive trees to improve the probability estimates while limiting tree complexity. We selected this configuration using fold four, then reported it on fold five. On one hundred and twelve thousand six hundred and sixteen matched rows, log loss falls from zero point three four eight eight eight four to zero point three four four eight one six. That is a further one point one seven percent reduction against the earlier tree. Brier and average precision improve as well, and the model also improves in fold four. This is a separate sample and comparison from the previous slide. The percentages should not be added, and fold five had already been opened in earlier research.

**What the audience should understand:** The later selected booster gives an additional gain against an earlier tree on a separate sample.

**Sources:** [data/v5/market_learner_screen_20261009/report.json](/Users/zhurong/UROP/data/v5/market_learner_screen_20261009/report.json); [eventx/release/v5/OPENED_METHOD_SURVEY_20261009.md](/Users/zhurong/UROP/eventx/release/v5/OPENED_METHOD_SURVEY_20261009.md)

### Slide 7: Exposure correction gives the best score in this news trial

**6:35–8:05 (90 seconds)**

The news experiments show why the baseline definition matters. On nine thousand nine hundred and sixty-five matched article-exposed rows, the market reference has log loss of zero point three three zero five nine one. An exposure-context correction improves this to zero point three two seven five three three, a gain of about zero point zero zero three zero five eight nats per row. This correction recalibrates the market forecast for observations covered by news. Timing features and semantic features both improve over the original reference, but neither beats the exposure-context arm. Semantic features are about zero point zero zero one two five four nats worse than that control. If we compared only against the original reference, we could attribute the improvement too readily to news content. The stronger control changes the interpretation: the tested content has not demonstrated an additional gain. In a separate exact comparison on five thousand three hundred and eighty-eight rows, the selected market booster also beats the selected news timing arm. This is a completed, informative result about the value of the tested representations, with broader conclusions reserved for independent evidence.

**What the audience should understand:** A feature can beat the original reference yet fail to beat the stronger exposure control.

**Sources:** [data/v5/opened_news_offset_trial_20261009/report.json](/Users/zhurong/UROP/data/v5/opened_news_offset_trial_20261009/report.json); [data/v5/method_screen_observed_row_join_20261009/report.json](/Users/zhurong/UROP/data/v5/method_screen_observed_row_join_20261009/report.json)

### Slide 8: What we have achieved so far

**8:05–9:05 (60 seconds)**

Our nonlinear market model reduced development log loss by 9.68% relative to a logistic baseline. A further selected booster improved on an earlier tree by 1.17% in a separate comparison. Independent confirmation and incremental news gains remain outstanding. The gains come from different comparison populations and should not be added. The first comparison contains 364,903 matched development rows. The booster comparison contains 112,616 matched fold-five rows. We also made the news comparison more demanding by controlling exposure and matching predictions exactly. Recovered resolution text now covers 116 of 120 macro review pairs, improving the review context. Paper A revision two consolidates the results and their limitations. Together, these achievements give us a stronger benchmark and a clearer basis for the next experiment.

**What the audience should understand:** Development gains are measured against named internal baselines. Independent confirmation and incremental news gains remain outstanding.

**Sources:**[data/v5/no_terminal_baseline_diagnostic_20261009/report.json](/Users/zhurong/UROP/data/v5/no_terminal_baseline_diagnostic_20261009/report.json); [data/v5/market_learner_screen_20261009/report.json](/Users/zhurong/UROP/data/v5/market_learner_screen_20261009/report.json); [eventx/release/v5/OPENED_METHOD_SURVEY_20261009.md](/Users/zhurong/UROP/eventx/release/v5/OPENED_METHOD_SURVEY_20261009.md); [data/v5/method_screen_observed_row_join_20261009/report.json](/Users/zhurong/UROP/data/v5/method_screen_observed_row_join_20261009/report.json); [eventx/release/v7/pilot_20261010/PREPARATION_RESULTS_REV2.md](/Users/zhurong/UROP/eventx/release/v7/pilot_20261010/PREPARATION_RESULTS_REV2.md); [MARKET_NEWS_PAPER_A_DRAFT_20261010_REV2.md](/Users/zhurong/UROP/MARKET_NEWS_PAPER_A_DRAFT_20261010_REV2.md)

### Slide 9: Bottlenecks and the next research step

**9:05–10:00 (55 seconds)**

The bottlenecks now explain what should happen next. Signed contract evidence occurs in only twenty-one fitting rows and zero evaluation rows, so the latest signed-evidence trial cannot establish predictive value. In the thirty-article macro pilot, median publication-to-system availability is about two hundred and twenty-six minutes, which may miss early market adjustment. Reliable contract linking and independent human review are also unfinished. Finally, overlapping targets, common events and opened development data limit confirmatory inference. The next cycle should improve timely evidence coverage, test verified information events and examine delayed repricing by liquidity and trade age. We will add structural volatility benchmarks and freeze a separate evaluation after the design checks. V4 keeps its existing protocol. Our completed progress is stronger market forecasting and a clearer test of what news must contribute.

**What the audience should understand:** The next research priority is usable evidence and independent evaluation; the current gains remain exploratory.

**Sources:** [data/v7/signed_evidence_exploration_20261010/report.json](/Users/zhurong/UROP/data/v7/signed_evidence_exploration_20261010/report.json); [eventx/release/v7/pilot_20261010/PREPARATION_RESULTS_REV2.md](/Users/zhurong/UROP/eventx/release/v7/pilot_20261010/PREPARATION_RESULTS_REV2.md); [eventx/release/v4/protocol.json](/Users/zhurong/UROP/eventx/release/v4/protocol.json)

## Backup slide responses

### Slide 10: Backup: methods, features and target definition

If asked about the algorithmic contribution: the current contribution is empirical evaluation and evidence diagnosis, rather than inventing gradient boosting. If asked about the label: the inherited threshold is four times a trailing one-minute standard deviation, not four thirty-minute Gaussian standard deviations. Eligibility differs by research version; the 9.68% panel deliberately uses the no-terminal development diagnostic, and should not be described as a certified active-contract population. Learned semantic representations fitted across a full discovery period are an exploratory limitation; a future study should fit them inside each forward training window.

Sources (not spoken):
/Users/zhurong/UROP/eventx/release/v5/PROTOCOL_V1_1.md
/Users/zhurong/UROP/data/v5/no_terminal_baseline_diagnostic_20261009/report.json
/Users/zhurong/UROP/eventx/release/paper_a_20261010/TABLES.md
Additional method-screen source:
/Users/zhurong/UROP/eventx/release/v5/OPENED_METHOD_SURVEY_20261009.md
LightGBM and XGBoost did not fit because the local libomp runtime was absent; report them as dependency failures, not evaluated methods.

### Slide 11: Backup: published performance is task-specific

These values are from the primary-source versions recorded in our literature review. They use different event selection, aggregation, horizons and targets. The Prophet Arena intervals do not by themselves establish paired significance. Hindcast's retrieval improvement is against its zero-shot model, not a demonstrated advantage over contemporaneous market prices, and its outcome-based selection needs qualification. Halawi Table Three is used consistently because other table captions in that version differ. No external study in our reviewed set provides a directly matched replication of EventX's thirty-minute movement task.

Sources (not spoken):
/Users/zhurong/UROP/eventx/release/literature_baselines_20261010/evidence.json
https://arxiv.org/html/2402.18563v1
https://arxiv.org/html/2510.17638v1
https://arxiv.org/html/2607.14051v1

### Slide 12: Backup: evidence status and confirmation

If asked whether the latest signed-evidence model improved: control log loss was 0.242828416 and augmented log loss 0.242823935, a difference of about 0.000004481 nats per row. There were zero evaluation rows with signed evidence, so the difference comes from jointly refitting control coefficients and is not evidence of a signed-news benefit. If asked about V4: its primary contrast remains B3 versus B0, with a 0.001-nat minimum improvement, a positive lower uncertainty bound and the frozen Brier guardrail. Source completeness can fail and make confirmation incomplete. The consumed OOT holdout must not be rerun; the original v1 test was also previously exposed.

Sources (not spoken):
/Users/zhurong/UROP/data/v7/signed_evidence_exploration_20261010/report.json
/Users/zhurong/UROP/eventx/release/v4/protocol.json
/Users/zhurong/UROP/eventx/release/paper_a_20261010/TABLES.md
Additional market-screen source:
/Users/zhurong/UROP/data/v5/market_learner_screen_20261009/report.json

## Presentation language and numerical conventions

- Say “9.68% lower development log loss than logistic regression.” Log loss is not classification accuracy or trading return.
- Say “a further 1.17% reduction against the earlier tree in a separate comparison.” Do not add it to 9.68% or treat panels as one common test.
- Average-precision changes on slides 5–6 are absolute changes, not percentage-point changes in accuracy.
- A nonlinear model can represent feature interactions; these experiments do not isolate which interaction caused the gain.
- The exposure control operates on news-exposed rows selected by the existing pipeline. It does not prove fully content-neutral population selection.
- The selected news arm in the 5,388-row comparison is a timing/offset model. It is not the V7 signed-evidence model.
- The 116/120 rule-text coverage improvement is evidence preparation, not linker accuracy or verified historical metadata validity.
- Related papers use different targets and horizons. No direct performance ranking is supported.
- V4 remains its original frozen B3-versus-B0 study. It does not confirm every later selected market model.
- Bottlenecks belong on slide 9. Keep short exploratory-status labels visible beside the earlier results.

