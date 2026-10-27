"""Fixed development diagnosis and subject/context revision; no gold inputs."""
import json
from pathlib import Path
from collections import Counter
from eventx.tasks.check_proposition_v03_development import read,digest
from eventx.v6.subject_retrieval import retrieve
from eventx.v6.subject_retrieval_v02 import subjects,context_gate,missing_class
from eventx.v6.proposition_matcher_v03 import match


def main():
    out=Path('data/v6/subject_diagnosis_v02_20260917');out.mkdir(exist_ok=False)
    cp=Path('data/v6/contract_link_pilot_20260916/contract_cards.jsonl')
    dp=Path('data/v6/hybrid_development_reviews_20260916/packet.jsonl')
    prior=Path('data/v6/subject_context_20260917/cases.jsonl')
    receipt_path=Path('data/v6/subject_retrieval_20260917/selection_receipt.json')
    old_registry_path=Path('data/v6/subject_retrieval_20260917/subject_registry.json')
    ids=set(json.loads(receipt_path.read_text())['article_ids'])
    articles={r['article']['article_id']:r['article'] for r in read(dp) if r['article']['article_id'] in ids}
    assert set(articles)==ids and len(ids)==160
    cards={c['contract_id']:c for c in read(cp)}
    old_registry=json.loads(old_registry_path.read_text())
    inputs=[cp,dp,prior,receipt_path,old_registry_path,Path(__file__)]
    inputs+=sorted(Path('eventx/v6').glob('*.py'))
    (out/'receipt.json').write_text(json.dumps({'scope':'opened fixed 160 articles; no outcome/reviewer inputs',
        'article_ids':sorted(ids),'hashes':{str(p):digest(p) for p in inputs}},indent=2)+'\n')
    old=[r for r in read(prior) if r['context_status']=='subject_context_candidate']
    failure_counts=dict(Counter(r['semantic_reason'] for r in old))
    inventory=[{'contract_id':cid,'question':c['question'],'failure_class':missing_class(c)}
               for cid,c in sorted(cards.items()) if not old_registry[cid]]
    (out/'uncovered_inventory.jsonl').write_text(''.join(json.dumps(r)+'\n' for r in inventory))
    registry={cid:subjects(c) for cid,c in cards.items()}
    (out/'registry.json').write_text(json.dumps(registry,indent=2)+'\n')
    rows=[]
    for aid,a in sorted(articles.items()):
        for cid,evidence in sorted(retrieve(a,registry).items()):
            c=cards[cid];gate=context_gate(a,c,evidence);r=match(a,c)
            rows.append({'article_id':aid,'contract_id':cid,'headline':a['headline'],'question':c['question'],
                         'evidence':evidence,'context_status':gate,'semantic_status':r['semantic_status'],
                         'semantic_reason':r['semantic_reason'],'eligibility':r['eligibility'],
                         'eligibility_reasons':r['eligibility_reasons'],'predictive_admitted':False})
    kept=[r for r in rows if r['context_status']=='subject_context_candidate']
    oldkeys={(r['article_id'],r['contract_id']) for r in old}
    newkeys={(r['article_id'],r['contract_id']) for r in kept}
    report={'previous_155_failure_reasons':failure_counts,'previous_pairs_reaching_period_check':0,
        'date_decision':'No blanket date relaxation: none of these 155 reached period checks. Exact period rules need separate future adapter validation.',
        'uncovered_2909_groups':dict(Counter(r['failure_class'] for r in inventory)),
        'contracts_with_subjects':sum(bool(v) for v in registry.values()),
        'newly_covered_contracts':sum(bool(registry[cid]) and not old_registry[cid] for cid in cards),
        'remaining_uncovered':sum(not v for v in registry.values()),
        'retrieved_pairs':len(rows),'retained_pairs':len(kept),'retained_articles':len({r['article_id'] for r in kept}),
        'added_retained_pairs':len(newkeys-oldkeys),'removed_retained_pairs':len(oldkeys-newkeys),
        'semantic_status':dict(Counter(r['semantic_status'] for r in kept)),
        'semantic_reason':dict(Counter(r['semantic_reason'] for r in kept)),
        'eligibility':dict(Counter(r['eligibility'] for r in kept)),
        'predictive_admitted':0,'limitations':['Development diagnostics are not human gold.','No precision/recall or predictive claims.','No new review packet.']}
    (out/'cases.jsonl').write_text(''.join(json.dumps(r)+'\n' for r in rows))
    (out/'report.json').write_text(json.dumps(report,indent=2)+'\n')
    (out/'manifest.json').write_text(json.dumps({p.name:digest(p) for p in sorted(out.iterdir())},indent=2)+'\n')
    print(json.dumps(report,indent=2))

if __name__=='__main__':main()
