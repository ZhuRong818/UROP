"""Recover only descriptive/provenance fields from exact cached source pointers."""
import json
from pathlib import Path
from collections import Counter
from eventx.tasks.check_proposition_v03_development import read,digest

def main():
    out=Path('data/v6/candidate_metadata_cache_20260919');out.mkdir(exist_ok=False)
    checks=Path('data/v6/candidate_yield_20260919/checks.jsonl')
    cards={r['contract_id']:r for r in read('data/v6/contract_link_pilot_20260916/contract_cards.jsonl')}
    ids={r['contract_id'] for r in read(checks)}
    keys={(cards[i]['venue'],cards[i]['market_id']) for i in ids}
    mp=Path('data/v5/source_readiness_20260908/metadata_staging.jsonl')
    targets=[r for r in read(mp) if (r['venue'],r['market_id']) in keys]
    fields=['id','condition_id','conditionId','ticker','market_id','question','title','subtitle','description',
            'rules_primary','rules_secondary','source_ingest_ts','ingest_ts','source_run_id','created_at','updated_at',
            'open_time','close_time','start_date','end_date','valid_from','valid_until']
    recovered=[];hashes={str(checks):digest(checks),str(mp):digest(mp),str(Path(__file__)):digest(Path(__file__))}
    for path in sorted({r['source_file'] for r in targets}):
        p=Path(path);hashes[path]=digest(p)
        byline={r['source_line']:r for r in targets if r['source_file']==path}
        for line,raw in enumerate(p.open(),1):
            if line not in byline:continue
            r=json.loads(raw);t=byline[line]
            # Do not output prices, results, settlement or other outcome fields.
            projection={k:r[k] for k in fields if k in r}
            possible=[str(r.get(k,'')) for k in ('ticker','market_id','condition_id','conditionId','id')]
            recovered.append({'venue':t['venue'],'market_id':t['market_id'],'source_file':path,'source_line':line,
                              'identifier_matches':str(t['market_id']) in possible,'descriptive_fields':projection,
                              'validity_certified':False})
    (out/'recovered.jsonl').write_text(''.join(json.dumps(r)+'\n' for r in recovered))
    report={'targets':len(targets),'recovered':len(recovered),'identifier_matches':sum(r['identifier_matches'] for r in recovered),
            'nonempty_field_counts':dict(Counter(k for r in recovered for k,v in r['descriptive_fields'].items() if v not in (None,''))),
            'certificates_created':0,'decision':'Descriptive snapshots alone cannot certify historical status/version intervals.',
            'provider_evidence_needed':['Exact contract text version available before each news availability time.',
                                        'Version validity intervals and historical open/close/trading status timeline.',
                                        'Replayable source lineage or authoritative immutable version identifiers.']}
    (out/'report.json').write_text(json.dumps(report,indent=2)+'\n')
    (out/'receipt.json').write_text(json.dumps(hashes,indent=2)+'\n')
    (out/'manifest.json').write_text(json.dumps({p.name:digest(p) for p in out.iterdir()},indent=2)+'\n')
    print(json.dumps(report,indent=2))

if __name__=='__main__':main()
