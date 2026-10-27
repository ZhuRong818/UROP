# V7 development specification and confirmation gates

Date: 10 October 2026. Development preparation is authorized and started. This specification is not a confirmatory freeze. V4, V5 and V6 retain their existing controlling designs. Current outputs are a new macro review packet, descriptive rule recovery, source/window feasibility and a synthetic inference screen; no V7 forecasting model has been fit.

## 1. Questions and populations

Forecasting question: does automated contract-specific evidence improve the probability forecast of a large remaining 30-minute movement beyond a strong market model and article exposure/timing?

Begin with U.S. monetary-policy, inflation and employment news and the associated unresolved macro contracts. Domain membership is fixed from metadata and broad keyword routes before price outcomes. The historical pilot is an enriched retrospective development sample. Its human judgments can establish measurement examples, not confirm forecasting performance or production precision.

Two designs remain distinct:

- **Grid study:** all eligible five-minute observations in a prospectively declared domain contract cohort, including observations without articles. The primary content contrast is mean log loss of M+E+T minus M+E+T+R+S. Report the final model versus M on the same full population as a performance guardrail. Primary weighting is one vote per eligible row; event-balanced loss is secondary.
- **Event study:** one decision at `t0+5 minutes` per contract-information episode, measuring the next 30 minutes. Weight episodes equally, averaging within episode over its eligible contracts. This diagnoses remaining repricing after system access; it does not measure the immediate response to public release. It requires independently reviewed episode identity and a deployable trigger; a gold-trigger analysis is explicitly an oracle diagnostic, not a deployable forecast claim.

No result-guided choice between these populations or horizons is allowed. For a paper centered on delayed adjustment, the event study requires its own final freeze and primary contrast. The grid and event estimands must not share a pooled significance claim.

## 2. Clocks, overlap and outcomes

Keep publication, official release if evidenced, provider ingestion, exact version availability and local first observation separately. Prospective prediction time uses the maximum of all required availability clocks, including local observation of the exact bytes; retrospective acquisition time cannot establish historical availability. The pilot's derived historical clock is retained as a source diagnostic, not certified first public time.

Retain the established threshold recipe for continuity: last observed executed canonical-YES price, clipped to [0.0001,0.9999], one-minute carry-forward log odds, trailing 240-minute population volatility with at least 30 differences, and `y = sigma>0 and abs(logodds(t+30)-logodds(t)) >= 4*sigma`. It is a heuristic threshold. Require at decision time at least three positive executions and 100 units of YES-price-times-size notional in the trailing 240 minutes, latest execution age at most 60 minutes, an active contract and a known terminal beyond the full horizon. The new adapter must prove what trade records were observable; no future trade-arrival eligibility rule is allowed.

Keep price-age strata at 0–5, >5–30 and >30–60 minutes; activity interactions use trailing counts/notional and age. Call these activity proxies unless valid quotes permit spread/depth analysis. Quotes are optional diagnostics and cannot silently replace the primary trade endpoint. A complete stream with no future trade gives carried-forward unchanged price; unknown endpoint coverage gives missing outcome and an explicit denominator loss. Record missingness per arm identically and retain fallback analysis separately.

For event sampling, collapse duplicates/versions and prespecify one landmark per episode-contract. Combine same-episode updates arriving before the landmark using only those then available. Overlap across different episodes remains in an episode/family/calendar dependency ledger; it is not removed using later price movement. A release on a contract already closed cannot enter a post-release forecast. Restrict to still-unresolved downstream predicates when announcement contracts close before their release. Independent human episode IDs do not prove calendar independence.

## 3. Comparator and candidate algorithms

All arms share keys, market history and training weights. M starts with the selected no-terminal seven-leaf histogram booster: 600 iterations, maximum depth 3, learning rate 0.05, minimum leaf size 100, L2 10, seed 907. Its historical gain remains exploratory. Retain L2 logistic as an explicit weak-baseline ablation. Historical terminal fields are excluded; verified time-to-known-terminal can be a separately declared ablation after source timing is fixed.

E uses complete declared feed coverage, source/calendar indicators and raw article occurrence. T uses time since available arrival and trailing counts at 5, 30 and 120 minutes. The main control observes all articles in the fixed feed opportunity set, not just semantically accepted ones. Broad keyword routing is an additional declared text-based exposure control; it cannot be called content-neutral. R never changes E/T's opportunity mask or the scored population.

R includes supported subject, action/metric, period/meeting, comparator/threshold, evidence role and ambiguity. S initially means **signed new evidence**, not measured surprise. Preserve direction and magnitude separately and interact them with market state. Surprise stays missing unless an independent expectation was recorded before the release. A YES-favoring claim is not an additive update to the probability of a future unsigned movement.

Bound the next development algorithm comparison to: (a) lexical BM25 plus explicit abstention, (b) the existing typed-predicate/role linker, and (c) a span-constrained extractor with a fixed local model and schema. Do not auto-promote a neural score as evidence. The local model and decoding implementation are not selected yet; existing NLI/format failures remain failures. Compare on the same independently reviewed development cases, reporting coverage, unknowns and errors. Choose one candidate before any new evaluation episode is opened. Gold labels supply oracle diagnostics only; predictions need a frozen automatic extractor or a real-time human service whose timestamps and availability are captured.

Use forward development folds with a 30-minute horizon purge; no story or contract-family component spans a train/validation boundary. If reviewed dependencies cause conflicts, exclude the affected component with a ledger rather than repair it from outcomes. Fit vocabulary, embeddings, scalers, novelty memory and calibration using training data only. Retain at most three predefined ridge penalties, 0.001/0.01/0.1, for a market-logit offset; select using pooled forward development loss with stronger penalty on exact ties. The same correction family and budget apply to context and news. Calibration and feature selection cannot use confirmation data.

## 4. Inference and useful gain

The fixed screen covers irregular episode counts, shared day shocks, persistence and a random regime shift. Neither IID episode normal intervals, calendar-cluster normal intervals nor the specified 14-day Bartlett HAC intervals pass all declared cases. None is adopted. Oracle known-DGP variance is a design reference, not an available estimator. Assumed 0.02-nat shock/noise scales are not estimated EventX noise.

The tested 0.001/0.003-nat gains are sensitivity values, not adopted practical thresholds. Estimate loss-difference scales and episode/calendar dependence only from opened development once usable labels exist. Define the useful effect from a stated forecasting objective before confirmation; do not raise it merely to make power look adequate. Require power at least 80% at that useful effect and a prespecified coverage/type-I simulation gate matched to the claimed population. Retain an explicitly descriptive study if a defensible inferential design is unavailable. Switching an existing V5 claim to conditional-calendar inference is not authorized by this new specification.

For the eventual frozen study, classify confirmed useful gain, harm, useful-gain exclusion and inconclusive using predeclared bounds, threshold and guardrail. A zero-crossing interval that permits useful gain is inconclusive. Secondary horizons (5, 15 and 60 minutes), direction, role and activity interactions remain exploratory unless assigned multiplicity control before evaluation. V4's 0.001-nat promotion rule remains specific to V4.

## 5. What must be resolved before confirmation

1. Receive two independent outcome-blind reviews and one adjudication, retaining unknowns; verify diverse information episodes and hard-negative/miss labels.
2. Complete active-status, exact contract-rule/version, feed/window and trade-arrival evidence for the chosen source; unknown windows remain unknown. Development annotation proceeds without waiting for a support-day certificate.
3. Implement and fix the automatic semantic pipeline; do not substitute offline gold evidence at prediction time.
4. Obtain forward-development loss differences and real episode yield, then a defensible inference/power result and practical effect threshold.
5. Choose a new evaluation interval after all selected implementation hashes are frozen, disjoint from V4 and consumed historical holdouts, with a fresh exposure/consumption ledger. No dates are fixed from eventual V4 performance. Do not invent an untouched retrospective period.
6. Freeze cohort, clocks, source adapters, target, candidate budget, features, weights, inference, date boundaries and one-shot gates. Only then collect/evaluate confirmatory observations under that protocol.

The current development packet is ready. Human annotations, deployable semantic measurement, empirical power, untouched dates and a forecasting freeze are outstanding; claiming them complete would overstate the work.
