"""Publish collector operation and precise source/confirmation limitations."""
from datetime import datetime, timezone
from pathlib import Path
from zoneinfo import ZoneInfo
import hashlib
import json

ROOT=Path(__file__).resolve().parents[2]
BASE=ROOT/'data/v7/official_source_capture_20261018'
RELEASE=ROOT/'eventx/release/v7/original_source_capture_20261018_v02'
def sha(p):
 with p.open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()
def main():
 health=sorted((BASE/'health').iterdir())[-1]
 h=json.loads((health/'report.json').read_text())
 contract=json.loads((RELEASE/'capture_contract.json').read_text())
 schedule=json.loads((RELEASE/'schedule.json').read_text())['events']
 out=ROOT/'EVENTX_ORIGINAL_RELEASE_CAPTURE_20261018.md'
 if out.exists():raise RuntimeError('Preserve completed report; publish new version')
 started=datetime.fromisoformat(h['started_at']).astimezone(ZoneInfo('Asia/Singapore'))
 text=['# EventX original-release capture — started 18 October 2026','',
  f'**The local background collector is running.** Start: {started:%d %B %Y %H:%M:%S} Singapore time. Operational PID: {h["collector_pid"]}. User LaunchAgent: `com.eventx.original-releases.20261018.v02`.', '',
  'The existing **raw condition_120k market model remains fixed**, with SHA-256 `d5d5a8c12fd999674f687c712e14f3a4406e7ab5ec34774baf1828f644f73a3c`. Its file and selection receipt match their canonical manifests. This task changes source capture only.', '',
  '## What is collecting','',
  '| Source | Capture | Health at launch |','|---|---|---|',
  '| Federal Reserve | Complete declared monetary-policy and speech/testimony RSS items, then original linked documents | Both feeds reachable |',
  '| BEA | Complete official RSS items, then original linked documents; daily release-calendar snapshot | Feed and calendar reachable |',
  '| BLS / Department of Labor | Official DOL-hosted original CPI, PPI and employment PDFs; dated future targets | All three recent originals downloaded; future URLs remain naming hypotheses until observed |',
  '| BLS website | Slow health probes of the three standard release pages | HTTP403; preserved as unknown access, never zero news |','',
  'This is an explicitly separate original-source feasibility branch authorized by the user. It does not replace Lumid records or enter any frozen study. All three declared feeds are captured without topic filtering; RSS retention/truncation and outages still limit coverage.', '',
  '## Cadence and receipt method','',
  '- Fed/BEA RSS every **60 seconds** when requests succeed normally.',
  '- Scheduled target documents every **15 seconds for the first 15 minutes**, then every minute through one hour and hourly through 24 hours. Feed polling accelerates from two minutes before to 15 minutes after scheduled releases.',
  '- HTTP failures back off;401/403 wait at least six hours. Server Retry-After is respected. These intervals are targets, not latency guarantees.',
  '- Preserve raw HTTP entity payloads after transport decompression, content hashes, separate extracted text, original URL, request/response clocks and version links. Every request and observation enters an append-only SHA-256 chain.',
  '- `available_at` follows durable local payload storage. Publisher feed dates and announced schedule times remain separate claims; neither backdates local availability.',
  '- A changed page is a new observed version, not automatically a new information event. First observed is not necessarily first published.', '',
  '## Scheduled coverage','',
  f'**{len(schedule)} scheduled release targets on {len({e["scheduled_at"][:10] for e in schedule})} dates**, plus unscheduled Fed speeches/testimony and other items in the declared feeds. Collection ends **1 January 2027 00:00 UTC**.', '',
  '| Event | Planned UTC time |','|---|---|']
 for e in schedule:text.append(f'| {e["name"]} | {e["scheduled_at"]} |')
 text+=['',
  'Calendar references: [BLS November](https://www.bls.gov/schedule/2026/11_sched.htm), [BLS December](https://www.bls.gov/schedule/2026/12_sched.htm), [BEA](https://www.bea.gov/news/schedule), [FOMC](https://www.federalreserve.gov/monetarypolicy/fomccalendars.htm). New York timezone conversion accounts for November’s daylight-saving change. FOMC14:00ET is the standard-time assumption; actual publication times must be observed. Dates can change. Retained BEA calendar changes need review; BLS direct calendar access is restricted from this machine.', '',
  'Simultaneous GDP and PCE releases are separate documents but share a timestamp and shock environment. Fourteen targets must not be described as fourteen independent events or a powered sample.', '',
  '## First operational snapshot','',
  f'Snapshot: **{h["checked_at"]}**. [Machine-readable health report]({(health/"report.json").relative_to(ROOT)}).','',
  f'- {h["journal_records_verified"]} journal records and {h["unique_source_payloads_verified"]} distinct stored source payloads verify.',
  f'- {h["document_versions"]} document versions captured; **{h["historical_baseline_versions"]} historical baseline imports**, {h["prospective_source_candidate_versions"]} prospective source-candidate versions.',
  f'- Repeated polling of all three primary feeds observed: **{str(h["feed_poll_repeats_observed"]).lower()}**.',
  '- Collector implementation and selected-model hashes match. Process presence was separately checked using ps.',
  '- Three BLS pages return403. One older2021 BEA item redirects outside the official-host allowlist and is refused; its missing capture is logged. These failures do not become empty-news observations.', '',
  'The old releases and feed items were fetched now as baseline imports. They are **not timely captures of past events**. New-release latency, event diversity and missed first versions can only be assessed after future observations. No predictive improvement has been measured.', '',
  '## Research separation and next step','',
  'No prediction-market endpoint or V4 sealed payload is read; no model is trained, calibrated or scored, and no outcome labels or forecast metrics are produced. This pilot is not an untouched forecasting evaluation. Any source observations overlapping V4 remain pilot-only; no new confirmation cohort is admitted.', '',
  'After the first new releases, audit actual receipt delays, exact source versions, failed requests and distinct event dates. Then choose a market cohort and family/time separation explicitly, collect its price/trade freshness and freeze the later M → exposure/timing → reviewed-evidence comparison. Current source capture alone does not supply those market observations or certify power.', '',
  '## Operation and files','',
  '- [Launch specification](eventx/release/v7/original_source_capture_20261018_v02/LAUNCH_SPEC.md)',
  '- [Capture contract](eventx/release/v7/original_source_capture_20261018_v02/capture_contract.json)',
  '- [Schedule](eventx/release/v7/original_source_capture_20261018_v02/schedule.json)',
  '- [Implementation lock](eventx/release/v7/original_source_capture_20261018_v02/implementation_manifest.json)',
  '- [Live status](data/v7/official_source_capture_20261018/live/status.json)',
  '- [Service installation receipt](data/v7/official_source_capture_20261018/service_install_receipt.json)',
  '- Raw objects and text: `data/v7/official_source_capture_20261018/live/objects/` and `texts/`.',
  '- Journal: `data/v7/official_source_capture_20261018/live/journal.jsonl`.', '',
  'The user LaunchAgent restarts after failures and at login. Caffeinate inhibits idle sleep while running. The computer must remain powered, awake and connected; shutdown, logout, lid closure and network outages can create irrecoverable gaps. To stop cleanly, create `data/v7/official_source_capture_20261018/live/STOP`.', '',
  'Endpoint probes retained: sandbox DNS failures; approved network BLS403; initial guessed BEA feed404; corrected official BEA RSS200; all three official DOL copies200. V1 implementation was prepared but never launched. V2 restores pending discoveries on restart and follows only bounded official-host redirects. Both versions are preserved. No software tests were added/run; the evidence above comes from actual source requests and artifact integrity checks.', '']
 out.write_text('\n'.join(text))
 files=[out,RELEASE/'LAUNCH_SPEC.md',RELEASE/'implementation_manifest.json',health/'report.json',health/'manifest.json',BASE/'service_install_receipt.json',Path(__file__),ROOT/'eventx/tasks/snapshot_v7_original_capture_20261018.py']
 (BASE/'launch_delivery_manifest.json').write_text(json.dumps({'created_at':datetime.now(timezone.utc).isoformat(),'artifacts':{str(p.relative_to(ROOT)):sha(p) for p in files}},indent=2)+'\n')
 print(json.dumps({'report':str(out),'health':str(health),'document_versions':h['document_versions'],'repeat_polls':h['feed_poll_repeats_observed']},indent=2))
if __name__=='__main__':main()
