"""Opened development cases only; candidate matching, no new audit."""
import hashlib
import json
from collections import Counter
from pathlib import Path
from eventx.v6.proposition_matcher import match

def main():
    source=Path('data/v6/bounded_audit_20260917/relevance_review_packet.jsonl')
    out=Path('data/v6/proposition_matcher_debug_20260917')
    if out.exists():raise FileExistsError(out)
    sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
    frozen=json.loads((source.parent/'manifest.json').read_text())
    assert sha(source)==frozen['outputs'][source.name]
    rows=[]
    for line in source.read_text().splitlines():
        r=json.loads(line)
        rows.append({'pair_id':r['pair_id'],'headline':r['article']['headline'],
                     'question':r['contract']['question'],**match(r['article'],r['contract'])})
    report={'cases':len(rows),'status_counts':dict(Counter(r['status'] for r in rows)),
            'reason_counts':dict(Counter(r['reason'] for r in rows)),
            'proposed_direct_pair_ids':[r['pair_id'] for r in rows if r['status']=='direct_candidate'],
            'predictive_admissions':0,'independent_validation':False,
            'limits':'Known opened development cases; no precision/recall or independent evidence claimed.'}
    out.mkdir()
    (out/'cases.jsonl').write_text(''.join(json.dumps(r)+'\n' for r in rows))
    (out/'report.json').write_text(json.dumps(report,indent=2)+'\n')
    inputs=[source,Path(__file__),Path('eventx/v6/proposition_matcher.py'),Path('eventx/v6/multitype.py'),
            Path('eventx/v6/measurement_v02.py'),Path('eventx/v6/measurement_extractor.py')]
    (out/'manifest.json').write_text(json.dumps({'inputs':{str(p):sha(p) for p in inputs},
        'outputs':{p.name:sha(p) for p in out.iterdir()}},indent=2)+'\n')
    print(json.dumps(report,indent=2))
if __name__=='__main__':main()
