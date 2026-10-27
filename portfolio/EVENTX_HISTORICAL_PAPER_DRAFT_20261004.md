# Does Timestamped News Improve Short-Horizon Prediction-Market Repricing Forecasts? A Source-Bounded Historical Study

**Draft:** 4 October 2026  
**Authors and affiliations:** to be supplied  
**Study status:** Completed EventX v3.1 historical study; V4 historical discovery reported as exploratory context. The separate V4 prospective holdout has not been evaluated.  
**Scope of claim:** Predictive performance for the specified Lumid-sourced cohort, news representation, learner, and dates. No causal, trading-profit, social-virality, or universal news-null claim.

## Abstract

Prediction-market prices incorporate information, but it remains an empirical question whether a timestamped news feed improves short-horizon forecasts after executed-market history is observed. We studied 4,651 binary markets on Kalshi and Polymarket from 17 May to 8 August 2026 using a source-bounded Lumid warehouse extract. At five-minute decision times, the task was to predict whether the absolute canonical-YES log-odds change over the next 30 minutes crossed a prespecified, trailing-volatility-based threshold. A frozen market-only logistic model (B0) used price, momentum, volatility, executed-trade activity, and venue. A matched model (B1) added counts of associated news articles available by the decision time. Development used five purged, expanding-time folds with held-out market groups; promotion required improvements in average precision, Brier score, fold consistency, a paired block-bootstrap interval, and both venues.

Across 1,460,454 matched out-of-fold development observations, B1 had lower average precision than B0 (0.191378 versus 0.193294) and a higher Brier score (0.119494 versus 0.119209). It failed all five promotion conditions. The frozen B0 fallback was evaluated once on the 17-day historical holdout: 211,718 observations from 300 eligible markets yielded average precision 0.171628, Brier score 0.107107, and ROC AUC 0.628037. B1 was not evaluated on that holdout. In a separate, outcome-open Polymarket development analysis, increasingly rich news-quality and cross-publisher features also failed to improve a matched market-only model; this finding remains exploratory. The completed result shows that this specific, conservatively timed news-count representation did not earn promotion over the market-history baseline. It does not establish that relevant news has no predictive value. The study illustrates how feed provenance, decision clocks, source completeness, and one-shot evaluation constrain claims about external information in prediction markets.

**Keywords:** prediction markets; news; point-in-time data; repricing; forecast evaluation; data provenance

## 1. Introduction

Prediction markets aggregate traders' information into contract prices [1]. External news may precede a price adjustment, but the timestamp printed by a publisher is not necessarily the time at which a research system could observe the article. A delayed ingestion, retrospective backfill, duplicate article, or interrupted feed can make a historical news signal look more timely or more complete than it was. Repeated observations from the same market can also give a misleading impression of sample size.

We ask a deliberately narrow predictive question: **does the count of market-associated articles available by a decision time improve prediction of a 30-minute absolute canonical-YES repricing event beyond executed-market history?** This differs from predicting eventual contract resolution or the direction of a trade. It also differs from estimating the causal effect of a particular article.

Our completed historical experiment compared a fixed market-history model with the same learner plus three rolling news-count features. A fifth preregistered promotion condition guarded against an aggregate gain that came at the expense of either venue. The news model failed every condition in development. The protocol then selected a market-only candidate for a single historical holdout evaluation. We report that absolute benchmark and the exact limits of its interpretation.

This paper contributes (i) an auditable short-horizon prediction task based on executed canonical-YES trades, (ii) a point-in-time, source-bounded news comparison with prespecified fallback behavior, and (iii) a fully reported negative *model-selection* result with an absolute market-only holdout benchmark. The broader EventX program includes a later, frozen news-quality/diffusion study and work on article-to-contract linkage; neither supplies a completed prospective news result in this paper.

## 2. Related work and positioning

Wolfers and Zitzewitz describe prediction markets as mechanisms for aggregating dispersed information and emphasize the dependence of their usefulness on market design [1]. Work on media and conventional asset markets shows why external text is a plausible signal, while also showing that media content and market responses need careful interpretation [2]. Pennock and colleagues linked changes in news vocabulary to political prediction-market events [3]. Vaughan Williams and Reade studied the timing of Twitter activity and Betfair price adjustment around one political event [4].

Our unit is a five-minute market-time observation across many contracts. Our measured external signal is publisher article *count*, not Twitter activity, media tone, validated article-to-contract semantics, or true social diffusion. The outcome is a future unsigned price movement over 30 minutes. The analysis asks whether that representation adds out-of-fold predictive performance to an executed-trade baseline under conservative data-availability rules.

## 3. Data and prediction task

### 3.1 Sources, cohort, and windows

All observational market, trade, news, and run-provenance data came from Lumid FinData's bounded warehouse retrieval. The claim is about rows present in that warehouse, not completeness of all published news. The label-blind v3.1 cohort contains 4,651 binary markets: 3,832 Kalshi and 819 Polymarket. A market required Lumid metadata available before the development interval closed, a unique canonical YES outcome, at least 100 positive-notional canonical-YES development executions, and activity on at least 10 UTC days. The development interval was `[2026-05-17, 2026-07-22)` UTC. The one-shot historical holdout was `[2026-07-22, 2026-08-08)` UTC.

The v3.1 cohort is a disclosed, pre-outcome correction to the original v3 data gate. That gate found 204,069 Kalshi rows with zero executed contracts. Removing such records from execution calculations left 19 of the original 4,670 markets below the frozen activity minimum. V3.1 removed exactly those 19 before any development label or model result was inspected; the failed v3 gate remains preserved.

### 3.2 Decision time and outcome

For each market, the primary price at five-minute UTC time `t` is the last executed canonical-YES trade observed at or before `t`. Polymarket uses the unique YES asset price; Kalshi YES prices are converted from cents. We carry that last trade forward and record its age. We do not switch the primary series to candles or order-book midpoints. Prices are clipped to `[0.0001, 0.9999]` before conversion to log-odds.

Let `p_t` be this canonical-YES price. For the 30-minute horizon, the unsigned movement is `|logit(p_(t+30)) − logit(p_t)|`. The binary label is one when that movement meets or exceeds `4 × sigma_(1m, trailing 240m)(t) × sqrt(30/30)`, with the frozen implementation's minimum of 30 trailing volatility observations. The factor of four is a **preregistered heuristic event threshold**; it is not a claim that the event is four horizon-standard deviations from a Gaussian mean. Rows lacking the required history, recent activity or full pre-terminal horizon are excluded under the frozen eligibility rule. No forward-liquidity filter is used.

### 3.3 News identity, availability, and association

The frozen news rule associates article headline and summary text with markets. A stable document identity is counted once at its earliest conservative availability time. Conflicting publication timestamps for the same normalized URL are quarantined. The effective clock is the maximum of publication time, server ingestion time, and the joined source run's start and end times when present. This is deliberately later than an article's printed publication time when ingestion or run completion was later. It is a conservative research decision clock, not a measured first-client-delivery timestamp. Rows with missing required provenance or more than 24 hours between publication and derived availability are excluded from the primary news features.

The frozen development association inventory contained 218,496 article-market associations from 147,377 documents; 1,420 of the 4,651 markets had at least five associations. These figures describe candidate feature support, not semantic accuracy or complete provider coverage. A failed or partial upstream run does not certify a zero-news interval. The frozen source claim therefore remains conditional on the rows actually retrievable from Lumid.

## 4. Models and evaluation

**B0 (market history)** has 12 features: current price log-odds; momentum over 5, 30, and 120 minutes; realized volatility over 30 and 240 minutes; executed-trade count and notional over 60 and 240 minutes; minutes since the latest trade; and a venue indicator. **B1 (market history plus news)** adds article counts over 60, 360, and 1,440 minutes and a schema-retained `news_symbol_mapped` indicator. The last feature is constant zero in this frozen study because a canonical event-market financial-symbol map was unavailable. Thus the tested increment is effectively the three rolling counts.

Both candidates use the same standardized logistic stochastic-gradient learner, eight epochs, L2 parameter 0.0001, fixed learning rate 0.02, and an arithmetic mean of predicted probabilities from seeds 11, 23, and 47. Count and notional features receive `log1p`; standardization is fitted on each training fold only. No hyperparameter search was conducted for this comparison.

Development used five purged expanding-time folds. Each validation fold had an 11-day calendar window and one disjoint held-out market-hash group; training used eligible earlier rows from the other groups, with a 30-minute purge. B0 and B1 were scored on identical validation keys. Average precision (AP) was the primary ranking metric and Brier score the calibration-sensitive promotion metric. The prespecified B1 promotion rule required **all** of the following:

1. Positive aggregate out-of-fold `AP(B1) − AP(B0)`.
2. Positive aggregate out-of-fold `Brier(B0) − Brier(B1)`.
3. Both improvements positive in at least four of five folds.
4. A positive lower bound of a paired 95% moving-block-bootstrap interval for the Brier improvement.
5. Nonnegative Brier improvement separately on Kalshi and Polymarket.

The bootstrap used 5,000 paired circular blocks of 72 eligible five-minute rows within each market, nominally six hours per block. Its estimand is conditional on the frozen market cohort; the row count is not a count of independent markets. The protocol selected B1 for the single holdout only if every promotion condition passed; otherwise it froze B0.

## 5. Results

### 5.1 Prespecified historical development comparison

Development produced 7,706,324 eligible examples and 1,460,454 matched out-of-fold comparison observations. The jump rate on those observations was 0.141270. Table 1 gives aggregate metrics; a positive difference is favorable to B1.

| Metric | B0 market history | B1 plus news counts | B1 relative to B0 |
|---|---:|---:|---:|
| Average precision | 0.193294 | 0.191378 | −0.001916 |
| Brier score | 0.119209 | 0.119494 | −0.000284 Brier improvement |
| ROC AUC | 0.626311 | 0.622853 | −0.003459 |
| Equal-frequency ECE (10 bins) | 0.016942 | 0.018230 | +0.001288 |

The paired 95% moving-block interval for `Brier(B0) − Brier(B1)` was `[−0.000341, −0.000230]`. Both AP and Brier improved in **zero of five** folds. Brier improvement was negative for Kalshi (`−0.000285`) and Polymarket (`−0.000277`) separately. All five prespecified promotion conditions were false; B0 was selected. The interval supports a narrow conclusion about this development comparison under its within-market resampling scheme. It does not establish the effect of all possible news representations or generalization to a new market population.

### 5.2 One-shot historical holdout of the selected model

The holdout contained 211,718 eligible observations from 300 markets, including 26,381 labeled repricing events. Only the frozen B0 candidate was evaluated. Its AP was **0.171628**, Brier score **0.107107**, and ROC AUC **0.628037**; the jump prevalence was **0.124604**. Ten-bin equal-frequency ECE was 0.015317. The resulting AP exceeded prevalence, but this is an absolute benchmark for B0, not a held-out B1-versus-B0 comparison.

Performance varied by venue: AP was 0.192295 on 164,569 Kalshi observations and 0.139318 on 47,149 Polymarket observations. The carried-forward last-trade series was often stale: 179,054 of the 211,718 holdout observations had a latest trade more than five minutes old. The development-frozen alert threshold of 0.215509 issued 6,430 alerts, or 3.04% of observations, with positive predictive value 0.175583 and sensitivity 0.042796. These diagnostics describe the operational characteristics of the *market-only* candidate; they do not supply news lift or a trading return.

### 5.3 Separate historical discovery of richer news features

A later V4 design tested a nested ladder on an outcome-open historical Polymarket development interval. B0 used market history; B1 added volume; B2 added frozen relevance and market-relative novelty; B3 added publisher diversity and exact-headline cross-publisher diffusion. On 745,443 identical out-of-fold observations, log loss was 0.459158 for B0, 0.461659 for B1, 0.461946 for B2, and 0.465617 for B3. The B3-versus-B0 improvement was `−0.006459` nats per row, with a paired historical interval of `[−0.007411, −0.005545]`. Brier score and AP also favored B0 over B3 in this development comparison.

This analysis used a different, Polymarket-only cohort and an interval whose outcomes had already been opened. It is **exploratory** and cannot confirm the v3.1 result, test social virality, or substitute for V4's untouched future evaluation. Its practical role here is to show that simply adding richer publisher-news proxies did not resolve the observed historical weakness under that fixed implementation.

## 6. Discussion

The strongest completed inference is procedural and predictive: the preregistered count-based news model did not qualify for holdout selection, while the selected market-only model gave a measurable but modest absolute holdout benchmark. The paired development comparison makes it unlikely that the specific B1 implementation hid a small positive Brier gain *within the frozen development cohort and bootstrap assumptions*. It cannot rule out gains from a better article-to-contract link, richer semantic features, a different learner, cleaner feed coverage, or a different period. Such questions require their own frozen designs and untouched evaluation samples.

Several mechanisms could explain the observed B1 failure, but this study does not identify one causally. The market-history features may already absorb much public information by the time an article enters the Lumid feed. Rolling article counts may pool material market-moving reports with incidental topical mentions. Sparse association coverage means most markets have little measured news exposure. Conservative availability times can exclude a prompt publisher signal that the research system could not verify as available. Finally, warehouse rows cannot establish the completeness of all upstream articles or every failed run's requested page window. These are hypotheses and measurement limits, not post hoc corrections to the frozen result.

The historical V4 discovery result points in the same descriptive direction for its own model family, but the cohorts, metric hierarchy, and data status differ. We therefore report it separately and do not pool estimates or call it replication. The pending V4 prospective test remains governed by its original frozen dates and one-shot execution order. Publishing the present historical study does not authorize an early or revised V4 evaluation.

## 7. Limitations and integrity disclosures

First, the observational source is a bounded Lumid warehouse extract. The run join establishes conservative timing for observed article rows, but it is not a certificate that every provider page, symbol, or zero-news window was complete. `available_at` is derived from several timestamps and does not measure per-client delivery. Article content and market-term revision histories are not fully versioned in the accessible source. The result should be interpreted as a test of the frozen, source-bounded representation.

Second, a lexical article-market association is only a candidate relevance rule. This study did not conduct a comprehensive, independent audit of semantic applicability for every pair. The `news_symbol_mapped` feature is constant zero. Cross-publisher diffusion in V4 is distinct from social sharing, reposts, impressions, or KOL influence; the completed v3.1 experiment tests none of those channels.

Third, the target is a thresholded, unsigned log-odds movement in a last-trade series. Stale trade prices, venue-specific market structure, endpoint changes, and the chosen heuristic threshold affect interpretation. The 300 eligible holdout markets are fewer than the 4,651-market development cohort. Millions of five-minute rows do not erase dependence within markets or create millions of independent contracts. The within-market block interval conditions on the selected cohort and may not capture dependence across related market families or shared news events.

Fourth, the original v3 activity gate failed on zero-notional Kalshi records and led to the exact 19-market, label-blind v3.1 correction described above. The holdout builder later wrote a summary of 26,381 positive labels and prevalence 0.124604 **before** the consumption receipt, contrary to the stronger intended receipt order. No candidate predictions or performance metrics were read at that point; the B0 candidate, transforms, and evaluation formulas had been frozen. The deviation and receipt amendment are preserved. The holdout is therefore a one-shot evaluation **with a disclosed procedural deviation**, not an untouched-label demonstration under the original receipt-order wording.

Finally, B1 was not run on the consumed holdout, and it must not be reconstructed there after observing B0's result. This paper supplies no held-out estimate of the incremental value of news. It supports the narrower development-selection finding and B0 absolute holdout performance.

## 8. Conclusion

In this historical, source-bounded EventX study, three rolling counts of conservatively available, lexically associated news articles failed to improve a frozen market-history model for predicting 30-minute absolute repricing. B1 missed all five prespecified development promotion conditions; the selected B0 model achieved AP 0.171628 and Brier 0.107107 in its one-shot historical holdout. A separate historical development study of richer news-quality and publisher-diffusion proxies also showed no improvement, but awaits its own prospective evaluation. These results define a transparent baseline and a measurement challenge for future article-to-market research. They do not imply that public news, social media, or contract-specific reporting is universally uninformative.

## References

1. Wolfers, J., & Zitzewitz, E. (2004). [Prediction Markets](https://www.aeaweb.org/articles?id=10.1257/0895330041371321). *Journal of Economic Perspectives*, 18(2), 107–126.
2. Tetlock, P. C. (2007). [Giving Content to Investor Sentiment: The Role of Media in the Stock Market](https://onlinelibrary.wiley.com/doi/10.1111/j.1540-6261.2007.01232.x). *The Journal of Finance*, 62(3), 1139–1168.
3. Pennock, D. M., Debnath, S., Glover, E., & Giles, C. L. (2013 preprint). [Modelling Information Incorporation in Markets, with Application to Detecting and Explaining Events](https://arxiv.org/abs/1301.0594).
4. Vaughan Williams, L., & Reade, J. J. (2016). [Prediction Markets, Social Media and Information Efficiency](https://irep.ntu.ac.uk/id/eprint/29386/). *Kyklos*, 69(3), 518–556.

## Internal evidence and submission checks

This section is an audit aid for the draft and can be converted to a public reproducibility appendix after source-rights review. It is not a claim that raw Lumid records can be redistributed.

- Frozen v3.1 design: `eventx/release/v3_1_historical_primary/protocol.json`; implementation: `eventx/release/v3_1_historical_primary/IMPLEMENTATION_SPEC.md`.
- Development selection: `data/v3_1_historical/primary/development/selection_result.json`.
- Holdout evaluation and receipt: `data/v3_1_historical/primary/holdout/evaluation_result.json`, `data/v3_1_historical/primary/holdout/holdout_consumption_receipt.json`.
- Disclosed deviation: `eventx/release/v3_1_historical_primary/HOLDOUT_PROTOCOL_DEVIATION.md`.
- V4 historical discovery: `data/v4/discovery/models/result.json`; prospective protocol: `eventx/release/v4/protocol.json`.
- Before submission: independently verify every table value against these frozen files, audit claim wording and artifact hashes, confirm what code/aggregate data can be shared, and supply author details and the venue's formatting requirements. No protected V4 holdout inspection is required for this manuscript.
