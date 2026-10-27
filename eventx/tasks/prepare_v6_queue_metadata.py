"""Prepare bounded descriptive recovery for the corrected fetch queue."""
import json
from pathlib import Path
from eventx.tasks.check_proposition_v03_development import read,digest

def main():
    base=Path('data/v6/fetch_priority_v2_20260921')
    m=json.loads((base/'manifest.json').read_text())
    for n,h in m['outputs'].items():assert digest(base/n)==h
    cards={c['contract_id']:c for c in read(Path('data/v6/contract_link_pilot_20260916/contract_cards.jsonl'))}
    oldp=Path('data/v5/provenance_recovery_20260908/v6_targeted_metadata_20260921.json')
    old=json.loads(oldp.read_text());assert digest(Path(old['data_path']))==old['data_sha256']
    cached={'kalshi:contract:'+r['ticker'] for r in read(Path(old['data_path']))}
    wanted={cid for g in read(base/'fetch_queue.jsonl') for cid in g['contract_ids']}
    out=Path('data/v6/queue_metadata_20260921');out.mkdir(exist_ok=False)
    template={
        'kalshi':"SELECT ticker,event_ticker,title,yes_sub_title,open_time,close_time,expiration_time,ingest_ts,source,source_endpoint,source_run_id,raw->>'rules_primary' AS rules_primary,raw->>'rules_secondary' AS rules_secondary FROM prediction_markets.kalshi_markets WHERE ticker",
        'polymarket':"SELECT condition_id,question,ingest_ts,source,source_endpoint,source_run_id,raw->>'description' AS description,raw->>'startDate' AS start_date,raw->>'endDate' AS end_date,raw->>'resolutionSource' AS resolution_source FROM prediction_markets.polymarket_markets WHERE condition_id"}
    batches=[]
    for venue in template:
        ids=sorted(cards[c]['market_id'] for c in wanted-cached if cards[c]['venue']==venue)
        for i in range(0,len(ids),50):
            part=ids[i:i+50];name=f'{venue}_{i//50:02d}'
            values=','.join("'"+v.replace("'","''")+"'" for v in part)
            sql=template[venue]+f" IN ({values}) AND ingest_ts < '2026-07-22T00:00:00Z' LIMIT 500\n"
            (out/(name+'.sql')).write_text(sql)
            batches.append({'name':name,'venue':venue,'ids':part})
    plan={'contracts':len(wanted),'reuse':len(wanted&cached),'requested':len(wanted-cached),'batches':batches}
    (out/'plan.json').write_text(json.dumps(plan,indent=2)+'\n')
    (out/'manifest.json').write_text(json.dumps({'inputs':{str(base/'manifest.json'):digest(base/'manifest.json'),str(oldp):digest(oldp)},'outputs':{p.name:digest(p) for p in out.iterdir()}},indent=2)+'\n')
    print(json.dumps({k:v for k,v in plan.items() if k!='batches'}));print([b['name'] for b in batches])

if __name__=='__main__':main()
