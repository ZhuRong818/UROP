"""Publish exact results and a verified checkpoint of the new forecast service."""
from collections import Counter,defaultdict
import hashlib
import json
from pathlib import Path
import subprocess
from eventx.tasks.discover_v7_direct_pilot_20261022 import REPO_ROOT,now,sha,write,verify_originals
from eventx.v7.quote_experiment_20261024 import stamp

OUT=REPO_ROOT/'data/v7/usable_forecast_progress_20261024'
REPORT=REPO_ROOT/'EVENTX_USABLE_FORECAST_PROGRESS_20261024.md'

def copy_chain(source,target):
    body=source.read_bytes();body=body[:body.rfind(b'\n')+1];target.write_bytes(body);rows=[];head=None
    for line in body.splitlines():
        r=json.loads(line);v=dict(r);h=v.pop('record_sha256')
        if v['previous_sha256']!=head or hashlib.sha256(json.dumps(v,sort_keys=True,separators=(',',':')).encode()).hexdigest()!=h:raise RuntimeError('Chain failure')
        head=h;rows.append(r)
    return rows

def main():
    OUT.mkdir(exist_ok=False);locks=verify_originals();at=now().isoformat()
    base=REPO_ROOT/'data/v7/memory_quote_20261024';shadow=base/'shadow';source=REPO_ROOT/'data/v7/quote_source_20261024_v02/live'
    manifests=[base/'development/manifest.json',base/'error_diagnosis/manifest.json',
        REPO_ROOT/'eventx/release/v7/memory_quote_20261024/implementation_manifest.json',
        REPO_ROOT/'eventx/release/v7/memory_shadow_20261024/implementation_manifest.json',
        REPO_ROOT/'eventx/release/v7/quote_source_20261024_v02/implementation_manifest.json',
        REPO_ROOT/'data/v7/quote_shadow_diagnosis_20261024/manifest.json']
    verified=0
    for path in manifests:
        m=json.loads(path.read_text())
        for p,h in m.get('locked_files',m.get('files',{})).items():
            if sha(REPO_ROOT/p)!=h:raise RuntimeError('Frozen file drift: '+p)
            verified+=1
    # Copy source after forecast journal so every referenced source record is included.
    forecasts=copy_chain(shadow/'journal.jsonl',OUT/'forecast_journal.jsonl')
    receipts=copy_chain(source/'journal.jsonl',OUT/'source_journal.jsonl')
    for name,p in [('shadow_status',shadow/'status.json'),('source_status',source/'status.json'),('latest_forecasts',shadow/'latest_forecasts.json'),('run_contract',shadow/'run_contract.json')]:
        write(OUT/(name+'.json'),json.loads(p.read_text()))
    process=subprocess.run(['ps','-o','pid,ppid,etime,stat,command','-p','600,23793,5099,8023'],capture_output=True,text=True)
    (OUT/'processes.txt').write_text(process.stdout)
    decisions={r['record_sha256']:r for r in forecasts if r['kind']=='decision'}
    commits=[r for r in forecasts if r['kind']=='emission_commit' and r['timely']]
    payload_receipts=defaultdict(list)
    for r in receipts:
        if r.get('kind')=='rest' and r.get('status')=='observed' and r.get('available_at'):payload_receipts[r['payload_sha256']].append(stamp(r['available_at']))
    used={}
    for c in commits:
        d=decisions[c['decision_sha256']];t=stamp(d['grid_at'])
        if not t<=stamp(d['recorded_at'])<=stamp(c['at'])<=t+30<t+1800:raise RuntimeError('Forecast timing failure')
        if d['predictions']['persistence']!=d['midpoint']:raise RuntimeError('Baseline mismatch')
        for h in d['input_payload_hashes']:
            if not any(a<=t for a in payload_receipts[h]):raise RuntimeError('Post-decision or missing input')
            p=source/'objects'/h
            if sha(p)!=h:raise RuntimeError('Payload mismatch')
            used[str(p.relative_to(REPO_ROOT))]=h
    outcome_count=sum(r['kind']=='outcome' and r['status']=='observed' for r in forecasts)
    audit={'at':at,'original_locks_verified':locks,'manifest_entries_verified':verified,'source_records_verified':len(receipts),
        'forecast_records_verified':len(forecasts),'scheduled_decisions':len(decisions),'timely_forecasts':len(commits),'observed_endpoints':outcome_count,
        'statuses':dict(Counter(r['status'] for r in decisions.values())),'used_input_payloads_verified':len(used),
        'input_availability_before_decision':True,'emission_before_target':True,'new_source_pid':5099,'forecast_pid':8023,
        'predictive_superiority_established':False,'independent_confirmation':False,'protected_data_opened':False}
    write(OUT/'audit.json',audit);write(OUT/'used_payload_hashes.json',used)
    dev=json.loads((base/'development/report.json').read_text());old=json.loads((REPO_ROOT/'data/v7/quote_experiment_20261024/development/report.json').read_text())
    diag=json.loads((base/'error_diagnosis/report.json').read_text());live=json.loads((OUT/'latest_forecasts.json').read_text())
    def table(panel):
        return '\n'.join('| '+k+' | '+str(v['rows'])+' | '+format(v['mae'],'.10f')+' | '+format(v['rmse'],'.10f')+' |' for k,v in panel.items())
    examples=[]
    for r in live['forecasts'].values():
        examples.append(f"| {r['question']} | {r['grid_at']} | {r['target_at']} | {r['status']} | {r['reference_midpoint_30m']} |")
    report=f'''# EventX: usable quote-forecast prototype and research progress

Checkpoint: {at}. This report is a frozen checkpoint; use the freshness-checking command below for current output.

## Result and meaning

The separate quote pipeline now has **{len(commits)} timely prospective forecasts recorded**, with **{outcome_count} observed endpoints** at this checkpoint. This is an operational forecasting prototype, not demonstrated predictive superiority. The reference forecasts the same YES-book midpoint30minutes later. Candidate regression forecasts are recorded separately; neither regression beat persistence in development.

The original condition_120k trade-movement classifier remains frozen and unscored on this capture. Quote-midpoint prediction is a different target and cannot inherit its historical log-loss improvements. No news effect, profitability or resolved-market outcome prediction is claimed.

## What failed and what changed

The first four-hour-history shadow finished with100decision opportunities:44abstentions,56missed,0forecasts,0endpoints. Every abstention lacked continuous240-minute history. Observed cycle gaps were4473.100816seconds and2159.973661seconds. These records establish interruption; this audit alone does not establish its cause. All closed artifacts are preserved.

The new experiment explicitly separates feature requirements:

1. **Snapshot reference:** current valid book and verified current market/status mapping. No past price history is needed to forecast an unchanged midpoint.
2. **Snapshot ridge:** seven current-book features, fixed ridge penalty100, fitted once on chronological development training data.
3. **Short-history ridge:** those seven features plus5-minute momentum,30-minute momentum and30-minute volatility. Available only with uninterrupted30-minute quote history.
4. **Weighted midpoint:** a size-weighted best-bid/best-ask comparator, not a fully estimated microprice model.

The current-book gates remain: receipt age<=120seconds, two positive sides inside(0,1), spread<=0.05, at least10tokens at each best side, exact condition/token/rules mapping, active and accepting orders, not closed, and unresolved/undisputed status. Status receipt age<=360seconds. Scheduled expiry must exceed the30-minute horizon. Future labels still require continuous quote/status coverage; failed or missing observations are never imputed. These are separately specified research eligibility rules, not certified economic thresholds.

Snapshot ridge inputs are midpoint,spread,log bid size,log ask size,imbalance,weighted-midpoint offset and log source-message age. Training-only mean/std normalization; ridge with unpenalized intercept predicts midpoint change and clips the resulting midpoint to[0,1]. No parameter search, live refitting, promotion or automatic trading.

## Development results: compare within each panel

Same previously exposed source snapshot,4032scheduled rows. Snapshot eligible1625,short-history eligible1418;1418complete snapshot observations versus686in the earlier240-minute-history design. This is a coverage improvement caused by different feature requirements, not an accuracy improvement or new independent events.

Snapshot:684training rows;614validation rows across11markets. Only23validation midpoints changed.

| Model | Matched validation rows | MAE | RMSE |
|---|---:|---:|---:|
{table(dev['matched_metrics']['snapshot'])}

Short-history panel:605training rows;588validation rows across11markets. Only23validation midpoints changed.

| Model | Matched validation rows | MAE | RMSE |
|---|---:|---:|---:|
{table(dev['matched_metrics']['short'])}

Errors are in0–1 price units; lower is better. Multiplying by100 converts to percentage points. Rows differ between panels; compare models within a panel. Persistence remains best in both. The prior240-minute panel had444validation rows: persistence MAE{old['metrics']['persistence']['mae']},ridge MAE{old['metrics']['ridge']['mae']},weighted MAE{old['metrics']['weighted_midpoint']['mae']}.

Train endpoints precede24Oct00:00UTC; validation decisions start00:30UTC, with the intervening rows purged. The data were already exposed in related research. This is exploratory development, with overlapping30-minute horizons and one short shared calendar period; no confidence intervals or independent-confirmation claims.

## Why the learned forecasts lose

In the short panel,565/588validation endpoints are unchanged. Persistence makes zero error there; short ridge introduces MAE0.000047602735990905376. On23changed endpoints, short ridge MAE0.0016600457606747287 is slightly below persistence0.001673913043478262, but that does not overcome errors on unchanged rows. This is an **outcome-conditioned diagnosis**, not a deployable filter: we cannot select changed rows before forecasting.

The short-model training mean change is+0.000016528925619834755; validation mean change is−0.00005017006802721093. Drift direction changes, and the median change is zero in both. A useful next learned component would need to predict whether a change occurs, before predicting its direction/size. More independent changing episodes are needed before fitting and assessing that component. It is not added to the current frozen run.

## Live run and how to inspect it

SourcePID5099 started24Oct14:04UTC and is bounded to25Oct14:04UTC(22:04SGT). ForecastPID8023 started14:08UTC,first grid14:10UTC; last grid25Oct13:30UTC and scheduled stop14:03UTC(22:03SGT). A powered, awake, networked Mac with its lid open is required; the process cannot produce forecasts during a host interruption.

| Market | Decision UTC | Target UTC | Recorded state | Persistence midpoint |
|---|---|---|---|---:|
{chr(10).join(examples)}

These are checkpoint examples, not permanently current prices. From the repository run:

```sh
.venv/bin/python -m eventx.tasks.show_v7_quote_forecasts_20261024
```

This reader suppresses forecasts when the service heartbeat is older than30seconds, the current five-minute display interval has expired, or no timely forecast was committed. `latest_forecasts.json` contains reference and candidate values, book timestamps, short-history availability and out-of-training-range flags. The frozen historical range is a diagnostic, not a calibrated confidence interval.

The append-only forecast journal records inputs available by the decision grid, model hashes, output, emission time, abstentions and missed deadlines. A forecast must be durably recorded by grid+30seconds. Its30-minute endpoint is adjudicated after a120-second operational delay, using only receipts available by the target time. No backdated forecasts or late-filled targets. The completion report will compare all models on matched eligible endpoints, with missing endpoints and coverage reported separately.

At this checkpoint, {audit['manifest_entries_verified']}manifest entries and both journal chains were checked; {len(used)}used input payloads verified. Every committed forecast checked used pre-decision receipts and was emitted before its target. The original{locks}file locks also match. No protected holdout was opened.

## Next research decision

1. Let the fixed run collect actual forecasts and endpoints; monitor receipt gaps and endpoint loss. No tuning from interim results.
2. Audit its completed journal and report coverage, MAE/RMSE, changed-endpoint count, per-market results and missingness. A few repeated predictions on two markets establish operation, not broad forecasting validity.
3. Collect across additional independent dates and the already reserved release episodes, with exact evidence/terminal checks for any news comparison.
4. After sufficient development evidence, freeze a separate change-occurrence plus conditional-movement experiment. It must beat persistence across all eligible rows, not just hindsight-selected changed rows.

## Reproducible artifacts

- New policy/code locks: `eventx/release/v7/memory_quote_20261024/`.
- Development receipt,models,observations,predictions,metrics and manifest: `data/v7/memory_quote_20261024/development/`.
- Error diagnosis: `data/v7/memory_quote_20261024/error_diagnosis/`.
- Prospective activation: `eventx/release/v7/memory_shadow_20261024/`.
- Live journal/status/output and eventual completion report: `data/v7/memory_quote_20261024/shadow/`.
- New source receipts: `data/v7/quote_source_20261024_v02/live/`.
- This checkpoint and audit: `data/v7/usable_forecast_progress_20261024/`.
- Preserved first-run diagnosis: `data/v7/quote_shadow_diagnosis_20261024/`.
'''
    REPORT.write_text(report)
    state=REPO_ROOT/'CURRENT_STATE.md';oldstate=state.read_text();archive=REPO_ROOT/'docs/progress/CURRENT_STATE_ARCHIVE_20261024_BEFORE_MEMORY_FORECAST.md';archive.write_text(oldstate)
    tail=oldstate[oldstate.index('## Selected market model: retain raw condition_120k'):]
    a=tail.index('## Next actions');b=tail.index('## Authoritative references')
    tail=tail[:a]+'''## Next actions

1. Monitor current source and memory-tier forecast jobs; use the freshness-checking CLI below.
2. At completion audit matched endpoints and missingness, report MAE/RMSE and per-market results.
   No candidate promotion or retuning from interim results; two markets are not independent event yield.
3. Continue original release capture and reserved29Oct–4Dec episodes; exact evidence/terminal gates remain.
4. After enough independent development episodes, freeze a separate change-occurrence model; unchanged
   endpoints must remain in its population. Original trade-model gates remain unsatisfied.
5. Keep V4 operational checks separate; follow its frozen close/consumption sequence exactly once.

'''+tail[b:]
    intro=f'''# EventX current state

> Canonical startup handoff. Frozen artifacts govern conflicts. Detailed preceding state:
> `docs/progress/CURRENT_STATE_ARCHIVE_20261024_BEFORE_MEMORY_FORECAST.md`.
> Append history to `docs/progress/2026-10.md`,not legacy PROGRESS.md.

Last updated: **2026-10-24 Asia/Singapore**, checkpoint{at}.

## Active objective and locked decisions

User authorized autonomous LOCAL research and separately versioned quote forecasting;SSH unavailable.
Produce timely forecasts and evaluate actual endpoints; do not equate operation with predictive superiority.
Original raw condition_120k trade classifier stays frozen:zero current prospective admissions.
New quote target is received YES-book midpoint30min later,not the original absolute-movement classifier.
No outcome-driven cohort replacement,protected early evaluation,external messages or trading.

## Current quote forecast result and jobs

Report:`EVENTX_USABLE_FORECAST_PROGRESS_20261024.md`;checkpoint:`data/v7/usable_forecast_progress_20261024/`.
- First240m-history shadow CLOSED:100decisions,44abstentions,56missed,zero forecasts/endpoints.
  All44abstentions lacked240m history;source cycle gaps4473.100816s/2159.973661s.
  `data/v7/quote_shadow_diagnosis_20261024/`;closed PIDs31131/61679. No late rescoring.
- First development:686complete,168train,444validation/9markets,21changed;persist MAE0.00008445945945945952,
  ridge0.00018114435192817977. All exploratory;no candidate promoted.
- NEW frozen memory-tier development:`data/v7/memory_quote_20261024/development/`:
  4032grids,1625snapshot-eligible,1418short-history-eligible,1418complete snapshot rows.
  Snapshot684train/614validation11markets,23changed;MAE persist0.0000627035830618893,ridge0.00015594596290242812.
  Short605train/588validation11markets,23changed;MAE persist0.00006547619047619052,short-ridge0.0001106744869564291.
  Same rows within panels,not across panels. Coverage improved;accuracy did not beat persistence.
  Outcome-exposed development,overlapping horizons,no independent confirmation. No promotion/refit.
- Snapshot reference needs fresh valid book/current status;short-ridge needs continuous30m history.
  Current book<=120s,spread<=.05,best-side depth>=10;mapping/status<=360s,active/unresolved;
  full30m forward quote/status continuity still required. Missing data stay unknown.
- NEW sourcePID5099,`data/v7/quote_source_20261024_v02/live/`,same2metadata-defined markets.
  Started24Oct14:04UTC,scheduledstop25Oct14:04UTC(22:04SGT);separate24h source run.
- NEW forecastPID8023,`data/v7/memory_quote_20261024/shadow/`;firstgrid24Oct14:10UTC;
  lastgrid25Oct13:30UTC,stop14:03UTC(22:03SGT). Code/models frozen in memory_shadow_20261024.
  Checkpoint:{len(commits)}timelyforecasts,{outcome_count}observedendpoints;see journal/status for later counts.
  Reference=persistence;fixed weighted/snapshot-ridge/short-ridge candidates;no proven predictive edge.
  Reader:`.venv/bin/python -m eventx.tasks.show_v7_quote_forecasts_20261024`;rejects stale heartbeat/grid.
- Original releasePID600 and37-marketPID23793 verified alive at checkpoint. Last source audit79documentversions;
  zero newly admitted release evidence;BLS403 historically unresolved. No current V4 health claim.
- KeepMacpowered/awake/networked/lid-open. Sleep/receipt gaps invalidate affected windows;
  service cannot forecast while host suspended. Raw backfills never restore earlier availability.

## Other source evidence retained

- Original/revised22-market rehearsals completed:588233/380142records;0/3159 and0/2016activitypasses.
  Different periods,not controlled improvement. Revised maxgap26627.861848s;host sleep overlaps.
- Price-blind metadata expansion204records ->2new candidates,470protected IDs excluded.
  GDP full-year/annualized rule and recession dual GDP/NBER early-terminal caveats remain;not human gold.
- Provider52records map52orderfills/29transactions,mixedmaker/taker schema;16/63omissions recovered late,
  remaining47chainmatched. No general accounting fix or old-model feature parity. Request remains unsent.
- Cross-token overlap V03:8roundedcomplementarypairs in240m,0same-directionpairs;last60m naivecount4->2ifcollapsed.
  PriorV01/V02prose errors preserved/superseded;not general executiondeduplication.
- Alternative methods report:`EVENTX_ALTERNATIVE_FORECASTING_METHODS_20261024.md`;later frozen quote studies
  supersede its unactivated-proposal status. Original source/frozen-trade rules remain unchanged.
- Six original release episodes29Oct–4Dec retained;12new metadata links provisional. No news-event service
  activated,exact-predicate and independent episode/power requirements unresolved.

'''
    state.write_text(intro+tail)
    with (REPO_ROOT/'docs/progress/2026-10.md').open('a') as f:
        f.write(f'\n\n### 2026-10-24 — prospective memory-tier service and checkpoint\n\nAt{at},sourcePID5099 and forecastPID8023 verified running alongside600/23793. First forecast grid14:10UTC,source ends25Oct14:04UTC,shadow25Oct14:03UTC. Checkpoint{len(commits)}timely forecasts,{outcome_count}observed endpoints;{len(used)}input payloads independently checked for pre-decision availability/hash;{verified}manifest entries verified. Fixed persistence reference plus weighted/snapshot-ridge/short-ridge;no promotion,trading,holdout use or original trade-model scoring. Freshness-checking reader rejects heartbeat>30s or expired five-minute display. Full result,method,limits and exact artifacts in `EVENTX_USABLE_FORECAST_PROGRESS_20261024.md`;frozen checkpoint `data/v7/usable_forecast_progress_20261024/`. Error diagnosis:565/588short-panel endpoints unchanged;short ridge adds MAE0.000047602735990905376 there;on23changed endpoints MAE0.0016600457606747287 vs persistence0.001673913043478262. Hindsight changed-row subset is diagnostic only. No model change from diagnosis. Prior state archived;CURRENT_STATE compacted.\n')
    paths=list(OUT.iterdir())+manifests+[REPORT,Path(__file__).resolve(),archive]
    write(OUT/'manifest.json',{'files':{str(p.relative_to(REPO_ROOT)):sha(p) for p in paths}})
    print(json.dumps({'audit':audit,'report':str(REPORT.relative_to(REPO_ROOT)),'state_lines':len(state.read_text().splitlines())},indent=2))

if __name__=='__main__':main()
