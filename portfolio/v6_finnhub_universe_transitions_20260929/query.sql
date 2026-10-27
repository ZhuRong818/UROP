WITH ordered AS (
 SELECT run_id, started_at, args->>'n_symbols' AS n_symbols,
 LAG(args->>'n_symbols') OVER (ORDER BY started_at, run_id) AS previous_n_symbols
 FROM provenance.runs
 WHERE endpoint_id = 'finnhub:company-news'
   AND started_at >= TIMESTAMPTZ '2026-05-17T00:00:00Z'
   AND started_at < TIMESTAMPTZ '2026-07-22T00:00:00Z'
)
SELECT run_id, started_at, previous_n_symbols, n_symbols
FROM ordered
WHERE n_symbols IS DISTINCT FROM previous_n_symbols
ORDER BY started_at, run_id LIMIT 50
