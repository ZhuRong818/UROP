# EventX research status and publication gap assessment

28 October 2026. Assessment of the current report, frozen result summaries and label-free operating status,
with comparison to strong peer-reviewed forecasting and empirical-finance papers. Venue suitability is a
reviewer-style judgment, not an acceptance prediction. No new research cycle or model change is initiated.

## Assessment

EventX supports a substantial undergraduate research report and a promising preliminary empirical study.
It does not yet establish state-of-the-art prediction-market forecasting or a broad result about news
efficiency. The most consequential gaps are comparator strength, breadth of independent evidence, and
the specificity of the scientific contribution. Improving those may be more valuable than increasing
the score of the current booster.

Algorithmic novelty is currently low: the learner is standard histogram gradient boosting. There is
potential empirical and measurement value in examining expiring, heterogeneous prediction contracts,
receipt/source-time differences, endpoint availability, transfer, and operational abstention. None alone
establishes priority over the literature. A benchmark contribution would also need a sufficiently broad,
legally distributable, documented artifact and clear evaluation tasks.

## Verified current evidence

Completed consumption receipts were checked before reading stored June results. No labels were built,
predictions regenerated, bootstrap rerun, model fitted, or protected evaluation opened.

| Quantity | June 1–7 development50 | June 8–14 new identities |
|---|---:|---:|
| Contributing contracts | 18 | 35 |
| Known outcomes | 16,453 | 35,218 |
| Booster log loss | 0.2930988249673845 | 0.4207686547802655 |
| Activity-logistic log loss | 0.3522500571887579 | 0.49430959882643905 |
| Gain in nats | 0.05915123222137342 | 0.07354094404617356 |
| Relative LL reduction | 16.79239818822128% | 14.877506773238913% |
| Booster Brier | 0.0848348206792063 | 0.13351194804222916 |
| Booster AUC | 0.834995182898584 | 0.8266522597439964 |
| Contract-bootstrap 95% CI of gain | [0.039051379707736304, 0.08046837804557748] | [0.03278869199980915, 0.11877411421880779] |
| Issued / scheduled | 19,304 / 96,600 | 39,656 / 77,280 |
| Issued coverage | 19.983436853002072% | 51.31469979296066% |
| Missing / issued | 2,851 / 19,304 | 4,438 / 39,656 |
| All-issued gain bounds vs logistic | [-0.00101045976006508, 0.09980202106005877] | [0.008981253073143031, 0.11364430473132993] |

These are meaningful within-study improvements. They cannot be ranked numerically against papers using
different assets, targets, event-time horizons, label thresholds or metrics. The intervals concern matched
known outcomes. The bounds address unknown labels among issued forecasts, not abstained grids or
nonparticipating contracts. Coverage loss is not synonymous with feed failure: expired/inactive contracts
and frozen quote gates contribute. Those denominators nevertheless limit the population being described.

Canonical sources:
- `data/v7/june_replication_20261026/evaluation/{consumption_receipt.json,result.json}` and
  `data/v7/june_replication_20261026/bootstrap.json`.
- `data/v7/new_identity_test_20261026_recovered/evaluation/{consumption_receipt.json,result.json}`.
- `eventx/release/v7/{june_replication_20261026,new_identity_test_20261026}/protocol.json`.

The V3.1 news result remains a negative development comparison for the specified count features:
1,460,454 OOF rows, 2,290 contributing bootstrap markets; Brier improvement -0.0002844665960089199,
one-sided upper bound -0.00019586714212149262. This does not identify why those features fail or rule out
other information channels. Source: `data/v3_1_historical/news_bound_20261027/result.json`.

Label-free status at 2026-10-28T11:12:30Z: V02b has 7,109 ready forecasts, all with timely commits,
2,581 abstentions and 270 misses, totaling 9,960 elapsed decisions. Issuance coverage is 71.37550200803213%.
Source and emitter status ages were zero seconds, WebSocket connected, corrected clock valid. No accuracy
was read. The status command's process count was zero because sandboxed process listing failed, not
because the jobs were absent. An approved external process check verified source PID14152, emitter14287,
V4 collector12937 and close-out waiter52875. No restart or configuration change was made.

V4 checkpoint: `collecting_sealed_inputs`, 59 completed news days, 52 completed trade days,
last success `2026-10-28T00:01:03.537437Z`, `last_error=null`. This is operational evidence, not a completed
collection/data-integrity gate. V4 and prospective accuracy remain pending. June15–28 remains reserved for
the already-frozen two-model test after live close.

## What strong published work contributes

The following are comparators for research design; their venues have different standards and objectives.
These are not a claim that every work occupies an identical journal tier or that the search is exhaustive.

| Work | Relevant contribution | Implication for EventX |
|---|---|---|
| Zhang, Zohren & Roberts (2019), DeepLOB, IEEE Transactions on Signal Processing | Order-book architecture, benchmark evaluation and a year of LSE data with a three-month test; transfer from five training stocks to five other stocks | New-contract transfer already has precedent; longer temporal replication and matched strong comparators matter more than claiming transfer itself is novel |
| Sirignano & Cont (2019), Quantitative Finance | Large-scale pooled price-formation modelling; tests across stocks/time and against asset-specific linear/nonlinear models | Pooling versus individual-contract learning is a testable scientific question, but EventX cannot yet claim broad invariance |
| Kolm, Turiel & Westray (2023), Mathematical Finance | Multi-horizon forecasts for 115 Nasdaq stocks; order-flow representations improve over many raw-book approaches | Test information representation and forecast horizon, rather than assuming a larger network is the next improvement |
| Croxson & Reade (2014), The Economic Journal | Uses goal arrivals near half-time to isolate major news from ongoing game information | For an information-incorporation claim, exact events and information timing provide a stronger basis than article-volume associations |
| Grinsztajn, Oyallon & Varoquaux (2022), NeurIPS Datasets and Benchmarks | Broad tabular comparison accounting for hyperparameter search, with strong tree models | Standard boosting is a defensible learner; fair tuning and comparative evidence are required before inferring an architecture advantage |

Primary links:
- [DeepLOB](https://www.oxford-man.ox.ac.uk/wp-content/uploads/2020/03/DeepLOB-Deep-Convolutional-Neural-Networks-for-Limit-Order-Books.pdf)
- [Universal features](https://arxiv.org/abs/1803.06917)
- [Deep order flow imbalance](https://onlinelibrary.wiley.com/doi/abs/10.1111/mafi.12413)
- [Information and efficiency](https://academic.oup.com/ej/article-abstract/124/575/62/5076978)
- [Tabular learning benchmark](https://papers.neurips.cc/paper_files/paper/2022/file/0378c7692da36807bdec87ab043cdadc-Paper-Datasets_and_Benchmarks.pdf)

Published work also has limitations: DeepLOB's illustrative trading simulation uses mid-prices without
transaction costs. EventX should not copy that setup and describe it as executable profit. Paper-specific
summaries here rely on the primary full text or author/publisher abstract as available; no exhaustive
systematic literature review or head-to-head empirical reproduction was conducted.

## Ranked improvements for a separately authorized research cycle

### 1. Establish a fair baseline ladder

The headline row_hgb7 model uses 18 inputs versus activity logistic's nine. This is a valid comparison of
complete systems, but not a controlled test of nonlinearity. The legacy HGB also has different training
provenance. V03's full-logistic comparison is stronger in this respect, but it is a separate model/input
contract; it does not repair the primary comparison retroactively.

Suggested next-cycle ladder:

1. Frozen global and shrunk contract rates, plus an adaptive empirical-rate baseline using only outcomes
   that have matured and become available before each decision. Never use pending 30-minute labels.
2. Full-feature regularized logistic regression on exactly the candidate's inputs, with regularization
   selected on purged forward development folds.
3. A spline/GAM baseline and a small prespecified interaction set, to test whether smooth nonlinearities
   explain the improvement.
4. A tuned alternative tree ensemble and a matched retraining of the existing HGB. Match training rows,
   preprocessing, feature availability, validation splits and tuning budgets.
5. A compact temporal CNN or recurrent model if enough independent development data exist. Compare it
   on identical histories, and report the benefit of extra sequence information separately from architecture.

The most informative first experiment is a learner-by-feature-set factorial: logistic, GAM and HGB on
the same nine inputs and on the same full inputs. A newer neural architecture is not required to answer
that question. Published tabular results motivate retaining boosting as a serious reference, not a guarantee
of its superiority in EventX.

Duration/intensity baselines are also relevant, but predict a different object unless adapted. The probability
of at least one quote change is not the probability that the endpoint price differs: changes can reverse.
A duration model requires a marked transition/return component or an explicitly different secondary target.
The new report's description of duration modelling as the direct continuous-time counterpart should be
qualified accordingly. Do not score unadapted arrival probabilities as if they model the same label.

### 2. Expand independent evidence and repair measurement limitations

Prioritize more independent events and time periods over denser overlapping rows. Use a metadata-as-of
selection rule, one defined event-family grouping, and prespecified slices for liquidity, category and time
to expiry. Extend to multiple market regimes and eventually a second venue with harmonized semantics.
Select the scale from cluster-level precision/power planning on development data, not an arbitrary row target.

Separate: (a) chronological transfer on familiar identities; (b) transfer to new event families;
(c) prospective issuance; and (d) venue transfer. Current evidence does not establish all four.
Assess dependence across both events and dates with a justified blocked/multiway scheme; separate contract
and date intervals do not automatically capture joint dependence. A few weeks remain a small temporal sample.

Improve continuity and endpoint observability while recording all failures. Report scores alongside coverage
and all-issued bounds. A future selection/abstention policy must be frozen before its test. Show both a common
eligible panel and operational coverage for models with different input requirements, so selective issuance
does not silently determine the winner. Current retrospective metadata and archive/live differences remain
important even though the source-time V03 design improves compatibility.

### 3. Seek a specific explanatory result

Candidate hypotheses, not established findings:
- Recent activity predicts endpoint changes beyond a calibrated activity-rate or duration-based reference.
- Transfer gains arise from identifiable interactions between activity, price level, spread and expiry regime.
- Apparent archive gains shrink when source-time availability and missing outcomes are handled prospectively.

Choose one primary question, register its contrasts, and use ablations fitted only within development.
Permutation and SHAP-style explanations can describe a fitted model but cannot replace controlled comparisons.
For a finance audience, explain the mechanism and test distinguishing implications. Causal identification is
needed if claiming a causal news effect; it is not a universal requirement for a predictive forecasting paper.

### 4. Improve prediction through information and calibration before complexity

Candidate additions include source-compatible update interarrival times, quote/trade imbalance, spread/depth
dynamics and point-in-time time-to-expiry. Each requires verified live/historical semantics and may require
a new input contract. Adding fields opportunistically to the frozen model is not appropriate.

Test calibration using a dedicated development calibration split or forward cross-fitting; assess LL/Brier
and reliability rather than ECE alone. Compare fixed versus causally updated rate calibration under a
predeclared update schedule. Do not recalibrate from consumed June results and relabel them as confirmation.

A forecast could become more useful without a higher AUC if calibration, availability, latency and coverage
improve. Conversely, better matched AUC with falling coverage need not improve the deployed service.

### 5. Give the news track a viable measurement basis

Before richer text or LLM features, obtain independently reviewed contract-event links, exact information
release times, and first-availability evidence. The current weak link/availability support means a richer
model could learn timing artifacts or context. Compare market-only nonlinear controls, news-volume controls,
context-only controls and genuine incremental content on identical rows. Timestamp-delay and irrelevant-news
controls can be planned on new development data; they are proposed falsification tests, not completed evidence.

V4 must finish under its existing protocol. A negative V4 result would still not establish that public
information has no value. A positive one would need interpretation within its cohort, representation and gates.

### 6. Demonstrate usefulness with a target-aligned decision

Quote activity does not provide a buy/sell direction. A suitable future application might be allocating a
limited monitoring budget or prioritizing contract review. Compare uniform allocation and simple activity
ranking under the same budget and measure captured endpoint changes, calibration and workload. This is a
proposed utility experiment, not a demonstrated application or proof of economic value. A trading extension
would additionally need directional/size information, bid/ask execution, latency, fees, fills and inventory risk.

## Publication positioning and immediate work

For a general ML methods venue, a standard HGB application on a modest cohort currently lacks a clear new
method or broadly reusable benchmark result. For empirical finance, the strongest missing pieces are a sharp
market-information question, measurement/identification, temporal breadth and economic interpretation. For
an applied forecasting or market-microstructure paper, a substantially strengthened empirical comparison is
a plausible development route. These are judgments about present evidence, not predictions of acceptance.

Near the report deadline, preserve the existing studies and complete their authorized close-out. Useful work
now is the literature comparison, explicit limitations, source-to-claim checking, and a written experimental
specification for a future cycle. Heavy analysis and final rendering remain deferred on the live host.

After close, fill the report from the once-only results, including failure or insufficient data. Do not add
new comparators to the frozen late-June/live/V4 test and present them as preregistered primary results.
Any model/baseline selection needs a separately frozen study with genuinely unopened evaluation data.

The highest-priority package for a stronger paper is **matched-feature baselines + longer event-disjoint
prospective evidence + one specific scientific or operational contribution**. A bigger model is optional;
an honest negative result against those stronger baselines is still informative.
