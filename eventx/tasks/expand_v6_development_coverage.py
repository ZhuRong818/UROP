"""Fixed 500-article development expansion, unchanged linking and cached metadata."""
import hashlib
import json
from pathlib import Path
from collections import Counter
from eventx.tasks.check_proposition_v03_development import read,digest
from eventx.v6.contracts import utc
from eventx.v6.subject_retrieval import retrieve
from eventx.v6.subject_retrieval_v02 import subjects,context_gate
from eventx.v6.relation_candidates import constraint
from eventx.v6.claim_period import assess

def main():
    out=Path('data/v6/expanded_coverage_20260919');out.mkdir(exist_ok=False)
    np=Path('data/v5/source_readiness_20260908/news_provenance_staging.jsonl')
    cp=Path('data/v6/contract_link_pilot_20260916/contract_cards.jsonl')
    ap=Path('data/v6/contract_link_pilot_20260916/articles.jsonl')
    rp=Path('data/v6/hybrid_audit_20260916/reserved_articles.jsonl')
    # Read reservation identifiers/hashes solely for exclusion; no content/labels emitted.
    reserved=[{k:r[k] for k in ('article_id','content_sha256')} for r in read(rp)]
    old=read(ap);excluded_ids={r['article_id'] for r in old+reserved}
    excluded_hashes={r['content_sha256'] for r in old+reserved}
    pool=[r for r in read(np) if r['article_id'] not in excluded_ids and r['content_sha256'] not in excluded_hashes and r['clock_consistent']
          and utc('2026-05-17T00:00:00Z')<=utc(r['source_clock_available_at'])<utc('2026-07-22T00:00:00Z')]
    selected=sorted(pool,key=lambda r:hashlib.sha256(('coverage-20260919|'+r['article_id']).encode()).hexdigest())[:500]
    assert len(selected)==500 and len({r['article_id'] for r in selected})==500
    code={str(p):digest(p) for p in sorted(Path('eventx/v6').glob('*.py'))}
    receipt={'selection':'first500 SHA256(coverage-20260919|article_id); no scores used',
             'scope':'opened discovery only; not independent confirmation; reserved IDs/content hashes excluded',
             'article_ids':[r['article_id'] for r in selected],'pool_size':len(pool),
             'inputs':{str(p):digest(p) for p in [np,cp,ap,rp,Path(__file__)]},'algorithm_hashes':code}
    (out/'selection_receipt.json').write_text(json.dumps(receipt,indent=2)+'\n')
    wanted={r['source_line']:r for r in selected};source=Path(selected[0]['source_file'])
    assert all(r['source_file']==str(source) for r in selected)
    articles=[]
    for line,raw in enumerate(source.open(),1):
        if line not in wanted:continue
        r=json.loads(raw);p=wanted[line];content={k:r.get(k) for k in ('headline','summary')}
        assert str(r['id'])==p['article_id']
        assert hashlib.sha256(json.dumps(content,sort_keys=True).encode()).hexdigest()==p['content_sha256']
        articles.append({**content,**p})
    assert len(articles)==500
    cards={r['contract_id']:r for r in read(cp)};registry={cid:subjects(c) for cid,c in cards.items()}
    rows=[];retrieved=retained=0
    for i,a in enumerate(articles):
        for cid,ev in retrieve(a,registry).items():
            retrieved+=1;c=cards[cid]
            if context_gate(a,c,ev)!='subject_context_candidate':continue
            retained+=1;r=constraint(a,c)
            if r['status']!='event_channel_candidate':continue
            rows.append({'article_id':a['article_id'],'contract_id':cid,'event_ids':c['event_ids'],
                         'relation':r,'claim_period':assess(a,c,r)})
        if i%100==0:print('processed',i,flush=True)
    updates=[r for r in rows if r['claim_period']['role']=='event_update_candidate' and r['claim_period']['period']['status']=='before_question_deadline']
    report={'sample_articles':500,'retrieved_pairs':retrieved,'context_retained_pairs':retained,
            'channel_pairs':len(rows),'channel_articles':len({r['article_id'] for r in rows}),
            'before_deadline_update_pairs':len(updates),'before_deadline_update_articles':len({r['article_id'] for r in updates}),
            'before_deadline_update_source_events':len({e for r in updates for e in r['event_ids']}),
            'roles':dict(Counter(r['claim_period']['role'] for r in rows)),
            'periods':dict(Counter(r['claim_period']['period']['status'] for r in rows)),
            'training_admissions':0,'neural_reranking':'not run; rank does not affect unchanged threshold-free candidate gates',
            'limits':['Coverage only, not precision or recall.','Source event IDs are not independent event certificates.','Nonexact story overlap with reserved data not certified; development only.']}
    assert all(digest(p)==h for p,h in code.items())
    (out/'articles.jsonl').write_text(''.join(json.dumps(a)+'\n' for a in articles))
    (out/'candidates.jsonl').write_text(''.join(json.dumps(r)+'\n' for r in rows))
    (out/'report.json').write_text(json.dumps(report,indent=2)+'\n')
    (out/'manifest.json').write_text(json.dumps({p.name:digest(p) for p in out.iterdir()},indent=2)+'\n')
    print(json.dumps(report,indent=2))

if __name__=='__main__':main()
