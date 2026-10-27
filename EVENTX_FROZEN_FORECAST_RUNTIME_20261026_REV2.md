# EventX: frozen forecast runtime and fresh readiness

26 October 2026. Runtime release: `forecast_runtime_20261026_v01`.

The live forecast emitter and evaluator are frozen against the existing V03 protocol. The market model, baselines, target, cohort and thresholds are unchanged. A separate 40-minute input-only rehearsal is required before activation. **No activation receipt has been created and no prospective test has started.**

## What is frozen

| Component | Behavior |
|---|---|
| Target | Probability that the observed YES midpoint differs 30 minutes later; not direction, resolution or profit |
| Models | Existing V03 histogram booster, full-feature logistic regression, global event rate and shrunk contract rate |
| Inputs | Existing 14 source-time features, 120-second freshness, 250-millisecond cross-clock lead cap; both source and durable-availability times must precede the decision |
| Clock check | Validate the raw selected SNTP packet before applying the existing independent-provider offset checks |
| Forecast deadline | Decision must be durably written by grid time +30 seconds; a commit binds its hash, source prefix and measured completion time |
| Missing input | Retain an abstention or missed decision; never backfill a forecast |
| Endpoint capture | Record a source-prefix receipt at endpoint +120 seconds, with up to 30 seconds of scheduling grace; endpoint information cutoff remains the endpoint itself |
| Missing endpoint | Late/missing receipt, invalid quote, failed clock/transport check or interrupted metadata coverage leaves the target unknown |
| Evaluation | After the complete window and operational grace, audit frozen files and replay forecasts; write an exclusive consumption receipt before constructing targets and scoring |
| Reporting | All four models on matched known outcomes, all scheduled coverage, unknown-outcome gain bounds, nonoverlap, per-contract/date metrics, calibration and equal-contract loss |

The emitter constructs no online labels and computes no live performance. Its endpoint receipts preserve the evidence available for later adjudication. The evaluator retains unknown outcomes and failed comparisons.

The seven-day window remains fixed: the first full UTC date after a separate activation receipt, seven consecutive dates, daily five-minute grids from 00:30 through 23:25 UTC. The receipt must bind the model, protocol, cohort, implementation and completed readiness report. The emitter and source collector refuse prospective operation without it.

The existing development gain—15.99% lower log loss than logistic regression—is unchanged. Freezing runtime code is an operational milestone, not new forecasting evidence.

## Verification

The pre-freeze suite passed **51 checks**, including **25 new runtime checks**. These cover clock-packet rejection, stale/future clocks, interruption warmup, future-data exclusion, endpoint status gaps, missing endpoints, forecast deadlines, journal corruption, duplicate decisions, unknown-outcome bounds and absent activation.

A separate synthetic integration check exercised the actual emitter and evaluator entry points using generated quotes and the frozen model. It verified a timely forecast, an abstention, endpoint receipts without online labels, early-opening rejection and refusal of a second evaluation. Its one-grid synthetic fixture is not a prospective study or a live accuracy result.

The runtime manifest freezes 41 code/configuration/model dependencies and records Python/package versions. SHA-256:

`e1594c1bb5d862345fc39553d8ae854dcf39c58b71e8fd6f120653acf5a4197e`

## Fresh operational rehearsal

The fixed capture started **26 October 2026, 11:26:11 UTC** and was scheduled to stop at **12:06:11 UTC**. It uses the same two contracts and the same clock, source, metadata and transport gates as the frozen emitter. It scores no model and constructs no target.

The gate requires normal completion, no schema/scope failures, and at least two fully ready market-decisions across at least one market after 30 minutes of transport warmup. Strict and bounded timestamp rules are compared on identical captured messages. The completed audit result is recorded below; a connected stream alone is insufficient.

## Operational limits before activation

This is a short rehearsal on two contracts. Passing does not establish sustained coverage, adequate statistical power or improved live accuracy. A newly started source must warm up again and maintain the gates throughout the experiment.

The source collector deliberately refuses an implicit restart into an existing source directory. A source-process crash therefore requires an explicit, versioned recovery decision; it cannot silently reuse stale warmup. The emitter can resume its existing journal, retain completed decisions and mark elapsed opportunities as missed.

No activation command is part of this preparation task. No protected holdout, historical test, news experiment, trading action or remote SSH host is used.

## Review package

- [Frozen runtime policy](eventx/release/v7/forecast_runtime_20261026_v01/runtime_policy.json)
- [Implementation manifest](eventx/release/v7/forecast_runtime_20261026_v01/implementation_manifest.json)
- [Pre-freeze checks](eventx/release/v7/forecast_runtime_20261026_v01/qa.json)
- [Synthetic integration check](data/v7/forecast_runtime_20261026_v01/integration_qa.json)
- [Activation schema—this is not an activation receipt](eventx/release/v7/forecast_runtime_20261026_v01/activation_schema.json)
- [Parent V03 protocol](eventx/release/v7/source_time_study_20261026_v03/protocol.json)

## Completed rehearsal result

The collector stopped at **2026-10-26T12:06:11.716248+00:00**. Normal fixed-duration completion: **False**. Fresh input gate: **FAIL**.

| Measurement | Result |
|---|---:|
| Scheduled market-decisions | 16 |
| Fully ready under frozen runtime | 0 |
| Fully ready under strict timestamp comparison | 0 |
| Contributing contracts | 0 |
| Valid native selected packets | 6/24 |
| Detected clock steps | 1 |
| Live forecasts issued | 0 |
| Live labels constructed | 0 |

Decision exclusion counts overlap: `transport_history_warming`: 16, `insufficient_precise_independent_clocks`: 12, `quote_missing_stale_invalid_or_conflicting`: 6, `host_clock_offset_exceeds100ms_budget`: 4.

For diagnosis only, 0 post-warmup decisions satisfied the other gates when clock failures were ignored. This does not admit those decisions or override the frozen clock requirement.

**Activation remains blocked by the fresh input gate.** Preserve this failed rehearsal. Address the recorded measurement/availability problem under a separately justified version and repeat the unchanged readiness design; do not reuse the earlier successful capture as a substitute. No threshold was relaxed, model retuned or capture extended to produce a pass.

The native SNTP command returned some unusable selected-packet records. Exit code zero is not sufficient clock evidence. The runtime correctly excludes invalid packets; their printed offsets must not be interpreted as actual host offsets. The raw exchange/selection discrepancy needs investigation before replacing this measurement method.

Clock steps were also observed: -109.910 ms at 2026-10-26T11:51:08.535541+00:00. Each step reset the 30-minute transport warmup. A working replacement clock adapter alone would not remove this separate operational issue: the host must sustain the frozen clock and uninterrupted-warmup requirements. No system clock setting was changed by this task.

[Readiness audit](data/v7/forecast_runtime_20261026_v01/readiness_audit/report.json) · [Per-grid diagnosis](data/v7/forecast_runtime_20261026_v01/readiness_diagnosis.json)

**No activation receipt exists, no forecast service is running, and no prospective test has started.**

## Completion-clock clarification

The collector recorded its deadline event and shut down, rather than failing with an unhandled exception. However, its recorded wall-clock stop precedes the scheduled wall-clock stop by **117.089 ms**, so the frozen auditor correctly reports `normal_completion: false` under its strict comparison. The first-to-last logged monotonic interval was **2399.985994 seconds**, while the logged wall interval was **2399.850486 seconds**. These are different clocks; the observed discrepancy must remain visible.

This does not rescue the readiness result: all 16 decisions were still within required transport warmup after the detected discontinuity, and clock evidence failed at every scheduled grid. Any future revision of deadline accounting or the native clock adapter must be separately frozen before another capture. No tolerance was changed retrospectively.

[Completion timing evidence](data/v7/forecast_runtime_20261026_v01/completion_timing.json). This revision adds explanation only; the original report, code freeze and failed audit remain unchanged.
