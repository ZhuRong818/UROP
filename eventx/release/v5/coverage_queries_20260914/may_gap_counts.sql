WITH scoped AS (
 SELECT a.id, a.published_at, a.ingest_ts, a.source_endpoint, a.source_run_id,
        r.run_id AS linked_run, r.started_at, r.ended_at, r.status,
        GREATEST(a.published_at,a.ingest_ts,r.started_at,
                 COALESCE(r.ended_at,a.ingest_ts)) AS legacy_available
 FROM news.articles a
 LEFT JOIN provenance.runs r ON r.run_id=a.source_run_id
 WHERE a.ingest_ts >= TIMESTAMPTZ '2026-05-17T00:00:00Z'
   AND a.ingest_ts < TIMESTAMPTZ '2026-05-20T00:00:00Z'
)
SELECT (ingest_ts AT TIME ZONE 'UTC')::date AS ingest_day, source_endpoint,
       count(*) AS retained_rows,
       count(*) FILTER (WHERE linked_run IS NULL) AS missing_run_rows,
       count(*) FILTER (WHERE published_at IS NULL) AS missing_publication_rows,
       count(*) FILTER (WHERE ingest_ts > published_at + INTERVAL '24 hours') AS ingest_lag_gt_24h,
       count(*) FILTER (WHERE published_at > ingest_ts) AS publication_after_ingest,
       count(*) FILTER (WHERE legacy_available >= TIMESTAMPTZ '2026-05-20T00:00:00Z') AS shifted_beyond_window,
       count(*) FILTER (WHERE linked_run IS NOT NULL
          AND published_at >= TIMESTAMPTZ '2026-05-16T00:00:00Z'
          AND published_at < TIMESTAMPTZ '2026-07-22T00:00:00Z'
          AND ingest_ts >= published_at AND ingest_ts <= published_at + INTERVAL '24 hours'
          AND ingest_ts >= started_at AND (ended_at IS NULL OR ended_at >= started_at)
          AND legacy_available >= TIMESTAMPTZ '2026-05-17T00:00:00Z'
          AND legacy_available < TIMESTAMPTZ '2026-07-22T00:00:00Z'
          AND legacy_available <= published_at + INTERVAL '24 hours') AS legacy_filter_pass_rows
FROM scoped
GROUP BY ingest_day, source_endpoint
ORDER BY ingest_day, source_endpoint
LIMIT 500
