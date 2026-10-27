"""Diagnostic clocks and field gaps; never certifies trading eligibility."""
import json
from pathlib import Path
from collections import Counter
from eventx.tasks.check_proposition_v03_development import read,digest
from eventx.v6.contracts import utc

def main():
    root=Path('data/v5/provenance_recovery_20260908');inputs={};meta={}
    for name in ['v6_targeted_metadata_20260921','v6_queue_kalshi_00_20260921','v6_queue_kalshi_01_20260921','v6_queue_polymarket_00_20260921']:
        rp=root/(name+'.json');r=json.loads(rp.read_text());p=Path(r['data_path'])
        assert r['status']=='complete' and digest(p)==r['data_sha256']
        inputs[str(rp)]=digest(rp);inputs[str(p)]=digest(p)
        for x in read(p):
            venue='kalshi' if 'ticker' in x else 'polymarket'
            cid=venue+':contract:'+x.get('ticker',x.get('condition_id'))
            assert cid not in meta
            meta[cid]={**x,'venue':venue}
    base=Path('data/v6/fetch_priority_v2_20260921')
    for n,h in json.loads((base/'manifest.json').read_text())['outputs'].items():assert digest(base/n)==h
    wanted={cid for g in read(base/'fetch_queue.jsonl') for cid in g['contract_ids']}
    assert wanted<=meta.keys() and len(wanted)==134
    ap=Path('data/v6/expanded_coverage_20260919/articles.jsonl')
    assert digest(ap)==json.loads((ap.parent/'manifest.json').read_text())[ap.name]
    aa={a['article_id']:a for a in read(ap)};rows=[];gaps=[]
    for cid in sorted(wanted):
        r=meta[cid];missing=[]
        if not (r.get('rules_primary') or r.get('description')):missing.append('rules')
        if not (r.get('close_time') or r.get('end_date')):missing.append('end')
        if missing:gaps.append({'contract_id':cid,'missing':missing,'record':r})
    for pair in read(base/'pairs.jsonl'):
        if pair['contract_id'] not in wanted:continue
        r=meta[pair['contract_id']];t=utc(aa[pair['article_id']]['source_clock_available_at'])
        start=r.get('open_time') or r.get('start_date');end=r.get('close_time') or r.get('end_date')
        try:
            lo=utc(start) if start else None;hi=utc(end) if end else None
            status='missing_bound' if lo is None or hi is None else 'invalid_interval' if lo>=hi else 'before_start' if t<lo else 'at_or_after_end' if t>=hi else 'within_bounds'
        except ValueError:status='unparseable_or_timezone_missing'
        rows.append({**pair,'venue':r['venue'],'bound_semantics':'recorded_open_close' if r['venue']=='kalshi' else 'nominal_start_end',
            'screen':status,'snapshot_precedes_article':utc(r['ingest_ts'])<=t,'admitted':False})
    out=Path('data/v6/queue_windows_20260921');out.mkdir(exist_ok=False)
    report={'contracts':len(wanted),'pairs':len(rows),'by_venue':{v:dict(Counter(r['screen'] for r in rows if r['venue']==v)) for v in ('kalshi','polymarket')},
        'primary_within_bounds':sum(r['role']=='primary_mention' and r['screen']=='within_bounds' for r in rows),
        'primary_within_bounds_snapshot_precedes':sum(r['role']=='primary_mention' and r['screen']=='within_bounds' and r['snapshot_precedes_article'] for r in rows),
        'gap_contracts':len(gaps),'admissions':0}
    for name,data in [('pairs',rows),('gaps',gaps)]:
        (out/(name+'.jsonl')).write_text(''.join(json.dumps(r)+'\n' for r in data))
    for venue in ('kalshi','polymarket'):
        rr=[r for r in gaps if r['record']['venue']==venue]
        if not rr:continue
        key='ticker' if venue=='kalshi' else 'condition_id'
        ids=','.join("'"+r['record'][key].replace("'","''")+"'" for r in rr)
        fields="raw->>'rules_primary' AS rules_primary,raw->>'rules_secondary' AS rules_secondary,raw->>'rules' AS alternative_rules" if venue=='kalshi' else "raw->>'endDate' AS end_date,raw->>'endDateIso' AS end_date_iso,raw->>'closeTime' AS close_time,raw->>'description' AS description"
        (out/(venue+'_gaps.sql')).write_text(f"SELECT {key},ingest_ts,{fields} FROM prediction_markets.{venue}_markets WHERE {key} IN ({ids}) AND ingest_ts < '2026-07-22T00:00:00Z' LIMIT 100\n")
    (out/'report.json').write_text(json.dumps(report,indent=2)+'\n')
    inputs.update({str(ap):digest(ap),str(base/'manifest.json'):digest(base/'manifest.json'),str(Path(__file__)):digest(Path(__file__))})
    (out/'manifest.json').write_text(json.dumps({'inputs':inputs,'outputs':{p.name:digest(p) for p in out.iterdir()}},indent=2)+'\n')
    print(json.dumps(report,indent=2))

if __name__=='__main__':main()
