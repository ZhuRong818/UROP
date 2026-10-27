"""Audit the closed point-forecast journals, without changing forecasts or labels."""
from collections import Counter
from datetime import datetime,timezone
import hashlib,json
from pathlib import Path
import numpy as np
from eventx.tasks.discover_v7_direct_pilot_20261022 import REPO_ROOT,now,sha,write,verify_originals
from eventx.v7.quote_experiment_20261024 import stamp
from eventx.v7.memory_quote_20261024 import MemoryQuoteTape,predict
from eventx.v7.segment_candidate_20261024 import forecast

OUT=REPO_ROOT/'data/v7/live_memory_completion_20261026'
BASE=REPO_ROOT/'data/v7/memory_quote_20261024/shadow'
SEG=REPO_ROOT/'data/v7/segment_candidate_20261024'
SRC=REPO_ROOT/'data/v7/quote_source_20261024_v02/live'
REL=REPO_ROOT/'eventx/release/v7/memory_shadow_20261024'
SREL=REPO_ROOT/'eventx/release/v7/segment_candidate_20261024'


def load(p):return json.loads(p.read_text())

def chain(p):
    rows=[];head=None
    for line in p.read_bytes().splitlines(keepends=True):
        assert line.endswith(b'\n'),'Partial journal'
        r=json.loads(line);v=dict(r);h=v.pop('record_sha256')
        assert v['previous_sha256']==head and hashlib.sha256(json.dumps(v,sort_keys=True,separators=(',',':')).encode()).hexdigest()==h
        rows.append(r);head=h
    return rows


def scores(rows,prediction):
    if not rows:return {'rows':0,'mae':None,'rmse':None,'mean_error':None}
    e=np.array([r[prediction]-r['target'] for r in rows]);return {'rows':len(rows),'mae':float(abs(e).mean()),'rmse':float(np.sqrt(np.mean(e**2))),'mean_error':float(e.mean())}


def main():
    assert now().timestamp()>stamp(load(BASE/'run_contract.json')['stop_at'])
    assert now().timestamp()>stamp(load(SEG/'run_contract.json')['stop_at'])
    assert load(BASE/'status.json')['phase']==load(SEG/'status.json')['phase']=='stopped'
    assert load(BASE/'status.json')['error_type'] is None and load(SEG/'status.json')['error_type'] is None
    OUT.mkdir(exist_ok=False)
    write(OUT/'consumption_receipt.json',{'at':now().isoformat(),'status':'started','scope':'Audit of closed live point forecasts;not historical classifier evaluation'})
    try:
        verify_originals();hashes={};manifests=[BASE/'completion_manifest.json',SEG/'completion_manifest.json',REL/'implementation_manifest.json',SREL/'implementation_manifest.json']
        for p in manifests:
            m=load(p)
            for name,h in m.get('files',m.get('locked_files',{})).items():
                assert sha(REPO_ROOT/name)==h,name;hashes[name]=h
        for p in [SRC/'journal.jsonl',SRC/'status.json',SRC/'run_contract.json']:
            hashes[str(p.relative_to(REPO_ROOT))]=sha(p)
        cfg=load(REL/'activation_policy.json');policy=load(REPO_ROOT/cfg['quote_policy']);models=load(REPO_ROOT/cfg['models']);samples=[json.loads(x) for x in (REPO_ROOT/cfg['cohort']).read_text().splitlines()]
        base=chain(BASE/'journal.jsonl');seg=chain(SEG/'journal.jsonl');source=chain(SRC/'journal.jsonl');source_by_hash={r['record_sha256']:r for r in source}
        assert base[-1]['record_sha256']==load(BASE/'completion_report.json')['journal_head_sha256']
        assert seg[-1]['record_sha256']==load(SEG/'completion_report.json')['journal_head_sha256']
        tape=MemoryQuoteTape(SRC,samples,policy);tape.refresh_live();assert tape.head==source[-1]['record_sha256']
        decisions={r['record_sha256']:r for r in base if r['kind']=='decision'}
        commits=[r for r in base if r['kind']=='emission_commit'];assert len({r['decision_sha256'] for r in commits})==len(commits)
        outcomes={r['decision_sha256']:r for r in base if r['kind']=='outcome'};assert len(outcomes)==sum(r['kind']=='outcome' for r in base)
        assert len({(r['market_id'],r['grid_at']) for r in decisions.values()})==len(decisions)
        contract=load(BASE/'run_contract.json');expected={(s['market_id'],t) for s in samples for t in range(int(stamp(contract['first_grid_at'])),int(stamp(contract['last_grid_at']))+1,300)}
        assert {(r['market_id'],int(stamp(r['grid_at']))) for r in decisions.values()}==expected
        feature_parity=0;endpoint_parity=0;delays=[];source_ages=[];receipt_ages=[];rows=[]
        for d in decisions.values():
            assert d['source_journal_head'] in source_by_hash
            f,why=tape.features(d['market_id'],int(stamp(d['grid_at'])))
            if d['status']=='ready':
                assert f is not None
                for key in ['snapshot_features','short_features']:
                    if d[key] is None:assert f[key] is None
                    else:assert np.allclose(f[key],d[key],rtol=0,atol=1e-12)
                assert f['input_payload_hashes']==d['input_payload_hashes']
                p,ood=predict(f,models);assert p.keys()==d['predictions'].keys()
                assert all(abs(p[k]-d['predictions'][k])<1e-12 for k in p)
                assert ood==d['outside_training_range'];feature_parity+=1
            elif d['status']=='abstained':assert f is None and why==d['reasons']
        for c in commits:
            d=decisions[c['decision_sha256']];delay=stamp(c['at'])-stamp(d['grid_at']);assert c['timely'] and 0<=delay<=policy['forward_emission_seconds'];delays.append(delay)
            assert d['models_sha256']==sha(REPO_ROOT/cfg['models'])
            assert stamp(d['recorded_at'])<=stamp(c['at'])<stamp(d['target_at'])
            assert c['decision_sha256'] in outcomes;o=outcomes[c['decision_sha256']]
            assert stamp(o['at'])>=stamp(d['target_at'])+policy['forward_adjudication_delay_seconds']
            target,why=tape.endpoint(d['market_id'],int(stamp(d['grid_at'])))
            assert target==o['target'] and why==o['reasons'] and o['status']==('observed' if target else 'unavailable');endpoint_parity+=1
            source_ages.append(stamp(d['grid_at'])-stamp(d['latest_book_source_at']));receipt_ages.append(stamp(d['grid_at'])-stamp(d['latest_book_available_at']))
            rows.append({'market_id':d['market_id'],'grid_at':d['grid_at'],'target_at':d['target_at'],'outcome_status':o['status'],'target':target['midpoint'] if target else None,'short_available':'short_ridge' in d['predictions'],**d['predictions'],'source_message_age_seconds':source_ages[-1],'receipt_age_seconds':receipt_ages[-1]})
        observed=[r for r in rows if r['target'] is not None];panels={}
        for tier in ['snapshot','short']:
            rr=[r for r in observed if tier=='snapshot' or r['short_available']];names=['persistence','weighted_midpoint','snapshot_ridge']+(['short_ridge'] if tier=='short' else [])
            panels[tier]={n:scores(rr,n) for n in names}
        completion=load(BASE/'completion_report.json')
        for tier,panel in panels.items():
            for n,m in panel.items():
                original=completion['matched_metrics'][tier][n]
                for k,v in m.items():assert abs(v-original[k])<1e-12,(tier,n,k)
        # Audit segment consumption against the already committed base forecasts.
        model=load(SREL/'model.json');sp={r['record_sha256']:r for r in seg if r['kind']=='forecast'};sc=[r for r in seg if r['kind']=='commit'];so={r['forecast_sha256']:r for r in seg if r['kind']=='outcome'}
        assert len(sc)==len({r['forecast_sha256'] for r in sc}) and len(so)==sum(r['kind']=='outcome' for r in seg)
        bc={r['record_sha256']:r for r in commits};bo={r['record_sha256']:r for r in outcomes.values()};srows=[]
        for c in sc:
            f=sp[c['forecast_sha256']];d=decisions[f['base_decision_sha256']];assert f['base_commit_sha256'] in bc
            assert c['timely'] and 0<=stamp(c['at'])-stamp(f['grid_at'])<=30
            assert stamp(bc[f['base_commit_sha256']]['at'])<=stamp(f['at'])<=stamp(c['at'])<stamp(f['target_at'])
            assert f['input_payload_hashes']==d['input_payload_hashes'] and f['model_sha256']==sha(SREL/'model.json')
            expected=forecast(d,model)
            assert f['segment_active']==expected['segment_active']
            for n in ['prediction','reference']:assert abs(f[n]-expected[n])<1e-12
            o=so[c['forecast_sha256']];assert o['base_outcome_sha256'] in bo;original=bo[o['base_outcome_sha256']]
            assert original['decision_sha256']==f['base_decision_sha256'] and o['target']==original['target'] and o['status']==original['status']
            assert stamp(o['at'])>=stamp(original['at'])
            srows.append({'market_id':f['market_id'],'grid_at':f['grid_at'],'segment_active':f['segment_active'],'outcome_status':o['status'],'target':o['target']['midpoint'] if o['target'] else None,'reference':f['reference'],'prediction':f['prediction']})
        sm={};sobserved=[r for r in srows if r['target'] is not None];completion_seg=load(SEG/'completion_report.json')
        for pop in ['all','segment']:
            rr=[r for r in sobserved if pop=='all' or r['segment_active']];sm[pop]={n:scores(rr,n) for n in ['reference','prediction']}
            for n,m in sm[pop].items():
                for k,v in m.items():assert abs(v-completion_seg['matched_metrics'][pop][n][k])<1e-12
        per_market=[]
        for s in samples:
            rr=[r for r in rows if r['market_id']==s['market_id']];oo=[r for r in rr if r['target'] is not None]
            per_market.append({'market_id':s['market_id'],'question':s.get('question'),'issued':len(rr),'observed':len(oo),'changes':sum(abs(r['target']-r['persistence'])>1e-12 for r in oo),'snapshot_metrics':{n:scores(oo,n) for n in ['persistence','weighted_midpoint','snapshot_ridge']}})
        report={'at':now().isoformat(),'passed':True,'scope':'Completed live point-midpoint forecasts,not quote-change classifier','decisions':len(decisions),'timely_forecasts':len(rows),'abstentions':sum(r['status']=='abstained' for r in decisions.values()),'missed':sum(r['status']=='missed' for r in decisions.values()),'observed':len(observed),'unavailable':len(rows)-len(observed),'changed_endpoints':sum(abs(r['target']-r['persistence'])>1e-12 for r in observed),'feature_replays':feature_parity,'endpoint_replays':endpoint_parity,'matched_metrics':panels,'per_market':per_market,'abstention_reasons':dict(Counter(reason for r in decisions.values() if r['status']=='abstained' for reason in r['reasons'])),'unavailable_reasons':dict(Counter(reason for r in outcomes.values() if r['status']!='observed' for reason in r['reasons'])),'max_emission_delay_seconds':max(delays),'book_receipt_age_max_seconds':max(receipt_ages),'book_source_age_median_seconds':float(np.median(source_ages)),'book_source_age_max_seconds':max(source_ages),'books_source_age_over120s':sum(x>120 for x in source_ages),'source_age_policy_note':'Frozen live gate bounds receipt age,not elapsed exchange-message age;source age is a feature and future source clocks are rejected. This differs from historical quote-change eligibility.','segment':{'timely':len(srows),'active':sum(r['segment_active'] for r in srows),'observed':len(sobserved),'unavailable':len(srows)-len(sobserved),'observed_active':sum(r['segment_active'] for r in sobserved),'matched_metrics':sm},'source_chain_records':len(source),'base_chain_records':len(base),'segment_chain_records':len(seg),'input_payloads_verified':len(tape.payload_hashes),'model_promoted':False,'news_tested':False,'independent_confirmation':False}
        write(OUT/'report.json',report);write(OUT/'matched_rows.json',rows);write(OUT/'segment_rows.json',srows)
        write(OUT/'consumption_receipt.json',{'at':now().isoformat(),'status':'completed','scope':'Closed live point-forecast audit;no model/label modification'})
        for path,h in tape.payload_hashes.items():hashes[str(Path(path).relative_to(REPO_ROOT))]=h
        for name,h in hashes.items():assert sha(REPO_ROOT/name)==h,name
        inputs=list(OUT.iterdir())+[Path(__file__).resolve()]+manifests
        write(OUT/'manifest.json',{'files':{**hashes,**{str(p.relative_to(REPO_ROOT)):sha(p) for p in inputs}}})
        print(json.dumps(report,indent=2))
    except Exception as e:
        write(OUT/'failure.json',{'at':now().isoformat(),'error':type(e).__name__,'message':str(e)[:500]})
        raise

if __name__=='__main__':main()
