"""Prepare bounded descriptive metadata probes; no price/status/outcome fields."""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / 'data/v5/design_reassessment_20260915'


def main():
    OUT.mkdir(exist_ok=False)
    (OUT / 'queries').mkdir()
    spec = Path('/tmp/eventx_reassessment_openapi_20260915.json').read_bytes()
    json.loads(spec)
    (OUT / 'openapi.json').write_bytes(spec)
    rows = [json.loads(s) for s in (ROOT / 'data/v5/topic_coverage_triage_20260914/topic_review_queue.jsonl').read_text().splitlines()]
    unresolved = [json.loads(s) for s in (ROOT / 'data/v5/unresolved_pair_enrichment_20260915/enriched_pairs.jsonl').read_text().splitlines()]
    selected = {c['market_id'] for r in unresolved for side in ('left', 'right') for c in r[side]['contracts'] if c['venue'] == 'kalshi'}
    selected.update(r['market_id'] for r in sorted(rows, key=lambda x:x['market_id']) if r['venue']=='kalshi' and r['category']=='macro')
    selected = sorted(selected)[:200]
    literal = lambda s: "'" + s.replace("'", "''") + "'"
    queries = {'kalshi_quality': """SELECT ticker, event_ticker, title, yes_sub_title, no_sub_title,
open_time, close_time, ingest_ts, source, source_endpoint, source_run_id,
length(raw->>'rules_primary') AS primary_rule_chars,
length(raw->>'rules_secondary') AS secondary_rule_chars,
raw->>'series_ticker' AS raw_series_ticker,
jsonb_typeof(raw->'mve_selected_legs') AS leg_container_type
FROM prediction_markets.kalshi_markets
WHERE ticker IN (""" + ','.join(map(literal, selected)) + """ )
AND ingest_ts < TIMESTAMPTZ '2026-07-22T00:00:00Z'
ORDER BY ticker, ingest_ts LIMIT 5000
"""}
    ids = sorted(r['market_id'] for r in rows if r['venue']=='polymarket')[:30]
    queries['polymarket_quality'] = """SELECT condition_id, id, question, ingest_ts, source, source_endpoint, source_run_id,
raw->>'groupItemTitle' AS contract_subtitle,
length(raw->>'description') AS description_chars,
raw->>'resolutionSource' AS resolution_source,
jsonb_typeof(raw->'events') AS event_container_type,
jsonb_typeof(raw->'outcomes') AS outcome_container_type,
jsonb_typeof(raw->'clobTokenIds') AS token_container_type
FROM prediction_markets.polymarket_markets WHERE condition_id IN (""" + ','.join(map(literal, ids)) + """ )
AND ingest_ts < TIMESTAMPTZ '2026-07-22T00:00:00Z'
ORDER BY condition_id, ingest_ts LIMIT 1000
"""
    queries['news_quality'] = """SELECT source, source_endpoint, count(*) AS sampled_rows,
count(*) FILTER (WHERE coalesce(headline,'') <> '') AS with_headline,
count(*) FILTER (WHERE coalesce(summary,'') <> '') AS with_summary,
count(*) FILTER (WHERE coalesce(body,'') <> '') AS with_body,
count(*) FILTER (WHERE coalesce(publisher,'') <> '') AS with_publisher,
count(*) FILTER (WHERE related_symbols IS NOT NULL) AS with_related_symbols,
count(*) FILTER (WHERE raw ? 'updated_at') AS raw_updated_at_key,
count(*) FILTER (WHERE raw ? 'published_utc') AS raw_published_utc_key,
min(published_at) AS min_publication, max(published_at) AS max_publication,
min(ingest_ts) AS min_ingest, max(ingest_ts) AS max_ingest
FROM (SELECT headline,summary,body,publisher,related_symbols,raw,published_at,ingest_ts,source,source_endpoint
FROM news.articles WHERE ingest_ts >= TIMESTAMPTZ '2026-06-01T00:00:00Z'
AND ingest_ts < TIMESTAMPTZ '2026-06-02T00:00:00Z' ORDER BY id LIMIT 1000) s
GROUP BY source, source_endpoint ORDER BY source, source_endpoint
"""
    for name, sql in queries.items():
        (OUT / 'queries' / (name+'.sql')).write_text(sql)
    (OUT / 'selection.json').write_text(json.dumps({'kalshi_ids':selected,'polymarket_ids':ids,
        'news_scope':'first 1000 IDs ingested June 1; descriptive nonrandom sample',
        'outcome_columns_requested':False}, indent=2)+'\n')
    print(json.dumps({'kalshi_targets':len(selected),'polymarket_targets':len(ids),'queries':list(queries)}))


if __name__ == '__main__':
    main()
