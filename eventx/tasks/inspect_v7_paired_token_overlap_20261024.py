"""Investigate the sole pooled-activity promotion without admitting executions."""
from collections import Counter
from datetime import datetime
import json
from pathlib import Path
from eventx.tasks.discover_v7_direct_pilot_20261022 import REPO_ROOT,now,sha,write
from eventx.tasks.explore_v7_alternative_inputs_20261024 import stamp

OUT=REPO_ROOT/'data/v7/paired_token_overlap_20261024'
INPUT=REPO_ROOT/'data/v7/alternative_inputs_20261024'
AUDIT=REPO_ROOT/'data/v7/direct_source_pilot_20261022_v03/audits/20261024T060327Z_808a25'
RELEASE=REPO_ROOT/'eventx/release/v7/direct_source_pilot_20261022_v03'

def main():
    for manifest in [INPUT/'manifest.json',AUDIT/'manifest.json']:
        for p,h in json.loads(manifest.read_text())['files'].items():
            if sha(REPO_ROOT/p)!=h:raise RuntimeError('Input hash mismatch')
    rows=[json.loads(l) for l in (INPUT/'grids.jsonl').read_text().splitlines()]
    chosen=[r for r in rows if r['source']=='completed_v03' and r['role']=='prospective_macro_candidate' and
        r['trade_features'] and r['trade_features']['pooled']['raw_activity_screen'] and not r['trade_features']['yes']['raw_activity_screen']]
    if len(chosen)!=1:raise RuntimeError('Unexpected diagnostic population')
    grid=chosen[0];cid=grid['market_id'];t=stamp(grid['grid_at'])
    sample=next(json.loads(l) for l in (RELEASE/'sample.jsonl').read_text().splitlines() if json.loads(l)['market_id']==cid)
    requests={};summaries=[]
    with (AUDIT/'journal.jsonl').open() as f:
        for line in f:
            r=json.loads(line)
            if r.get('market_id')!=cid or r.get('source')!='venue':continue
            if r['kind']=='rest' and r['endpoint_kind']=='trades':requests.setdefault(r['cycle'],[]).append(r)
            elif r['kind']=='window_summary' and r['endpoint_window_returned'] and r['end']-r['start']>=14400:summaries.append(r)
    options=[]
    for w in summaries:
        rs=requests.get(w['cycle'],[])
        if len(rs)!=1 or rs[0].get('status')!='observed':continue
        r=rs[0];av=max(stamp(r['available_at']),stamp(w['at']))
        if av<=t:options.append((av,w,r))
    _,w,r=max(options,key=lambda x:x[0]);run=REPO_ROOT/json.loads((AUDIT/'report.json').read_text())['run']
    p=run/'objects'/r['payload_sha256']
    if sha(p)!=r['payload_sha256']:raise RuntimeError('Payload mismatch')
    sets={'yes':Counter(),'no':Counter()};details=[]
    for x in json.loads(p.read_text())['data']:
        ts=stamp(x['timestamp'])
        if not t-14400<ts<=t:continue
        side='yes' if str(x['token_id'])==sample['yes_asset_id'] else 'no'
        rawside=x['side'].upper();canonical_side=rawside if side=='yes' else ('SELL' if rawside=='BUY' else 'BUY')
        px=float(x['price']) if side=='yes' else 1-float(x['price'])
        tx=x.get('transaction_hash',x.get('transactionHash'))
        if not tx:raise RuntimeError('Missing transaction identity')
        key=(tx,ts,round(px,9),round(float(x['size']),6),canonical_side)
        sets[side][key]+=1
        details.append({'outcome_side':side,'transaction_hash':tx,'timestamp':ts,'yes_oriented_price':px,
            'size':float(x['size']),'raw_side':rawside,'yes_oriented_side':canonical_side,'in_last60m':ts>t-3600})
    paired=sets['yes']&sets['no']
    paired60=sum(v for k,v in paired.items() if k[1]>t-3600)
    report={'at':now().isoformat(),'market_id':cid,'question':grid['question'],'grid_at':grid['grid_at'],
        'selected_payload':str(p.relative_to(REPO_ROOT)),'selected_payload_sha256':sha(p),
        'yes_records240m':sum(sets['yes'].values()),'no_records240m':sum(sets['no'].values()),
        'cross_token_fingerprint_pairs240m':sum(paired.values()),'cross_token_fingerprint_pairs60m':paired60,
        'distinct_transactions240m':len({x['transaction_hash'] for x in details}),
        'fingerprint':'transaction+timestamp+YES-oriented price rounded9dp+quantity rounded6dp+YES-oriented BUY/SELL',
        'conclusion':'Identical cross-token transaction/economic signatures make naive pooling unsuitable as an eligibility improvement. This is overlap evidence, not certified execution deduplication.',
        'predictive_admissions':0,'labels_computed':False}
    OUT.mkdir(parents=True,exist_ok=False);write(OUT/'report.json',report)
    (OUT/'scoped_records.jsonl').write_text(''.join(json.dumps(x,sort_keys=True)+'\n' for x in details))
    files=list(OUT.iterdir())+[Path(__file__).resolve(),INPUT/'manifest.json',p]
    write(OUT/'manifest.json',{'files':{str(p.relative_to(REPO_ROOT)):sha(p) for p in files}})
    print(json.dumps(report,indent=2))

if __name__=='__main__':main()
