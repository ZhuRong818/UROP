# EventX: new-contract transfer test and V02 live runtime

26 October 2026. Versions `new_identity_test_20261026` (evaluated from `new_identity_test_20261026_recovered`) and `forecast_runtime_20261026_v02`.

**Both frozen quote-change boosters transfer to 40 never-used contracts on the unopened week June 8–14. Each beats every baseline, and the 95% contract-clustered bootstrap intervals exclude zero. A V02 live runtime was built to remove the host-clock failure of V01, with a 30-contract metadata-selected cohort. Its rehearsal result is recorded below.**

## 1. New-contract transfer test (June 8–14)

**Cohort selection.** Only identity, event-type and clock columns were read, from 2026-06-07 T12 and T13 (an already-consumed date), plus current Gamma metadata. No price, quote or outcome column was read before the cohort froze. Rules:
- market IDs in the hex range `[0x10, 0x18)`, disjoint from every earlier cohort (all below `0x0a`);
- at least two book events in both hours;
- not in the 1,231 protected IDs or the earlier 60;
- binary Yes/No, with no event shared with earlier cohorts and one contract per event;
- start before June 8 and end after June 15;
- taken in salted-hash order.

151 candidates and 103 metadata lookups gave 40 contracts across sports, politics, finance, tech and geopolitics.

**Protocol deviation.** A local DNS outage failed 74 hours on both permitted fetch attempts with `[Errno 8]` errors. Before any evaluation, only those hours were refetched with the same code into a separate `_recovered` directory. All 74 recovered, so 165 of 168 hours are available. The other 3 hours are genuine archive 404s and remain missing. The original 91-hour source is preserved and was never evaluated. The refetch is outcome-blind but exceeds the single-retry rule.

**Primary result: `row_hgb7`, the 18-feature booster.** These are matched known outcomes from 35 contributing contracts in 35 distinct events, 35,218 known and 8,830 positive.

| Model | Log loss | Brier | AUC | Booster LL reduction |
|---|---:|---:|---:|---:|
| **row_hgb7** | **0.4208** | **0.1335** | 0.827 | — |
| activity logistic | 0.4943 | 0.1584 | 0.756 | 14.9% |
| legacy HGB | 0.4873 | 0.1547 | 0.785 | 13.6% |
| global / contract rate | 0.5843 | 0.1945 | 0.500 | 28.0% |

All prespecified pass conditions hold.

- **Bootstrap.** The 95% contract-clustered interval for the gain over logistic is [0.0328, 0.1188] nats, from 35 clusters. Resampling by date gives [0.0474, 0.0942].
- **Consistency.** The booster wins on 7/7 dates and 27/35 contracts. Its equal-contract log loss is 0.4222, versus 0.5134 for logistic.
- **Subsets.** The nonoverlapping subset gives 0.4146 versus 0.4859, and the strict subset 0.2029 versus 0.2948.
- **Missing labels.** The bounds over all 39,656 issued forecasts are [+0.0090, +0.1136] nats versus logistic. They are positive even if every unknown endpoint went against the booster.

**Secondary result: frozen V03 14-feature booster, the live-runtime model.** This was registered in an addendum before evaluation. It has 35,749 known outcomes and 9,122 positives.

| Model | Log loss | Brier | AUC |
|---|---:|---:|---:|
| **V03 hgb7** | **0.4270** | **0.1358** | 0.825 |
| full logistic | 0.5316 | 0.1716 | 0.766 |
| global rate | 0.5865 | 0.1960 | 0.500 |

That is a 19.7% log-loss reduction versus logistic. The contract-clustered interval is [0.0661, 0.1472] nats, and the booster wins on 31/35 contracts. This passes the addendum criterion, so V03 is fit to run on a larger, newly selected live cohort.

**Evidence ladder.** The development gain is unchanged, the same-cohort result holds on the unopened June 1–7 block (16.8%), and it now transfers to unseen contracts on unopened June 8–14 (14.9%, or 19.7% for V03).

**Limits.**
- This is historical replay using current metadata; it is not live issuance.
- Observations are dependent.
- One venue.
- Prevalence on the new cohort (25%) is higher than in development, and the booster's advantage held regardless.
- The target is quote activity only, not direction, profit or news.

## 2. V02 live runtime

V01 stays frozen. Its fresh rehearsal failed on host-clock discipline: macOS `sntp` returned empty packets, and a −110 ms OS step reset warmup.

V02 makes these changes:
- **SNTP client.** A pure-Python client keeps the raw 48-byte replies and recomputes each offset from them. Validation checks the header and stratum, the originate echo, wall-versus-monotonic agreement during the exchange, and the round-trip delay.
- **Corrected time.** Every record carries `corrected_epoch`: the latest valid estimate, carried forward on the monotonic clock. An estimate needs two or more hosts, one with half-delay of 20 ms or less, agreeing intervals, and residual uncertainty of 50 ms or less. Raw wall times are retained.
- **Clock gate and steps.** Decisions require a valid estimate no older than 360 s. OS clock steps are logged for audit only and cannot move corrected time.
- **Corrected-time logic.** Availability, transport warmup, metadata freshness, deadlines and emission timing all use corrected time. The run deadline is monotonic.
- **Unchanged.** The model, features, target, freshness, spread and 250 ms lead rules are V03's.
- **Cohort.** 30 contracts were chosen by metadata only, with no prices read. Rules: active, binary, order book enabled, a single "posed" resolution, end on or after Nov 10, older than 7 days, 24-hour volume of at least $10k as a floor only, salted-hash order, and one contract per event. Protected IDs and both earlier cohorts are excluded. The Gamma API capped pages at 100 rows, so the pool was 500 markets rather than the planned 1,000, of which 62 were eligible.
- **Checks.** 18 synthetic V02 checks pass, and the V01 suite (25) still passes unchanged.

**Rehearsal attempts.** All are preserved.

1. **Startup crash.** The inherited `save()` needed `stop_at`. Fixed.
2. **WebSocket before clock.** During the DNS outage the first probe was imprecise (41 ms half-delays), so `ws_connected` was logged without a corrected time. The transport check would never have seen the connection. The run was stopped after about 5 minutes and not audited. Fixed: the WebSocket now waits for a valid anchor, and a regression check was added.
3. **Full 60-minute run, 15:10–16:10 UTC: PASSED.**
   - The run reached its monotonic deadline normally.
   - **164/180** post-warmup decisions were fully ready, across **28/30** contracts. All 16 non-ready decisions failed only on missing or stale quotes.
   - 61 of 63 clock estimates were valid, and every one re-validated from raw packets.
   - **4 OS clock steps** were absorbed with no effect; under V01, each would have reset warmup.
   - 0 corrected-stamp errors, 0 causal-replay mismatches, 0 schema errors and 0 uncorrectable records.
   - V01, by comparison, got 0/16.

## 3. Pre-activation changes and activation

All of these changes were made **before any prospective decision**.

- **Window shortened to 3 full UTC days**, for the 1 November report deadline. The evaluation opens Friday 30 Oct, 07:57 Singapore time. See `protocol_addendum_window.json`.
- **Bounded, incremental inputs and a single-pass evaluator.** The first activation was stopped before its first grid and archived as `superseded_activation_1/` with zero forecasts. The problem was cost: about 317 MB per hour held in memory and a full journal scan per decision. By day 3 that meant about 25 GB and roughly 30 s per grid, plus an evaluator taking many hours.
  - `BoundedInputs` keeps 3 h of history; every rule looks back 32 minutes at most.
  - It matched the unbounded inputs in **510/510** decision and endpoint comparisons, with pruning exercised (`bounded_equivalence_qa.json`).
  - Decisions now take 11 ms per 30 markets, down from 370 ms.
  - A sandboxed end-to-end run of the real evaluator, including its once-only refusal, passes. 31 checks in total.
- **Readiness binding.** Readiness ran on the pre-change code. The exact pre-change manifest was reconstructed and its hash matches the one the readiness run recorded. Activation verifies that only the documented files differ; the collector is byte-identical to the readiness run.
- **Second supersession: thread race.** Activation 2 (16:25 UTC) was also stopped with zero forecasts and archived as `superseded_activation_2/`.
  - The clock worker thread called `log()` concurrently with the event loop, which forked the source hash chain.
  - The emitter's chain check caught it while pre-loading, and the evaluator would also have refused the journal.
  - Fix: probes run in a thread, but estimation and logging happen only on the event loop (with a regression check). Readiness was re-run on the fixed collector:
    - **PASS**: 156/180 post-warmup decisions ready, 27/30 contracts, 58/61 clock estimates valid, 1 clock step absorbed;
    - 0 chain breaks, stamp errors or replay mismatches.
  - The earlier passing readiness is preserved as `readiness_v1_passed_pre_threadfix/`.
- **Activated 17:53:53 UTC, 26 Oct.** An emitter supervisor (`scripts/supervise_v7_emitter_20261026_v02.sh`) restarts the resumable emitter if it exits. It never restarts the source.

**Live status, 27 Oct 01:08 UTC.** The source, emitter and supervisor are all running, with 0 emitter restarts. After 8 grids, 181 of 240 decisions are ready, and all 181 have timely commits.

**Known defect: the first grid abstained.** All 30 decisions at 00:30 UTC abstained with `pong_missing_or_old`.
- **Cause:** a wrapper handoff bug. V01's loop calls `Inputs(source, samples)` on its first grid and only calls `refresh()` on later grids. My wrapper returned the pre-primed `BoundedInputs` object at that first call, and that object was last advanced at `first_grid-60`. So the 00:30 decision saw source data about 60 s old (`source_bytes` 245.9 MB, against 248.8 MB at 00:35), and the last pong it could see was more than 35 s old.
- **Effect:** the error is fail-closed. That grid's decisions are recorded as abstentions, and no future information can enter.
- **Scope:** it costs 30 of 24,840 scheduled decisions (0.12%). Every grid from 00:35 onward refreshes normally.
- **No patch:** the running emitter is frozen, so it was not changed. The evaluation will count these as abstentions.

**Incident, 27 Oct 03:24–04:41 UTC: host memory stalls during a concurrent job.**
- **What happened:** the host's swap was already nearly full (20.3/21.5 GB, mostly desktop apps). My concurrent historical-evaluation QA job (a June 8–14 rerun) pushed the Mac into heavy swapping. The source stopped receiving pongs from 03:31:27 to 03:47:22, and again from 04:10 to 04:11.
- **Effect:** the emitter missed the emission deadlines for the 03:25, 03:35, 03:40 and 03:45 grids, which are recorded as `missed`. The transport warmup then restarted twice, and grids up to about 04:40 abstained with `transport_history_warming`.
- **Integrity:** every effect is fail-closed, and nothing was backfilled.
- **Response:** no heavy jobs run on this host until the window closes on 30 Oct 00:00 UTC. The June 15–28 capture is deferred until after the close.
- **Normal venue drops:** separately, the venue WebSocket drops about once an hour or more (18:49, 19:54, 01:27). Each drop costs 30 minutes of warmup by rule.

| Item | Value |
|---|---|
| Grids | 2026-10-27 00:30 → 2026-10-29 23:25 UTC, every 5 min, 30 contracts (24,840 scheduled) |
| Evaluation opens | 2026-10-29 23:57:30 UTC (Fri 07:57 SGT) |
| Health check | `.venv/bin/python -m eventx.tasks.status_v7_forecast_runtime_20261026_v02` (label-free) |
| Evaluate once | `.venv/bin/python -m eventx.tasks.evaluate_v7_forecast_runtime_20261026_v02` |

**Operational requirements.** The Mac must stay on AC power, awake (lid open) and online until 30 Oct 00:00 UTC. A source crash cannot be restarted into the same run; affected grids are recorded as abstentions, never backfilled. The emitter can resume its journal.

## Files

- New-identity: `eventx/release/v7/new_identity_test_20261026/`, `eventx/tasks/run_v7_new_identity_test_20261026.py`, `eventx/tasks/evaluate_v7_new_identity_v03_20261026.py`, `eventx/tasks/recover_v7_new_identity_capture_20261026.py`, `data/v7/new_identity_test_20261026_recovered/{evaluation,evaluation_v03}/result.json`
- V02 runtime: `eventx/release/v7/forecast_runtime_20261026_v02/`, `eventx/v7/{forecast_runtime_20261026_v02,sntp_client_20261026}.py`, `eventx/tasks/{collect,run,evaluate,check,select,activate}_v7_*_20261026_v02.py`, `eventx/tasks/audit_v7_forecast_runtime_readiness_20261026_v02.py`
