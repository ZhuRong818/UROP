SELECT endpoint_id, scope_key, last_run_id, last_data_date,
       last_run_at, next_action, retry_count
FROM provenance.scrape_cursor
WHERE endpoint_id = 'finnhub:company-news'
ORDER BY scope_key
LIMIT 20
