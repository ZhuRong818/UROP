"""Publish exact source-research findings and the active next collection step."""
from datetime import datetime
import json
from pathlib import Path
import subprocess
from eventx.tasks.discover_v7_direct_pilot_20261022 import REPO_ROOT,now,sha,write,verify_originals

OUT=REPO_ROOT/'data/v7/forecast_progress_20261024'

def read(p):return json.loads((REPO_ROOT/p).read_text())

def main():
    if OUT.exists() and any(OUT.iterdir()):raise RuntimeError('Preserve existing publication')
    OUT.mkdir(parents=True,exist_ok=True)
    refs={
        'original':'data/v7/source_workflow_20261022/original_final_review.json',
        'revised':'data/v7/source_workflow_20261022/revised_final_review.json',
        'diagnosis':'data/v7/completed_rehearsal_diagnosis_20261024/report.json',
        'features':'data/v7/full_feature_compatibility_20261024/report.json',
        'enrollment':'eventx/release/v7/expansion_source_pilot_20261024/enrollment_report.json',
        'first_capture':'data/v7/expansion_source_pilot_20261024/audits/20261024T072825Z_89cce9/report.json',
    }
    reports={k:read(v) for k,v in refs.items()}
    verified={}
    manifests=[
        'eventx/release/v7/forecast_path_20261023/manifest.json',
        'eventx/release/v7/expansion_source_pilot_20261024/implementation_manifest.json',
        'eventx/release/v7/source_workflow_20261022/implementation_manifest.json',
        'data/v7/full_feature_compatibility_20261024/manifest.json',
        'data/v7/completed_rehearsal_diagnosis_20261024/manifest.json',
        'data/v7/forecast_expansion_20261024_v02/6054fd69ba8e4d28b53ebbc7c8acef18/manifest.json',
    ]
    for rel in manifests:
        m=read(rel);items=m.get('files',m.get('locked_files',{}))
        if not items:raise RuntimeError('Unknown manifest format')
        for p,h in items.items():
            if sha(REPO_ROOT/p)!=h:raise RuntimeError('Hash mismatch: '+p)
        verified[rel]=len(items)
    status=read('data/v7/expansion_source_pilot_20261024/live/status.json')
    proc=subprocess.run(['ps','-o','pid,etime,command','-p',','.join(map(str,[600,23793,status['pid']]))],capture_output=True,text=True,check=True)
    (OUT/'process_snapshot.txt').write_text(proc.stdout)
    for name,path in [('new_collector','data/v7/expansion_source_pilot_20261024/live/status.json'),
                      ('controller','data/v7/source_workflow_20261022/status.json'),
                      ('official_releases','data/v7/official_source_capture_20261018/live/status.json'),
                      ('original_market_collector','data/v7/market_cohort_capture_20261018/live/status.json')]:
        (OUT/(name+'_status.json')).write_bytes((REPO_ROOT/path).read_bytes())
    report={'at':now().isoformat(),'references':refs,'verified_manifest_file_counts':verified,
        'original_locks_verified':verify_originals(),'original_and_revised_source_runs_complete':True,
        'new_collector_pid':status['pid'],'new_collector_stop_at':status['stop_at'],
        'predictive_admissions':0,'model_loaded_or_scored':False,'tests_added_or_run':False,
        'publisher_prior_attempt':'Sandbox denied ps subprocess; no publication outputs existed. Retried with explicit escalation.',
        'human_operational_dependency':'Keep Mac powered, lid open, awake and networked for continuous capture.',
        'scientific_activation_pending':['documented source/accounting compatibility','exact predicate binding for new contracts',
            'valid240m prospective history and complete decision/endpoint observation','actual release evidence',
            'separate activation receipt before any shadow predictions']}
    write(OUT/'report.json',report)
    doc=REPO_ROOT/'EVENTX_FORECAST_READINESS_PROGRESS_20261024.md'
    text=f'''# EventX: progress toward usable forecasting

Updated {report['at']}. **No usable forecast has been issued yet.** This work advances source feasibility and fixes the prospective timing specification. The selected market model remains frozen.

## Completed work

### 1. Both source rehearsals completed

|Measure|Original24h run|Revised24h run|
|---|---:|---:|
|Journal records|{reports['original']['journal_records']:,}|{reports['revised']['journal_records']:,}|
|Verified payloads|{reports['original']['verified_payloads']:,}|{reports['revised']['verified_payloads']:,}|
|HTTP429 responses|52|0|
|Comparable macro activity windows|3159|2016|
|Activity passes|0|0|
|Maximum market trade-receipt gap|121.13min|443.80min|

The runs cover different periods. These are descriptive source results, not a controlled performance improvement. Original activity diagnostics use cash/inclusive boundaries; revised diagnostics use token quantity/inclusive boundaries. Neither is exact model eligibility.

The revised longest trade-receipt gap runs from23October10:01:38UTC to17:25:26UTC.62host power events occur in the bounded overlap check, including repeated sleep/dark-wake states; a full wake at17:25UTC precedes renewed trade receipts. This supports host sleep as a contributor, without attributing every source omission to sleep. The longest gap across *all* journal events is6895.002863seconds, distinct from the per-market trade gap.

All1441revised HTTP404responses came from venue book requests, not the resolution endpoint. We captured3182successful resolution responses. Repeated API success does not certify continuous trading status.

### 2. Prospective endpoint policy frozen

`eventx/release/v7/forecast_path_20261023/policy.json` was frozen before expansion data were fetched. For this new feasibility branch:

- Inputs must be durably available by the five-minute decision grid; any later shadow forecast must be issued within30seconds, otherwise mark a missed emission.
- Decision and target prices must be no more than5minutes old.
- The target uses the latest unambiguous trade at or before t+30minutes, durably captured by t+32minutes. Never use a post-target nearest trade.
- A receipt/status gap over120seconds blocks affected observations. Backfill cannot repair timely availability. A fresh valid240-minute warmup is required after interruption.
- Missing endpoints remain explicit, and every issued forecast stays in the coverage denominator.
- First establish one complete prospective feasibility observation, then separately activate predictions on later grids. Do not relabel retrospective scores as live forecasts.

The120-second operational limits and30-second issuance budget are prespecified design choices, not validated optimal thresholds. This policy does not modify V4 or earlier studies. The inherited source auditor still prints its generic 'forward policy pending' message; the new branch's policy exists, but source readiness and activation remain pending.

### 3. Metadata expansion completed; two candidates enrolled for source capture

The price-blind search returned204records without hitting its1000-row cap and excluded all470protected V4IDs. The first network attempt failed in the sandbox; the next returned HTTP400. A separately versioned query using `NOT (question ~* ...)` succeeded. The original400body was not retained, so the exact server-side failure cause is unknown.

The ledger retains14existing candidates,89own-release-terminal records,99other excluded records, and two new candidates:

|New contract|Why investigate it|Remaining rule issue|
|---|---|---|
|Negative GDP growth in2026?|A longer-lived US GDP predicate|Full-year/annualized wording requires exact BEA table binding|
|US recession by end of2026?|GDP component evidence and a longer-lived horizon|Either two negative quarters or NBER announcement can terminate it early|

These are source candidates, not predictive admissions. No liquidity ranking or price movements were used. Short-lived contracts were not promoted just because their metadata end date follows a release. Other-release contextual links remain a possible separately specified branch.

### 4. Expanded feature sensitivity to all22columns

From114retained source representations across22markets,11vectors across two markets could be reconstructed. The other histories remain unavailable. Seven paired comparisons were possible; three changed at least one column by more than1e-6. For the BTC74kcontrol, provider versus direct taker-only changed10columns, including volatility, counts, quantities, recency and derived ratios.

This establishes that source substitution can affect much more than counts. It does not establish production feature equivalence, complete source history, or forecasting improvement. No model was loaded or scored; no labels were computed.

## Running now

The separate two-market collector started24October07:27:27UTC (15:27SGT), PID{status['pid']}; scheduled stop **24October13:27:27UTC (21:27SGT)**. It captures metadata/resolution every cycle, records long cycle gaps, and automatically produces a final source audit. It has no scoring or event-activation capability. Original collectors remain unchanged.

The first57.92seconds yielded14HTTP200responses,18verified payloads, and two-sided uncrossed books for both markets. Both mappings/rules matched venue metadata and both accepted orders at the sampled instant. The recession contract had12venue and12provider records in the bounded six-hour window, but0canonical YES records; negative GDP had0trade records. Both fail activity eligibility. Counts do not establish unique executions or source completeness. Initial retained trade windows are retrospective, not prospectively accumulated history.

**Operational requirement:** keep the Mac powered, connected, awake and lid-open through the six-hour capture. The recorded sleep states make this a concrete dependency. No settings override or SSH deployment was performed.

## Next gates

1. Read the new completed source audit after21:27SGT; preserve any failed/zero-yield run.
2. Determine whether enough fresh canonical YES observations exist, whether current metadata/rules remain consistent, and whether provider/venue counting can reproduce all22inputs.
3. Resolve the two explicit predicate/terminal caveats using source evidence; any human adjudication should receive this concrete package.
4. Activate a release-time feasibility window only after source readiness. The first existing reservation is29October12:30UTC, with six-hour warmup planned from06:30UTC. No event service is activated yet.
5. After one complete observation passes, freeze later shadow-forecast activation and comparator artifacts. A prospective baseline comparison remains outstanding.

If the broader sample still cannot support the trade-based target, preserve that result and specify a separate quote-based or alternate-horizon study. Do not silently transform NO trades into YES model inputs or substitute quote midpoints for historical trades.

## Evidence

- Completion reviews: `data/v7/source_workflow_20261022/{{original,revised}}_final_review.json`
- Gap diagnosis: `data/v7/completed_rehearsal_diagnosis_20261024/`
- Feature analysis: `data/v7/full_feature_compatibility_20261024/`
- New source package: `eventx/release/v7/expansion_source_pilot_20261024/`
- Runtime: `data/v7/expansion_source_pilot_20261024/live/`
- This report's manifest and operational snapshots: `data/v7/forecast_progress_20261024/`

Protected holdouts remain untouched. No new performance statistics, tests, model fitting, trading, or provider messages were produced.
'''
    doc.write_text(text)
    state=REPO_ROOT/'CURRENT_STATE.md';old=state.read_text()
    archive=REPO_ROOT/'docs/progress/CURRENT_STATE_ARCHIVE_20261024_FORECAST.md'
    archive.write_text(old)
    start=old.index('## Latest completed research');end=old.index('## Selected market model')
    replacement=f'''## Latest completed research

Canonical report: `EVENTX_FORECAST_READINESS_PROGRESS_20261024.md`.
Evidence: `data/v7/forecast_progress_20261024/`;prior detail archived in
`docs/progress/CURRENT_STATE_ARCHIVE_20261024_FORECAST.md`.

- Original/revised24h source runs completed; controller finished24Oct06:06UTC.
  Original588233records/483894payloads; revised380142/317984. Revised0HTTP429,
  1441book404s;3182resolution200s. Different periods, not controlled improvement.
  Macro activity0/3159original and0/2016revised overlapping diagnostic windows.
- Revised max market trade-receipt gap26627.861848s(443.80min),23Oct10:01:38–17:25:26UTC;
  repeated sleep/dark-wake states overlap; full wake17:25UTC. Host sleep contributes,
  not an explanation for every provider omission. `data/v7/completed_rehearsal_diagnosis_20261024/`.
- New feasibility timing policy frozen23Oct before expansion: inputs available by t,
  emission by t+30s; endpoint trade<=t+30m,age<=5m,receipt<=t+32m;120s operational
  receipt/status gap limit. New design choices,not optimized/validated thresholds.
  `eventx/release/v7/forecast_path_20261023/`;scoring disabled,source convention unresolved.
- Price-blind expansion204metadata records:14existing,89own-release-terminal,99other,
  2new longer-lived US candidates. Sandbox failures and HTTP400 preserved; V02query200.
  470protected IDs excluded;no liquidity ranking. `eventx/release/v7/expansion_source_pilot_20261024/`.
- New negative-annual-GDP candidate needs exact full-year/annualized BEA binding;
  recession candidate has dual GDP/NBER rule and early-terminal risk. Not human gold.
- Full22feature reconstruction:11/114representations across2/22markets;7paired
  comparisons,3withdifferences>1e-6. Source-sensitive,not production parity; no scores.
  `data/v7/full_feature_compatibility_20261024/`.
- Prior exact as-of diagnostic23Oct02:35UTC:0/14freshYES,0/2696activitypasses,
  13unseededpaths,onezero-volatilitypath. `EVENTX_INPUT_COMPATIBILITY_AND_ELIGIBILITY_20261023.md`.
- Provider52records map52orderfills/29transactions,mixedmaker/taker schema;
  16/63omissions recovered late;remaining47chainmatched. No general coverage fix.
  Narrowed provider request remains UNSENT in `data/v7/eligibility_report_20261023/`.

## Local source jobs and next gates

Processes checked24Oct at{report['at']};snapshots in current evidence package.
- Original release collectorPID600 and37-market collectorPID23793 remain running.
  Original-source checkpoint79documentversions;0new release admissions.BLS403 persists.
  Services/data paths retained in archive;original20filelocks verified unchanged.
- Original22-market pilot and revisedV03 pilot completed; workflowPID74338 exited.
  `data/v7/source_workflow_20261022/status.json`:finished_source_review.
<!-- V7_SOURCE_WORKFLOW_STATUS_START -->
- Autonomous source phase: **finished_source_review**, at2026-10-24T06:06:48.061042+00:00.
- Live status/evidence: `data/v7/source_workflow_20261022/status.json`.
- Event activation disabled; model frozen; zero admissions.
<!-- V7_SOURCE_WORKFLOW_STATUS_END -->
- NEW six-hour two-market collectorPID{status['pid']},service`com.eventx.expansion-source-pilot.20261024`.
  `data/v7/expansion_source_pilot_20261024/live/`;stop24Oct13:27:27UTC(21:27SGT).
  Metadata/resolution everycycle;cycle-gaplogging;automatic final source audit.
  First57.92s:14HTTP200/18payloads,both books two-sided/mappingrules match.
  Recession12venue/12provider trade records,zeroYES;negativeGDPzero.0activitypasses.
  Initial histories retrospective;not prospective warmup. No forecast/activation code.
- KeepMacpowered/awake/networked/lid-open;recorded sleep makes this necessary.
  Receipt gaps>120s invalidate affectedwindows;latebackfill never restores availability.
- Six original episodes29Oct–4Dec retained;12new metadata-linkplans are provisional.
  First29Octwarmup06:30UTC remains conditional. No event service activated.
- Remaining:source/accounting compatibility,valid240m history,exactpredicate/terminal
  evidence,timelynewrelease,onecompleteprospectiveobservation;then separate activation
  oflater shadowgrids and baseline artifacts. No statisticalpower or forecastgain claim.

'''
    updated=old[:start]+replacement+old[end:]
    updated=updated.replace('Last updated: **2026-10-23 Asia/Singapore** (compatibility measured; current eligibility zero)',
        'Last updated: **2026-10-24 Asia/Singapore** (source rehearsals complete; new two-market pilot running; zero forecasts)')
    updated=updated.replace('3. Resolve measured source gaps; version a longer-lived cohort across more releases.\n   Model stays frozen until one complete gated observation.\n4. Local source workflow reviews the original final24h audit after23Oct05:58UTC,\n   then runs/audits V03 for24h. Resolve trade identity/feature compatibility using\n   local receipts; six future episodes remain reserved, activation gated.',
        '3. Review the new two-market six-hour capture after24Oct21:27SGT; retain failures.\n   Resolve quantity/counting compatibility and exact predicate/terminal caveats.\n4. Use the separately frozen timing policy for a future feasibility observation;\n   keep model fixed/scoring disabled until all gates pass, then freeze later activation.')
    state.write_text(updated)
    with (REPO_ROOT/'docs/progress/2026-10.md').open('a') as f:
        f.write(f'\n\n## 2026-10-24 — Usable-forecast path: source completion, metadata expansion and new pilot\n\n{text}\n\nCanonical report: `{doc.name}`. Archived previous handoff: `{archive.relative_to(REPO_ROOT)}`.\n')
    files=list(OUT.iterdir())+[doc,Path(__file__).resolve()]+[REPO_ROOT/v for v in refs.values()]+[REPO_ROOT/p for p in manifests]
    write(OUT/'manifest.json',{'files':{str(p.relative_to(REPO_ROOT)):sha(p) for p in files}})
    print(json.dumps({'report':doc.name,'evidence':str(OUT.relative_to(REPO_ROOT)),
        'current_state_lines':len(updated.splitlines()),'new_collector_pid':status['pid'],'predictive_admissions':0},indent=2))

if __name__=='__main__':main()
