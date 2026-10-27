"""Run bounded extraction on opened cases without loading reviewer labels."""
import hashlib
import json
import re
from collections import Counter
from pathlib import Path
from eventx.v6.measurement_extractor import assess

def main():
    source=Path('data/v6/bounded_audit_20260917/relevance_review_packet.jsonl')
    out=Path('data/v6/measurement_extraction_debug_20260917')
    if out.exists(): raise FileExistsError(out)
    packet=[json.loads(x) for x in source.read_text().splitlines()]
    registry={}
    # Explicit subject of the supported contract grammar only. No invented ticker
    # aliases, external lookups, NER claims or reading reviewer labels.
    for p in packet:
        m=re.match(r'^Will (.+?) report\b',p['contract']['question'])
        if m:
            name=m[1].strip(); key='company:'+re.sub(r'\W+','_',name.casefold()).strip('_')
            registry[key]=[name]  # exact-only; short names need separately evidenced alias
    rows=[]
    for p in packet:
        a='\n'.join(p['article'].get(k) or '' for k in ('headline','summary'))
        c=p['contract']['question']
        rows.append({'pair_id':p['pair_id'], **assess(a,c,registry)})
    report={'cases':len(rows),'semantic_status_counts':dict(Counter(r['semantic_status'] for r in rows)),
        'entity_registry':registry,'predictive_admissions':0,'independent_evaluation':False,
        'scope':'Development debug, exact names and explicit quarterly measurement grammar only; no new audit.'}
    out.mkdir()
    (out/'cases.jsonl').write_text(''.join(json.dumps(r)+'\n' for r in rows))
    (out/'report.json').write_text(json.dumps(report,indent=2)+'\n')
    paths=[source,Path(__file__),Path('eventx/v6/measurement_extractor.py')]
    sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
    (out/'manifest.json').write_text(json.dumps({'inputs':{str(p):sha(p) for p in paths},
        'outputs':{p.name:sha(p) for p in out.iterdir()}},indent=2)+'\n')
    print(json.dumps(report,indent=2))

if __name__=='__main__':main()
