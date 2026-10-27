"""Recover rule text for exactly the 43 formerly missing sampled contracts."""
import json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
def main():
    pairs=list(map(json.loads,(ROOT/'data/v5/unresolved_pair_enrichment_20260915/enriched_pairs.jsonl').read_text().splitlines()))
    targets={c['market_id'] for p in pairs for s in ('left','right') for c in p[s]['contracts']}
    sampled=list(map(json.loads,(ROOT/'data/v5/provenance_recovery_20260908/reassessment_20260915_kalshi_quality.jsonl').read_text().splitlines()))
    ids=sorted(r['ticker'] for r in sampled if r['ticker'] in targets and r['primary_rule_chars'])
    assert len(ids)==43
    sql="""SELECT ticker,event_ticker,title,yes_sub_title,no_sub_title,
open_time,close_time,expiration_time,source,source_endpoint,source_run_id,ingest_ts,
raw->>'rules_primary' AS rules_primary, raw->>'rules_secondary' AS rules_secondary
FROM prediction_markets.kalshi_markets WHERE ticker IN ("""+','.join("'"+s.replace("'","''")+"'" for s in ids)+""" )
AND ingest_ts < TIMESTAMPTZ '2026-07-22T00:00:00Z'
ORDER BY ticker,ingest_ts LIMIT 1000
"""
    p=ROOT/'data/v5/design_reassessment_20260915/queries/recovered_rule_text.sql'
    assert not p.exists()
    p.write_text(sql)
if __name__=='__main__':main()
