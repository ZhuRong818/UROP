# Draft: Lumid market-source coverage diagnosis

**Prepared only; not sent.** Snapshot 2026-10-18T10:12:47.834706+00:00. No credentials included.

## Scope

37 exact Polymarket condition IDs and canonical YES asset IDs in `eventx/release/v7/market_capture_20261018/cohort.jsonl`. Rules/YES mapping derive from the metadata projection in `data/v7/market_cohort_capture_20261018/discovery/1a872b9ecec242109d9383e5554e5a36/polymarket.jsonl`. Exclude all V4 protected IDs; this request does not seek their prices/outcomes.

## Observations

- Latest sampled trades: CPI15October08:52:56UTC, GDP16October12:25:04UTC, unemployment11October22:55:54UTC. No claim these prove source staleness rather than inactivity.
- Three latest YES-asset quote queries with limit1 returned HTTP200 empty lists. Bounded recent-window capture results are frozen in `data/v7/market_cohort_capture_20261018/health/20261018T101247Z/report.json`.
- Orderbook documentation caps limit at500. Initial limit1000 requests were422; corrected subsequent capture uses1.
- Narrow future-close Kalshi KXCPI/KXUNRATE/KXGDP prefix queries returned zero rows; earlier broad title query failed400. Is this catalogue coverage/freshness or a query/mapping issue?

## Requested clarification / evidence

1. Are all37 contracts covered by the live trade recorder? Please give recorder start/end timestamps, latest ingest/run timestamps, gaps and whether first-read Predexon backfill was invoked for our queries.
2. For an HTTP200 empty trade window, can completeness be established? If not, what fields/receipts distinguish inactivity, unavailable coverage and failed backfill?
3. Are YES-asset orderbook snapshots recorded for these assets? Please provide sampling coverage and snapshot/ingest clocks, including absence/gap reasons. No bid/ask data for unrelated contracts is requested.
4. Confirm inclusive/exclusive time-window semantics, newest-first ordering, pagination and timestamp-tie handling for trade endpoints.
5. Explain future-close macro catalogue coverage for the three Kalshi ticker ranges; if names changed, provide metadata-only mapping without prices/results.

Server request IDs from the frozen snapshot:
- {"at": "2026-10-18T10:11:01.752963+00:00", "kind": "quotes", "market_id": "0x0663378212ab1da5727f4c5eb768f0334e0eb141be456c1dc4816063101645a4", "request_id": "75040e89-bb83-4778-bf55-ea462503b7b0"}

Please return source facts and point-in-time provenance. Do not substitute later-resolved contract data or broad market rosters containing protected prices.
