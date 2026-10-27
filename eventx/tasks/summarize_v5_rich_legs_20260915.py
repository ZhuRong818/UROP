"""Validate bounded metadata exports and preserve unresolved underlying identities."""
import hashlib
import json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
REC=ROOT/'data/v5/provenance_recovery_20260908'
OUT=ROOT/'data/v5/rich_leg_recovery_20260915'
def main():
    inputs=[]
    def read(name):
        receipt=REC/(name+'.json');r=json.loads(receipt.read_text())
        p=ROOT/r['data_path'];inputs.extend([receipt,p])
        assert r['status']=='complete' and hashlib.sha256(p.read_bytes()).hexdigest()==r['data_sha256']
        rows=[json.loads(l) for l in p.read_text().splitlines()]
        assert len(rows)==r['rows'] and len(rows)<1000
        return rows
    parents=[r for i in range(4) for r in read(f'rich_legs_{i:02d}_20260915')]
    underlying=read('rich_legs_underlying_20260915')
    target=ROOT/'data/v5/multileg_boundary_review_20260915/unresolved_multileg.jsonl';inputs.append(target)
    targets={json.loads(l)['market_id'] for l in target.read_text().splitlines()}
    assert len(parents)==len({r['ticker'] for r in parents})==397
    assert {r['ticker'] for r in parents}==targets
    refs=[]
    for r in parents:
        assert r['selected_legs']
        for i,leg in enumerate(r['selected_legs']):
            assert leg['market_ticker'] and leg['event_ticker'] and leg['side'] in ('yes','no')
            refs.append({'parent_market_id':r['ticker'],'parent_event_id':r['event_ticker'],
                'leg_index':i,**leg,'source_run_id':r['source_run_id'],'source_ingest_ts':r['ingest_ts'],
                'historical_semantics_certified':False})
    requested={r['market_ticker'] for r in refs};found={r['ticker'] for r in underlying}
    assert found<=requested and len(found)==len(underlying)
    conflicts=[r for r in refs for u in underlying if r['market_ticker']==u['ticker'] and r['event_ticker']!=u['event_ticker']]
    missing=sorted(requested-found)
    report={'parent_contracts_requested':397,'parent_contracts_returned':len(parents),
        'parents_with_explicit_legs':397,'leg_references':len(refs),'distinct_underlying_contracts':len(requested),
        'underlying_metadata_returned':len(found),'underlying_metadata_missing':len(missing),
        'event_identity_conflicts':len(conflicts),
        'parents_with_all_underlying_metadata':sum(all(l['market_ticker'] in found for l in r['selected_legs']) for r in parents),
        'parent_nonempty_primary_rules':sum(bool(r['rules_primary']) for r in parents),
        'parent_nonempty_secondary_rules':sum(bool(r['rules_secondary']) for r in parents),
        'underlying_nonempty_primary_rules':sum(bool(r['rules_primary']) for r in underlying),
        'underlying_nonempty_secondary_rules':sum(bool(r['rules_secondary']) for r in underlying),
        'final_family_certification':False,'family_graph_modified':False,
        'prediction_outcomes_requested':False,'holdouts_accessed':False}
    OUT.mkdir(exist_ok=False)
    for name,value in [('report.json',report),('missing_underlying_ids.json',missing),('event_identity_conflicts.json',conflicts)]:
        (OUT/name).write_text(json.dumps(value,indent=2)+'\n')
    for name,value in [('parent_metadata.jsonl',parents),('leg_references.jsonl',refs),('underlying_metadata.jsonl',underlying)]:
        (OUT/name).write_text(''.join(json.dumps(r)+'\n' for r in value))
    inputs+=[Path(__file__),*sorted((ROOT/'data/v5/rich_leg_queries_20260915').glob('*.sql'))]
    sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
    (OUT/'manifest.json').write_text(json.dumps({'inputs':{str(p.relative_to(ROOT)):sha(p) for p in inputs},
        'outputs':{p.name:sha(p) for p in OUT.iterdir()}},indent=2)+'\n')
    print(json.dumps(report,indent=2))
if __name__=='__main__':main()
