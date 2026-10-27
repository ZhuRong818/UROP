SELECT id, condition_id, question, slug, source, source_endpoint, source_run_id,
       ingest_ts, raw->'events'->0->>'id' AS embedded_event_id,
       raw->'events'->0->>'title' AS embedded_event_title,
       raw->'events'->0->>'slug' AS embedded_event_slug
FROM prediction_markets.polymarket_markets
WHERE condition_id='0x3ceb5b631318be5000758200590efe2b308a581d6787c3e7bc050bfd8f627627'
LIMIT 10
