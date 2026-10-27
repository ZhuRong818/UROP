"""Full fixed-development retrieval with cleaning before subject search."""
import json
from collections import Counter
from pathlib import Path
from eventx.tasks.check_proposition_v03_development import read, digest
from eventx.v6.subject_retrieval import retrieve
from eventx.v6.subject_retrieval_v02 import subjects, context_gate
from eventx.v6.clean_speech import clean, prepare
from eventx.v6.claim_role_v02 import assess as roles
from eventx.v6.claim_period import assess as period


def main():
    source = Path('data/v6/expanded_coverage_20260919')
    for name, expected in json.loads((source/'manifest.json').read_text()).items():
        assert digest(source/name) == expected
    cp = Path('data/v6/contract_link_pilot_20260916/contract_cards.jsonl')
    prior = Path('data/v6/clean_speech_20260919')
    manifest = json.loads((prior/'manifest.json').read_text())
    for name, expected in manifest['inputs'].items():
        assert digest(Path(name)) == expected
    for name, expected in manifest['outputs'].items():
        assert digest(prior/name) == expected
    out = Path('data/v6/clean_retrieval_20260920')
    out.mkdir(exist_ok=False)
    inputs = {str(p): digest(p) for p in [cp, source/'manifest.json', prior/'manifest.json', Path(__file__)]}
    code = {str(p): digest(p) for p in sorted(Path('eventx/v6').glob('*.py'))}
    (out/'start_receipt.json').write_text(json.dumps({'inputs': inputs, 'code': code,
        'scope': 'same 500 opened development articles; no new labels or neural ranking'}, indent=2)+'\n')
    cards = {c['contract_id']: c for c in read(cp)}
    registry = {cid: subjects(c) for cid, c in cards.items()}
    articles = read(source/'articles.jsonl')
    counts = Counter(); reasons = Counter(); rows = []; masks = []
    for article in articles:
        cleaned, excluded = clean(article)
        if excluded:
            masks.append({'article_id': article['article_id'], 'excluded_spans': excluded})
        for cid, evidence in retrieve(cleaned, registry).items():
            counts['retrieved_pairs'] += 1
            card = cards[cid]
            if context_gate(cleaned, card, evidence) != 'subject_context_candidate':
                continue
            counts['context_retained_pairs'] += 1
            _, relation = prepare(article, card)
            reasons[relation['reason']] += 1
            if relation['status'] != 'event_channel_candidate':
                continue
            rows.append({'article_id': article['article_id'], 'contract_id': cid,
                'question': card['question'], 'relation': relation,
                'roles': roles(relation), 'claim_period': period(cleaned, card, relation)})
    keys = lambda rr: {(r['article_id'], r['contract_id']) for r in rr}
    previous = keys(read(prior/'ranking_inputs.jsonl')); current = keys(rows)
    report = {'sample_articles': len(articles), **counts, 'masked_articles': len(masks),
        'channel_pairs': len(rows), 'channel_articles': len({r['article_id'] for r in rows}),
        'reasons': dict(reasons), 'roles': dict(Counter(e['role'] for r in rows for e in r['roles'])),
        'periods': dict(Counter(r['claim_period']['period']['status'] for r in rows)),
        'added_vs_fixed_filter': len(current-previous), 'removed_vs_fixed_filter': len(previous-current),
        'training_admissions': 0, 'neural_ranking': 'not run; no rank-based acceptance rule',
        'limits': 'Development candidate yield only, not precision/recall or source certification.'}
    for name, data in [('candidates', rows), ('masked_articles', masks)]:
        (out/(name+'.jsonl')).write_text(''.join(json.dumps(r)+'\n' for r in data))
    (out/'report.json').write_text(json.dumps(report, indent=2)+'\n')
    assert all(digest(Path(p)) == h for p, h in {**inputs, **code}.items())
    (out/'manifest.json').write_text(json.dumps({p.name: digest(p) for p in out.iterdir()}, indent=2)+'\n')
    print(json.dumps(report, indent=2))


if __name__ == '__main__':
    main()
