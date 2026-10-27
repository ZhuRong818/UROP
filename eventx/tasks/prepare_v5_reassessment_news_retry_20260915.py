"""Exact-ID fallback after a bounded news quality query failed."""
import json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
def main():
    path=ROOT/'data/v5/source_readiness_20260908/news_provenance_staging.jsonl'
    ids=[]
    with path.open() as handle:
        for line in handle:
            r=json.loads(line)
            value=r.get('id',r.get('article_id'))
            if value is not None:
                ids.append(int(value))
            if len(ids)>=100: break
    assert ids
    sql="""SELECT id, source, source_endpoint, source_run_id, published_at, ingest_ts,
length(headline) AS headline_chars, length(summary) AS summary_chars,
length(body) AS body_chars, publisher, related_symbols,
raw ? 'updated_at' AS has_raw_updated_at
FROM news.articles WHERE id IN ("""+','.join(map(str,ids))+') ORDER BY id LIMIT 1000\n'
    out=ROOT/'data/v5/design_reassessment_20260915/queries/news_exact_ids.sql'
    assert not out.exists()
    out.write_text(sql)
    print(len(ids))
if __name__=='__main__': main()
