"""Publish source migration, identity and host evidence; no evaluations or messages."""
from pathlib import Path
from collections import Counter
from decimal import Decimal
import json,re,subprocess
from eventx.tasks.discover_v7_direct_pilot_20261022 import REPO_ROOT,now,sha,write,verify_originals
from eventx.tasks.audit_v7_direct_pilot_20261022 import stamp
OUT=REPO_ROOT/'data/v7/autonomous_progress_20261022'
V03=REPO_ROOT/'data/v7/direct_source_pilot_20261022_v03'
AUDIT=V03/'audits/20261022T111727Z_158a60'
RUN=V03/'smoke/7982a689e9014012a3ff8410fd55dad7'
PROBE=REPO_ROOT/'data/v7/execution_identity_20261022/d1ae8e245c3f47b1a7d9160759a52613'

def fp(r,source):
    return (str(r['token_id']),int(stamp(r['timestamp'] if source=='venue' else r['ts'])),str(Decimal(str(r['price'])).normalize()),str(Decimal(str(r['size'])).normalize()),r['side'].upper())

def main():
    OUT.mkdir(exist_ok=False)
    power=subprocess.run(['pmset','-g','log'],capture_output=True,text=True,check=True).stdout
    selected=[l for l in power.splitlines() if re.match(r'^2026-10-22 (16|17):[0-9:]+ \+0800 (Sleep|Wake|DarkWake)\s+\t',l)]
    (OUT/'host_sleep_evidence.txt').write_text('\n'.join(selected)+'\n')
    network={'checked_at':now().isoformat(),'host_preference':'always-on host, user selected',
             'checks':[{'alias':'kv-run','result':'Connection refused at kv.run:10020','authenticated':False},
                       {'alias':'luyao1','result':'Same kv.run:10020 route refused; connection closed','authenticated':False}],
             'deployed':False,'credentials_transferred':False,'cloud_resources_created':False,
             'required_human_action':'Restore existing SSH server/tunnel or provide a reachable existing host/alias. Do not send secrets in chat.'}
    write(OUT/'host_access.json',network)
    records=[json.loads(l) for l in (AUDIT/'journal.jsonl').read_text().splitlines()]
    summaries={(r['market_id'],r['cycle'],r['source']):r for r in records if r['kind']=='window_summary'}
    source={}
    for r in records:
        if r['kind']=='rest' and r.get('endpoint_kind')=='trades' and r['cycle']==1 and r.get('status')=='observed':
            path=RUN/'objects'/r['payload_sha256']
            if sha(path)!=r['payload_sha256']:raise RuntimeError('Raw hash mismatch')
            v=json.loads(path.read_text());rows=v['data'] if isinstance(v,dict) else v
            window=summaries[r['market_id'],1,r['source']]
            source[r['market_id'],r['source']]=[x for x in rows if window['start']<=stamp(x['timestamp'] if r['source']=='venue' else x['ts'])<=window['end']]
    identities=[]
    for (cid,src),provider in source.items():
        if src!='lumid':continue
        venue=source.get((cid,'venue'),[])
        for p in provider:
            matches=[v for v in venue if fp(v,'venue')==fp(p,'lumid')]
            identities.append({'market_id':cid,'provider_id_sha256':__import__('hashlib').sha256(str(p['trade_id']).encode()).hexdigest(),
                'economic_matches':len(matches),'id_equal_to_matched_transaction_hash':any(str(p['trade_id'])==str(v['transaction_hash']) for v in matches),
                'id_starts_matched_transaction_hash':any(str(p['trade_id']).startswith(str(v['transaction_hash'])) for v in matches),
                'execution_identity_certified':False})
    (OUT/'provider_identity_matches.jsonl').write_text(''.join(json.dumps(r,sort_keys=True)+'\n' for r in identities))
    modes=json.loads((PROBE/'report.json').read_text())
    pairs=[json.loads(l) for l in (PROBE/'paired_modes.jsonl').read_text().splitlines()]
    source_report=json.loads((AUDIT/'report.json').read_text())
    comps=[json.loads(l) for l in (AUDIT/'market_comparison.jsonl').read_text().splitlines()]
    macro=[x for x in comps if x['role']=='prospective_macro_candidate']
    result={'at':now().isoformat(),'source_audit':str(AUDIT.relative_to(REPO_ROOT)),'source_report':source_report,
            'candidate_comparable_windows':sum(x['status']=='comparable_single_page_window' for x in macro),
            'candidate_activity_pass_windows':sum(x.get('observed_activity_screen',False) for x in macro),
            'identity_probe':modes,'paired_mode_role_differences':dict(Counter(x['role'] for x in pairs if x['inclusive_rows_in_window']!=x['taker_rows_in_window'])),
            'provider_rows_examined':len(identities),'provider_rows_with_exact_economic_match':sum(x['economic_matches']>0 for x in identities),
            'provider_rows_with_unique_economic_match':sum(x['economic_matches']==1 for x in identities),
            'provider_ids_equal_transaction_hash':sum(x['id_equal_to_matched_transaction_hash'] for x in identities),
            'provider_ids_start_transaction_hash':sum(x['id_starts_matched_transaction_hash'] for x in identities),
            'identity_status':'unresolved; prefix agreement does not establish unique fills or historical accounting',
            'sleep_evidence_lines':len(selected),'host_access':network,'production_locks_verified':verify_originals(),
            'remote_package':json.loads((REPO_ROOT/'data/v7/remote_deployment_20261022/artifact.json').read_text()),
            'local_continuation':'prepared and frozen; not launched after user chose always-on host',
            'predictive_admissions':0,'models_scored':False,'labels_computed':False,'tests_added_or_run':False,
            'next_dependency':'human restore/provide SSH access; then target-host preflight and smoke, original final audit, remote24h source rehearsal'}
    write(OUT/'report.json',result)
    md=f'''# EventX — autonomous research continuation, 22 October 2026

## Current decision

The next source rehearsal is prepared for an **always-on host**, as requested. Both configured SSH routes are unavailable: `kv-run` refuses port10020 and `luyao1` uses that route. No deployment or credential transfer occurred. **Human action is now needed: restore the existing SSH route or provide another reachable existing host.** The original local collectors continue; their reliability is not assumed.

## Research progress completed

### 1. Feature semantics traced to the frozen model

Verified four code hashes along the historical preparation → V3.1 examples → V4 discovery → selected market model chain. The historical fields named notional contain **token size**, not cash value. Historical trailing windows are open on the left. Earlier source diagnostics used cash value and inclusive boundaries. Their artifacts remain preserved; a new audit makes the distinction explicit.

Re-auditing602comparable candidate windows under the quantity convention produced0activity passes and changed0candidate pass decisions. Three model inputs depend on this convention: two log-size columns and the size-rate ratio. The model artifact was not loaded or scored. [Feature report](EVENTX_FEATURE_SEMANTICS_20261022.md).

### 2. Prepared and exercised the replacement market API

The [official migration notice](https://docs.polymarket.com/migrate/data-api-v1-to-v2) states the legacy Data API retires24October, before our first reserved release. The [replacement trade API](https://docs.polymarket.com/api-reference/feeds/list-trades) uses a different filter, envelope and cursor. Its market-scoped time bounds are ignored, so the new version validates descending pages and filters the requested window locally. Resolution-state capture was added. This is a V7 source-interface change, not a new project-v2 research cycle.

The separate five-minute V03 run completed with:

|Measure|Observed result|
|---|---:|
|Markets with successful replacement-API trade responses|22/22|
|HTTP200 responses|454|
|HTTP404 responses|10|
|Queued requests cancelled at deadline|42|
|HTTP429 / stream disconnects|0 / 0|
|Chained journal records / verified payloads|3,271 / 2,840|
|Comparable macro windows / activity passes|23 / 0|
|Predictive admissions|0|

The33-file source implementation freeze and20original production locks matched. All fourteen candidate mappings/rules matched at least once. The short concurrent run is not a reliability comparison or proof of complete exchange data. The sandbox DNS failure was stopped and preserved separately. V03 diagnostic boundaries remain inclusive; the prepared remote version explicitly uses the historical open-left convention.

### 3. Measured maker/taker accounting differences

A separate fixed22-market paired probe returned44successful responses. Maker-inclusive and taker-only counts differed in8markets: one prospective macro candidate, three legacy macro samples and four controls. Both first pages reached the six-hour lower bound in all22pairs. The documented distinction is therefore material to trade counts; these are separately fetched snapshots, not guaranteed exchange-complete histories.

For illustration, the $90,000 BTC control had45maker-inclusive versus9taker-only rows in the probe window; the $80,000 control had219versus60. These controls are not research-cohort observations.

In the earlier V03 matched first-cycle windows, {len(identities)}provider rows were examined: {result['provider_rows_with_exact_economic_match']}had at least one exact token/time/price/size/side match, {result['provider_ids_equal_transaction_hash']}provider IDs equalled a matching transaction hash, and {result['provider_ids_start_transaction_hash']}started with one. Prefix matches do not establish fill identity. Keep the execution mapping gate open; do not sum maker rows as independently verified executions.

### 4. Identified a host contribution to the receipt gap

A targeted macOS power-log extract records clamshell sleep at17:06:24Singapore, intermittent dark wakes, then maintenance sleep17:09:23–17:46:09(2,206seconds). This overlaps the earlier maximum2,482.995746second trade-receipt gap. It supports a host-suspension contribution; it does not explain every HTTP/network failure. Existing caffeinate assertions did not prevent the recorded lid-closed sleep.

### 5. Prepared deployment and continuation artifacts

- Portable, credential-free package: `data/v7/remote_deployment_20261022/eventx-source-remote-v01.tar.gz` ({result['remote_package']['bytes']:,}bytes;21files).
- Separate remote source freeze: `eventx/release/v7/remote_source_pilot_20261022/implementation_manifest.json`.
- Includes fixed22-market metadata, protected-ID exclusion list, collector/audit, dependency pins, runtime/file preflight, systemd unit and setup instructions. Model bytes are included only for hash verification.
- A live remote run requires a verified completed-original-source-audit receipt. No future completion is fabricated. It stops after24hours, with26October12:00UTC outer deadline. A target-host smoke run is still required.
- The original macOS interpreter lock cannot certify a Linux runtime. The remote version records a distinct Python3.12 runtime; original frozen files are unchanged.
- The local automatic continuation is prepared/frozen but **not launched**, following the always-on-host choice. No remote process has started.

## What happens after access is restored

1. Inspect the designated host, provision a new isolated directory and minimal source credentials through the existing secure channel, and verify package hashes/runtime.
2. Run the target-host smoke capture and inspect actual scoped responses and clocks.
3. Review the original24h rehearsal after23October05:58UTC(13:58Singapore), then transfer its verified completion receipt and start the new24h source rehearsal.
4. Resolve execution identity, source coverage and terminal evidence; freeze forward freshness/acquisition latency before event scoring. Original-release capture also needs its own remote deployment before the event study.
5. First reserved episode remains29October12:30UTC; source readiness must precede its06:30UTC warmup. If gates fail, retain the failed episode and do not manufacture an eligible observation.

No new predictive result is claimed. Source collection, input compatibility and future event yield remain the research focus. No protected evaluation, model fitting, metric alteration, test-suite execution, provider message or cloud-resource purchase occurred.

## Canonical evidence

`data/v7/autonomous_progress_20261022/report.json` links the V03 audit, paired probe, identity analysis and deployment artifact. `host_sleep_evidence.txt` contains only the targeted power events; `host_access.json` records the failed routes. Supporting source reports and all failed attempts are preserved.
'''
    public=REPO_ROOT/'EVENTX_AUTONOMOUS_RESEARCH_PROGRESS_20261022.md';public.write_text(md);(OUT/'REPORT.md').write_text(md)
    draft='''# Provider clarification — prepared, not sent

Subject: EventX V7 execution identity and observation semantics

Please clarify the Polymarket trade endpoint/warehouse contract for this separate V7 source feasibility study:

1. Does `trade_id` identify one fill, a transaction, or a participant-side row? Define any suffix, and its mapping to transaction hash plus log/sequence index.
2. Are maker and taker rows both retained? What does the `taker` field mean, and are canonical YES-token maker/taker representations transformed?
3. State minimum size filters, timestamp precision/order for same-second trades, pagination/tied-timestamp guarantees, and late-ingestion behavior.
4. Confirm how upstream Data API v2 migration (legacy retirement notice24Oct) affects this contract and whether `size` remains token quantity.
5. Provide an execution-level reconciliation for the exact scoped receipts in the attached local research package; matching economic fingerprints alone is insufficient.

Evidence package: data/v7/autonomous_progress_20261022/; exact market IDs and hashed provider-ID diagnostics in provider_identity_matches.jsonl; source hashes and request windows in data/v7/direct_source_pilot_20261022_v03/audits/20261022T111727Z_158a60/. Paired maker/taker probe: data/v7/execution_identity_20261022/d1ae8e245c3f47b1a7d9160759a52613/.

No credentials or protected evaluation data should be attached. This draft has not been sent.
'''
    (OUT/'PROVIDER_CLARIFICATION_DRAFT.md').write_text(draft)
    files=[p for p in OUT.iterdir() if p.is_file()]+[public,Path(__file__).resolve(),AUDIT/'manifest.json',PROBE/'manifest.json',REPO_ROOT/'data/v7/remote_deployment_20261022/artifact.json']
    write(OUT/'manifest.json',{'files':{str(p.relative_to(REPO_ROOT)):sha(p) for p in files}})
    print(json.dumps({k:result[k] for k in ['provider_rows_examined','provider_rows_with_exact_economic_match','provider_ids_equal_transaction_hash','provider_ids_start_transaction_hash','sleep_evidence_lines','next_dependency']}))

if __name__=='__main__':main()
