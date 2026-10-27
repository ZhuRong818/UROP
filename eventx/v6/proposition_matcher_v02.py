"""Separate semantic hypotheses from temporal admissibility; no accepted links."""
import re
from eventx.v6.proposition_matcher import specification, mention, clauses, date_value
from eventx.v6.measurement_v02 import company_registry, assess_card
from eventx.v6.contracts import utc


def match(article,card):
    spec=specification(card)
    result={'version':'proposition-matcher-0.2','specification':spec,
        'semantic_status':'insufficient_evidence','semantic_reason':'unsupported_proposition_adapter',
        'claim_span':None,'eligibility':'uncertified','eligibility_reasons':[],
        'predictive_admitted':False,'supported_links':[]}
    try: arrival=utc(article['source_clock_available_at'])
    except (KeyError,TypeError,ValueError,AttributeError):arrival=None
    if arrival is None:result['eligibility_reasons'].append('missing_or_malformed_availability')
    fields=card.get('terminal_fields',{})
    result['terminal_evidence']=fields
    # end_date retained as evidence, never silently equated with verified close_time.
    try:close=utc(fields['close_time'])
    except (KeyError,TypeError,ValueError,AttributeError):close=None
    if close is None:result['eligibility_reasons'].append('trading_close_not_verified')
    if close and arrival and arrival>=close:
        result['eligibility']='ineligible';result['eligibility_reasons'].append('after_recorded_close')
    result['eligibility_reasons'].append('exact_article_and_contract_versions_not_certified')
    def finish(status,reason,span=None):
        result.update(semantic_status=status,semantic_reason=reason,claim_span=span)
        return result
    if card.get('subtitle_conflict'):return finish('insufficient_evidence','conflicting_subtitles')
    if spec['type']=='measurement':
        registry,_=company_registry([card]);r=assess_card(article,card,registry)
        result['measurement_details']=r
        mapping={'direct_candidate':'direct_candidate','mismatch_candidate':'contradiction',
                 'background_candidate':'background','insufficient_evidence':'insufficient_evidence'}
        return finish(mapping[r['semantic_status']],r['reason'])
    if not spec['cue'] or not spec['subject']:return result
    text='\n'.join(article.get(k) or '' for k in ('headline','summary'))
    if not mention(text,spec['subject']):return finish('insufficient_evidence','subject_not_resolved')
    spans=[s for s in clauses(text) if mention(s,spec['subject'])
           and not re.search(r'\b(?:but|while|whereas|and)\b',s,re.I)]
    spans=[s for s in spans if re.search(spec['cue'],s,re.I)]
    if not spans:return finish('background','subject_without_bound_predicate')
    for span in spans:
        policy=spec['time_policy'];subject=re.escape(spec['subject'])
        if policy=='current_price_before_deadline':
            if len(spec['explicit_dates'])!=1 or arrival is None:continue
            deadline=date_value(spec['explicit_dates'][0])
            if deadline is None or arrival.date()>deadline:continue
            if re.search(r'\b(?:20\d{2}|yesterday|last|previous|historical|ago)\b',span,re.I):continue
            strict=subject+r"(?:'s price| price)?\s+(?:trades?|trading|tops?|rises?|falls?|fell|drops?|surges?|climbs?)\s*(?:(?:at|to|above|below)\s+)?\$\s*\d"
            if re.search(strict,span,re.I):
                return finish('direct_candidate','current_price_for_future_threshold',span)
        elif policy=='explicit_month_and_benchmark':
            if (len(spec['explicit_months'])==1 and spec['benchmarks']
                and mention(span,spec['explicit_months'][0]) and any(mention(span,b) for b in spec['benchmarks'])
                and re.search(subject+r'\s+(?:ranks?|ranked|scores?)\b',span,re.I)):
                return finish('direct_candidate','subject_bound_ranking_period_source',span)
        elif policy=='exact_observation_date':
            if (len(spec['explicit_dates'])==1 and mention(span,spec['explicit_dates'][0])
                and re.search(subject+r'\s+(?:reaches?|ranks?|ranked|tops?|falls?)\b',span,re.I)):
                return finish('direct_candidate','subject_bound_chart_date',span)
        elif policy=='office_and_explicit_date':
            if (len(spec['explicit_dates'])==1 and mention(span,spec['explicit_dates'][0])
                and mention(span,'Director of National Intelligence')
                and re.search(subject+r"(?:'s)?\s+(?:nomination|confirmation|appointment|withdrawal)\b",span,re.I)):
                return finish('direct_candidate','candidate_office_date',span)
        elif policy=='explicit_month_and_count':
            if (len(spec['explicit_months'])==1 and mention(span,spec['explicit_months'][0])
                and re.search(subject+r'\s+(?:posted|posts|tweeted)\s+\d+\s+(?:tweets|posts)\b',span,re.I)):
                return finish('direct_candidate','subject_count_period',span)
    return finish('insufficient_evidence','predicate_present_but_binding_unproven')
