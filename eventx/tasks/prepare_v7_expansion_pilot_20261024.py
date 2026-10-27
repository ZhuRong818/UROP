"""Enroll two new source-feasibility candidates using rules, without prices."""
from collections import Counter
from datetime import timedelta
import hashlib
import json
from pathlib import Path
import plistlib
from eventx.tasks.discover_v7_direct_pilot_20261022 import REPO_ROOT,PROTECTED,now,sha,write,verify_originals
from eventx.tasks.prepare_v7_direct_pilot_20261022 import classify,convert

DISCOVERY=REPO_ROOT/'data/v7/forecast_expansion_20261024_v02/6054fd69ba8e4d28b53ebbc7c8acef18'
BASE=REPO_ROOT/'data/v7/expansion_source_pilot_20261024'
RELEASE=REPO_ROOT/'eventx/release/v7/expansion_source_pilot_20261024'

def main():
    verify_originals()
    for p,h in json.loads((DISCOVERY/'manifest.json').read_text())['files'].items():
        if sha(REPO_ROOT/p)!=h:raise RuntimeError('Discovery hash mismatch')
    if json.loads((DISCOVERY/'report.json').read_text())['cap_reached']:raise RuntimeError('Incomplete universe')
    rows=[json.loads(l) for l in (DISCOVERY/'metadata.jsonl').read_text().splitlines()]
    protected=set(json.loads(PROTECTED.read_text()));decisions=[];sample=[]
    for r in rows:
        q,d=r['question'],r.get('description') or ''
        family=classify(r);reason='outside_prespecified_US_longer_lived_rule_candidates'
        if family: reason='existing14_candidate_family_retained_in_original_cohort'
        elif q=='Negative GDP growth in 2026?' and all(s in d for s in ['full year 2026','Q4 2026','Bureau of Economic Analysis']):
            family='US_GDP_NEGATIVE_FULL_YEAR_2026';reason='new_source_candidate_with_measure_definition_review_pending'
        elif q=='US recession by end of 2026?' and all(s in d for s in ['two consecutive quarters','National Bureau of Economic Research','Q4 2026']):
            family='US_RECESSION_DUAL_RULE_2026';reason='new_source_candidate_with_early_terminal_risk'
        elif 'Resolution of this market will take place upon release' in d or 'resolve as soon as the relevant data is issued' in d:
            reason='own_release_terminal; other_release_context_branch_not_enrolled'
        if r['condition_id'] in protected:raise RuntimeError('Protected scope')
        if reason.startswith('new_source_candidate'):
            item=convert(r,'prospective_macro_candidate',family)
            item['selection_reason']=reason
            item['review_provenance']='single assistant rule review; not independent human gold'
            item['rule_caveat']=('Full-year and annualized wording requires exact BEA table binding; no signed evidence admitted.' if 'NEGATIVE' in family else 'Either consecutive negative quarters or NBER announcement can terminate early; verify both branches before eligibility.')
            sample.append(item)
        decisions.append({'market_id':r['condition_id'],'question':q,'family':family,'decision':reason,'rules_sha256':hashlib.sha256(d.encode()).hexdigest()})
    if len(sample)!=2:raise RuntimeError('Unexpected candidate count; inspect before enrollment')
    RELEASE.mkdir(parents=True,exist_ok=False);BASE.mkdir(parents=True,exist_ok=True)
    for name,rs in [('sample',sample),('metadata_decisions',decisions)]:
        (RELEASE/(name+'.jsonl')).write_text(''.join(json.dumps(r,sort_keys=True)+'\n' for r in rs))
    parent=REPO_ROOT/'eventx/release/v7/direct_source_pilot_20261022_v03'
    spec=json.loads((parent/'spec.json').read_text());at=now()
    spec.update(version='expansion_source_20261024',created_at=at.isoformat(),
        scope='Two new metadata-selected candidates; six-hour source/activity feasibility only; not event activation or scoring',
        selection='Negative annual US GDP and dual-rule US recession; exact questions and rule spans, no prices or liquidity ranking',
        live_duration_seconds=21600,rehearsal_stop_at=(at+timedelta(hours=7)).isoformat(),
        sample_counts={'prospective_macro_candidate':2},candidate_family_counts=dict(Counter(r['family'] for r in sample)),
        metadata_every_cycle=True,process_gap_log_seconds=120,
        observation_policy='eventx/release/v7/forecast_path_20261023/policy.json',
        dependencies='Freshness and endpoint policy frozen for new branch; source convention, exact rule binding, continuity and release evidence remain gated',
        control_rule='No controls enrolled in this two-market expansion run; earlier controls remain diagnostic only',
        cold_start='Six-hour historical overlap is late-acquired data; future as-of warmup must accumulate prospectively',
        event_activation_enabled=False)
    write(RELEASE/'spec.json',spec)
    events=json.loads((parent/'episode_reservation.json').read_text())
    links=[]
    for e in events['episodes']:
        for r in sample:
            gdp=any('GDP' in s for s in e['components'])
            links.append({'episode_id':e['episode_id'],'market_id':r['market_id'],
                'role':'component_evidence_pending_predicate_binding' if gdp else 'context_hypothesis_only',
                'actual_release_review':'pending','direction':None,'novelty':'unknown',
                'terminal_risk':r['rule_caveat'],'predictive_admitted':False})
    (RELEASE/'evidence_link_plan.jsonl').write_text(''.join(json.dumps(r,sort_keys=True)+'\n' for r in links))
    write(RELEASE/'episode_reservation.json',events)
    report={'at':at.isoformat(),'metadata_rows':len(rows),'decision_counts':dict(Counter(r['decision'] for r in decisions)),
        'new_source_candidates':len(sample),'prices_or_outcomes_used_for_selection':False,'v4_overlap':0,
        'predictive_admissions':0,'existing_cohort_changed':False,'pilot_hours':6}
    write(RELEASE/'enrollment_report.json',report)
    label='com.eventx.expansion-source-pilot.20261024';live=BASE/'live';live.mkdir(exist_ok=True)
    plist={'Label':label,'ProgramArguments':['/usr/bin/caffeinate','-i','-s',str(REPO_ROOT/'.venv/bin/python'),'-m','eventx.tasks.collect_v7_expansion_pilot_20261024'],
        'WorkingDirectory':str(REPO_ROOT),'RunAtLoad':True,'KeepAlive':{'SuccessfulExit':False},'ThrottleInterval':60,
        'EnvironmentVariables':{'PYTHONUNBUFFERED':'1'},'StandardOutPath':str(live/'stdout.log'),'StandardErrorPath':str(live/'stderr.log')}
    (RELEASE/(label+'.plist')).write_bytes(plistlib.dumps(plist))
    files=list(RELEASE.iterdir())+[DISCOVERY/'manifest.json',PROTECTED,Path(__file__).resolve(),
        REPO_ROOT/'eventx/release/v7/forecast_path_20261023/manifest.json']
    for n in ['collect_v7_expansion_pilot_20261024.py','launch_v7_expansion_pilot_20261024.py','collect_v7_direct_pilot_20261022_v03.py','audit_v7_direct_pilot_20261022_v03.py']:
        files.append(REPO_ROOT/'eventx/tasks'/n)
    files.append(REPO_ROOT/'eventx/v7/source_request_scheduler_v02.py')
    write(RELEASE/'implementation_manifest.json',{'locked_files':{str(p.relative_to(REPO_ROOT)):sha(p) for p in files}})
    print(json.dumps(report,indent=2))

if __name__=='__main__':main()
