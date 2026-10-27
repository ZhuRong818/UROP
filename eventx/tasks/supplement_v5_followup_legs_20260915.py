"""Correct omitted parent-leg joins without changing published packets or reviews."""
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def main():
    files = ['data/v5/rich_leg_recovery_20260915/leg_references.jsonl',
             'data/v5/unresolved_pair_enrichment_20260915/enriched_pairs.jsonl',
             'data/v5/unresolved_followup_validation_20260915/remaining_unresolved.jsonl']
    data = [list(map(json.loads, (ROOT / f).read_text().splitlines())) for f in files]
    legs, pairs, reviews = data
    pairs = {p['pair_id']: p for p in pairs}
    rows = []
    for review in reviews:
        p = pairs[review['pair_id']]
        sides = {}
        for side in ('left', 'right'):
            node = p[side]['event_id']
            refs = [r for r in legs if node == 'kalshi:event:' + r['parent_event_id']]
            sides[side] = {'event_id': node, 'parent_leg_references': refs}
        left = {r['market_ticker'] for r in sides['left']['parent_leg_references']}
        right = {r['market_ticker'] for r in sides['right']['parent_leg_references']}
        rows.append({'pair_id': p['pair_id'], **sides, 'shared_underlying_contract_ids': sorted(left & right),
                     'review_decision': 'unresolved_preserved', 'automatic_merge': False,
                     'note': 'Exact cached leg IDs restored; inspect dates, polarity and rules before a new decision.'})
    out = ROOT / 'data/v5/unresolved_leg_supplement_20260915'
    out.mkdir(exist_ok=False)
    (out / 'corrected_leg_evidence.jsonl').write_text(''.join(json.dumps(r) + '\n' for r in rows))
    report = {'unresolved_pairs': len(rows), 'pairs_with_parent_refs_both_sides': sum(bool(r['left']['parent_leg_references']) and bool(r['right']['parent_leg_references']) for r in rows),
              'pairs_with_shared_underlying_contract_ids': sum(bool(r['shared_underlying_contract_ids']) for r in rows),
              'cause': 'Published enrichment compared prefixed event node to unprefixed parent_event_id.',
              'prior_artifacts_preserved': True, 'graph_changed': False, 'outcomes_accessed': False}
    (out / 'report.json').write_text(json.dumps(report, indent=2) + '\n')
    (out / 'README.md').write_text('# Corrected multi-leg evidence\n\nThe original enrichment omitted parent references due to a prefixed/unprefixed ID join mismatch.\nThis supplement restores existing cached IDs; original packet and submitted reviews remain unchanged.\nReview `corrected_leg_evidence.jsonl` alongside the original context, preserving unresolved decisions\nuntil evidence is reconsidered. Shared exact underlying IDs are structural-link evidence, not\nfull historical semantics or family certification. No links were automatically adopted.\n')
    sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
    (out / 'manifest.json').write_text(json.dumps({'inputs': {f: sha(ROOT / f) for f in files + [str(Path(__file__).relative_to(ROOT))]},
        'outputs': {p.name: sha(p) for p in out.iterdir()}}, indent=2) + '\n')
    assert all(r['parent_event_id'] == row[s]['event_id'].removeprefix('kalshi:event:') for row in rows for s in ('left', 'right') for r in row[s]['parent_leg_references'])
    print(json.dumps(report, indent=2))


if __name__ == '__main__':
    main()
