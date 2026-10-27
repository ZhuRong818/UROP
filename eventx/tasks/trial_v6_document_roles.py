"""Replay unchanged scores with new document-role hypotheses on opened pairs."""
import json
from pathlib import Path
from collections import Counter
from eventx.tasks.check_proposition_v03_development import read, digest
from eventx.v6.document_roles import fields, hypothesis
from eventx.v6.field_aware import query


def main():
    base = Path('data/v6/field_aware_trial_20260921')
    m = json.loads((base/'manifest.json').read_text())
    for n, h in m['outputs'].items():
        assert digest(base/n) == h
    for n, h in m['inputs'].items():
        assert digest(Path(n)) == h
    cp = Path('data/v6/enriched_rule_comparison_20260921/cards.jsonl')
    ap = Path('data/v6/expanded_coverage_20260919/articles.jsonl')
    cards = {c['contract_id']: c for c in read(cp)}
    old = {c['contract_id']: c for c in read(base/'cards.jsonl')}
    articles = {a['article_id']: a for a in read(ap)}
    ff = {k: fields(c) for k, c in cards.items()}
    assert all(query(ff[k]) == query(old[k]) for k in ff)
    rows = read(base/'scores.jsonl'); changes = []
    for r in rows:
        previous = r['field_hypothesis']
        h = hypothesis(articles[r['article_id']], ff[r['contract_id']])
        r['previous_hypothesis'] = previous
        r['field_hypothesis'] = h
        supported = h['status'] != 'abstain'
        r['l1'] = r['question_score'] if supported else None
        r['l2_reranker'] = r['raw_reranker'] if supported else None
        if previous['status'] != h['status']:
            changes.append({'article_id': r['article_id'], 'contract_id': r['contract_id'],
                            'question': cards[r['contract_id']]['question'],
                            'before': previous['status'], 'after': h['status'], 'evidence': h['evidence']})
    kept = [r for r in rows if r['l1'] is not None]
    report = {'pairs': len(rows), 'articles': len({r['article_id'] for r in rows}),
              'statuses': dict(Counter(r['field_hypothesis']['status'] for r in rows)),
              'hypothesis_articles': len({r['article_id'] for r in kept}),
              'hypothesis_contracts': len({r['contract_id'] for r in kept}),
              'added': sum(r['before'] == 'abstain' for r in changes),
              'removed': sum(r['after'] == 'abstain' for r in changes),
              'admissions': 0, 'scores_reused': True,
              'scope': 'development-only role comparison; no real-data accuracy or source certification'}
    out = Path('data/v6/document_role_trial_20260921'); out.mkdir(exist_ok=False)
    for n, data in [('scores', rows), ('changes', changes), ('cards', list(ff.values()))]:
        (out/(n+'.jsonl')).write_text(''.join(json.dumps(r)+'\n' for r in data))
    (out/'report.json').write_text(json.dumps(report, indent=2)+'\n')
    inputs = [base/'manifest.json', cp, ap, Path(__file__), Path('eventx/v6/document_roles.py'), Path('eventx/tasks/test_document_roles.py')]
    (out/'manifest.json').write_text(json.dumps({'inputs': {str(p): digest(p) for p in inputs},
        'outputs': {p.name: digest(p) for p in out.iterdir()}}, indent=2)+'\n')
    print(json.dumps(report, indent=2))


if __name__ == '__main__':
    main()
