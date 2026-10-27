SELECT count(*) AS retained_rows,
       count(*) FILTER (WHERE ingest_ts > published_at + INTERVAL '24 hours') AS ingest_lag_gt_24h,
       count(*) FILTER (WHERE ingest_ts >= published_at
                         AND ingest_ts <= published_at + INTERVAL '24 hours') AS within_24h_rows,
       min(ingest_ts) AS earliest_ingest, max(ingest_ts) AS latest_ingest
FROM news.articles
WHERE ingest_ts >= TIMESTAMPTZ '2026-05-17T00:00:00Z'
  AND ingest_ts < TIMESTAMPTZ '2026-05-18T00:00:00Z'
