# EventX: collector V02 integration and source validation

Report timestamp: 2026-10-22T11:00:13.225770+00:00. **Source study only; no prediction evaluation.**

## Completed

- Created and froze a separate V02 collector and audit; retained the exact 22-market sample (14 prospective macro candidates, three legacy diagnostics, five controls).
- Integrated independent fixed endpoint queues: trades every 2 seconds, books every 0.5 seconds, metadata every 1 second, provider REST every 2 seconds. Each queue stays locked through its response and backoff update.
- Recorded queue, actual dispatch, response and durable availability clocks. Added a bounded shutdown with explicit cancellation records and numeric/HTTP-date Retry-After parsing.
- Finished the five-minute live validation. Verified 2,129 journal records and 1,707 payloads. All 25 frozen files and 20 original production locks matched.
- Preserved the failed sandbox DNS attempt and its audit. Original services and frozen market model were not changed. No test suite was added or rerun; prior component tests remain separate evidence.

## Live validation result

| Measure | Result |
|---|---|
| HTTP responses | {"200": 420, "404": 10, "None": 32} |
| Request statuses | {"cancelled_before_dispatch": 32, "failed_http": 10, "observed": 420} |
| Stream disconnect records | {} |
| Candidate mappings and rules matched | 14/14 |
| Comparable macro windows | 23 |
| Candidate activity passes | 0 windows; 0/14 markets |
| Predictive admissions | 0 |

Pacing and in-flight overlap diagnostics are in `report.json`. These examine actual receipts; they do not establish source completeness. Queue cancellation at the deadline is distinct from a failed HTTP response. The full REST cycle can exceed 60 seconds because it waits for all endpoint groups; configured cadence must not be reported as achieved cadence.

## Original 24-hour rehearsal: still incomplete

The frozen interim audit at 2026-10-22T10:51:37.887878+00:00 verified 119,595 payloads. It recorded seven HTTP429 responses, 77 HTTP502 responses, 746 deferred requests, 271 other request failures, 15 WebSocket disconnects and 16 SSE disconnects. The largest successful trade receipt gap was **41.38 minutes**. Causes are unresolved; local/network/provider interruptions must not be assigned from heartbeat alone.

There were 602 comparable macro windows and 0 activity passes. These windows overlap and are not independent events. A 240-minute elapsed run does not demonstrate 240 minutes of timely, complete data.

## Interpretation

The implementation is now concrete and the bounded capture has run. A clean five-minute interval, if observed, would not prove the scheduler cured the original interruptions or rate limits. The original collector ran concurrently, and the observation periods differ. No forecast was scored and no metric was adjusted.

The remaining bottlenecks are source continuity, sparse eligible trades, and the absence of a complete prospectively captured release observation. Keep the selected market model frozen and event activation disabled.

## Next execution gates

1. Review the original rehearsal's automatic final audit after **23 October 05:58 UTC / 13:58 Singapore**. Separate DNS/connection failures, HTTP failures, stream gaps and genuine zero-trade responses.
2. Resolve continuity and source-field compatibility, then freeze and run a longer V02 source rehearsal before activating event capture. The five-minute run does not replace the original 24-hour criterion.
3. Prespecify forward-price freshness and receipt latency, verify actual terminal conditions, and assemble one full event dossier: original evidence availability, valid trailing 240-minute history, fresh decision price and valid 30-minute forward price.
4. First reserved release is **29 October 12:30 UTC**; the staged six-hour warmup starts **06:30 UTC**, conditional on readiness. Six reserved episodes remain a feasibility sample, not a powered confirmation.
5. If verified feeds still yield no trade-based eligible observations, record that feasibility result and design a separately frozen quote-based study; do not silently substitute quotes into the current target.

## Evidence

- New source audit: `data/v7/direct_source_pilot_20261022_v02/audits/20261022T110002Z_aac90e`
- Original interim audit: `data/v7/direct_source_pilot_20261022/audits/20261022T105137Z_f62ac0`
- V02 freeze: `eventx/release/v7/direct_source_pilot_20261022_v02/implementation_manifest.json`
- Machine-readable validation: `data/v7/direct_source_pilot_20261022_v02/validation_v01/report.json`
