"""Evidence-span claim records. Bounded clause grammar, not a relevance classifier.

No contract names/headline exceptions or automatic identity/episode certification.
All parsed roles are hypotheses; unsupported clauses retain explicit unknowns.
"""
import re
from eventx.v6.clean_speech import clean

VERSION = 'structured-evidence-0.1'
ACTION = r'sold|sells|sell|purchased|purchases|bought|buys|acquired|acquires|hosts|hosted|secures|secured|won|wins|qualified|qualifies|falls|fell|rises|rose'
STANCE = r'expects?|expected|predicts?|predicted|argues?|argued|believes?|believed|says|said|presents?|presented'
PASSIVE = re.compile(r'^(?P<object>.+?)\s+(?:was|were|is|are)\s+(?P<predicate>sold|purchased|bought|acquired|hosted)\s+by\s+(?P<actor>.+)$', re.I)
CLAUSE = re.compile(r'^(?P<actor>.+?)\s+(?P<predicate>'+STANCE+'|'+ACTION+r')\b\s*(?P<object>.*)$', re.I)


def unknown():
    return {'status': 'unknown', 'value': None, 'evidence': []}


def value(text, field, start, end, normalized=None):
    quote = text[start:end]
    return {'status': 'candidate', 'value': normalized if normalized is not None else quote,
            'evidence': [{'field': field, 'start': start, 'end': end, 'quote': quote}]}


def extract(article):
    cleaned, masked = clean(article)
    claims = []
    for field in ('headline', 'summary'):
        text = cleaned.get(field) or ''
        # Decimal-safe splitting; no HTML normalization that would corrupt offsets.
        for seg in re.finditer(r'[^\n]+?(?:[.!?](?=\s|$)|$)', text):
            lo, hi = seg.start(), seg.end()
            while lo < hi and text[lo].isspace(): lo += 1
            while hi > lo and (text[hi-1].isspace() or text[hi-1] in '.!?'): hi -= 1
            if lo == hi: continue
            sentence = text[lo:hi]
            record = {k: unknown() for k in ('actor', 'speaker', 'object', 'predicate', 'proposition', 'epistemic_status', 'polarity', 'voice')}
            record.update(evidence=value(text, field, lo, hi), time_mentions=[], stage_mentions=[],
                          entity_identity='unknown', episode_identity='unknown',
                          predictive_admitted=False, settlement_evidence=False)
            match = PASSIVE.match(sentence)
            passive = match is not None
            match = match or CLAUSE.match(sentence)
            if match:
                for k in ('actor', 'object', 'predicate'):
                    if match[k]:
                        record[k] = value(text, field, lo+match.start(k), lo+match.end(k))
                record['voice'] = value(text, field, lo, hi, 'passive' if passive else 'active')
                stance = bool(re.fullmatch(STANCE, match['predicate'], re.I))
                if stance:
                    record['speaker'] = record['actor']
                    record['actor'] = unknown()  # speaker is not the actor in embedded proposition
                    record['proposition'] = record['object']
                    record['object'] = unknown()  # whole complement is not a canonical object
                else:
                    record['proposition'] = value(text, field, lo, hi)
                status = 'attributed_claim' if stance else 'reported_action_or_state'
                if re.search(r'\bexpect|\bpredict', match['predicate'], re.I): status = 'forecast'
                elif re.search(r'\bargu|\bbeliev', match['predicate'], re.I): status = 'opinion'
                record['epistemic_status'] = value(text, field, lo+match.start('predicate'), lo+match.end('predicate'), status)
            # Lexical markers are evidence candidates even when grammatical roles fail.
            # Do not infer an occurrence merely from an action verb or absent negation.
            for m in re.finditer(r'\b(?:19|20)\d{2}\b', sentence):
                record['time_mentions'].append(value(text, field, lo+m.start(), lo+m.end()))
            for m in re.finditer(r'\b(?:quarterfinals?|semifinals?|finals?|knockout|group stage|training)\b', sentence, re.I):
                record['stage_mentions'].append(value(text, field, lo+m.start(), lo+m.end()))
            if re.search(r'\bnot\b|\bnever\b|\bno\b', sentence, re.I):
                record['polarity'] = value(text, field, lo, hi, 'negation_present_scope_unknown')
            claims.append(record)
    return {'schema_version': VERSION, 'claims': claims, 'masked': masked,
            'predictive_admitted': False}


def compare_contract(extraction, question):
    # Diagnostic only: mention agreement is neither date binding nor eligibility.
    article_years = sorted({v['value'] for c in extraction['claims'] for v in c['time_mentions']})
    question_years = sorted(set(re.findall(r'\b(?:19|20)\d{2}\b', question)))
    state = 'unknown'
    if article_years and question_years:
        state = 'overlapping_mentions' if set(article_years) & set(question_years) else 'disjoint_mentions'
    return {'article_year_mentions': article_years, 'contract_year_mentions': question_years,
            'year_mention_relation': state, 'episode_identity': 'unknown',
            'relevance': 'unassessed', 'predictive_admitted': False}


def validate_spans(extraction, article):
    def visit(obj):
        if isinstance(obj, dict):
            if {'field', 'start', 'end', 'quote'} <= obj.keys():
                assert (article.get(obj['field']) or '')[obj['start']:obj['end']] == obj['quote']
            for v in obj.values(): visit(v)
        elif isinstance(obj, list):
            for v in obj: visit(v)
    visit(extraction)
