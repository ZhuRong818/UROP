SELECT event_object_schema AS table_schema, event_object_table AS table_name,
       trigger_name, event_manipulation, action_timing
FROM information_schema.triggers
WHERE event_object_schema IN ('news', 'prediction_markets')
  AND event_object_table IN ('articles', 'article_sources', 'polymarket_markets', 'kalshi_markets')
ORDER BY table_schema, table_name, trigger_name, event_manipulation
LIMIT 200
