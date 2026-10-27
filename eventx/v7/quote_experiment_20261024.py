"""Point-in-time quote measurements for the separate V7 midpoint experiment."""
from bisect import bisect_right
from collections import defaultdict
from datetime import datetime,timezone
import hashlib
import json
from pathlib import Path
import numpy as np

FEATURES=['midpoint','spread','log_bid_size','log_ask_size','imbalance','weighted_mid_shift',
          'momentum5','momentum30','momentum120','volatility30','volatility240','log_quote_message_age_minutes']

def stamp(s):
    if isinstance(s,(int,float)) or str(s).replace('.','',1).isdigit():
        n=float(s);return n/1000 if n>1e11 else n
    return datetime.fromisoformat(s.replace('Z','+00:00')).timestamp()

def iso(t):return datetime.fromtimestamp(t,timezone.utc).isoformat()
def digest(p):
    with Path(p).open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()

class QuoteTape:
    def __init__(self,root,samples,policy):
        self.root=Path(root);self.samples={r['market_id']:r for r in samples};self.policy=policy
        self.series=defaultdict(list);self.times=defaultdict(list);self.cache={};self.payload_hashes={}
        self.offset=0;self.head=None

    def payload(self,r):
        h=r['payload_sha256']
        if h not in self.cache:
            p=self.root/'objects'/h
            if digest(p)!=h:raise RuntimeError('Quote input payload hash mismatch')
            self.cache[h]=json.loads(p.read_text());self.payload_hashes[str(p)]=h
        return self.cache[h]

    def ingest(self,r):
        cid=r.get('market_id');kind=r.get('endpoint_kind')
        if cid not in self.samples or r.get('source')!='venue' or kind not in ['book_yes_asset_id','market_metadata','resolution_state']:return
        av=r.get('available_at') or r.get('finished_at')
        if not av:return
        item={'at':stamp(av),'ok':False,'receipt_sha256':r.get('record_sha256'),'payload_sha256':r.get('payload_sha256')}
        if r.get('status')=='observed':
            s=self.samples[cid];v=self.payload(r)
            if kind=='book_yes_asset_id':
                if v.get('market')!=cid or str(v.get('asset_id'))!=s['yes_asset_id']:raise RuntimeError('Quote identity mismatch')
                bids=[(float(x['price']),float(x['size'])) for x in v.get('bids',[]) if float(x['size'])>0]
                asks=[(float(x['price']),float(x['size'])) for x in v.get('asks',[]) if float(x['size'])>0]
                if bids and asks and v.get('timestamp'):
                    b=max(x[0] for x in bids);a=min(x[0] for x in asks)
                    qb=sum(q for p,q in bids if p==b);qa=sum(q for p,q in asks if p==a)
                    item.update(ok=0<b<=a<1 and a-b<=self.policy['max_spread']+1e-12 and min(qb,qa)>=self.policy['min_best_size'],
                        source_at=stamp(v['timestamp']),mid=(a+b)/2,spread=a-b,bid_size=qb,ask_size=qa,
                        imbalance=(qb-qa)/(qb+qa),weighted=(a*qb+b*qa)/(qb+qa))
            elif kind=='market_metadata':
                if isinstance(v,list) and len(v)==1:
                    m=v[0];tokens=m.get('clobTokenIds',[]);outcomes=m.get('outcomes',[])
                    if isinstance(tokens,str):tokens=json.loads(tokens)
                    if isinstance(outcomes,str):outcomes=json.loads(outcomes)
                    same=m.get('conditionId')==cid and tokens==[s['yes_asset_id'],s['no_asset_id']] and outcomes==['Yes','No'] and m.get('description')==s['rules']
                    item.update(ok=bool(same and m.get('acceptingOrders') is True and m.get('closed') is False and m.get('active') is True),
                        scheduled_end=stamp(m['endDate']) if m.get('endDate') else None)
            else:
                rows=v.get('data',[])
                if len(rows)==1:
                    m=rows[0]
                    item['ok']=m.get('condition_id')==cid and m.get('status')=='posed' and not m.get('resolved_at') and not m.get('was_disputed')
        key=(cid,kind);i=bisect_right(self.times[key],item['at'])
        self.times[key].insert(i,item['at']);self.series[key].insert(i,item)

    def load_frozen(self,journal):
        with Path(journal).open() as f:
            for line in f:
                r=json.loads(line)
                if r['kind']=='rest':self.ingest(r)

    def refresh_live(self):
        with (self.root/'journal.jsonl').open('rb') as f:
            f.seek(self.offset)
            while True:
                line=f.readline()
                if not line or not line.endswith(b'\n'):break
                r=json.loads(line);v=dict(r);h=v.pop('record_sha256')
                actual=hashlib.sha256(json.dumps(v,sort_keys=True,separators=(',',':')).encode()).hexdigest()
                if h!=actual or v['previous_sha256']!=self.head:raise RuntimeError('Source live chain mismatch')
                self.head=h;self.offset=f.tell()
                if r['kind']=='rest':self.ingest(r)

    def at(self,cid,kind,t):
        key=(cid,kind);i=bisect_right(self.times[key],t)-1
        if i<0:return None
        r=self.series[key][i];age=self.policy['book_max_age_seconds'] if kind=='book_yes_asset_id' else self.policy['status_max_age_seconds']
        if not r['ok'] or not 0<=t-r['at']<=age:return None
        if kind=='book_yes_asset_id' and r['source_at']>t:return None
        return r

    def covers(self,cid,kind,start,end):
        first=self.at(cid,kind,start)
        if first is None:return False
        key=(cid,kind);i=bisect_right(self.times[key],start);j=bisect_right(self.times[key],end)
        age=self.policy['book_max_age_seconds'] if kind=='book_yes_asset_id' else self.policy['status_max_age_seconds']
        prev=first['at']
        for r in self.series[key][i:j]:
            if not r['ok'] or r['at']-prev>age:return False
            if kind=='book_yes_asset_id' and r['source_at']>r['at']:return False
            prev=r['at']
        return end-prev<=age

    def features(self,cid,t):
        reasons=[];b=self.at(cid,'book_yes_asset_id',t);m=self.at(cid,'market_metadata',t);r=self.at(cid,'resolution_state',t)
        if b is None:reasons.append('current_book_missing_stale_or_quality_failed')
        if m is None:reasons.append('current_mapping_rules_or_active_status_unverified')
        if r is None:reasons.append('current_unresolved_status_unverified')
        if m and (m['scheduled_end'] is None or m['scheduled_end']<=t+1800):reasons.append('scheduled_terminal_not_beyond_horizon')
        if not self.covers(cid,'book_yes_asset_id',t-14400,t):reasons.append('incomplete_quality_240m_book_history')
        if reasons:return None,reasons
        history=[self.at(cid,'book_yes_asset_id',u) for u in range(t-14400,t+1,60)]
        if any(x is None for x in history):return None,['minute_history_unavailable']
        mids=np.array([x['mid'] for x in history]);d=np.diff(mids)
        x=[b['mid'],b['spread'],np.log1p(b['bid_size']),np.log1p(b['ask_size']),b['imbalance'],b['weighted']-b['mid'],
            mids[-1]-mids[-6],mids[-1]-mids[-31],mids[-1]-mids[-121],np.std(d[-30:]),np.std(d),np.log1p((t-b['source_at'])/60)]
        if not np.isfinite(x).all():return None,['nonfinite_features']
        hashes=sorted({z['payload_sha256'] for z in history+[m,r]})
        return {'features':list(map(float,x)),'midpoint':b['mid'],'weighted_midpoint':b['weighted'],
                'input_payload_hashes':hashes,'latest_book_available_at':iso(b['at'])},[]

    def endpoint(self,cid,t):
        end=t+1800;reasons=[]
        for kind in ['book_yes_asset_id','market_metadata','resolution_state']:
            if not self.covers(cid,kind,t,end):reasons.append('forward_'+kind+'_coverage_or_status_failed')
        b=self.at(cid,'book_yes_asset_id',end)
        if b is None:reasons.append('endpoint_book_unavailable')
        if reasons:return None,reasons
        return {'midpoint':b['mid'],'available_at':iso(b['at']),'payload_sha256':b['payload_sha256']},[]

def predictions(feature,model):
    x=np.array(feature['features']);z=(x-np.array(model['center']))/np.array(model['scale'])
    delta=float(model['intercept']+z@np.array(model['coefficients']))
    return {'persistence':feature['midpoint'],'weighted_midpoint':feature['weighted_midpoint'],
            'ridge':float(np.clip(feature['midpoint']+delta,0,1))}
