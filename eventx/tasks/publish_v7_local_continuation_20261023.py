"""Freeze local diagnostic handoff and concrete source-review questions."""
from collections import Counter
from datetime import datetime, timezone
import json
from pathlib import Path
from eventx.tasks.diagnose_v7_execution_accounting_20261022 import (
    ROOT, AUDIT, RUN, lines, economic, sha, write, verify_manifest,
)
from eventx.tasks.discover_v7_direct_pilot_20261022 import verify_originals

OUT = ROOT / 'data/v7/local_continuation_20261023'

def main():
    OUT.mkdir(exist_ok=False)
    diagnostic = ROOT / 'data/v7/local_execution_accounting_20261022'
    coverage = ROOT / 'data/v7/participant_coverage_20261023'
    for p in [diagnostic/'manifest.json', coverage/'manifest.json']:
        verify_manifest(p)
    accounting = json.loads((diagnostic/'report.json').read_text())
    result = json.loads((coverage/'report.json').read_text())
    source = {}
    for r in lines(AUDIT/'journal.jsonl'):
        if r['kind']=='rest' and r.get('endpoint_kind')=='trades' and r['cycle']==1 and r.get('status')=='observed':
            p=RUN/'objects'/r['payload_sha256']
            if sha(p)!=r['payload_sha256']:raise RuntimeError('Payload mismatch')
            v=json.loads(p.read_text());source[r['market_id'],r['source']]=v['data'] if isinstance(v,dict) else v
    wallet=Counter()
    for (cid,src),ps in source.items():
        if src!='lumid':continue
        for p in ps:
            m=[v for v in source[cid,'venue'] if economic(v,True)==economic(p,True) and str(p['trade_id']).startswith(v['transaction_hash'])]
            w=[v for v in m if str(p.get('taker','')).lower()==str(v.get('proxy_wallet','')).lower()]
            wallet['provider_rows']+=1;wallet['wallet_matches_'+str(len(w))]+=1
    workflow=json.loads((ROOT/'data/v7/source_workflow_20261022/status.json').read_text())
    captures={}
    for name,rel in [('direct','data/v7/direct_source_pilot_20261022/live'),('releases','data/v7/official_source_capture_20261018/live'),('original_market','data/v7/market_cohort_capture_20261018/live')]:
        raw=(ROOT/rel/'status.json').read_bytes();p=OUT/(name+'_status_snapshot.json');p.write_bytes(raw)
        v=json.loads(raw)
        captures[name]={k:v[k] for k in ['at','pid','journal_records','document_versions','cycle','cycles','stop_at'] if k in v}
    write(OUT/'workflow_status_snapshot.json',workflow)
    summary={'at':datetime.now(timezone.utc).isoformat(),'local_workflow':workflow,'capture_checkpoints':captures,
             'production_locks_verified':verify_originals(),'accounting_report':str((diagnostic/'report.json').relative_to(ROOT)),
             'coverage_report':str((coverage/'report.json').relative_to(ROOT)), 'wallet_diagnostic':dict(wallet),
             'human_review_needed_before':'Canonical execution mapping and future event-study activation; collection continues automatically.',
             'provider_message_sent':False,'models_scored':False,'labels_computed':False,'predictive_admissions':0,'tests_added_or_run':False}
    write(OUT/'report.json',summary)
    review='''# Source-accounting review package — 23 October 2026 Singapore

Status: prepared for review; no provider message sent. Collection continues locally.

## Decisions requiring external evidence or scientific review

1. **Define one historical observation.** Does provider `trade_id` identify a participant row, fill, or transaction? What does its suffix encode? Provide a stable execution/log index and same-second ordering. A transaction-hash prefix is insufficient: four of52provider rows still have two rounded economic candidates within that transaction.
2. **Explain mixed participant coverage.** In the common six-hour diagnostic windows,52provider rows comprise29matching retained taker keys and23matching maker-inclusive-only keys. Liquid controls have45provider rows against88taker-only rows;25match and63taker rows are absent from the provider snapshot. Explain inclusion filters, upstream aggregation and delayed ingestion. The direct inclusive snapshot has378control rows and is identical in the later capture over these same windows. This is bounded evidence, not exchange completeness.
3. **Clarify participant fields.** Provider `taker` equals venue `proxy_wallet` for only16of52provider rows under the rounded economic/transaction-prefix match. The remaining36do not match. Do not use those field names as a verified join rule.
4. **Approve an accounting bridge only after evidence.** Preserve historical provider rows. Do not silently substitute taker-only records into the frozen booster, collapse a whole transaction to one fill, or count maker-inclusive rows as independent executions. Any new representation requires a separate version and compatibility analysis.
5. **Freeze endpoint timing before prospective forecasting.** After the24hsource audits, review the proposed fresh YES endpoint at t+30m, acquisition-latency deadline, terminal-state rule and event anchor in EVENTX_CONCRETE_STUDY_PLAN_20261022.md. These remain design proposals; no forward target has been constructed here.

## Evidence to inspect

- `data/v7/local_execution_accounting_20261022/provider_reconciliation.jsonl`: per-provider-row match counts, hashed IDs and raw receipt hashes.
- `data/v7/local_execution_accounting_20261022/canonical_yes_modes.jsonl`:22market maker-inclusive/taker-only YES counts and quantities.
- `data/v7/participant_coverage_20261023/market_coverage.jsonl`:22common windows, original/later direct snapshot agreement and provider coverage.
- `data/v7/participant_coverage_20261023/provider_membership.jsonl`: per-row classification; later snapshot membership is not a gold participant-role label.
- V03 raw receipt/audit: `data/v7/direct_source_pilot_20261022_v03/audits/20261022T111727Z_158a60/`.
- Paired probe: `data/v7/execution_identity_20261022/d1ae8e245c3f47b1a7d9160759a52613/`.

Reviewer response should state reviewer identity/role, exact evidence inspected, answers with source documentation, unresolved items, and any proposed mapping. Do not mark this packet approved merely because its JSON or hashes are valid. No independent human review has occurred.
'''
    (OUT/'REVIEW_PACKAGE.md').write_text(review)
    md=f'''# EventX local research continuation

23 October 2026, Singapore. Evidence captured at {summary['at']}.

## Local workflow is active

Following your instruction to work locally, the separately frozen background service `com.eventx.source-workflow.20261022` was registered and its process verified (PID74338). Its current phase is **{workflow['phase']}**. SSH is no longer a dependency. The previous failed SSH record and remote package remain historical artifacts.

The workflow will:

1. Wait for the original rehearsal to finish on **23October13:58:25Singapore** and verify its completed audit.
2. Run the separately frozen revised collector for24hours using the replacement trade API.
3. Write and review the final source audit, then stop before event activation or model scoring. If it starts promptly, the second run will finish around **24October14:00Singapore**. This is conditional on local execution, not a guarantee.

The three original collectors remain present (PIDs600,23793,39643). The41workflow dependency hashes and original production locks were verified. The Mac must remain powered, awake and connected; the prior lid-closed sleep gap remains part of the source record.

## New findings

|Diagnostic|Result|Meaning|
|---|---:|---|
|First-cycle provider rows|52|Bounded source sample, not52independent events|
|Exact decimal economic matches|42|Previous result reproduced|
|Additional matches explained by price precision|10|All from one liquid control; largest price difference2.69823×10⁻¹¹|
|Rounded economic matches with transaction prefix|52/52|Every provider row is compatible with retained direct data under this diagnostic|
|Ambiguous transaction-prefix matches|4|Unique execution identity remains unresolved|
|Extra direct rows after multiset matching|334|333in controls,1in prospective macro candidates|
|Different YES prices within the same second|9seconds|All in controls; ordering can affect last-trade features|

The ten-decimal rounding rule is an exploratory explanation, **not an adopted change to model inputs**. Across all31comparable market-cycle windows,54provider row occurrences comprise44exact matches and10precision-explained matches. Repeated occurrences are dependent.

### Maker/taker selection cannot by itself reconcile the provider

We compared the same retained time windows against the later paired maker-inclusive/taker-only probe. All22markets had a shared range. The earlier and later maker-inclusive snapshots were identical under transaction plus rounded economic keys in these windows.

|Source group|Provider rows|Direct maker-inclusive rows|Direct taker-only rows|Taker-only rows unmatched by provider|
|---|---:|---:|---:|---:|
|14prospective macro candidates|3|4|2|0|
|3legacy macro diagnostic markets|4|4|2|0|
|5liquid controls|45|378|88|63|

Among the52provider rows,29match retained taker keys and23match keys found only in the maker-inclusive response. Thus the provider sample cannot be reconstructed simply by selecting all taker rows. This suggests both differing participant accounting and incomplete/different provider coverage. Separately captured API snapshots and unknown filters prevent a claim about complete exchange history.

The distinction affects the candidate cohort too: one annual GDP candidate has2YES maker-inclusive rows/59.96tokens versus1taker-only row/29.98tokens in the paired probe. Selecting a mode can change activity counts and size features. No canonical mode was selected from this diagnostic.

## Research status and next review

**Zero predictive admissions; no new forecast-performance claim.** The market model remains fixed, protected evaluations remain untouched, and no labels or predictions were generated. Source accounting is now more clearly diagnosed: price formatting explains the earlier10unmatched records, while participant semantics, coverage and same-second ordering still require evidence.

The local workflow can complete its scheduled collection without another research decision. Before canonical trade mapping or event-study activation, review [the concrete source-accounting package](data/v7/local_continuation_20261023/REVIEW_PACKAGE.md). Provider clarification remains prepared and unsent. We have not described automated checks as independent human review.

## Reproducible artifacts

- [Execution accounting](data/v7/local_execution_accounting_20261022/report.json), frozen code/input hashes and row-level receipts.
- [Participant coverage](data/v7/participant_coverage_20261023/report.json), shared windows and row classifications.
- [Continuation snapshot](data/v7/local_continuation_20261023/report.json), timestamped process checkpoints and model/source locks.
- Live workflow status: `data/v7/source_workflow_20261022/status.json`; phase transitions also append to the monthly progress log.

No model retraining, protected evaluation, test-suite execution or external message was performed.
'''
    public=ROOT/'EVENTX_LOCAL_RESEARCH_CONTINUATION_20261023.md';public.write_text(md);(OUT/'REPORT.md').write_text(md)
    files=list(OUT.iterdir())+[public,Path(__file__).resolve(),diagnostic/'manifest.json',coverage/'manifest.json']
    write(OUT/'manifest.json',{'files':{str(p.relative_to(ROOT)):sha(p) for p in files}})
    state=ROOT/'CURRENT_STATE.md';s=state.read_text()
    s=s.replace('Last updated: **2026-10-22 Asia/Singapore** (local continuation authorized; source workflow starting)',
                'Last updated: **2026-10-23 Asia/Singapore** (local workflow active; execution accounting diagnosed)')
    marker='### Prior source diagnosis and remaining gates'
    addition='''### Local source diagnosis,23October

- `EVENTX_LOCAL_RESEARCH_CONTINUATION_20261023.md`; workflow PID74338 verified.
  Original stop23Oct13:58SGT, then separate24hV03 capture/audit; no event activation.
- Price precision explains10previously unmatched rows (maximum2.69823e-11);52/52
  provider rows have rounded economic+transaction-prefix matches,4remain ambiguous.
- Extra direct rows334:333controls/1candidate. Same-window later inclusive snapshots
  unchanged; provider52rows mix29taker keys/23maker-only keys. Controls63taker rows
  absent from provider. A taker-only switch cannot reproduce historical accounting.
- Provider taker versus venue proxy_wallet agrees16/52only; no verified join rule.
  Nine YES seconds have conflicting prices,all controls; sequence remains unresolved.
- Review package `data/v7/local_continuation_20261023/REVIEW_PACKAGE.md` prepared,
  unsent. External semantic clarification required before canonical mapping/admission.
  Source diagnostics do not change frozen features; zero new predictive results.

'''
    s=s.replace(marker,addition+marker);state.write_text(s)
    with (ROOT/'docs/progress/2026-10.md').open('a') as f:
        f.write('\n### Local workflow active and execution accounting diagnosis — '+summary['at']+'\n\n')
        f.write('Registered com.eventx.source-workflow.20261022, PID74338; confirmed original PIDs600/23793/39643 present. It waits for original completion, runs/audits V03 for24h, then stops before scoring. SSH blocker superseded by user local-only instruction.\n\n')
        f.write('Frozen diagnostic:42/52exact matches plus10precision explanations(max2.69823e-11),52rounded-prefix matches,4ambiguous. All31market-cycle windows contain54provider occurrences:44exact+10precision. Extra direct rows334(333controls,1candidate);9conflicting YES seconds in controls. Shared22market windows show unchanged early/later direct-inclusive keys; provider52rows mix29taker/23maker-inclusive-only keys. Controls63taker rows unmatched by provider. Wallet match16/52;36unmatched. No canonical remapping or unique-execution claim.\n\n')
        f.write('Evidence and concrete human/provider review packet: EVENTX_LOCAL_RESEARCH_CONTINUATION_20261023.md; data/v7/local_continuation_20261023/manifest.json; linked accounting/coverage freezes. Source/model locks verified; no labels, models, holdouts, tests or external messages. Background phase receipts continue in this log.\n')
    print(json.dumps({'report':str(public.relative_to(ROOT)),'review_package':str((OUT/'REVIEW_PACKAGE.md').relative_to(ROOT)), 'workflow_phase':workflow['phase'],'wallet_diagnostic':dict(wallet)},indent=2))

if __name__=='__main__':
    main()
