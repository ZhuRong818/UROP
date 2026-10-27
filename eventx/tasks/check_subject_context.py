"""Preserves first-pass retrieval and publishes separate context diagnostics."""
import json
from pathlib import Path
from collections import Counter
from eventx.tasks.check_proposition_v03_development import read,digest
from eventx.v6.subject_context import context_gate

def main():
    root=Path('data/v6/subject_context_20260917');root.mkdir(exist_ok=False)
    source=Path('data/v6/subject_retrieval_20260917/candidates.jsonl')
    dp=Path('data/v6/hybrid_development_reviews_20260916/packet.jsonl')
    cp=Path('data/v6/contract_link_pilot_20260916/contract_cards.jsonl')
    articles={r['article']['article_id']:r['article'] for r in read(dp)}
    cards={c['contract_id']:c for c in read(cp)}
    receipt={'scope':'development filter designed after inspecting first-pass retrieval; exploratory',
             'hashes':{str(p):digest(p) for p in [source,dp,cp,Path(__file__),Path('eventx/v6/subject_context.py')]}}
    (root/'receipt.json').write_text(json.dumps(receipt,indent=2)+'\n')
    rows=read(source)
    for r in rows:r['context_status']=context_gate(articles[r['article_id']],cards[r['contract_id']],r['subject_evidence'])
    kept=[r for r in rows if r['context_status']=='subject_context_candidate']
    report={'input_pairs':len(rows),'context_status':dict(Counter(r['context_status'] for r in rows)),
            'retained_pairs':len(kept),'retained_articles':len({r['article_id'] for r in kept}),
            'new_to_previous_packet':sum(not r['in_previous_packet'] for r in kept),
            'semantic_status':dict(Counter(r['semantic_status'] for r in kept)),
            'eligibility':dict(Counter(r['eligibility'] for r in kept)),
            'predictive_admitted':0,'claim':'Unvalidated retrieval coverage, not relevance accuracy or recall.'}
    (root/'cases.jsonl').write_text(''.join(json.dumps(r)+'\n' for r in rows))
    (root/'report.json').write_text(json.dumps(report,indent=2)+'\n')
    (root/'manifest.json').write_text(json.dumps({p.name:digest(p) for p in sorted(root.iterdir())},indent=2)+'\n')
    print(json.dumps(report,indent=2))

if __name__=='__main__':main()
