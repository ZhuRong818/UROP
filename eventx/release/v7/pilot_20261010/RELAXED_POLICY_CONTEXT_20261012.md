# Relaxed policy-context yield — 12 October 2026

## Result

**The 100-article development candidate target is achievable without changing market eligibility or the availability clock.**

| Stage | Articles | Existing OOF rows within 30 minutes |
|---|---:|---:|
| Previous exact signed extractor | 2 | 0 |
| New policy-decision context, before row screening | 331 | — |
| Policy-decision context with row coverage | **144** | **1,056** |
| Broader topic + decision context with coverage | 154 | 1,093 |
| Selected policy-decision review package | **100** | See link-level traces |

All 147,377 deduplicated documents and 479,179 legacy candidate associations were processed. The broader context extractor retained 9,338 associations: 8,196 decision-context links and 1,142 topic-context links, across 380 articles and 29 markets. Distinct articles are not independent episodes; the policy-decision covered population spans 32 arrival dates.

## What was loosened

Exact evidence required the action to imply the specific contract month, quantity and bucket. The new v0.4 development tier accepts Fed and policy-rate language in the same text segment, including forecasts, conditional statements and market expectations. Decision-language context is distinguished from broader topic context. Exact month and amount entailment is not required. **Direction remains unknown**: no YES/NO signal or information surprise is inferred from these contextual matches.

Conservative system availability, existing market decision eligibility, held-group keys and the primary 30-minute window were preserved. The 60/180-minute windows are descriptive sensitivity only, not the selected task. No labels were read and no forecasting model was fit.

## The remaining bottleneck

| Existing fold | Covered decision-context articles | Covered rows |
|---|---:|---:|
| 1 | 51 | 440 |
| 2 | 71 | 537 |
| 3 | 3 | 7 |
| 4 | 13 | 55 |
| 5 | **6** | **17** |

Counts are deduplicated within each fold; do not sum article counts to infer independent events. Earlier-fold concentration means the overall 144-article yield does not imply 100 usable articles in the latest fold. At 60 minutes fold 5 has eight articles/28 rows; at 180 minutes fourteen/62. Widening the window does not establish useful predictive information.

This operational coverage screen does not validate semantic relevance, historic contract status or feed completeness. Broad context can include investment commentary, stale forecasts and coverage repeating market expectations. For example, the packet includes conditional Fed statements and dividend/ETF commentary; review must distinguish direct information from peripheral coverage.

## Deliverables and next step

- [100 policy-decision articles, readable review package](../../../../data/v7/relaxed_policy_context_v04_1_20261012/POLICY_DECISION_REVIEW_100.md)
- [Structured blank review packet](../../../../data/v7/relaxed_policy_context_v04_1_20261012/policy_decision_review_100.jsonl)
- [Full coverage report](../../../../data/v7/relaxed_policy_context_v04_1_20261012/report.json)

Review the 100 candidates for material relevance and evidence role, then group repeated coverage into event episodes. A subsequent development comparison should use the selected strong market model plus exposure/timing controls versus unsigned policy context, on identical keys. Report all-population and exposed-subset outcomes separately. The latest-fold sample is presently too small for a strong independent claim; do not change frozen V4 or use consumed holdouts to enlarge it.

## Execution record

The first run completed candidate processing but failed JSON serialization on a NumPy integer. Its partial output remains in `data/v7/relaxed_policy_context_20261012/`. A separate corrected run in `relaxed_policy_context_v04_1_20261012` completed with identical extraction rules and a fresh code receipt. Thirty-six input hashes, availability clocks and evidence spans matched. No software tests were run. Code, reports and review packet are hash-receipted.
