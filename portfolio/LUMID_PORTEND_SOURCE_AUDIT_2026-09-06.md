# Lumid source audit for PORTEND

Date: 2026-09-06  
Surface: `https://lum.id/findata`  
Method: authenticated, read-only requests; response contents were not persisted.

## Verdict

Lumid is usable as a primary input for the first PORTEND L2 feasibility study, with
important routing and completeness guardrails. It can currently provide an active
Polymarket roster, instrument IDs, trades, candles and timestamped historical L2
snapshots. It does not yet prove complete historical L2 coverage across the intended
benchmark cohort.

## Observed behavior

| Capability | Result | PORTEND decision |
|---|---|---|
| Live OpenAPI | Passed; 57,970-byte specification retrieved | Pin the specification hash with each collector version |
| `/prediction-markets/events` | Returned 100 open events, but all 100 had `market_ids = null` | Do not use for event-to-market enumeration |
| `/prediction-markets/markets/search` | Returned rows with venue, market ID and basic metadata | Useful for discovery, not a complete roster |
| Documented market detail | `/prediction-markets/markets/polymarket/{condition_id}` returned 404 and is absent from live OpenAPI | Unusable until fixed |
| `/api/v1/lqt/markets?venue=polymarket` | Returned 4,528 markets; every row had a non-empty instrument list | Use as the active-cohort and token-enumeration spine |
| Polymarket trades | Returned price, side, size, taker, token ID, trade ID and timestamp | Usable, subject to bounded pagination/completeness audit |
| Prediction-market candles | Returned timestamped OHLC, trade count and volume | Usable as a price panel, not an L2 substitute |
| Polymarket orderbook | Asset-ID query returned timestamped rows with bids, asks, condition ID, tick size and minimum order size | Usable for historical snapshot feasibility |
| Orderbook time filters | `from`, `to` and `limit` worked | Implement time-window pagination |

## L2 sample evidence

One active-flagged Polymarket sample produced:

- 500 order-book rows and 500 distinct snapshot timestamps;
- one asset and one condition ID;
- a default returned span from 2026-06-28 to 2026-07-01;
- a bounded 2026-06-01 to 2026-06-15 query returning 500 rows from June 10–14;
- a bounded 2026-05-17 to 2026-06-01 query returning 500 rows around May 30;
- zero rows in the tested January 2026 and August 2025 windows;
- 337/500 default rows with empty ask arrays, requiring book-quality analysis.

These are single-market observations, not cohort-wide coverage claims. Returning
exactly 500 rows is treated as possible censoring and requires backward time-window
pagination. Empty sides are not automatically interpreted as missing data; they must
be reconciled against market mechanics, complementary tokens and observed trades.

## Source plan

Use Lumid as follows:

1. Enumerate active conditions and token IDs through `/api/v1/lqt/markets`.
2. Freeze the returned roster, response time and raw hash.
3. Fetch order-book snapshots by asset ID in bounded windows, paging whenever the
   response reaches the observed 500-row cap.
4. Fetch condition-level trades over the identical intervals.
5. Fetch candles only as a price-panel and reconciliation source.
6. Capture the prediction-market SSE/WebSocket prospectively for future deltas.
7. Obtain settlement/oracle and full semantic metadata from an independently verified
   source where the Lumid detail route is insufficient.

## Remaining gate

Before PORTEND can claim historical executable replay, run this process over a
representative frozen market sample and report:

```text
market and token coverage
first/last snapshot time
snapshot interval distribution
one-sided and empty-book rates
time-window censoring
latest valid pre-trade snapshot rate
VWAP and fill reconstruction error
```

Until that gate passes, Lumid is a promising historical snapshot source, not proven
complete executable-benchmark infrastructure.

## 2026-09-07 pre-May coverage follow-up

Authenticated, bounded read-only requests confirmed that Lumid contains some
Polymarket market data before 1 May 2026, but availability is market- and
modality-specific.

- For one currently active long-duration condition, the daily candle route returned
  418 rows spanning `2025-07-12T00:00:00Z` through
  `2026-09-08T00:00:00Z`; 287 rows were dated before 1 May 2026 and 167 before
  1 January 2026. The apparent future 8 September bucket requires timestamp/bucketing
  investigation before use.
- The same condition's first observed bounded L2 snapshot was
  `2026-02-23T00:06:25.785000Z`. February, March and April queries returned data;
  January returned none. Broad windows repeatedly hit exactly 500 rows, so they do
  not establish completeness without narrower-window pagination.
- The tested February L2 rows had non-empty bid and ask arrays, showing that useful
  two-sided historical books exist for at least this asset.
- Three other current long-duration markets returned no L2 rows during the first
  week of March. This can mean later market creation or missing collection and
  demonstrates that one asset's early coverage cannot be generalized to the cohort.
- The condition-level trade endpoint returned zero rows before May for the condition
  that had candles and L2. Cross-modality presence is therefore not guaranteed.
- The live OpenAPI description says candle intervals such as `1d`, but the endpoint
  rejected `interval=1d` and accepted the legacy integer `interval=1440` form.
- A warehouse-wide aggregate was stopped after it remained slow; no global pre-May
  row or market count is claimed.

Decision: pre-May data are available and can extend the feasibility window, but the
PORTEND cohort must be selected from measured intersection coverage across metadata,
L2 and trades. Do not set a universal start date from this sample alone.
