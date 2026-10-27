"""Rebuild development fetch priorities without context-only count inflation."""
import json
from collections import Counter, defaultdict
from pathlib import Path
from eventx.tasks.check_proposition_v03_development import read,digest
from eventx.v6.subject_retrieval import retrieve
from eventx.v6.subject_retrieval_v02 import subjects
from eventx.v6.clean_speech import clean
from eventx.v6.fetch_priority import mention_role,group_key

def main():
    base=Path('data/v6/expanded_coverage_20260919')
    for n,h in json.loads((base/'manifest.json').read_text()).items():assert digest(base/n)==h
    cp=Path('data/v6/contract_link_pilot_20260916/contract_cards.jsonl')
    cards={c['contract_id']:c for c in read(cp)}
    registry={k:subjects(c) for k,c in cards.items()}
    wp=Path('data/v6/window_reconciliation_20260921/pairs.jsonl')
    wm=json.loads((wp.parent/'manifest.json').read_text());assert digest(wp)==wm['outputs'][wp.name]
    windows={(r['article_id'],r['contract_id']):r['recovered_window_status'] for r in read(wp)}
    pairs=[];groups={};counts=Counter()
    for a in read(base/'articles.jsonl'):
        for cid,ev in retrieve(clean(a)[0],registry).items():
            card=cards[cid];role=mention_role(card,registry[cid],ev);counts[role]+=1
            window=windows.get((a['article_id'],cid),'unverified_window')
            pairs.append({'article_id':a['article_id'],'contract_id':cid,'role':role,'window':window})
            key=group_key(card)
            g=groups.setdefault(key,{'contracts':set(),'primary':set(),'context':set(),'within':set()})
            g['contracts'].add(cid)
            if role=='primary_mention':
                g['primary'].add(a['article_id'])
                if window=='within_recorded_window':g['within'].add(a['article_id'])
            elif role=='context_only':g['context'].add(a['article_id'])
    ranked=[{'group':k,'contract_ids':sorted(g['contracts']),'primary_article_ids':sorted(g['primary']),
        'primary_articles':len(g['primary']),'context_articles':len(g['context']),
        'within_window_primary_articles':len(g['within'])} for k,g in groups.items() if g['primary']]
    ranked.sort(key=lambda r:(-r['primary_articles'],r['group']))
    report={'pairs':len(pairs),'roles':dict(counts),'primary_event_groups':len(ranked),
        'selected_groups':min(40,len(ranked)),'admissions':0,
        'policy':'Unique primary-mention articles per source event; ID tie-break. Timing separate, unresolved grammar abstains. Metadata recovery priority, not trade/news eligibility or independent-family certification.'}
    out=Path('data/v6/fetch_priority_v2_20260921');out.mkdir(exist_ok=False)
    for name,rr in [('pairs',pairs),('ranked_groups',ranked),('fetch_queue',ranked[:40])]:
        (out/(name+'.jsonl')).write_text(''.join(json.dumps(r)+'\n' for r in rr))
    (out/'report.json').write_text(json.dumps(report,indent=2)+'\n')
    inputs=[cp,base/'manifest.json',wp,Path(__file__),Path('eventx/v6/fetch_priority.py')]
    (out/'manifest.json').write_text(json.dumps({'inputs':{str(p):digest(p) for p in inputs},'outputs':{p.name:digest(p) for p in out.iterdir()}},indent=2)+'\n')
    print(json.dumps(report,indent=2))

if __name__=='__main__':main()
