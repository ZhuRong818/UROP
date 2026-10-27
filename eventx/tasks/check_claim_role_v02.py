import json
from pathlib import Path
from collections import Counter
from eventx.tasks.check_proposition_v03_development import read,digest
from eventx.v6.claim_role_v02 import assess

def main():
    out=Path('data/v6/claim_role_v02_20260919');out.mkdir(exist_ok=False)
    source=Path('data/v6/expanded_coverage_20260919')
    for name,h in json.loads((source/'manifest.json').read_text()).items():assert digest(source/name)==h
    rows=read(source/'candidates.jsonl')
    for r in rows:r['role_v02']=assess(r['relation'])
    unique={}
    for r in rows:
        for x in r['role_v02']:unique[(r['article_id'],x['evidence']['field'],x['evidence']['start'],x['evidence']['end'])]=x
    report={'pairs':len(rows),'articles':len({r['article_id'] for r in rows}),
            'pair_role_counts':dict(Counter(x['role'] for r in rows for x in r['role_v02'])),
            'unique_evidence_role_counts':dict(Counter(x['role'] for x in unique.values())),
            'admissions':0,'limits':['Reported action is not verified fact or contract applicability.','Speech speaker/occasion binding remains unresolved.','Designed after inspecting opened development examples; not independent accuracy.']}
    (out/'cases.jsonl').write_text(''.join(json.dumps(r)+'\n' for r in rows))
    (out/'report.json').write_text(json.dumps(report,indent=2)+'\n')
    (out/'manifest.json').write_text(json.dumps({'inputs':{str(p):digest(p) for p in [source/'candidates.jsonl',Path(__file__),Path('eventx/v6/claim_role_v02.py')]},'outputs':{p.name:digest(p) for p in out.iterdir()}},indent=2)+'\n')
    print(json.dumps(report,indent=2))

if __name__=='__main__':main()
