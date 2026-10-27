SELECT k.key, COUNT(*) AS n
FROM (SELECT raw FROM prediction_markets.polymarket_markets
      WHERE ingest_ts < TIMESTAMPTZ '2026-07-22T00:00:00Z'
      AND condition_id = '0x00406e85288b97f3d587f259f15c557f61bdaa235124d82fe956c65974949ee8'
) m
CROSS JOIN LATERAL jsonb_object_keys(m.raw) k(key)
GROUP BY 1
ORDER BY 1
LIMIT 200
