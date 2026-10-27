"""Freeze operational evidence from the completed first quote shadow run."""
from collections import Counter
import hashlib
import json
from pathlib import Path
from eventx.tasks.discover_v7_direct_pilot_20261022 import REPO_ROOT,now,sha,write,verify_originals
from eventx.v7.quote_experiment_20261024 import stamp

OUT=REPO_ROOT/'data/v7/quote_shadow_diagnosis_20261024'
def chain(path):
    rows=[];head=None
    for line in path.read_bytes().splitlines():
        r=json.loads(line);v=dict(r);h=v.pop('record_sha256')
        if v['previous_sha256']!=head or hashlib.sha256(json.dumps(v,sort_keys=True,separators=(',',':')).encode()).hexdigest()!=h:
            raise RuntimeError('Journal chain mismatch')
        rows.append(r);head=h
    return rows

def main():
    OUT.mkdir(exist_ok=False);verify_originals()
    shadow=REPO_ROOT/'data/v7/quote_experiment_20261024/shadow'
    source=REPO_ROOT/'data/v7/expansion_source_pilot_20261024/audits/20261024T134408Z_49467b'
    manifests=[shadow/'completion_manifest.json',source/'manifest.json',REPO_ROOT/'data/v7/quote_experiment_20261024/development/manifest.json',
        REPO_ROOT/'eventx/release/v7/quote_experiment_20261024/implementation_manifest.json',REPO_ROOT/'eventx/release/v7/quote_shadow_20261024/implementation_manifest.json']
    for p in manifests:
        m=json.loads(p.read_text())
        for f,h in m.get('locked_files',m.get('files',{})).items():
            if sha(REPO_ROOT/f)!=h:raise RuntimeError('Artifact hash mismatch: '+f)
    rows=chain(shadow/'journal.jsonl');src=chain(source/'journal.jsonl')
    decisions=[r for r in rows if r['kind']=='decision']
    gaps=[r for r in src if r['kind']=='operational_cycle_gap']
    report={'at':now().isoformat(),'shadow_records':len(rows),'source_records':len(src),
        'decisions':len(decisions),'decision_statuses':dict(Counter(r['status'] for r in decisions)),
        'abstention_reasons':dict(Counter(x for r in decisions if r['status']=='abstained' for x in r['reasons'])),
        'timely_forecasts':sum(r['kind']=='emission_commit' and r['timely'] for r in rows),
        'outcomes':sum(r['kind']=='outcome' for r in rows),
        'cycle_gaps':[{'at':r['at'],'seconds':r['seconds']} for r in gaps],
        'missed_grid_times':sorted({r['grid_at'] for r in decisions if r['status']=='missed'}),
        'interpretation':'Operational availability failure; no predictive errors can be measured. Process interruptions observed; this audit alone does not identify host-sleep causality.',
        'old_trade_model_changed':False,'protected_data_opened':False}
    write(OUT/'report.json',report)
    for name,p in [('source_status',source/'status.json'),('shadow_completion',shadow/'completion_report.json')]:write(OUT/(name+'.json'),json.loads(p.read_text()))
    archive=REPO_ROOT/'docs/progress/CURRENT_STATE_ARCHIVE_20261024_QUOTE_PRE_HANDOFF.md'
    state=REPO_ROOT/'CURRENT_STATE.md';old=state.read_text();archive.write_text(old)
    s=old.replace('(source rehearsals complete; new two-market pilot running; zero forecasts)','(first quote comparison completed; first shadow finished with zero forecasts)')
    s=s.replace('Proposal not activated;no fit/labels/scores.','Proposal subsequently authorized and frozen; see quote update below.')
    s=s.replace('authorizes V7 sources only.','authorizes V7 sources and a separate quote-forecast experiment.')
    s=s.replace('## Selected market model: retain raw condition_120k',
        '## Quote forecast update (canonical correction, 24October)\n\n'
        '- New authorized quote target: received YES-book midpoint in30min; separate from old trade classifier.\n'
        '- Frozen development:686 complete rows;168 training,444 validation across9markets,74purged.\n'
        '- MAE persistence0.00008445945945945952;ridge0.00018114435192817977;weighted0.0019342785670910098.\n'
        '  Only21/444 validation midpoints changed; source-exposed, no independent confirmation or promotion.\n'
        '- First shadow completed:100 decisions,44abstentions,56missed,0timely forecasts,0outcomes.\n'
        '  Source and shadow PIDs31131/61679 exited; prior running claims above are historical.\n'
        '- Frozen evidence:`data/v7/quote_experiment_20261024/development/`,shadow/completion_manifest.json;\n'
        '  diagnosis:`data/v7/quote_shadow_diagnosis_20261024/report.json`. Original jobs600/23793 verified alive.\n'
        '- Next: separately versioned snapshot persistence plus30m-history candidate, fresh-input gates intact;\n'
        '  new bounded source run and prospective forecast journal. Old four-hour study remains closed.\n\n'
        '## Selected market model: retain raw condition_120k')
    state.write_text(s)
    with (REPO_ROOT/'docs/progress/2026-10.md').open('a') as f:
        f.write('\n\n### 2026-10-24 — first quote experiment and completed shadow diagnosis\n\n'
            'The preceding turn was interrupted before handoff maintenance. Corrected stale proposal/running claims using frozen artifacts. '
            'Separate quote study:686complete,168train/7markets,444validation/9markets,74purged;21changed validation midpoints. '
            'Persistence MAE8.445945945945952e-05/RMSE0.0005884588208054871;ridge MAE0.00018114435192817977/RMSE0.0006922761121688823;'
            'weighted MAE0.0019342785670910098/RMSE0.0028303653041149564. No candidate promoted; retrospective source-exposed comparison only. '
            'First prospective shadow started08:49:56UTC,finished13:35:52UTC;100decisions,44abstentions,56missed,zero forecasts/outcomes. '
            'New source run finished13:44:08UTC;4722records,1340verifiedpayloads,2031HTTP200,8HTTP502,3failedrequests. '
            'Original release/37-market jobs600/23793 alive at13:58UTC;31131/61679 absent. '
            'Diagnosed evidence and cycle gaps in `data/v7/quote_shadow_diagnosis_20261024/report.json`; old state archived as '
            '`docs/progress/CURRENT_STATE_ARCHIVE_20261024_QUOTE_PRE_HANDOFF.md`. '
            'No holdout opened, no old trade model change. Next authorized work: separate memory-tier quote service; preserve closed240m study.\n')
    files=list(OUT.iterdir())+manifests+[Path(__file__).resolve(),archive]
    write(OUT/'manifest.json',{'files':{str(p.relative_to(REPO_ROOT)):sha(p) for p in files}})
    print(json.dumps(report,indent=2))

if __name__=='__main__':main()
