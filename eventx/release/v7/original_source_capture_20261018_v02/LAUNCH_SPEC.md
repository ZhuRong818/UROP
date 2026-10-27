# Original-release capture: launch specification

User-authorized source feasibility pilot, prepared 18 October 2026. This adds a separate original-source branch; it does not replace Lumid inputs or admit a forecasting confirmation cohort.

## Operation

- Official Federal Reserve monetary-policy and speech/testimony RSS feeds, and official BEA RSS: poll every 60 seconds.
- Fourteen scheduled release targets on eleven dates through December; 15-second polling during the first 15 minutes, then 60 seconds through one hour and hourly through 24 hours. Feed burst starts two minutes before release.
- Preserve full official payloads, first local receipt clocks, changed versions and request failures in an append-only hash chain. Failed requests back off; HTTP401/403 at least six hours, Retry-After honored.
- BLS web access currently HTTP403. Official DOL-hosted original BLS PDFs were successfully downloaded. Future PDF paths are naming hypotheses and must return the expected source document; they are not guaranteed endpoints.
- The initial RSS and PDF contents are historical baseline imports or unverified source candidates, not newly captured information shocks.
- Keep condition_120k model hash d5d5a8c12fd999674f687c712e14f3a4406e7ab5ec34774baf1828f644f73a3c fixed. No model loading for inference, training, calibration, scores, labels, market prices or V4 sealed payload access.
- Local user LaunchAgent restarts after failure and at login; caffeinate inhibits idle sleep while the collector runs. Network and an awake computer are required; lid closure, logout, shutdown or outages can cause gaps.
- Stop: create data/v7/official_source_capture_20261018/live/STOP. Finite collection ends 1 January 2027 00:00 UTC. No further network requests after that end.
- Status: data/v7/official_source_capture_20261018/live/status.json. It reports source receipt health, not information-event independence or forecast performance.

## Schedule

| Event | Announced time UTC | Calendar |
|---|---|---|
| FOMC statement | 2026-10-28T18:00:00+00:00 | https://www.federalreserve.gov/monetarypolicy/fomccalendars.htm |
| GDP advance estimate | 2026-10-29T12:30:00+00:00 | https://www.bea.gov/news/schedule |
| Personal Income and Outlays | 2026-10-29T12:30:00+00:00 | https://www.bea.gov/news/schedule |
| EMPLOYMENT SITUATION | 2026-11-06T13:30:00+00:00 | https://www.bls.gov/schedule/2026/11_sched.htm |
| CONSUMER PRICE INDEX | 2026-11-10T13:30:00+00:00 | https://www.bls.gov/schedule/2026/11_sched.htm |
| PRODUCER PRICE | 2026-11-13T13:30:00+00:00 | https://www.bls.gov/schedule/2026/11_sched.htm |
| GDP second estimate | 2026-11-25T13:30:00+00:00 | https://www.bea.gov/news/schedule |
| Personal Income and Outlays | 2026-11-25T13:30:00+00:00 | https://www.bea.gov/news/schedule |
| EMPLOYMENT SITUATION | 2026-12-04T13:30:00+00:00 | https://www.bls.gov/schedule/2026/12_sched.htm |
| FOMC statement | 2026-12-09T19:00:00+00:00 | https://www.federalreserve.gov/monetarypolicy/fomccalendars.htm |
| CONSUMER PRICE INDEX | 2026-12-10T13:30:00+00:00 | https://www.bls.gov/schedule/2026/12_sched.htm |
| PRODUCER PRICE | 2026-12-15T13:30:00+00:00 | https://www.bls.gov/schedule/2026/12_sched.htm |
| GDP third estimate | 2026-12-23T13:30:00+00:00 | https://www.bea.gov/news/schedule |
| Personal Income and Outlays | 2026-12-23T13:30:00+00:00 | https://www.bea.gov/news/schedule |

Clock conversion uses America/New_York, including November daylight-saving transition. Scheduled dates/times can change; daily BEA schedule snapshots are retained for review. FOMC 14:00 ET is the standard release-time assumption; the calendar establishes meeting dates, not an authenticated actual publication clock.

## Reviewable artifacts

- capture_contract.json: source scope, cadence, availability semantics and frozen market fingerprint.
- schedule.json: dated targets and official calendar references.
- implementation_manifest.json: collector, launcher, interpreter, contract, schedule and market hashes.
- com.eventx.original-releases.20261018.v02.plist: exact local user service to install.
- Version1 was prepared but never launched. Version2 fixes restart restoration of pending feed discoveries and handles bounded official-host redirects/bare bea.gov. Both preserved.
