"""One-shot finite-frame association audit; no predictive outcomes accessed."""
import json
import math
from pathlib import Path
from scipy.stats import hypergeom
from eventx.tasks.validate_v6_boundary_submissions import read, sha, validate, write
from eventx.v6.link_audit import validate_reviews


def endpoint(N, n, x, q, alpha=0.05/3):
    if not (0 <= x <= n <= N and n > 0):
        raise ValueError('Invalid finite sample')
    k0 = math.ceil(q*N)
    p = float(hypergeom.cdf(x, N, k0, n))
    upper = max(k for k in range(x, N-n+x+1)
                if hypergeom.cdf(x, N, k, n) > alpha) / N
    status = 'PASS' if p <= alpha else ('FAIL quality target' if x/n >= q else 'INCONCLUSIVE')
    return dict(N=N, n=n, errors=x, observed_error_fraction=x/n,
                upper_error_fraction=upper, tolerance=q, alpha=alpha,
                null_error_count=k0, p_value=p, status=status)


def main():
    base = Path('data/v6/bounded_audit_20260917')
    submissions = Path('data/v6/bounded_submission_validation_20260917')
    revision = Path('data/v6/bounded_adjudication_revision_20260917')
    relevance = Path('data/v6/bounded_relevance_receipt_20260917')
    out = Path('data/v6/bounded_final_audit_20260917')
    if out.exists():
        raise FileExistsError('Final audit already started; do not rerun')
    inputs = {}
    for folder in (base, submissions, revision, relevance):
        manifest = folder / 'manifest.json'
        inputs[str(manifest)] = sha(manifest)
        for name, digest in json.loads(manifest.read_text())['outputs'].items():
            path = folder / name
            assert sha(path) == digest, path
            inputs[str(path)] = digest
    freeze = json.loads((base / 'frame_freeze.json').read_text())
    for name, digest in freeze['inputs'].items():
        assert sha(Path(name)) == digest, name
    correction = Path('eventx/release/v6/BOUNDED_ADJUDICATION_CORRECTION_20260917.md')
    inputs[str(correction)] = sha(correction)
    closure = Path('eventx/release/v6/BOUNDED_UNRESOLVED_CLOSURE_20260917.md')
    inputs[str(closure)] = sha(closure)
    adj = {r['review_id']: r for r in read(revision / 'submission_snapshot.jsonl')}
    tasks = read(submissions / 'adjudication_packet.jsonl')
    assert len(adj) == len(tasks) == 8
    assert set(adj) == {r['review_id'] for r in tasks}
    for task in tasks:
        row = adj[task['review_id']]
        assert all(row[k] == task[k] for k in ('first_review','second_review','kind'))
        assert row['adjudication_attempts_used'] == 1 and row['adjudicator'] and row['rationale']
    decisions = []
    for kind, good in [('family','no_direct_link_established'), ('story','distinct_story')]:
        rows = read(submissions / f'{kind}_submission_snapshot.jsonl')
        assert not validate(read(base / f'{kind}_review_packet.jsonl'), rows, kind)
        for row in rows:
            identity = row['review_id']
            label = adj[identity]['adjudication_decision'] if identity in adj else row['decision']
            allowed = {'must_link','no_direct_link_established','unresolved'} if kind == 'family' else {'same_story','related_update','distinct_story','unresolved'}
            assert label in allowed
            decisions.append(dict(endpoint=kind, id=identity, decision=label, error=label != good))
    packet = read(base / 'relevance_review_packet.jsonl')
    a, b = [read(relevance / f'relevance_reviewer_{r}_responses.jsonl') for r in ('A','B')]
    checked = validate_reviews(packet,a,b)
    unresolved = set(checked['disagreement_ids'])
    assert unresolved == {'95bb346e685cbe07703d3759','837e2ad1ef9441dd597f6d7f'}
    for row in a:
        label = row['labels']
        is_unresolved = row['pair_id'] in unresolved
        decisions.append(dict(endpoint='relevance', id=row['pair_id'],
            decision='unresolved_user_closed' if is_unresolved else label,
            error=is_unresolved or not (label['relevance']=='direct' and label['outcome_applicability']=='yes_proposition')))
    # Receipt precedes endpoint calculation; failures are preserved, never retried silently.
    out.mkdir()
    (out / 'consumption_receipt.json').write_text(json.dumps(dict(inputs=inputs,
        code_sha256=sha(Path(__file__)), scope='association audit only',
        deviation='Evaluator implemented after review submission; mathematical rules prefrozen.',
        unresolved_ids=sorted(unresolved)), indent=2)+'\n')
    results = {}
    for kind, frame in freeze['frames'].items():
        rows = [r for r in decisions if r['endpoint']==kind]
        assert len(rows) == frame['n']
        results[kind] = endpoint(frame['N'],frame['n'],sum(r['error'] for r in rows),freeze['error_tolerances'][kind],freeze['alpha'])
    report = dict(endpoints=results, overall='PASS' if all(r['status']=='PASS' for r in results.values()) else 'STOP: bounded feasibility not established',
        unresolved_relevance_cases=2, new_adjudication_judgments=8,
        predictive_outcomes_accessed=False, reserved_pairs_admitted=0,
        scope='Finite enumerated development frames, conditional on submitted reference judgments; not universal independence or predictive evidence.',
        deviation='Evaluator code implemented after annotations; fixed mathematical specification unchanged.')
    write(out / 'case_decisions.jsonl', decisions)
    write(out / 'discovered_dependencies.jsonl', [r for r in decisions if r['endpoint']=='family' and r['error']])
    (out / 'report.json').write_text(json.dumps(report,indent=2)+'\n')
    (out / 'manifest.json').write_text(json.dumps(dict(inputs=inputs,outputs={p.name:sha(p) for p in out.iterdir()}),indent=2)+'\n')
    print(json.dumps(report,indent=2))


if __name__ == '__main__':
    main()
