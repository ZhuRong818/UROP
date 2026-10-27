SELECT table_schema, table_name, column_name, data_type, ordinal_position
FROM information_schema.columns
WHERE (table_schema = 'prediction_markets' AND table_name IN ('kalshi_markets', 'polymarket_markets', 'activity_events'))
   OR (table_schema = 'provenance' AND table_name IN ('scrape_cursor', 'runs'))
ORDER BY table_schema, table_name, ordinal_position
LIMIT 250
