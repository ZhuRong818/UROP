"""Verify and publish the frozen seven-day replication; no training or evaluation rerun."""
from collections import defaultdict
from datetime import datetime,timezone
import json
from pathlib import Path
import numpy as np
import pyarrow.parquet as pq
from sklearn.metrics import log_loss,brier_score_loss,average_precision_score,roc_auc_score
from eventx.tasks.discover_v7_direct_pilot_20261022 import REPO_ROOT,sha,write,now
from eventx.tasks.run_v7_week_replication_20261025 import BASE,REL,PRIOR,MODELS,DATES


def load(p):return json.loads(p.read_text())


def verify_delivery():
    visited=set();entries=0
    def check(p):
        nonlocal entries
        if p in visited:return
        visited.add(p);m=load(p);hashes=m.get('files',m.get('locked_files'));assert hashes is not None,str(p)
        for name,h in hashes.items():
            f=REPO_ROOT/name;assert sha(f)==h,name;entries+=1
            if f.name.endswith('manifest.json'):check(f)
    check(BASE/'evaluation/manifest.json')
    r=load(BASE/'evaluation/result.json');receipt=load(BASE/'evaluation/consumption_receipt.json')
    assert receipt['status']=='completed' and r['dates']==DATES and r['selected']=='row_hgb7'
    assert not r['model_refit'] and not r['prospective']
    freeze_at=datetime.fromisoformat(load(REL/'protocol.json')['at'])
    source=BASE/'source';receipts=load(source/'file_receipts.json')
    assert len(receipts)==168 and len({x['hour'] for x in receipts})==168
    for rec in receipts:
        assert rec['hour'][:10] in DATES and datetime.fromisoformat(rec['at'])>freeze_at
        assert (source/'hours'/rec['hour']).resolve()==(source/f"attempt_{rec['attempt']}"/'hours'/rec['hour']).resolve()
    failed={x['hour'] for x in receipts if not x['complete']}
    co=load(PRIOR/'cohort/cohorts.json');dev={x['market_id'] for x in co['development50']};held={x['market_id'] for x in co['unseen10']}
    assert len(dev)==50 and len(held)==10 and not dev&held
    grid=pq.read_table(BASE/'evaluation/grid_ledger.parquet').to_pylist();pred=pq.read_table(BASE/'evaluation/issued_predictions.parquet').to_pylist()
    assert len(grid)==115920 and {x['date'] for x in grid}==set(DATES)
    assert {x['market_id'] for x in grid}==dev|held
    assert len({(x['market_id'],x['decision_at']) for x in grid})==len(grid)
    lookup={(x['market_id'],x['decision_at']):x for x in grid if x['current_valid']}
    assert len(lookup)==len(pred) and len({(x['market_id'],x['decision_at']) for x in pred})==len(pred)
    for x in grid:
        assert (x['target'] is not None)==x['endpoint_eligible']
        if x['endpoint_eligible']:assert x['target']==int(abs(x['endpoint_midpoint']-x['current_midpoint'])>1e-12)
        if any(datetime.fromtimestamp(x['t']+lag,timezone.utc).strftime('%Y-%m-%dT%H') in failed for lag in [0,1800]):assert x['target'] is None
        if x['strict_eligible']:assert x['endpoint_eligible']
    for p in pred:
        row=lookup[p['market_id'],p['decision_at']];assert p['target']==row['target'] and p['endpoint_eligible']==row['endpoint_eligible']
        assert all(np.isfinite(p[n]) and 1e-6<=p[n]<=1-1e-6 for n in MODELS)
        if p['cohort']=='training_excluded10':assert p['global_rate']==p['market_rate']
    checked=0
    for c,summary in r['cohorts'].items():
        current=[x for x in pred if c=='all' or x['cohort']==c]
        observed=[x for x in current if x['endpoint_eligible']]
        assert summary['issued']==len(current) and summary['observed']==len(observed) and summary['missing_outcomes']==len(current)-len(observed)
        assert summary['scheduled']==sum(c=='all' or x['cohort']==c for x in grid)
        for pop in ['primary','strict','nonoverlap']:
            rows=[x for x in observed if pop=='primary' or (pop=='strict' and x['strict_eligible']) or (pop=='nonoverlap' and datetime.fromisoformat(x['decision_at']).timestamp()%1800==0)]
            y=np.asarray([x['target'] for x in rows]);
            for model in MODELS:
                m=summary[pop][model];p=np.array([x[model] for x in rows]);assert m['n']==len(y) and m['positives']==int(y.sum())
                if not len(y):continue
                values={'log_loss':log_loss(y,p,labels=[0,1]),'brier':brier_score_loss(y,p),'average_precision':average_precision_score(y,p) if y.sum() else None,'roc_auc':roc_auc_score(y,p) if len(set(y))==2 else None}
                for name,v in values.items():assert (v is None and m[name] is None) or (v is not None and abs(v-m[name])<1e-12),(c,pop,model,name)
                if pop=='primary':
                    families=defaultdict(list)
                    mapping={m['market_id']:'|'.join(sorted(e['id'] for e in m['events'])) for m in co['development50']+co['unseen10']}
                    for i,row in enumerate(rows):families[mapping[row['market_id']]].append(i)
                    macro=np.mean([log_loss(y[ix],p[ix],labels=[0,1]) for ix in families.values()]);assert abs(macro-m['family_macro_log_loss'])<1e-12
                checked+=1
        for model,b in summary['missing_outcome_bounds'].items():
            sums=[0.,0.]
            for x in current:
                labels=[x['target']] if x['target'] is not None else [0,1]
                diffs=[]
                for y in labels:
                    p=x['row_hgb7'];q=x[model]
                    diffs.append(-(y*np.log(q)+(1-y)*np.log1p(-q))+(y*np.log(p)+(1-y)*np.log1p(-p)))
                sums[0]+=min(diffs);sums[1]+=max(diffs)
            if current:assert abs(sums[0]/len(current)-b['lower'])<1e-12 and abs(sums[1]/len(current)-b['upper'])<1e-12
    coverage=[]
    for m in co['development50']+co['unseen10']:
        rows=[x for x in pred if x['market_id']==m['market_id']];known=[x for x in rows if x['target'] is not None]
        coverage.append({'market_id':m['market_id'],'question':m['question'],'cohort':'training_excluded10' if m['market_id'] in held else 'development50','issued':len(rows),'observed':len(known),'positives':sum(x['target'] for x in known)})
    qa={'at':now().isoformat(),'passed':True,'hash_entries':entries,'manifests':len(visited),'recomputed_metric_sets':checked,'all_grid_rows':len(grid),'issued_predictions':len(pred),'unknown_outcomes_preserved':sum(x['target'] is None for x in pred),'coverage':coverage}
    write(BASE/'quality_assurance.json',qa)
    return qa


def publish():
    if (BASE/'delivery_manifest.json').exists():raise RuntimeError('Delivery already frozen; create a new version for corrections')
    qa=verify_delivery();r=load(BASE/'evaluation/result.json');source=load(BASE/'source/capture_report.json');schedule=load(BASE/'metadata_schedule_diagnostic.json');groups=load(BASE/'evaluation/groups.json');cs=r['cohorts']
    def fmt(x):return 'NA' if x is None else f'{x:.6f}'
    contrasts={}
    for c in ['development50','training_excluded10','all']:
        m=cs[c]['primary'];a=m['row_hgb7']['log_loss']
        contrasts[c]={n:{'selected_log_loss':a,'baseline_log_loss':m[n]['log_loss'],'relative_reduction_pct':100*(m[n]['log_loss']-a)/m[n]['log_loss'] if m[n]['log_loss'] else None} for n in MODELS if n!='row_hgb7'}
    write(BASE/'comparison_summary.json',contrasts)
    lines=['# EventX seven-day fixed-model replication','',
    'This extends the fixed-model historical test to May 13–19. The current booster, earlier booster and three baselines were frozen before retrieval. There was no model selection, fitting, recalibration or contract replacement. All sixty existing contracts were retained. The ten training-excluded contracts had already appeared in the preceding evaluation; this is temporal replication, not a new-identity test.','',
    '| Cohort | Issued / scheduled | Known outcomes | Contributing contracts | Current HGB LL | Logistic LL | Legacy HGB LL |','|---|---:|---:|---:|---:|---:|---:|']
    for c in ['development50','training_excluded10']:
        z=cs[c];m=z['primary'];lines.append(f"| {c} | {z['issued']:,} / {z['scheduled']:,} | {z['observed']:,} | {z['contributing_contracts']} | {fmt(m['row_hgb7']['log_loss'])} | {fmt(m['activity_logit']['log_loss'])} | {fmt(m['legacy_hgb7']['log_loss'])} |")
    lines+=['','Lower log loss is better. The binary target is whether the recorded midpoint at t+30 minutes differs from the midpoint at t by more than 1e-12. It does not measure direction, economically meaningful movement, a move that reverses by the endpoint, market resolution or trading profit. This is a quote-change activity task, distinct from the original large-log-odds-movement news study; these results do not transfer to that task.','',
    '## Paired comparison','',
    '| Cohort | Baseline | Current-model log-loss reduction |','|---|---|---:|']
    for c in ['development50','training_excluded10']:
        for n,d in contrasts[c].items():lines.append(f"| {c} | {n} | {fmt(d['relative_reduction_pct'])}% |")
    lines+=['','Positive reductions favor the current booster; negative values are losses. The earlier booster remains a fixed comparator and does not become a newly selected winner after inspection. Global and market-rate forecasts are identical on the training-excluded contracts.','',
    '## Forecast coverage and missing outcomes','',
    'Unlike the preceding delivery, this report saves a probability for every decision with a valid current quote before selecting rows with known endpoints. The inference function never reads the label or endpoint-eligibility flag. This is retrospective replay, not evidence that forecasts were issued live in May. Decisions without valid current quotes abstain. No missing outcome is labeled zero.','',
    '| Cohort | Current-valid forecast coverage | Outcome coverage among issued | Missing outcomes |','|---|---:|---:|---:|']
    for c in ['development50','training_excluded10']:
        z=cs[c];lines.append(f"| {c} | {100*z['issued']/z['scheduled']:.2f}% | {100*z['observed']/z['issued'] if z['issued'] else 0:.2f}% | {z['missing_outcomes']:,} |")
    lines+=['','For each unknown outcome, we consider both possible labels and calculate the minimum and maximum baseline-minus-current log-loss difference. Combining these with observed losses bounds the average difference across all current-valid forecasts. These are deterministic missing-label bounds, not confidence intervals; they do not address invalid sources, quotes or unobserved contracts. A range spanning zero means the observed advantage is not guaranteed for all issued forecasts. These bounds assume a comparable binary target exists for each missing endpoint. If a market is closed or no meaningful quote exists, forecasting accuracy there is undefined; assigning hypothetical labels does not establish tradability or target validity.','',
    '| Cohort | Comparator | Lower mean LL improvement | Upper mean LL improvement |','|---|---|---:|---:|']
    for c in ['development50','training_excluded10']:
        for n,b in cs[c]['missing_outcome_bounds'].items():lines.append(f"| {c} | {n} | {fmt(b['lower'])} | {fmt(b['upper'])} |")
    lines+=['','## All metrics and sensitivity','',
    '| Cohort | Model | Rows / positives | Log loss | Brier | AP | AUC | Family-macro LL |','|---|---|---:|---:|---:|---:|---:|---:|']
    for c in ['development50','training_excluded10']:
        for n,m in cs[c]['primary'].items():lines.append(f"| {c} | {n} | {m['n']} / {m['positives']} | {fmt(m['log_loss'])} | {fmt(m['brier'])} | {fmt(m['average_precision'])} | {fmt(m['roc_auc'])} | {fmt(m['family_macro_log_loss'])} |")
    lines+=['','| Cohort | Population | Observations | Current HGB LL | Logistic LL | Legacy HGB LL |','|---|---|---:|---:|---:|---:|']
    for c in ['development50','training_excluded10']:
        for pop in ['strict','nonoverlap']:
            m=cs[c][pop];lines.append(f"| {c} | {pop} | {m['row_hgb7']['n']} | {fmt(m['row_hgb7']['log_loss'])} | {fmt(m['activity_logit']['log_loss'])} | {fmt(m['legacy_hgb7']['log_loss'])} |")
    lines+=['','| Date | Cohort | Issued / observed | Current HGB LL | Logistic LL | Legacy HGB LL |','|---|---|---:|---:|---:|---:|']
    for g in groups:
        if g['field']=='date' and g['cohort']!='all':
            m=g['models'];lines.append(f"| {g['value']} | {g['cohort']} | {g['issued']} / {g['observed']} | {fmt(m['row_hgb7']['log_loss'])} | {fmt(m['activity_logit']['log_loss'])} | {fmt(m['legacy_hgb7']['log_loss'])} |")
    lines+=['','## Source and validity limits','',
    f"Capture completed {source['successful_files']}/{source['files']} hourly files through {source['attempts']} attempts. Failed attempts: {source['failed_attempts']}; recovered hours: {source['recovered_hours']}; final missing hours: {source['missing_hours']}. Recorded completed-range bytes: {source['archive_bytes']:,}; retained YES events: {source['events']:,}. All retry receipts remain preserved. Successful retrieval verifies requested archive chunks, not completeness relative to all exchange events. Mixed pre-holdout chunks decoded {source['excluded_pre_holdout_rows_decoded']:,} excluded-cohort rows before filtering; protected evaluation periods were not read.",'',
    'Current metadata lists six development contracts with scheduled end dates before this test; nine development and two training-excluded contracts end during it. They remain in every scheduled-grid denominator. These dates are diagnostic metadata, not proof of actual historical closure or a posthoc exclusion rule.','',
    'The cohort is a convenience sample selected with current metadata, not a representative market universe or verified historical-status panel. Contracts remain counted after scheduled expiry and when coverage vanishes; retained valid quotes alone do not prove tradability. Adjacent thirty-minute targets overlap, and contracts share calendar conditions. Seven dates and event IDs do not establish independence. No statistical-significance, causal training-breadth, incremental-news or live-promotion claim follows.','',
    f"Verification passed: {qa['hash_entries']:,} hash entries across {qa['manifests']} manifests; {qa['recomputed_metric_sets']} metric sets recomputed from {qa['issued_predictions']:,} unique issued predictions; {qa['unknown_outcomes_preserved']:,} null outcomes preserved. Missing-label bounds were independently recomputed. Preflight matched the prior predictions exactly for all five models and confirmed inference does not read labels.",'',
    '## Artifacts','',
    '- [Frozen protocol](eventx/release/v7/week_replication_20261025/protocol.json)',
    '- [Canonical results](data/v7/week_replication_20261025/evaluation/result.json)',
    '- [Issued predictions, including null outcomes](data/v7/week_replication_20261025/evaluation/issued_predictions.parquet)',
    '- [Full scheduled grid](data/v7/week_replication_20261025/evaluation/grid_ledger.parquet)',
    '- [Day/contract results](data/v7/week_replication_20261025/evaluation/groups.json)',
    '- [Calibration bins](data/v7/week_replication_20261025/evaluation/calibration_bins.json)',
    '- [QA and zero-coverage contracts](data/v7/week_replication_20261025/quality_assurance.json)','']
    report=REPO_ROOT/'EVENTX_SEVEN_DAY_REPLICATION_20261025.md';report.write_text('\n'.join(lines))
    # Keep the report editable until final scientific interpretation and chart inspection.
    print(json.dumps({'report':str(report),'contrasts':contrasts,'qa':{k:v for k,v in qa.items() if k!='coverage'}},indent=2))


if __name__=='__main__':publish()
