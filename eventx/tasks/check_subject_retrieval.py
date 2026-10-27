"""Opened-development-only retrieval census with immutable selection receipt."""
import json
from pathlib import Path
from collections import Counter
from eventx.tasks.check_proposition_v03_development import read,digest
from eventx.v6.subject_retrieval import build_registry,retrieve
from eventx.v6.proposition_matcher_v03 import match

def main():
    root=Path('data/v6/subject_retrieval_20260917');root.mkdir(exist_ok=False)
    cp=Path('data/v6/contract_link_pilot_20260916/contract_cards.jsonl')
    dp=Path('data/v6/hybrid_development_reviews_20260916/packet.jsonl')
    sp=Path('data/v6/proposition_v03_development_20260917/selection_receipt.json')
    selection=json.loads(sp.read_text());ids=set(selection['pair_ids'])
    rows=[r for r in read(dp) if r['pair_id'] in ids]
    assert len(rows)==len(ids)
    articles={r['article']['article_id']:r['article'] for r in rows}
    cards={c['contract_id']:c for c in read(cp)}
    registry=build_registry(cards.values())
    inputs=[cp,dp,sp,Path(__file__),Path('eventx/v6/subject_retrieval.py'),Path('eventx/v6/proposition_matcher_v03.py'),Path('eventx/v6/proposition_matcher_v02.py'),Path('eventx/v6/proposition_matcher.py'),Path('eventx/v6/multitype.py'),Path('eventx/v6/measurement_v02.py'),Path('eventx/v6/measurement_extractor.py'),Path('eventx/v6/contracts.py')]
    receipt={'scope':'same 160 opened development articles; all cached contract cards; no reserved article or label inputs',
             'article_ids':sorted(articles),'contract_ids':sorted(cards),'input_hashes':{str(p):digest(p) for p in inputs},
             'selection_rule':'all explicit subject matches; no forced top-one or score cutoff'}
    (root/'selection_receipt.json').write_text(json.dumps(receipt,indent=2)+'\n')
    (root/'subject_registry.json').write_text(json.dumps(registry,indent=2)+'\n')
    old={(r['article']['article_id'],r['contract']['contract_id']) for r in rows}
    output=[];per_article=[]
    for aid,a in sorted(articles.items()):
        hits=retrieve(a,registry)
        per_article.append({'article_id':aid,'headline':a['headline'],'retrieved_contracts':len(hits)})
        for cid,evidence in sorted(hits.items()):
            r=match(a,cards[cid])
            output.append({'article_id':aid,'contract_id':cid,'headline':a['headline'],
                           'question':cards[cid]['question'],'subject_evidence':evidence,
                           'in_previous_packet':(aid,cid) in old,'semantic_status':r['semantic_status'],
                           'semantic_reason':r['semantic_reason'],'eligibility':r['eligibility'],
                           'predictive_admitted':r['predictive_admitted']})
    (root/'candidates.jsonl').write_text(''.join(json.dumps(r)+'\n' for r in output))
    (root/'article_coverage.json').write_text(json.dumps(per_article,indent=2)+'\n')
    report={'articles':len(articles),'contracts':len(cards),'contracts_with_subjects':sum(bool(v) for v in registry.values()),
            'articles_with_candidates':sum(r['retrieved_contracts']>0 for r in per_article),
            'candidate_pairs':len(output),'new_to_previous_packet':sum(not r['in_previous_packet'] for r in output),
            'previous_packet_pairs_retained':sum(r['in_previous_packet'] for r in output),
            'semantic_status':dict(Counter(r['semantic_status'] for r in output)),
            'semantic_reason':dict(Counter(r['semantic_reason'] for r in output)),
            'eligibility':dict(Counter(r['eligibility'] for r in output)),
            'predictive_admitted':sum(r['predictive_admitted'] for r in output),
            'limitations':['Subject mention is not relevance.','No precision or recall estimate.','Contract metadata is not point-in-time certified.','Original candidate packet was not exhaustive ground truth.']}
    (root/'report.json').write_text(json.dumps(report,indent=2)+'\n')
    (root/'manifest.json').write_text(json.dumps({p.name:digest(p) for p in sorted(root.iterdir())},indent=2)+'\n')
    print(json.dumps(report,indent=2))

if __name__=='__main__':main()
