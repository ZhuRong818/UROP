"""Development matcher 0.1: local claim binding, not predictive admission.

No learned thresholds, network, outcome inputs or implicit source certification.
Canonical IDs here are local typed mention keys, not a verified knowledge graph.
"""
import re
from datetime import datetime, timezone
from eventx.v6.multitype import parse, MONTH
from eventx.v6.measurement_v02 import assess_card, company_registry
from eventx.v6.contracts import utc

VERSION = 'proposition-matcher-0.1'


def mention(text, value):
    return re.search(r'(?<!\w)'+re.escape(value)+r'(?!\w)',text,re.I) if value else None


def clauses(text):
    # Do not bind cross-sentence or across contrast/conjunction clauses.
    return [m.group().strip() for m in re.finditer(r'[^\n;.!?]+(?:\.(?!\s|$)[^\n;.!?]+)*',text)
            if m.group().strip()]


def date_value(value):
    clean=re.sub(r'\s+',' ',value.replace(',','')).strip()
    for fmt in ('%B %d %Y','%b %d %Y'):
        try:return datetime.strptime(clean,fmt).replace(tzinfo=timezone.utc).date()
        except ValueError:pass
    return None


def specification(card):
    routed=parse(card)
    q=card['question']; kind=routed['type_hypothesis']
    name=None; field='question'; cue=None; policy=None
    # Predicate-specific binding, not a generic word-overlap score.
    m=re.match(r'^Will (.+?) reach\s+\$',q,re.I)
    if m:
        name=m[1];kind='asset_price';cue=r'\b(?:price|trades?|trading|tops?|rises?|falls?|fell|drops?|surges?|climbs?)\b.{0,24}\$\s*\d'
        policy='current_price_before_deadline'
    elif kind=='ai_ranking':
        m=re.match(r'^Will (.+?) have the best AI',q,re.I)
        name=m[1] if m else card.get('yes_subtitle')
        field='question' if m else 'yes_subtitle'
        cue=r'\b(?:ranked|ranks|ranking|leaderboard|benchmark|score)\b';policy='explicit_month_and_benchmark'
    elif kind=='music_ranking':
        m=re.match(r'^Will (.+?) be (?:#?1|number one)\b',q,re.I)
        name=m[1] if m else card.get('yes_subtitle')
        field='question' if m else 'yes_subtitle'
        cue=r'\bBillboard Hot 100\b';policy='exact_observation_date'
    elif kind=='leadership':
        name=card.get('yes_subtitle');field='yes_subtitle'
        cue=r'\b(?:nominat\w*|confirm\w*|appoint\w*|withdraw\w*|reject\w*)\b'
        policy='office_and_explicit_date'
    elif kind=='tweet_count':
        m=re.match(r'^Will (.+?) post\b',q,re.I)
        name=m[1] if m else None;cue=r'\b(?:tweets?|posts?)\b';policy='explicit_month_and_count'
    dates=[m.group() for m in re.finditer(rf'\b{MONTH}\s+\d{{1,2}},?\s+20\d{{2}}\b',q,re.I)]
    months=[m.group() for m in re.finditer(rf'\b{MONTH}\s+20\d{{2}}\b',q,re.I)]
    basis='\n'.join([q,*[r['text'] for r in card.get('rule_evidence',[])]])
    benchmarks=sorted(set(m.group().casefold() for m in re.finditer(r'\b(?:Arena|Datacurve|DeepSWE)\b',basis,re.I)))
    return {'type':kind,'subject':name,'subject_source_field':field,
        'local_entity_key':kind+':'+re.sub(r'\W+','_',name.casefold()).strip('_') if name else None,
        'canonical_identity_verified':False,'cue':cue,'time_policy':policy,
        'explicit_dates':dates,'explicit_months':months,'benchmarks':benchmarks,
        'source_card':routed}


def match(article,card):
    spec=specification(card)
    result={'version':VERSION,'specification':spec,'status':'insufficient_evidence',
        'reason':'unsupported_proposition_adapter','claim_span':None,
        'predictive_admitted':False,'supported_links':[]}
    def finish(status,reason,span=None):
        result.update(status=status,reason=reason,claim_span=span)
        return result
    if card.get('subtitle_conflict'):return finish('insufficient_evidence','conflicting_subtitles')
    try:
        arrival=utc(article['source_clock_available_at'])
        close=utc(card['terminal_fields']['close_time'])
    except (KeyError,ValueError,TypeError,AttributeError):
        return finish('insufficient_evidence','missing_or_malformed_time')
    if arrival>=close:return finish('contradiction','article_after_recorded_close')
    text='\n'.join(article.get(k) or '' for k in ('headline','summary'))
    if spec['type']=='measurement':
        registry,_=company_registry([card]);r=assess_card(article,card,registry)
        mapping={'direct_candidate':'direct_candidate','mismatch_candidate':'contradiction',
                 'background_candidate':'background','insufficient_evidence':'insufficient_evidence'}
        result['measurement_details']=r
        return finish(mapping[r['semantic_status']],r['reason'])
    if not spec['cue'] or not spec['subject']:
        return result
    if not mention(text,spec['subject']):return finish('insufficient_evidence','subject_not_resolved_in_article')
    usable=[s for s in clauses(text) if mention(s,spec['subject'])
            and not re.search(r'\b(?:but|while|whereas|and)\b',s,re.I)]
    with_cue=[s for s in usable if re.search(spec['cue'],s,re.I)]
    if not with_cue:return finish('background','subject_without_bound_predicate')
    policy=spec['time_policy']
    for span in with_cue:
        if policy=='current_price_before_deadline':
            if len(spec['explicit_dates'])!=1:continue
            deadline=date_value(spec['explicit_dates'][0])
            if deadline is None or arrival.date()>deadline:continue
            # Reported historical dates must not masquerade as current observations.
            if re.search(r'\b(?:20\d{2}|yesterday|last|previous|historical|ago)\b',span,re.I):continue
            # bind subject directly to price verb/value, avoiding another entity's price
            strict=re.escape(spec['subject'])+r"(?:'s price| price)?\s+(?:trades?|trading|tops?|rises?|falls?|fell|drops?|surges?|climbs?)\s*(?:(?:at|to|above|below)\s+)?\$\s*\d"
            if not re.search(strict,span,re.I):continue
            return finish('direct_candidate','current_price_evidence_for_future_threshold',span)
        if policy=='explicit_month_and_benchmark':
            if len(spec['explicit_months'])!=1 or not spec['benchmarks']:continue
            if mention(span,spec['explicit_months'][0]) and any(mention(span,b) for b in spec['benchmarks']):
                return finish('direct_candidate','named_ranking_period_and_source',span)
        if policy=='exact_observation_date':
            if len(spec['explicit_dates'])==1 and mention(span,spec['explicit_dates'][0]):
                return finish('direct_candidate','named_chart_and_observation_date',span)
        if policy=='office_and_explicit_date':
            if (mention(span,'Director of National Intelligence') and len(spec['explicit_dates'])==1
                    and mention(span,spec['explicit_dates'][0])):
                return finish('direct_candidate','candidate_office_and_date',span)
        if policy=='explicit_month_and_count':
            if (len(spec['explicit_months'])==1 and mention(span,spec['explicit_months'][0])
                    and re.search(r'\b\d+\s+(?:tweets|posts)\b',span,re.I)):
                return finish('direct_candidate','subject_count_and_period',span)
    return finish('insufficient_evidence','predicate_present_time_or_source_binding_missing')
