"""Offline exploratory ranking comparison; no reserved inputs or accuracy claims."""
import os
os.environ['HF_HUB_OFFLINE']='1'
os.environ['TRANSFORMERS_OFFLINE']='1'
os.environ['TOKENIZERS_PARALLELISM']='false'
import json
from pathlib import Path
from collections import Counter
import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from eventx.tasks.check_proposition_v03_development import read,digest
from eventx.v6.relation_candidates import constraint
from eventx.tasks.test_proposition_matcher import card,article

def main():
    import torch
    from sentence_transformers import CrossEncoder
    out=Path('data/v6/link_algorithm_comparison_20260919');out.mkdir(exist_ok=False)
    base=Path('data/v6/subject_diagnosis_v02_20260917')
    models=Path('data/v6/local_models_20260916')
    manifest=json.loads((models/'manifest.json').read_text())
    selected=next(m for m in manifest['models'] if m['path'].endswith('/reranker'))
    for name,expected in selected['files'].items():
        assert digest(Path(selected['path'])/name)==expected
    cp=Path('data/v6/contract_link_pilot_20260916/contract_cards.jsonl')
    dp=Path('data/v6/hybrid_development_reviews_20260916/packet.jsonl')
    rows=[r for r in read(base/'cases.jsonl') if r['context_status']=='subject_context_candidate']
    cards={c['contract_id']:c for c in read(cp)}
    articles={r['article']['article_id']:r['article'] for r in read(dp)}
    scenarios=[
        ('US x Iran permanent peace deal by July 1, 2026?', 'US and Iran resumed peace negotiations.', 'US and Iran reported oil prices.', 'US and Canada resumed peace negotiations.'),
        ('Will Example announce acquisition of Other before July 1, 2026?', 'Example announced acquisition talks with Other.', 'Example announced quarterly revenue.', 'Different announced acquisition talks with Other.'),
        ('Will Example have the best AI model in June 2026?', 'Example ranks first on the AI benchmark.', 'Example announced a new office.', 'Different ranks first on the AI benchmark.'),
        ('Will Bitcoin reach $90000 by July 1, 2026?', 'Bitcoin price falls to $60000.', 'Bitcoin miners discuss executive security.', 'Ether price falls to $60000.'),
        ('Will Example be added to the S&P 500 in Q2 2026?', 'Example will not be added to the S&P 500.', 'Example sponsors a golf tournament.', 'Different will be added to the S&P 500.'),
        ('What will Example Corporation say during their next earnings call?', 'Example Corporation discusses earnings.', 'Example Corporation hosts a technology conference.', 'Different Corporation discusses earnings.'),
    ]
    synthetic=[{'scenario':i,'variant':j,'contract':card(q),'article':article(t)}
               for i,(q,*texts) in enumerate(scenarios) for j,t in enumerate(texts)]
    inputs=[cp,dp,base/'cases.jsonl',models/'manifest.json',Path(__file__),Path('eventx/v6/relation_candidates.py')]
    receipt={'scope':'opened development ranking comparison, retrospective only',
             'input_hashes':{str(p):digest(p) for p in inputs},'model':selected['repo'],
             'model_revision':selected['revision'],'methods':['tfidf_cosine','crossencoder','constrained_crossencoder'],
             'acceptance_threshold':None,'synthetic_cases':synthetic,
             'candidate_keys':[(r['article_id'],r['contract_id']) for r in rows]}
    (out/'receipt.json').write_text(json.dumps(receipt,indent=2)+'\n')
    pairs=[(articles[r['article_id']],cards[r['contract_id']]) for r in rows]
    pairs += [(r['article'],r['contract']) for r in synthetic]
    texts=[(c['question']+' '+(c.get('yes_subtitle') or ''),'\n'.join(a.get(k) or '' for k in ('headline','summary'))) for a,c in pairs]
    tf=TfidfVectorizer(ngram_range=(1,2),lowercase=True)
    matrix=tf.fit_transform([t for pair in texts for t in pair])
    lexical=np.asarray(matrix[::2].multiply(matrix[1::2]).sum(axis=1)).ravel()
    torch.set_num_threads(4);torch.manual_seed(20260919)
    model=CrossEncoder(str(models/'reranker'),device='cpu',max_length=384,local_files_only=True,model_kwargs={'attn_implementation':'eager'})
    model.model.bfloat16()
    print('Scoring fixed development and synthetic pairs',flush=True)
    scores=model.predict(texts,batch_size=16,show_progress_bar=False,activation_fn=torch.nn.Identity())
    assert np.isfinite(scores).all()
    outputs=[]
    for i,((a,c),lex,score) in enumerate(zip(pairs,lexical,scores)):
        gate=constraint(a,c)
        outputs.append({'index':i,'question':c['question'],'headline':a['headline'],
                        'tfidf':float(lex),'crossencoder':float(score),'constraint':gate,
                        'constrained_crossencoder':float(score) if gate['status']=='event_channel_candidate' else None})
    dev=outputs[:len(rows)];syn=outputs[len(rows):]
    for r,o in zip(rows,dev):o.update(article_id=r['article_id'],contract_id=r['contract_id'],eligibility=r['eligibility'])
    ranking={}
    for method in ('tfidf','crossencoder','constrained_crossencoder'):
        wins=0
        for i in range(len(scenarios)):
            group=syn[i*3:i*3+3];values=[x[method] if x[method] is not None else -float('inf') for x in group]
            wins+=int(values[0]>max(values[1:]))
        ranking[method]={'synthetic_positive_strictly_above_both_negatives':wins,'scenarios':len(scenarios)}
    report={'development_pairs':len(dev),'development_articles':len({r['article_id'] for r in rows}),
            'constraint_status':dict(Counter(x['constraint']['status'] for x in dev)),
            'constraint_candidate_eligibility':dict(Counter(x['eligibility'] for x in dev if x['constraint']['status']=='event_channel_candidate')),
            'synthetic_ranking':ranking,'predictive_admissions':0,
            'limits':['Synthetic tests are not real-data accuracy.','Neural scores are not calibrated link probabilities.',
                      'Model historical availability uncertified.','Event-channel candidates do not establish event identity or temporal compatibility.']}
    (out/'scores.jsonl').write_text(''.join(json.dumps(x)+'\n' for x in outputs))
    (out/'report.json').write_text(json.dumps(report,indent=2)+'\n')
    (out/'manifest.json').write_text(json.dumps({p.name:digest(p) for p in sorted(out.iterdir())},indent=2)+'\n')
    print(json.dumps(report,indent=2))

if __name__=='__main__':main()
