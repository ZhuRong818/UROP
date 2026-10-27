# EventX original-release capture — started 18 October 2026

**The local background collector is running.** Start: 18 October 2026 11:49:00 Singapore time. Operational PID: 600. User LaunchAgent: `com.eventx.original-releases.20261018.v02`.

The existing **raw condition_120k market model remains fixed**, with SHA-256 `d5d5a8c12fd999674f687c712e14f3a4406e7ab5ec34774baf1828f644f73a3c`. Its file and selection receipt match their canonical manifests. This task changes source capture only.

## What is collecting

| Source | Capture | Health at launch |
|---|---|---|
| Federal Reserve | Complete declared monetary-policy and speech/testimony RSS items, then original linked documents | Both feeds reachable |
| BEA | Complete official RSS items, then original linked documents; daily release-calendar snapshot | Feed and calendar reachable |
| BLS / Department of Labor | Official DOL-hosted original CPI, PPI and employment PDFs; dated future targets | All three recent originals downloaded; future URLs remain naming hypotheses until observed |
| BLS website | Slow health probes of the three standard release pages | HTTP403; preserved as unknown access, never zero news |

This is an explicitly separate original-source feasibility branch authorized by the user. It does not replace Lumid records or enter any frozen study. All three declared feeds are captured without topic filtering; RSS retention/truncation and outages still limit coverage.

## Cadence and receipt method

- Fed/BEA RSS every **60 seconds** when requests succeed normally.
- Scheduled target documents every **15 seconds for the first 15 minutes**, then every minute through one hour and hourly through 24 hours. Feed polling accelerates from two minutes before to 15 minutes after scheduled releases.
- HTTP failures back off;401/403 wait at least six hours. Server Retry-After is respected. These intervals are targets, not latency guarantees.
- Preserve raw HTTP entity payloads after transport decompression, content hashes, separate extracted text, original URL, request/response clocks and version links. Every request and observation enters an append-only SHA-256 chain.
- `available_at` follows durable local payload storage. Publisher feed dates and announced schedule times remain separate claims; neither backdates local availability.
- A changed page is a new observed version, not automatically a new information event. First observed is not necessarily first published.

## Scheduled coverage

**14 scheduled release targets on 11 dates**, plus unscheduled Fed speeches/testimony and other items in the declared feeds. Collection ends **1 January 2027 00:00 UTC**.

| Event | Planned UTC time |
|---|---|
| FOMC statement | 2026-10-28T18:00:00+00:00 |
| GDP advance estimate | 2026-10-29T12:30:00+00:00 |
| Personal Income and Outlays | 2026-10-29T12:30:00+00:00 |
| EMPLOYMENT SITUATION | 2026-11-06T13:30:00+00:00 |
| CONSUMER PRICE INDEX | 2026-11-10T13:30:00+00:00 |
| PRODUCER PRICE | 2026-11-13T13:30:00+00:00 |
| GDP second estimate | 2026-11-25T13:30:00+00:00 |
| Personal Income and Outlays | 2026-11-25T13:30:00+00:00 |
| EMPLOYMENT SITUATION | 2026-12-04T13:30:00+00:00 |
| FOMC statement | 2026-12-09T19:00:00+00:00 |
| CONSUMER PRICE INDEX | 2026-12-10T13:30:00+00:00 |
| PRODUCER PRICE | 2026-12-15T13:30:00+00:00 |
| GDP third estimate | 2026-12-23T13:30:00+00:00 |
| Personal Income and Outlays | 2026-12-23T13:30:00+00:00 |

Calendar references: [BLS November](https://www.bls.gov/schedule/2026/11_sched.htm), [BLS December](https://www.bls.gov/schedule/2026/12_sched.htm), [BEA](https://www.bea.gov/news/schedule), [FOMC](https://www.federalreserve.gov/monetarypolicy/fomccalendars.htm). New York timezone conversion accounts for November’s daylight-saving change. FOMC14:00ET is the standard-time assumption; actual publication times must be observed. Dates can change. Retained BEA calendar changes need review; BLS direct calendar access is restricted from this machine.

Simultaneous GDP and PCE releases are separate documents but share a timestamp and shock environment. Fourteen targets must not be described as fourteen independent events or a powered sample.

## First operational snapshot

Snapshot: **2026-10-18T03:50:26.690982+00:00**. [Machine-readable health report](data/v7/official_source_capture_20261018/health/20261018T035026Z/report.json).

- 338 journal records and 83 distinct stored source payloads verify.
- 79 document versions captured; **79 historical baseline imports**, 0 prospective source-candidate versions.
- Repeated polling of all three primary feeds observed: **true**.
- Collector implementation and selected-model hashes match. Process presence was separately checked using ps.
- Three BLS pages return403. One older2021 BEA item redirects outside the official-host allowlist and is refused; its missing capture is logged. These failures do not become empty-news observations.

The old releases and feed items were fetched now as baseline imports. They are **not timely captures of past events**. New-release latency, event diversity and missed first versions can only be assessed after future observations. No predictive improvement has been measured.

## Research separation and next step

No prediction-market endpoint or V4 sealed payload is read; no model is trained, calibrated or scored, and no outcome labels or forecast metrics are produced. This pilot is not an untouched forecasting evaluation. Any source observations overlapping V4 remain pilot-only; no new confirmation cohort is admitted.

After the first new releases, audit actual receipt delays, exact source versions, failed requests and distinct event dates. Then choose a market cohort and family/time separation explicitly, collect its price/trade freshness and freeze the later M → exposure/timing → reviewed-evidence comparison. Current source capture alone does not supply those market observations or certify power.

## Operation and files

- [Launch specification](eventx/release/v7/original_source_capture_20261018_v02/LAUNCH_SPEC.md)
- [Capture contract](eventx/release/v7/original_source_capture_20261018_v02/capture_contract.json)
- [Schedule](eventx/release/v7/original_source_capture_20261018_v02/schedule.json)
- [Implementation lock](eventx/release/v7/original_source_capture_20261018_v02/implementation_manifest.json)
- [Live status](data/v7/official_source_capture_20261018/live/status.json)
- [Service installation receipt](data/v7/official_source_capture_20261018/service_install_receipt.json)
- Raw objects and text: `data/v7/official_source_capture_20261018/live/objects/` and `texts/`.
- Journal: `data/v7/official_source_capture_20261018/live/journal.jsonl`.

The user LaunchAgent restarts after failures and at login. Caffeinate inhibits idle sleep while running. The computer must remain powered, awake and connected; shutdown, logout, lid closure and network outages can create irrecoverable gaps. To stop cleanly, create `data/v7/official_source_capture_20261018/live/STOP`.

Endpoint probes retained: sandbox DNS failures; approved network BLS403; initial guessed BEA feed404; corrected official BEA RSS200; all three official DOL copies200. V1 implementation was prepared but never launched. V2 restores pending discoveries on restart and follows only bounded official-host redirects. Both versions are preserved. No software tests were added/run; the evidence above comes from actual source requests and artifact integrity checks.
