"""Deliver the source diagnosis and a concrete unsent provider evidence request."""
import json
from eventx.settings import REPO_ROOT
from eventx.tasks.discover_v7_source_control_20261018 import BASE,sha,write

OUT=BASE/'analysis_v01'
def main():
 s=json.loads((OUT/'report.json').read_text());rs=[json.loads(l) for l in (OUT/'market_comparison.jsonl').read_text().splitlines()]
 table=[]
 names={'0x1477a29da5':'October CPI +0.3%','0x5661913d58':'October unemployment4.2%',
  '0xe4f31ce91f':'Q3 GDP2.0–2.5%','0x25d707a88c':'Bitcoin84k activity control'}
 for r in rs:
  if r['round']!=1 or r['market_id'][:12] not in names:continue
  table.append(f"|{names[r['market_id'][:12]]}|{r['venue_trade_rows']}|{r['lumid_trade_rows']}|{r['venue_bid_levels']} / {r['venue_ask_levels']}|{r['lumid_quote_rows']}|{r['venue_price_history_points']} / {r['lumid_candle_rows']}|")
 report=REPO_ROOT/'EVENTX_SOURCE_VERIFICATION_20261018.md'
 report.write_text(f'''# EventX: source verification results

**Step1 completed as a bounded diagnostic; predictive evaluation remains gated.** Analysis frozen{s['created_at']}. Market model and both running collectors unchanged.

## Main conclusion

**Both sampled market sparsity and source-coverage gaps are present.** Empty Lumid quote responses do not establish that a market has no live order book. A higher-volume activity control also exposes missing reference-visible trade records in Lumid's REST response and warehouse. More model tuning cannot resolve these input problems.

## What was compared

Before fetching diagnostic prices, froze three macro contracts by question text and five Bitcoin control candidates ranked using metadata liquidity. All470 protected V4 market IDs were excluded before source requests. This diagnostic sample is not a new prediction cohort and establishes no independent research-event count.

Two REST rounds ran from15:05:28 to15:09:16UTC on18October,112 requests total:104 HTTP200/eight404. Each round requested a common six-hour trade window from Lumid and Polymarket. Analysis intersects exact timestamp boundaries and compares print fingerprints. Both YES and NO books were queried. Each source's raw payloads, request/receipt clocks and hashes are retained.

### First round: comparable source observations

|Market|Venue trade rows|Lumid trade rows|Venue YES bid/ask levels|Lumid quote snapshots|Venue chart points / Lumid candles|
|---|---:|---:|---:|---:|---:|
{chr(10).join(table)}

Trade rows include both outcome tokens and can reflect the endpoint's print/accounting conventions; they are not necessarily distinct economic transactions. The chart/candle columns describe different data products and are not treated as equivalent observations.

## Findings

### 1. Quote coverage is missing from the queried Lumid archive

All three macro samples returned two-sided venue books in both rounds. Their Lumid quote responses were empty in both rounds. Fresh venue quote timestamps and direct WebSocket book/level updates confirm that live quotations existed during this diagnostic. The raw Lumid response was `[]`, so this discrepancy is not explained by the existing collector discarding a nonempty quote payload.

Across all eight samples, six had a venue YES book and five had two-sided YES books. Two metadata-ranked controls returned venue book404 despite warehouse active/liquidity metadata. Stale metadata, mapping and current book availability require separate checks;404 alone does not identify the cause.

This finding applies to the sampled assets and times. It does not authenticate missing historical quote snapshots or prove a platform-wide outage.

### 2. Sparse macro trades are supported by both sources

The CPI and GDP samples returned zero trades in the common six-hour windows from both endpoints. Unemployment returned five print rows from each, including three canonical YES rows. All five source fingerprints matched. Its latest YES print was14:13:53UTC, approximately52minutes before round1; only two YES rows lay in the preceding hour.

Thus the selected macro markets had active books but insufficient observed trading activity for the inherited freshness screen. Quote changes cannot be counted as executed trades or used to make the frozen trade-based model appear eligible. This diagnostic does not prove complete trading coverage for every cohort market.

### 3. The activity control reveals a separate trade-coverage problem

For **“Will Bitcoin reach $84,000 October12–18?”**, the venue returned183 print rows versus six from Lumid for round1. All six Lumid fingerprints appeared in the venue response;177 additional venue fingerprints were absent from that response. Neither request reached its1000-row limit.

Round2 returned179 versus six over its slightly later rolling window;173 venue-only fingerprints remained. Do not sum these overlapping comparisons as new events.

An exact-window warehouse query also returned six rows, including four YES prints whose latest timestamp was10:25:21UTC. The venue returned88 YES rows in round1, latest14:58:35UTC. This places the discrepancy upstream of the local file writer: changing its parser alone would not recover records absent from both the REST response and warehouse.

Follow-up queries with the venue's taker-only filter returned59 rows for the same control/window, versus183 with that filter disabled. Both exceed six. Filter semantics therefore matter but do not fully explain the discrepancy. Fingerprints compare asset/time/price/size/side; they are not a globally unique fill identity or a certified completeness estimate.

The control passed the predeclared first-round activity screen: fresh two-sided book plus three YES prints in the preceding hour. That count fell to two in round2 as the window rolled. It is an independently checked activity control, **not a stable high-frequency liquidity benchmark**. Two more highly ranked metadata candidates lacked a current venue book, illustrating why metadata liquidity alone is insufficient.

### 4. Streaming transport and market-data coverage differ

The venue WebSocket observation completed its bounded three-minute window and delivered **717 market messages:12 book snapshots and705 price-change messages** across six markets. No last-trade-price messages occurred. These are book updates, not717 trades or independent events.

The initial concurrent Lumid SSE attempt hit the diagnostic client's20-second idle-read timeout. During that common interval, the venue WS delivered12 book and35 price-change messages. We preserved the failed attempt and ran a separate version with a full180-second total deadline and no short idle timeout.

That recheck stayed connected and returned one open acknowledgement plus five heartbeats, **zero market-data events**. Its180-second window was later than the venue WS window; do not present them as a synchronized three-minute loss estimate. A working heartbeat establishes transport liveness, not coverage of these markets. Provider producer/filter/cadence facts remain needed.

### 5. Dense chart history does not validate the target

The three macro venue histories each returned358 chart points for six hours, while the Lumid candle endpoint returned0/2/0. The CPI and GDP samples nevertheless had no executed trades in the same interval. Chart sampling, live books, execution prints and archival candles have different meanings.

Dense sampled price timestamps do not establish fresh executed prices, a valid240-minute trade-derived volatility history, historical system availability, or a valid30-minute forward price. They are not silently substituted into the existing model.

## Research decision and next steps

1. **Keep the model frozen.** No fitting, calibration, forecast scoring or target-label construction occurred. No predictive observations were admitted.
2. Resolve exact-asset quote recorder and trade ingestion/backfill coverage. A concrete provider request is prepared below; it has not been sent. Direct public observations remain a separately recorded diagnostic source.
3. Then create a separately versioned, metadata-defined cohort across more release dates, with verified tradability beyond each information release. Preserve the initial37-contract pilot and quarantine protected overlaps.
4. Require every prospective observation to pass source availability, fresh canonical prices, valid240-minute history, a prespecified valid30-minute forward observation, actual terminal status and defensible event relevance. Count release episodes and group simultaneous/shared shocks.
5. **No further model development before at least one complete prospectively captured observation passes all gates.** Afterward assess episode yield/power before comparing market-only with news-enhanced forecasts.

The gate contract is recorded in [observation_gate_contract.json](data/v7/source_verification_20261018/analysis_v01/observation_gate_contract.json). It is a readiness specification, not completed eligibility validation or a replacement confirmatory protocol.

## Evidence package

- [Canonical analysis](data/v7/source_verification_20261018/analysis_v01/report.json) and [per-market comparisons](data/v7/source_verification_20261018/analysis_v01/market_comparison.jsonl).
- [Frozen plan/sample](eventx/release/v7/source_verification_20261018/plan.json).
- [REST/WS run](data/v7/source_verification_20261018/runs/7386a2e9c114494281a4040874253dc3/report.json), [SSE recheck](data/v7/source_verification_20261018/runs/39bf148e147b4a4da51fd91ed3edb9f4/report.json), [filter/warehouse follow-up](data/v7/source_verification_20261018/followup/da4cfefa28c5464c9131393899afc77a/report.json).
- [Unsent provider evidence request](EVENTX_SOURCE_VERIFICATION_PROVIDER_REQUEST_20261018.md).
- {s['verified_artifact_hashes']} diagnostic artifact/payload hashes and20 existing production-file locks verified; model SHA256 remains `{s['model_sha256']}`. V4 payloads/outcomes were not opened. No software tests were added/run.

## Official interface references

The direct book endpoint uses outcome-token identifiers. [Polymarket order-book documentation](https://docs.polymarket.com/market-data/prices-order-books).

Trade queries support market/time filters and taker-only selection. [Polymarket trade documentation](https://docs.polymarket.com/api-reference/core/get-trades-for-a-user-or-markets).

Chart history is a separate endpoint queried by asset. [Price-history documentation](https://docs.polymarket.com/api-reference/markets/get-prices-history).

Market WebSocket subscriptions and application heartbeats follow the public interface. [Real-time documentation](https://docs.polymarket.com/market-data/realtime-data).
''')
 request=REPO_ROOT/'EVENTX_SOURCE_VERIFICATION_PROVIDER_REQUEST_20261018.md'
 control=next(r for r in rs if r['market_id']==s['selected_activity_control']['market_id'] and r['round']==1)
 request.write_text(f'''# Lumid source-verification request — evidence draft

**Prepared, not sent.** No credentials included. Bounded comparison18October2026,15:05:28–15:09:16UTC; separate SSE recheck15:12:16–15:15:16UTC.

## Reproduction scope

Control condition: `{control['market_id']}` — Will Bitcoin reach$84,000 October12–18?

Common first-round trade window: **{control['common_window_from']} to {control['common_window_to']}**. Source requests/precise parameters are in `data/v7/source_verification_20261018/runs/7386a2e9c114494281a4040874253dc3/receipts.json`.

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
''')
 delivery=BASE/'delivery_v01';delivery.mkdir()
 write(delivery/'manifest.json',{'files':{str(p.relative_to(REPO_ROOT)):sha(p) for p in [report,request,OUT/'manifest.json']}})
 print(json.dumps({'report':str(report.relative_to(REPO_ROOT)),'provider_draft':str(request.relative_to(REPO_ROOT))}))
if __name__=='__main__':main()
