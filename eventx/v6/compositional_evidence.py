"""Versioned syntactic complements and attribution edges; no semantic admission."""
from eventx.v6.dependency_evidence import extract as dependency
from eventx.v6.structured_evidence import value


def extract(article, nlp):
    result = dependency(article, nlp)
    result['schema_version'] = 'compositional-evidence-0.1'
    tokens = {(t['field'], t['start']): t for t in result['tokens']}
    claims = {(c['predicate']['evidence'][0]['field'], c['attachment']['predicate_start']): c
              for c in result['claims']}
    children = {}
    for key, t in tokens.items():
        parent = (t['field'], t['head_start'])
        if key != parent:
            children.setdefault(parent, []).append(t)

    def nominal_members(t):
        # No relative clauses, coordination, temporal PPs or verb subtrees.
        members = [t]
        for child in children.get((t['field'], t['start']), []):
            if child['dep'] in {'det', 'amod', 'compound', 'poss', 'case', 'nummod', 'quantmod'}:
                members.extend(nominal_members(child))
            elif child['dep'] == 'prep' and child['lemma'].lower() == 'of':
                objects = [x for x in children.get((child['field'], child['start']), []) if x['dep'] == 'pobj']
                if objects:
                    members.append(child)
                    for obj in objects:
                        members.extend(nominal_members(obj))
        return members

    for c in result['claims']:
        c['role_expansions'] = []
        for role in ('actor', 'object', 'speaker'):
            for e in list(c[role]['evidence']):
                field = e['field']
                inside = [t for t in tokens.values() if t['field'] == field and e['start'] <= t['start'] < e['end']]
                roots = [t for t in inside if not e['start'] <= t['head_start'] < e['end']]
                if len(roots) != 1:
                    continue
                members = nominal_members(roots[0])
                lo = min(e['start'], *(t['start'] for t in members))
                hi = max(e['end'], *(t['end'] for t in members))
                # Reject noncontiguous expansion instead of swallowing intervening clauses.
                selected = {t['start'] for t in inside + members}
                if any(t['field'] == field and lo <= t['start'] < hi and t['start'] not in selected for t in tokens.values()):
                    continue
                if (lo, hi) != (e['start'], e['end']):
                    c['role_expansions'].append({'role': role, 'previous': c[role], 'rule': 'nominal_of_complement'})
                    c[role] = value(article[field], field, lo, hi)
        c['attribution_chain'] = []
        e = c['predicate']['evidence'][0]
        node = tokens[(e['field'], e['start'])]
        seen = set()
        while node['dep'] in {'ccomp', 'xcomp'}:
            key = (node['field'], node['head_start'])
            if key in seen or key not in tokens:
                break
            seen.add(key)
            parent = claims.get(key)
            if parent and parent['speaker']['value'] is not None:
                c['attribution_chain'].append({
                    'predicate': parent['predicate'], 'speaker': parent['speaker'],
                    'epistemic_status': parent['epistemic_status'],
                    'negation': parent['polarity'], 'relation': 'syntactic_complement',
                    'factuality': 'unknown'})
            node = tokens[key]
        # Negated speech does not imply a negated embedded event, nor its truth.
        c['assertion_commitment'] = 'unknown'
    return result
