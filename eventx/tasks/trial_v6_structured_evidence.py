"""Extraction coverage, never relevance accuracy, on fixed opened inputs."""
import json
from pathlib import Path
from collections import Counter
from eventx.tasks.check_proposition_v03_development import read, digest
from eventx.v6.structured_evidence import extract, compare_contract, validate_spans


def main():
    base = Path('data/v6/evidence_binding_comparison_20260921')
    m = json.loads((base/'manifest.json').read_text())
    for n, h in m['inputs'].items(): assert digest(Path(n)) == h
    for n, h in m['outputs'].items(): assert digest(base/n) == h
    synthetic = []
    for r in read(base/'synthetic_scores.jsonl'):
        a = {'headline': r['text'], 'summary': ''}
        e = extract(a); validate_spans(e, a)
        synthetic.append({**r, 'structured': e, 'contract_diagnostic': compare_contract(e, r['question'])})
    opened = []
    cards = {r['contract_id']: r for r in read(Path('data/v6/document_role_trial_20260921/cards.jsonl'))}
    for a in read(base/'opened_inventory.jsonl'):
        e = extract(a); validate_spans(e, a)
        opened.append({'article_id': a['article_id'], 'structured': e,
            'pairs': [{'contract_id': p['contract_id'], 'v02_status': p['field_hypothesis']['status'],
                       'diagnostic': compare_contract(e, cards[p['contract_id']]['question'])} for p in a['pairs']]})
    def counts(rows):
        cc = [c for r in rows for c in r['structured']['claims']]
        return {'documents': len(rows), 'claims': len(cc),
                'documents_with_predicate': sum(any(c['predicate']['status'] == 'candidate' for c in r['structured']['claims']) for r in rows),
                'known_field_candidates': {k: sum(c[k]['status'] == 'candidate' for c in cc) for k in ('actor', 'speaker', 'object', 'predicate', 'proposition')},
                'epistemic_candidates': dict(Counter(c['epistemic_status']['value'] or 'unknown' for c in cc))}
    report = {'synthetic_by_category': {g: counts([r for r in synthetic if r['category'] == g]) for g in ('actions', 'opinions', 'event_stages')},
              'synthetic_year_diagnostics': dict(Counter(r['contract_diagnostic']['year_mention_relation'] for r in synthetic)),
              'opened': counts(opened), 'opened_year_diagnostics': dict(Counter(p['diagnostic']['year_mention_relation'] for r in opened for p in r['pairs'])),
              'predictive_admissions': 0, 'scope': 'Extraction coverage; neither field correctness nor relevance accuracy measured'}
    out = Path('data/v6/structured_evidence_trial_20260924'); out.mkdir(exist_ok=False)
    for n, rr in [('synthetic', synthetic), ('opened', opened)]:
        (out/(n+'.jsonl')).write_text(''.join(json.dumps(r)+'\n' for r in rr))
    (out/'report.json').write_text(json.dumps(report, indent=2)+'\n')
    inputs = [base/'manifest.json', base/'synthetic_scores.jsonl', base/'opened_inventory.jsonl',
              Path('data/v6/document_role_trial_20260921/cards.jsonl'), Path(__file__),
              Path('eventx/v6/structured_evidence.py'), Path('eventx/tasks/test_structured_evidence.py'), Path('eventx/v6/clean_speech.py')]
    (out/'manifest.json').write_text(json.dumps({'inputs': {str(p): digest(p) for p in inputs},
        'outputs': {p.name: digest(p) for p in out.iterdir()}}, indent=2)+'\n')
    print(json.dumps(report, indent=2))


if __name__ == '__main__': main()
