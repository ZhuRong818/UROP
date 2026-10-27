"""Opened-development comparison; immutable predecessor backends and artifacts."""
import json
from collections import Counter, defaultdict
from pathlib import Path
from datetime import datetime, timezone
import spacy
import en_core_web_sm
from eventx.tasks.score_v6_evidence_fields import score, digest
from eventx.v6.compositional_evidence import extract
from eventx.v6.structured_evidence import validate_spans


def read(p):
    return [json.loads(s) for s in p.read_text().splitlines()]


def main():
    prior = Path('data/v6/evidence_field_scorecard_20260924')
    dep = Path('data/v6/dependency_evidence_trial_20260924')
    base = Path('data/v6/evidence_binding_comparison_20260921')
    for root in (prior, dep, base):
        m = json.loads((root/'manifest.json').read_text())
        for p, h in m['inputs'].items():
            assert digest(Path(p)) == h, p
        for p, h in m['outputs'].items():
            assert digest(root/p) == h, p
    provenance = json.loads((dep/'provenance.json').read_text())
    for p, h in provenance['model_hashes'].items():
        assert digest(Path(en_core_web_sm.__file__).parent/p) == h
    assert spacy.__version__ == '3.8.7'
    out = Path('data/v6/compositional_evidence_trial_20260924')
    out.mkdir(exist_ok=False)
    inputs = [Path(__file__), Path('eventx/v6/compositional_evidence.py'),
              Path('eventx/tasks/test_compositional_evidence.py'),
              prior/'manifest.json', dep/'manifest.json', base/'manifest.json']
    hashes = {str(p): digest(p) for p in inputs}
    (out/'receipt.json').write_text(json.dumps({'created_at': datetime.now(timezone.utc).isoformat(),
        'inputs': hashes, 'scope': 'fixed 12-case scorecard and same 70 opened articles; no independent accuracy'}, indent=2)+'\n')
    nlp = en_core_web_sm.load()
    assert nlp.meta['version'] == '3.8.0'
    rows, scores, changes = [], [], []
    counts = defaultdict(Counter)
    cases = json.loads((prior/'spec.json').read_text())['cases']
    for case in cases:
        a = {'headline': case[1], 'summary': ''}
        e = extract(a, nlp)
        validate_spans(e, a)
        rows.append({'kind': 'synthetic', 'case': case[0], 'extraction': e})
        for r in score(case, e):
            scores.append(r)
            counts[r['field']][r['status']] += 1
    old = {str(r['article_id']): r['structured'] for r in read(dep/'opened.jsonl')}
    expanded, chains, predicates = 0, 0, 0
    articles_changed = set()
    for a in read(base/'opened_inventory.jsonl'):
        e = extract(a, nlp)
        validate_spans(e, a)
        assert len(e['claims']) == len(old[str(a['article_id'])]['claims'])
        for c in e['claims']:
            assert c['entity_identity'] == c['episode_identity'] == c['assertion_commitment'] == 'unknown'
            assert not c['predictive_admitted'] and not c['settlement_evidence']
            predicates += 1
            expanded += len(c['role_expansions'])
            chains += bool(c['attribution_chain'])
            if c['role_expansions'] or c['attribution_chain']:
                articles_changed.add(str(a['article_id']))
                changes.append({'article_id': a['article_id'], 'predicate': c['predicate'],
                    'role_expansions': c['role_expansions'],
                    'updated_roles': {k: c[k] for k in ('actor','object','speaker')},
                    'attribution_chain': c['attribution_chain']})
        rows.append({'kind': 'opened', 'article_id': a['article_id'], 'extraction': e})
    report = {'synthetic_fields': dict(counts), 'opened_articles': len(old),
        'opened_predicates': predicates, 'expanded_roles': expanded,
        'predicates_with_attribution_chain': chains, 'articles_changed': len(articles_changed),
        'predictive_admissions': 0, 'independent_accuracy_estimate': False}
    for name, records in [('extractions', rows), ('scores', scores), ('changes', changes)]:
        (out/(name+'.jsonl')).write_text(''.join(json.dumps(r)+'\n' for r in records))
    (out/'report.json').write_text(json.dumps(report, indent=2)+'\n')
    (out/'manifest.json').write_text(json.dumps({'inputs': hashes,
        'outputs': {p.name: digest(p) for p in out.iterdir()}}, indent=2)+'\n')
    print(json.dumps(report, indent=2))


if __name__ == '__main__':
    main()
