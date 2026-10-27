"""Build bounded source-only metadata queries for exact previously reviewed IDs."""
import json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
def main():
    targets=sorted(json.loads(l)['market_id'] for l in (ROOT/'data/v5/multileg_boundary_review_20260915/unresolved_multileg.jsonl').read_text().splitlines())
    out=ROOT/'data/v5/rich_leg_queries_20260915';out.mkdir(exist_ok=False)
    for i in range(0,len(targets),100):
        ids=','.join("'"+t.replace("'","''")+"'" for t in targets[i:i+100])
        sql="""SELECT ticker, event_ticker, open_time, close_time, expiration_time,
 source, source_endpoint, source_run_id, ingest_ts,
 raw->'mve_selected_legs' AS selected_legs,
 raw->>'rules_primary' AS rules_primary,
 raw->>'rules_secondary' AS rules_secondary
FROM prediction_markets.kalshi_markets
WHERE ticker IN ("""+ids+")\nORDER BY ticker, ingest_ts\nLIMIT 1000\n"
        (out/f'batch_{i//100:02d}.sql').write_text(sql)
    print('Prepared four exact-ID metadata queries')
if __name__=='__main__':main()
