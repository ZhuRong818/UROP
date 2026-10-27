import json
from pathlib import Path
from collections import Counter
from eventx.tasks.check_proposition_v03_development import read,digest
from eventx.v6.clean_speech import prepare

def main():
    out=Path('data/v6/clean_speech_20260919');out.mkdir(exist_ok=False)
    source=Path('data/v6/expanded_coverage_20260919')
    for name,h in json.loads((source/'manifest.json').read_text()).items():assert digest(source/name)==h
    rows=read(source/'candidates.jsonl');aa={r['article_id']:r for r in read(source/'articles.jsonl')}
    cp=Path('data/v6/contract_link_pilot_20260916/contract_cards.jsonl');cc={r['contract_id']:r for r in read(cp)}
    results=[];rank_inputs=[]
    for r in rows:
        a,new=prepare(aa[r['article_id']],cc[r['contract_id']])
        results.append({**r,'clean_relation':new})
        if new['status']=='event_channel_candidate':rank_inputs.append({'article_id':r['article_id'],'contract_id':r['contract_id'],'headline':a['headline'],'summary':a.get('summary')})
    report={'prior_pairs':len(rows),'retained_pairs':len(rank_inputs),'retained_articles':len({r['article_id'] for r in rank_inputs}),
            'reasons':dict(Counter(r['clean_relation']['reason'] for r in results)),
            'masked_pairs':sum(bool(r['clean_relation']['excluded_spans']) for r in results),'admissions':0,
            'scope':'fixed previous candidates only; cleaned pre-ranking inputs generated, neural scores not rerun'}
    for name,rr in [('cases',results),('ranking_inputs',rank_inputs)]:
        (out/(name+'.jsonl')).write_text(''.join(json.dumps(r)+'\n' for r in rr))
    (out/'report.json').write_text(json.dumps(report,indent=2)+'\n')
    (out/'manifest.json').write_text(json.dumps({'inputs':{str(p):digest(p) for p in [source/'manifest.json',cp,Path(__file__),Path('eventx/v6/clean_speech.py')]},'outputs':{p.name:digest(p) for p in out.iterdir()}},indent=2)+'\n')
    print(json.dumps(report,indent=2))

if __name__=='__main__':main()
