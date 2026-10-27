"""Compare still-missing control fills with captured order roles and senders."""
from collections import Counter
from decimal import Decimal
from pathlib import Path
from datetime import datetime,timezone
import json
from eventx.tasks.diagnose_v7_execution_accounting_20261022 import ROOT,PROBE,lines,economic,stamp,sha,write,verify_manifest
NEW=ROOT/'data/v7/missing_chain_20261023/fae52fd451084c578b7aa064b71410be'
OLD=ROOT/'data/v7/scoped_chain_20261023/c8c3fe64457e419989135e831b06ee07'
OUT=ROOT/'data/v7/missing_receipt_analysis_20261023'

def main():
    OUT.mkdir(exist_ok=False)
    manifests=[NEW/'manifest.json',OLD/'manifest.json',ROOT/'data/v7/hypothesis_followup_20261023/manifest.json']
    for p in manifests:verify_manifest(p)
    missing=[r for r in lines(ROOT/'data/v7/hypothesis_followup_20261023/missing_row_recovery.jsonl') if not r['recovered']]
    probe={r['market_id']:r for r in lines(PROBE/'journal.jsonl') if r.get('status')=='observed' and r['taker_only']}
    fs=lines(NEW/'decoded_fills.jsonl');receipts={r['transactionHash']:r for r in lines(NEW/'receipts.jsonl')}
    old_receipts={r['transactionHash']:r for r in lines(OLD/'receipts.jsonl')}
    old_fills=lines(OLD/'decoded_fills.jsonl')
    rows=[];payloads={}
    for m in missing:
        p=PROBE/'objects'/probe[m['market_id']]['payload_sha256']
        if sha(p)!=p.name:raise RuntimeError('Raw mismatch')
        payloads[str(p.relative_to(ROOT))]=sha(p)
        ts=[r for r in json.loads(p.read_text())['data'] if r['transaction_hash']==m['transaction_hash'] and str(r['token_id'])==m['token_id'] and stamp(r)==m['timestamp']]
        if len(ts)!=1:raise RuntimeError('Unexpected direct candidate multiplicity')
        t=ts[0];matches=[]
        for f in fs:
            if f['transaction_hash']!=t['transaction_hash'] or f['token_id']!=str(t['token_id']) or f['taker']!=f['exchange']:continue
            ma,ta=Decimal(f['maker_amount']),Decimal(f['taker_amount'])
            if f['side'] not in [0,1] or not ma or not ta:continue
            size=(ta if f['side']==0 else ma)/Decimal(10**6);price=ma/ta if f['side']==0 else ta/ma
            if size==Decimal(str(t['size'])) and abs(price-Decimal(str(t['price'])))<Decimal('1e-9') and ('BUY' if f['side']==0 else 'SELL')==t['side'] and f['maker']==t['proxy_wallet'].lower():matches.append(f)
        rec=receipts.get(t['transaction_hash'],{})
        row={**m,'direct_side':t['side'],'direct_size':t['size'],'direct_price':t['price'],'chain_matches':len(matches),
             'receipt_status':rec.get('status'),'sender_seen_in_captured_transactions':rec.get('from') in {r['from'] for r in old_receipts.values()},
             'to_seen_in_captured_transactions':rec.get('to') in {r['to'] for r in old_receipts.values()}}
        if len(matches)==1:
            f=matches[0];row.update(exchange=f['exchange'],block_number=f['block_number'],block_hash=f['block_hash'],transaction_index=f['transaction_index'],log_index=f['log_index'],order_hash=f['order_hash'],
                                   exchange_seen_in_captured_fills=f['exchange'] in {x['exchange'] for x in old_fills},
                                   participant_seen_in_captured_fills=f['maker'] in {x['maker'] for x in old_fills},
                                   within_transaction_allowlisted_fill_logs=sum(x['transaction_hash']==t['transaction_hash'] for x in fs),role='exchange_facing_taker_order_fill')
        rows.append(row)
    report={'at':datetime.now(timezone.utc).isoformat(),'missing_records':len(rows),'unique_chain_matches':sum(r['chain_matches']==1 for r in rows),
            'successful_receipts':sum(r['receipt_status']=='0x1' for r in rows),'by_exchange':dict(Counter(r.get('exchange','unresolved') for r in rows)),
            'exchange_seen_in_captured':sum(r.get('exchange_seen_in_captured_fills',False) for r in rows),
            'sender_seen_in_captured':sum(r['sender_seen_in_captured_transactions'] for r in rows),
            'destination_seen_in_captured':sum(r['to_seen_in_captured_transactions'] for r in rows),
            'participant_seen_in_captured':sum(r.get('participant_seen_in_captured_fills',False) for r in rows),
            'by_side':dict(Counter(r['direct_side'] for r in rows)),
            'interpretation':'Missing direct records are checked against successful scoped settlement receipts. Shared exchange/sender/role weakens simple venue/catalog exclusion, but does not identify provider filtering or ingestion cause.',
            'limits':['One public RPC source; finality not independently certified.','Exact sampled event matches do not establish global API coverage.','On-chain event data were acquired retrospectively.'],
            'models_scored':False,'predictive_admissions':0}
    (OUT/'missing_event_mapping.jsonl').write_text(''.join(json.dumps(r,sort_keys=True)+'\n' for r in rows))
    write(OUT/'report.json',report);write(OUT/'payload_hashes.json',payloads)
    files=list(OUT.iterdir())+[Path(__file__).resolve()]+manifests
    write(OUT/'manifest.json',{'files':{str(p.relative_to(ROOT)):sha(p) for p in files}})
    print(json.dumps(report,indent=2))
if __name__=='__main__':main()
