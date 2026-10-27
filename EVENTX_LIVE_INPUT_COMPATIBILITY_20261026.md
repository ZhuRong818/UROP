# EventX: live inputs for the quote-change classifier

26 October 2026. Input engineering and label-blind replay only.

The archive feature calculation now has an exact replay implementation, and the live WebSocket projection is implemented. **The existing 18-feature classifier cannot yet be admitted to the live feed:** its receipt-group features depend on collector behavior that has not been shown equivalent. A separately versioned, shared 14-feature measurement removes those dependencies. It requires a new fitted model and validation; the existing classifier's performance does not transfer to it.

## 1. What was established

- Reproduced **10,969 current-valid development feature vectors exactly**, with maximum absolute error **0.0**. May 7/8/9 contributed 3,592/3,709/3,668 vectors from 41,400 scheduled grids. These counts include inputs without known forward outcomes; they differ from the 9,212 rows used in the earlier refit.
- Parsed the closed two-contract WebSocket capture with **zero projection errors**. The YES projection contains 5,657 price-change rows, 19 book rows and one trade row.
- Preserved exchange time, wire receipt time and durable availability separately. Live availability is rounded upward to milliseconds; nothing is backdated.
- Added a guard that rejects the live candidate contract at the frozen model's input boundary.
- Implemented a second, shared source-time feature contract for archive and live observations. It excludes receipt-group counts and numerical message ages while retaining causal availability and freshness gates.

The first adapter has 12 passing unit tests; the second has nine. Tests cover asset/condition identity, missing and malformed inputs, clocks, conflicting quotes, missing lags, duplicate behavior, future-data invariance and explicit model incompatibility.

## 2. Why an ordinary column mapping is insufficient

The development archive contains 1,416,544 events. All 1,415,679 `price_change` rows have top quotes; all 810 `book`, 54 `last_trade_price` and one `tick_size_change` rows have null top quotes. Deriving new BBOs from book depth would therefore change the old measurement process.

The published collector exports BBOs from price-change messages and stores other event types without those fields. Its sink/schema indicate a database insertion default for `timestamp_received`; its ingestion pipeline also applies deduplication. These observations are pinned to commit `cb0f6631556bf460d03594fe20f9bbd020b47d19`, dated 31 July 2026. **The exact May deployment is unverified.** This is source-code evidence, not proof of the May service configuration. See the [collector exporter](https://github.com/pmxt-dev/polymarket-orderbook-collector/blob/cb0f6631556bf460d03594fe20f9bbd020b47d19/services/r2-archive/exporter/run.py), [sink](https://github.com/pmxt-dev/polymarket-orderbook-collector/blob/cb0f6631556bf460d03594fe20f9bbd020b47d19/shared/rust/polymarket-orderbook-rust/src/sink.rs) and [deduplication implementation](https://github.com/pmxt-dev/polymarket-orderbook-collector/blob/cb0f6631556bf460d03594fe20f9bbd020b47d19/shared/rust/polymarket-orderbook-rust/src/ws/dedup.rs).

The archive has 942,224 market/receipt-time groups, including 288,207 multirow groups. One group contains 60 rows; source times within a receipt group span as much as 16.360000133514404 seconds. The original classifier counts valid **receipt groups**, not individual exchange updates.

This matters even on the same captured live messages: substituting wire receipt time for durable availability changes the update-count feature on 38 decisions and valid-state fraction on 30. Receipt age changes on 260; one eligibility decision and one five-minute missing-lag indicator change. Maximum durable-storage delay is only 0.06900191307067871 seconds. There are also 1,687 repeated asset/hash occurrences in the complete stream; repetition alone does not establish which records the archive collector would have discarded.

## 3. Feature mapping and the repair

| Feature family | Existing 18-feature model | Shared 14-feature candidate |
|---|---|---|
| Midpoint, logit midpoint, spread | Latest valid receipt group | Latest available exchange-source timestamp |
| Source age and receipt age | Two numerical predictors | Removed as predictors; freshness remains an eligibility rule |
| UTC hour sine/cosine | Two predictors | Retained |
| Valid update count in 30 minutes | Log of valid receipt-group count plus one | Removed |
| Valid-state fraction in 30 minutes | Valid receipt groups / all groups | Removed |
| 5/15/30-minute changes | Signed difference, absolute difference, missing flag | Same feature families, recomputed using the new source-time measurement |

Both projections use identified YES tokens and decimal-four quote precision. The new definition uses only directly supplied price-change BBOs, as documented for the [venue market stream](https://docs.polymarket.com/market-data/realtime-data). It does not reconstruct a book or substitute REST quotes.

For each decision or lag clock, only messages already available at that clock may contribute. Source age must be at most 120 seconds, source time must not exceed availability, and the latest source-time quote must satisfy `0 < bid <= ask < 1` with spread at most 0.05. Repeated identical values collapse; conflicting quotes at the same source timestamp are unknown. An invalid latest quote does not fall back to an older valid one. An older, out-of-order update does not overwrite a newer source-time quote. Lags are computed as of their own clocks, so later delivery cannot retrospectively repair them.

Decision grids remain every five minutes from 00:30 through 23:25 UTC. The source-time process is deliberately a **new measurement contract**: null book events no longer invalidate it, receipt batches no longer determine order, and the numerical predictor set changes. Do not place these inputs into the frozen 18-feature booster or attach its historical scores to the new representation.

Removing collector-dependent predictors does not make receivers identical. Missing messages, different arrival times, source-version differences and incomplete metadata can still change eligibility and features. The empirical replay measures sensitivity on this capture; it does not prove venue delivery completeness.

## 4. Operational admission

The original 18-feature replay has 281 quote-eligible decisions out of 562 scheduled decisions. With live transport, daily-grid, current metadata, unresolved status and expiry checks, 196 are mechanically ready: 109 GDP decisions and 87 recession decisions. **Frozen-model admissions remain zero.** Mechanical readiness is an input diagnostic, not a forecast or a performance result.

Live operational checks require a connected stream, recent application pong, 30-minute warmup after a known interruption, fresh identity/rules/status evidence, and scheduled expiry beyond the 30-minute horizon. Unknown information remains an abstention. The closed source has not been restarted by this work.

The separate source-time replay is recorded in `data/v7/live_input_compatibility_20261026/source_time_v2/report.json`; its ledger preserves every scheduled decision, including missing inputs.

| Replay population | Scheduled decisions | New quote-eligible inputs | Mechanically ready |
|---|---:|---:|---:|
| May 7 development | 13,800 | 3,620 | Not a live operational test |
| May 8 development | 13,800 | 3,776 | Not a live operational test |
| May 9 development | 13,800 | 3,688 | Not a live operational test |
| Closed GDP live capture | 281 | 164 | 122 |
| Closed recession live capture | 281 | 122 | 89 |

The new definition produces **11,084 development vectors**, including all 10,969 previously valid decisions and 115 additional decisions. It yields **286 quote-eligible and 211 mechanically ready live decisions**. These are changed measurement/coverage counts, not evidence of improved prediction. The old live quote-only diagnostic includes off-grid feature attempts whereas the new one enforces the daily grid; the mechanically-ready counts both enforce it.

For the new definition, wire versus durable clocks change eligibility on two decisions. Among decisions eligible under both clocks, each lag's signed and absolute difference changes on one decision; the five-minute missing flag changes on two, and the 15/30-minute missing flags on one each. Current midpoint, spread and time-of-day features are unchanged in this sensitivity replay. This remaining boundary sensitivity is preserved rather than hidden by backdating availability.

## 5. What must happen before a prospective forecast test

1. Use the new source-time contract for a separately fitted classifier and baselines. Freeze its target definition using the same observed quote process at the current and 30-minute endpoint; unavailable endpoints must remain unknown. Do not reuse old target arrays silently.
2. Fit and select only on allowed development data. The already opened April and May test periods cannot confirm this redesign. Freeze a new evaluation plan, model, cohort and inference code before accessing a fresh evaluation block.
3. Run a label-blind live readiness capture on metadata-defined active contracts. Preserve clocks, reconnects, schema errors, payload hashes and every scheduled abstention. Require actual current coverage; the closed two-contract capture is insufficient to establish broad availability.
4. Start a prospective test only after the model and operational input gates pass. Retain all issued forecasts and missing outcomes; compare the new model with matched baselines on the same target and rows.

An alternative is to obtain the original archive collector's May deployment, receipt-clock and deduplication evidence and establish equivalence for the old model. No external request has been sent. The shared source-time route avoids relying on a reconstruction of receipt-batch features, but still requires fresh predictive validation.

## 6. Reproducibility and scope

- Original adapter, tests and parity audit: `eventx/v7/live_quote_inputs_20261026.py`, `eventx/tasks/check_v7_live_quote_inputs_20261026.py`, `eventx/tasks/audit_v7_live_input_compatibility_20261026.py`.
- New measurement, tests and replay: `eventx/v7/source_time_quote_inputs_20261026.py`, `eventx/tasks/check_v7_source_time_quote_inputs_20261026.py`, `eventx/tasks/audit_v7_source_time_inputs_20261026.py`.
- Original frozen audit: `data/v7/live_input_compatibility_20261026/manifest.json`.
- New frozen audit: `data/v7/live_input_compatibility_20261026/source_time_v2/manifest.json`.
- Copied and hashed primary source: `eventx/release/v7/live_input_compatibility_20261026/upstream/source_receipt.json`.

No labels were read for these input audits, no model was fitted or modified, no prediction metrics were computed, and no prospective test was started. Protected holdouts and previously frozen artifacts remain unchanged. Feature coverage is not predictive accuracy, and no baseline improvement is claimed for the new representation.
