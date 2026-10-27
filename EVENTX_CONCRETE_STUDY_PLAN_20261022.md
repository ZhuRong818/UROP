# EventX: a concrete prospective study

Prepared 22 October 2026. **Design recommendation, not a preregistration or completed experiment.** Evidence below is from the frozen 18–19 October diagnosis; collector status and event yield have not been refreshed for this document.

## 1. The study to pursue

**Question:** Do promptly captured official US economic releases improve forecasts of large, subsequent 30-minute prediction-market movements beyond a fixed market model and release-timing controls?

Study contracts whose outcomes remain unresolved after the release. A release may provide evidence about a later economic outcome without determining it immediately. Such links require an explicit economic rationale and evidence review; topical similarity is insufficient. A contract resolving on the announcement belongs outside this forecasting target, even if its displayed end date is later.

The intended contribution is an auditable measurement of incremental information: trace original evidence through actual availability, contract relevance, market observability and subsequent repricing. The histogram booster is an established algorithm. Novelty would lie in the dataset, measurement design and resulting evidence; priority over related work is not established by this plan.

This is a predictive association study. It cannot by itself establish that news caused a price change or that all public information is efficiently incorporated.

## 2. What the existing evidence permits

The [canonical source diagnosis](data/v7/source_verification_20261018/analysis_v01/report.json) records zero predictive admissions. Three macro samples had two-sided venue books despite empty Lumid quote responses. Their venue/Lumid six-hour trade-row counts were 0/0, 5/5 and 0/0. The Bitcoin activity control returned 183 venue print rows against six Lumid rows; the warehouse also contained six. These are endpoint records, not necessarily distinct transactions.

The [continuity report](data/v7/source_verification_20261018/continuity/20261019T011710Z/report.json) records a largest market journal gap of 13,487.463046 seconds. Source coverage and actual sparse execution are both obstacles. No completed news gain or currently usable cohort follows from successful requests or dense chart histories.

The immediate research deliverable should therefore be a **prospective feasibility dataset with explicit failures**, followed conditionally by a forecasting study.

## 3. Phase A — establish a usable observation process

Prepare a separately versioned direct-venue capture pilot, preserving existing collectors and all frozen studies. Use the diagnosed provider feed as a comparison source. This avoids making new research dependent on an unverified provider repair, while also avoiding silent substitution into old datasets.

Before launch, freeze exact market/token allowlists, source semantics, raw receipt storage, deduplication, pagination, reconnect behavior, observation-gap handling and terminal-status checks. Retain public execution time, local receipt time, durable availability and processing completion separately. Authenticate contract rules and YES mapping. Direct API responses themselves are not proof of complete exchange history.

Run concurrent bounded REST and streaming checks, including a prospectively selected activity control. Reconcile common windows, caps and print conventions; investigate mismatches rather than declaring every stream update a trade. A proposed 24-hour rehearsal tests operations, but cannot certify continuity around a later release. Event windows need their own coverage audit.

For each release, capture at least six hours beforehand and through the last scheduled forecast's 30-minute target. Preserve gaps and acquisition latency. Prefer a reliably available host with explicit outage monitoring; deployment and credentials are separate implementation tasks.

**Exit requirement:** one complete prospective observation passes every existing [readiness gate](data/v7/source_verification_20261018/analysis_v01/observation_gate_contract.json), including verified original evidence. One observation establishes technical feasibility only. It does not justify estimating a news effect or starting a broad tuning search.

## 4. Phase B — measure event yield in a fixed feasibility cohort

Start with scheduled US inflation and employment releases. Add GDP/PCE only if the same predeclared linking rules produce valid longer-lived contracts; simultaneous releases form a shared episode. Keep protected V4 IDs and quarantined families excluded.

Before prices or outcomes from each study window are inspected, freeze:

- An official release calendar and the exact future dates included; recheck current schedules at implementation time.
- Contract discovery rules, metadata cutoff and all accepted and rejected candidates. Select using predicate, period, rule text and expected tradability beyond the target, not subsequent movement.
- The release-to-contract economic channel and evidence role. Reviewers must not see post-release prices. Human review or explicitly labelled assistant review must retain its actual provenance.
- Episode/family identifiers, grouping simultaneous announcements and contracts exposed to the same event. Separate dates can still share dependence.

**Proposed bounded pilot:** the next six scheduled release episodes after source readiness, all identified before capture begins, with a fixed administrative end date. Six is an operational budget, not a statistical sample-size calculation. Record all failures; do not replace quiet or unusable events with exciting ones. This phase is development data and cannot later become untouched confirmation.

Deliver a funnel: scheduled episodes → captured releases → timely evidence → valid contract links → source-complete windows → fresh prices/history → valid forward observations. Report both counts and denominators by episode and contract, including zero-yield episodes.

If no complete observation survives the pilot, stop the current forecasting route and report why. If only a few survive, continue a measurement study and calculate the collection horizon required for a meaningful predictive comparison.

## 5. Specify one target and its clock

Retain the current target:

`Y(t) = 1[abs(logit(pYES(t+30m)) - logit(pYES(t))) >= 4 * sigma240(t)]`

Here `sigma240` is the population standard deviation of trailing 240 one-minute, forward-filled canonical YES log-odds increments under the existing feature convention. It is not a 24-hour volatility estimate. Keep the existing price clipping and feature semantics; explicitly reject missing warmup and invalid or degenerate volatility under a frozen new-cohort rule.

Use the existing five-minute decision grid. Proposed primary event anchor: the first grid point after both the release body and the fixed evidence extractor's output are durably available. Never move the anchor later just to find a fresh trade. Missing anchor observations remain missing. Live predictions must be recorded before their forward targets become observable.

Retain the decision-time screen: canonical YES age ≤5 minutes, at least three YES prints in 60 minutes, at least three in 240 minutes, and at least 100 notional in 240 minutes, with source accounting verified. A proposed new-cohort endpoint rule is the last valid YES trade at or before `t+30m`, at most five minutes old, and received within a fixed acquisition-latency deadline. Freeze that deadline after source rehearsal and before outcome inspection. This is a new eligibility specification, not a retrospective change to historical evaluations.

The market must actually remain unresolved and tradable through the endpoint. No settlement price, quote midpoint or stale chart point substitutes for the required trade price.

Primary estimand: performance among eligible observations at the fixed first event anchor. Also report all attempted anchors and missing-forward rates, because forward-price availability can depend on trading activity. Secondary five-minute paths through 60 minutes after receipt describe adjustment; their overlapping targets are not independent samples.

## 6. A small, interpretable comparison

Keep raw `condition_120k` fixed, SHA256 `d5d5a8c12fd999674f687c712e14f3a4406e7ab5ec34774baf1828f644f73a3c`. New source inputs must pass a feature-semantics compatibility audit before this model is scored.

|Model|Purpose|
|---|---|
|M: frozen market booster|Strong existing market-history reference|
|M+E+T: same base plus exposure/timing correction|Control for scheduled announcements, feed availability and time since receipt|
|M+E+T+C: same correction plus evidence content|Test incremental contract-relevant information|

Use a small regularized logistic correction with the frozen model logit as an offset. Give both corrected models identical training dates, intercept/calibration opportunities and regularization-selection rules. Fit only after the feasibility gate, with enough usable development episodes; do not fit on one successful observation. Limit selection to a small prespecified regularization grid evaluated forward in time.

E/T must be defined from the full preselected release/market panel without semantic filtering by C. Keep missing or irrelevant content as an explicit state. All three models score identical eligible keys, including rows with no usable content.

Initial C features should be a compact, reviewed set: correctly bound statistic and reference period, newly reported value, contemporaneously published revision, change from an already available prior value, evidence role and novelty. A change from the previous release is **not** an expectations surprise. Use an actual-minus-consensus feature only if its pre-release consensus vintage is independently captured. Signed YES/NO support is optional for this absolute-movement task and must not be fabricated when ambiguous.

Human annotations produced after the decision can assess extraction quality. They cannot become as-of features in the primary operational forecast; a retrospective annotation study must be labelled separately.

## 7. Evidence required for a forecasting claim

Primary contrast: `Delta_content = LL(M+E+T) - LL(M+E+T+C)`; positive means content helps. Also report `LL(M) - LL(M+E+T+C)` on the full eligible event panel. An improvement over M alone does not isolate semantic value.

Use log loss as primary, Brier score as secondary, and average precision as descriptive with prevalence and class counts. Lower log loss/Brier is better. Proper scoring rules support probabilistic evaluation; see [Gneiting and Raftery (2007)](https://sites.stat.washington.edu/people/raftery/Research/PDF/Gneiting2007jasa.pdf).

Proposed primary aggregation: average paired loss differences within each release episode, then give each episode equal weight. Report pooled-row results separately. This changes the estimand from the historical row-weighted comparisons, so their numbers are not directly comparable. Group linked shocks/families and account for dependence across dates; equal weighting does not make episodes independent.

Development, tuning and confirmation must use chronologically separated episode groups, with overlapping target windows purged and shared-family dependence addressed. All learned transformations fit on training data only. These choices follow the forecasting-evaluation concerns described by [Hewamalage, Ackermann and Bergmeir (2023)](https://link.springer.com/article/10.1007/s10618-022-00894-5).

Before confirmation, simulate interval coverage and false-positive behavior under the observed dependence and missingness. Existing EventX inference attempts failed; no bootstrap procedure is adopted here. Estimate power for a scientifically useful gain, then freeze episode count, collection deadline, interval procedure and stopping rule. Treat 0.001 nat only as a candidate design effect for this new study; V4's threshold remains specific to V4.

Define success before confirmation: content improves over timing controls by the prespecified meaningful amount, with an interval supporting that claim, and the full model also improves over M. A narrow interval excluding a useful gain supports a bounded negative result. A wide interval supports an inconclusive result. A small cohort does not establish that news is uninformative. Do not stop collection when results first look favorable.

## 8. Deliverables and decision points

|Order|Concrete deliverable|Decision it enables|
|---|---|---|
|1|New source-pilot specification, synchronized reconciliation and continuity report|Can the required market history be observed reliably?|
|2|Frozen episode/contract manifest and reviewable evidence rules|Are relevant, still-tradable markets available prospectively?|
|3|One full observation dossier: raw hashes, clocks, evidence, history, endpoint and gate reasons|Does the existing trade-based target work at all?|
|4|Six-episode feasibility ledger, including rejected observations|What is usable event yield and the likely collection horizon?|
|5|Development comparison and validated inference/power design|Is a future confirmation feasible and worth collecting?|
|6|Separate preregistration, frozen models and untouched future evaluation|Is there credible incremental predictive information?|

If trade freshness fails despite verified source coverage, a quote-based information-absorption study is a plausible separate branch. It requires new target semantics, spread/depth and stale/crossed-book rules, a new baseline and independent evaluation. Current trade-model results cannot be claimed for that branch.

The near-term paper contribution can be the validated information-to-observation funnel and a measured explanation of feasibility failures. A predictive paper additionally needs adequate independent evidence and future confirmation. Neither publication nor a positive news effect is guaranteed by this plan.

## Work completed for this recommendation

Read CURRENT_STATE and AGENTS; inspected the frozen diagnosis, gate contract, source plan, continuity/report references and delivery manifest. Created this design document and updated the handoff/history. No collector launch/change, source fetch, model fit, scoring, new eligibility admission, external message or protected evaluation was performed. Proposed dates, thresholds and source choices require an implementation freeze; this document is not that freeze.
