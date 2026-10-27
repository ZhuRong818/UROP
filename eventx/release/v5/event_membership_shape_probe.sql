SELECT jsonb_typeof(e.market_ids) AS container_type,
       jsonb_typeof(member.value) AS member_type, COUNT(*) AS n
FROM prediction_markets.polymarket_events e
LEFT JOIN LATERAL jsonb_array_elements(
  CASE WHEN jsonb_typeof(e.market_ids) = 'array' THEN e.market_ids ELSE '[]'::jsonb END
) AS member(value) ON true
WHERE e.ingest_ts < TIMESTAMPTZ '2026-07-22T00:00:00Z'
GROUP BY 1, 2
LIMIT 100
