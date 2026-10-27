# Contract-specific evidence rubric v0.1

This is a development rubric. Two reviewers work independently without prices, future outcomes, retrieval scores, strata, prior labels or each other's responses. Record reviewer pseudonym, human/assistant identity, prior exposure and whether this blinding instruction was followed. An assistant review is not an independent human review.

## Fields

| Field | Allowed values / instructions |
|---|---|
| applicability | `exact_predicate`, `material_context`, `topic_only`, `incompatible`, `unknown` |
| role | `official_measurement_or_action`, `attributed_reporting`, `opinion_or_forecast`, `market_odds_reporting`, `mixed`, `unknown` |
| direction | `yes`, `no`, `ambiguous`, `not_applicable`, `unknown`; direction concerns the canonical YES resolution predicate, not the probability of a large future move |
| novelty | `new_in_supplied_context`, `repeat_in_supplied_context`, `update_in_supplied_context`, `unknown`; no public-information novelty claim |
| public_surprise | `unknown` unless a timestamped independent pre-event expectation is supplied; this packet supplies none |
| market_odds_content | `yes`, `no`, `mixed`, `unknown`; mixed articles can also carry external evidence |
| episode_key | Human-proposed event identity: issuing institution, release/action, reference period and event date; `unknown` permitted. Article publication date alone is not an event ID |
| duplicate_of | ID of an earlier supplied article if evidenced; otherwise null; nonexact syndication needs explanation |
| predicate | Structured subject, metric/action, comparator, threshold/unit, period/meeting and resolution source, each with exact contract spans or null |
| evidence_spans | Exact article spans with `field`, Unicode code-point `start`, `end`, `text`, and `purpose`; end is exclusive |
| prior_evidence_spans | Earlier article ID plus exact headline/summary spans supporting repeat/update judgments |
| rationale | Brief relation between supported article claim and exact predicate; identify missing facts and attribution |

`exact_predicate` requires matching entity, metric/action, reference period and relevant outcome condition. A Fed mention is not enough for a specific meeting-rate contract. `material_context` needs an explicit, plausible information channel to the predicate, but supplies no direct outcome evidence. Topic overlap without that channel is `topic_only`. Wrong country, period, metric, actor or logically contrary binding is `incompatible` when evidenced. Missing resolution terms or insufficient text can require `unknown` even with a plausible match.

YES/NO direction requires supported contract-specific reasoning. A cut prediction does not imply every annual cut-count contract is YES. Lower inflation does not automatically favor YES for an unspecified threshold or meeting. Preserve modality: a commentator's forecast is not an observed central-bank action. Ignore navigation, related-story sidebars and snippets unrelated to the main story. Split mixed external and market-derived evidence spans.

## Novelty and source validity

Distinguish an article's claim from independently new evidence. Compare only earlier available supplied reports; if that context is inadequate, use unknown. No expectation is provided, so numerical surprise and the time information first became public remain unknown. Do not infer novelty from a different publisher, headline or later timestamp alone.

Semantic review does not certify news versions, feed completeness, active market status, historical rules or quote/trade arrival. Those are separate source fields. Retrospectively valid semantics can still be unavailable for forecasting. Absence of a rule or a trade is not evidence that a contract was inactive.

## Agreement and adjudication

Preserve both responses. Report agreement per field and class, unknown rates and event diversity. Inspect disagreements once with a separate adjudicator; retain original answers and an exact evidence-based final decision. Unresolved cases remain unknown. Do not count agreement on selected positives as overall retrieval recall. A new held-out policy audit is a later study; this developmental annotation cannot rescue the closed V6 audit.
