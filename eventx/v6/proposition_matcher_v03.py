"""Development extensions: traceable aliases and bounded relation templates.

These yield hypotheses, not gold labels or predictive admission. All text remains
unaltered; aliases are matched with offsets into original article fields.
"""
import re
from eventx.v6.proposition_matcher_v02 import match as previous_match
from eventx.v6.proposition_matcher import specification, date_value, mention
from eventx.v6.contracts import utc


def aliases(name, kind):
    if not name:
        return []
    variants=[{'alias':name,'source_quote':name,'transformation':'exact','entity_type':kind}]
    if kind in {'company','market_cap','measurement','speech'}:
        short=re.sub(r',?\s+(?:Inc\.?|Corp\.?|Corporation|Ltd\.?)$','',name,flags=re.I)
        if short!=name and len(short.split())>=2:
            variants.append({'alias':short,'source_quote':name,'transformation':'legal_suffix_removal','entity_type':kind})
    if kind=='ai_ranking' and '-' in name:
        variants.append({'alias':name.replace('-',' '),'source_quote':name,
                         'transformation':'model_separator_normalization','entity_type':kind})
    return variants


def alias_hits(text,entries):
    hits=[]
    for entry in entries:
        for m in re.finditer(r'(?<!\w)'+re.escape(entry['alias'])+r'(?!\w)',text,re.I):
            hits.append({**entry,'quote':m.group(),'start':m.start(),'end':m.end(),
                         'identity_verified':False})
    return hits


def extension(card):
    q=card['question']
    # Each adapter has a subject plus an explicit metric/relation, never just topic.
    patterns=[
        ('market_cap',r"^Will (.+?)(?:'s|’s) market cap\b",'market cap'),
        ('net_worth',r'^Will (.+?) have a net worth\b','net worth'),
        ('music_sales',r'^Will (.+?) by (.+?) have .*?Pure Album Sales\b','pure album sales'),
        ('index_inclusion',r'^Will (.+?) be added to the (.+?) in\b','index inclusion'),
        ('peace_agreement',r'^(.+?) x (.+?) (?:permanent )?peace deal\b','peace deal'),
        ('announcement',r'^Will (.+?) announce that (.+?) by\b','announcement'),
    ]
    for kind,pattern,metric in patterns:
        m=re.search(pattern,q,re.I)
        if m:
            return {'kind':kind,'subjects':list(m.groups()),'metric':metric,
                    'source_quote':m.group(),'source_field':'question'}
    return None


def sentence_spans(text):
    # Split punctuation only at sentence boundaries, not decimal points.
    return [s.strip() for s in re.split(r'\n|;|(?<=[.!?])\s+(?=[A-Z])',text) if s.strip()]


def match(article,card):
    r=previous_match(article,card)
    r['version']='proposition-matcher-0.3'
    ext=extension(card);r['extension']=ext
    spec=specification(card)
    name=spec['subject'];kind=spec['type']
    if ext:name=ext['subjects'][0];kind=ext['kind']
    text='\n'.join(article.get(k) or '' for k in ('headline','summary'))
    entries=aliases(name,kind);r['alias_evidence']=entries;r['article_alias_hits']=alias_hits(text,entries)
    if card.get('subtitle_conflict'):return r
    if not ext:
        # A spelling variant is diagnostic evidence only, never silently substituted
        # into the old matcher or sufficient by itself to promote a candidate.
        if r['semantic_reason']=='subject_not_resolved' and r['article_alias_hits']:
            r['semantic_reason']='alias_found_predicate_binding_requires_adapter'
        return r
    def finish(status,reason,span=None):
        r.update(semantic_status=status,semantic_reason=reason,claim_span=span)
        return r
    if not r['article_alias_hits']:
        return finish('insufficient_evidence','extension_subject_not_in_supplied_text')
    spans=[s for s in sentence_spans(text) if alias_hits(s,entries)]
    spans=[s for s in spans if not re.search(r'\b(?:but|whereas|while)\b',s,re.I)]
    subject='(?:'+'|'.join(re.escape(a['alias']) for a in entries)+')'
    patterns={
        'market_cap':subject+r"(?:'s|’s)?\s+market cap(?:italization)?\s+(?:(?:is|was|fell to|rose to|reached|of|at)\s+)?\$\s*\d",
        'net_worth':subject+r"(?:'s|’s)?\s+net worth\s+(?:(?:is|was|fell to|rose to|reached|of|at)\s+)?\$\s*\d",
        'music_sales':subject+r'\s+by\s+'+(re.escape(ext['subjects'][1]) if len(ext['subjects'])>1 else r'(?!)')+r'\s+(?:sold|recorded|registered)\s+[\d,]+\s+pure album sales',
        'index_inclusion':subject+r'\s+(?:was |is |will be |was not |will not be )?(?:added|included|admitted)\s+(?:to|in)\s+(?:the )?'+(re.escape(ext['subjects'][1]) if len(ext['subjects'])>1 else r'(?!)'),
        'peace_agreement':subject+r'\s+and\s+'+(re.escape(ext['subjects'][1]) if len(ext['subjects'])>1 else r'(?!)')+r'\s+(?:signed|rejected|agreed to|announced)\s+(?:a |the )?(?:permanent )?peace deal',
        'announcement':subject+r'\s+announced that\s+'+(re.escape(ext['subjects'][1]) if len(ext['subjects'])>1 else r'(?!)'),
    }
    bound=[s for s in spans if re.search(patterns[kind],s,re.I)]
    if not bound:return finish('background','extension_subject_without_bound_relation')
    dates=spec['explicit_dates'];months=spec['explicit_months']
    for span in bound:
        if kind=='music_sales':
            # Both endpoints of a tracking week must be named, not merely the year.
            if dates and all(mention(span,d) for d in dates):
                return finish('direct_candidate','album_artist_sales_and_tracking_period',span)
        elif kind in {'market_cap','net_worth'}:
            # IPO-month terminal prices are not current cap observations. Require
            # explicit observation dates; never infer IPO timing or calendar from ID.
            if dates and len(dates)==1 and mention(span,dates[0]):
                return finish('direct_candidate','typed_valuation_measurement_and_date',span)
        elif kind=='index_inclusion':
            quarters=re.findall(r'\bQ[1-4]\s+20\d{2}\b',card['question'],re.I)
            if len(quarters)==1 and mention(span,quarters[0]):
                return finish('direct_candidate','company_index_action_and_quarter',span)
        else:
            if len(dates)==1 and mention(span,dates[0]):
                return finish('direct_candidate','bound_event_relation_and_date',span)
    return finish('insufficient_evidence','extension_relation_found_period_unproven')
