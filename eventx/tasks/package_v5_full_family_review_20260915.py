"""Package all provisional families and blank review responses, no outcomes."""
from collections import defaultdict
import hashlib
import json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
BASE=ROOT/'data/v5/embedding_family_reconciliation_20260915_v2'
OUT=ROOT/'data/v5/full_family_review_20260915'
RULES=ROOT/'eventx/release/v5/FAMILY_REVIEW_RULES_20260915.md'
QUEUE=ROOT/'data/v5/topic_coverage_triage_20260914/topic_review_queue.jsonl'
def rows(p):return [json.loads(l) for l in p.read_text().splitlines()]
def main():
    graph=json.loads((BASE/'candidate_components.json').read_text())
    node_family={n:'family-'+hashlib.sha256('|'.join(g).encode()).hexdigest()[:16] for g in graph for n in g}
    contracts=defaultdict(list)
    for r in rows(QUEUE):contracts[node_family[r['candidate_family_id']]].append({k:r.get(k) for k in ('market_id','venue','candidate_family_id','question','yes_sub_title','no_sub_title')})
    external=set(json.loads((BASE/'external_nodes.json').read_text()))
    pairs=[]; related=defaultdict(list)
    for r in rows(BASE/'semantic_review_candidates.jsonl'):
        pid='pair-'+hashlib.sha256((r['left']+'|'+r['right']).encode()).hexdigest()[:16]
        p={k:r[k] for k in ('left','right','left_text','right_text','explicit_year_disagreement')}
        p.update(pair_id=pid,left_family=node_family[r['left']],right_family=node_family[r['right']])
        pairs.append(p)
        for f in (p['left_family'],p['right_family']):related[f].append(pid)
    families=[]
    for g in graph:
        fid=node_family[g[0]]
        families.append({'family_id':fid,'event_ids':g,'contracts':contracts[fid],
            'external_nodes':sorted(set(g)&external),'candidate_pair_ids':sorted(related[fid]),
            'boundary_review_required':True,'certified':False})
    assert len(families)==1280 and sum(len(f['contracts']) for f in families)==4651
    assert len(pairs)==3849 and len({p['pair_id'] for p in pairs})==3849
    OUT.mkdir(exist_ok=False);(OUT/'families').mkdir()
    family_responses=[{'family_id':f['family_id'],'reviewer':None,'decision':None,'rationale':None,
        'evidence_refs':[],'related_pair_ids':[],'missing_evidence':[],'reviewed_at':None} for f in families]
    pair_responses=[{'pair_id':p['pair_id'],'reviewer':None,'decision':None,'relation_type':None,
        'rationale':None,'evidence_refs':[],'missing_evidence':[],'reviewed_at':None} for p in pairs]
    for name,value in [('families.jsonl',families),('pairs.jsonl',pairs),('family_responses.jsonl',family_responses),('pair_responses.jsonl',pair_responses)]:
        (OUT/name).write_text(''.join(json.dumps(r)+'\n' for r in value))
    index=['# All provisional families requiring review','','1,280 families; 4,651 inventory contracts; 3,849 candidate pairs. None certified.',
        '', '[Review rules](REVIEW_RULES.md)', '', 'Largest groups first; IDs are content-addressed to this graph version.', '']
    for f in sorted(families,key=lambda f:(-len(f['event_ids']),f['family_id'])):
        fid=f['family_id'];index.append(f"- [{fid}](families/{fid}.md): {len(f['event_ids'])} events, {len(f['contracts'])} contracts, {len(f['external_nodes'])} external nodes, {len(f['candidate_pair_ids'])} candidate pairs")
        page=[f'# {fid}','','Status: provisional; full boundary review required.','','## Event IDs','']
        page += ['- '+n for n in f['event_ids']]
        page += ['','## Contract context','']
        for r in f['contracts']:
            page += [f"- {r['market_id']} — {r['question']}",f"  - Event: {r['candidate_family_id']}; YES subtitle: {r['yes_sub_title'] or '[missing]'}; NO subtitle: {r['no_sub_title'] or '[missing]'}"]
        page += ['','## External nodes with missing descriptive context','']+['- '+n for n in f['external_nodes']]
        page += ['','## Candidate pairs (look up in ../pairs.jsonl)','']+['- '+p for p in f['candidate_pair_ids']]
        (OUT/'families'/f'{fid}.md').write_text('\n'.join(page)+'\n')
    (OUT/'INDEX.md').write_text('\n'.join(index)+'\n');(OUT/'REVIEW_RULES.md').write_text(RULES.read_text())
    sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
    inputs=[QUEUE,RULES,BASE/'candidate_components.json',BASE/'semantic_review_candidates.jsonl',BASE/'external_nodes.json',Path(__file__)]
    (OUT/'manifest.json').write_text(json.dumps({'inputs':{str(p.relative_to(ROOT)):sha(p) for p in inputs},
        'outputs':{str(p.relative_to(OUT)):sha(p) for p in OUT.rglob('*') if p.is_file()}},indent=2)+'\n')
    print('Packaged 1280 families, 4651 contracts, 3849 pairs; blank response templates validated.')
if __name__=='__main__':main()
