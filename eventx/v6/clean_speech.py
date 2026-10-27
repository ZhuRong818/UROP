"""Pre-ranking text masking and conservative speech binding. No admission."""
import re
from eventx.v6.relation_candidates import constraint

def clean(article):
    result=dict(article);excluded=[]
    for field in ('headline','summary'):
        text=article.get(field) or ''
        m=re.search(r'Most Read from|Related Articles|Recommended Stories',text,re.I)
        if m:
            excluded.append({'field':field,'start':m.start(),'end':len(text),'reason':'sidebar_tail'})
            result[field]=text[:m.start()]+' '*(len(text)-m.start())
    return result,excluded

def prepare(article,card):
    cleaned,excluded=clean(article)
    r=constraint(cleaned,card);r['excluded_spans']=excluded
    if r['status']!='event_channel_candidate':return cleaned,r
    q=card['question']
    m=re.search(r'^(?:Will|What will) (.+?) say\b',q,re.I)
    if not m:return cleaned,r
    speaker=m[1]
    occasion=re.search(r'\bduring (.+?)[?]?$',q,re.I)
    # Literal occasion only. Relative "next" occasion requires separate identity evidence.
    if occasion and re.search(r'\bnext\b',occasion[1],re.I):
        r.update(status='abstain',reason='relative_speech_occasion_unresolved');return cleaned,r
    usable=[]
    for e in r['evidence']:
        s=e['quote']
        if not re.search(r'(?<!\w)'+re.escape(speaker)+r'\s+(?:said|says|stated|announced)\b',s,re.I):continue
        if occasion and occasion[1].rstrip('?') .casefold() not in s.casefold():continue
        usable.append(e)
    if not usable:r.update(status='abstain',reason='speech_speaker_or_occasion_unbound',evidence=[])
    else:r['evidence']=usable
    return cleaned,r
