"""Compile reviewed source-only must-links; fail closed on unreviewed boundaries.

This certifies graph consistency, not historical semantics or final independence.
No price/label/prediction files are read, and no final families are auto-approved.
"""

from collections import defaultdict
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
QUEUE = ROOT/'data/v5/recovery_summary_20260910/candidate_family_queue.jsonl'
OUT = ROOT/'data/v5/family_certification_20260910'

# Exact scopes reviewed from the projected questions, not a broad keyword merger.
SCOPES = {
    'california_governor_2026_primary_to_general': [
        'kalshi:event:KXCAGOV2ND-26JUN02-2', 'kalshi:event:KXCAGOV3RD-26JUN02-3',
        'kalshi:event:KXCAGOVMATCHUP-26JUN', 'kalshi:event:KXCAGOVPRIMARY1ST-26JUN02-1ST',
        'kalshi:event:KXCAGOVPRIMARYEXACT-26JUN02', 'kalshi:event:KXCAGOVPRIMARYTOP3-26JUN02',
        'kalshi:event:KXPRIMARYMOV-CAGOVPRIMARY1ST26JUN021ST',
        'kalshi:event:KXVOTEPRIMARY-26JUN02KPOR', 'kalshi:event:KXVOTEPRIMARY-26JUN02SHIL',
        'kalshi:event:KXVOTEPRIMARY-26JUN02TSYE', 'kalshi:event:KXVOTEPRIMARY-CAGOVR1SHILSHIL',
        'kalshi:event:KXVOTEPRIMARY-GOVCAPRIMARY26XBEC', 'polymarket:event:57096'],
    'wimbledon_men_2026_cross_venue': [
        'kalshi:event:KXATP-26WIM', 'kalshi:event:KXATPADVANCE-26WIMFIN', 'polymarket:event:139122'],
    'wimbledon_women_2026_cross_venue': ['kalshi:event:KXWTA-26WIM', 'polymarket:event:139182'],
    'olivia_rodrigo_album_2026': [
        'kalshi:event:KXALBUMDEBUT-26JUN27-YOU', 'kalshi:event:KXALBUMEQUIV-YOU26JUN18',
        'kalshi:event:KXALBUMEQUIV-YOU26JUN25', 'kalshi:event:KXALBUMSALES-YOUS-ACT',
        'kalshi:event:KXALBUMSALES-YOUS-PURE', 'kalshi:event:KXTOPALBUMRECORD-YOU-OLI'],
}
REASONS = {
    'california_governor_2026_primary_to_general':
        'Same 2026 California gubernatorial primary counts/ranks/margins; primary-to-general stage dependency',
    'wimbledon_men_2026_cross_venue': 'Same named 2026 Wimbledon mens tournament, winner/advance and cross-venue winners',
    'wimbledon_women_2026_cross_venue': 'Same named 2026 Wimbledon womens tournament winner across venues',
    'olivia_rodrigo_album_2026': 'Same named album: debut, units, sales and consecutive number-one weeks',
}


def components(nodes, edges):
    parent = {n: n for n in nodes}
    def find(n):
        if n not in parent:
            raise ValueError('Edge references unknown candidate event')
        while parent[n] != n:
            parent[n] = parent[parent[n]]
            n = parent[n]
        return n
    for a, b in edges:
        ra, rb = find(a), find(b)
        parent[max(ra, rb)] = min(ra, rb)
    grouped = defaultdict(list)
    for node in sorted(parent):
        grouped[find(node)].append(node)
    return sorted(grouped.values())


def validate_split_certificate(nodes, edges, mapping, boundary_review_complete):
    if set(mapping) != set(nodes):
        raise ValueError('Missing/extra candidate membership')
    if any(mapping[a] != mapping[b] for a, b in edges):
        raise ValueError('Known must-link crosses proposed family split')
    if set(boundary_review_complete) != set(nodes) or not all(boundary_review_complete.values()):
        return {'graph_consistent': True, 'final_family_certified': False,
                'reason': 'Unreviewed external/adjacent/multi-leg boundaries'}
    return {'graph_consistent': True, 'final_family_certified': True,
            'scope': 'declared reviewed graph only, not source-version admission or statistical independence'}


def main():
    OUT.mkdir(parents=True, exist_ok=False)
    groups = defaultdict(list)
    with QUEUE.open() as handle:
        for line in handle:
            row = json.loads(line)
            if not row['candidate_family_id']:
                raise ValueError('Missing candidate identity')
            groups[row['candidate_family_id']].append(row)
    scopes = dict(SCOPES)
    reasons = dict(REASONS)
    oldpath = ROOT/'data/v5/family_review_20260909/scoped_merges.json'
    for record in json.loads(oldpath.read_text()):
        scopes[record['scope']] = record['candidate_family_ids']
        reasons[record['scope']] = record['reason']
    edges, evidence = [], []
    for scope, keys in scopes.items():
        if not set(keys).issubset(groups):
            raise ValueError('Reviewed scope missing from source queue')
        links = [(keys[0], key) for key in keys[1:]]
        edges.extend(links)
        evidence.append({'scope': scope, 'candidate_event_ids': keys, 'must_links': links,
            'reviewer': 'Codex source-only semantic review 2026-09-10',
            'reason': reasons[scope], 'not_logical_equivalence': True,
            'review_basis': 'projected market questions and prior scoped tournament review',
            'market_count': sum(len(groups[k]) for k in keys),
            'identities': [{k: r.get(k) for k in ('venue', 'market_id', 'question', 'candidate_family_id')}
                           for key in keys for r in groups[key]],
            'boundary_review_complete': False,
            'remaining': 'Full contract/subtitle versions, annual/season/multi-leg bridges and all cross-venue boundaries'})
    graph = components(groups, edges)
    mapping = {n: 'candidate-component-'+hashlib.sha256('|'.join(c).encode()).hexdigest()[:16]
               for c in graph for n in c}
    certificate = validate_split_certificate(groups, edges, mapping, {n: False for n in groups})
    report = {'status': 'must_links_reviewed_final_boundaries_uncertified',
              'candidate_events': len(groups), 'candidate_components_after_known_merges': len(graph),
              'reviewed_scopes': len(scopes), 'reviewed_must_link_edges': len(edges),
              'markets_in_reviewed_scopes': sum(r['market_count'] for r in evidence),
              'final_approved_families': 0, 'source_versions_certified': False,
              'graph_certificate': certificate, 'labels_or_prices_read': False}
    for name, value in [('reviewed_edges.json', evidence), ('candidate_components.json', graph),
                        ('report.json', report)]:
        (OUT/name).write_text(json.dumps(value, indent=2)+'\n')
    paths = [Path(__file__), QUEUE, oldpath, *sorted(OUT.iterdir())]
    (OUT/'manifest.json').write_text(json.dumps({'artifacts': [
        {'path': str(p.relative_to(ROOT)), 'sha256': hashlib.sha256(p.read_bytes()).hexdigest()}
        for p in paths]}, indent=2)+'\n')
    print(json.dumps(report, indent=2))


if __name__ == '__main__':
    main()
