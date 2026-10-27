"""Retrospective rule-text retrieval ablation; scores never admit links."""
import json
from pathlib import Path
from collections import defaultdict
from sklearn.feature_extraction.text import TfidfVectorizer
from eventx.tasks.check_proposition_v03_development import read,digest
from eventx.v6.clean_speech import clean

def main():
    base=Path('data/v6/screened_relations_20260921')
    m=json.loads((base/'manifest.json').read_text())
    for p,h in m['inputs'].items():assert digest(Path(p))==h
    for n,h in m['outputs'].items():assert digest(base/n)==h
    cases=[r for r in read(base/'cases.jsonl') if r['snapshot_precedes_article']]
    cards={c['contract_id']:c for c in read(Path('data/v6/contract_link_pilot_20260916/contract_cards.jsonl'))}
    articles={a['article_id']:a for a in read(Path('data/v6/expanded_coverage_20260919/articles.jsonl'))}
    wanted={cid for g in read(Path('data/v6/fetch_priority_v2_20260921/fetch_queue.jsonl')) for cid in g['contract_ids']}
    enriched={};inputs={}
    for name in ['v6_targeted_metadata_20260921','v6_queue_kalshi_00_20260921','v6_queue_kalshi_01_20260921','v6_queue_polymarket_00_20260921']:
        rp=Path('data/v5/provenance_recovery_20260908')/(name+'.json');receipt=json.loads(rp.read_text());p=Path(receipt['data_path'])
        assert receipt['status']=='complete' and digest(p)==receipt['data_sha256'];inputs[str(p)]=digest(p)
        for line,r in enumerate(read(p),1):
            cid=('kalshi:contract:'+r['ticker']) if 'ticker' in r else 'polymarket:contract:'+r['condition_id']
            if cid not in wanted:continue
            evidence=[{'text':r[k],'field':k,'source_file':str(p),'source_line':line,'available_at':r['ingest_ts']} for k in ('rules_primary','rules_secondary','description') if r.get(k)]
            enriched[cid]={**cards[cid],'schema_version':'v6-enriched-review-card-0.1','recovered_rule_evidence':evidence,'training_admissible':False,'pit_certificate':None}
    assert len(enriched)==134
    ids=sorted(enriched)
    short=['\n'.join(filter(None,[enriched[k]['question'],enriched[k].get('yes_subtitle')])) for k in ids]
    full=[s+'\n'+'\n'.join(e['text'] for e in enriched[k]['recovered_rule_evidence']) for k,s in zip(ids,short)]
    # Shared vocabulary/IDF keeps representation comparison on the same scale.
    vectorizer=TfidfVectorizer(stop_words='english',ngram_range=(1,2))
    vectorizer.fit(short+full)
    matrices=[vectorizer.transform(short),vectorizer.transform(full)];index={k:i for i,k in enumerate(ids)}
    rows=[];by_article=defaultdict(list)
    for r in cases:
        a=clean(articles[r['article_id']])[0];x=vectorizer.transform(['\n'.join(a.get(k) or '' for k in ('headline','summary'))])
        j=index[r['contract_id']]
        scores=[float(x.multiply(mat[j]).sum()) for mat in matrices]
        row={**r,'question_score':scores[0],'enriched_score':scores[1],'admitted':False}
        rows.append(row);by_article[r['article_id']].append(row)
    changes=[]
    for aid,rr in by_article.items():
        picks=[sorted(rr,key=lambda r:(-r[field],r['contract_id']))[0]['contract_id'] for field in ('question_score','enriched_score')]
        changes.append({'article_id':aid,'candidates':len(rr),'question_top':picks[0],'enriched_top':picks[1],'changed':picks[0]!=picks[1]})
    report={'enriched_cards':len(enriched),'cards_with_recovered_rules':sum(bool(c['recovered_rule_evidence']) for c in enriched.values()),'pairs':len(rows),'articles':len(by_article),'articles_with_multiple_candidates':sum(len(r)>1 for r in by_article.values()),'top_choice_changes':sum(r['changed'] for r in changes),'admissions':0,'scope':'Development TF-IDF ranking ablation only; no accuracy labels or relation acceptance. Shared IDF uses all134 retrospective cards, not PIT deployment.'}
    out=Path('data/v6/enriched_rule_comparison_20260921');out.mkdir(exist_ok=False)
    for name,rr in [('cards',list(enriched.values())),('scores',rows),('rank_changes',changes)]:
        (out/(name+'.jsonl')).write_text(''.join(json.dumps(r)+'\n' for r in rr))
    (out/'report.json').write_text(json.dumps(report,indent=2)+'\n')
    inputs[str(base/'manifest.json')]=digest(base/'manifest.json');inputs[str(Path(__file__))]=digest(Path(__file__))
    (out/'manifest.json').write_text(json.dumps({'inputs':inputs,'outputs':{p.name:digest(p) for p in out.iterdir()}},indent=2)+'\n')
    print(json.dumps(report,indent=2))

if __name__=='__main__':main()
