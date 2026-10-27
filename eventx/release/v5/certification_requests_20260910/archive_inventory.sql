SELECT table_schema, table_name, column_name, data_type
FROM information_schema.columns
WHERE table_schema NOT IN ('pg_catalog', 'information_schema')
AND (table_name ILIKE '%audit%' OR table_name ILIKE '%archive%'
     OR table_name ILIKE '%version%' OR table_name ILIKE '%capture%'
     OR table_name ILIKE '%request%' OR table_name ILIKE '%response%'
     OR table_name ILIKE '%histor%' OR column_name ILIKE '%valid_from%'
     OR column_name ILIKE '%valid_until%' OR column_name ILIKE '%content_hash%')
ORDER BY table_schema, table_name, ordinal_position
LIMIT 2000
