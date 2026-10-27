"""Opened development routing/evidence debug; no reference labels loaded."""
import json,hashlib
from pathlib import Path
from collections import Counter
from eventx.v6.multitype import parse,compare

def main():
    p=Path('data/v6/bounded_audit_20260917/relevance_review_packet.jsonl')
    out=Path('data/v6/multitype_debug_20260917')
    if out.exists():raise FileExistsError(out)
    rows=[]
    for line in p.read_text().splitlines():
        r=json.loads(line);c=parse(r['contract'])
        rows.append({'pair_id':r['pair_id'],'contract':c,'comparison':compare(r['article'],c)})
    report={'cases':len(rows),'type_hypotheses':dict(Counter(r['contract']['type_hypothesis'] for r in rows)),
            'subject_extracted':sum(bool(r['contract']['fields']['subject_mentions']) for r in rows),
            'time_mentions_extracted':sum(bool(r['contract']['fields']['time_mentions']) for r in rows),
            'predictive_admissions':0,'scope':'lexical development debug, not semantic accuracy'}
    out.mkdir()
    (out/'cases.jsonl').write_text(''.join(json.dumps(r)+'\n' for r in rows))
    (out/'report.json').write_text(json.dumps(report,indent=2)+'\n')
    sha=lambda x:hashlib.sha256(x.read_bytes()).hexdigest()
    inputs=[p,Path(__file__),Path('eventx/v6/multitype.py')]
    (out/'manifest.json').write_text(json.dumps({'inputs':{str(x):sha(x) for x in inputs},'outputs':{x.name:sha(x) for x in out.iterdir()}},indent=2)+'\n')
    print(json.dumps(report,indent=2))
if __name__=='__main__':main()
