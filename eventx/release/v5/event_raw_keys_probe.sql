SELECT k.key, COUNT(*) AS n
FROM (SELECT raw FROM prediction_markets.polymarket_events
      WHERE ingest_ts < TIMESTAMPTZ '2026-07-22T00:00:00Z'
      ORDER BY event_id, source LIMIT 100) e
CROSS JOIN LATERAL jsonb_object_keys(e.raw) k(key)
GROUP BY 1
ORDER BY 1
LIMIT 200
