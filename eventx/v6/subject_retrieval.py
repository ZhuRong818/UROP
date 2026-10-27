"""Subject-first development retrieval, never relevance or source certification."""
import re
from eventx.v6.proposition_matcher_v03 import aliases, extension
from eventx.v6.proposition_matcher import specification

VERSION = 'subject-retrieval-0.1'


def subjects(card):
    q=card['question']; found=[]
    def add(name,field,kind):
        source=q if field=='question' else card.get(field) or ''
        start=source.find(name)
        if start<0 or not 2<=len(name)<=100:return
        if re.match(r'^(?:any|a |an |over|under|above|below|the maximum|the minimum)',name,re.I):return
        found.append({'name':name,'field':field,'start':start,'end':start+len(name),'kind':kind})
    ext=extension(card)
    if ext:
        for name in ext['subjects'][:1 if ext['kind']=='announcement' else None]:add(name,'question',ext['kind'])
    patterns=[
        (r'^What will (.+?) say during','company'),
        (r'^Will (.+?) report\b','company'),
        (r'^Will (.+?) by (.+?) have .*?(?:Album Sales|Album Equivalent Units)','music'),
        (r'^Will (?:the )?(.+?) (?:win|qualify|score|record|perform|announce|post|reach|hit|hike|cut|be confirmed|be out|be added|have|be #?\d)\b','subject'),
        (r'^(.+?) wins by\b','sports'),
    ]
    for pattern,kind in patterns:
        m=re.search(pattern,q,re.I)
        if m:
            for name in m.groups():add(name,'question',kind)
            break
    spec=specification(card)
    if spec['subject']:add(spec['subject'],spec['subject_source_field'],spec['type'])
    unique={}
    for item in found:
        for alias in aliases(item['name'],item['kind']):
            value=alias['alias']
            # Case-sensitive matching for short abbreviations; no surname/ticker invention.
            key=(value.casefold(),item['field'])
            unique[key]={**item,**alias,'case_sensitive':len(value)<=3}
    return list(unique.values())


def build_registry(cards):
    return {c['contract_id']:subjects(c) if not c.get('subtitle_conflict') else [] for c in cards}


def retrieve(article,registry):
    result={}
    # Cache identical alias searches across threshold variants of a contract.
    cache={}
    for cid,entries in registry.items():
        evidence=[]
        for entry in entries:
            key=(entry['alias'],entry['case_sensitive'])
            if key not in cache:
                pattern=r'(?<!\w)'+re.escape(entry['alias'])+r'(?!\w)'
                cache[key]=[{'article_field':field,'quote':m.group(),'start':m.start(),'end':m.end()}
                            for field in ('headline','summary')
                            for m in re.finditer(pattern,article.get(field) or '',0 if entry['case_sensitive'] else re.I)]
            evidence.extend({**h,'contract_evidence':entry} for h in cache[key])
        if evidence:result[cid]=evidence
    return result
