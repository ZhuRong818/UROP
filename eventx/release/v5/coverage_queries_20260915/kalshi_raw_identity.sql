SELECT ticker, source, source_run_id, ingest_ts,
       raw->>'yes_sub_title' AS raw_yes_sub_title,
       raw->>'no_sub_title' AS raw_no_sub_title,
       raw->>'subtitle' AS raw_subtitle,
       raw->'market'->>'yes_sub_title' AS nested_yes_sub_title,
       raw->'market'->>'subtitle' AS nested_subtitle,
       ARRAY(SELECT jsonb_object_keys(raw)) AS raw_top_level_keys
FROM prediction_markets.kalshi_markets
WHERE ticker IN ('KXBALLONDOR-26-HKAN','KXBALLONDOR-26-KMBA',
 'KXGOVCA-26-SHIL','KXGOVCA-26-XBEC','KXMAYORLA-26-KBAS',
 'KXNEXTTEAMNBA-26LJAM-CLE','KXNEXTTEAMNBA-26LJAM-GSW','KXNEXTTEAMNBA-26LJAM-IND',
 'KXNEXTTEAMNBA-26LJAM-LAC','KXNEXTTEAMNBA-26LJAM-MIN','KXNEXTTEAMNBA-26LJAM-PHI',
 'KXNEXTTEAMNBA-26LJAM-SAS','KXNEXTTEAMNBA-26LJAM-WAS',
 'KXPRESPERSON-28-GWHI','KXPRESPERSON-28-RDES')
ORDER BY ticker, source
LIMIT 100
