"""Supplement raw-string timestamp comparison with parsed UTC equality."""
import json
from pathlib import Path
from eventx.v6.contracts import utc
from eventx.tasks.check_proposition_v03_development import read,digest

def main():
    root=Path('data/v6/candidate_yield_clock_reconciliation_20260919');root.mkdir(exist_ok=False)
    prior=Path('data/v6/candidate_yield_20260919/checks.jsonl')
    dp=Path('data/v6/hybrid_development_reviews_20260916/packet.jsonl')
    np=Path('data/v5/source_readiness_20260908/news_provenance_staging.jsonl')
    rows=read(prior);ids={r['article_id'] for r in rows}
    articles={r['article']['article_id']:r['article'] for r in read(dp) if r['article']['article_id'] in ids}
    news={r['article_id']:r for r in read(np) if r['article_id'] in ids}
    same={i:utc(articles[i]['source_clock_available_at'])==utc(news[i]['source_clock_available_at']) for i in ids}
    report={'normalized_matching_articles':sum(same.values()),'normalized_matching_pairs':sum(same[r['article_id']] for r in rows),
            'actual_clock_mismatch_articles':[i for i,v in same.items() if not v],
            'correction':'Prior article_clock_matches is raw string equality only: Z versus +00:00. Use this parsed UTC comparison.',
            'input_hashes':{str(p):digest(p) for p in [prior,dp,np,Path(__file__)]}}
    (root/'report.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(report,indent=2))

if __name__=='__main__':main()
