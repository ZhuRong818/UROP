"""Conservative diagnostic claim roles and explicit question-period checks."""
import calendar
import re
from datetime import date
from eventx.v6.contracts import utc
from eventx.v6.multitype import MONTH
from eventx.v6.proposition_matcher import date_value


def period(article, card):
    q=card['question'];bounds=[]
    for m in re.finditer(rf'\b(?:by|before|on)\s+({MONTH}\s+\d{{1,2}},?\s+20\d{{2}})\b',q,re.I):
        d=date_value(m[1])
        if d:bounds.append((d,m.group()))
    for m in re.finditer(rf'\bat the end of ({MONTH})\s+(20\d{{2}})\b',q,re.I):
        d=date_value(m[1]+' 1 '+m[2])
        if d:bounds.append((date(d.year,d.month,calendar.monthrange(d.year,d.month)[1]),m.group()))
    result={'status':'unresolved_period','question_evidence':[q for _,q in bounds],
            'interpretation':'calendar screening only; timezone and exact cutoff not certified'}
    try:
        arrival=utc(article['source_clock_available_at'])
        if arrival.tzinfo is None:return result
    except (KeyError,ValueError,TypeError,AttributeError):return result
    try:
        close=utc(card.get('terminal_fields',{}).get('close_time'))
        if close and close.tzinfo and arrival>=close:
            return {**result,'status':'after_recorded_close'}
    except (ValueError,TypeError,AttributeError):pass
    unique={d for d,_ in bounds}
    if len(unique)!=1:return result
    end=next(iter(unique));delta=(arrival.date()-end).days
    # Allow a full date buffer for unspecified local timezone. Boundary dates abstain.
    result['screening_end_date']=end.isoformat()
    result['status']='expired_question_period' if delta>=2 else ('boundary_timezone_unresolved' if delta>=0 else 'before_question_deadline')
    return result


def assess(article,card,relation):
    result={'role':'unresolved','role_evidence':[], 'period':period(article,card),
            'predictive_admitted':False,'settlement_verified':False}
    if relation['status']!='event_channel_candidate':
        result['role']='no_bound_event_channel';return result
    for e in relation['evidence']:
        s=e['quote']
        if re.search(r'\b(?:calls?|said|says|believes?|appears?|suggest\w*|expects?|forecasts?)\b',s,re.I):
            result.update(role='opinion_or_attributed_assessment',role_evidence=[e]);return result
    for e in relation['evidence']:
        s=e['quote']
        if relation['channel'] in {'peace','acquisition','inclusion'}:
            result.update(role='event_update_candidate',role_evidence=[e]);return result
        if relation['channel'] in {'valuation','price','tweet_count','ranking'} and re.search(r'\$\s*\d|\b\d+(?:\.\d+)?\b',s):
            result.update(role='measurement_claim_period_unverified',role_evidence=[e]);return result
    return result
