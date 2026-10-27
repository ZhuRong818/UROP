"""Post-audit development diagnostics, not new gold or independent evaluation."""
import hashlib
import json
import os
from collections import Counter, defaultdict
from pathlib import Path

os.environ['HF_HUB_OFFLINE'] = '1'
os.environ['TRANSFORMERS_OFFLINE'] = '1'
from eventx.v6.contracts import review_text, utc
from eventx.v6.link_audit import validate_reviews


def main():
    root = Path('data/v6')
    out = root / 'matching_diagnosis_20260917'
    if out.exists():
        raise FileExistsError(out)
    inputs = {}
    def read(p):
        inputs[str(p)] = hashlib.sha256(p.read_bytes()).hexdigest()
        return [json.loads(x) for x in p.read_text().splitlines()]
    packet = read(root / 'bounded_audit_20260917/relevance_review_packet.jsonl')
    a,b = [read(root / f'bounded_relevance_receipt_20260917/relevance_reviewer_{k}_responses.jsonl') for k in ('A','B')]
    validation = validate_reviews(packet,a,b)
    aa,bb = [{r['pair_id']:r for r in rows} for rows in (a,b)]
    cards = {r['contract_id']:r for r in read(root / 'contract_link_pilot_20260916/contract_cards.jsonl')}
    articles = {r['article_id']:r for r in read(root / 'contract_link_pilot_20260916/articles.jsonl')}
    pool = defaultdict(list)
    for r in read(root / 'hybrid_audit_20260916/scored_candidate_pool.jsonl'):
        if r['split']=='development':
            pool[r['article_id']].append(r)
    # Local tokenizer only; no weights, downloads, scoring or outcome reads.
    from transformers import AutoTokenizer
    tokenizers = {k:AutoTokenizer.from_pretrained(str(root / f'local_models_20260916/{k}'),local_files_only=True) for k in ('encoder','reranker')}
    # Analyst classifications by fixed packet index, derived from both text and
    # submitted reviews. They are diagnostic interpretations, never reference gold.
    special = {
        0:('wrong_period',['measurement_mismatch','background_only'],'Q1 earnings preview versus Q3 skier visits; no visit metric in supplied text.'),
        4:('wrong_event',['predicate_mismatch','background_only'],'ChatGPT equity selection is not the contract leaderboard comparison.'),
        7:('wrong_event',['predicate_mismatch'],'Salesforce agents are not the named model winning the specified leaderboard.'),
        8:('wrong_entity',['measurement_mismatch'],'AMD corporate valuation is not Musk personal net worth.'),
        14:('wrong_event',['background_only'],'AI stock prices do not establish model leaderboard performance.'),
        16:('wrong_entity',['predicate_mismatch'],'Duluth earnings transcript is not United Airlines saying the named term.'),
        18:('predicate_mismatch',['measurement_mismatch'],'Musk/SpaceX wallet story does not address tweet counts.'),
        19:('wrong_period',['predicate_mismatch','background_only'],'News follows the May31 deadline and does not evidence the required lifting announcement.'),
        21:('predicate_mismatch',['background_only'],'Index opening direction and SpaceX IPO are not index inclusion.'),
        25:('predicate_mismatch',['background_only'],'Anthropic drug discovery programme is not leaderboard superiority.'),
        30:('wrong_entity',['wrong_event'],'CFPB directorship is not DNI succession; candidate also differs.'),
        31:('wrong_event',['wrong_entity'],'Cross-country skiing partnership is not World Cup football qualification.'),
        36:('reference_success',[],'Both reviewers accepted current Bitcoin price as evidence relevant to the future threshold; settlement proof is not required.'),
        37:('wrong_entity',['measurement_mismatch'],'WisdomTree equity is not WTI crude oil.'),
        38:('wrong_entity',['wrong_event'],'Banco BBVA Argentina is not the Argentina football team.')}
    cases=[]
    for i,p in enumerate(packet):
        identity=p['pair_id']; art=p['article']; card=p['contract']
        assert card == cards[card['contract_id']] and art == articles[art['article_id']]
        assert identity == hashlib.sha256((art['article_id']+'|'+card['contract_id']).encode()).hexdigest()[:24]
        for r in (aa[identity],bb[identity]):
            if 'article' in r: assert r['article']==art
            if 'contract' in r: assert r['contract']==card
        ranked=sorted(pool[art['article_id']],key=lambda r:(-r['crossencoder_logit'],r['contract_id']))
        selected=next(r for r in ranked if r['contract_id']==card['contract_id'])
        assert selected['crossencoder_logit']==ranked[0]['crossencoder_logit']
        ct=review_text(card); at='\n'.join(art.get(k) or '' for k in ('headline','summary'))
        counts={k:len(tokenizers['encoder'](v,truncation=False)['input_ids']) for k,v in [('contract',ct),('article',at)]}
        pair_tokens=len(tokenizers['reranker'](ct,at,truncation=False)['input_ids'])
        primary, secondary, reason=special.get(i,('wrong_entity_or_event',[],
            'The article subject and the selected contract concern different entities/events; no direct link is supported by the supplied headline/summary.'))
        close=card['terminal_fields'].get('close_time')
        cases.append(dict(pair_id=identity,article_id=art['article_id'],contract_id=card['contract_id'],
            headline=art['headline'],question=card['question'],subtitle=card['yes_subtitle'],
            reviewer_A=aa[identity]['labels'],reviewer_B=bb[identity]['labels'],
            primary_diagnostic=primary,secondary_diagnostics=secondary,diagnostic_rationale=reason,
            diagnostic_provenance='assistant post-audit interpretation; not human gold',
            unresolved=identity in validation['disagreement_ids'],
            selected_score=selected,top_score_ties=sum(r['crossencoder_logit']==ranked[0]['crossencoder_logit'] for r in ranked),
            pool_size=len(ranked),rules_present=bool(card['rule_evidence']),subtitle_present=bool(card['yes_subtitle']),
            semantic_fields_populated=sum(v is not None for v in card['semantic_fields'].values()),
            summary_missing=not bool((art.get('summary') or '').strip()),
            received_after_recorded_close=bool(close and utc(art['source_clock_available_at'])>=utc(close)),
            encoder_token_counts=counts,encoder_truncates=any(n>256 for n in counts.values()),
            reranker_pair_tokens=pair_tokens,reranker_truncates=pair_tokens>384,
            localization='accepted reference success' if primary=='reference_success' else
                'selection/acceptance failure; retrieval miss versus ranking error not identifiable without a verified alternative',
            alternatives=[dict(contract_id=r['contract_id'],question=cards[r['contract_id']]['question'],
                subtitle=cards[r['contract_id']]['yes_subtitle'],score=r['crossencoder_logit'],
                relevance_status='unreviewed; not a correct alternative assertion') for r in ranked[:5]]))
    report=dict(cases=len(cases),primary_diagnostics=dict(Counter(r['primary_diagnostic'] for r in cases)),
        integrity_checks=dict(exact_card_article_joins=40,review_embedded_evidence_unchanged=80,
            pair_id_hashes=40,selected_maximum_score=40),
        counts={k:sum(bool(r[k]) for r in cases) for k in ['rules_present','subtitle_present','summary_missing','received_after_recorded_close','encoder_truncates','reranker_truncates']},
        fully_empty_semantic_fields=sum(r['semantic_fields_populated']==0 for r in cases),
        top_score_tie_cases=sum(r['top_score_ties']>1 for r in cases),
        negative_top_score_cases=sum(r['selected_score']['crossencoder_logit']<0 for r in cases),
        chosen_contract_frequency=dict(Counter(r['contract_id'] for r in cases)),
        rank_field_one_cases=sum(r['selected_score']['rank']==1 for r in cases),
        retrieval_recall='not identifiable: alternative candidates lack reference labels',
        diagnostic_only=True,protected_outcomes_accessed=False,audit_rerun=False)
    out.mkdir()
    (out/'cases.jsonl').write_text(''.join(json.dumps(r,ensure_ascii=False)+'\n' for r in cases))
    (out/'report.json').write_text(json.dumps(report,indent=2)+'\n')
    lines=['# Forty-case development failure analysis','',
        'Assistant diagnostic classifications, not new gold labels. Original audit unchanged.',
        'Alternatives, scores, token counts and original reviewer labels are in cases.jsonl.', '',
        '| Pair | Article | Contract | Diagnostic | Explanation |','|---|---|---|---|---|']
    for r in cases:
        vals=[r['pair_id'],r['headline'],r['question']+' / '+str(r['subtitle']),r['primary_diagnostic'],r['diagnostic_rationale']]
        lines.append('| '+' | '.join(str(v).replace('|','/').replace('\n',' ') for v in vals)+' |')
    (out/'FAILURE_ANALYSIS.md').write_text('\n'.join(lines)+'\n')
    inputs[str(Path(__file__))]=hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
    (out/'manifest.json').write_text(json.dumps(dict(inputs=inputs,outputs={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in out.iterdir()}),indent=2)+'\n')
    print(json.dumps(report,indent=2))

if __name__=='__main__': main()
