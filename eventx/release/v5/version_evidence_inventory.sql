SELECT table_schema, table_name, column_name, data_type
FROM information_schema.columns
WHERE table_schema IN ('news', 'prediction_markets', 'provenance')
  AND (table_name ILIKE '%version%' OR table_name ILIKE '%history%'
       OR table_name ILIKE '%snapshot%' OR column_name ILIKE '%valid_%'
       OR column_name ILIKE '%updated%' OR column_name ILIKE '%version%')
ORDER BY table_schema, table_name, ordinal_position
LIMIT 1000
