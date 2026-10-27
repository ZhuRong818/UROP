"""Re-fetch four previously captured V7 windows; preserve late availability."""
from datetime import datetime,timezone
from collections import Counter
from pathlib import Path
import hashlib,json,time,uuid
import httpx
from eventx.settings import ApiSettings
from eventx.tasks.diagnose_v7_execution_accounting_20261022 import ROOT,RELEASE,lines,sha,stamp,economic,write,verify_manifest
from eventx.tasks.collect_v7_direct_pilot_20261022_v03 import check_scope
BASE=ROOT/'data/v7/delayed_recovery_20261023'
HYP=ROOT/'data/v7/source_hypotheses_20261023'

def main():
    verify_manifest(HYP/'manifest.json')
    missing=lines(HYP/'missing_taker.jsonl');markets=sorted({r['market_id'] for r in missing})
    sample={r['market_id']:r for r in lines(RELEASE/'sample.jsonl')}
    windows={r['market_id']:r for r in lines(ROOT/'data/v7/participant_coverage_20261023/market_coverage.jsonl')}
    if len(markets)!=4 or set(markets)&set(json.loads((ROOT/'eventx/release/v7/market_capture_20261018/protected_ids.json').read_text())):raise RuntimeError('Scope mismatch')
    out=BASE/uuid.uuid4().hex;out.mkdir(parents=True);(out/'objects').mkdir()
    write(out/'contract.json',{'at':datetime.now(timezone.utc).isoformat(),'code_sha256':sha(Path(__file__)),
                             'windows':{cid:{k:windows[cid][k] for k in ['window_start','window_end']} for cid in markets},
                             'max_requests':4,'page_limit':1000,'interval_seconds':2,'max_seconds':120,
                             'interpretation':'Late retrieval cannot create historical availability. Full page unresolved; no pagination or extrapolated completeness.'})
    cfg=ApiSettings.from_env();journal=[];comparisons=[];deadline=time.monotonic()+120;last=0
    status='completed'
    with httpx.Client(base_url=cfg.base_url,headers={'Authorization':'Bearer '+cfg.token},timeout=20) as client:
        for cid in markets:
            if time.monotonic()+20>deadline:status='deadline';break
            time.sleep(max(0,last+2-time.monotonic()));last=time.monotonic()
            w=windows[cid];lo,hi=w['window_start'],w['window_end'];r={'market_id':cid,'requested_at':datetime.now(timezone.utc).isoformat()}
            try:
                params={'from':datetime.fromtimestamp(lo,timezone.utc).isoformat(),'to':datetime.fromtimestamp(hi,timezone.utc).isoformat(),'limit':1000}
                r['params']=params
                response=client.get('/prediction-markets/trades/polymarket/'+cid,params=params)
                r.update(http_status=response.status_code,response_received_at=datetime.now(timezone.utc).isoformat())
                if response.status_code!=200:
                    r.update(status='failed_http',body_sha256=hashlib.sha256(response.content).hexdigest());status='failed_http'
                    journal.append(r);break
                value=response.json();check_scope(value,{cid},{sample[cid]['yes_asset_id'],sample[cid]['no_asset_id']})
                if not isinstance(value,list) or any(not lo<=stamp(x)<=hi for x in value):raise ValueError('Unexpected window')
                h=hashlib.sha256(response.content).hexdigest();(out/'objects'/h).write_bytes(response.content)
                r.update(payload_sha256=h,available_at=datetime.now(timezone.utc).isoformat(),status='observed',rows=len(value))
                absent=[x for x in missing if x['market_id']==cid]
                # The missing ledger retains transaction identity and size; compare exact
                # transaction/token/second/size, without inventing absent side/price fields.
                recovered=[]
                for x in absent:
                    candidates=[p for p in value if str(p['trade_id']).startswith(x['transaction_hash']) and str(p['token_id'])==x['token_id'] and stamp(p)==x['timestamp'] and str(__import__('decimal').Decimal(str(p['size'])).normalize())==str(__import__('decimal').Decimal(x['size']).normalize())]
                    recovered.append({'transaction_hash':x['transaction_hash'],'matching_late_provider_rows':len(candidates)})
                comparisons.append({'market_id':cid,'old_provider_rows':w['provider_rows'],'late_provider_rows':len(value),
                    'original_missing_taker_rows':len(absent),'missing_with_late_tx_token_time_size_match':sum(x['matching_late_provider_rows']>0 for x in recovered),
                    'missing_transaction_hashes_now_present':len({x['transaction_hash'] for x in absent if any(str(p['trade_id']).startswith(x['transaction_hash']) for p in value)}),
                    'bounded_page_returned':len(value)<1000,'late_receipt_at':r['response_received_at'],
                    'hours_after_window_end':(datetime.fromisoformat(r['response_received_at']).timestamp()-hi)/3600,
                    'recovery':recovered,'historical_availability_changed':False})
            except Exception as e:
                r.update(status='failed',error_type=type(e).__name__);status='failed_'+type(e).__name__;journal.append(r);break
            journal.append(r)
    (out/'journal.jsonl').write_text(''.join(json.dumps(x,sort_keys=True)+'\n' for x in journal))
    (out/'comparisons.jsonl').write_text(''.join(json.dumps(x,sort_keys=True)+'\n' for x in comparisons))
    report={'at':datetime.now(timezone.utc).isoformat(),'run':str(out.relative_to(ROOT)),'status':status,'requested_markets':len(journal),
            'observed_markets':len(comparisons),'old_missing_rows_examined':sum(x['original_missing_taker_rows'] for x in comparisons),
            'recovered_by_tx_token_time_size':sum(x['missing_with_late_tx_token_time_size_match'] for x in comparisons),
            'old_provider_rows':sum(x['old_provider_rows'] for x in comparisons),'late_provider_rows':sum(x['late_provider_rows'] for x in comparisons),
            'all_pages_below_cap':bool(comparisons) and all(x['bounded_page_returned'] for x in comparisons),
            'model_scored':False,'predictive_admissions':0,'historical_availability_changed':False}
    write(out/'report.json',report)
    files=[p for p in out.rglob('*') if p.is_file()]+[Path(__file__).resolve(),HYP/'manifest.json']
    write(out/'manifest.json',{'files':{str(p.relative_to(ROOT)):sha(p) for p in files}})
    print(json.dumps(report,indent=2))
    if status!='completed':raise SystemExit(1)
if __name__=='__main__':main()
