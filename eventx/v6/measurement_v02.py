"""Development adapter 0.2: provenance-preserving company aliases/quarters.

Never creates source certificates or claims that lexical aliases are verified.
Earlier extractor/release remains unchanged.
"""
import re
from dataclasses import asdict
from eventx.v6.measurement_extractor import extract as legacy_extract, collapse


def company_registry(cards):
    registry, evidence = {}, []
    for card in cards:
        question = card['question']
        match = re.match(r'^Will (.+?) report\b', question)
        if not match:
            continue
        name = match[1].strip()
        key = 'company:' + re.sub(r'\W+', '_', name.casefold()).strip('_')
        short = re.sub(r',?\s+(?:Inc\.?|Corporation|Corp\.?|Ltd\.?)$', '', name, flags=re.I)
        aliases = {name}
        # Multiword-only suffix removal; never infer stock symbols or abbreviations.
        if len(short.split()) >= 2:
            aliases.add(short)
        registry[key] = sorted(set(registry.get(key, [])) | aliases)
        evidence.append({'entity': key, 'aliases': sorted(aliases),
                         'source_contract_id': card['contract_id'], 'source_field': 'question',
                         'quote': name, 'method': 'explicit_report_subject_and_legal_suffix_normalization',
                         'independently_verified': False})
    return registry, evidence


def extract(text, registry):
    result = legacy_extract(text, registry)
    hits = []
    for m in re.finditer(r'\bQ([1-4])\s+(20\d{2})\b', text, re.I):
        hits.append((f'{m[2]}Q{m[1]}', m.group()))
    numbers = {'first':'1', 'second':'2', 'third':'3', 'fourth':'4'}
    for m in re.finditer(r'\b(first|second|third|fourth)[ -]quarter\s+(?:of\s+)?(20\d{2})\b',text,re.I):
        hits.append((f'{m[2]}Q{numbers[m[1].lower()]}',m.group()))
    result['fields']['period'] = asdict(collapse(hits))
    result['version'] = 'measurement-extractor-0.2'
    # Dots in company legal suffixes must not sever the claim. Keep original spans.
    boundaries = [0]
    for m in re.finditer(r'[\n;!?]|\.(?=\s|$)', text):
        if m.group()=='.' and re.search(r'\b(?:Inc|Corp|Ltd)$',text[:m.start()],re.I):
            continue
        boundaries.append(m.end())
    boundaries.append(len(text))
    result['claim_span'] = None
    for start,end in zip(boundaries,boundaries[1:]):
        span=text[start:end].strip()
        if (all(result['fields'][k]['status']=='known' and result['fields'][k]['quote'] in span
                for k in ('entity','metric','period'))
                and not re.search(r'\b(?:but|while|whereas|and)\b',span,re.I)):
            result['claim_span']=span
            break
    result['period_basis']='fiscal' if re.search(r'\bfiscal\b',text,re.I) else 'unspecified'
    return result


def assess_card(article, card, registry):
    text='\n'.join(article.get(k) or '' for k in ('headline','summary'))
    sources=[{'field':'question','text':card['question']},
             {'field':'yes_subtitle','text':card.get('yes_subtitle') or ''}]
    sources += [{'field':f'rule_evidence[{i}]','text':e['text'],'provenance':e}
                for i,e in enumerate(card.get('rule_evidence',[]))]
    contract_text='\n'.join(s['text'] for s in sources)
    a,c=extract(text,registry),extract(contract_text,registry)
    status,reason='insufficient_evidence','missing_or_conflicting_semantics'
    if card.get('subtitle_conflict'):
        reason='conflicting_subtitles'
    elif not re.match(r'^Will .+? report\b',card['question']):
        reason='unsupported_contract_grammar'
    else:
        for k in ('entity','metric','period'):
            x,y=a['fields'][k],c['fields'][k]
            if x['status']==y['status']=='known' and x['value']!=y['value']:
                status,reason='mismatch_candidate',k+'_mismatch'
                break
        else:
            if a['claim_span'] and c['claim_span']:
                status,reason='direct_candidate','same_period_measurement_lexical_support_only'
            elif a['fields']['entity']['status']==c['fields']['entity']['status']=='known':
                if a['fields']['metric']['status']=='unknown':
                    status,reason='background_candidate','entity_only'
    return {'article_extraction':a,'contract_extraction':c,'contract_source_fields':sources,
            'semantic_status':status,'reason':reason,'predictive_admitted':False,
            'supported_links':[], 'period_equivalence_certified':False}
