"""Validate returned annotations without approving merges or reviewer provenance."""
from collections import Counter
from datetime import datetime
import hashlib
import json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
BASE=ROOT/'data/v5/full_family_review_20260915'
OUT=ROOT/'data/v5/pair_submission_validation_20260915'
def main():
    source=BASE/'pair_responses_reviewed_20260915.jsonl'
    pairs={r['pair_id']:r for r in map(json.loads,(BASE/'pairs.jsonl').read_text().splitlines())}
    rs=list(map(json.loads,source.read_text().splitlines()))
    ids=[r.get('pair_id') for r in rs];issues=[]
    if len(ids)!=len(set(ids)):issues.append('duplicate_pair_ids')
    if set(ids)!=set(pairs):issues.append('missing_or_extra_pair_ids')
    decisions={'must_link','no_direct_link_established','unresolved'}
    relations={'same_event','stage_dependency','nested_outcome','explicit_leg','distinct_event','unknown'}
    for r in rs:
        errs=[]
        if r.get('decision') not in decisions:errs.append('invalid_decision')
        if r.get('relation_type') not in relations:errs.append('invalid_relation')
        for k in ('reviewer','rationale'):
            if not isinstance(r.get(k),str) or not r[k].strip():errs.append('missing_'+k)
        for k in ('evidence_refs','missing_evidence'):
            if not isinstance(r.get(k),list) or any(not isinstance(x,str) for x in r[k]):errs.append('invalid_'+k)
        try:
            if datetime.fromisoformat(r['reviewed_at'].replace('Z','+00:00')).tzinfo is None:errs.append('naive_timestamp')
        except (KeyError,ValueError,TypeError):errs.append('invalid_timestamp')
        if r['decision']=='must_link' and not r.get('evidence_refs'):errs.append('merge_without_evidence_refs')
        if errs:issues.append({'pair_id':r.get('pair_id'),'errors':errs})
    counts=dict(Counter(r['decision'] for r in rs))
    report={'submitted_rows':len(rs),'expected_pairs':len(pairs),'decision_counts':counts,
        'reviewer_ids':dict(Counter(r['reviewer'] for r in rs)),
        'schema_and_coverage_pass':not issues,'issues':issues,
        'provenance_status':'requires clarification: submitted IDs say simulated_model_reviewer',
        'second_independent_review_complete':False,'evidence_content_verified_for_all_pairs':False,
        'graph_changed':False,'current_provisional_components':1280,'outcomes_accessed':False}
    OUT.mkdir(exist_ok=False)
    (OUT/'report.json').write_text(json.dumps(report,indent=2)+'\n')
    if not issues:
        # Blinded to submitted decision, rationale and reviewer. Do not send the
        # report together with this file to the independent second reviewer.
        proposed=[r for r in rs if r['decision']=='must_link']
        packet=[{**pairs[r['pair_id']],'reviewer':None,'decision':None,'relation_type':None,
                 'rationale':None,'evidence_refs':[],'missing_evidence':[],'reviewed_at':None} for r in proposed]
        (OUT/'second_review_proposed_links.jsonl').write_text(''.join(json.dumps(r)+'\n' for r in packet))
        (OUT/'unresolved_submitted.jsonl').write_text(''.join(json.dumps(r)+'\n' for r in rs if r['decision']=='unresolved'))
    sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
    (OUT/'manifest.json').write_text(json.dumps({'inputs':{str(p.relative_to(ROOT)):sha(p) for p in [source,BASE/'pairs.jsonl',BASE/'REVIEW_RULES.md',Path(__file__)]},
        'outputs':{p.name:sha(p) for p in OUT.iterdir()}},indent=2)+'\n')
    print(json.dumps(report,indent=2))
if __name__=='__main__':main()
