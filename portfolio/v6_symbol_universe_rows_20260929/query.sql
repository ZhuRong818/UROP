SELECT symbol, source, source_endpoint, valid_from, valid_to,
 is_actively_trading, is_etf, is_fund, source_run_id, ingest_ts
FROM reference.symbol_universe
WHERE symbol IN ('NVDA', 'MSTR')
ORDER BY symbol, valid_from, ingest_ts LIMIT 20
