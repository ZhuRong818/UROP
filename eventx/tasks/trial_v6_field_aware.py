"""Fixed opened-data L0/L1/local-reranker trial, not a relevance audit."""
import os
os.environ['HF_HUB_OFFLINE'] = '1'
os.environ['TRANSFORMERS_OFFLINE'] = '1'
os.environ['TOKENIZERS_PARALLELISM'] = 'false'
import json
from pathlib import Path
from collections import Counter, defaultdict
import numpy as np
from eventx.tasks.check_proposition_v03_development import read, digest
from eventx.v6.field_aware import fields, query, hypothesis, top_set
from eventx.v6.clean_speech import clean


def main():
    import torch
    from sentence_transformers import CrossEncoder
    base = Path('data/v6/enriched_rule_comparison_20260921')
    manifest = json.loads((base/'manifest.json').read_text())
    for n, h in manifest['outputs'].items():
        assert digest(base/n) == h, n
    cards = {c['contract_id']: c for c in read(base/'cards.jsonl')}
    ap = Path('data/v6/expanded_coverage_20260919/articles.jsonl')
    articles = {a['article_id']: a for a in read(ap)}
    rows = read(base/'scores.jsonl')
    assert len(rows) == 185 and len({r['article_id'] for r in rows}) == 70
    ff = {k: fields(c) for k, c in cards.items()}
    models = Path('data/v6/local_models_20260916')
    mm = json.loads((models/'manifest.json').read_text())
    selected = next(m for m in mm['models'] if m['path'].endswith('/reranker'))
    for name, h in selected['files'].items():
        assert digest(Path(selected['path'])/name) == h
    out = Path('data/v6/field_aware_trial_20260921')
    out.mkdir(exist_ok=False)
    inputs = [base/'manifest.json', base/'cards.jsonl', base/'scores.jsonl', ap,
              models/'manifest.json', Path(__file__), Path('eventx/v6/field_aware.py'),
              Path('eventx/v6/clean_speech.py'), Path('eventx/tasks/test_field_aware.py')]
    receipt = {'scope': 'opened development only', 'inputs': {str(p): digest(p) for p in inputs},
               'model_revision': selected['revision'], 'model_repo': selected['repo'],
               'limits': ['L2 reranker ablation only; dense retrieval expansion not run.',
                         'No calibrated acceptance threshold or real-data accuracy labels.',
                         'Three typed adapters only; unsupported types abstain.',
                         'No temporal/version certification or predictive admission.']}
    (out/'receipt.json').write_text(json.dumps(receipt, indent=2)+'\n')
    texts = [(query(ff[r['contract_id']]), '\n'.join(clean(articles[r['article_id']])[0].get(k) or ''
              for k in ('headline', 'summary'))) for r in rows]
    torch.set_num_threads(4)
    torch.manual_seed(20260921)
    model = CrossEncoder(str(models/'reranker'), device='cpu', max_length=384,
                         local_files_only=True, model_kwargs={'attn_implementation': 'eager'})
    model.model.bfloat16()
    scores = model.predict(texts, batch_size=16, show_progress_bar=False, activation_fn=torch.nn.Identity())
    assert np.isfinite(scores).all()
    groups = defaultdict(list)
    for r, s in zip(rows, scores):
        h = hypothesis(articles[r['article_id']], ff[r['contract_id']])
        supported = h['status'] != 'abstain'
        r.update(field_hypothesis=h, l0=r['enriched_score'],
                 l1=r['question_score'] if supported else None,
                 l2_reranker=float(s) if supported else None, raw_reranker=float(s))
        groups[r['article_id']].append(r)
    ranks = [{'article_id': aid, **{k: top_set(rr, k) for k in ('l0', 'l1', 'l2_reranker')}}
             for aid, rr in groups.items()]
    hypotheses = [r for r in rows if r['l1'] is not None]
    report = {'pairs': len(rows), 'articles': len(groups), 'cards': len(ff),
              'typed_cards': dict(Counter(f['entity_type_hypothesis'] for f in ff.values())),
              'rule_spans': dict(Counter(s['role'] for f in ff.values() for s in f['rule_spans'])),
              'hypotheses': dict(Counter(r['field_hypothesis']['status'] for r in rows)),
              'abstention_reasons': dict(Counter(r['field_hypothesis']['reason'] for r in rows if r['l1'] is None)),
              'hypothesis_articles': len({r['article_id'] for r in hypotheses}),
              'hypothesis_contracts': len({r['contract_id'] for r in hypotheses}),
              'l0_tied_articles': sum(len(r['l0']) > 1 for r in ranks),
              'l1_l2_different_top_sets': sum(r['l1'] != r['l2_reranker'] for r in ranks),
              'admissions': 0, 'limits': receipt['limits']}
    for name, data in [('cards', list(ff.values())), ('scores', rows), ('ranks', ranks)]:
        (out/(name+'.jsonl')).write_text(''.join(json.dumps(r)+'\n' for r in data))
    (out/'report.json').write_text(json.dumps(report, indent=2)+'\n')
    (out/'manifest.json').write_text(json.dumps({'inputs': receipt['inputs'],
        'outputs': {p.name: digest(p) for p in out.iterdir()}}, indent=2)+'\n')
    print(json.dumps(report, indent=2))


if __name__ == '__main__':
    main()
