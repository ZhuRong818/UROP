"""Opened-case extraction debug only; no labels or forecast outcomes."""
import hashlib
import json
from pathlib import Path
from collections import Counter
from eventx.v6.measurement_v02 import company_registry, assess_card

def main():
    p=Path('data/v6/bounded_audit_20260917/relevance_review_packet.jsonl')
    out=Path('data/v6/measurement_v02_debug_20260917')
    if out.exists():raise FileExistsError(out)
    rows=[json.loads(x) for x in p.read_text().splitlines()]
    registry,evidence=company_registry([r['contract'] for r in rows])
    results=[{'pair_id':r['pair_id'],**assess_card(r['article'],r['contract'],registry)} for r in rows]
    report={'cases':len(results),'status_counts':dict(Counter(r['semantic_status'] for r in results)),
            'reason_counts':dict(Counter(r['reason'] for r in results)),
            'registry':registry,'predictive_admissions':0,'independent_evaluation':False}
    out.mkdir()
    for name,value in [('cases',results),('alias_evidence',evidence)]:
        (out/f'{name}.jsonl').write_text(''.join(json.dumps(r)+'\n' for r in value))
    (out/'report.json').write_text(json.dumps(report,indent=2)+'\n')
    sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
    sources=[p,Path(__file__),Path('eventx/v6/measurement_v02.py'),Path('eventx/v6/measurement_extractor.py')]
    (out/'manifest.json').write_text(json.dumps({'inputs':{str(s):sha(s) for s in sources},
        'outputs':{s.name:sha(s) for s in out.iterdir()}},indent=2)+'\n')
    print(json.dumps(report,indent=2))
if __name__=='__main__':main()
