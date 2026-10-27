# EventX clock alignment and repeated input readiness

26 October 2026. Canonical correction: **source_time_study_20261026_v03**.

The independent clock audit supports a small host-clock offset rather than assuming every exchange timestamp must precede a locally recorded receipt. V03 therefore replaces exact cross-clock ordering with a bounded ordering check while retaining both as-of gates. Raw times are unchanged. The correction was frozen before rebuilding development data and before the fresh readiness capture. No prospective forecasting test has started.

The completed readiness result is recorded in the delivery section below; a connected stream alone does not pass the gate.

## Evidence and what it establishes

The previous strict-clock capture rejected 84/92 price-change records because their source times were ahead of local durable availability by up to 91 ms. It produced zero fully ready decisions. That failure remains frozen.

The new audit made nine read-only SNTP queries across Google, Cloudflare and Apple and twelve public CLOB server-time requests. No system clock settings were changed. The initial sandbox DNS failure was preserved; the successful requests used approved network access.

| Reference | Initial offset estimate, remote minus local | Reported uncertainty | Interpretation |
|---|---:|---:|---|
| Google, three probes | +58.124 to +61.000 ms | 7.302–9.534 ms | Local clock behind this reference during these measurements |
| Cloudflare, three probes | +58.456 to +59.916 ms | 82.468–84.773 ms | Compatible with Google; less precise |
| Apple, three initial queries | Summaries excluded | 566.569–581.099 ms | Native selected packets were zero/invalid; summaries are not valid offset estimates |

Google and Cloudflare offset signs and values were checked against their raw four-timestamp exchanges. The calculation estimates remote-minus-local offset from the two directions of the exchange; transport delay and reference error must be considered when interpreting it. The displayed uncertainties are not statistical confidence intervals. [NTP specification, RFC 5905](https://www.rfc-editor.org/rfc/rfc5905.html#section-8).

An initial verification script tried to equate every native summary with the first packet calculation and failed on Apple. Inspection found zero selected packets despite exit code zero. Those Apple summaries had already exceeded the frozen precision limit and were not used to establish the correction. The final audit retains this limitation and validates selected packets for clock measurements that could admit a decision.

The official market-stream schema describes the price-change timestamp as Unix milliseconds. The CLOB server-time endpoint returns integer seconds. Neither source establishes a millisecond-accuracy guarantee shared by the WebSocket server and the laptop. The twelve HTTP replies are therefore coarse consistency checks, not proof of a 91 ms venue offset. [Official WebSocket schema](https://docs.polymarket.com/asyncapi.json), [official CLOB API specification](https://docs.polymarket.com/api-spec/clob-openapi.yaml).

These contemporary measurements cannot reconstruct the host offset during the earlier capture. They also do not identify precisely when the exchange assigns an event timestamp relative to matching-engine processing. The study remains a forecast of the **observed quote process**, not a causal estimate of information arrival or exchange processing latency.

## Separately frozen correction

V03 requires all of the following for a price-change observation to contribute at decision time `t`:

1. Durable availability is at or before `t`.
2. Source timestamp is also at or before `t`.
3. Apparent source-minus-durable lead is at most **250 ms**.
4. Source age is at most 120 seconds, with the unchanged quote-quality, tie and lag rules.

The 250 ms limit is a declared engineering cap with margin over the measured local offset and previously observed 91 ms lead. It is **not a confidence bound or a venue service guarantee**. No tolerance sweep or forecast-result selection was performed. An excessively ahead-of-receipt latest observation fails the clock gate. A source time later than the decision is rejected even when its lead would fit inside the 250 ms budget.

No timestamp is shifted, clipped to receipt time, backdated or replaced. Actual durable availability remains the causal cutoff. Signed and absolute changes and missingness indicators are still computed separately as of each lag clock.

The repeated live run adds independent clock monitoring:

- Latest completed probe must already be available at the decision and be no more than 360 seconds old.
- At least two different providers must have reported uncertainty no greater than 100 ms, including at least one no greater than 20 ms.
- Their offset intervals must overlap, and that intersection must lie within **±100 ms**.
- A wall-clock versus monotonic-clock step exceeding 20 ms resets the 30-minute transport warmup.

The frozen model and readiness thresholds are not weakened when a probe fails. For example, the first live probe's approximately 94 ms offset was borderline because its uncertainty extended beyond the 100 ms budget. A later probe near 63 ms passed. Both observations remain in the journal.

Reading macOS automatic-time configuration returned an administrator-access requirement. No privileged clock inspection, synchronization or adjustment was performed.

## Consistent development rebuild

All May 7–9 development features and targets were rebuilt under V03, and the same four fixed learners were refitted. **All 41,400 grid rows, including features and targets, and all 3,688 development prediction rows are identical to corrected V02.** The archive's clock relationships therefore do not change the evaluated development examples under this correction.

The booster still has development log loss **0.3585589345042676**, versus logistic **0.42678936650339094**, a **15.986910020304176% reduction**. Brier remains **0.11137085419290263** versus **0.129403343713303**. This is unchanged exploratory development evidence, not a new predictive gain caused by clock handling.

The final refit has 9,406 known rows across 20 contracts. The 586 unknown May 9 endpoints remain unknown; all-issued gain bounds versus logistic still cross zero. Previous test blocks and protected holdouts were not opened or used for tuning.

Verification passed 38 unit checks, replayed all 3,688 saved development predictions and recomputed the four matched metric sets. The new model bundle explicitly binds the V03 input contract. Old models and failures remain intact.

## Why a fresh repetition is necessary

A feature-only replay of the earlier failed capture gives 8 quote-valid decisions under V03 versus 3 under V02 on the same 16 grids. Two decisions also satisfy its old post-warmup transport/metadata checks. This is a mechanism diagnostic only: that older capture has no contemporaneous independent clock monitor, so those two decisions do **not** constitute a retrospectively passed live gate.

The new capture uses the same two metadata-defined contracts, a fixed 40-minute duration, the unchanged five-minute grid and 30-minute warmup. Strict V02 and corrected V03 are compared on the same new messages, with the same current clock, transport and metadata checks. There are no forecasts, live targets, trades, cohort replacements or extensions to obtain a passing result.

## Review artifacts

- [Clock probes and primary-source receipts](data/v7/clock_alignment_20261026/report.json)
- [Raw-packet and old-capture semantics QA](data/v7/source_time_study_20261026_v03/clock_semantics_qa.json)
- [Frozen V03 protocol](eventx/release/v7/source_time_study_20261026_v03/protocol.json)
- [Development report](data/v7/source_time_study_20261026_v03/development/report.json)
- [Development parity QA](data/v7/source_time_study_20261026_v03/development_qa.json)
- [Repeated readiness audit](data/v7/source_time_study_20261026_v03/readiness_audit/report.json)
- [Repeated clock diagnosis](data/v7/source_time_study_20261026_v03/clock_repeat_diagnosis.json)

The future seven-day forecast test still requires a separate activation receipt and a frozen live emitter/evaluator. Any completed readiness capture is a dated operational check; a subsequent service must establish its own warmup and continue enforcing clock-health checks.

## Completed repeat and decision

The fresh capture ran **2026-10-26T08:38:58.908625+00:00 to 2026-10-26T09:18:58.981186+00:00**. Normal bounded completion: **True**. It is now stopped; no forecast service was started.

| Contract | Scheduled grids | Strict quote-valid | Corrected quote-valid | Strict fully ready | Corrected fully ready |
|---|---:|---:|---:|---:|---:|
| Negative GDP growth in 2026? | 8 | 3 | 3 | 2 | 2 |
| US recession by end of 2026? | 8 | 3 | 3 | 2 | 2 |

On identical captured messages, fully ready decisions changed from **4 under strict V02 to 4 under V03**. Contributing contracts: 2. The fixed input gate **passed**; combined development/input gates **passed**. This is input availability, not forecast accuracy.

Both rules admitted the same number of decisions in this repeat. None of its source timestamps led durable availability, so this capture does **not** demonstrate an incremental coverage gain caused by the 250 ms correction. The earlier failure and this successful repeat are different observation windows and must not be treated as a controlled improvement comparison.

There were 8 clock-probe rounds, 7 passing at their completion times, and 0 detected wall/monotonic steps over 20 ms. Of 100 price-change rows, 0 had source timestamps ahead of durable availability; 0 exceeded the 250 ms cap. The exact per-grid abstention reasons and clock measurements are preserved in the audit and diagnosis.

The final audit checked 24 native selected packets; 24 were valid. Every packet eligible to contribute to the clock gate passed the raw-packet check. All 16 feature decisions and 16 clock decisions were reproduced using only observations available by their own decision times.

![Clock measurements and matched input readiness](data/v7/source_time_study_20261026_v03/clock_readiness.png)

The next step is to freeze the live prediction emitter and evaluator, including online native-packet validation, and bind them to an activation receipt for the seven-day test. A new service must warm up again and maintain the clock/metadata/source gates. This small successful rehearsal does not establish sustained coverage, predictive superiority or enough independent observations for a paper.

**No prospective test has started, no live forecasts were issued and no live labels were constructed.**
