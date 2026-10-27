SELECT id, published_at, ingest_ts, source_endpoint, source_run_id
FROM news.articles
WHERE ingest_ts >= TIMESTAMPTZ '2026-05-19T00:00:00Z'
  AND ingest_ts < TIMESTAMPTZ '2026-05-20T00:00:00Z'
ORDER BY ingest_ts
LIMIT 10
