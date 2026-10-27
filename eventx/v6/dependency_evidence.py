"""spaCy dependency candidates through the structured-evidence interface.

Syntactic roles are hypotheses, not semantic identities or link acceptance.
"""
import re
from eventx.v6.clean_speech import clean
from eventx.v6.structured_evidence import unknown, value

SPEECH = {'say', 'state', 'report', 'argue', 'believe', 'expect', 'predict', 'forecast', 'claim'}


def extract(article, nlp):
    cleaned, masked = clean(article)
    claims, tokens = [], []
    for field in ('headline', 'summary'):
        text = cleaned.get(field) or ''
        doc = nlp(text)
        chunks = {c.root.i: c for c in doc.noun_chunks}
        def span(t, subtree=False):
            if subtree:
                members = list(t.subtree)
                return value(text, field, min(x.idx for x in members), max(x.idx+len(x) for x in members))
            c = chunks.get(t.i)
            return value(text, field, c.start_char, c.end_char) if c is not None else value(text, field, t.idx, t.idx+len(t))
        for t in doc:
            if t.is_space: continue
            tokens.append({'field': field, 'start': t.idx, 'end': t.idx+len(t), 'quote': t.text,
                           'pos': t.pos_, 'dep': t.dep_, 'lemma': t.lemma_, 'head_start': t.head.idx})
            if t.pos_ != 'VERB': continue
            children = list(t.children)
            r = {k: unknown() for k in ('actor', 'speaker', 'object', 'predicate', 'proposition', 'epistemic_status', 'polarity', 'voice')}
            r.update(evidence=span(t, True), predicate=value(text, field, t.idx, t.idx+len(t)),
                     time_mentions=[], stage_mentions=[], entity_identity='unknown', episode_identity='unknown',
                     predictive_admitted=False, settlement_evidence=False,
                     attachment={'predicate_start': t.idx, 'head_start': t.head.idx, 'dependency': t.dep_})
            subject = next((c for c in children if c.dep_ in ('nsubj', 'nsubjpass')), None)
            passive = any(c.dep_ in ('auxpass', 'nsubjpass') for c in children)
            obj = next((c for c in children if c.dep_ in ('dobj', 'obj', 'attr')), None)
            agent = next((c for c in children if c.dep_ == 'agent'), None)
            agent_obj = next((c for c in agent.children if c.dep_ == 'pobj'), None) if agent is not None else None
            if passive:
                if subject is not None: r['object'] = span(subject)
                if agent_obj is not None: r['actor'] = span(agent_obj)
            else:
                if subject is not None: r['actor'] = span(subject)
                if obj is not None: r['object'] = span(obj)
            r['voice'] = value(text, field, t.idx, t.idx+len(t), 'passive' if passive else 'active')
            complement = next((c for c in children if c.dep_ in ('ccomp', 'xcomp')), None)
            if t.lemma_.lower() in SPEECH:
                r['speaker'], r['actor'] = r['actor'], unknown()
                if complement is not None: r['proposition'] = span(complement, True)
                state = 'forecast' if t.lemma_.lower() in {'expect','predict','forecast'} else 'opinion' if t.lemma_.lower() in {'argue','believe'} else 'attributed_claim'
            else:
                r['proposition'] = span(t, True)
                # Embedded predicates do not automatically become reported facts.
                state = 'embedded_status_unknown' if t.dep_ in ('ccomp','xcomp','advcl','acl','relcl') else 'assertion_status_unknown'
            r['epistemic_status'] = value(text, field, t.idx, t.idx+len(t), state)
            neg = [c for c in children if c.dep_ == 'neg']
            if neg: r['polarity'] = span(neg[0]); r['polarity']['value'] = 'syntactic_negation'
            for x in t.subtree:
                if re.fullmatch(r'(?:19|20)\d{2}', x.text): r['time_mentions'].append(span(x))
                if x.lemma_.lower() in {'quarterfinal','semifinal','final','knockout','training'}:
                    r['stage_mentions'].append(span(x))
            claims.append(r)
    return {'schema_version': 'dependency-evidence-0.1', 'claims': claims, 'tokens': tokens,
            'masked': masked, 'predictive_admitted': False}
