SELECT COUNT(*) AS total_rows,
 COUNT(DISTINCT symbol) AS distinct_symbols,
 COUNT(*) FILTER (WHERE is_etf IS TRUE OR is_fund IS TRUE) AS etf_or_fund_rows,
 COUNT(*) FILTER (WHERE NOT (is_etf IS TRUE OR is_fund IS TRUE)) AS neither_etf_nor_fund_rows,
 COUNT(*) FILTER (WHERE is_actively_trading IS TRUE) AS active_rows,
 COUNT(*) FILTER (WHERE is_actively_trading IS TRUE AND NOT (is_etf IS TRUE OR is_fund IS TRUE)) AS active_plain_rows,
 MAX(ingest_ts) AS latest_ingest
FROM reference.symbol_universe
