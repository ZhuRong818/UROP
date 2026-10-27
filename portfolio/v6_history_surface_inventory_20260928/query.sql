SELECT table_schema, table_name
FROM information_schema.tables
WHERE table_schema IN ('provenance', 'prediction_markets')
ORDER BY table_schema, table_name
LIMIT 200
