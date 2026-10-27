"""Bounded read-only receipt probe for47captured missing V7control transactions."""
import json,time,uuid,hashlib
from pathlib import Path
from datetime import datetime,timezone
import httpx
from eventx.tasks.diagnose_v7_execution_accounting_20261022 import ROOT,sha,write,lines,verify_manifest
BASE=ROOT/'data/v7/missing_chain_20261023'
PLAN=ROOT/'data/v7/missing_receipt_plan_20261023'
RPC='https://polygon-bor-rpc.publicnode.com'
EXCHANGES={'0xe111180000d2663c0091e4f400237545b87b996b','0xe2222d279d744050d28e00520010520000310f59'}
TOPIC='0xd543adfd945773f1a62f74f0ee55a5e3b9b1a28262980ba90b1a89f2ea84d8ee'
def now():return datetime.now(timezone.utc).isoformat()

def main():
    verify_manifest(PLAN/'manifest.json')
    plan=json.loads((PLAN/'chain_probe_plan.json').read_text());provider=lines(PLAN/'provider_rows.jsonl')
    out=BASE/uuid.uuid4().hex;out.mkdir(parents=True);(out/'objects').mkdir()
    write(out/'contract.json',{'at':now(),'rpc':RPC,'plan_sha256':sha(PLAN/'chain_probe_plan.json'),'code_sha256':sha(Path(__file__)),
                             'max_seconds':240,'max_requests':60,'interval_seconds':1,'scope':plan['scope'],
                             'receipt_policy':'Store full response hash only; retain transaction metadata and token-allowlisted OrderFilled logs. Other receipt logs discarded without economic decoding.'})
    deadline=time.monotonic()+240;last=0.;n=0;journal=[];decoded=[];receipts={};code=[];txs=[];docs=[]
    def save_record(r):
        r['finished_at']=now();journal.append(r)
        with (out/'journal.jsonl').open('a') as f:f.write(json.dumps(r,sort_keys=True)+'\n')
    with httpx.Client(timeout=12,follow_redirects=True) as client:
        def rpc(method,params):
            nonlocal last,n
            if n>=60 or time.monotonic()+12>=deadline:raise RuntimeError('Bounded request limit')
            time.sleep(max(0,last+1-time.monotonic()));last=time.monotonic();n+=1
            r={'at':now(),'method':method,'params':params}
            try:
                response=client.post(RPC,json={'jsonrpc':'2.0','id':n,'method':method,'params':params})
                r.update(http_status=response.status_code,raw_response_sha256=hashlib.sha256(response.content).hexdigest())
                response.raise_for_status();v=response.json()
                if 'error' in v:r['rpc_error']=v['error'];save_record(r);return None
                r['status']='observed';save_record(r);return v.get('result')
            except httpx.HTTPError as e:
                r.update(status='failed',error_type=type(e).__name__);save_record(r);raise
        try:
            chain=rpc('eth_chainId',[])
            if chain!='0x89':raise RuntimeError('Chain mismatch or unavailable')
            for name,url in [
                ('ITrading.sol','https://raw.githubusercontent.com/Polymarket/ctf-exchange-v2/main/src/exchange/interfaces/ITrading.sol'),
                ('Trading.sol','https://raw.githubusercontent.com/Polymarket/ctf-exchange-v2/main/src/exchange/mixins/Trading.sol')]:
                r={'at':now(),'url':url,'kind':'official_source'}
                response=client.get(url);r['http_status']=response.status_code;response.raise_for_status()
                (out/name).write_bytes(response.content);r['sha256']=sha(out/name);docs.append(r);save_record(r)
            if 'event OrderFilled(' not in (out/'ITrading.sol').read_text():raise RuntimeError('Event source unavailable')
            allowed=set(plan['allowed_token_ids'])
            for tx in plan['transaction_hashes']:
                v=rpc('eth_getTransactionReceipt',[tx])
                if v is None:continue
                if v['transactionHash'].lower()!=tx.lower():raise RuntimeError('Transaction mismatch')
                meta={k:v.get(k) for k in ['transactionHash','blockHash','blockNumber','transactionIndex','from','to','status']}
                receipts[tx]=meta;scoped=[]
                for log in v.get('logs',[]):
                    topics=log.get('topics',[]);data=log.get('data','')[2:]
                    if log['address'].lower() not in EXCHANGES or len(topics)!=4 or topics[0].lower()!=TOPIC:continue
                    if len(data)!=7*64:raise RuntimeError('Unexpected OrderFilled layout')
                    token=str(int(data[64:128],16))
                    if token not in allowed:continue
                    words=[int(data[i:i+64],16) for i in range(0,len(data),64)]
                    row={'transaction_hash':tx,'block_hash':log['blockHash'],'block_number':int(log['blockNumber'],16),
                         'transaction_index':int(log['transactionIndex'],16),'log_index':int(log['logIndex'],16),'removed':log.get('removed'),
                         'exchange':log['address'].lower(),'order_hash':topics[1].lower(),'maker':'0x'+topics[2][-40:].lower(),
                         'taker':'0x'+topics[3][-40:].lower(),'side':words[0],'token_id':token,'maker_amount':str(words[2]),'taker_amount':str(words[3]),'fee':str(words[4])}
                    scoped.append(log);decoded.append(row)
                write(out/'objects'/tx,{'transaction':meta,'allowlisted_orderfilled_logs':scoped,'excluded_log_count':len(v.get('logs',[]))-len(scoped)})
            for tx in plan['ambiguous_transactions']:
                v=rpc('eth_getTransactionByHash',[tx])
                if v:txs.append({k:v.get(k) for k in ['hash','blockHash','blockNumber','transactionIndex','nonce','from','to']})
            for address in plan['provider_addresses']:
                candidates=[receipts[t] for p in provider if p['taker']==address for t in p['candidate_transactions'] if t in receipts]
                if not candidates:continue
                block=min((v['blockNumber'] for v in candidates),key=lambda x:int(x,16))
                v=rpc('eth_getCode',[address,block])
                code.append({'address':address,'block_number':int(block,16),'available':v is not None,
                             'has_code':None if v is None else v!='0x','code_bytes':None if v is None else (len(v)-2)//2,
                             'code_sha256':None if v is None else hashlib.sha256(v.encode()).hexdigest(),
                             'interpretation':'Code at one sampled block does not identify a router or prove tx.from semantics.'})
            status='completed'
        except Exception as e:
            status='failed_'+type(e).__name__
        for name,rs in [('decoded_fills',decoded),('receipts',list(receipts.values())),('address_code',code),('ambiguous_transactions',txs)]:
            (out/(name+'.jsonl')).write_text(''.join(json.dumps(r,sort_keys=True)+'\n' for r in rs))
        report={'at':now(),'status':status,'requests':n,'receipts':len(receipts),'scoped_orderfilled_logs':len(decoded),
                'address_checks':len(code),'run':str(out.relative_to(ROOT)),'model_scored':False,'predictive_admissions':0,'chain_finality_certified':False}
        write(out/'report.json',report)
        files=[p for p in out.rglob('*') if p.is_file()]+[Path(__file__).resolve(),PLAN/'manifest.json']
        write(out/'manifest.json',{'files':{str(p.relative_to(ROOT)):sha(p) for p in files}})
        print(json.dumps(report,indent=2))
        if status!='completed':raise SystemExit(1)
if __name__=='__main__':main()
