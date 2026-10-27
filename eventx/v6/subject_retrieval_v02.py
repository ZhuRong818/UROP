"""Evidence-preserving subject extensions and context checks; development only."""
import re
from eventx.v6.subject_retrieval import subjects as previous_subjects
from eventx.v6.subject_context import context_gate as previous_gate


def subjects(card):
    if card.get('subtitle_conflict'):return []
    result=previous_subjects(card)
    q=card['question']
    if re.match(r'^(?:yes|no)\s',q,re.I):return result
    patterns=[
        (r'^Will (.+?) (?:say|play for|leave|resign|retire|defeat|beat)\b','named_actor'),
        (r'^.+?: Will (.+?) finish (?:top|in)\b','sports_participant'),
        (r'^Will the margin of victory for (.+?) in\b','election_candidate'),
        (r'^Will (?:the )?(.+?) (?:close price|compute per hour price)\b','priced_asset'),
    ]
    for pattern,kind in patterns:
        m=re.search(pattern,q,re.I)
        if not m:continue
        name=m[1]
        if not 2<=len(name)<=80 or re.match(r'^(?:any|it|there|a |an )\b',name,re.I):continue
        result.append({'name':name,'field':'question','start':m.start(1),'end':m.end(1),
                       'kind':kind,'alias':name,'source_quote':name,'transformation':'exact',
                       'entity_type':kind,'case_sensitive':len(name)<=3})
    return result


def context_gate(article,card,evidence):
    original=previous_gate(article,card,evidence)
    if original!='subject_context_candidate':return original
    q=card['question'];text='\n'.join(article.get(k) or '' for k in ('headline','summary'))
    extra=[
        (r'\bwin on \d{4}-|\bplay for\b|finish top|goals|1st Half',r'football|soccer|basketball|golf|NBA|FIFA|World Cup|match|tournament|team|roster'),
        (r'Spotify|Top Songs|Billboard|album',r'Spotify|song|music|album|rapper|singer|Billboard'),
    ]
    for contract_pattern,article_pattern in extra:
        if re.search(contract_pattern,q,re.I) and not re.search(article_pattern,text,re.I):
            return 'reject_missing_specific_domain_context'
    return original


def missing_class(card):
    q=card['question']
    if card.get('subtitle_conflict'):return 'conflicting_subtitles'
    if re.match(r'^(?:yes|no)\s',q,re.I):return 'compound_contract_requires_leg_resolution'
    if re.search(r'^Will (?:over|under) .*goals',q,re.I):return 'fixture_identity_missing_from_question'
    if re.match(r'^(?:Who|What|Which)\b',q,re.I):return 'answer_identity_requires_typed_subtitle'
    return 'unsupported_subject_structure'
