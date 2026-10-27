"""Publish provisional agreed-link graph; never certify independent families."""
import hashlib
import json
from pathlib import Path
from eventx.tasks.certify_v5_family_graph import components, validate_split_certificate
ROOT=Path(__file__).resolve().parents[2]
OUT=ROOT/'data/v5/reviewed_pair_graph_20260915'
def read(p):return [json.loads(l) for l in p.read_text().splitlines()]
def main():
    base=ROOT/'data/v5/embedding_family_reconciliation_20260915_v2'
    firstpath=ROOT/'data/v5/full_family_review_20260915/pair_responses_reviewed_20260915.jsonl'
    secondpath=ROOT/'data/v5/pair_submission_validation_20260915/independent_pair_review_B_20260915.jsonl'
    validation=ROOT/'data/v5/second_pair_validation_20260915'
    # Bind adoption to the exact already-validated inputs, not just their filenames.
    receipt=json.loads((validation/'manifest.json').read_text())
    for name,digest in receipt['inputs'].items():
        assert hashlib.sha256((ROOT/name).read_bytes()).hexdigest()==digest
    assert json.loads((validation/'report.json').read_text())['validation_pass']
    first={r['pair_id']:r for r in read(firstpath)}; second=read(secondpath)
    assert len(second)==154 and all(r['decision']==first[r['pair_id']]['decision']=='must_link' for r in second)
    old=json.loads((base/'candidate_components.json').read_text())
    nodes=[n for c in old for n in c];previous=[(c[0],n) for c in old for n in c[1:]]
    edges=[(r['left'],r['right']) for r in second]
    graph=components(nodes,previous+edges);mapping={n:i for i,c in enumerate(graph) for n in c}
    assert len(graph)==1197 and all(len({mapping[n] for n in c})==1 for c in old)
    assert graph==json.loads((validation/'NON_ADOPTED_graph_preview.json').read_text())
    for a,b in edges:
        bad=dict(mapping);bad[b]=-1
        try:validate_split_certificate(nodes,previous+edges,bad,{n:False for n in nodes})
        except ValueError:pass
        else:raise AssertionError('Known link separated')
    fid=lambda g:'family-'+hashlib.sha256('|'.join(g).encode()).hexdigest()[:16]
    ids={n:fid(c) for c in graph for n in c}
    evidence=[{'pair_id':r['pair_id'],'left':r['left'],'right':r['right'],
        'first_review':first[r['pair_id']],'second_review':r,'adoption_scope':'provisional_split_isolation',
        'reviewers_distinct':'user_attested','blinding_independently_verified':False} for r in second]
    report={'agreed_links_adopted_provisionally':154,'prior_components':len(old),
        'current_components':len(graph),'largest_component_event_nodes':max(map(len,graph)),
        'split_rejection_tests_passed':154,'prior_components_preserved':True,
        'reviewer_distinctness':'confirmed by user 2026-09-15',
        'blinding_independently_verified':False,'final_family_certification':False,
        'unresolved_first_review_pairs':59,'outcomes_accessed':False}
    OUT.mkdir(exist_ok=False)
    for name,obj in [('candidate_components.json',graph),('report.json',report),
        ('old_to_new_family_ids.json',{fid(c):ids[c[0]] for c in old})]:
        (OUT/name).write_text(json.dumps(obj,indent=2)+'\n')
    (OUT/'reviewed_edge_evidence.jsonl').write_text(''.join(json.dumps(r)+'\n' for r in evidence))
    markets=read(base/'market_family_mapping.jsonl')
    (OUT/'market_family_mapping.jsonl').write_text(''.join(json.dumps({'market_id':r['market_id'],
        'event_id':r['event_id'],'family_id':ids[r['event_id']],'family_certified':False})+'\n' for r in markets))
    sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
    inputs=[firstpath,secondpath,validation/'manifest.json',base/'candidate_components.json',base/'market_family_mapping.jsonl',Path(__file__)]
    (OUT/'manifest.json').write_text(json.dumps({'inputs':{str(p.relative_to(ROOT)):sha(p) for p in inputs},
        'outputs':{p.name:sha(p) for p in OUT.iterdir()}},indent=2)+'\n')
    print(json.dumps(report,indent=2))
if __name__=='__main__':main()
