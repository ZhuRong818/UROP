"""Development context filter layered over subject retrieval; not entailment."""
import re

def context_gate(article,card,evidence):
    text='\n'.join(article.get(k) or '' for k in ('headline','summary'))
    q=card['question']
    usable=[h for h in evidence if h['quote'].casefold() not in {'there','it','this','that','they','he','she'}]
    if not usable:return 'reject_generic_subject'
    rules=[
        (r'World Cup|Basketball|goals|1st Half|playoffs|semifinals',r'football|soccer|basketball|World Cup|NBA|FIFA|goals|playoffs|semifinals|match|tournament'),
        (r'album|Billboard|Best Play|Tony Awards',r'album|music|song|Billboard|rapper|singer|Tony Awards|Broadway|theatre|theater'),
        (r'peace deal|ceasefire',r'peace|ceasefire|negotiat|war|conflict|military|bomb|Hormuz'),
        (r'tweets|\bpost\b',r'tweets?|posts?|Twitter|social media|\bX\b'),
        (r'say during.*earnings call',r'earnings|transcript|quarter|results'),
        (r'best AI|top AI',r'\bAI\b|artificial intelligence|model|leaderboard|benchmark'),
        (r'added to the S&P',r'S&P|index|indices|inclusion'),
    ]
    for contract_pattern,news_pattern in rules:
        if re.search(contract_pattern,q,re.I) and not re.search(news_pattern,text,re.I):
            return 'reject_missing_contract_domain_context'
    return 'subject_context_candidate'
