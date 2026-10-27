# Alternative linking algorithms — exploratory development

Compared TF-IDF word/bigram cosine, cached MS-MARCO MiniLM cross-encoder logits,
and that neural ranker constrained by same-sentence subjects and event-channel
evidence. Inputs: previous180 pairs/22 opened-development articles and18 authored
examples across6 scenarios. Receipt records candidate IDs, synthetic cases, input
hashes and pinned model revision before scoring. Model file hashes verified.

| Algorithm | Intended example above both synthetic negatives |
|---|---:|
| TF-IDF | 5/6 |
| Neural cross-encoder | 6/6 |
| Constrained neural cross-encoder | 6/6 |

Scenarios cover negotiations, acquisitions, AI ranking, asset prices, index inclusion
and earnings, with wrong-actor/wrong-relation negatives. Opposite-direction news can
remain relevant. These authored probes are not independent gold or real accuracy;
six scenarios cannot establish superiority. Constraints were designed alongside them.
TF-IDF is fitted jointly on diagnostic texts, not evaluated as a prospective model.

Real-data constraints yield15 provisional event-channel candidates and165 abstentions.
All15 remain uncertified, with zero predictive admissions. They come from only3
articles: US–Iran negotiation context, SpaceX valuation and a reported opinion about
Anthropic. Repeated contract deadlines inflate pair counts. Opinion is not a measured
leaderboard rank; current valuation is not an IPO settlement observation; talks do
not establish a signed deal. Event-channel candidates are a new weaker tier, NOT an
accuracy improvement over the old zero direct matches.

No acceptance threshold fitted or model promoted. Cached neural scores are neither
calibrated probabilities nor entailment certificates; model historical eligibility
remains uncertified. Inference was offline CPU/bfloat16, four threads, eager attention,
384-token maximum. No downloading, new training, annotation or protected data access.
All130 related software tests pass, including7 new relation-constraint tests.

Next: period/claim-role constraints distinguishing updates, measurements, opinions
and background. Missing close_time must not mask expired stated deadlines. Retain
neural-plus-constraints as exploratory; do not tune thresholds on these six examples.

Implementation: `eventx/v6/relation_candidates.py`; runner:
`eventx/tasks/compare_v6_link_algorithms.py`. Immutable comparison outputs:
`data/v6/link_algorithm_comparison_20260919/` (receipt, scores, report, manifest).
