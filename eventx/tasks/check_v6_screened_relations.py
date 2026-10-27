"""Existing relation diagnostic on clock-screened development pairs, not an audit."""
import json
from pathlib import Path
from collections import Counter
from eventx.tasks.check_proposition_v03_development import read,digest
from eventx.v6.clean_speech import prepare
from eventx.v6.claim_role_v02 import assess

def main():
    base=Path('data/v6/queue_windows_20260921')
    m=json.loads((base/'manifest.json').read_text())
    for p,h in m['inputs'].items():assert digest(Path(p))==h
    for n,h in m['outputs'].items():assert digest(base/n)==h
    ap=Path('data/v6/expanded_coverage_20260919/articles.jsonl')
    cp=Path('data/v6/contract_link_pilot_20260916/contract_cards.jsonl')
    aa={a['article_id']:a for a in read(ap)};cc={c['contract_id']:c for c in read(cp)}
    rows=[]
    for p in read(base/'pairs.jsonl'):
        if p['role']!='primary_mention' or p['screen']!='within_bounds':continue
        _,r=prepare(aa[p['article_id']],cc[p['contract_id']])
        rows.append({**p,'relation':r,'claim_roles':assess(r)})
    def summarize(rr):
        return {'pairs':len(rr),'articles':len({r['article_id'] for r in rr}),
            'reasons':dict(Counter(r['relation']['reason'] for r in rr)),
            'channel_candidates':sum(r['relation']['status']=='event_channel_candidate' for r in rr)}
    report={'within_bounds':summarize(rows),'snapshot_precedes_article':summarize([r for r in rows if r['snapshot_precedes_article']]),
        'admissions':0,'limits':'Existing lexical checks only; no measured precision/recall. Original cards retained; recovered rules not integrated. Polymarket times nominal.'}
    out=Path('data/v6/screened_relations_20260921');out.mkdir(exist_ok=False)
    (out/'cases.jsonl').write_text(''.join(json.dumps(r)+'\n' for r in rows))
    (out/'report.json').write_text(json.dumps(report,indent=2)+'\n')
    inputs=[base/'manifest.json',ap,cp,Path(__file__),Path('eventx/v6/clean_speech.py'),Path('eventx/v6/relation_candidates.py')]
    (out/'manifest.json').write_text(json.dumps({'inputs':{str(p):digest(p) for p in inputs},'outputs':{p.name:digest(p) for p in out.iterdir()}},indent=2)+'\n')
    print(json.dumps(report,indent=2))

if __name__=='__main__':main()
