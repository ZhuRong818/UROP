"""Event-channel constraints for exploratory ranking, never link acceptance."""
import re
from eventx.v6.subject_retrieval_v02 import subjects

CHANNELS = [
    ('peace',r'peace deal|ceasefire',r'peace|ceasefire|negotiat|talks|agreement'),
    ('acquisition',r'acquisition|acquire|merge',r'acquisition|acquire|buyout|merg'),
    ('earnings',r'earnings call',r'earnings|quarterly results'),
    ('valuation',r'market cap|net worth',r'market cap|valuation|net worth'),
    ('price',r'reach\s+\$|hit\s+\$|close price',r'price|trades? at|trading at|rises? to|falls? to'),
    ('ranking',r'best AI|top AI',r'benchmark|leaderboard|rank|frontrunner|best AI|top AI'),
    ('tweet_count',r'tweets',r'tweets?|posts?'),
    ('inclusion',r'added to the',r'added to|inclusion|join.{0,30}index'),
    ('speech',r'\bsay\b',r'\bsays?\b|said|speech|press conference'),
]

def constraint(article,card):
    q=card['question'];text='\n'.join(article.get(k) or '' for k in ('headline','summary'))
    entries=subjects(card)
    names=sorted(set(e['name'] for e in entries))
    channel=next(((k,p) for k,c,p in CHANNELS if re.search(c,q,re.I)),None)
    result={'status':'abstain','reason':'unsupported_event_channel','evidence':[],
            'predictive_admitted':False,'channel':channel[0] if channel else None}
    if not channel or not names:return result
    # A single sentence must contain each required subject and the event relation.
    for field in ('headline','summary'):
        source=article.get(field) or ''
        for span in re.finditer(r'[^\n.!?]+',source):
            sentence=span.group()
            if not all(any(re.search(r'(?<!\w)'+re.escape(e['alias'])+r'(?!\w)',sentence,
                                    0 if e['case_sensitive'] else re.I)
                           for e in entries if e['name']==name) for name in names):continue
            cue=re.search(channel[1],sentence,re.I)
            if cue:
                result.update(status='event_channel_candidate',reason='same_sentence_subjects_and_channel',
                              evidence=[{'field':field,'start':span.start(),'end':span.end(),'quote':sentence}])
                return result
    result['reason']='subjects_or_relation_not_bound_in_sentence'
    return result
