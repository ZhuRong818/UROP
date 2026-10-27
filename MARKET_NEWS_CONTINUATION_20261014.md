# EventX research continuation — 14 October 2026

The latest `condition_120k` market model has now been compared directly with exposure calibration, article timing and relaxed unsigned policy context. **Exposure calibration has the lowest log loss; the tested timing/context additions do not beat that control.** This is opened historical development evidence, not independent confirmation.

## Matched forecasting result

| Model | All 112,616 rows: log loss | Article-exposed 5,388 rows: log loss | Exposed Brier | Exposed AP |
|---|---:|---:|---:|---:|
| M — selected market only | 0.342948929815 | 0.242722439562 | 0.078022336243 | 0.354569694112 |
| E — exposure calibration | **0.342929884610** | **0.242324370760** | 0.077911731310 | 0.354569694112 |
| T — E + article timing | 0.342933285944 | 0.242395462930 | 0.077889380642 | 0.355894469666 |
| C — fixed T + unsigned context | 0.342932941284 | 0.242388259086 | **0.077885845543** | **0.355959330947** |

Lower log loss/Brier is better; higher average precision is better. Models are compared on identical market/time keys and labels within each population. Do not compare the exposed scores directly with the all-population scores as if they measured an improvement: the populations differ.

Exposure calibration improves exposed log loss versus raw market by **0.00039806880153231097 nats/row**. C improves versus T by only **0.000007203843363788398 nats/row** on the exposed population, and is still worse than E by **0.0000638883264548 nats/row**. Its slight Brier/AP improvements do not establish a robust content benefit, and its full-population AP remains below raw market AP.

## Algorithm and controls

The existing selected market forecasts remain the baseline; no market booster was refit. The E/T corrections fit on 4,577 article-exposed fold-4 rows and report on fold 5. E has an intercept and market-logit adjustment. T adds article count, latest article age and publisher count over the unchanged 30-minute availability window. Each correction uses fixed L2 penalty 0.1 with training-only scaling.

C freezes T's predictions and fits two gated unsigned-context coefficients: presence and standardized count. The context correction is **exactly zero outside covered rows**. This prevents a small apparent content benefit arising solely from refitting the timing-control coefficients. All choices and input/code hashes were receipted before the new fits. No hyperparameter search or new selection was performed.

The existing exposure population comes from legacy semantic routing. The C-versus-T comparison therefore concerns additional policy-context selection/count information conditional on that population; it does not isolate a causal effect of external news or a fully content-neutral exposure design.

## Why the context result cannot establish predictive value

Only **55 fitting rows** carry the new context feature. In evaluation it reaches **six articles, 17 rows and three markets**. **All 17 evaluation labels are negative**. AP and ROC AUC are undefined within that subset.

| Model | Log loss on those same 17 rows |
|---|---:|
| M | **0.199919775670** |
| E | 0.240271702991 |
| T | 0.235400370068 |
| C | 0.233117175477 |

C slightly lowers T's predictions on these negative rows, but remains worse than raw market on the same subset. This cannot demonstrate improved detection of movement events. The original all-history yield of 144 articles/1,056 rows does not imply a sufficiently diverse later evaluation population. No significance or independent-event count is claimed.

## Development evidence review

A single assistant inspection categorized all 100 fixed review candidates before new forecast scores. It is not independent human annotation, semantic gold or a measured accuracy estimate. The review was not used to select model inputs or relabel candidates.

| Coarse article role | Articles |
|---|---:|
| Market expectation or reaction | 40 |
| Peripheral investment discussion or opinion | 25 |
| Calendar or meeting preview | 10 |
| Attributed forecast or policy analysis | 9 |
| Reported decision or minutes | 9 |
| Official statement | 6 |
| Explicit prediction-market odds repetition | 1 |

The assistant review describes 74 articles as plausible policy context and 26 as uncertain/peripheral. Exact contract correctness and novelty remain unreviewed/unknown. Automated diagnostic flags include 23 possible repetitions of market expectations, ten past-policy backgrounds and six summaries containing Bloomberg sidebars. These categories overlap and are not validated error rates.

Among the 144 primary-covered candidates, there is one exact duplicate-headline group and nine exact normalized-summary groups. Exact summary grouping removed sidebar suffixes for the diagnostic only. It does not certify same-story identity or merge information episodes. Independent review and broader episode grouping remain necessary.

## Prospective collection

Label-blind V4 check at **2026-10-14 08:01:46 UTC** confirms collector and guard alive, 45 news days and 38 trade days checkpointed through 13 October, 425 receipt sets, zero closed-day backlog and all 15 frozen hashes matching. No protected downstream artifacts exist. The check read process/checkpoint/receipt metadata and frozen code hashes, not sealed data or outcomes. Source completeness remains uncertified. The original 30 October close and consumption sequence control the prospective experiment.

## Next research action

1. Continue market calibration and condition robustness work, preserving raw M as the selected strong baseline. E's gain is small and developmental, so it is not promoted from this comparison.
2. Review the six later-fold context articles and recover distinct timely information events with positive and negative movement examples. Larger generic article counts alone do not resolve the event-yield problem.
3. Independently review material relevance, background/market-odds repetition and episode boundaries before a new confirmatory content study. Use a separately defined untouched interval and validated dependence inference.
4. Keep V4 collection healthy through its original close and follow its frozen one-shot audit sequence afterward.

## Canonical artifacts

- [Machine-readable comparison](data/v7/strong_market_context_comparison_20261014/report.json)
- [Pre-fit contract](data/v7/strong_market_context_comparison_20261014/contract.json)
- [Assistant development review](data/v7/strong_market_context_comparison_20261014/assistant_context_review_100.jsonl)
- [Review/duplicate diagnostics](data/v7/strong_market_context_comparison_20261014/review_report.json)
- [Predictions and matched keys](data/v7/strong_market_context_comparison_20261014/predictions.npz)
- [V4 operational check](data/v4/health_checks/20261014T080146Z/report.json)

The consumed OOT and V3.1 holdouts were not accessed. No frozen model, source, eligibility, target or association rules were altered. No deployment or candidate promotion occurred.
