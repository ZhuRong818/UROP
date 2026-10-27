SELECT ticker, event_ticker, source, source_endpoint, source_run_id, ingest_ts,
 ARRAY(SELECT jsonb_object_keys(raw)) AS raw_keys,
 raw->>'rules_primary' AS rules_primary,
 raw->>'rules_secondary' AS rules_secondary,
 raw->'mve_selected_legs' AS selected_legs,
 raw->'market'->'mve_selected_legs' AS nested_selected_legs
FROM prediction_markets.kalshi_markets
WHERE ticker IN (
 'KXMVECROSSCATEGORY-S2026011FCE3B5CA-C9D53633F5F',
 'KXMVECROSSCATEGORY-S202602A5152409B-04FE5F8A154',
 'KXMVECROSSCATEGORY-S202602A5152409B-8572109E9A9')
ORDER BY ticker, ingest_ts
LIMIT 30
