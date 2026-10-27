# EventX market-news research status and direction

**Report date:** 9 October 2026, Asia/Singapore  
**Operational status checked:** 9 October 2026, 11:04 UTC / 19:04 Singapore time  
**Scope:** EventX market-news forecasting research.  
**Evidence:** Completed frozen historical results, opened development experiments, contract-link diagnostics, and a fresh V4 process/checkpoint audit. No new forecast experiment was run for this report.

## 1. Research summary

EventX asks whether external news available at a decision time improves prediction of a **large absolute prediction-market price movement over the next 30 minutes**, after the model has already observed executed-market history.

The research has produced a completed historical study, a frozen prospective study that is still collecting data, and several exploratory model and article-linking experiments. The clearest improvement so far comes from **nonlinear modeling of market history**. News counts, timing, relevance–novelty, and publisher-diffusion features have not demonstrated a stable incremental gain over appropriate market and context controls.

The strongest current numerical findings are:

- **Completed historical news comparison:** news counts reduced average precision by **0.001916** and worsened Brier score by **0.000284** on **1,460,454** matched development predictions. All five promotion gates failed.
- **Opened development baseline improvement:** a shallow market-only boosted tree reduced log loss from **0.451070 to 0.407391**, a **9.68% reduction**, on **364,903** matched rows. This gain remains exploratory.
- **Latest algorithm search:** the fold-4-selected market-only histogram booster improved fold-5 log loss from **0.348884 to 0.344816** on **112,616** rows. On the exact **5,388** observed-article rows, the selected news model scored **0.244576**, worse than the stronger market-only model's **0.243727**.
- **Independent prospective result:** pending. V4 covers **470 Polymarket markets** and closes at **30 October 2026, 00:00 UTC**. No prospective labels, predictions, prevalence, or performance metrics have been opened.

The intended scientific result is a defensible estimate of news's incremental predictive value. A positive effect would need to survive strong controls and independent evaluation. A negative or inconclusive result is also meaningful if the paper states exactly which news representation, source, cohort, dates, and uncertainty assumptions were tested.

## 2. Research question and method

### Forecast target

At five-minute UTC decision times, the historical primary task uses the last executed canonical-YES price observed by time `t`. Prices are clipped to `[0.0001, 0.9999]` before conversion to log odds. The model predicts whether the absolute log-odds movement from `t` to `t + 30 minutes` crosses the frozen trailing-volatility threshold.

In the completed V3.1 study, the threshold is four times the trailing one-minute volatility estimate, with a minimum of 30 observations in the trailing 240-minute window. This is a prespecified heuristic event threshold. Rows require sufficient history, recent activity, and a complete horizon before the terminal boundary. The price series can be stale between executions; trade age is therefore an important predictor and limitation.

This task forecasts short-horizon repricing magnitude. Eventual contract resolution, price direction, causal effects of articles, and executable trading returns require different outcomes and designs.

### Information availability

News is usable only at its conservative research availability clock:

```text
available_at = max(publication time, ingestion time,
                   joined source-run start, joined source-run end)
```

This clock records a conservative time at which the retained information can be used. It does not establish the first time a subscriber received the article. Stable document identities are deduplicated; conflicting timestamps are quarantined under the applicable frozen rules. Missing or failed feed windows cannot establish zero news.

### Comparisons and evaluation

Market models use price, momentum, volatility, executed-trade counts and notional, and trade age. News models add external-information features to matched controls. Forward validation, a 30-minute horizon purge, and disjoint market groups reduce leakage from future labels and repeated contracts. Models are compared on identical `(market, decision time)` keys.

For the redesigned news experiments, a context-only correction is especially important: selecting moments with an observed article can change the risk distribution even when article content has no additional information. Timing and semantic features must beat that matched correction as well as a strong market-only forecast.

**Metric interpretation:** lower log loss and Brier score are better; higher average precision (AP) is better. Reported “improvement” in a loss is control loss minus candidate loss, so a negative number means the candidate performed worse. Scores from different cohorts or validation subsets should not be compared as if they measured the same experiment.

## 3. Status by research branch

| Branch | Purpose | Current status | What the evidence supports |
|---|---|---|---|
| V3.1 historical primary | Market history versus added news counts | Complete; holdout consumed | News-count candidate failed development promotion; selected market-only holdout benchmark completed |
| V4 news-quality confirmation | Volume, relevance–novelty, and publisher diffusion | Models and protocol frozen; collection active | Historical discovery is negative; prospective result pending |
| V5 algorithm redesign | Stronger market models and sparse news corrections | Opened development only; no new-data confirmation | Nonlinear market-only gains; no stable news increment |
| V6 contract-aware linking | Link articles to the correct contract, episode, predicate, and period | Development implementation and diagnostics; no forecast result | Retrieval, role binding, timing, and data validity remain unresolved |
| V2.3 pilot | Small prospective news-count replication | Secondary branch; unchanged | Fourteen-market pilot scale; no new result assessed for this report |

KOL research remains deferred after failed association audits. Publisher diversity and duplicate-headline diffusion measure cross-publisher activity; validated social engagement, repost, share, or view data are unavailable.

## 4. Current data and performance statistics

### 4.1 Completed V3.1 historical study

The cohort contains **4,651 markets**: **3,832 Kalshi** and **819 Polymarket**. Development covers `[2026-05-17, 2026-07-22)` UTC; the consumed historical holdout covers `[2026-07-22, 2026-08-08)` UTC.

Development generated **7,706,324** eligible examples and **1,460,454** matched out-of-fold predictions. The frozen association inventory contained **218,496** article-market associations from **147,377** documents; **1,420** markets had at least five associations. These are representation-support counts, not independently validated semantic links.

| Development model | AP | Brier | ROC AUC |
|---|---:|---:|---:|
| B0: market-history logistic model | 0.193294 | 0.119209 | 0.626311 |
| B1: same model plus news counts | 0.191378 | 0.119494 | 0.622853 |

B1's AP difference is **−0.001916** and Brier improvement is **−0.000284**. The paired within-market moving-block Brier interval is **[−0.000341, −0.000230]**. Both AP and Brier improved in **zero of five folds**; all five promotion conditions failed. The protocol selected B0.

The holdout evaluated **only B0**, once:

| Holdout quantity | Value |
|---|---:|
| Eligible rows / markets | 211,718 / 300 |
| Repricing events / prevalence | 26,381 / 0.124604 |
| AP | 0.171628 |
| Brier | 0.107107 |
| ROC AUC | 0.628037 |
| Equal-frequency ECE, 10 bins | 0.015317 |

B1 was never evaluated on this holdout. The result supplies an absolute benchmark for B0, not a held-out estimate of incremental news value. Label prevalence was disclosed before the consumption receipt, although before predictions or performance; the recorded status includes this protocol deviation.

Sources: [development selection](data/v3_1_historical/primary/development/selection_result.json), [holdout result](data/v3_1_historical/primary/holdout/evaluation_result.json), and [deviation disclosure](eventx/release/v3_1_historical_primary/HOLDOUT_PROTOCOL_DEVIATION.md).

### 4.2 V4 richer-news discovery and prospective confirmation

The opened historical discovery compared **745,443** identical out-of-fold rows:

| Model | Added information | Log loss | Brier | AP | Log-loss improvement versus B0 |
|---|---|---:|---:|---:|---:|
| B0 | Market history | 0.459158 | 0.143117 | 0.206147 | — |
| B1 | News volume | 0.461659 | 0.143817 | 0.201221 | −0.002500 |
| B2 | Relevance and market-relative novelty | 0.461946 | 0.143817 | 0.202546 | −0.002788 |
| B3 | Publisher diversity and headline diffusion | 0.465617 | 0.143959 | 0.204842 | −0.006459 |

B3's paired historical log-loss interval is **[−0.007411, −0.005545]**. This discovery result is exploratory. Its semantic transform was fitted on the full discovery text before the forward folds, creating a future-text limitation for the historical comparison.

The prospective protocol was frozen before its future interval:

- **Cohort:** 470 Polymarket markets and 470 protocol market clusters.
- **Window:** `[2026-09-06, 2026-10-30)` UTC.
- **Primary comparison:** B3 versus B0 on identical eligible rows.
- **Success requirement:** mean log-loss improvement of at least **0.001 nats per row**, paired bootstrap 95% lower bound above zero, Brier improvement at least **−0.0005**, and the eligible-venue nonnegative guardrail.
- **Source requirement:** incomplete news coverage makes the news confirmation incomplete; missing coverage must not be encoded as zero news.

At the fresh **11:04 UTC** operational check, collector PID **39078** and guard PID **39109** were alive. The checkpoint covered **40 news days** and **33 trade days**, both through **8 October**. There were **40 news** and **330 trade** receipt sets with corresponding payload and SQL files, **zero closed-day backlog**, **15/15 frozen hashes matching**, and **no reported problems**. No consumption receipt, example, prediction, or evaluation artifact existed. The check examined metadata and implementation hashes; it did not certify sealed payload contents or upstream completeness.

Sources: [historical result](data/v4/discovery/models/result.json), [frozen protocol](eventx/release/v4/protocol.json), and [fresh collector check](data/v4/health_checks/20261009T110400Z/report.json).

### 4.3 V5 market-model improvement and news corrections

The broader opened development inventory contains **4,651 markets**, **21,439,891 trade rows**, **148,543 news rows**, and **479,179 legacy association events**. These differ from V3.1's frozen document/association counts because they describe a different inventory and processing stage. Source coverage and historical validity remain unresolved.

The original V5 audit ran **108 fits** across logistic, spline, and shallow boosted-tree approaches on **364,903 validation rows / 1,135 contracts**. A paired diagnostic removing terminal metadata from both market models gave:

| Market-only model without terminal predictor | Log loss | Brier | AP |
|---|---:|---:|---:|
| L2 logistic | 0.451070 | 0.140952 | 0.226649 |
| Shallow boosted tree | 0.407391 | 0.131106 | 0.334964 |

The tree improves log loss by **0.043679 nats per row / 9.68%**, Brier by **0.009845**, and AP by **0.108315**. Log-loss improvement is positive in all three forward folds; the descriptive market-cluster interval is **[0.039575, 0.047682]**. This is a reanalysis of frozen opened-data predictions, not an independent confirmation.

An observed-news fixed-offset trial subsequently evaluated **9,965 rows / 219 markets**:

| Correction on the same observed-news rows | Log loss |
|---|---:|
| Original market-only tree | 0.330591 |
| Exposure-gated market context | 0.327533 |
| Context plus news timing | 0.327942 |
| Timing plus relevance–novelty | 0.328787 |

Context correction improves over the original tree by **0.003058**, but adding news timing or semantic features makes the result worse. The full semantic arm is **0.001254** worse than context. Thus a gain against the uncorrected tree alone would overstate the contribution of news content.

The latest broader search attempted **50 additional configurations**; **45 completed both forward folds**. The fold-4-selected seven-leaf, 600-iteration histogram booster improved fold-5 market-only log loss **0.348884 → 0.344816** on **112,616 rows / 228 markets**. Its improvement is **0.004068**, with descriptive interval **[0.002841, 0.005276]**, Brier improvement **0.001203**, and AP gain **0.010482**.

The essential news comparison uses an exact join on the **same 5,388 fold-5 observed-article rows**:

| Model or correction | Log loss | Brier | AP |
|---|---:|---:|---:|
| Original market tree | 0.245673 | 0.078771 | 0.350843 |
| Selected stronger market-only booster | **0.243727** | 0.078230 | **0.355478** |
| Selected context-only correction | 0.243985 | **0.078174** | 0.350843 |
| Selected news timing correction | 0.244576 | 0.078265 | 0.350656 |

Selected news loses to the stronger market model by **0.000849** and to context by **0.000591**. Its descriptive interval versus the stronger market control is **[−0.004221, 0.002996]**. It also loses to both controls in fold 4. A post-hoc CatBoost market score of **0.343900** and semantic-offset score of **0.243699** do not justify promotion: their earlier-fold performance was weaker, and fold 5 was already exposed.

All V5 intervals are descriptive and unadjusted for adaptive search, related event families, and shared calendar shocks. No new-data V5 result or candidate promotion exists.

Sources: [inventory](data/v5/readiness_inventory_20260914/report.json), [paired baseline diagnostic](data/v5/no_terminal_baseline_diagnostic_20261009/report.json), [offset trial](data/v5/opened_news_offset_trial_20261009/report.json), [method survey](eventx/release/v5/OPENED_METHOD_SURVEY_20261009.md), and [same-row join](data/v5/method_screen_observed_row_join_20261009/report.json).

### 4.4 V6 contract-aware linking

V6 investigates whether an article concerns the correct entity, contract predicate, episode, measurement period, and information role. Topical similarity alone is insufficient: a report about a host country, an opinion about an asset, or an expired event can rank highly without supplying relevant contract evidence.

The fixed development comparison uses **70 articles / 134 contract cards**, with **669 candidate pairs**. Typed rules produced **52 hypotheses from only eight articles**, seven Bitcoin-related and one World Cup-related. Dense retrieval added candidates but no additional hypothesis-bearing article in that comparison. Candidate counts therefore exaggerate the diversity of useful information episodes.

The completed strict direct-link audit failed: **39/40 conservative relevance errors**, including unresolved cases counted as errors. Its story-boundary endpoint passed with **0/72 errors**, while family-boundary evidence was inconclusive with **3/74 errors**. The later relaxed review used a different opened-development rubric: **102 pairs**, **63 human-agreed pairs**, and **39 assistant-adjudicated disagreements**, yielding **26 material-predicate**, **21 shared-context**, and **55 not-applicable** labels. The material labels reuse only **five articles**. Reviewer distinctness was accepted on user attestation; blinding remains unverified. These labels do not establish independent linker accuracy.

The overlap ledger contains **134 contracts × 66 days = 8,844 contract-days**; **3,803** have observed trades. None currently meets the complete predictive-admission requirements because feed windows, article/market historical versions and status, semantic relevance, and family boundaries remain unresolved. The requested exploratory V5 results above were produced without waiting for these requirements, but retain their narrower opened-data interpretation.

Sources: [strict audit](eventx/release/v6/BOUNDED_AUDIT_RESULT_20260917.md), [pipeline readiness](eventx/release/v6/SUPPORT_AND_PIPELINE_READINESS_20260926.md), [relaxed review](data/v6/relaxed_adjudication_20260927/report.json), and [overlap ledger](data/v6/support_ledger_20260926/report.json).

## 5. Algorithms and representations tried

| Method family | Reason for trying it | Observed outcome or limitation |
|---|---|---|
| L2 logistic / standardized SGD | Transparent market and news-count benchmark | Completed V3.1 comparison; news counts failed promotion |
| Spline logistic | Capture smooth nonlinear market relationships | Improved market modeling relative to linear in the opened audit; no stable semantic increment |
| Histogram gradient boosting | Capture nonlinear interactions among price, activity, and volatility | Strongest selected opened-data market result; later seven-leaf configuration improved both reported folds |
| Fixed-offset ridge and quadratic corrections | Preserve the market forecast while estimating a small added correction | Context recalibration helped; selected timing/semantic additions failed to beat matched controls |
| Extra Trees, random forest, small MLP | Broaden the learner comparison beyond boosting and linear corrections | Completed bounded configurations; no selected stable news gain |
| CatBoost | Test another nonlinear boosting implementation | Completed fits; attractive post-hoc fold-5 market score but weaker fold-4 performance |
| LightGBM and XGBoost | Test additional boosting implementations | No fits completed: installed packages could not load the missing macOS `libomp.dylib` runtime |
| TF-IDF, BM25, dense retrieval, cross-encoder ranking | Retrieve and rank article-contract candidates | Produced broader candidate pools; ranking did not establish contract-specific relevance |
| Typed contract/entity/period rules and document-role checks | Separate real event evidence from background, opinions, figurative language, and expired periods | Repaired individual development cases; useful general coverage and independent accuracy remain unproven |
| Grammar, spaCy dependency parsing, and compositional spans | Extract actors, objects, propositions, negation, and speakers with traceable evidence | Dependency coverage improved; attachment, attribution, partitives, and scope still fail in inspected cases |
| DeBERTa NLI | Test whether article evidence supports a contract proposition | Selected 8/8 supported synthetic probes but falsely selected 3/10 unsupported probes; not promoted |
| Local Qwen2.5-0.5B structured extraction | Test schema-based evidence extraction | 10/10 fixed development outputs were schema-invalid; semantic performance could not be scored |

The NLP probe counts are bounded development diagnostics, often using assistant-authored cases. They are not population accuracy estimates. The forecasting search is broad but does not exhaust all possible learners, representations, or objectives.

## 6. Direction and intended result

The immediate direction is to complete the frozen V4 prospective test and develop the historical manuscript using the results already available. The redesign direction is to combine a strong nonlinear market forecast with a small, contract-relevant news correction, using separate controls for exposure context, timing, relevance, and novelty.

The proposed V6 ladder is **M / T / R / N**: market history, timing, relevance, and novelty. Its exact feature definitions, admission policy, primary contrast, and inference are not frozen. If timing uses the same semantic exposure gate as relevance, an R-versus-T contrast tests added features conditional on that gate; it cannot measure the entire value of content beyond a content-neutral timing model. This estimand must be resolved before a new confirmatory experiment.

The intended result has three components:

1. **Quantify baseline improvement.** Confirm whether the promising nonlinear market model improves on genuinely new data, rather than treating opened-fold gains as established generalization.
2. **Measure the incremental news effect.** Compare the news model with the strong market model and a matched context/timing control on identical rows. For V4, apply the existing 0.001-nat success rule. Any subsequent cycle needs its own prospectively fixed useful-gain threshold and power analysis.
3. **Explain the measured scope.** Report source timing, coverage, link quality, event diversity, calibration, and dependence assumptions so a gain, harm, or inconclusive result is interpretable.

Positive market-only improvement is already visible in development. Positive incremental news value remains an intended hypothesis, not an achieved result.

## 7. Main gaps

| Gap | Why it matters | What resolves it |
|---|---|---|
| Independent confirmation | Repeated search on opened folds can select accidental gains | Complete frozen V4; use a separate untouched interval for any later redesign |
| News availability and feed coverage | Publisher time can precede actual access; absent exports may reflect failed or filtered collection | Delivery/version semantics, per-window/page/symbol receipts, and explicit missingness |
| Contract relevance | Entity or topic matches can link an article to the wrong predicate, role, episode, or period | Stable linker plus independent review of accepted, rejected, and nonretrieved cases |
| Historical market terms and status | Current rows and nominal start/end dates do not reconstruct historical active contracts | Versioned terms and activation/status evidence at decision time |
| Independent episode yield | Many article-contract pairs can reuse the same few stories | Count distinct eligible articles, episodes, families, and calendar exposures before power planning |
| Dependence and inference | Related markets and common news shocks make row counts overstate sample size | Defensible event/family/calendar design with simulation of interval coverage and power |
| Representation leakage | Full-development semantic fitting includes text from later validation dates | Fit all learned representations inside each training window in a newly versioned cycle |
| Strong matched controls | News can appear useful against a weaker linear model or an uncorrected exposed cohort | Preserve nonlinear market and context/timing comparisons on identical keys |

Previous block-bootstrap and grouped-t redesign candidates failed dependence simulations. Nominal 95% grouped-t coverage fell to **84.0%–92.3%** under strong persistence and **85.4%–86.3%** under regime shifts in the recorded screen. Those methods were not adopted. Market-cluster intervals in the latest searches do not resolve this problem.

The focused Lumid request covering nine articles, 15 contracts, and the problematic source windows is prepared but remains unsent. Older publisher-dated backfills cannot supply a new pre-May point-in-time confirmation sample. See [inference assessment](eventx/release/v5/CERTIFICATION_RESOLUTION_20260910.md), [V6 design review](eventx/release/v6/PLAN_DATA_ALGORITHM_RUBRIC_EVALUATION_20260927.md), and [source request](portfolio/LUMID_EVENTX_V6_SINGLE_FILE_REQUEST_20261002.md).

## 8. Paper direction and next milestones

The existing [historical EventX manuscript](portfolio/EVENTX_HISTORICAL_PAPER_DRAFT_20261004.md) provides a starting point for a paper about short-horizon forecasting under conservative information clocks. Its completed contribution is the failed news-count development selection, the selected market-only holdout benchmark, and a reproducible account of measurement limits. Broader V5 results can support an exploratory discussion of stronger controls; V4 can supply its separate prospective result after close if the source gate passes.

A useful working paper question is: **“Does timestamped, contract-relevant news improve short-horizon prediction-market repricing forecasts beyond market history?”** The scope must distinguish the tested count-based historical representation from the still unfinished contract-relevant redesign. The paper does not need to force a positive news result. It does need clear claims, exact artifact-backed tables, a reproducible release, permitted data/code sharing, and a comparison with closely related literature before submission.

The next milestones are:

1. **Through 30 October:** maintain V4 collection with process, checkpoint, receipt, and frozen-hash checks that do not inspect outcomes.
2. **After the window closes:** execute `audit_v4_confirmatory_collection` → `consume_v4_confirmatory_holdout` → `prepare_v4_confirmatory_inputs` → `build_v4_confirmatory_examples` → `evaluate_v4_confirmatory`, once and in order. Stop if a gate fails.
3. **For the historical paper:** verify the existing manuscript's values and claim scope, prepare figures/tables from canonical artifacts, and disclose failed experiments and the receipt-order deviation.
4. **For a subsequent redesigned study:** resolve source and linker validity, freeze the estimand and strong controls, establish episode yield and valid inference, and specify a new untouched confirmation sample. This report does not launch that cycle.

Consumed historical holdouts remain closed. V4 cannot be retuned using the new V5 search or its eventual prospective result. The original v1 test was previously exposed and cannot be described as untouched. These constraints preserve the distinction between exploration and independent confirmation.

## 9. Evidence and report provenance

The canonical startup handoff is [CURRENT_STATE.md](CURRENT_STATE.md); detailed history is appended in [October progress](docs/progress/2026-10.md). The broader research plan is [COMPLETE_RESEARCH_PLAN.md](COMPLETE_RESEARCH_PLAN.md), and the previous expanded synthesis is [the 7 October report, updated with 9 October experiments](MARKET_NEWS_RESEARCH_PROGRESS_20261007.md).

Metrics above are rounded to six decimal places from the linked JSON artifacts. Full precision, model settings, predictions, failures, and manifests remain in those artifacts. Operational counts come from the fresh 9 October 11:04 UTC check. No dataset was fetched, forecast model fitted, protected result opened, or frozen research decision changed while preparing this report.
