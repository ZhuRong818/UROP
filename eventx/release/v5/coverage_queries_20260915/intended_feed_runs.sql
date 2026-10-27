SELECT (started_at AT TIME ZONE 'UTC')::date AS run_day, endpoint_id, status,
       count(*) AS runs, min(started_at) AS earliest_start, max(ended_at) AS latest_end,
       count(*) FILTER (WHERE rows_inserted IS NULL OR rows_updated IS NULL) AS missing_counters
FROM provenance.runs
WHERE started_at >= TIMESTAMPTZ '2026-05-17T00:00:00Z'
  AND started_at < TIMESTAMPTZ '2026-05-21T00:00:00Z'
  AND endpoint_id IN ('finnhub:company-news','fmp:stable/news/stock',
    'fmp:stable/news/forex-latest','fmp:stable/news/crypto-latest',
    'fmp:stable/news/press-releases-latest','fmp:stable/news/general-latest',
    'fmp:stable/news/stock-latest','massive:v2/reference/news')
GROUP BY run_day, endpoint_id, status
ORDER BY run_day, endpoint_id, status
LIMIT 500
