"""Fixed contrastive diagnostic of unchanged binders; never trains or admits links."""
import os
os.environ['HF_HUB_OFFLINE'] = '1'
os.environ['TRANSFORMERS_OFFLINE'] = '1'
os.environ['TOKENIZERS_PARALLELISM'] = 'false'
import json
from pathlib import Path
from collections import defaultdict
import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from eventx.tasks.check_proposition_v03_development import read, digest
from eventx.v6 import field_aware, document_roles

# Assistant-authored context relevance contrasts, NOT independent reference labels.
# Each triple has a relevant context, a same-topic wrong relation, a wrong entity/time.
SCENARIOS = [
    ('actions', 'sale', 'Will Bitcoin hit $150k by June 30, 2026?',
     'Fund sold Bitcoin holdings.', 'Bitcoin software firm sold office furniture.', 'Fund sold Ethereum holdings.'),
    ('actions', 'passive_action', 'Will Ethereum hit $9000 by June 30, 2026?',
     'Ethereum was purchased by a pension fund.', 'Ethereum developers purchased office chairs.', 'Bitcoin was purchased by a pension fund.'),
    ('actions', 'price_subject', 'Will Bitcoin hit $150k by June 30, 2026?',
     'Bitcoin price falls after large exchange sales.', 'Bitcoin software company stock price falls after earnings.', 'Gold price falls after large exchange sales.'),
    ('opinions', 'thesis', 'Will Bitcoin hit $150k by June 30, 2026?',
     'Analyst presents a bullish investment thesis for Bitcoin.', 'Analyst praises Bitcoin conference catering.', 'Analyst presents a bullish investment thesis for gold.'),
    ('opinions', 'forecast', 'Will Ethereum hit $9000 by June 30, 2026?',
     'Economist expects Ethereum to appreciate as demand grows.', 'Economist expects Ethereum developers to relocate offices.', 'Economist expects gold to appreciate as demand grows.'),
    ('opinions', 'valuation', 'Will Bitcoin hit $150k by June 30, 2026?',
     'Strategist argues Bitcoin is overvalued relative to adoption.', 'Strategist argues Bitcoin convention tickets are overpriced.', 'Strategist argues silver is overvalued relative to adoption.'),
    ('event_stages', 'qualifying', 'Will Brazil win the 2026 FIFA World Cup?',
     'Brazil qualified for the 2026 FIFA World Cup knockout stage.', 'Brazil hosts Canada team training for the 2026 FIFA World Cup.', 'Brazil qualified for the 2022 FIFA World Cup knockout stage.'),
    ('event_stages', 'logistics', 'Will Iran win the 2026 FIFA World Cup?',
     'Iran team secures a training base for the 2026 FIFA World Cup.', 'Iran tourism office sponsors the 2026 FIFA World Cup fan festival.', 'Mexico team secures a training base for the 2026 FIFA World Cup.'),
    ('event_stages', 'semifinal', 'Will Argentina reach the Semifinals at the 2026 FIFA World Cup?',
     'Argentina won its quarterfinal at the 2026 FIFA World Cup.', 'Argentina government hosts foreign fans during the 2026 FIFA World Cup.', 'Argentina won its quarterfinal at the 2022 FIFA World Cup.'),
]


def main():
    import torch
    from sentence_transformers import CrossEncoder
    previous = Path('data/v6/document_role_trial_20260921')
    manifest = json.loads((previous/'manifest.json').read_text())
    for n, h in manifest['inputs'].items():
        assert digest(Path(n)) == h
    for n, h in manifest['outputs'].items():
        assert digest(previous/n) == h
    models = Path('data/v6/local_models_20260916')
    mm = json.loads((models/'manifest.json').read_text())
    selected = next(m for m in mm['models'] if m['path'].endswith('/reranker'))
    for n, h in selected['files'].items():
        assert digest(Path(selected['path'])/n) == h
    out = Path('data/v6/evidence_binding_comparison_20260921')
    out.mkdir(exist_ok=False)
    inputs = [Path(__file__), Path('eventx/v6/field_aware.py'), Path('eventx/v6/document_roles.py'),
              Path('eventx/v6/clean_speech.py'), models/'manifest.json', previous/'manifest.json',
              previous/'scores.jsonl', Path('data/v6/expanded_coverage_20260919/articles.jsonl')]
    receipt = {'inputs': {str(p): digest(p) for p in inputs}, 'scenarios': SCENARIOS,
               'reference_type': 'assistant_authored_synthetic_development',
               'model_revision': selected['revision'], 'model_repo': selected['repo'],
               'matcher_changes': False, 'acceptance_threshold': None}
    (out/'receipt.json').write_text(json.dumps(receipt, indent=2)+'\n')
    cases = []
    for category, name, q, *texts in SCENARIOS:
        for variant, text in enumerate(texts):
            c = {'contract_id': name, 'question': q, 'recovered_rule_evidence': []}
            a = {'headline': text, 'summary': ''}
            cases.append({'category': category, 'scenario': name, 'variant': variant,
                          'question': q, 'text': text,
                          'expected_context': variant == 0,
                          'v01': field_aware.hypothesis(a, field_aware.fields(c)),
                          'v02': document_roles.hypothesis(a, document_roles.fields(c))})
    texts = [(r['question'], r['text']) for r in cases]
    tf = TfidfVectorizer(ngram_range=(1,2), stop_words='english')
    mat = tf.fit_transform([t for pair in texts for t in pair])
    lexical = np.asarray(mat[::2].multiply(mat[1::2]).sum(axis=1)).ravel()
    torch.set_num_threads(4); torch.manual_seed(20260921)
    model = CrossEncoder(str(models/'reranker'), device='cpu', max_length=384,
                         local_files_only=True, model_kwargs={'attn_implementation': 'eager'})
    model.model.bfloat16()
    scores = model.predict(texts, batch_size=16, show_progress_bar=False, activation_fn=torch.nn.Identity())
    assert np.isfinite(scores).all()
    for r, lex, score in zip(cases, lexical, scores):
        r.update(tfidf=float(lex), neural=float(score))
    summary = {}
    for category in ('actions', 'opinions', 'event_stages'):
        rr = [r for r in cases if r['category'] == category]
        d = {'scenarios': 3}
        for method in ('v01', 'v02'):
            d[method] = {'positive_hypotheses': sum(r[method]['status'] != 'abstain' for r in rr if r['expected_context']),
                         'negative_hypotheses': sum(r[method]['status'] != 'abstain' for r in rr if not r['expected_context']),
                         'positive_denominator': 3, 'negative_denominator': 6}
        for method in ('tfidf', 'neural'):
            d[method+'_strict_ranking_wins'] = sum(rr[i][method] > max(rr[i+1][method], rr[i+2][method])+1e-12 for i in range(0,9,3))
        summary[category] = d
    # Whole opened pool archived for inspection: no inferred human role labels.
    articles = {a['article_id']: a for a in read(inputs[-1])}
    grouped = defaultdict(list)
    for r in read(previous/'scores.jsonl'):
        grouped[r['article_id']].append(r)
    inventory = [{'article_id': aid, 'headline': articles[aid]['headline'], 'summary': articles[aid].get('summary'),
                  'pairs': rr} for aid, rr in grouped.items()]
    report = {'synthetic': summary, 'synthetic_pairs': len(cases), 'opened_inventory_articles': len(inventory),
              'admissions': 0, 'scope': 'synthetic diagnostic plus complete opened-pool inventory; no real accuracy estimate'}
    for n, rr in [('synthetic_scores', cases), ('opened_inventory', inventory)]:
        (out/(n+'.jsonl')).write_text(''.join(json.dumps(r)+'\n' for r in rr))
    (out/'report.json').write_text(json.dumps(report, indent=2)+'\n')
    (out/'manifest.json').write_text(json.dumps({'inputs': receipt['inputs'],
        'outputs': {p.name: digest(p) for p in out.iterdir()}}, indent=2)+'\n')
    print(json.dumps(report, indent=2))


if __name__ == '__main__':
    main()
