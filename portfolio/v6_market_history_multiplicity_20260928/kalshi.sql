SELECT ticker, COUNT(*) AS row_count,
 MIN(ingest_ts) AS first_ingest, MAX(ingest_ts) AS last_ingest,
 COUNT(DISTINCT source_run_id) AS run_count,
 COUNT(DISTINCT title) AS title_versions,
 COUNT(DISTINCT (yes_sub_title, no_sub_title)) AS outcome_versions,
 COUNT(DISTINCT status) AS status_states
FROM prediction_markets.kalshi_markets
WHERE ticker = 'KXWC3RDPLACE-26-MEX'
GROUP BY ticker LIMIT 1
