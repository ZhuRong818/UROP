"""Validate a second submitted review and compute a non-adopted graph preview."""
from collections import Counter
from datetime import datetime
import hashlib
import json
from pathlib import Path
from eventx.tasks.certify_v5_family_graph import components
ROOT=Path(__file__).resolve().parents[2]
BASE=ROOT/'data/v5/pair_submission_validation_20260915'
OUT=ROOT/'data/v5/second_pair_validation_20260915'
def read(p):return [json.loads(l) for l in p.read_text().splitlines()]
def main():
    submission=BASE/'independent_pair_review_B_20260915.jsonl'
    packet=BASE/'second_review_proposed_links.jsonl'
    first_path=ROOT/'data/v5/full_family_review_20260915/pair_responses_reviewed_20260915.jsonl'
    graph_path=ROOT/'data/v5/embedding_family_reconciliation_20260915_v2/candidate_components.json'
    rows=read(submission);expected={r['pair_id']:r for r in read(packet)}
    first={r['pair_id']:r for r in read(first_path)}
    ids=[r['pair_id'] for r in rows];issues=[]
    if len(ids)!=len(set(ids)) or set(ids)!=set(expected):issues.append('ID coverage/uniqueness mismatch')
    for r in rows:
        pid=r['pair_id']
        if pid not in expected:continue
        for k in ('left','right','left_text','right_text','left_family','right_family','explicit_year_disagreement'):
            if r.get(k)!=expected[pid][k]:issues.append({'pair_id':pid,'context_mismatch':k})
        if r.get('decision') not in ('must_link','no_direct_link_established','unresolved'):issues.append({'pair_id':pid,'invalid_decision':True})
        if r.get('relation_type') not in ('same_event','stage_dependency','nested_outcome','explicit_leg','distinct_event','unknown'):issues.append({'pair_id':pid,'invalid_relation':True})
        if not all(r.get(k) for k in ('reviewer','rationale','evidence_refs')):issues.append({'pair_id':pid,'missing_required_field':True})
        try:
            assert datetime.fromisoformat(r['reviewed_at'].replace('Z','+00:00')).tzinfo
        except (KeyError,ValueError,AssertionError):issues.append({'pair_id':pid,'invalid_timestamp':True})
    disagreements=[r for r in rows if r['decision']!=first[r['pair_id']]['decision']]
    old=json.loads(graph_path.read_text());nodes=[n for c in old for n in c]
    prior=[(c[0],n) for c in old for n in c[1:]]
    edges=[(r['left'],r['right']) for r in rows if r['decision']==first[r['pair_id']]['decision']=='must_link']
    preview=components(nodes,prior+edges) if not issues else None
    report={'submitted_rows':len(rows),'expected_rows':len(expected),'validation_pass':not issues,
        'issues':issues,'decision_counts':dict(Counter(r['decision'] for r in rows)),
        'reviewer_ids':dict(Counter(r['reviewer'] for r in rows)),
        'decision_agreements':len(rows)-len(disagreements),'disagreements':len(disagreements),
        'agreement_scope':'Selected first-review positives only; not overall accuracy or recall',
        'provenance':'Second file says independent_model_reviewer_B_blind; human identity and independence from first-review B require clarification',
        'current_components':len(old),'preview_components':len(preview) if preview else None,
        'preview_largest_component':max(map(len,preview)) if preview else None,
        'graph_adopted':False,'final_families_certified':0,'outcomes_accessed':False}
    OUT.mkdir(exist_ok=False)
    for name,value in [('report.json',report),('disagreements.json',disagreements),('NON_ADOPTED_graph_preview.json',preview)]:
        (OUT/name).write_text(json.dumps(value,indent=2)+'\n')
    sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
    (OUT/'manifest.json').write_text(json.dumps({'inputs':{str(p.relative_to(ROOT)):sha(p) for p in [submission,packet,first_path,graph_path,Path(__file__)]},
        'outputs':{p.name:sha(p) for p in OUT.iterdir()}},indent=2)+'\n')
    print(json.dumps(report,indent=2))
if __name__=='__main__':main()
