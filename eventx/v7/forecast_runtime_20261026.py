"""V03 live runtime. No fitting, selection, trading, or automatic activation."""
from collections import defaultdict
from datetime import datetime, timezone, timedelta
from pathlib import Path
import hashlib
import json
import math
import os
import importlib.metadata
import platform
import numpy as np
from eventx.settings import REPO_ROOT
from eventx.v7.quote_experiment_20261024 import QuoteTape, stamp, iso
from eventx.v7.live_quote_inputs_20261026 import project_ws, transport_ready
from eventx.v7.clock_bounded_quote_inputs_20261026 import SourceTimeQuoteTape, clock_health, CONTRACT
from eventx.v7.native_clock_receipt_20261026 import selected_packet_check
from eventx.v7.source_time_study_20261026_v03 import predict, paired_summary, NAMES

REL = REPO_ROOT/'eventx/release/v7/forecast_runtime_20261026_v01'
BASE = REPO_ROOT/'data/v7/forecast_runtime_20261026_v01'
OLDREL = REPO_ROOT/'eventx/release/v7/source_time_study_20261026_v03'
OLD = REPO_ROOT/'data/v7/source_time_study_20261026_v03'
MODEL = OLD/'development/frozen_models.joblib'

def sha(path):
    with Path(path).open('rb') as f: return hashlib.file_digest(f, 'sha256').hexdigest()

def now(): return datetime.now(timezone.utc).timestamp()

def write_new(path, value):
    path = Path(path); path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('x') as f:
        json.dump(value, f, indent=2, sort_keys=True, allow_nan=False); f.write('\n'); f.flush(); os.fsync(f.fileno())

def verify_manifest(path):
    for name, h in json.loads(Path(path).read_text())['files'].items():
        if sha(REPO_ROOT/name) != h: raise RuntimeError('Frozen file mismatch: '+name)

def verify_release():
    verify_manifest(REL/'implementation_manifest.json')
    verify_manifest(OLDREL/'delivery_manifest.json')
    verify_manifest(OLD/'development/manifest.json')
    env=json.loads((REL/'environment.json').read_text())
    if platform.python_version()!=env['python']: raise RuntimeError('Python version drift')
    for package,version in env['packages'].items():
        if importlib.metadata.version(package)!=version: raise RuntimeError('Dependency version drift: '+package)

def read_chain(path, limit=None, partial=False):
    rows=[]; head=None; offset=0
    with Path(path).open('rb') as f:
        while limit is None or f.tell()<limit:
            line=f.readline()
            if not line: break
            if not line.endswith(b'\n'):
                if partial: break
                raise RuntimeError('Partial journal')
            r=json.loads(line); v=dict(r); h=v.pop('record_sha256')
            if v['previous_sha256']!=head or hashlib.sha256(json.dumps(v,sort_keys=True,separators=(',',':')).encode()).hexdigest()!=h:
                raise RuntimeError('Journal chain mismatch')
            rows.append(r); head=h; offset=f.tell()
    if limit is not None and offset!=limit: raise RuntimeError('Invalid source prefix boundary')
    return rows, head, offset

class Journal:
    def __init__(self, path):
        self.path=Path(path); self.head=None
        if self.path.exists(): _,self.head,_=read_chain(self.path)
    def append(self, value):
        r={**value,'previous_sha256':self.head}
        r['record_sha256']=hashlib.sha256(json.dumps(r,sort_keys=True,separators=(',',':'),allow_nan=False).encode()).hexdigest()
        with self.path.open('a') as f:
            f.write(json.dumps(r,sort_keys=True,allow_nan=False)+'\n'); f.flush(); os.fsync(f.fileno())
        self.head=r['record_sha256']; return r

def packet_clock_health(records,t):
    """Invalid selected packets cannot enter the frozen offset-interval calculation."""
    probes=[r for r in records if r.get('kind')=='clock_probe' and r['available_epoch']<=t]
    if not probes: return False,['clock_probe_missing']
    p=max(probes,key=lambda r:r['available_epoch'])
    checked={**p,'measurements':[m for m in p['measurements'] if selected_packet_check(m)['valid']]}
    return clock_health([checked],t)

def grids(first,last):
    return [t for t in range(int(first),int(last)+1,300) if 1800<=t%86400<84600]

def window(activated):
    day=int(activated//86400+1)*86400
    return {'first_grid':day+1800,'last_grid':day+6*86400+84300,'open_after':day+6*86400+84300+1920}

def require_activation(receipt, at):
    """No activation file is created by the emitter, collector, or evaluator."""
    expected=window(receipt['activated_epoch'])
    if any(receipt.get(k)!=v for k,v in expected.items()): raise RuntimeError('Invalid fixed seven-day window')
    if receipt['activated_epoch']>=receipt['first_grid'] or at<receipt['activated_epoch']: raise RuntimeError('Activation clock invalid')
    if receipt.get('input_contract')!=CONTRACT: raise RuntimeError('Activation input mismatch')
    for key,path in [('implementation_sha256',REL/'implementation_manifest.json'),('model_sha256',MODEL),('cohort_sha256',OLDREL/'live_cohort.jsonl'),('protocol_sha256',OLDREL/'protocol.json')]:
        if receipt.get(key)!=sha(path): raise RuntimeError('Activation hash mismatch: '+key)
    ready=BASE/'readiness_audit/report.json'
    verify_manifest(BASE/'readiness_audit/manifest.json')
    verify_manifest(BASE/'readiness/capture_manifest.json')
    if receipt.get('readiness_sha256')!=sha(ready) or not json.loads(ready.read_text())['passed']: raise RuntimeError('Readiness missing or failed')
    if receipt['activated_epoch']<stamp(json.loads(ready.read_text())['completed_at']): raise RuntimeError('Activation predates readiness')
    if receipt.get('source_path')!=str((BASE/'prospective/source').relative_to(REPO_ROOT)): raise RuntimeError('Source path mismatch')
    return expected

class Inputs:
    def __init__(self,root,samples,limit=None):
        self.root=Path(root);self.samples=samples
        self.records,self.head,self.offset=read_chain(self.root/'journal.jsonl',limit,partial=limit is None)
        self.status=QuoteTape(root,samples,{'book_max_age_seconds':120,'status_max_age_seconds':360,'max_spread':.05,'min_best_size':0})
        self.by=defaultdict(list);self.errors=[]
        for r in self.records:
            if r['kind']=='rest': self.status.ingest(r)
            if r['kind']=='ws_frame':
                p=self.root/'objects'/r['payload_sha256']
                if sha(p)!=r['payload_sha256']: raise RuntimeError('Payload hash mismatch')
                try:
                    for row in project_ws(json.loads(p.read_text()),r['available_at'],r['response_received_at'],samples): self.by[row['market'].decode()].append(row)
                except (ValueError,TypeError,KeyError) as e:
                    self.errors.append({'at':stamp(r['available_at']),'reason':type(e).__name__})
        self.tapes={s['market_id']:SourceTimeQuoteTape(self.by[s['market_id']]) for s in samples}
    def refresh(self):
        with (self.root/'journal.jsonl').open('rb') as f:
            f.seek(self.offset)
            while True:
                line=f.readline()
                if not line or not line.endswith(b'\n'): break
                r=json.loads(line);v=dict(r);h=v.pop('record_sha256')
                if v['previous_sha256']!=self.head or hashlib.sha256(json.dumps(v,sort_keys=True,separators=(',',':')).encode()).hexdigest()!=h:
                    raise RuntimeError('Incremental source chain mismatch')
                self.records.append(r);self.head=h;self.offset=f.tell()
                if r['kind']=='rest': self.status.ingest(r)
                if r['kind']=='ws_frame':
                    p=self.root/'objects'/r['payload_sha256']
                    if sha(p)!=r['payload_sha256']: raise RuntimeError('Payload hash mismatch')
                    try:
                        for row in project_ws(json.loads(p.read_text()),r['available_at'],r['response_received_at'],self.samples): self.by[row['market'].decode()].append(row)
                    except (ValueError,TypeError,KeyError) as e: self.errors.append({'at':stamp(r['available_at']),'reason':type(e).__name__})
        self.tapes={s['market_id']:SourceTimeQuoteTape(self.by[s['market_id']]) for s in self.samples}
    def current(self,cid,t):
        f=self.tapes[cid].features(t);_,reasons=transport_ready(self.records,t)
        _,clock=packet_clock_health(self.records,t);reasons+=clock
        if any(e['at']<=t for e in self.errors): reasons.append('source_schema_error')
        if f is None: reasons.append('quote_missing_stale_invalid_or_conflicting')
        meta=self.status.at(cid,'market_metadata',t);res=self.status.at(cid,'resolution_state',t)
        if meta is None or res is None: reasons.append('metadata_resolution_invalid_or_stale')
        if meta and (meta['scheduled_end'] is None or meta['scheduled_end']<=t+1800): reasons.append('expiry_not_beyond_horizon')
        return (f if not reasons else None),reasons
    def endpoint(self,cid,t):
        end=t+1800; quote=self.tapes[cid].at(end)
        _,reasons=transport_ready(self.records,end);_,clock=packet_clock_health(self.records,end);reasons+=clock
        if quote is None: reasons.append('endpoint_quote_invalid')
        if any(e['at']<=end for e in self.errors): reasons.append('source_schema_error')
        for kind in ['market_metadata','resolution_state']:
            if not self.status.covers(cid,kind,t,end): reasons.append('forward_'+kind+'_coverage_failed')
        # Every intervening metadata version must retain expiry beyond the target.
        meta=[self.status.at(cid,'market_metadata',t)]+[r for r in self.status.series[(cid,'market_metadata')] if t<r['at']<=end]
        if any(r is None or r.get('scheduled_end') is None or r['scheduled_end']<=end for r in meta): reasons.append('forward_expiry_failed')
        return (quote['midpoint'] if quote and not reasons else None),reasons

def decision(inputs,bundle,cid,t,at):
    base={'kind':'decision','market_id':cid,'t':t,'target_at':t+1800,'recorded_at':at,'source_bytes':inputs.offset,'source_head':inputs.head}
    if at<t: raise ValueError('Future decision')
    if at>t+30: return {**base,'status':'missed','features':None,'predictions':{},'reasons':['emission_deadline_missed']}
    f,reasons=inputs.current(cid,t)
    if f is None: return {**base,'status':'abstained','features':None,'predictions':{},'reasons':reasons}
    p=predict(bundle,[{'market_id':cid,'features':f}])
    return {**base,'status':'ready','features':f,'predictions':{n:float(v[0]) for n,v in p.items()},'reasons':[]}

def evaluate_rows(rows):
    p={n:np.array([r['predictions'][n] for r in rows]) for n in NAMES}
    result=subset(rows,lambda r:True)
    result['nonoverlap']=subset(rows,lambda r:r['t']%1800==0)
    result['by_market']={cid:subset(rows,lambda r:r['market_id']==cid) for cid in sorted({r['market_id'] for r in rows})}
    result['by_date']={date:subset(rows,lambda r:iso(r['t'])[:10]==date) for date in sorted({iso(r['t'])[:10] for r in rows})}
    result['equal_contract_log_loss']={n:float(np.mean([v['metrics'][n]['log_loss'] for v in result['by_market'].values() if v['known']])) if result['known'] else None for n in NAMES}
    result['calibration']={}
    bins=[0,.05,.1,.2,.4,.6,.8,1]
    for n in NAMES:
        result['calibration'][n]=[]
        for lo,hi in zip(bins[:-1],bins[1:]):
            rr=[r for r in rows if r['target'] is not None and lo<=r['predictions'][n]<hi]
            result['calibration'][n].append({'lower':lo,'upper':hi,'n':len(rr),'mean_probability':float(np.mean([r['predictions'][n] for r in rr])) if rr else None,'observed_rate':float(np.mean([r['target'] for r in rr])) if rr else None})
    pos=sum(r['target'] or 0 for r in rows);known=result['known']
    result['minimum_reporting_passed']=known>=100 and pos>=20 and known-pos>=20
    result['descriptive_improvement']=bool(result['minimum_reporting_passed'] and all(result['metrics']['hgb7']['log_loss']<result['metrics'][n]['log_loss'] and result['metrics']['hgb7']['brier']<=result['metrics'][n]['brier'] for n in ['full_logit','global_rate']))
    result['inference']='Descriptive only; no IID intervals, profit, news or independent-event claim'
    return result

def subset(rows,predicate):
    rr=[r for r in rows if predicate(r)]
    if not rr:
        return {'issued':0,'known':0,'unknown':0,'metrics':{n:{'n':0,'positives':0,'log_loss':None,'brier':None,'average_precision':None,'roc_auc':None} for n in NAMES},'contrasts':{n:{'log_loss_gain':None,'relative_reduction_pct':None,'all_issued_gain_bounds':None} for n in NAMES if n!='hgb7'}}
    return paired_summary(rr,{n:np.array([r['predictions'][n] for r in rr]) for n in NAMES})
