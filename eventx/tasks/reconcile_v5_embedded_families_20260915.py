"""ID-backed family reconciliation plus local LSA embedding review suggestions.

Embeddings never authorize a merge. Metadata-only transductive review aid, not a
predictive feature transform or a frozen evaluation artifact.
"""
from collections import defaultdict
import hashlib
import json
from pathlib import Path
import re
import numpy as np
import sklearn
from sklearn.decomposition import TruncatedSVD
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.preprocessing import normalize
from eventx.tasks.certify_v5_family_graph import components, validate_split_certificate

ROOT=Path(__file__).resolve().parents[2]
OUT=ROOT/'data/v5/embedding_family_reconciliation_20260915_v2'
QUEUE=ROOT/'data/v5/topic_coverage_triage_20260914/topic_review_queue.jsonl'
PRIOR=ROOT/'data/v5/multileg_boundary_review_20260915/candidate_components.json'
LEGS=ROOT/'data/v5/rich_leg_recovery_20260915/leg_references.jsonl'
META=ROOT/'data/v5/rich_leg_recovery_20260915/underlying_metadata.jsonl'
def read(p):return [json.loads(l) for l in p.read_text().splitlines()]
def main():
    rows=read(QUEUE); legs=read(LEGS); meta=read(META)
    old=json.loads(PRIOR.read_text()); original={n for c in old for n in c}
    bymarket={r['market_id']:r for r in rows}
    nodes=set(original); added=set(); references=[]
    for leg in legs:
        parent='kalshi:event:'+leg['parent_event_id']
        child='kalshi:event:'+leg['event_ticker']
        assert parent in original
        assert bymarket[leg['parent_market_id']]['candidate_family_id']==parent
        if leg['market_ticker'] in bymarket:
            assert bymarket[leg['market_ticker']]['candidate_family_id']==child
        nodes.add(child);added.add(tuple(sorted((parent,child))))
        references.append({**leg,'parent_node':parent,'underlying_node':child,
            'evidence_type':'explicit_source_selected_leg','scope':'split_isolation_not_payout_equivalence'})
    previous=[(c[0],n) for c in old for n in c[1:]]
    graph=components(nodes,previous+sorted(added))
    mapping={n:i for i,c in enumerate(graph) for n in c}
    assert all(len({mapping[n] for n in c})==1 for c in old)
    assert components(sorted(nodes,reverse=True),list(reversed(previous+sorted(added))))==graph
    certificate=validate_split_certificate(nodes,previous+sorted(added),mapping,{n:False for n in nodes})
    rejected=0
    for a,b in added:
        bad=dict(mapping);bad[b]=-1
        try:validate_split_certificate(nodes,previous+sorted(added),bad,{n:False for n in nodes})
        except ValueError:rejected+=1
        else:raise AssertionError('Broken dependency accepted')
    documents=defaultdict(set)
    for r in rows:
        # Exclude recovered rules: only preselected descriptive metadata is embedded.
        documents[r['candidate_family_id']].add(' '.join(str(r.get(k) or '') for k in ('question','yes_sub_title','no_sub_title')))
    for r in meta:
        documents['kalshi:event:'+r['event_ticker']].add(' '.join(str(r.get(k) or '') for k in ('title','yes_sub_title','no_sub_title')))
    ids=sorted(n for n in nodes if documents[n]);texts=[' '.join(sorted(documents[n])) for n in ids]
    vectorizer=TfidfVectorizer(ngram_range=(1,2),min_df=1,max_features=30000,sublinear_tf=True)
    x=vectorizer.fit_transform(texts)
    svd=TruncatedSVD(n_components=min(128,x.shape[0]-1,x.shape[1]-1),random_state=73,n_iter=7)
    z=normalize(svd.fit_transform(x))
    scores=z@z.T; proposals={}
    for i,a in enumerate(ids):
        # Top five across DIFFERENT reconciled groups, stable ID tie-breaking.
        eligible=[j for j,b in enumerate(ids) if mapping[a]!=mapping[b]]
        for j in sorted(eligible,key=lambda j:(-float(scores[i,j]),ids[j]))[:5]:
            if scores[i,j]<0.65:continue
            b=ids[j]; pair=tuple(sorted((a,b)))
            ya=set(re.findall(r'\b20\d{2}\b',texts[i]));yb=set(re.findall(r'\b20\d{2}\b',texts[j]))
            proposals[pair]={'left':a,'right':b,'cosine':float(scores[i,j]),
                'left_text':texts[i],'right_text':texts[j],
                'explicit_year_disagreement':bool(ya and yb and ya.isdisjoint(yb)),
                'review_status':'pending','merge_authorized':False,
                'required_checks':['exact event/date','entities and outcomes','resolution semantics','external and multi-leg boundaries']}
    candidates=sorted(proposals.values(),key=lambda r:(-r['cosine'],r['left'],r['right']))
    report={'prior_components':len(old),'original_event_nodes':len(original),
        'external_underlying_event_nodes_added':len(nodes-original),'leg_references':len(references),
        'unique_parent_underlying_edges':len(added),'reconciled_components':len(graph),
        'original_inventory_components':len({mapping[n] for n in original}),
        'largest_component_event_nodes':max(map(len,graph)),
        'split_rejection_tests_passed':rejected,'prior_links_preserved':True,
        'embedded_event_documents':len(ids),'nodes_without_text':len(nodes)-len(ids),
        'embedding_dimensions':z.shape[1],'embedding_method':'TF-IDF word/bigram + 128-dimensional LSA; not neural sentence embeddings',
        'candidate_pairs':len(candidates),'embedding_merges':0,'final_families_certified':0,
        'certificate':certificate,'outcomes_or_holdouts_accessed':False}
    OUT.mkdir(exist_ok=False)
    for name,value in [('report.json',report),('candidate_components.json',graph),
        ('external_nodes.json',sorted(nodes-original)),('config.json',{'seed':73,'top_k':5,'min_cosine':0.65,'sklearn':sklearn.__version__,
        'fit_scope':'all allowlisted descriptive metadata, review-only transductive transform; not prediction features','merge_rule':'explicit IDs only'})]:
        (OUT/name).write_text(json.dumps(value,indent=2)+'\n')
    for name,value in [('leg_edge_evidence.jsonl',references),('semantic_review_candidates.jsonl',candidates),
        ('document_index.jsonl',[{'event_id':n,'text':t} for n,t in zip(ids,texts)]),
        ('market_family_mapping.jsonl',[{'market_id':r['market_id'],'event_id':r['candidate_family_id'],
            'provisional_component':mapping[r['candidate_family_id']],'family_certified':False} for r in rows])]:
        (OUT/name).write_text(''.join(json.dumps(r)+'\n' for r in value))
    np.save(OUT/'embeddings.npy',z)
    np.savez_compressed(OUT/'lsa_transform.npz',components=svd.components_,idf=vectorizer.idf_)
    (OUT/'vocabulary.json').write_text(json.dumps({k:int(v) for k,v in vectorizer.vocabulary_.items()},sort_keys=True)+'\n')
    sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
    (OUT/'manifest.json').write_text(json.dumps({'inputs':{str(p.relative_to(ROOT)):sha(p) for p in [QUEUE,PRIOR,LEGS,META,Path(__file__)]},
        'outputs':{p.name:sha(p) for p in OUT.iterdir()}},indent=2)+'\n')
    print(json.dumps(report,indent=2))
if __name__=='__main__':main()
