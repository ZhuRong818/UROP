# EventX: external baselines and performance comparison

Research review date: **10 October 2026**. Scope: prediction-market price movement, information absorption, and news-assisted forecasting. This is a literature comparison using published results and existing EventX aggregate artifacts; it is not a new forecasting evaluation.

## 1. Assessment

**EventX has demonstrated an exploratory improvement over its own linear market baseline, but has not demonstrated incremental news value or superiority to a published external baseline.** The strongest comparable local gain is a **9.68% reduction in log loss** from better market modeling. Published studies support investigating both volatility structure and contract-specific information, rather than assuming a larger text model will improve short-horizon forecasts.

No study verified in this search reports exactly our combination of a five-minute decision grid, 30-minute absolute log-odds movement label, conservative news availability, and matched market/exposure/content controls. Therefore, external scores below describe their respective tasks; they cannot establish a performance ranking against EventX.

## 2. What we predict

EventX predicts whether a contract will undergo a large absolute log-odds movement during the next 30 minutes. The inherited label is `sigma > 0 AND abs(logodds(t+30m)-logodds(t)) >= 4*sigma`, where sigma is estimated from trailing one-minute changes. This is a heuristic threshold, not four 30-minute Gaussian standard deviations. The model probability is the probability of that **movement event**, not the probability that the contract eventually resolves YES. See [V5 protocol](eventx/release/v5/PROTOCOL_V1_1.md).

Raw Brier scores depend on the target, event prevalence, sampling and weighting. An outcome-forecast Brier of 0.184 and our movement Brier of 0.078230 do not show that our model is better. Similarly, a continuous-return likelihood and our binary classification log loss are different quantities, even when both use logarithms.

## 3. Verified external results

### A. Closest price-process and information-absorption studies

| Study | Method and evaluation | Reported performance | Comparison with EventX |
|---|---|---|---|
| Archak & Ipeirotis, *Modeling Volatility in Prediction Markets* (2009) | Prediction-market diffusion volatility from current price and time to expiry; compare ordinary GARCH(1,1), structural model, and GARCH on structural standardized residuals. Chronological half-training/half-testing within 51 InTrade election contracts. | Structural normalization + GARCH gave the best test likelihood in **26/51 contracts**. Among the remaining 25, the structural model beat ordinary GARCH in **17**. These are contract counts, not a pooled percentage loss improvement. | Closest baseline family for our unsigned movement target. Our logistic/tree comparison does not establish superiority to this structural volatility family. It needs adaptation to our exact label and horizon. [Primary paper, §4.3](https://pages.stern.nyu.edu/~narchak/acm_ec_paper.pdf). |
| Angelini & De Angelis, *When Do Markets Fully Process Public Information?* (2026 preprint) | One-minute Kalshi NBA midpoints and public game state; five-fold game-level cross-fitting estimates a fundamental probability benchmark. Updating-gap regressions control for prices, game state, spreads and activity. | Contemporaneous response coefficient **0.638** (SE **0.010**). Updating-gap coefficients for raw future drift: **0.195** at 5 minutes and **0.236** at 15 minutes; after netting future benchmark changes: **0.459** and **0.484**. These are regression coefficients, not forecast-loss reductions. | They provide evidence of delayed signed adjustment to structured public information; we currently have no validated equivalent news-surprise signal. Their clock and midpoint measurement are more suitable for absorption analysis than our delayed article feed and last trades. Their five-minute all-observation midpoint return **0.0039** becomes executable-style return **−0.0120** after spreads; predictability does not imply profit. [Primary paper, Tables 5, 6, 11](https://arxiv.org/html/2606.07811v1). |
| Sung et al., *Improving prediction market forecasts by detecting and correcting possible over-reaction to price movements* (EJOR, 2019) | Conditional logit correction using odds trends; 6,058 Betfair markets and over 8.4 million price observations. Target is event outcome probability. | Publisher abstract reports systematic corrections and improved forecasts. **A numerical loss improvement was not verified**: the full accepted-manuscript fetch failed. | Supports a transparent trend/reversal correction baseline. It does not supply a verified numeric score for a direct comparison. [Publisher abstract](https://www.sciencedirect.com/science/article/pii/S0377221718305575). |

### B. News/retrieval and language-model forecasting studies

| Study | Method and target | Reported performance | Comparison with EventX |
|---|---|---|---|
| Halawi et al., *Approaching Human-Level Forecasting with Language Models* (2024; pinned arXiv v1) | Question-specific news retrieval, relevance ranking, summaries, reasoning, fine-tuning and ensembling; final binary outcomes from forecasting platforms. | Full-test Brier: **system 0.179**, **crowd 0.149**, **crowd+system 0.146**. Base GPT-4 without retrieval: **0.206**; with retrieval: **0.186**. The latter is a retrieval ablation, whereas 0.206→0.179 also changes training/ensemble components. | Shows retrieval can improve a weak text-only baseline and modestly complement crowd forecasts. Our relevant contrast is news added to a strong market model, not retrieval versus a model without market information. [Primary paper, Tables 3 and 5, §6.4](https://arxiv.org/html/2402.18563v1). |
| *LLM-as-a-Prophet: Understanding Predictive Intelligence with Prophet Arena* (2025; pinned arXiv v1) | Kalshi market context plus shared retrieved news; repeated forecasts of final outcomes. Evaluation uses 1,367 resolved events and event-weighted Brier scores. | **GPT-5 High 0.184 ± 0.006**, **market 0.187 ± 0.006** (reported 95% bootstrap intervals). Point difference is **0.003**; overlapping marginal intervals alone do not establish a paired significant gain. Market performance overtakes LLMs near resolution. | Closest broad market-plus-news architecture. Its task and weighting differ from ours; its headline score also does not isolate news from reasoning/calibration. Use its market-only/news-only/both ablation design. [Primary paper, Table 2 and §4.2.2](https://arxiv.org/html/2510.17638v1). |
| *Hindcast: Replaying Prediction Markets to Evaluate LLM Forecasters* (2026 preprint) | Frozen, timestamp-filtered Reddit retrieval versus the same zero-shot model; final Polymarket outcomes on 216 markets, averaged over five runs. | Qwen3-32B Brier **0.234→0.179**, about **23%** lower; accuracy **64.6%→72.8%**. Retrieval reduces Brier for eight of nine models. | A positive retrieval result against zero-shot, not a demonstrated 23% improvement over market prices. Selection uses evidence supporting the resolved side, followed by outcome balancing; gains apply to that enriched sample. Five-run variation is not a confidence interval over independent events. This differs from our eligible population. [Primary paper, §4.1 and Table 1](https://arxiv.org/html/2607.14051v1). |

### C. Additional context, with access and metric limits

- **Zemani, 2026 SSRN working paper:** its primary abstract reports about **0.001 nats** of bias-corrected incremental log-likelihood beyond liquid market prices over **25 ForecastBench rounds**, versus approximately **0.09 nats** for a human positive control on one round. This resembles our question about incremental information, but the metric is a fitted forecast-encompassing statistic, not our raw paired model loss difference. These are **abstract-level claims**; full-method/replication verification remains outstanding. [Primary record](https://papers.ssrn.com/sol3/papers.cfm?abstract_id=6944258).
- **PolyBench, 2026 preprint:** final-outcome trading on news/order-book snapshots; Table 5 reports **75.0% selected-trade accuracy and 6.2% confidence-weighted return** for Gemini-3-Flash, and **62.1% / 17.6%** for MiMo-V2-Flash at $10 base lot size. Skipped cases are excluded and proper scoring rules are not reported. This is an execution-aware benchmark, not a movement-forecast baseline; EventX has no corresponding profitability result. [Primary paper, §4.2 and Table 5](https://arxiv.org/html/2604.14199v1).

## 4. Our performance, using matched local comparisons

Lower log loss and Brier are better; higher average precision (AP) is better. Improvements below are within a single named cohort. Cohorts must not be mixed.

| Comparison | Rows | Baseline → model log loss | Brier | AP | Interpretation |
|---|---:|---:|---:|---:|---|
| V5 market modeling: matched L2 logistic → shallow nonlinear market tree | 364,903 | **0.451070→0.407391** | 0.140952→0.131106 | 0.226649→0.334964 | **9.68% lower log loss**, +0.108315 AP; opened development, after model search. |
| V5 fixed-offset control: original market tree → exposure-context correction | 9,965 | **0.330591→0.327533** | 0.107047→0.105861 | 0.373627→0.374094 | 0.003058-nat gain; availability/context calibration can explain apparent news-associated gains. |
| V5 fixed-offset information: context → timing + relevance/novelty features | Same 9,965 | **0.327533→0.328787** | 0.105861→0.106183 | 0.374094→0.373029 | **Worse by 0.001254 nats**; no aggregate content gain in this trial. |
| V5 exact matched fold 5: selected stronger market HGB → selected news-family timing offset | 5,388 | **0.243727→0.244576** | 0.078230→0.078265 | 0.355478→0.350656 | **Worse by 0.000849 nats**, about **0.35%**. Selected news arm is timing, not the richer semantic arm. |

Sources: [market diagnostic](data/v5/no_terminal_baseline_diagnostic_20261009/report.json), [fixed-offset report](data/v5/opened_news_offset_trial_20261009/report.json), [exact-row comparison](data/v5/method_screen_observed_row_join_20261009/report.json). Full precision and source hashes are recorded in [comparison evidence](eventx/release/literature_baselines_20261010/evidence.json).

The exact-row news-minus-market improvement interval is **[−0.004221, +0.002996] nats**. It is descriptive and unadjusted for search/shared shocks; it does not exclude a useful positive gain. Our market-model gain has a descriptive interval **[0.039575, 0.047682]**, with the same generalization limitations. Neither is independent confirmation.

V3.1 development also found news counts reduced AP by 0.001916. Its consumed historical holdout evaluated **B0 only**, so it supplies no independent held-out news comparison. The prospective V4 result remains pending; the frozen close and evaluation sequence are unchanged. See [existing consolidated tables](eventx/release/paper_a_20261010/TABLES.md).

## 5. Where we stand against the literature

1. **Raw forecasting improvement:** our nonlinear gain is meaningful within our development cohort. Its size cannot be ranked against Hindcast's 23% Brier reduction: different loss, target, population and baseline strength.
2. **Incremental external information:** Halawi demonstrates a small benefit from combining system and crowd forecasts; the NBA paper identifies subsequent adjustment to a structured public signal. EventX has not yet demonstrated the corresponding gain for contract-specific news.
3. **Evaluation design:** our explicit exposure controls and conservative availability clocks address confounding that a retrieval-versus-zero-shot comparison leaves open. However, unresolved dependence/inference and source/semantic validity prevent a strong independent performance claim.
4. **Evidence quality:** V7's assistant review agreement is not model accuracy. Five jointly exact/signed links reduce to two nominally timely pairs from one analyst article; all novelty/surprise labels remain unknown. The macro pilot's median article lag is approximately **226 minutes**, much longer than a 30-minute target. This is a plausible signal-loss mechanism, not proof that public news lacks information. See [review diagnosis](MARKET_NEWS_REVIEW_RESULTS_20261010.md).

## 6. Recommended baseline comparison next

Priority is a small, literature-grounded benchmark on identical opened development keys, followed by a separately frozen evaluation. This recommendation does not authorize changes to frozen V4.

| Priority | Baseline to add/adapt | How to make it comparable |
|---|---|---|
| 1 | Training-only constant event rate; transparent price/momentum/reversal logistic; selected market HGB | Predict our movement event on the same rows. A contract YES price is not the correct probability baseline for this target. |
| 1 | EWMA and GARCH(1,1); Archak–Ipeirotis structural volatility and structural-normalized GARCH | Convert each distribution/variance forecast to the probability of exceeding the exact 30-minute log-odds threshold. Estimate residual tails/calibration only within forward training. Record assumptions and expiry/zero-volatility handling. |
| 2 | Question-specific retrieval/reasoning with signed evidence | Use the exact resolution predicate, supplied evidence spans, conservative availability, novelty and direction. Compare market+exposure+timing against the same model plus content; fit/calibrate within each training fold. Historical LLMs must predate evaluation events or contamination must be addressed explicitly. |
| 2 | Public-state updating-gap model inspired by the NBA study | For a separately defined delayed-adjustment task, derive a defensible external probability benchmark from verified macro releases and estimate signed gaps. An article sentiment score is not automatically a fundamental probability. |

Use the same target, source clock, eligibility, rows, temporal splits and tuning budget for all eligible candidates. Report log loss, Brier, AP, calibration, population-wide results and news-exposed results separately. A usable benchmark needs reviewed information episodes and dependence-aware uncertainty; row count alone is not sample size. Preserve failed experiments and reserve a new evaluation once design decisions are fixed.

**Recommended order:** compare structural volatility baselines first; repair the news evidence and timing pipeline in parallel; then assess whether signed contract-specific information improves over the strongest market/context baseline. A positive result must survive the baseline ladder and independent evaluation. A negative result should bound a useful effect rather than rely on a nonsignificant difference.

## 7. Search and verification limits

Searches covered prediction-market volatility, price corrections, public-information absorption, market-relative LLM forecasting, and retrieval-based forecasting. Numeric comparisons were drawn from primary author/publisher papers and existing local JSON reports. Sources are pinned to the linked versions, not a claim that every latest revision or all literature was exhausted.

OpenReview final-version PDFs were blocked by a browser-verification page; the Prophet Arena numbers therefore come from arXiv v1. The Sung accepted PDF could not be fetched, so its numeric improvement is omitted. SSRN discussion is marked abstract-only. Live leaderboards with differing model cohorts, blog summaries, stock-direction studies, and illustrative documentation scores were excluded from the numeric baseline comparison. No external method was implemented or evaluated in this task, and no protected holdout records were opened.
