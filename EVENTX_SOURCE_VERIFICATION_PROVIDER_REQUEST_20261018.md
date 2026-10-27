# Lumid source-verification request — evidence draft

**Prepared, not sent.** No credentials included. Bounded comparison18October2026,15:05:28–15:09:16UTC; separate SSE recheck15:12:16–15:15:16UTC.

## Reproduction scope

Control condition: `0x25d707a88c94c8311e131997e2686c6235e70c7758baea69b5613e49f7044c38` — Will Bitcoin reach$84,000 October12–18?

Common first-round trade window: **2026-10-18T09:05:28.726677+00:00 to 2026-10-18T15:05:28+00:00**. Source requests/precise parameters are in `data/v7/source_verification_20261018/runs/7386a2e9c114494281a4040874253dc3/receipts.json`.

Other macro conditions:
- `0x1477a29da5bdf455b9dc9a592462fc50be5d36ea303d8eb68934e54e82866c92` CPI.
- `0x5661913d58d1ab6efcdd8ad3de389ae065328b8e7fa94df300b1b00df8117cf7` unemployment.
- `0xe4f31ce91f6b0d71b926ffdf48068ebb101081d3678354d205483f1bd22ee6b2` GDP.

No V4-protected market data is requested. The full preselected eight-market/16-asset allowlist is in `eventx/release/v7/source_verification_20261018/sample.jsonl`.

## Observations to explain

1. All three macro samples had two-sided venue order books; Lumid orderbook queries returned200/empty in both rounds. Is this endpoint an archive limited to explicitly recorded assets, and which of these assets is subscribed/covered? Please provide coverage intervals, snapshot/ingest clocks, recorder health and gap reasons. An empty archive must be distinguishable from an empty live order book.
2. For the control/window, the venue returned183 records with takerOnly=false,59 with takerOnly=true, while Lumid REST and warehouse each returned six. All six REST fingerprints matched the venue response; additional venue records include later YES prints. Please provide ingestion/source-run provenance, recorder subscriptions and on-demand backfill state. Aggregate warehouse run ID `7d90f4de-09f9-40fb-a7c3-252ee0456dc8` reproduced the six-row count.
3. SSE `/prediction-markets/stream` acknowledged both asset/condition filters and maintained30s heartbeats during a180s recheck, but delivered no market-data events. Initial simultaneous20s observation had35 venue price-change messages; a separate venue180s observation had705. Please confirm expected producer/cadence, whether quote updates are published for the requested assets, and whether condition_ids plus asset_ids use AND/OR semantics. The180s source windows were not synchronized; no message-loss rate is claimed.
4. Venue chart histories are dense while Lumid candles are sparse/empty. Please document candle construction, canonical token handling, quote-midpoint coverage and whether missing windows trigger backfill. Do not infer executed-trade freshness from chart points.
5. Two metadata-ranked control candidates had nonempty active/liquidity metadata but venue books404. Please provide metadata refresh/version guarantees and how stale/resolved/migrated instruments are distinguished without opening unrelated outcomes.

Please provide per-asset source facts and availability provenance. No silent data replacement or broad market rosters with protected prices. Responses can be recorded against this frozen diagnostic; source or collector repairs should use a new version.
