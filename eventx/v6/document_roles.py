"""Bounded document-role hypotheses v0.2; not a general coreference resolver."""
import re
from eventx.v6.field_aware import fields as old_fields, hypothesis as old_hypothesis
from eventx.v6.clean_speech import clean


def fields(card):
    f = old_fields(card)
    f['version'] = 'document-roles-0.2'
    m = re.search(r'^Will (.+?) reach the (?:final|semifinals?) at the .*World Cup', card['question'], re.I)
    if m:
        f.update(entity_type_hypothesis='sports_team', subject=m[1], predicate='reach_stage')
    return f


def spans(article):
    for field in ('headline', 'summary'):
        for m in re.finditer(r'[^\n.!?]+', article.get(field) or ''):
            yield {'field': field, 'start': m.start(), 'end': m.end(), 'quote': m.group()}


def hypothesis(article, f):
    a, masked = clean(article)
    result = old_hypothesis(a, f)
    result['masked'] = masked
    kind, subject = f['entity_type_hypothesis'], f['subject']
    if kind not in ('sports_team', 'asset_price'):
        return result
    result.update(status='abstain', reason='document_role_unverified', evidence=[],
                  contract_specificity='unverified')
    ss = list(spans(a))
    if kind == 'asset_price':
        alias = r'(?:bitcoin|BTC)' if subject.lower() == 'bitcoin' else r'(?:ethereum|ether|ETH)'
        # Require local asset-object or asset-property bindings, not any buy/price
        # elsewhere in a sentence about a stock. Still contextual, never measurement.
        patterns = [r'\b(?:sell(?:s|ing)?|sold|buy(?:s|ing)?|bought|purchas(?:e|es|ed))\s+(?:some of (?:its|their)\s+)?'+alias+r'\b',
                    r'\b'+alias+r"(?:['’]s)?\s+(?:holdings|price|ETF|trust|bet|redemptions)\b",
                    r'\b'+alias+r'\s+(?:itself\s+)?(?:has\s+)?(?:fallen|rose|rises|falls|rallied|trades)\b']
        for s in ss:
            if any(re.search(p, s['quote'], re.I) for p in patterns):
                result.update(status='asset_context_hypothesis', reason='local_asset_role_binding',
                              evidence=[s], contract_specificity='shared_context_only')
                return result
        return result
    name = r'(?<!\w)'+re.escape(subject)+r'(?!\w)'
    # Context may cross headline/summary only when a target-team action/role is
    # explicit. Generic country mentions never inherit the document sports cue.
    contexts = [s for s in ss if re.search(r'\bWorld Cup\b|\bFIFA\b|\bfootball\b|\bsoccer\b', s['quote'], re.I)]
    roles = [name+r"(?:['’]s)?\s+(?:(?:national|football|soccer)\s+)?team\b",
             name+r"(?:['’]s)?\s+(?:(?:late|dramatic|narrow)\s+)?(?:win|victory|defeat|loss)\b",
             name+r'\s+(?:wins|won|beats|beat|defeats|defeated|qualifies|qualified|scores|scored)\b']
    for s in ss:
        if not any(re.search(p, s['quote'], re.I) for p in roles):
            continue
        if contexts:
            evidence = [s] + [c for c in contexts[:1] if c != s]
            result.update(status='event_context_hypothesis', reason='explicit_team_role_with_document_sport_context',
                          evidence=evidence, contract_specificity='shared_context_only')
            return result
    return result
