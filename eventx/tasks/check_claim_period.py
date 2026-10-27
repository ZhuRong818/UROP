import json
from pathlib import Path
from collections import Counter
from eventx.tasks.check_proposition_v03_development import read,digest
from eventx.v6.claim_period import assess

def main():
    root=Path('data/v6/claim_period_20260919');root.mkdir(exist_ok=False)
    prior=Path('data/v6/link_algorithm_comparison_20260919')
    for name,h in json.loads((prior/'manifest.json').read_text()).items():assert digest(prior/name)==h
    cp=Path('data/v6/contract_link_pilot_20260916/contract_cards.jsonl')
    dp=Path('data/v6/hybrid_development_reviews_20260916/packet.jsonl')
    cards={c['contract_id']:c for c in read(cp)}
    articles={r['article']['article_id']:r['article'] for r in read(dp)}
    rows=[r for r in read(prior/'scores.jsonl') if 'article_id' in r]
    inputs=[cp,dp,prior/'scores.jsonl',Path(__file__),Path('eventx/v6/claim_period.py')]
    (root/'receipt.json').write_text(json.dumps({'hashes':{str(p):digest(p) for p in inputs},'scope':'same 180 opened-development pairs; cached scores unchanged'},indent=2)+'\n')
    for r in rows:r['claim_period']=assess(articles[r['article_id']],cards[r['contract_id']],r['constraint'])
    candidates=[r for r in rows if r['constraint']['status']=='event_channel_candidate']
    report={'pairs':len(rows),'previous_candidates':len(candidates),
            'candidate_roles':dict(Counter(r['claim_period']['role'] for r in candidates)),
            'candidate_periods':dict(Counter(r['claim_period']['period']['status'] for r in candidates)),
            'joint':dict(Counter(r['claim_period']['role']+' / '+r['claim_period']['period']['status'] for r in candidates)),
            'predictive_admissions':0,'settlement_verified':0,
            'limitations':['Heuristic claim roles, not independent labels.','Question dates screen expiration, not certify historical validity.','No new scoring or threshold tuning.']}
    (root/'cases.jsonl').write_text(''.join(json.dumps(r)+'\n' for r in rows))
    (root/'report.json').write_text(json.dumps(report,indent=2)+'\n')
    (root/'manifest.json').write_text(json.dumps({p.name:digest(p) for p in sorted(root.iterdir())},indent=2)+'\n')
    print(json.dumps(report,indent=2))

if __name__=='__main__':main()
