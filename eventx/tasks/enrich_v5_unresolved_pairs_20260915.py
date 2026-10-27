"""Package cached, label-free evidence for unresolved family-pair follow-up."""
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / 'data/v5/unresolved_pair_enrichment_20260915'
INPUTS = {}


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read(name, lines=False):
    path = ROOT / name
    INPUTS[name] = digest(path)
    return [json.loads(s) for s in path.read_text().splitlines() if s] if lines else json.loads(path.read_text())


def write(name, value, lines=False):
    path = OUT / name
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text((''.join(json.dumps(v, ensure_ascii=False) + '\n' for v in value))
                    if lines else json.dumps(value, indent=2, ensure_ascii=False) + '\n')


def main():
    graph = 'data/v5/reviewed_pair_graph_20260915/'
    manifest = read(graph + 'manifest.json')
    for name, expected in manifest['outputs'].items():
        assert digest(ROOT / graph / name) == expected, name
    unresolved = read('data/v5/pair_submission_validation_20260915/unresolved_submitted.jsonl', True)
    pairs = {p['pair_id']: p for p in read('data/v5/full_family_review_20260915/pairs.jsonl', True)}
    components = read(graph + 'candidate_components.json')
    node_family = {}
    for nodes in components:
        fid = 'family-' + hashlib.sha256('|'.join(sorted(nodes)).encode()).hexdigest()[:16]
        for node in nodes:
            assert node not in node_family
            node_family[node] = (fid, len(nodes))
    contexts = read('data/v5/topic_coverage_triage_20260914/topic_review_queue.jsonl', True)
    staged = {r['market_id']: r for r in read('data/v5/source_readiness_20260908/metadata_staging.jsonl', True)}
    recovered = {}
    for name in ('parent_metadata', 'underlying_metadata'):
        path = 'data/v5/rich_leg_recovery_20260915/' + name + '.jsonl'
        for index, row in enumerate(read(path, True), 1):
            recovered[row['ticker']] = (row, f'{path}:{index}')
    legs = read('data/v5/rich_leg_recovery_20260915/leg_references.jsonl', True)
    by_event = {}
    for row in contexts:
        by_event.setdefault(row['candidate_family_id'], []).append(row)
    rules_path = ROOT / 'eventx/release/v5/FAMILY_REVIEW_RULES_20260915.md'
    INPUTS[str(rules_path.relative_to(ROOT))] = digest(rules_path)
    assert len(unresolved) == len({r['pair_id'] for r in unresolved}) == 59
    assert not OUT.exists(), 'Preserve published outputs; choose a new version.'
    OUT.mkdir()
    records, responses = [], []
    for review in unresolved:
        pair = pairs[review['pair_id']]
        record = {'pair_id': pair['pair_id'], 'original_review': review,
                  'explicit_year_disagreement': pair['explicit_year_disagreement'],
                  'review_status': 'unresolved_followup_required', 'final_certification': False}
        for side in ('left', 'right'):
            node = pair[side]
            fid, size = node_family[node]
            contracts = []
            for ctx in by_event.get(node, []):
                mid = ctx['market_id']
                contract = {k: ctx.get(k) for k in ('market_id', 'venue', 'question', 'yes_sub_title', 'no_sub_title', 'flags')}
                contract['cached_metadata'] = staged.get(mid)
                raw, ref = recovered.get(mid, ({}, None))
                contract['rules'] = {k: raw.get(k) for k in ('rules_primary', 'rules_secondary')}
                contract['rules_source_ref'] = ref
                contract['rules_status'] = ('nonempty_cached_rules' if any(contract['rules'].values())
                                             else 'empty_in_recovered_projection' if ref else 'not_in_recovered_projection')
                contract['historical_rules_certified'] = False
                contracts.append(contract)
            record[side] = {'event_id': node, 'original_family_id': pair[side + '_family'],
                            'current_family_id': fid, 'component_event_count': size,
                            'event_text': pair[side + '_text'], 'contracts': contracts,
                            'metadata_gap': not bool(contracts),
                            'leg_references': [r for r in legs if node in
                                               (r['parent_event_id'], 'kalshi:event:' + r['event_ticker'])]}
        record['already_same_provisional_component'] = record['left']['current_family_id'] == record['right']['current_family_id']
        records.append(record)
        responses.append({'pair_id': pair['pair_id'], 'reviewer': None, 'decision': None,
                          'relation_type': None, 'rationale': None, 'evidence_refs': [],
                          'missing_evidence': [], 'reviewed_at': None,
                          'review_type': 'evidence_followup_not_blind_second_review'})
        page = [f"# {pair['pair_id']}", '', '## Original unresolved review', '',
                review['rationale'], '', 'Missing evidence requested: ' + json.dumps(review['missing_evidence']), '',
                f"Already in the same provisional component: {record['already_same_provisional_component']}. This does not resolve the direct relation.", '']
        for side in ('left', 'right'):
            item = record[side]
            page += [f'## {side.title()}: {item["event_id"]}', '',
                     f"Current: `{item['current_family_id']}` ({item['component_event_count']} event nodes). Original: `{item['original_family_id']}`.", '',
                     item['event_text'], '', '### Contract evidence', '']
            for contract in item['contracts']:
                page += ['```json', json.dumps(contract, indent=2, ensure_ascii=False), '```', '']
            if not item['contracts']:
                page += ['No contract metadata in the local review inventory. Identity/rules remain missing.', '']
            page += ['### Explicit leg references', '', '```json', json.dumps(item['leg_references'], indent=2), '```', '']
        page += ['## Follow-up checklist', '',
                 '- Establish event, entity, year/date and stage on both sides using cited evidence.',
                 '- Check exact rules and direct dependencies; do not equate topic similarity with a link.',
                 '- Empty or unavailable cached rules are not proof that the source has no rules.',
                 '- Record unresolved if the original missing evidence is still unavailable.',
                 '- No outcome access, graph edits or historical-availability certification.', '',
                 '[Instructions](../README.md) · [All pairs](../INDEX.md)', '']
        (OUT / 'pairs').mkdir(exist_ok=True)
        (OUT / 'pairs' / (pair['pair_id'] + '.md')).write_text('\n'.join(page))
    write('enriched_pairs.jsonl', records, True)
    write('review_responses.jsonl', responses, True)
    all_contracts = {c['market_id']: c for r in records for side in ('left', 'right') for c in r[side]['contracts']}
    report = {'pairs': len(records), 'unique_endpoint_events': len({r[s]['event_id'] for r in records for s in ('left', 'right')}),
              'unique_contracts': len(all_contracts),
              'contracts_with_cached_metadata': sum(c['cached_metadata'] is not None for c in all_contracts.values()),
              'contracts_with_nonempty_rules': sum(c['rules_status'] == 'nonempty_cached_rules' for c in all_contracts.values()),
              'endpoint_occurrences_without_contract_context': sum(r[s]['metadata_gap'] for r in records for s in ('left', 'right')),
              'pairs_already_same_component': sum(r['already_same_provisional_component'] for r in records),
              'current_provisional_components': len(components), 'pairs_resolved_by_this_task': 0,
              'external_requests': 0, 'outcomes_accessed': False, 'graph_changed': False}
    write('report.json', report)
    (OUT / 'REVIEW_RULES.md').write_text(rules_path.read_text())
    (OUT / 'README.md').write_text('''# Unresolved pair evidence follow-up

This packet preserves all 59 unresolved reviews and enriches them from cached,
label-free metadata only. It does not resolve pairs or certify family boundaries.
The current graph has 1,197 provisional components; the copied original review
rules describe the historical 1,280-component inventory. Use the current IDs here.

Start with [INDEX.md](INDEX.md), then fill a COPY of `review_responses.jsonl`.
Allowed decisions: `must_link`, `no_direct_link_established`, `unresolved`.
Allowed relation types and evidence requirements: [REVIEW_RULES.md](REVIEW_RULES.md).
Include reviewer, timestamp, rationale, evidence references and remaining gaps.
No-direct-link is not proof of independence. Indirect existing connectivity does
not settle the direct relation. Original reviews remain unchanged and attributed.

Because this packet shows previous rationales, this is evidence follow-up or
adjudication, NOT a blinded independent second review. New proposed links require
the separate independent-review procedure before graph adoption.

Cached dates are contract metadata, not verified historical semantics. Rules absent
from this packet may exist at the provider; no new retrieval occurred. Do not infer
missing outcome names from tickers. Do not consult realized results or prices.
`enriched_pairs.jsonl` includes source references and precise empty/missing flags.
The manifest hashes inputs and generated artifacts; preserve this release unchanged.
''')
    (OUT / 'INDEX.md').write_text('# All 59 unresolved pairs — enriched evidence\n\n[Instructions](README.md)\n\n' + '\n'.join(
        f"{i}. [{r['pair_id']}](pairs/{r['pair_id']}.md): {r['left']['event_id']} ↔ {r['right']['event_id']}" for i, r in enumerate(records, 1)) + '\n')
    INPUTS[str(Path(__file__).resolve().relative_to(ROOT))] = digest(Path(__file__))
    assert all(digest(ROOT / p) == h for p, h in INPUTS.items())
    assert all((OUT / 'pairs' / (r['pair_id'] + '.md')).exists() for r in records)
    write('manifest.json', {'inputs': INPUTS, 'outputs': {str(p.relative_to(OUT)): digest(p) for p in sorted(OUT.rglob('*')) if p.is_file()},
                            'input_hashes_unchanged': True, 'purpose': 'cached_label_free_review_enrichment'})
    print(json.dumps(report, indent=2))


if __name__ == '__main__':
    main()
