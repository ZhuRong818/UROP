# Methodology and proposed research contribution

## The contribution to present

“Our contribution is a controlled, contract-specific evaluation of incremental news information, with traceable evidence and an explicit diagnosis of usable forecast coverage.”

This is a methodological and empirical contribution. Gradient boosting, logistic regression, forward validation and volatility features are established tools. We have not demonstrated a new learning algorithm or established first-ever priority relative to the full literature.

## What the methodology does

1. **Defines a short-horizon target.** At each five-minute decision, predict a large absolute change in canonical YES log odds over the next 30 minutes. The inherited threshold is four times trailing one-minute standard deviation; it is not four standard deviations of a 30-minute Gaussian return. This differs from predicting eventual contract resolution.
2. **Builds a demanding market reference.** Trailing price, momentum, volatility, trading intensity and trade age enter logistic and nonlinear learners. The latest selected histogram booster adds nine deterministic condition features and uses 120,000 earlier training rows. Feature interactions are a plausible explanation for gains, not an established causal mechanism.
3. **Separates comparison questions.** Market → exposure/context → timing → added semantic content. Compare identical market-time keys within each experiment. Existing exposure selection uses semantic routing, so this estimates added content features conditional on that population. Fully content-neutral exposure selection is a future design requirement.
4. **Enforces a conservative decision clock.** Use the stored system availability clock, incorporating publication and ingestion/run timing. Publication time alone cannot establish model access. This does not certify first public disclosure, article revisions, feed completeness or historical contract status.
5. **Binds evidence to the exact contract.** The repaired extractor checks agency, action, rate object, threshold/operator and explicit period, records exact spans and preserves uncertainty through abstention. Distinguish conditional forecasts from observations, hypotheticals and attributed commentary. Signed support is not a calibrated probability surprise: prior expectations remain unmeasured.
6. **Measures usable yield.** Raw article and association counts are reduced to evidence-bearing articles, episode hypotheses and eligible observable forecast decisions. An article can be relevant but arrive late or concern a market without fresh executions. This funnel distinguishes failure mechanisms before running another forecast.
7. **Reports forward development performance with scope.** Earlier training, later scoring, 30-minute purge and held-market groups limit certain leakage paths. They do not establish independence across common events. Previously opened folds and adaptive search make the current gains exploratory.

## What is achieved, and what remains proposed

| Component | Current evidence | Scope |
|---|---|---|
| Nonlinear market reference | 9.68% lower development log loss than logistic on 364,903 matched rows | Opened historical comparison |
| Earlier selected booster | 1.17% lower loss than earlier tree on 112,616 fold-5 rows | Separate comparison |
| Latest condition model | LL 0.3429489298145635; Brier 0.10905976503729453; AP 0.3462485264100695 | 0.5415604842619057% below previous booster; 1.7012452641439602% below earlier tree |
| Exposure/content control | Exposure arm beats tested timing and semantic extensions on 9,965 matched rows | Conditional on existing article-exposed population |
| Predicate repair | 11 signed associations, two articles, ten markets; six known fitting errors now abstain | Development repair, not independent precision or recall |
| Coverage diagnosis | Eleven signed landmarks / three candidate forecast episodes yield zero eligible observations | No new signed-news forecast fit or improvement |
| Independent confirmation | Original frozen V4 study remains separate | It does not confirm the latest selected market model |

The latest model has not yet been compared with news on the old 5,388-row matched sample. Its tuning combines sample-size and feature changes; attribution requires ablations. May–July results do not demonstrate October performance. Do not add percentages from different comparison panels.

## Questions to prepare for

**What is novel if boosting is standard?** Our proposed contribution is the combination of a strong market reference, staged information controls, exact contract evidence and decision-level coverage diagnosis applied to short-horizon prediction-market repricing. Its scientific value is distinguishing apparent news gains from calibration and data-pipeline effects. First-ever priority has not been established.

**Why exact predicates?** “The Fed may reduce rates” does not bind July, a 50+ bp threshold or an annual cut count. Actor/action/topic overlap can create convincing-looking false links. Exact spans and abstention expose that ambiguity.

**Does no gain prove efficiency?** No. Noisy links, delayed feed arrival, insufficient usable events and dependence can explain the result. The current conclusion concerns tested representations and this forecast target.

**Is the current model better?** It beats the named internal baselines on identical historical rows, with improved log loss, Brier and average precision. Independent current-period superiority remains unmeasured. Related published studies use different horizons and labels; no directly matched external performance ranking is supported.

## Canonical evidence

- `data/v5/no_terminal_baseline_diagnostic_20261009/report.json`
- `data/v5/market_learner_screen_20261009/report.json`
- `data/v5/market_condition_tuning_20261012/report.json`
- `data/v5/market_condition_tuning_20261012/selection_receipt.json`
- `data/v5/opened_news_offset_trial_20261009/report.json`
- `data/v5/method_screen_observed_row_join_20261009/report.json`
- `eventx/release/v7/pilot_20261010/SIGNED_EVIDENCE_V03_REPAIR_20261012.md`
- `eventx/release/v7/pilot_20261010/EVENT_COVERAGE_AND_MISSED_EVIDENCE_20261012.md`
- `eventx/release/v4/protocol.json`


## Selected market model explained

The established algorithm is histogram gradient boosting. At five-minute decisions, 13 base market features plus nine deterministic condition features enter the learner. Histogram bins make numerical split search efficient. Small successive trees update the combined prediction to reduce binary log loss. A sigmoid converts the combined score to movement probability. Training uses known future movement labels only in earlier training observations.

Selected settings: 600 iterations, at most seven leaves, maximum depth three, learning rate 0.05, minimum 100 samples per leaf, L2 regularization 10, and 120,000 sampled earlier observations. Model selection uses fold 4. The inherited label concerns a large absolute 30-minute YES log-odds movement, with a trailing volatility threshold; zero volatility yields a negative label. The model does not output movement direction or final resolution.

Our implementation adds volatility ratios, scaled momentum, short-versus-long momentum, count/size intensity ratios, an age-volatility interaction and price uncertainty p(1-p). Their individual contributions remain to be established through ablations. The algorithm is standard, and current-period independent confirmation remains outstanding.

## Actual news comparison

On 5,388 identical fold-5 rows, the previous selected market booster has LL 0.2437265271225144, Brier 0.07822983532104466 and AP 0.3554778299200714. The selected news-timing arm has LL 0.24457564485328948, Brier 0.07826503756015236 and AP 0.35065638221862316. News-minus-market differences are +0.0008491177307750619, +0.0000352022391077006 and -0.004821447701448211 respectively. These scores are measured development results. No numerical adjustments are applied.

The model-search and shared-shock qualifications remain. The descriptive log-loss gain interval includes zero. The latest condition_120k model and newly relaxed unsigned policy context have not been evaluated together on these keys.

## Broader context coverage

A separate development version retains 144 policy-decision-context articles covering 1,056 existing rows at the same conservative availability clock and 30-minute window. It relaxes exact month/amount entailment, leaves direction unknown and supplies a 100-article review package. Fold 5 has six articles/17 rows. These counts establish operational coverage, not news predictive value or independent episodes.


## Evaluated news correction: algorithm and tuning

The selected news candidate is `timing__offset_ridge_1`, a linear L2-regularized logistic offset fitted on article-exposed observations. It starts from the earlier frozen `tree_no_terminal` market probability. It adds a correction on log odds, then applies a sigmoid. The correction uses recent article count (30m), latest article age, 5m and 15m counts, distinct publishers (30m) and maximum cross-publisher diffusion. It contains no article polarity or exact contract evidence.

The method screen compared context-only, timing and semantic feature tiers. Candidate algorithms included linear offsets with penalties 0.001/0.01/0.1, a quadratic offset, spline logistic regression, histogram gradient boosting, Extra Trees, random forest and an MLP. Training scales features using training observations and minimizes mean binary log loss plus the selected L2 penalty. Earlier folds train; fold 4 determines the selected candidate; fold 5 reports matched performance. Selection and inference are exploratory because fold 5 had previously been opened.

The selected news correction was trained on the earlier market tree, not on the subsequently selected histogram booster or current `condition_120k`. The later exact-key join places its predictions alongside the stronger market booster for an honest comparison. On the 5,388 common rows, news timing scores LL 0.24457564485328948, Brier 0.07826503756015236, AP 0.35065638221862316; the booster scores 0.2437265271225144, 0.07822983532104466, 0.3554778299200714. No incremental gain is established.

The later v0.3.3 signed extractor and v0.4 relaxed unsigned policy-context rules are separate feature research, not fine-tuned language models. The relaxed tier has usable historical row coverage but has not been fitted in a forecasting comparison.
