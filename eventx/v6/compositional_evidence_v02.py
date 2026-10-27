"""Uncertainty-preserving evidence graph. Syntactic candidates are not entities."""
from copy import deepcopy
import re
from eventx.v6.structured_evidence import unknown


def assess_role(role, tokens):
    evidence = role['evidence']
    if not evidence:
        return {'status': 'missing', 'head': unknown(), 'risks': ['missing_span'],
                'entity_type': 'unknown', 'identity': 'unknown'}
    e = evidence[0]
    inside = [t for t in tokens if t['field'] == e['field'] and e['start'] <= t['start'] < e['end']]
    roots = [t for t in inside if not e['start'] <= t['head_start'] < e['end'] or t['head_start'] == t['start']]
    risks = []
    head = unknown()
    if len(roots) != 1:
        risks.append('ambiguous_head')
    else:
        t = roots[0]
        head = {'status': 'candidate', 'value': t['quote'], 'evidence': [
            {k: t[k] for k in ('field', 'start', 'end', 'quote')}]}
        if t['pos'] not in {'NOUN', 'PROPN', 'PRON'}:
            risks.append('non_nominal_head')
        if t['pos'] == 'PRON':
            risks.append('referent_unresolved')
    text = role['value'] or ''
    if re.search(r'&(?:#\d+|#x[0-9a-f]+|[a-z]+);', text, re.I):
        risks.append('encoded_text')
    if text.rstrip().endswith(("'s", '’s', "s'", 's’')):
        risks.append('dangling_possessive')
    if '...' in text or '…' in text:
        risks.append('fragment_marker')
    return {'status': 'structurally_flagged' if risks else 'syntactic_candidate',
            'head': head, 'risks': risks, 'entity_type': 'unknown', 'identity': 'unknown'}


def revise(extraction):
    """Lossless adaptation of cached v0.1; no new parser or external inference."""
    if extraction['schema_version'] != 'compositional-evidence-0.1':
        raise ValueError('Expected versioned v0.1 extraction')
    result = deepcopy(extraction)
    result['schema_version'] = 'compositional-evidence-0.2'
    for c in result['claims']:
        extensions = {x['role']: x for x in c.pop('role_expansions')}
        c['roles'] = {}
        for role in ('actor', 'object', 'speaker'):
            expanded = deepcopy(c[role])
            if role in extensions:
                c[role] = deepcopy(extensions[role]['previous'])
            assessment = assess_role(c[role], result['tokens'])
            alternatives = []
            if role in extensions:
                alternatives.append({'span': expanded, 'attachment': 'unresolved',
                    'basis': 'parser_nominal_expansion', 'assessment': assess_role(expanded, result['tokens']),
                    'allowed_as_resolved_entity': False})
            c['roles'][role] = {'base_span': deepcopy(c[role]), 'assessment': assessment,
                'complement_candidates': alternatives, 'resolved_entity': unknown()}
        c['speaker_assessment'] = deepcopy(c['roles']['speaker']['assessment'])
        # Even nominal heads (History, a share order) do not establish a source type.
        c['speaker_assessment']['communicator_type'] = 'unverified'
        c['speaker_assessment']['verified_speaker'] = False
        for edge in c['attribution_chain']:
            edge['speaker_assessment'] = assess_role(edge['speaker'], result['tokens'])
            edge['speaker_assessment'].update(communicator_type='unverified', verified_speaker=False)
            edge['attachment'] = 'syntactic_only'
            edge['verified_attribution'] = False
            edge['factuality'] = 'unknown'
        c['relation_readiness'] = {'status': 'unresolved',
            'reasons': ['entity_identity_unverified', 'episode_unverified', 'predicate_semantics_unverified'],
            'may_auto_link_contract': False}
    return result


def extract(article, nlp):
    from eventx.v6.compositional_evidence import extract as previous
    return revise(previous(article, nlp))
