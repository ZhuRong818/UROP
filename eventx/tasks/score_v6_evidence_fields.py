"""Fixed assistant-authored development scorecard; no backend tuning or admissions."""
import hashlib
import json
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path

from eventx.v6.structured_evidence import extract as grammar, validate_spans

# Fixed before this run; informed by earlier opened development errors, NOT blind gold.
CASES = [
    ('active', 'The fund purchased copper.', 'purchased', {'actor': 'The fund', 'object': 'copper'}),
    ('passive', 'Copper was purchased by a pension fund.', 'purchased', {'actor': 'a pension fund', 'object': 'Copper'}),
    ('partitive', 'The fund sold some of its copper holdings.', 'sold', {'actor': 'The fund', 'object': 'some of its copper holdings'}),
    ('forecast', 'The economist expects copper to appreciate.', 'expects', {'speaker': 'The economist', 'actor': None, 'proposition': 'copper to appreciate', 'epistemic_status': 'forecast'}),
    ('opinion', 'The analyst believes copper is overvalued.', 'believes', {'speaker': 'The analyst', 'actor': None, 'proposition': 'copper is overvalued', 'epistemic_status': 'opinion'}),
    ('postposed', 'Copper will rise, says analyst.', 'says', {'speaker': 'analyst', 'actor': None, 'proposition': 'Copper will rise'}),
    ('negation', 'The fund did not buy copper.', 'buy', {'actor': 'The fund', 'object': 'copper', 'negation': True}),
    ('negated_speech', 'The analyst did not say copper rose.', 'say', {'speaker': 'The analyst', 'proposition': 'copper rose', 'negation': True}),
    ('stage', 'Brazil won the quarterfinal in 2026.', 'won', {'actor': 'Brazil', 'object': 'the quarterfinal', 'year_mentions': ['2026']}),
    ('pronoun', 'The fund sold copper. It purchased silver.', 'purchased', {'actor': 'It', 'object': 'silver'}),
    ('nominal', 'The company celebrates design wins.', 'wins', {'predicate_absent': True}),
    ('contraction', 'The price won’t rise.', 'won', {'predicate_absent': True}),
]


def digest(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()


def normalize(v):
    # Only terminal punctuation/whitespace; no semantic synonym credit.
    return v.strip().rstrip('.,!?').strip() if isinstance(v, str) else v


def classify(actual, expected, found=True):
    if not found:
        return 'missing_predicate'
    if normalize(actual) == normalize(expected):
        return 'correct'
    return 'missing_field' if actual is None else 'incorrect'


def score(case, extraction):
    name, text, predicate, expected = case
    start = text.index(predicate)
    claims = [c for c in extraction['claims'] if any(
        e['field'] == 'headline' and e['start'] == start and e['end'] == start + len(predicate)
        for e in c['predicate']['evidence'])]
    assert len(claims) <= 1, 'Ambiguous exact predicate alignment'
    c = claims[0] if claims else None
    rows = []
    for field, target in expected.items():
        if field == 'predicate_absent':
            actual = not bool(claims)
            status = classify(actual, target)
        else:
            actual = None
            if c:
                if field == 'negation':
                    # Measures detection only, not semantic scope correctness.
                    actual = c['polarity']['value'] is not None
                elif field == 'year_mentions':
                    actual = sorted({v['value'] for v in c['time_mentions']})
                else:
                    actual = c[field]['value']
            status = classify(actual, target, c is not None)
        rows.append({'case': name, 'field': field, 'expected': target,
                     'actual': actual, 'status': status})
    return rows


def main():
    import spacy
    import en_core_web_sm
    from eventx.v6.dependency_evidence import extract as dependency
    old = Path('data/v6/dependency_evidence_trial_20260924')
    manifest = json.loads((old/'manifest.json').read_text())
    for p, h in manifest['inputs'].items():
        assert digest(Path(p)) == h, p
    for p, h in manifest['outputs'].items():
        assert digest(old/p) == h, p
    provenance = json.loads((old/'provenance.json').read_text())
    model_root = Path(en_core_web_sm.__file__).parent
    for p, h in provenance['model_hashes'].items():
        assert digest(model_root/p) == h, p
    assert spacy.__version__ == '3.8.7'
    out = Path('data/v6/evidence_field_scorecard_20260924')
    out.mkdir(exist_ok=False)
    spec = {'cases': CASES, 'reference_origin': 'assistant-authored, development-informed',
            'rules': 'Exact predicate offsets; exact fields except terminal punctuation. No case selection after inference. Null means role must remain unknown. Negation detection is not scope accuracy. Year mentions are not event identity.'}
    (out/'spec.json').write_text(json.dumps(spec, indent=2)+'\n')
    (out/'receipt.json').write_text(json.dumps({'created_at': datetime.now(timezone.utc).isoformat(),
        'spec_sha256': digest(out/'spec.json'), 'runner_sha256': digest(Path(__file__)),
        'predecessor_manifest_sha256': digest(old/'manifest.json'), 'inference_started': False}, indent=2)+'\n')
    nlp = en_core_web_sm.load()
    assert nlp.meta['version'] == '3.8.0'
    scores, extractions, summary = [], [], {}
    for backend, fn in [('grammar', grammar), ('dependency', lambda a: dependency(a, nlp))]:
        counts = defaultdict(Counter)
        safe = 0
        for case in CASES:
            a = {'headline': case[1], 'summary': ''}
            e = fn(a)
            validate_spans(e, a)
            assert not e['predictive_admitted']
            assert all(c['entity_identity'] == c['episode_identity'] == 'unknown' and
                       not c['predictive_admitted'] and not c['settlement_evidence'] for c in e['claims'])
            safe += 1
            extractions.append({'backend': backend, 'case': case[0], 'extraction': e})
            for r in score(case, e):
                counts[r['field']][r['status']] += 1
                scores.append({'backend': backend, **r})
        summary[backend] = {'fields': dict(counts), 'span_and_abstention_checks': safe}
    for name, rows in [('scores', scores), ('extractions', extractions)]:
        (out/(name+'.jsonl')).write_text(''.join(json.dumps(r)+'\n' for r in rows))
    (out/'report.json').write_text(json.dumps({'cases': len(CASES), 'summary': summary,
        'admissions': 0, 'independent_accuracy_estimate': False}, indent=2)+'\n')
    inputs = [Path(__file__), Path('eventx/tasks/test_v6_evidence_scorecard.py'), old/'manifest.json']
    (out/'manifest.json').write_text(json.dumps({'inputs': {str(p): digest(p) for p in inputs},
        'outputs': {p.name: digest(p) for p in out.iterdir()}}, indent=2)+'\n')
    print((out/'report.json').read_text())


if __name__ == '__main__':
    main()
