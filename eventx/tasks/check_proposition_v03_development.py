"""Fixed, label-free development coverage check; never an accuracy audit."""
import hashlib
import json
from collections import Counter
from pathlib import Path
from eventx.v6.proposition_matcher_v03 import match


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def read(path):
    return [json.loads(line) for line in Path(path).read_text().splitlines() if line]


def main():
    source=Path('data/v6/hybrid_development_reviews_20260916/packet.jsonl')
    original=Path('data/v6/bounded_audit_20260917/relevance_review_packet.jsonl')
    old=Path('data/v6/proposition_v02_debug_20260917/cases.jsonl')
    out=Path('data/v6/proposition_v03_development_20260917')
    out.mkdir(exist_ok=False)
    regression=read(original)
    excluded={r['article']['article_id'] for r in regression}
    selected=sorted((r for r in read(source) if r['article']['article_id'] not in excluded),key=lambda r:r['pair_id'])
    assert len({r['pair_id'] for r in selected})==len(selected)
    inputs=[source,original,old,Path(__file__),Path('eventx/v6/proposition_matcher_v03.py'),Path('eventx/v6/proposition_matcher_v02.py'),Path('eventx/v6/proposition_matcher.py')]
    receipt={'scope':'opened development only; no labels or outcomes used',
             'selection':'census of development packet excluding all original 40 article IDs',
             'input_sha256':{str(p):digest(p) for p in inputs},
             'excluded_article_ids':sorted(excluded),'pair_ids':[r['pair_id'] for r in selected]}
    (out/'selection_receipt.json').write_text(json.dumps(receipt,indent=2)+'\n')
    reports={}
    for name,rows in [('broader',selected),('regression',regression)]:
        results=[{'pair_id':r['pair_id'],'article_id':r['article']['article_id'],
                  'headline':r['article']['headline'],'question':r['contract']['question'],
                  **match(r['article'],r['contract'])} for r in rows]
        (out/f'{name}_cases.jsonl').write_text(''.join(json.dumps(r)+'\n' for r in results))
        reports[name]={'pairs':len(rows),'articles':len({r['article_id'] for r in results}),
                       'semantic_status':dict(Counter(r['semantic_status'] for r in results)),
                       'semantic_reason':dict(Counter(r['semantic_reason'] for r in results)),
                       'eligibility':dict(Counter(r['eligibility'] for r in results)),
                       'predictive_admitted':sum(r['predictive_admitted'] for r in results),
                       'adapter_types':dict(Counter((r['extension'] or {}).get('kind','legacy') for r in results))}
    indexed={r['pair_id']:r for r in read(out/'regression_cases.jsonl')}
    unresolved=[{'pair_id':r['pair_id'],'old_reason':r['semantic_reason'],
                 'subject':r['specification']['subject'],
                 'alias_evidence':indexed[r['pair_id']]['alias_evidence'],
                 'article_alias_hits':indexed[r['pair_id']]['article_alias_hits'],
                 'new_reason':indexed[r['pair_id']]['semantic_reason']}
                for r in read(old) if r['semantic_reason']=='subject_not_resolved']
    (out/'subject_diagnosis.json').write_text(json.dumps(unresolved,indent=2)+'\n')
    reports['limitations']=['Coverage, not precision or recall.','Original 40 informed adapter development.',
                           'No independent evaluation or predictive admission.','Reserved packets and holdouts not read.']
    (out/'report.json').write_text(json.dumps(reports,indent=2)+'\n')
    manifest={p.name:digest(p) for p in sorted(out.iterdir()) if p.is_file()}
    (out/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
    print(json.dumps(reports,indent=2))


if __name__=='__main__':
    main()
