"""Check proposed accounting explanations against fixed local source receipts."""
from collections import Counter, defaultdict
from decimal import Decimal
from datetime import datetime, timezone
import hashlib,json
from eventx.tasks.diagnose_v7_execution_accounting_20261022 import ROOT,AUDIT,RUN,PROBE,RELEASE,lines,sha,stamp,economic,write,verify_manifest
OUT=ROOT/'data/v7/source_hypotheses_20261023'

def main():
    OUT.mkdir(exist_ok=False)
    manifests=[ROOT/'data/v7/local_execution_accounting_20261022/manifest.json',ROOT/'data/v7/participant_coverage_20261023/manifest.json']
    for p in manifests:verify_manifest(p)
    samples={r['market_id']:r for r in lines(RELEASE/'sample.jsonl')}
    if set(samples)&set(json.loads((ROOT/'eventx/release/v7/market_capture_20261018/protected_ids.json').read_text())):raise RuntimeError('Protected overlap')
    records=lines(AUDIT/'journal.jsonl');old={};receipts={};inputs={};probe={}
    windows={(r['market_id'],r['source']):r for r in records if r['kind']=='window_summary' and r['cycle']==1}
    def body(base,r):
        p=base/'objects'/r['payload_sha256']
        if sha(p)!=r['payload_sha256']:raise RuntimeError('Payload mismatch')
        inputs[str(p.relative_to(ROOT))]=sha(p)
        return json.loads(p.read_text())
    for r in records:
        if r['kind']=='rest' and r.get('endpoint_kind')=='trades' and r['cycle']==1 and r.get('status')=='observed':
            v=body(RUN,r);old[r['market_id'],r['source']]=v['data'] if isinstance(v,dict) else v;receipts[r['market_id'],r['source']]=r
    for r in lines(PROBE/'journal.jsonl'):
        if r.get('status')=='observed':probe[r['market_id'],r['taker_only']]=body(PROBE,r)
    schema=defaultdict(set);ambiguous=[];missing=[];provider=[];ordering=[];groups=[]
    cov={r['market_id']:r for r in lines(ROOT/'data/v7/participant_coverage_20261023/market_coverage.jsonl') if r['status']=='shared_retained_range'}
    for cid,s in samples.items():
        for src in ['venue','lumid']:
            for r in old[cid,src]:schema[src].update(r)
        w=cov[cid];lo,hi=w['window_start'],w['window_end']
        vs=[v for v in old[cid,'venue'] if lo<=stamp(v)<=hi];ps=[p for p in old[cid,'lumid'] if lo<=stamp(p)<=hi]
        ts=[v for v in probe[cid,True]['data'] if lo<=stamp(v)<=hi]
        cp=Counter(economic(p,True) for p in ps)
        latest=max((stamp(p) for p in ps),default=None)
        observed_time=datetime.fromisoformat(receipts[cid,'lumid']['response_received_at']).timestamp()
        for t in ts:
            k=economic(t,True)
            if cp[k]:cp[k]-=1;continue
            missing.append({'market_id':cid,'role':s['diagnostic_role'],'token_id':str(t['token_id']),'transaction_hash':t['transaction_hash'],
                'timestamp':stamp(t),'size':str(t['size']),'age_at_provider_receipt_seconds':observed_time-stamp(t),
                'seconds_before_latest_provider_trade':None if latest is None else latest-stamp(t),
                'token_also_seen_in_provider':any(str(p['token_id'])==str(t['token_id']) for p in ps),
                'transaction_also_seen_in_provider':any(str(p['trade_id']).startswith(t['transaction_hash']) for p in ps),
                'hours_before_window_end':int((hi-stamp(t))//3600)})
        for p in ps:
            ms=[v for v in vs if economic(v,True)==economic(p,True) and str(p['trade_id']).startswith(v['transaction_hash'])]
            ph=hashlib.sha256(str(p['trade_id']).encode()).hexdigest()
            provider.append({'market_id':cid,'provider_id':p['trade_id'],'provider_id_sha256':ph,'taker':p['taker'],'timestamp':stamp(p),
                             'token_id':str(p['token_id']),'size':str(p['size']),'price':str(p['price']),'side':p['side'],
                             'candidate_transactions':sorted({v['transaction_hash'] for v in ms}),
                             'candidate_proxy_wallets':sorted({v['proxy_wallet'] for v in ms}),
                             'wallet_matches':any(str(p['taker']).lower()==str(v['proxy_wallet']).lower() for v in ms)})
            if len(ms)>1:
                ambiguous.append({'market_id':cid,'provider_id_sha256':ph,'provider_id':p['trade_id'],'provider_size':str(p['size']),
                    'candidate_sizes':[str(v['size']) for v in ms], 'candidate_sum':str(sum((Decimal(str(v['size'])) for v in ms),Decimal(0))),
                    'sum_equals_provider':sum((Decimal(str(v['size'])) for v in ms),Decimal(0))==Decimal(str(p['size'])),
                    'distinct_tx_hashes':sorted({v['transaction_hash'] for v in ms}),'distinct_full_candidate_rows':len({json.dumps(v,sort_keys=True) for v in ms}),
                    'candidate_wallets':sorted({v['proxy_wallet'] for v in ms})})
        secs=defaultdict(list)
        for v in vs:
            if str(v['token_id'])==s['yes_asset_id']:secs[stamp(v)].append(v)
        for sec,rr in secs.items():
            pp=[Decimal(str(v['price'])) for v in rr]
            if len(set(pp))<2:continue
            up=all(a<=b for a,b in zip(pp,pp[1:]));down=all(a>=b for a,b in zip(pp,pp[1:]))
            ordering.append({'market_id':cid,'timestamp':sec,'rows':len(rr),'prices_in_returned_order':list(map(str,pp)),
                             'monotonic':up or down,'ordering_verified':False,'note':'Price monotonicity cannot verify execution order.'})
        if ps:groups.append({'market_id':cid,'latest_provider_timestamp':latest,'provider_rows':len(ps),'role':s['diagnostic_role']})
    report={'at':datetime.now(timezone.utc).isoformat(),'ambiguous_provider_rows':len(ambiguous),
            'ambiguous_distinct_transactions':len({t for r in ambiguous for t in r['distinct_tx_hashes']}),
            'ambiguous_sum_equals_provider':sum(r['sum_equals_provider'] for r in ambiguous),
            'ambiguous_provider_ids_have_suffix':sum(':' in r['provider_id'] for r in ambiguous),
            'missing_taker_rows':len(missing),'missing_by_market':dict(Counter(r['market_id'] for r in missing)),
            'missing_age_seconds_min':min(r['age_at_provider_receipt_seconds'] for r in missing),
            'missing_age_seconds_max':max(r['age_at_provider_receipt_seconds'] for r in missing),
            'missing_older_than_latest_provider_trade':sum(r['seconds_before_latest_provider_trade'] is not None and r['seconds_before_latest_provider_trade']>0 for r in missing),
            'missing_token_seen_in_provider':sum(r['token_also_seen_in_provider'] for r in missing),
            'missing_tx_seen_in_provider':sum(r['transaction_also_seen_in_provider'] for r in missing),
            'missing_size_min':str(min(Decimal(r['size']) for r in missing)), 'missing_size_max':str(max(Decimal(r['size']) for r in missing)),
            'missing_hours_before_end':dict(Counter(str(r['hours_before_window_end']) for r in missing)),
            'schemas':{k:sorted(v) for k,v in schema.items()},'conflicting_seconds':len(ordering),'monotonic_conflicting_seconds':sum(r['monotonic'] for r in ordering),
            'findings':['All four ambiguous provider rows share one transaction but have different ID suffixes; each candidate has the full provider amount, so summing doubles it.',
                        'No nonce, receipt status, block number, transaction index or log index is present in the captured trade schemas.',
                        'Lag/scope/filter explanations require further evidence; timing patterns alone cannot identify cause.',
                        'Row order or monotonic prices cannot certify on-chain or off-chain matching order.'],
            'models_scored':False,'predictive_admissions':0}
    for name,rs in [('ambiguous',ambiguous),('missing_taker',missing),('provider_rows',provider),('same_second',ordering)]:
        (OUT/(name+'.jsonl')).write_text(''.join(json.dumps(r,sort_keys=True)+'\n' for r in rs))
    write(OUT/'report.json',report);write(OUT/'input_payload_hashes.json',inputs)
    write(OUT/'chain_probe_plan.json',{'chain_id':137,'transaction_hashes':sorted({t for r in provider for t in r['candidate_transactions']}),
           'ambiguous_transactions':sorted({t for r in ambiguous for t in r['distinct_tx_hashes']}),'provider_addresses':sorted({r['taker'] for r in provider}),
           'allowed_token_ids':sorted({str(s[k]) for s in samples.values() for k in ['yes_asset_id','no_asset_id']}),
           'scope':'Read-only exact-receipt/account-code probe. Decode only allowlisted token OrderFilled logs; no traces, broad logs or protected evaluation.'})
    files=list(OUT.iterdir())+[__import__('pathlib').Path(__file__).resolve()]+manifests
    write(OUT/'manifest.json',{'files':{str(p.relative_to(ROOT)):sha(p) for p in files}})
    print(json.dumps(report,indent=2))
if __name__=='__main__':main()
