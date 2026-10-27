"""Development-only field-aware hypotheses. Never certifies a link or time window."""
import math
import re
from eventx.v6.clean_speech import clean

VERSION = 'field-aware-0.1'
EXCLUSION = r'\bnot count|\bexclud|\bdoes not|\bwill not|\bdo not|\botherwise|\bunless'
BOILERPLATE = r'resolution source|credible reporting|source agenc|binance|trading pair|candle|early access|official statistics'


def fields(card):
    spans = []
    for i, evidence in enumerate(card.get('recovered_rule_evidence', [])):
        text = evidence['text']
        for m in re.finditer(r'[^\n.!?]+[.!?]?', text):
            quote = m.group()
            role = ('exclusion' if re.search(EXCLUSION, quote, re.I) else
                    'source_boilerplate' if re.search(BOILERPLATE, quote, re.I) else
                    'operative_candidate' if re.search(r'resolv|\bif\b|\bmust\b', quote, re.I) else
                    'unclassified')
            spans.append({'rule_index': i, 'start': m.start(), 'end': m.end(),
                          'quote': quote, 'role': role, 'source': evidence})
    q = card['question']
    speech = re.search(r'^Will (.+?) say ["“](.+?)["”]', q, re.I)
    sport = re.search(r'^Will (.+?) win (?:the .*World Cup|on \d{4}-\d{2}-\d{2})', q, re.I)
    asset = re.search(r'\b(Bitcoin|Ethereum|Ether)\b', q, re.I)
    kind, subject, predicate = 'unknown', None, None
    if speech:
        kind, subject, predicate = 'person_utterance', speech[1], speech[2]
    elif sport:
        kind, subject, predicate = 'sports_team', sport[1], 'win'
    elif asset and re.search(r'\breach\b|\bhit\b', q, re.I):
        kind, subject, predicate = 'asset_price', asset[1], 'price'
    return {'version': VERSION, 'contract_id': card['contract_id'], 'question': q,
            'yes_subtitle': card.get('yes_subtitle'), 'entity_type_hypothesis': kind,
            'subject': subject, 'predicate': predicate, 'rule_spans': spans,
            'training_admissible': False, 'pit_certificate': None}


def query(f):
    # Intentionally no rule prose until extracted propositions can be validated.
    # Rules remain available as evidence and negative constraints, not lexical mass.
    return '\n'.join(x for x in (f['question'], f.get('yes_subtitle')) if x)


def hypothesis(article, f):
    article, masked = clean(article)
    result = {'status': 'abstain', 'reason': 'unsupported_typed_adapter',
              'evidence': [], 'masked': masked, 'predictive_admitted': False,
              'settlement_evidence': False, 'contract_specificity': 'unverified'}
    kind, subject = f['entity_type_hypothesis'], f['subject']
    if not subject:
        return result
    alias = re.escape(subject)
    if kind == 'asset_price':
        alias = r'bitcoin|BTC' if subject.lower() == 'bitcoin' else r'ethereum|ether|ETH'
    for field in ('headline', 'summary'):
        for m in re.finditer(r'[^\n.!?]+', article.get(field) or ''):
            s = m.group()
            if not re.search(r'(?<!\w)(?:' + alias + r')(?!\w)', s, re.I):
                continue
            result['reason'] = 'subject_present_relation_unverified'
            if kind == 'person_utterance':
                # Word presence is necessary, not sufficient: do not certify speaker binding.
                result['reason'] = ('utterance_binding_unverified' if re.search(
                    r'(?<!\w)' + re.escape(f['predicate']) + r'(?!\w)', s, re.I)
                    else 'target_utterance_absent')
                continue
            if kind == 'sports_team':
                cue = r'world cup|football|soccer|FIFA|goal|knockout|match|tournament'
                status = 'event_context_hypothesis'
            else:
                cue = r'\bprice|\bsell|\bsells|\bsold|\bbuy|holdings|redemption|\bETF\b|\bbet\b|\btrade|\btrading|\brall|\bfall|\bris'
                status = 'asset_context_hypothesis'
            if not re.search(cue, s, re.I):
                continue
            result.update(status=status, reason='typed_subject_and_context_cue',
                          contract_specificity='shared_context_only',
                          evidence=[{'field': field, 'start': m.start(), 'end': m.end(), 'quote': s}])
            return result
    return result


def top_set(rows, key, tolerance=1e-12):
    valid = [r for r in rows if r.get(key) is not None and math.isfinite(r[key])]
    if not valid:
        return []
    best = max(r[key] for r in valid)
    return sorted(r['contract_id'] for r in valid if best - r[key] <= tolerance)
