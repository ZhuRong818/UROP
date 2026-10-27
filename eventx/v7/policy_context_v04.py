"""Broader unsigned macro context for opened development; not exact entailment."""
import re
from eventx.v7.signed_evidence_v03_3 import FED, parse_contract, _segments

FED_RE = re.compile(rf'\b{FED}\b', re.I)
RATE = re.compile(r'\b(?:interest|policy|benchmark|funds|target)\s+rates?\b|\brates?\s+(?:cuts?|hikes?|decisions?|increases?|reductions?)\b|\b(?:cuts?|hikes?|lower\w*|rais\w*|hold\w*|keep\w*)\s+(?:\w+\s+){0,3}rates?\b|\bbasis[ -]points?\b|\bbps\b|\bmonetary\s+policy\b', re.I)
DECISION = re.compile(r'\b(?:cuts?|cutting|hikes?|hiking|eas\w*|tighten\w*|hold\w*|rais\w*|lower\w*|unchanged|decisions?|meetings?|expects?|expected|forecast\w*|predict\w*|odds|bets?|paus\w*)\b', re.I)

def extract_context(headline, summary, question):
    contract = parse_contract(question)
    if not contract.kind.startswith('fed_'):
        return {'tier':'none','direction':None,'reason':'outside supported Fed policy-context scope','spans':[]}
    text='\n'.join(x for x in (headline,summary) if x)
    spans=[]
    for offset,segment in _segments(text):
        if FED_RE.search(segment) and RATE.search(segment):
            spans.append({'start':offset,'end':offset+len(segment),'text':segment,'decision_language':bool(DECISION.search(segment))})
    if spans:
        tier='policy_decision_context' if any(s['decision_language'] for s in spans) else 'policy_topic_context'
        return {'tier':tier,'direction':None,'reason':'Fed and policy-rate language in the same text segment; month/quantity entailment not required','spans':spans}
    return {'tier':'none','direction':None,'reason':'no same-segment Fed policy-rate context','spans':[]}
