"""Validate submitted follow-up; prepare evidence-only independent review, no merges."""
from collections import Counter
from datetime import datetime
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
BASE = ROOT / 'data/v5/unresolved_pair_enrichment_20260915'
OUT = ROOT / 'data/v5/unresolved_followup_validation_20260915'


def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()


def main():
    source = BASE / 'review_responses_filled_20260915.jsonl'
    inputs = [source, BASE / 'manifest.json', BASE / 'enriched_pairs.jsonl', BASE / 'REVIEW_RULES.md', Path(__file__)]
    hashes = {str(p.relative_to(ROOT)): sha(p) for p in inputs}
    manifest = json.loads((BASE / 'manifest.json').read_text())
    for name, expected in manifest['outputs'].items():
        assert sha(BASE / name) == expected, name
    graph = ROOT / 'data/v5/reviewed_pair_graph_20260915'
    gm = json.loads((graph / 'manifest.json').read_text())
    for name, expected in gm['outputs'].items():
        assert sha(graph / name) == expected, name
    hashes[str((graph / 'manifest.json').relative_to(ROOT))] = sha(graph / 'manifest.json')
    pairs = {r['pair_id']: r for r in map(json.loads, (BASE / 'enriched_pairs.jsonl').read_text().splitlines())}
    rows = list(map(json.loads, source.read_text().splitlines()))
    issues = []
    ids = [r.get('pair_id') for r in rows]
    if len(ids) != len(set(ids)) or set(ids) != set(pairs):
        issues.append({'error': 'duplicate_missing_or_extra_ids'})
    for r in rows:
        errs = []
        if r.get('decision') not in {'must_link', 'no_direct_link_established', 'unresolved'}:
            errs.append('invalid_decision')
        if r.get('relation_type') not in {'same_event', 'stage_dependency', 'nested_outcome', 'explicit_leg', 'distinct_event', 'unknown'}:
            errs.append('invalid_relation')
        for key in ('reviewer', 'rationale'):
            if not isinstance(r.get(key), str) or not r[key].strip():
                errs.append('missing_' + key)
        for key in ('evidence_refs', 'missing_evidence'):
            if not isinstance(r.get(key), list) or any(not isinstance(x, str) or not x.strip() for x in r[key]):
                errs.append('invalid_' + key)
        if not r.get('evidence_refs'):
            errs.append('missing_evidence_refs')
        if r.get('decision') == 'unresolved' and not r.get('missing_evidence'):
            errs.append('unresolved_without_gap')
        if r.get('review_type') != 'evidence_followup_not_blind_second_review':
            errs.append('incorrect_review_type')
        try:
            if datetime.fromisoformat(r['reviewed_at'].replace('Z', '+00:00')).tzinfo is None:
                errs.append('naive_timestamp')
        except (KeyError, ValueError, TypeError):
            errs.append('invalid_timestamp')
        if errs:
            issues.append({'pair_id': r.get('pair_id'), 'errors': errs})
    proposed = [r for r in rows if r.get('decision') == 'must_link']
    unresolved = [r for r in rows if r.get('decision') == 'unresolved']
    availability = []
    for r in unresolved:
        p = pairs[r['pair_id']]
        availability.append({'pair_id': r['pair_id'], 'requested_missing_evidence': r['missing_evidence'],
                             'cached_leg_reference_counts': {s: len(p[s]['leg_references']) for s in ('left', 'right')},
                             'evidence_page': str((BASE / 'pairs' / (r['pair_id'] + '.md')).relative_to(ROOT)),
                             'note': 'Presence of leg references is not full rule/fixture certification; recheck existing page before retrieval.'})
    report = {'submitted_rows': len(rows), 'expected_pairs': len(pairs), 'schema_and_coverage_pass': not issues,
              'issues': issues, 'decision_counts': dict(Counter(r.get('decision') for r in rows)),
              'reviewer_ids': dict(Counter(r.get('reviewer') for r in rows)),
              'review_type': 'evidence_followup_not_blind_second_review',
              'external_evidence_urls_verified': False, 'independent_second_review_complete': False,
              'unresolved_pairs_with_cached_leg_refs_both_sides': sum(all(v > 0 for v in a['cached_leg_reference_counts'].values()) for a in availability),
              'current_provisional_components': len(json.loads((graph / 'candidate_components.json').read_text())),
              'new_links_adopted': 0, 'graph_changed': False, 'outcomes_accessed': False,
              'final_family_certification': False}
    OUT.mkdir(exist_ok=False)
    def dump(name, value, lines=False):
        (OUT / name).write_text(''.join(json.dumps(r, ensure_ascii=False) + '\n' for r in value) if lines else json.dumps(value, indent=2) + '\n')
    dump('report.json', report)
    dump('remaining_unresolved.jsonl', unresolved, True)
    dump('evidence_gap_inventory.jsonl', availability, True)
    dump('proposed_links.jsonl', proposed, True)
    if not issues:
        # Omit all first/follow-up decisions, rationales, reviewer IDs and scores.
        packet = [{k: pairs[r['pair_id']][k] for k in ('pair_id', 'left', 'right', 'explicit_year_disagreement')} for r in proposed]
        dump('independent_review_context.jsonl', packet, True)
        dump('independent_review_responses.jsonl', [{'pair_id': r['pair_id'], 'reviewer': None, 'decision': None,
             'relation_type': None, 'rationale': None, 'evidence_refs': [], 'missing_evidence': [], 'reviewed_at': None} for r in proposed], True)
    (OUT / 'README.md').write_text('''# Follow-up validation

All 59 submissions pass structural checks: six proposed must-links, one
no-direct-link decision and 52 unresolved. The graph remains at 1,197 provisional
components. Structural validation does not verify the submitted external citations.

Give a different independent reviewer ONLY `independent_review_context.jsonl`,
`independent_review_responses.jsonl` and the original review rules. Fill a copy.
These files omit prior decisions/rationales, but selection is limited to proposed
positive links; this is not a population accuracy audit or proof of blinding.
Do not send the submitted responses or enriched pages containing prior rationales.

Check exact contract dates, entities and rules. Component metrics (pure sales versus
equivalent units) can imply structural dependence without proving nested binary
outcomes at arbitrary thresholds. Announcement/departure requires role/deadline
matching. The geographic proposal needs exact contract rules and deadline evidence:
its submitted URL slugs differ from the common deadline asserted in its rationale.
These are review checks, not automatic rejections or accepted semantic findings.
Avoid news articles or current market pages exposing outcomes; prefer projected
contract-rule evidence. No external pages or protected outcomes were opened here.

For the remaining 52, consult `evidence_gap_inventory.jsonl`: some requested leg IDs
may already be in cached evidence. Presence alone does not certify fixture/rule
semantics. No-direct-link is not a certificate of statistical independence.
No new merges or family/source/inference admission are authorized by this report.
''')
    assert all(sha(ROOT / name) == h for name, h in hashes.items())
    dump('manifest.json', {'inputs': hashes, 'outputs': {p.name: sha(p) for p in OUT.iterdir() if p.is_file()}, 'input_hashes_unchanged': True})
    print(json.dumps(report, indent=2))


if __name__ == '__main__':
    main()
