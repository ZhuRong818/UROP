"""Evidence-span contract routing 0.1. Parsing hypotheses, never accepted links."""
import re

# Specific patterns precede broad thresholds; no inference from market IDs.
ROUTES = [
    ('sports', r'\b(?:goals|three pointers|World Cup|Playoffs|semifinals)\b'),
    ('music_ranking', r'\bBillboard\b'),
    ('music_sales', r'\b(?:Album Sales|Album Equivalent Units)\b'),
    ('ai_ranking', r'\b(?:best AI|top AI|Best AI)\b'),
    ('leadership', r'\b(?:Director of National Intelligence|confirmed|Acting DNI)\b'),
    ('speech', r'\bsay during\b'),
    ('tweet_count', r'\btweets\b'),
    ('corporate_action', r'\b(?:acquire|merge|added to the S&P)\b'),
    ('measurement', r'\breport\b'),
    ('price_threshold', r'\b(?:reach|market cap|net worth|hit)\b'),
    ('event_deadline', r'\b(?:announce|peace deal|ceasefire)\b'),
]
MONTH = r'(?:Jan(?:uary)?|Feb(?:ruary)?|Mar(?:ch)?|Apr(?:il)?|May|Jun(?:e)?|Jul(?:y)?|Aug(?:ust)?|Sep(?:tember)?|Oct(?:ober)?|Nov(?:ember)?|Dec(?:ember)?)'
DATE = rf'\b(?:{MONTH}\s+\d{{1,2}},?\s+20\d{{2}}|{MONTH}\s+20\d{{2}}|Q[1-4]\s+20\d{{2}}|20\d{{2}}-\d{{2}}-\d{{2}})\b'


def evidence(pattern, sources):
    return [{'quote':m.group(), 'source_field':s['field'], 'start':m.start(), 'end':m.end()}
            for s in sources for m in re.finditer(pattern,s['text'],re.I)]


def parse(card):
    sources=[{'field':'question','text':card['question']},
             {'field':'yes_subtitle','text':card.get('yes_subtitle') or ''}]
    sources += [{'field':f'rule_evidence[{i}]','text':r['text'],'provenance':r}
                for i,r in enumerate(card.get('rule_evidence',[]))]
    routes=[(name,evidence(pattern,sources[:1])) for name,pattern in ROUTES]
    matches=[name for name,hits in routes if hits]
    kind=matches[0] if matches else 'unknown'
    subjects=[]
    for pattern in (r'^Will (.+?) (?:report|have|post|reach|be added|be #?1|record|announce)\b',
                    r'^(.+?) wins by\b'):
        m=re.search(pattern,card['question'],re.I)
        if m: subjects.append({'quote':m[1], 'source_field':'question', 'start':m.start(1),'end':m.end(1)})
    fields={
        'subject_mentions':subjects,
        'outcome_candidate':evidence(r'.+',sources[1:2]),
        'predicate':next((hits for name,hits in routes if name==kind),[]),
        'time_mentions':evidence(DATE,sources),
        'threshold_mentions':evidence(r'(?:\$\s*\d[\d,.]*(?:\s*[TBMK])?|\b(?:above|over|more than)\s+\d[\d,.]*)',sources),
        'ranking_source_mentions':evidence(r'\b(?:Billboard Hot 100|Luminate|Arena|Datacurve|DeepSWE)\b',sources),
        'deadline_relation':evidence(r'\b(?:before|by|during|at the end of|at market close)\b',sources),
    }
    return {'version':'multitype-router-0.1','contract_id':card['contract_id'],
            'type_hypothesis':kind,'matched_type_patterns':matches,'fields':fields,
            'sources':sources,'subtitle_conflict':bool(card.get('subtitle_conflict')),
            'unknowns':['canonical_entity_identity','normalized_event_interval','predicate_entailment','historical_validity'],
            'predictive_admitted':False}


def compare(article, contract):
    """Lexical evidence inspection only; no co-occurrence-as-relevance acceptance."""
    text='\n'.join(article.get(k) or '' for k in ('headline','summary'))
    mentions=[]
    for subject in contract['fields']['subject_mentions']:
        for m in re.finditer(r'(?<!\w)'+re.escape(subject['quote'])+r'(?!\w)',text,re.I):
            mentions.append({'quote':m.group(),'start':m.start(),'end':m.end()})
    return {'article_subject_mentions':mentions,
            'article_time_mentions':evidence(DATE,[{'field':'article_text','text':text}]),
            'status':'abstain','reason':'semantic_binding_and_availability_uncertified',
            'supported_links':[],'predictive_admitted':False}
