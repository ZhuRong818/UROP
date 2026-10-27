"""Bounded lexical measurement extractor 0.1; development only, no certificates.

Only explicit year-qualified quarters and registered typed names are supported.
Outputs are quoted hypotheses, not verified semantic facts or predictive admission.
"""
import re
from dataclasses import asdict
from eventx.v6.selective_vnext import Field

VERSION = 'measurement-extractor-0.1'
METRICS = {'revenue': r'\brevenue\b', 'skier_visits': r'\bskier visits\b',
           'earnings': r'\bearnings\b'}


def collapse(hits):
    values = {value for value, quote in hits}
    if not values:
        return Field('', '', 'unknown')
    if len(values) > 1:
        return Field('', '', 'conflicting')
    value, quote = hits[0]
    return Field(value, quote)


def extract(text, registry):
    if not isinstance(text, str):
        raise ValueError('Text required')
    entities = []
    for canonical, aliases in registry.items():
        if ':' not in canonical or not aliases or any(not alias.strip() for alias in aliases):
            raise ValueError('Typed entity and nonempty aliases required')
        for alias in aliases:
            for m in re.finditer(r'(?<!\w)' + re.escape(alias) + r'(?!\w)', text, re.I):
                entities.append((canonical, m.group()))
    metrics = [(name, m.group()) for name, pattern in METRICS.items()
               for m in re.finditer(pattern, text, re.I)]
    periods = [(f'{m[2]}Q{m[1]}', m.group())
               for m in re.finditer(r'\bQ([1-4])\s+(20\d{2})\b', text, re.I)]
    fields = {'entity': collapse(entities), 'metric': collapse(metrics), 'period': collapse(periods)}
    # No canonical unit or calendar/fiscal conversion is guessed.
    fields['predicate'] = Field('measurement', fields['metric'].quote, fields['metric'].status)
    units = [(m.group().upper(), m.group()) for m in re.finditer(r'\b(?:USD|EUR|GBP)\b', text)]
    fields['unit'] = collapse(units)
    # Claim span must contain all three pieces locally. Reject complex multi-clause
    # text rather than treating global co-occurrence as an assertion.
    claim = None
    if all(fields[k].status == 'known' for k in ('entity','metric','period')):
        for span in re.split(r'[\n;.!?]', text):
            if (all(fields[k].quote in span for k in ('entity','metric','period'))
                    and not re.search(r'\b(?:but|while|whereas|and)\b', span, re.I)):
                claim = span.strip()
                break
    return {'version': VERSION, 'fields': {k:asdict(v) for k,v in fields.items()},
            'claim_span': claim, 'certificate': None, 'predictive_admitted': False}


def assess(article_text, contract_text, registry):
    a, c = extract(article_text, registry), extract(contract_text, registry)
    status, reason = 'insufficient_evidence', 'unknown_or_conflicting_fields'
    af, cf = a['fields'], c['fields']
    for key in ('entity','metric','period'):
        if af[key]['status']==cf[key]['status']=='known' and af[key]['value']!=cf[key]['value']:
            status, reason = 'unrelated_candidate', key+'_mismatch'
            break
    else:
        if all(af[k]['status']==cf[k]['status']=='known' for k in ('entity','metric','period')):
            if a['claim_span'] and c['claim_span']:
                status, reason = 'direct_candidate', 'same_period_measurement_lexical_support'
            else:
                reason = 'claim_binding_not_established'
        elif (af['entity']['status']==cf['entity']['status']=='known'
              and af['entity']['value']==cf['entity']['value']
              and af['metric']['status']=='unknown' and cf['metric']['status']=='known'):
            status, reason = 'background_candidate', 'entity_only_no_measurement_evidence'
    return {'article':a,'contract':c,'semantic_status':status,'reason':reason,
            'supported_links':[], 'predictive_admitted':False,
            'acceptance_status':'not_validated_no_predictive_admission'}
