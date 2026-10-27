# Contract-specific evidence schema v0.2

This is a new development schema. It does not overwrite rubric v0.1 or either submitted response.

## Separate annotation objects

1. **Applicability** describes only the selected evidence span's relationship to the canonical contract predicate: `exact_predicate`, `material_context`, `topic_only`, `incompatible`, or `unknown`.
2. **Claim type** describes what the selected span asserts: `observed_measurement`, `observed_action`, `forecast`, `general_market_expectation`, `commentary`, `mixed`, or `unknown`. It is multi-label when a span contains more than one claim.
3. **Source attribution** records the speaker/source separately: source name, `official_source`, `named_analyst_or_institution`, `unnamed_market_participants`, `journalist`, or `unknown`; `direct`/`reported_by_article`; and the exact attribution span. A reported official measurement remains both an observed measurement and attributed reporting.
4. **Expectation content** distinguishes `none`, `general_market_expectation`, and `explicit_prediction_market_odds`. Explicit prediction-market odds require a named prediction market or contract plus a quoted probability, price, or odds span. “Traders expect,” “markets brace,” and conventional futures/yield expectations are general expectations.
5. **Information-event identity** identifies the information arrival, not the contract outcome: issuer/source, release/action/forecast, reference period, claim timestamp if evidenced, conservative system availability, content hash, and parent/update lineage. `contract_event_id` separately identifies the future settlement event or meeting.

## Direction and surprise

`direction` is relative to canonical YES and is annotated only when the selected claim plus contract terms support `yes` or `no`; otherwise use `ambiguous`, `not_applicable`, or `unknown`. Store modality separately so a forecast is never converted into an observed action. Signed evidence is not a forecast of an unsigned price move.

`public_surprise` remains `unknown` unless a timestamped, independent pre-event expectation and the realized value are both available. General expectation language and article adjectives such as “surprising” do not establish a numerical surprise signal.

## Predicate and null policy

The predicate object has `subject`, `metric_or_action`, `comparator`, `threshold_or_unit`, `period_or_meeting`, and `resolution_source`. Each component stores an exact contract span or a null with one of: `not_in_supplied_contract_text`, `not_applicable_to_predicate`, `ambiguous`, or `reviewer_omission`. Exact/material cases must not use an unexplained null. Use minimal spans; a full question is not a substitute when a component has a narrower span.

## Episode and timing policy

Exact-content duplicates and syndicated versions share a parent information event. A later article repeating a dated official release is an update/repeat, not a new release event. An article may map to several contracts but contributes one information episode unless it contains distinct, separately timestamped claims. Publication, official release, provider ingestion, conservative `available_at`, and local observation remain separate clocks. A pair at/after nominal close is excluded from post-arrival forecasting; missing historical active status stays unknown.

## Automatic feature contract

The v0.2 automatic extractor may emit claim type, attribution type, expectation flags, applicability, and signed direction. It must abstain when entity, metric/action, period/meeting, or threshold binding is insufficient. It never emits public surprise. Gold or assistant labels may diagnose it but are not prediction-time inputs.
