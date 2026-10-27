"""Development semantic/eligibility diagnostics, never audit evaluation."""
import json,hashlib
from pathlib import Path
from collections import Counter
from eventx.v6.proposition_matcher_v02 import match

def main():
    p=Path('data/v6/bounded_audit_20260917/relevance_review_packet.jsonl')
    out=Path('data/v6/proposition_v02_debug_20260917')
    if out.exists():raise FileExistsError(out)
    rows=[]
    for line in p.read_text().splitlines():
        r=json.loads(line);rows.append({'pair_id':r['pair_id'],**match(r['article'],r['contract'])})
    report={'cases':len(rows),'semantic_status_counts':dict(Counter(r['semantic_status'] for r in rows)),
            'reason_counts':dict(Counter(r['semantic_reason'] for r in rows)),
            'eligibility_counts':dict(Counter(r['eligibility'] for r in rows)),
            'direct_candidate_ids':[r['pair_id'] for r in rows if r['semantic_status']=='direct_candidate'],
            'predictive_admissions':0,'independent_evaluation':False}
    out.mkdir()
    (out/'cases.jsonl').write_text(''.join(json.dumps(r)+'\n' for r in rows))
    (out/'report.json').write_text(json.dumps(report,indent=2)+'\n')
    sha=lambda x:hashlib.sha256(x.read_bytes()).hexdigest()
    deps=[p,Path(__file__),*[Path('eventx/v6')/s for s in ('proposition_matcher_v02.py','proposition_matcher.py','multitype.py','measurement_v02.py','measurement_extractor.py','selective_vnext.py','contracts.py')]]
    (out/'manifest.json').write_text(json.dumps({'inputs':{str(s):sha(s) for s in deps},
        'outputs':{s.name:sha(s) for s in out.iterdir()}},indent=2)+'\n')
    print(json.dumps(report,indent=2))
if __name__=='__main__':main()
