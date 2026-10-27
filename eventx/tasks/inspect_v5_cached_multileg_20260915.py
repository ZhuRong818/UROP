"""Inspect allowlisted historical metadata caches, not trades or held-out payloads."""
from collections import Counter
import hashlib
import json
from pathlib import Path

ROOT=Path(__file__).resolve().parents[2]
TARGET=ROOT/'data/v5/multileg_boundary_review_20260915/unresolved_multileg.jsonl'
BASE=ROOT/'data/v3_historical/feasibility/raw/kalshi_markets'
OUT=ROOT/'data/v5/cached_multileg_inspection_20260915'

def main():
    targets={json.loads(l)['market_id'] for l in TARGET.read_text().splitlines()}
    paths=[BASE/'kalshi_markets.jsonl', *sorted((BASE/'pages').glob('page_*.jsonl'))]
    records={t:[] for t in targets}; inventory=[]
    structural={'legs','mve_selected_legs','selected_markets','underlying_market_ids',
                'rules_primary','rules_secondary','settlement_rules','cancellation_rules','raw'}
    for p in paths:
        keys=Counter(); matched=0
        for line_no,line in enumerate(p.open(),1):
            row=json.loads(line)
            if row.get('ticker') not in targets:continue
            matched+=1;keys.update(row.keys())
            records[row['ticker']].append({'file':str(p.relative_to(ROOT)), 'line':line_no,
                'fields':{k:row.get(k) for k in ('event_ticker','title','yes_sub_title','no_sub_title',
                    'open_time','close_time','expiration_time','ingest_ts','source','source_endpoint')},
                'structural_fields_present':sorted(structural & row.keys())})
        inventory.append({'path':str(p.relative_to(ROOT)),'target_records':matched,'target_field_counts':dict(keys)})
    details=[]
    for t,rs in sorted(records.items()):
        details.append({'market_id':t,'cached_records':rs,
            'underlying_leg_ids_recovered':False,'per_leg_dates_recovered':False,
            'rules_recovered':False,'status':'metadata_projection_only' if rs else 'no_matching_cached_record'})
    # Fail rather than silently treating an unexpected richer record as missing.
    assert not any(r['structural_fields_present'] for rs in records.values() for r in rs)
    canonical={r['market_id']:r['cached_records'][0]['fields'] for r in details if r['cached_records']}
    report={'target_contracts':len(targets),'contracts_found':len(canonical),
        'files_scanned':len(paths),'matching_records_including_page_duplicates':sum(len(x) for x in records.values()),
        'nonempty_contract_timestamps':{k:sum(bool(r[k]) for r in canonical.values()) for k in ('open_time','close_time','expiration_time','ingest_ts')},
        'explicit_leg_ids':0,'per_leg_polarity_mappings':0,'per_leg_event_dates':0,'resolution_or_cancellation_rules':0,
        'raw_payload_fields':0,'source_counts':dict(Counter(r['source'] for r in canonical.values())),
        'conclusion':'Fetched projection omitted leg structure and rules; contract timestamps are not per-leg event dates.',
        'scope':'Historical Kalshi metadata consolidated cache and its source pages only; not an exhaustive search of every repository file.',
        'provider_contacted':False,'heldout_payloads_or_outcomes_accessed':False}
    OUT.mkdir(exist_ok=False)
    for name,obj in [('report.json',report),('file_inventory.json',inventory)]:
        (OUT/name).write_text(json.dumps(obj,indent=2)+'\n')
    (OUT/'contract_evidence.jsonl').write_text(''.join(json.dumps(r)+'\n' for r in details))
    inputs=[TARGET,*paths,Path(__file__),*sorted((BASE/'pages').glob('query_*.sql'))]
    sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
    (OUT/'manifest.json').write_text(json.dumps({'inputs':{str(p.relative_to(ROOT)):sha(p) for p in inputs},
        'outputs':{p.name:sha(p) for p in OUT.iterdir()}},indent=2)+'\n')
    print(json.dumps(report,indent=2))

if __name__=='__main__':main()
