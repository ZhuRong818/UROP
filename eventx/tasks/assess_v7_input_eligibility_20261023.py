"""Accounting sensitivity and prospective eligibility diagnostics; no predictions."""
from collections import Counter,defaultdict
from datetime import datetime,timezone
from decimal import Decimal
import json,math
from pathlib import Path
import numpy as np
from eventx.tasks.diagnose_v7_execution_accounting_20261022 import ROOT,PROBE,RELEASE,lines,sha,write,verify_manifest
from eventx.tasks.discover_v7_direct_pilot_20261022 import verify_originals
from eventx.tasks.audit_v7_direct_pilot_20261022 import stamp
OUT=ROOT/'data/v7/input_eligibility_20261023'
AUDIT=ROOT/'data/v7/direct_source_pilot_20261022/audits/20261023T023646Z_d2af4c'
LIVE=ROOT/'data/v7/direct_source_pilot_20261022/live'
OLD_AUDIT=ROOT/'data/v7/direct_source_pilot_20261022_v03/audits/20261022T111727Z_158a60'
OLD_RUN=ROOT/'data/v7/direct_source_pilot_20261022_v03/smoke/7982a689e9014012a3ff8410fd55dad7'
CHAIN=ROOT/'data/v7/chain_reconciliation_20261023'
LATE=ROOT/'data/v7/delayed_recovery_20261023/bb25916406b04e52aa3f230324ac68c2'

def norm(r):
    return {'token':str(r.get('token_id',r.get('asset'))),'time':stamp(r.get('ts',r.get('timestamp'))),
            'price':float(r['price']),'size':float(r['size']),'trade_id':r.get('trade_id'),
            'tx':r.get('transaction_hash',r.get('transactionHash'))}

def features(rows,yes,t,chain_order=False):
    rr=[r for r in rows if r['token']==yes and r['time']<=t]
    rr.sort(key=lambda r:(r['time'],r.get('chain_order',(0,0,0))) if chain_order else (r['time'],r.get('trade_id') or ''))
    count60=sum(t-3600<r['time']<=t for r in rr);count240=sum(t-14400<r['time']<=t for r in rr)
    size60=sum(r['size'] for r in rr if t-3600<r['time']<=t);size240=sum(r['size'] for r in rr if t-14400<r['time']<=t)
    latest=max((r['time'] for r in rr),default=None);prices=sorted({r['price'] for r in rr if r['time']==latest})
    age=None if latest is None else (t-latest)/60
    fresh=age is not None and 0<=age<=5
    result={'yes_rows_in_retained_range':len(rr),'count60':count60,'count240':count240,'quantity60':size60,'quantity240':size240,
            'log1p_count60':math.log1p(count60),'log1p_count240':math.log1p(count240),'log1p_quantity60':math.log1p(size60),'log1p_quantity240':math.log1p(size240),
            'count_rate_ratio':4*count60/(count240+1),'size_rate_ratio':4*size60/(size240+1),
            'latest_trade_time':latest,'price_age_minutes':age,'latest_timestamp_prices':prices,'latest_price_ambiguous':len(prices)>1,
            'latest_price':(rr[-1]['price'] if chain_order and rr else prices[0] if len(prices)==1 else None),
            'fresh':fresh,'count60_pass':count60>=3,'count240_pass':count240>=3,'quantity240_pass':size240>=100,
            'observed_activity_screen':bool(fresh and count60>=3 and count240>=3 and size240>=100),
            'complete_source_history_certified':False,'mathematical_240m_history_available':False,'sigma240':None,'sigma30':None,
            'history_math_reason':'no_pre_window_seed'}
    if not any(r['time']<=t-14400 for r in rr):return result
    times=np.array([r['time'] for r in rr]);grid=np.arange(t-14400,t+1,60);ix=np.searchsorted(times,grid,side='right')-1
    if not chain_order:
        at_second=defaultdict(set)
        for r in rr:at_second[r['time']].add(r['price'])
        if any(len(at_second[rr[i]['time']])>1 for i in ix):
            result['history_math_reason']='unresolved_same_timestamp_prices';return result
    px=np.clip(np.array([rr[i]['price'] for i in ix]),.0001,.9999);lo=np.log(px/(1-px));d=np.diff(lo)
    result.update(mathematical_240m_history_available=True,history_math_reason='computed_from_retained_rows_only',sigma240=float(np.std(d,ddof=0)),sigma30=float(np.std(d[-30:],ddof=0)),
                  momentum5=float(lo[-1]-lo[-6]),momentum30=float(lo[-1]-lo[-31]),momentum120=float(lo[-1]-lo[-121]))
    return result

def main():
    OUT.mkdir(exist_ok=False)
    manifests=[AUDIT/'manifest.json',OLD_AUDIT/'manifest.json',CHAIN/'manifest.json',LATE/'manifest.json',ROOT/'data/v7/feature_semantics_20261022/manifest.json']
    for p in manifests:verify_manifest(p)
    original_locks=verify_originals()
    semantic=json.loads((ROOT/'data/v7/feature_semantics_20261022/report.json').read_text())
    for r in semantic['verified_code_chain']:
        if sha(ROOT/r['code'])!=r['sha256']:raise RuntimeError('Historical feature code changed')
    samples={r['market_id']:r for r in lines(RELEASE/'sample.jsonl')}
    protected=set(json.loads((ROOT/'eventx/release/v7/market_capture_20261018/protected_ids.json').read_text()))
    if set(samples)&protected:raise RuntimeError('Protected overlap')
    used={};cache={}
    def payload(base,r):
        p=base/'objects'/r['payload_sha256']
        if p not in cache:
            if sha(p)!=r['payload_sha256']:raise RuntimeError('Raw mismatch')
            used[str(p.relative_to(ROOT))]=sha(p);cache[p]=json.loads(p.read_text())
        return cache[p]
    old_records=lines(OLD_AUDIT/'journal.jsonl')
    old={(r['market_id'],r['source']):r for r in old_records if r['kind']=='rest' and r.get('endpoint_kind')=='trades' and r['cycle']==1 and r.get('status')=='observed'}
    probe={(r['market_id'],r['taker_only']):r for r in lines(PROBE/'journal.jsonl') if r.get('status')=='observed'}
    late={r['market_id']:r for r in lines(LATE/'journal.jsonl') if r.get('status')=='observed'}
    windows={r['market_id']:r for r in lines(ROOT/'data/v7/participant_coverage_20261023/market_coverage.jsonl') if r['status']=='shared_retained_range'}
    mapping={r['provider_id_sha256']:r for r in lines(CHAIN/'row_mapping.jsonl')}
    fs={(r['transaction_hash'],r['log_index']):r for r in lines(ROOT/'data/v7/scoped_chain_20261023/c8c3fe64457e419989135e831b06ee07/decoded_fills.jsonl')}
    compatibility=[]
    for cid,s in samples.items():
        w=windows[cid];t=(w['window_end']//300)*300;lo=w['window_start']
        ps=[p for p in payload(OLD_RUN,old[cid,'lumid']) if lo<=stamp(p['ts'])<=t]
        variants={'provider_original':list(map(norm,ps))}
        for mode,name in [(False,'direct_inclusive'),(True,'direct_taker_only')]:
            variants[name]=[norm(r) for r in payload(PROBE,probe[cid,mode])['data'] if lo<=stamp(r['timestamp'])<=t]
        chain_rows=[];chain_taker=[]
        for p in ps:
            key=__import__('hashlib').sha256(str(p['trade_id']).encode()).hexdigest();m=mapping[key]
            if m['candidate_fill_count']!=1:raise RuntimeError('Unresolved sampled event')
            f=fs[m['transaction_hash'],m['log_index']];r=norm(p);r['chain_order']=(m['block_number'],m['transaction_index'],m['log_index'])
            chain_rows.append(r)
            if f['taker']==f['exchange']:chain_taker.append(r)
        variants['provider_mapped_order_fills']=chain_rows;variants['provider_mapped_taker_order_fills']=chain_taker
        if cid in late:variants['provider_late']=[norm(r) for r in payload(LATE,late[cid]) if lo<=stamp(r['ts'])<=t]
        feats={name:features(rr,s['yes_asset_id'],t,name.startswith('provider_mapped')) for name,rr in variants.items()}
        compatibility.append({'market_id':cid,'question':s['question'],'role':s['diagnostic_role'],'diagnostic_grid':t,'retained_lower_bound':lo,
                              'variants':feats,'comparison_is_retrospective_not_decision_time':True})
    current=json.loads((AUDIT/'report.json').read_text());t=int(datetime.fromisoformat(current['created_at']).timestamp())//300*300
    rest={};summaries={};all_rest=[]
    with (AUDIT/'journal.jsonl').open() as f:
        for line in f:
            r=json.loads(line)
            if r['kind']=='rest':
                all_rest.append(r)
                if r.get('endpoint_kind')=='trades':rest.setdefault((r['market_id'],r['cycle'],r['source']),[]).append(r)
            elif r['kind']=='window_summary':summaries[r['market_id'],r['cycle'],r['source']]=r
    comps=lines(AUDIT/'market_comparison.jsonl');gaps={r['market_id']:r for r in json.loads((AUDIT/'trade_receipt_gaps.json').read_text())}
    activity=[];eligibility=[]
    for cid,s in samples.items():
        if s['diagnostic_role']!='prospective_macro_candidate':continue
        candidate=[]
        for c in comps:
            if c['market_id']!=cid or c['status']!='comparable_single_page_window':continue
            req=rest[cid,c['cycle'],'venue'][0];start,end=c['window_from'],c['window_to']
            rr=[norm(r) for r in payload(LIVE,req) if start<=stamp(r['timestamp'])<=end]
            f=features(rr,s['yes_asset_id'],end)
            activity.append({'market_id':cid,'cycle':c['cycle'],'window_end':end,**{k:f[k] for k in ['count60','count240','quantity240','price_age_minutes','observed_activity_screen']}})
            # Fixed five-minute as-of grid; only previously durable receipts are eligible inputs.
            if stamp(req['available_at'])<=t and start<=t-14400:
                candidate.append((stamp(req['available_at']),req,rr,c))
        candidate.sort(key=lambda x:x[0]);latest=candidate[-1] if candidate else None
        f=features(latest[2],s['yes_asset_id'],t) if latest else None
        histories=[r for r in activity if r['market_id']==cid]
        observed_meta=[r for r in all_rest if r['market_id']==cid and r.get('endpoint_kind')=='market_metadata' and r.get('status')=='observed' and stamp(r['available_at'])<=t]
        observed_meta.sort(key=lambda r:stamp(r['available_at']));metadata=None
        if observed_meta:
            mv=payload(LIVE,observed_meta[-1])
            if isinstance(mv,list) and len(mv)==1:
                m=mv[0];tokens=m.get('clobTokenIds',[]);outcomes=m.get('outcomes',[])
                if isinstance(tokens,str):tokens=json.loads(tokens)
                if isinstance(outcomes,str):outcomes=json.loads(outcomes)
                metadata={'available_at':observed_meta[-1]['available_at'],'mapping_matches':m.get('conditionId')==cid and tokens==[s['yes_asset_id'],s['no_asset_id']] and outcomes==['Yes','No'],
                          'rules_match':m.get('description')==s.get('rules'),'accepting_orders':m.get('acceptingOrders'),'closed':m.get('closed')}
        reasons=[]
        if f is None:reasons.append('no_bounded_history_receipt_available_by_grid')
        else:
            for flag,label in [('fresh','stale_or_absent_yes_trade'),('count60_pass','fewer_than_3_yes_records_60m'),('count240_pass','fewer_than_3_yes_records_240m'),('quantity240_pass','less_than_100_tokens_240m'),('mathematical_240m_history_available','cannot_compute_full240m_from_retained_rows')]:
                if not f[flag]:reasons.append(label)
            if f['sigma240']==0:reasons.append('zero_sampled_volatility')
        eligibility.append({'market_id':cid,'question':s['question'],'family':s['family'],'asof_grid':t,'metadata':metadata,
              'selected_trade_receipt':None if latest is None else {k:latest[1][k] for k in ['available_at','payload_sha256']},
              'latest_trade_window_end':None if latest is None else latest[3]['window_to'],'observed_features':f,'observed_failures':reasons,
              'comparable_windows':len(histories),'activity_pass_windows':sum(r['observed_activity_screen'] for r in histories),
              'max_receipt_gap_seconds':gaps[cid]['max_between_receipts_seconds'],
              'gates':{'source_coverage':'unverified','canonical_counting_compatibility':'unverified','complete_asof240m_history':'unverified',
                       'forward30m':'pending_unfrozen_receipt_policy_not_computed','tradable_through_target':'unverified',
                       'release_evidence':'reserved_release_not_yet_occurred','prospective_admission':False}})
    deltas=[]
    for baseline,alternative in [('provider_original','provider_mapped_order_fills'),('provider_original','provider_mapped_taker_order_fills'),('direct_inclusive','direct_taker_only'),('provider_original','direct_taker_only'),('provider_original','provider_late')]:
        for role in sorted({r['role'] for r in compatibility}):
            rr=[r for r in compatibility if r['role']==role and alternative in r['variants']]
            counts={}
            for field in ['count60','count240','quantity60','quantity240','size_rate_ratio','latest_trade_time','latest_price','observed_activity_screen']:
                counts[field+'_changed']=sum(r['variants'][baseline][field]!=r['variants'][alternative][field] for r in rr)
            deltas.append({'baseline':baseline,'alternative':alternative,'role':role,'markets':len(rr),**counts})
    report={'at':datetime.now(timezone.utc).isoformat(),'audit':str(AUDIT.relative_to(ROOT)),'audit_snapshot_at':current['created_at'],'asof_grid':datetime.fromtimestamp(t,timezone.utc).isoformat(),
            'source_audit_journal_records':current['journal_records'],'source_audit_payloads':current['verified_payloads'],'production_locks_verified':original_locks,
            'candidate_markets':len(eligibility),'candidate_comparable_windows':len(activity),'candidate_activity_pass_windows':sum(r['observed_activity_screen'] for r in activity),
            'candidate_markets_ever_activity_pass':sum(r['activity_pass_windows']>0 for r in eligibility),
            'candidate_latest_activity_pass':sum(bool(r['observed_features'] and r['observed_features']['observed_activity_screen']) for r in eligibility),
            'candidate_latest_fresh':sum(bool(r['observed_features'] and r['observed_features']['fresh']) for r in eligibility),
            'candidate_latest_math240_available':sum(bool(r['observed_features'] and r['observed_features']['mathematical_240m_history_available']) for r in eligibility),
            'candidate_latest_positive_sigma240':sum(bool(r['observed_features'] and r['observed_features']['sigma240'] is not None and r['observed_features']['sigma240']>0) for r in eligibility),
            'candidate_metadata_mapping_rules_match':sum(bool(r['metadata'] and r['metadata']['mapping_matches'] and r['metadata']['rules_match']) for r in eligibility),
            'observed_failure_counts':dict(Counter(x for r in eligibility for x in r['observed_failures'])),
            'largest_candidate_receipt_gap_seconds':max(r['max_receipt_gap_seconds'] or 0 for r in eligibility),
            'accounting_deltas':deltas,'prospective_admissions':0,'reserved_episodes':6,'captured_reserved_release_episodes':0,
            'model_loaded_or_scored':False,'forward_targets_or_labels_computed':False,'tests_added_or_run':False,
            'limits':['Accounting sensitivity uses retrospective common windows; later source receipts are not backdated.',
                      'Mathematical volatility from retained records is not a source-completeness certificate.',
                      'Current-grid diagnostics do not select later event anchors or alter the metadata-defined cohort.',
                      'Original API capture and revised short probe are distinct samples; no randomized collector-performance gain claimed.',
                      'Zero yield today does not prove the future release will have zero yield.']}
    for name,rs in [('accounting_compatibility',compatibility),('accounting_deltas',deltas),('candidate_activity_windows',activity),('candidate_eligibility',eligibility)]:
        (OUT/(name+'.jsonl')).write_text(''.join(json.dumps(r,sort_keys=True)+'\n' for r in rs))
    write(OUT/'report.json',report);write(OUT/'input_payload_hashes.json',used)
    write(OUT/'event_plan_reference.json',json.loads((RELEASE/'episode_reservation.json').read_text()))
    files=list(OUT.iterdir())+[Path(__file__).resolve()]+manifests
    write(OUT/'manifest.json',{'files':{str(p.relative_to(ROOT)):sha(p) for p in files}})
    print(json.dumps({k:v for k,v in report.items() if k!='accounting_deltas'},indent=2))
if __name__=='__main__':main()
