"""Development-only overlap inventory and bounded metadata fetch plan."""
import json
from pathlib import Path
from collections import Counter
from eventx.tasks.check_proposition_v03_development import read, digest
from eventx.v6.subject_retrieval import retrieve
from eventx.v6.subject_retrieval_v02 import subjects
from eventx.v6.clean_speech import clean
from eventx.v6.contracts import utc

def main():
    out=Path('data/v6/targeted_recovery_20260921');out.mkdir(exist_ok=False)
    base=Path('data/v6/expanded_coverage_20260919')
    for n,h in json.loads((base/'manifest.json').read_text()).items():assert digest(base/n)==h
    cp=Path('data/v6/contract_link_pilot_20260916/contract_cards.jsonl')
    cards={r['contract_id']:r for r in read(cp)}
    registry={k:subjects(c) for k,c in cards.items()}
    counts=Counter(); per={}; pairs=[]
    for a in read(base/'articles.jsonl'):
        for cid in retrieve(clean(a)[0],registry):
            c=cards[cid]; close=c['terminal_fields'].get('close_time')
            state='close_missing' if not close else ('before_recorded_close' if utc(a['source_clock_available_at'])<utc(close) else 'at_or_after_recorded_close')
            counts[state]+=1
            per.setdefault(cid,Counter())[state]+=1
            pairs.append({'article_id':a['article_id'],'contract_id':cid,'time_screen':state})
    # Prioritize evidence gaps among temporally plausible subject matches, not outcome gains.
    target=sorted(per,key=lambda k:(-per[k]['before_recorded_close'],k))[:40]
    ids={v:[cards[k]['market_id'] for k in target if cards[k]['venue']==v] for v in ('kalshi','polymarket')}
    quote=lambda vv:','.join("'"+v.replace("'","''")+"'" for v in vv)
    queries={
      'kalshi':"SELECT ticker,event_ticker,title,yes_sub_title,open_time,close_time,expiration_time,ingest_ts,source,source_endpoint,source_run_id,raw->>'rules_primary' AS rules_primary,raw->>'rules_secondary' AS rules_secondary FROM prediction_markets.kalshi_markets WHERE ticker IN ({ids}) AND ingest_ts < '2026-07-22T00:00:00Z' ORDER BY ticker,ingest_ts LIMIT 500",
      'polymarket':"SELECT condition_id,question,ingest_ts,source,source_endpoint,source_run_id,raw->>'description' AS description,raw->>'startDate' AS start_date,raw->>'endDate' AS end_date,raw->>'resolutionSource' AS resolution_source FROM prediction_markets.polymarket_markets WHERE condition_id IN ({ids}) AND ingest_ts < '2026-07-22T00:00:00Z' ORDER BY condition_id,ingest_ts LIMIT 500"}
    for v in ids:
        if ids[v]:(out/(v+'.sql')).write_text(queries[v].format(ids=quote(ids[v]))+'\n')
    rows=[{'contract_id':k,'market_id':cards[k]['market_id'],'venue':cards[k]['venue'],'question':cards[k]['question'],'counts':dict(per[k])} for k in target]
    (out/'fetch_targets.json').write_text(json.dumps(rows,indent=2)+'\n')
    (out/'overlap_pairs.jsonl').write_text(''.join(json.dumps(r)+'\n' for r in pairs))
    report={'cards':len(cards),'subject_covered_cards':sum(bool(v) for v in registry.values()),'sample_articles':500,'subject_matched_contracts':len(per),'time_screen_pair_counts':dict(counts),'metadata_targets':{v:len(ids[v]) for v in ids},'admissions':0,'limits':'Subject and close-time screening only; opening time/PIT validity unproven. Not relevance or source completeness. News/trade expansion awaits interval evidence.'}
    (out/'report.json').write_text(json.dumps(report,indent=2)+'\n')
    (out/'manifest.json').write_text(json.dumps({'inputs':{str(p):digest(p) for p in [cp,base/'manifest.json',Path(__file__)]},'outputs':{p.name:digest(p) for p in out.iterdir()}},indent=2)+'\n')
    print(json.dumps(report,indent=2))

if __name__=='__main__':main()
