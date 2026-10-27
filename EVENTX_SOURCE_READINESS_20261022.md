# EventX: interim source readiness and next implementation

**22 October 2026. The source rehearsal is running; event-period capture is not activated.**

The audit cutoff is 06:37:15 UTC, when the rehearsal was 38.824333 minutes old. Its fixed deadline remains **23 October at 05:58:25 UTC / 13:58:25 Singapore**. All three collector processes were verified present during this task.

## What the audit found

|Measure|Observed result|
|---|---:|
|Raw payloads verified|18,051|
|Successful REST responses|2,821|
|HTTP 404 responses|70|
|HTTP 429 responses|2|
|Requests deferred during backoff|209|
|Largest gap between successful trade receipts|180.063379 seconds|
|New macro candidates passing the activity screen in any comparable window|0 / 14|
|Complete predictive observations|0|

All 14 candidates' rules and YES mappings matched at least once. The 98 comparable macro windows overlap and are repeated diagnostics, not independent events or forecast observations.

Both HTTP 429 responses came from the venue trade endpoint. The collector honored their backoff, but its shared venue backoff also deferred 125 book requests and 22 metadata requests, alongside 62 trade requests. This identifies a consequence of the current scheduling design; the underlying cause of the rate-limit responses remains unknown.

The venue stream delivered 54 book events, 16,917 price-change events and six last-trade-price events. No stream disconnect was recorded in this snapshot. The provider stream delivered an acknowledgement and 77 heartbeats, with no market-data event. These observations do not certify complete execution coverage.

## Work completed

1. Created a frozen interim audit and a machine-readable readiness report with per-market results.
2. Prepared a separate request scheduler component with fixed endpoint buckets, one request in flight per bucket, numeric/date Retry-After handling, and support for propagating a server-wide backoff.
3. Passed six focused scheduler tests covering backoff isolation, pacing, concurrency, global restrictions, cancellation and retry headers. The component is not integrated or deployed; no reduction in live rate-limit responses is claimed.
4. Prepared all six reserved event-capture windows, from six hours before each scheduled release until three hours afterward. These are operational windows, not news-lag eligibility rules. Candidate membership is unchanged; all activation flags remain disabled.

The [official rate-limit documentation](https://docs.polymarket.com/api-reference/rate-limits) describes limits by endpoint and IP. The observed responses alone do not identify the binding quota or other traffic. Slower pacing is a mitigation to test.

## Next decision

Review the completed 24-hour rehearsal, integrate the scheduler into a separately frozen collector, and validate its acquisition behavior before activating event-period collection. The present audit is too early even to establish 240 minutes of elapsed prospective capture; elapsed time alone would still not establish complete history.

Forward receipt policy, source-to-feature compatibility and actual release evidence remain pending. The first reserved release is still in the future. No model fitting, forecasting, target labels, holdout consumption or collector changes occurred in this task.

## Evidence

- [Canonical readiness report](data/v7/direct_source_pilot_20261022/readiness/20261022T064259Z_a4dc72/report.json).
- [Per-market readiness](data/v7/direct_source_pilot_20261022/readiness/20261022T064259Z_a4dc72/market_readiness.jsonl).
- [Prepared event windows and scheduler configuration](data/v7/direct_source_pilot_20261022/readiness/20261022T064259Z_a4dc72/event_capture_staging.json).
- [Frozen source audit](data/v7/direct_source_pilot_20261022/audits/20261022T063715Z_e25bc9/report.json).
- [Staged scheduler component](eventx/v7/source_request_scheduler_v02.py).

The first readiness renderer used snapshot-specific prose. Its report remains accurate for its recorded cutoff and is preserved. V02 generates counts and elapsed-time statements from the supplied audit; its numerical findings for this snapshot are identical.
