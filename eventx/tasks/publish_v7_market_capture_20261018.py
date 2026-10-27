"""Publish operational findings, with no invented predictive metrics."""
import json
from pathlib import Path
from eventx.settings import REPO_ROOT
from eventx.tasks.prepare_v7_market_capture_20261018 import BASE,RELEASE,sha,write

def main():
 health=max((BASE/'health').glob('*'),key=lambda p:p.name);s=json.loads((health/'report.json').read_text())
 scope=BASE/'target_scope/report.json';cfg=json.loads((RELEASE/'capture_spec.json').read_text())
 latest=BASE/'latest_probes/7c883cc8e64f44bb82237274108c0a71/report.json'
 rs=json.loads(latest.read_text());sample='\n'.join('| '+r['episode_id']+' | '+str(r.get('latest_source_ts'))+' |' for r in rs if r['kind']=='trades')
 relative=lambda p:str(p.relative_to(REPO_ROOT))
 report=REPO_ROOT/'EVENTX_MARKET_CAPTURE_AND_COHORT_20261018.md'
 report.write_text(f'''# EventX: market cohort and capture progress

Operational snapshot: **{s['at']}**. This continues the original-release feasibility pilot with the existing market model fixed.

## Completed

- Retrieved178 Polymarket metadata records without prices/results. Selected37 contracts from explicit US measurement rules;141 outside scope excluded. Full rules, canonical YES asset IDs and metadata timestamps retained.
- Locked the cohort/specification/implementation before service launch. All470 V4 market IDs are excluded; Fed decision contracts quarantined. Metadata comparison found no shared resolution predicate in the three admitted US measurement families. Shared economic shocks remain possible; statistical independence is not established.
- Started local service `com.eventx.market-capture.20261018`, registered18October10:10:17UTC. It polls exact-cohort trades and YES-asset quote observations, with a120s requested cycle, six-hour initial warmup and30-minute overlapping retrieval windows. Slow endpoints may extend cycles.
- Saved raw response hashes, request/receipt clocks, execution/source clocks and append-only journal. First local durable receipt is the availability clock. Historical timestamps do not establish historical availability.
- Preserved raw `condition_120k`; SHA256 `{cfg['model_sha256']}`. No model load, training, calibration, scoring or target labels.

| Contract family | Contracts | Scheduled resolving release (UTC) |
|---|---:|---|
| US Q3 GDP advance estimate |7|29October12:30|
| US October unemployment (U-3) |9|6November13:30|
| US October CPI, annual/monthly |21|10November13:30|

These are **three resolving release dates**, not37 independent information events. Warehouse active-state snapshots are not proof of current venue tradability. Schedules can change.

## What the actual collection shows

At this snapshot: **{s['completed_network_window_summaries']} completed network window summaries**; latest per-market trade HTTP statuses `{s['latest_market_trades_http_status']}`; quote statuses `{s['latest_market_quotes_http_status']}`.

Latest observed windows contain **{s['latest_windows_returned_trade_rows']} returned trades / {s['latest_windows_returned_yes_rows']} canonical-YES trades**; **{s['markets_with_nonempty_quote']} markets** have a nonempty quote response. **{s['markets_with_unknown_window']} windows** are currently incomplete/unknown. Overlapping windows must not be added together as independent observations.

Separate latest-observation probes, with no lower timestamp bound, found:

| Sampled contract family | Latest trade returned by source (UTC) |
|---|---|
{sample}

All three sampled YES-quote probes returned empty lists. These are observations about the queried endpoints, not proof of inactivity or a complete source. Thin trading and source recording delays remain unresolved alternatives. Initial quote requests using limit1000 failed422; corrected to the documented limit1 for latest-snapshot capture. Any500 response remains recorded, including its request ID.

The initial sandbox-only collector cycle failed74 requests with DNS ConnectError and ended08:44:06UTC. It is preserved in the journal. The checkpoint's initial started_at08:42:53 describes that attempt; the first real service request is **{s['first_network_request_at']}**. Do not count the failed cycle as source coverage.

Narrow Kalshi CPI/unemployment/GDP ticker queries succeeded but returned zero metadata records; the earlier broad query failed400. This does not establish that Kalshi has no relevant contracts. No Kalshi market capture is claimed.

## Target compatibility: the main scientific constraint

The unchanged target predicts a large absolute YES log-odds movement over30minutes, with a threshold based on trailing240-minute volatility. Each selected contract resolves on its own data release; a later metadata end_date is not evidence of a usable post-release30-minute target.

- At29October GDP/PCE:30 later-resolving contracts pass the calendar-only screen; seven GDP contracts excluded. GDP and PCE are simultaneous, not two independent shocks.
- At6November employment:21 CPI contracts pass that screen;16 already/then resolving contracts excluded.
- At10November CPI:none of this initial cohort remains available under the expected-terminal screen.

These are **calendar possibilities, not eligible forecast observations**. Cross-release material relevance, novelty, actual terminal clocks, freshness and sufficient activity still require verification. No predictive rows are admitted. Original-release collection continues beyond these dates, but this first market cohort does not cover every original-source target.

## Next work

1. Establish whether empty trade/quote responses reflect genuine sparse activity or feed gaps. An unsent provider diagnostic is linked below; it requests coverage/latency facts rather than assuming completeness.
2. Build a separately versioned metadata-defined cohort with contracts remaining open after future releases, across more dates. Preserve the current37-contract pilot; do not select replacements using forecast outcomes.
3. Verify actual source arrivals, exact evidence/context and trade/quote freshness. Count distinct episode dates; preserve simultaneous-release groups.
4. Before predictive confirmation, freeze the new cohort, source clock, M/E/T/R/S comparisons, terminal exclusions, inference/power and unseen evaluation window. Continue to keep the market model fixed.

## Artifacts and service operation

- Cohort/rules/specification/lock: [{relative(RELEASE)}]({relative(RELEASE)}/).
- Immutable health snapshot: [{relative(health/'report.json')}]({relative(health/'report.json')}). {s['journal_records']} journal records, {s['unique_payloads_verified']} unique payload hashes and{s['implementation_files_verified']} locked implementation files verified. V4 exact-ID intersection0; model hash matches.
- Event/market terminal diagnosis: [{relative(scope)}]({relative(scope)}).
- Provider request draft: [EVENTX_MARKET_SOURCE_DIAGNOSTIC_REQUEST_20261018.md](EVENTX_MARKET_SOURCE_DIAGNOSTIC_REQUEST_20261018.md).
- Live observations: `{relative(BASE/'live')}`. Runs through12November00:00UTC; local awake power/network required. Create `live/STOP` to stop cleanly. LaunchAgent restarts after failures/at login; registration does not guarantee feed coverage.
- Original-release collector remains separate and active: snapshot heartbeat `{s['process_status_snapshots']['original_source']['at']}`, PID{s['process_status_snapshots']['original_source']['pid']}, {s['process_status_snapshots']['original_source']['document_versions']} document versions; its source-only status still reports no market reads.

No protected V4 prices/outcomes were opened; no holdout consumed; no model performance improvement or incremental news gain is claimed. Artifact checks and actual capture operations were performed; no software tests were added/run.
''')
 request=REPO_ROOT/'EVENTX_MARKET_SOURCE_DIAGNOSTIC_REQUEST_20261018.md'
 errors='\n'.join('- '+json.dumps(r) for r in s['server_error_request_ids']) or '- None in this snapshot.'
 request.write_text(f'''# Draft: Lumid market-source coverage diagnosis

**Prepared only; not sent.** Snapshot {s['at']}. No credentials included.

## Scope

37 exact Polymarket condition IDs and canonical YES asset IDs in `{relative(RELEASE/'cohort.jsonl')}`. Rules/YES mapping derive from the metadata projection in `data/v7/market_cohort_capture_20261018/discovery/1a872b9ecec242109d9383e5554e5a36/polymarket.jsonl`. Exclude all V4 protected IDs; this request does not seek their prices/outcomes.

## Observations

- Latest sampled trades: CPI15October08:52:56UTC, GDP16October12:25:04UTC, unemployment11October22:55:54UTC. No claim these prove source staleness rather than inactivity.
- Three latest YES-asset quote queries with limit1 returned HTTP200 empty lists. Bounded recent-window capture results are frozen in `{relative(health/'report.json')}`.
- Orderbook documentation caps limit at500. Initial limit1000 requests were422; corrected subsequent capture uses1.
- Narrow future-close Kalshi KXCPI/KXUNRATE/KXGDP prefix queries returned zero rows; earlier broad title query failed400. Is this catalogue coverage/freshness or a query/mapping issue?

## Requested clarification / evidence

1. Are all37 contracts covered by the live trade recorder? Please give recorder start/end timestamps, latest ingest/run timestamps, gaps and whether first-read Predexon backfill was invoked for our queries.
2. For an HTTP200 empty trade window, can completeness be established? If not, what fields/receipts distinguish inactivity, unavailable coverage and failed backfill?
3. Are YES-asset orderbook snapshots recorded for these assets? Please provide sampling coverage and snapshot/ingest clocks, including absence/gap reasons. No bid/ask data for unrelated contracts is requested.
4. Confirm inclusive/exclusive time-window semantics, newest-first ordering, pagination and timestamp-tie handling for trade endpoints.
5. Explain future-close macro catalogue coverage for the three Kalshi ticker ranges; if names changed, provide metadata-only mapping without prices/results.

Server request IDs from the frozen snapshot:
{errors}

Please return source facts and point-in-time provenance. Do not substitute later-resolved contract data or broad market rosters containing protected prices.
''')
 out=BASE/'delivery';out.mkdir(exist_ok=True)
 if (out/'manifest.json').exists():raise RuntimeError('Preserve delivery version')
 write(out/'manifest.json',{'health':relative(health/'report.json'),'files':{relative(p):sha(p) for p in [report,request,health/'manifest.json',scope,RELEASE/'implementation_manifest.json']}})
 print(json.dumps({'report':relative(report),'provider_draft':relative(request),'health':relative(health/'report.json')}))
if __name__=='__main__':main()
