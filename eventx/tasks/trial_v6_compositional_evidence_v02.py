"""Deterministic v0.2 replay on already-open v0.1 records; no model inference."""
import json
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from eventx.tasks.score_v6_evidence_fields import digest, score
from eventx.v6.compositional_evidence_v02 import revise
from eventx.v6.structured_evidence import validate_spans


def read(p):
    return [json.loads(s) for s in p.read_text().splitlines()]


def main():
    old = Path('data/v6/compositional_evidence_trial_20260924')
    base = Path('data/v6/evidence_binding_comparison_20260921')
    prior = Path('data/v6/evidence_field_scorecard_20260924')
    for root in (old, base, prior):
        m = json.loads((root/'manifest.json').read_text())
        for p,h in m['inputs'].items():
            assert digest(Path(p)) == h, p
        for p,h in m['outputs'].items():
            assert digest(root/p) == h, p
    out = Path('data/v6/compositional_evidence_v02_20260924')
    out.mkdir(exist_ok=False)
    inputs = [Path(__file__), Path('eventx/v6/compositional_evidence_v02.py'),
        Path('eventx/tasks/test_compositional_evidence_v02.py'), old/'manifest.json',
        base/'manifest.json', prior/'manifest.json']
    hashes = {str(p):digest(p) for p in inputs}
    (out/'receipt.json').write_text(json.dumps({'created_at':datetime.now(timezone.utc).isoformat(),
        'inputs':hashes, 'scope':'cached opened development; schema-safety not accuracy'},indent=2)+'\n')
    articles = {str(a['article_id']):a for a in read(base/'opened_inventory.jsonl')}
    cases = {c[0]:c for c in json.loads((prior/'spec.json').read_text())['cases']}
    rows, scores, diagnostics = [], [], []
    stats = Counter()
    fields = defaultdict(Counter)
    for record in read(old/'extractions.jsonl'):
        before = record['extraction']
        e = revise(before)
        synthetic = record['kind'] == 'synthetic'
        a = {'headline':cases[record['case']][1], 'summary':''} if synthetic else articles[str(record['article_id'])]
        validate_spans(e,a)
        assert len(e['claims']) == len(before['claims'])
        for c in e['claims']:
            assert not c['predictive_admitted'] and not c['relation_readiness']['may_auto_link_contract']
            assert c['assertion_commitment'] == c['entity_identity'] == c['episode_identity'] == 'unknown'
            if not synthetic:
                stats['predicates'] += 1
                for role, r in c['roles'].items():
                    assert r['resolved_entity']['value'] is None
                    stats['optional_expansions'] += len(r['complement_candidates'])
                    if r['assessment']['status'] == 'structurally_flagged':
                        stats['flagged_roles'] += 1
                        diagnostics.append({'article_id':record['article_id'], 'predicate':c['predicate']['value'],
                            'role':role, 'span':r['base_span'], 'assessment':r['assessment']})
                if c['speaker']['value'] is not None:
                    stats['speaker_candidates'] += 1
                stats['attribution_edges'] += len(c['attribution_chain'])
                stats['verified_attribution_edges'] += sum(x['verified_attribution'] for x in c['attribution_chain'])
        rows.append({**record, 'extraction':e})
        if synthetic:
            for s in score(cases[record['case']],e):
                fields[s['field']][s['status']] += 1
                scores.append(s)
        else:
            stats['articles'] += 1
    report = {'opened':dict(stats), 'legacy_base_span_fields':dict(fields),
        'admissions':0, 'independent_accuracy_estimate':False,
        'interpretation':'Base-span score is not alternative-span resolution; no accuracy improvement claimed.'}
    for name, records in [('extractions',rows),('scores',scores),('diagnostics',diagnostics)]:
        (out/(name+'.jsonl')).write_text(''.join(json.dumps(r)+'\n' for r in records))
    (out/'report.json').write_text(json.dumps(report,indent=2)+'\n')
    (out/'manifest.json').write_text(json.dumps({'inputs':hashes,
        'outputs':{p.name:digest(p) for p in out.iterdir()}},indent=2)+'\n')
    print(json.dumps(report,indent=2))


if __name__ == '__main__':
    main()
