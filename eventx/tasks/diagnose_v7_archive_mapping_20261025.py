"""Bounded identity-only endpoint probes for two failed historical conditions."""
import hashlib
import json
from pathlib import Path
import httpx
from eventx.tasks.discover_v7_direct_pilot_20261022 import REPO_ROOT,now,sha,write

def main():
    root=REPO_ROOT/'data/v7/archive_mapping_diagnosis_20261025';root.mkdir(exist_ok=False)
    parent=REPO_ROOT/'data/v7/archive_sample_20261024_v02/attempt_20261024T144922Z_e81ec5'
    for p,h in json.loads((parent/'manifest.json').read_text())['files'].items():
        if sha(REPO_ROOT/p)!=h:raise RuntimeError('Parent drift')
    ids=json.loads((parent/'candidate_ids_before_prices.json').read_text())[:2]
    control=json.loads((REPO_ROOT/'eventx/release/v7/memory_quote_20261024/forward_cohort.jsonl').read_text().splitlines()[1])['market_id']
    jobs=[]
    for cid in ids:
        for flags in [{},{'closed':'true'},{'archived':'true'},{'closed':'true','archived':'true'}]:jobs.append(('gamma',cid,'https://gamma-api.polymarket.com/markets',{'condition_ids':cid,**flags}))
        jobs.append(('clob',cid,'https://clob.polymarket.com/markets/'+cid,{}))
    jobs.append(('gamma_control',control,'https://gamma-api.polymarket.com/markets',{'condition_ids':control}))
    rows=[]
    with httpx.Client(timeout=20,follow_redirects=True) as c:
        for kind,cid,url,params in jobs:
            r={'at':now().isoformat(),'kind':kind,'requested_condition_id':cid,'url':url,'params':params}
            try:
                response=c.get(url,params=params);r.update(http_status=response.status_code,body_sha256=hashlib.sha256(response.content).hexdigest());response.raise_for_status();v=response.json()
                r['response_shape']=type(v).__name__;r['rows']=len(v) if isinstance(v,list) else None
                if isinstance(v,list):
                    r['identity_matches']=[m.get('conditionId')==cid for m in v]
                    r['matched_metadata']=[{k:m.get(k) for k in ['conditionId','question','description','clobTokenIds','outcomes','startDate','endDate','active','closed','archived']} for m in v if m.get('conditionId')==cid]
                else:
                    r['identity_match']=v.get('condition_id')==cid
                    if r['identity_match']:
                        r['matched_metadata']={k:v.get(k) for k in ['condition_id','question','description','end_date_iso','active','closed','archived']}
                        r['matched_metadata']['tokens']=[{k:t.get(k) for k in ['token_id','outcome']} for t in v.get('tokens',[])]
            except Exception as e:r['error_type']=type(e).__name__
            rows.append(r);write(root/'probes.json',rows)
    write(root/'manifest.json',{'files':{str(p.relative_to(REPO_ROOT)):sha(p) for p in [root/'probes.json',parent/'manifest.json',Path(__file__).resolve()]}})
    print(json.dumps([{k:r.get(k) for k in ['kind','params','http_status','rows','identity_match','identity_matches','error_type']} for r in rows],indent=2))

if __name__=='__main__':main()
