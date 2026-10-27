"""Cached provenance and distinct-article yield; no outcome or certification writes."""
import json
from pathlib import Path
from collections import Counter
from eventx.tasks.check_proposition_v03_development import read,digest
from eventx.v6.contracts import utc

def main():
    out=Path('data/v6/candidate_yield_20260919');out.mkdir(exist_ok=False)
    prior=Path('data/v6/claim_period_20260919')
    for name,h in json.loads((prior/'manifest.json').read_text()).items():assert digest(prior/name)==h
    cp=Path('data/v6/contract_link_pilot_20260916/contract_cards.jsonl')
    dp=Path('data/v6/hybrid_development_reviews_20260916/packet.jsonl')
    np=Path('data/v5/source_readiness_20260908/news_provenance_staging.jsonl')
    mp=Path('data/v5/source_readiness_20260908/metadata_staging.jsonl')
    rows=[r for r in read(prior/'cases.jsonl') if r['constraint']['status']=='event_channel_candidate']
    cards={r['contract_id']:r for r in read(cp)}
    articles={r['article']['article_id']:r['article'] for r in read(dp)}
    aids={r['article_id'] for r in rows}
    news={r['article_id']:r for r in read(np) if r['article_id'] in aids}
    metadata={(r['venue'],r['market_id']):r for r in read(mp)}
    checks=[]
    for r in rows:
        a=articles[r['article_id']];c=cards[r['contract_id']];n=news.get(r['article_id']);m=metadata.get((c['venue'],c['market_id']))
        checks.append({'article_id':r['article_id'],'contract_id':r['contract_id'],
            'event_ids':c['event_ids'],'provisional_group':c['provisional_split_group'],
            'role':r['claim_period']['role'],'period':r['claim_period']['period']['status'],
            'article_provenance_found':n is not None,
            'article_hash_matches':bool(n and n['content_sha256']==a['content_sha256']),
            'article_clock_matches':bool(n and n['source_clock_available_at']==a['source_clock_available_at']),
            'metadata_found':m is not None,'metadata_question_matches':bool(m and m['question']==c['question']),
            'metadata_ingested_after_article':bool(m and m.get('source_ingest_ts') and utc(m['source_ingest_ts'])>utc(a['source_clock_available_at'])),
            'pit_certificate_present':bool(c.get('pit_certificate')),
            'metadata_missing_proofs':m.get('missing_proofs',[]) if m else ['metadata_not_found'],
            'source_run_id':n.get('source_run_id') if n else None,
            'training_admissible':False})
    def coverage(rs):
        return {'pairs':len(rs),'articles':len({r['article_id'] for r in rs}),
                'contracts':len({r['contract_id'] for r in rs}),
                'source_event_ids':len({e for r in rs for e in r['event_ids']}),
                'provisional_groups':len({r['provisional_group'] for r in rs})}
    updates=[r for r in checks if r['role']=='event_update_candidate' and r['period']=='before_question_deadline']
    report={'fixed_article_denominator':160,'all_channel_candidates':coverage(checks),
            'before_deadline_updates':coverage(updates),
            'before_deadline_opinions':coverage([r for r in checks if r['role']=='opinion_or_attributed_assessment' and r['period']=='before_question_deadline']),
            'pair_checks':{k:sum(r[k] for r in checks) for k in ['article_provenance_found','article_hash_matches','article_clock_matches','metadata_found','metadata_question_matches','metadata_ingested_after_article','pit_certificate_present']},
            'missing_proofs':dict(Counter(x for r in checks for x in r['metadata_missing_proofs'])),
            'training_admissions':0,'limits':['Source IDs and provisional groups are not independent events.','No retrieval recall or accuracy claim.','News-content assurance remains provisionally accepted; old null certificate fields do not revoke it.','Snapshot later than article is not proof that the market did not exist then.']}
    (out/'checks.jsonl').write_text(''.join(json.dumps(r)+'\n' for r in checks))
    (out/'report.json').write_text(json.dumps(report,indent=2)+'\n')
    (out/'receipt.json').write_text(json.dumps({'hashes':{str(p):digest(p) for p in [cp,dp,np,mp,prior/'cases.jsonl',Path(__file__)]},'scope':'cached development provenance only'},indent=2)+'\n')
    (out/'manifest.json').write_text(json.dumps({p.name:digest(p) for p in out.iterdir()},indent=2)+'\n')
    print(json.dumps(report,indent=2))

if __name__=='__main__':main()
