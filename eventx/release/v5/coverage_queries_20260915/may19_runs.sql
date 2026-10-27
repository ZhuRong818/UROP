SELECT endpoint_id, status, count(*) AS runs,
       min(started_at) AS earliest_start, max(ended_at) AS latest_end,
       sum(rows_inserted) AS reported_inserts, sum(rows_updated) AS reported_updates,
       sum(rows_failed) AS reported_failed_rows,
       count(*) FILTER (WHERE rows_inserted IS NULL OR rows_updated IS NULL) AS missing_counters
FROM provenance.runs
WHERE started_at >= TIMESTAMPTZ '2026-05-19T00:00:00Z'
  AND started_at < TIMESTAMPTZ '2026-05-20T00:00:00Z'
  AND endpoint_id ILIKE '%news%'
GROUP BY endpoint_id, status
ORDER BY endpoint_id, status
LIMIT 100
