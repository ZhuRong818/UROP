"""Package the development diagnosis without changing frozen research outputs."""
import json
from pathlib import Path
import re

from eventx.tasks.prepare_v7_event_coverage_pilot_20261012 import OUT, PRIOR
from eventx.tasks.diagnose_v7_signed_evidence_coverage_20261012 import write_json
from eventx.tasks.run_v5_residual_feasibility import REPO_ROOT, read_jsonl, sha256_file

REPORT=REPO_ROOT/'eventx/release/v7/pilot_20261010/EVENT_COVERAGE_AND_MISSED_EVIDENCE_20261012.md'


def main():
    if (OUT/'delivery_manifest.json').exists():
        raise SystemExit('Delivery already complete; preserve it')
    checked={}
    for name in ('preparation_manifest.json','analysis_manifest.json','supplement_manifest.json'):
        for e in json.loads((OUT/name).read_text())['artifacts']:
            checked[e['path']]=e['sha256']
    for e in json.loads((OUT/'design_receipt.json').read_text())['inputs']:
        checked[e['path']]=e['sha256']
    metadata=REPO_ROOT/'data/v7/macro_metadata_20261010'
    meta_manifest=json.loads((metadata/'supplement_manifest.json').read_text())
    for name in ('contract_source_context.jsonl','packet_with_rules.jsonl'):
        checked[str((metadata/name).relative_to(REPO_ROOT))]=meta_manifest['outputs'][name]
    for p,h in checked.items():
        if sha256_file(REPO_ROOT/p)!=h:
            raise RuntimeError(f'Input or artifact changed: {p}')
    context=next(r for r in read_jsonl(metadata/'contract_source_context.jsonl') if r['contract_id']=='kalshi:contract:KXFEDDECISION-26JUL-H0')
    packet=next(r for r in read_jsonl(metadata/'packet_with_rules.jsonl') if r['contract']['contract_id']=='kalshi:contract:KXFEDDECISION-26JUL-H0')
    if context['rules_present'] or packet['rules'] or packet['contract']['yes_subtitle'] is not None:
        raise RuntimeError('Reconsider unresolved wording: cached rules/subtitle unexpectedly supplied')
    write_json(OUT/'cached_rule_check.json',{'contract_id':context['contract_id'],
        'question':context['original_question'],'rules_present':False,'yes_subtitle':None,
        'historical_validity':context['historical_validity'],'active_status':context['active_status'],
        'decision':'Keep selected 0bps Hike pair unresolved; do not silently infer settlement rules.',
        'inputs':[{'path':str((metadata/name).relative_to(REPO_ROOT)),'sha256':meta_manifest['outputs'][name]} for name in ('contract_source_context.jsonl','packet_with_rules.jsonl')]})
    values=json.loads((OUT/'report.json').read_text())
    supplement=json.loads((OUT/'supplement.json').read_text())
    links=[]
    for md in (OUT/'INDEX.md',REPORT):
        for match in re.finditer(r'\[[^\]]+\]\(([^)]+)\)',md.read_text()):
            target=match.group(1).split('#')[0]
            if '://' in target: continue
            p=(md.parent/target).resolve()
            if not p.exists(): raise RuntimeError(f'Broken report link: {target}')
            links.append(str(p.relative_to(REPO_ROOT)))
    checks={'status':'passed','unique_locked_input_artifact_hashes_verified':len(checked),
        'local_markdown_links_verified':len(links),'selected_review_pairs':values['selected_review']['pairs'],
        'miss_sample_articles':values['miss_sample']['articles'],'census_articles':values['policy_census']['articles'],
        'missed_directional_associations':values['assistant_identified_extraction_misses']['associations'],
        'earliest_episode_contract_landmarks':values['episode_contract_landmarks']['pairs'],
        'signed_eligible_landmarks':values['signed_forecast_landmarks']['eligible']['pairs'],
        'observed_context_endpoint_proxies':values['reported_decision_context_landmarks']['usable_observation_proxies']['pairs'],
        'positive_volatility_context_proxies':supplement['primary_positive_volatility_observation_proxies']['pairs'],
        'original_human_blank_forms_preserved':True,'ambiguous_0bp_contract_rule_absence_confirmed':True,
        'forecast_models_fit':0,'software_tests_run':False}
    write_json(OUT/'delivery_checks.json',checks)
    paths=sorted(p for p in OUT.iterdir() if p.is_file())+[REPORT,Path(__file__).resolve()]
    write_json(OUT/'delivery_manifest.json',{'scope':'opened development assistant review and observability diagnosis; no forecast confirmation',
        'inputs':[{'path':p,'sha256':h} for p,h in sorted(checked.items())],
        'artifacts':[{'path':str(p.relative_to(REPO_ROOT)),'sha256':sha256_file(p)} for p in paths]})
    print(json.dumps(checks,indent=2))


if __name__=='__main__':
    main()
