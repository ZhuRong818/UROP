SELECT column_name, data_type, ordinal_position
FROM information_schema.columns
WHERE table_schema = 'reference' AND table_name = 'symbol_universe'
ORDER BY ordinal_position LIMIT 100
