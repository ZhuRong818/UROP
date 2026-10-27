SELECT table_schema, table_name, column_name, data_type
FROM information_schema.columns
WHERE table_schema IN ('prediction_markets', 'news', 'provenance')
  AND (table_name ILIKE '%market%' OR table_name ILIKE '%event%'
       OR table_name ILIKE '%article%' OR table_name ILIKE '%version%'
       OR table_name ILIKE '%audit%' OR table_name ILIKE '%history%'
       OR table_name IN ('runs', 'sources'))
ORDER BY table_schema, table_name, ordinal_position
LIMIT 2000
