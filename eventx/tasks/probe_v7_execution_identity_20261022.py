"""Bounded paired maker-inclusive/taker-only public API probe on the fixed V7 sample."""
import json,time,uuid,hashlib,os
from collections import Counter,defaultdict
from decimal import Decimal
from pathlib import Path
import httpx
from eventx.tasks.discover_v7_direct_pilot_20261022 import REPO_ROOT,PROTECTED,now,sha,write,verify_originals
from eventx.tasks.collect_v7_direct_pilot_20261022_v03 import check_scope,ScopeError
from eventx.v7.source_request_scheduler_v02 import retry_seconds
BASE=REPO_ROOT/'data/v7/execution_identity_20261022'
RELEASE=REPO_ROOT/'eventx/release/v7/direct_source_pilot_20261022_v03'

def main():
    verify_originals()
    for p,h in json.loads((RELEASE/'implementation_manifest.json').read_text())['locked_files'].items():
        if sha(REPO_ROOT/p)!=h:raise RuntimeError('Source freeze changed')
    out=BASE/uuid.uuid4().hex;out.mkdir(parents=True);(out/'objects').mkdir()
    samples=[json.loads(l) for l in (RELEASE/'sample.jsonl').read_text().splitlines()]
    if {r['market_id'] for r in samples}.intersection(json.loads(PROTECTED.read_text())):raise RuntimeError('Protected overlap')
    cutoff=int(now().timestamp());deadline=time.monotonic()+300;records=[];head=None;results={}
    write(out/'contract.json',{'started_at':now().isoformat(),'cutoff':cutoff,'window_start':cutoff-21600,'sample_sha256':sha(RELEASE/'sample.jsonl'),'code_sha256':sha(Path(__file__)),'purpose':'same fixed sample; first page paired probe; no completeness or model claim','taker_modes':[False,True],'interval_seconds':2,'max_duration_seconds':300})
    last_start=0.;blocked_until=0.
    with httpx.Client(timeout=20) as client:
        for sample in samples:
            cid=sample['market_id']
            for mode in [False,True]:
                wait=max(0,last_start+2-time.monotonic(),blocked_until-time.monotonic())
                if time.monotonic()+wait>=deadline:break
                time.sleep(wait)
                record={'market_id':cid,'taker_only':mode,'requested_at':now().isoformat()};last_start=time.monotonic()
                try:
                    response=client.get('https://data-api.polymarket.com/v2/trades',params={'condition':cid,'limit':1000,'taker_only':str(mode).lower()})
                    record.update(http_status=response.status_code,response_received_at=now().isoformat())
                    if response.status_code==200:
                        v=response.json();check_scope(v,{cid},{sample['yes_asset_id'],sample['no_asset_id']})
                        if not isinstance(v.get('data'),list) or 'next_cursor' not in v.get('pagination',{}):raise ValueError('Bad envelope')
                        if any(r.get('condition_id')!=cid or str(r.get('token_id')) not in {sample['yes_asset_id'],sample['no_asset_id']} for r in v['data']):raise ScopeError('Explicit scope mismatch')
                        h=hashlib.sha256(response.content).hexdigest()
                        if not (out/'objects'/h).exists():
                            with (out/'objects'/h).open('xb') as f:
                                f.write(response.content);f.flush();os.fsync(f.fileno())
                        record.update(payload_sha256=h,available_at=now().isoformat(),status='observed',rows=len(v['data']))
                        results[cid,mode]=v
                    else:
                        record.update(status='failed_http',error_body_sha256=hashlib.sha256(response.content).hexdigest())
                        if response.status_code in [401,403,429]:
                            delay=retry_seconds(response.headers.get('Retry-After'))
                            if response.status_code in [401,403]:delay=max(3600,delay)
                            record['backoff_seconds']=delay;blocked_until=time.monotonic()+delay
                except ScopeError:
                    write(out/'scope_failure.json',{'at':now().isoformat(),'status':'scope_rejected_stopped'})
                    raise
                except (httpx.HTTPError,ValueError) as e:record.update(status='failed',error_type=type(e).__name__)
                record.update(finished_at=now().isoformat(),previous_sha256=head)
                head=hashlib.sha256(json.dumps(record,sort_keys=True,separators=(',',':')).encode()).hexdigest();record['record_sha256']=head
                with (out/'journal.jsonl').open('a') as f:
                    f.write(json.dumps(record,sort_keys=True)+'\n');f.flush();os.fsync(f.fileno())
                records.append(record)
    def key(x):return (x['token_id'],int(x['timestamp']),str(Decimal(str(x['price'])).normalize()),str(Decimal(str(x['size'])).normalize()),x['side'].upper())
    pairs=[]
    for s in samples:
        cid=s['market_id']
        if (cid,False) not in results or (cid,True) not in results:continue
        vs=[results[cid,m] for m in [False,True]]
        rs=[[x for x in v['data'] if cutoff-21600<=int(x['timestamp'])<=cutoff] for v in vs]
        cs=[Counter(map(key,r)) for r in rs]
        pairs.append({'market_id':cid,'role':s['diagnostic_role'],'inclusive_rows_in_window':len(rs[0]),'taker_rows_in_window':len(rs[1]),'matching_economic_fingerprints':sum((cs[0]&cs[1]).values()),
                      'inclusive_minus_taker_fingerprints':sum((cs[0]-cs[1]).values()),'taker_minus_inclusive_fingerprints':sum((cs[1]-cs[0]).values()),
                      'both_pages_reach_window_start':all(v['pagination']['next_cursor'] is None or (v['data'] and min(int(x['timestamp']) for x in v['data'])<cutoff-21600) for v in vs),
                      'source_completeness_certified':False})
    (out/'paired_modes.jsonl').write_text(''.join(json.dumps(x,sort_keys=True)+'\n' for x in pairs))
    report={'at':now().isoformat(),'run':str(out.relative_to(REPO_ROOT)),'http_status_counts':dict(Counter(str(r.get('http_status')) for r in records)),'markets_with_both_modes':len(pairs),
            'markets_with_mode_count_difference':sum(x['inclusive_rows_in_window']!=x['taker_rows_in_window'] for x in pairs),
            'both_pages_reach_window_start_markets':sum(x['both_pages_reach_window_start'] for x in pairs),
            'model_scored':False,'predictive_admissions':0,'interpretation':'Each mode fetched separately; changes/delayed insertion and first-page truncation limit causal accounting. No fabricated unique execution IDs; no source completeness claim.'}
    write(out/'report.json',report)
    files=[p for p in out.iterdir() if p.is_file()]+[Path(__file__).resolve()]
    write(out/'manifest.json',{'files':{str(p.relative_to(REPO_ROOT)):sha(p) for p in files},'payloads':{p.name:sha(p) for p in (out/'objects').iterdir()}})
    print(json.dumps(report,indent=2))

if __name__=='__main__':main()
