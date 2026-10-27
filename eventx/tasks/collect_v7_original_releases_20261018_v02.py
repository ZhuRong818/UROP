"""Capture official economic releases with first-observation receipts; no models.

Dedicated source-feasibility pilot. It never accesses V4 sealed inputs, prediction
market data, labels, or model fitting. Run with --once for an initial real pull or
without it for continuous source capture until the declared end.
"""
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone, timedelta
from email.utils import parsedate_to_datetime
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urljoin, urlsplit, urlunsplit
import argparse
import fcntl
import hashlib
import json
import os
import re
import shutil
import subprocess
import time
import threading
import uuid
import xml.etree.ElementTree as ET
import httpx

ROOT = Path(__file__).resolve().parents[2]
RELEASE = ROOT / 'eventx/release/v7/original_source_capture_20261018_v02'
OUT = ROOT / 'data/v7/official_source_capture_20261018/live'


def now(): return datetime.now(timezone.utc)
def dt(s): return datetime.fromisoformat(s.replace('Z','+00:00'))
def digest(b): return hashlib.sha256(b).hexdigest()
def filehash(p):
    with p.open('rb') as f: return hashlib.file_digest(f,'sha256').hexdigest()
def canonical(x): return json.dumps(x,sort_keys=True,separators=(',',':'),allow_nan=False).encode()
def atomic(p,x):
    p.parent.mkdir(parents=True,exist_ok=True)
    tmp=p.with_suffix('.tmp')
    with tmp.open('w') as f:
        json.dump(x,f,indent=2,sort_keys=True,allow_nan=False);f.write('\n');f.flush();os.fsync(f.fileno())
    os.replace(tmp,p)


class Text(HTMLParser):
    def __init__(self):
        super().__init__();self.parts=[];self.skip=0
    def handle_starttag(self,tag,attrs):
        if tag in ('script','style','noscript'):self.skip+=1
    def handle_endtag(self,tag):
        if tag in ('script','style','noscript') and self.skip:self.skip-=1
    def handle_data(self,data):
        if not self.skip:self.parts.append(data)


class Collector:
    def __init__(self):
        self.manifest=json.loads((RELEASE/'implementation_manifest.json').read_text())
        self.verify()
        self.config=json.loads((RELEASE/'capture_contract.json').read_text())
        self.schedule=json.loads((RELEASE/'schedule.json').read_text())['events']
        OUT.mkdir(parents=True,exist_ok=True)
        self.lock=(OUT/'collector.lock').open('a+')
        fcntl.flock(self.lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
        self.seq=0;self.last_hash=None;self.urls={};self.versions=0;recovered_queue={}
        journal=OUT/'journal.jsonl'
        if journal.exists():
            for line in journal.open():
                r=json.loads(line);h=r.pop('record_sha256')
                if r['previous_sha256']!=self.last_hash or digest(canonical(r))!=h:
                    raise RuntimeError('Journal chain failure; preserve and investigate')
                self.last_hash=h;self.seq=r['sequence']
                if r['kind']=='observation':self.urls[r['data']['url']]=r['data']
                if r['kind']=='document_version':self.versions+=1
                if r['kind']=='feed_item':
                    item=r['data'];recovered_queue[item['url']]={'url':item['url'],'kind':'document','title':item.get('title'),'published_at':item.get('published_at'),'discovered_via':'journal_feed_item','interval_seconds':300}
        self.journal=journal.open('a',buffering=1)
        self.journal_lock=threading.Lock()
        startfile=OUT/'start_receipt.json'
        if not startfile.exists():atomic(startfile,{'started_at':now().isoformat(),'contract_sha256':filehash(RELEASE/'capture_contract.json'),
            'implementation_manifest_sha256':filehash(RELEASE/'implementation_manifest.json'),
            'scope':'source_feasibility_only; no forecast cohort or confirmation admission', 'pid':os.getpid()})
        self.start=dt(json.loads(startfile.read_text())['started_at'])
        self.queue={**recovered_queue,**{url:r['job'] for url,r in self.urls.items() if r.get('job',{}).get('discovered_via')}}
        self.emit('process_start',{'pid':os.getpid(),'model_fingerprint_verified':True})
        self.last_model_check=time.monotonic()

    def verify(self):
        for rel,h in self.manifest['locked_files'].items():
            if filehash(ROOT/rel)!=h:raise RuntimeError('Locked input changed: '+rel)

    def emit(self,kind,data):
        with self.journal_lock:
            return self._emit(kind,data)

    def _emit(self,kind,data):
        self.seq+=1
        r={'sequence':self.seq,'recorded_at':now().isoformat(),'kind':kind,'previous_sha256':self.last_hash,'data':data}
        h=digest(canonical(r));r['record_sha256']=h
        self.journal.write(json.dumps(r,sort_keys=True,allow_nan=False)+'\n');self.journal.flush();os.fsync(self.journal.fileno())
        self.last_hash=h
        return r['recorded_at']

    def normalize(self,url):
        u=urlsplit(url)
        if u.scheme!='https' or u.hostname not in self.config['allowed_hosts'] or u.username or u.password:
            raise ValueError('Source URL outside official allowlist')
        return urlunsplit((u.scheme,u.netloc,u.path,u.query,''))

    def fetch(self,job):
        url=self.normalize(job['url']);prior=self.urls.get(url,{})
        request_id=uuid.uuid4().hex
        self.emit('request',{'request_id':request_id,'url':url,'job':job,'prior_payload_sha256':prior.get('payload_sha256')})
        r={'request_id':request_id,'url':url,'job':job,'request_started_at':now().isoformat(),
            'previous_version_sha256':prior.get('payload_sha256'),'first_seen_at':prior.get('first_seen_at')}
        body=None
        headers={'User-Agent':'EventXResearchCapture/1.0 (official public economic releases)', 'Accept-Encoding':'gzip, deflate'}
        if prior.get('etag'):headers['If-None-Match']=prior['etag']
        if prior.get('last_modified'):headers['If-Modified-Since']=prior['last_modified']
        try:
            with httpx.Client(timeout=15,follow_redirects=False,headers=headers) as client:
                response=client.get(url)
                redirects=[]
                for _ in range(3):
                    if response.status_code not in [301,302,303,307,308]:break
                    target=self.normalize(urljoin(str(response.url),response.headers.get('location','')))
                    self.emit('redirect_request',{'request_id':request_id,'from':str(response.url),'to':target})
                    redirects.append({'from':str(response.url),'to':target,'status':response.status_code})
                    response=client.get(target)
                r['redirects']=redirects;r['final_url']=str(response.url)
            r.update(http_status=response.status_code,content_type=response.headers.get('content-type',''),
                response_date=response.headers.get('date'),etag=response.headers.get('etag'),
                last_modified=response.headers.get('last-modified'),retry_after=response.headers.get('retry-after'))
            body=response.content
            if len(body)>self.config['max_payload_bytes']:raise ValueError('Payload size cap; incomplete, not admitted')
            if 300<=response.status_code<400 and response.status_code!=304:
                r['error']='Redirect limit exceeded; preserve failed request'
            if response.status_code==200:
                is_xml=job['kind']=='feed'
                is_pdf=job['kind']=='pdf'
                if is_xml:ET.fromstring(body)
                elif is_pdf:
                    if not body.startswith(b'%PDF-'):raise ValueError('Expected PDF signature absent')
                elif 'html' not in r['content_type'].lower():raise ValueError('Expected HTML content type absent')
                h=digest(body);path=OUT/'objects'/h[:2]/(h+'.body');path.parent.mkdir(parents=True,exist_ok=True)
                if not path.exists():
                    with path.open('xb') as f:f.write(body);f.flush();os.fsync(f.fileno())
                elif filehash(path)!=h:raise RuntimeError('Stored source object hash failure')
                r['payload_sha256']=h;r['payload_path']=str(path.relative_to(ROOT));r['bytes']=len(body)
                # available_at follows durable storage, never a claimed publisher date.
                r['available_at']=now().isoformat();r['first_seen_at']=prior.get('first_seen_at') or r['available_at']
                r['last_success_at']=r['available_at'];r['status']='captured'
                r['new_version']=h!=prior.get('payload_sha256')
                if not r['new_version']:r['available_at']=prior['available_at']
                if job['kind'] not in ['feed','calendar']:
                    pub=job.get('published_at') or job.get('scheduled_at')
                    try:pubdt=dt(pub) if pub else None
                    except (ValueError,TypeError):pubdt=None
                    r['source_time_claim']=pub
                    r['cohort_role']='baseline_or_unverified'
                    if pubdt and self.start<=pubdt<=now():r['cohort_role']='prospective_source_candidate_not_forecast_admission'
                    elif pubdt and pubdt<self.start:r['cohort_role']='historical_baseline_import'
                    r['observation_lag_seconds']=(dt(r['available_at'])-pubdt).total_seconds() if pubdt else None
                    r['source_identity']='raw_captured_pending_semantic_identity_review'
                    if is_pdf and shutil.which('pdftotext'):
                        result=subprocess.run(['pdftotext','-f','1','-l','1',str(path),'-'],capture_output=True,text=True,timeout=15)
                        text=result.stdout if result.returncode==0 else ''
                    else:
                        parser=Text();parser.feed(body.decode('utf-8',errors='replace'));text=' '.join(parser.parts)
                    if text:
                        th=digest(text.encode());tp=OUT/'texts'/(th+'.txt');tp.parent.mkdir(exist_ok=True)
                        if not tp.exists():tp.write_text(text)
                        r['text_sha256']=th;r['text_path']=str(tp.relative_to(ROOT))
                        required=job.get('identity_terms',[])
                        if required and all(term.lower() in text.lower() for term in required):
                            r['source_identity']='expected_title_and_reference_period_found; release_clock_not_independently_authenticated'
                    # A scheduled date is a plan, not an authenticated publication clock.
                    r['lag_clock_kind']='announced_schedule_not_actual_publication' if job.get('scheduled_at') else 'publisher_feed_claim'
            elif response.status_code==304 and prior.get('payload_sha256'):
                for k in ['payload_sha256','payload_path','bytes','available_at','first_seen_at','cohort_role','text_path','text_sha256']:
                    if k in prior:r[k]=prior[k]
                r['status']='unchanged_304';r['last_success_at']=now().isoformat()
            else:r['status']='unknown_failed_request'
        except Exception as exc:
            r.update(status='unknown_failed_request',error_type=type(exc).__name__,error=str(exc)[:200])
        r['response_finished_at']=now().isoformat()
        # Keep latest known success metadata through transient failures for version links.
        for k in ['payload_sha256','payload_path','bytes','available_at','first_seen_at','last_success_at']:
            if k not in r and k in prior:r[k]=prior[k]
        r['consecutive_failures']=0 if r.get('status') in ['captured','unchanged_304'] else prior.get('consecutive_failures',0)+1
        return r,body

    def discover(self,r,body):
        if r['job']['kind']!='feed' or not body or r.get('http_status')!=200:return
        tree=ET.fromstring(body)
        for item in tree.findall('.//item'):
            url=(item.findtext('link') or '').strip()
            if not url:continue
            try:url=self.normalize(url)
            except ValueError:
                self.emit('discovery_exclusion',{'url':url,'reason':'not_in_official_host_allowlist'});continue
            published=item.findtext('pubDate')
            try:published=parsedate_to_datetime(published).astimezone(timezone.utc).isoformat() if published else None
            except (ValueError,TypeError):published=None
            self.queue[url]={'url':url,'kind':'document','title':item.findtext('title'),
                'published_at':published,'discovered_via':r['url'],'interval_seconds':300}
            self.emit('feed_item',{'url':url,'title':item.findtext('title'),'published_at':published,'feed_receipt_id':r['request_id']})

    def due(self,job,interval):
        prior=self.urls.get(job['url'],{})
        seconds=interval
        if prior.get('http_status') in [401,403]:seconds=max(seconds,21600)
        elif prior.get('consecutive_failures',0):seconds=max(seconds,min(3600,30*2**min(prior['consecutive_failures'],7)))
        retry=prior.get('retry_after')
        if retry:
            try:seconds=max(seconds,int(retry))
            except ValueError:
                try:seconds=max(seconds,(parsedate_to_datetime(retry)-dt(prior['response_finished_at'])).total_seconds())
                except (ValueError,TypeError):pass
        return not prior.get('response_finished_at') or (now()-dt(prior['response_finished_at'])).total_seconds()>=seconds

    def jobs(self):
        jobs={j['url']:dict(j) for j in self.config['sources']}
        burst_feeds=set()
        for e in self.schedule:
            elapsed=(now()-dt(e['scheduled_at'])).total_seconds()
            # Never request a guessed future document before its announced release.
            if 0<=elapsed<=86400:
                job=dict(e['document']);job.update(event_id=e['event_id'],scheduled_at=e['scheduled_at'])
                job['interval_seconds']=15 if elapsed<=900 else (60 if elapsed<=3600 else 3600)
                jobs[job['url']]=job
            if -120<=elapsed<=900:burst_feeds.update(e.get('feed_ids',[]))
        for j in jobs.values():
            if j.get('source_id') in burst_feeds:j['interval_seconds']=15
        for url,j in self.queue.items():
            # Revisit known documents for 48h after publisher date or discovery;
            # baseline older documents retained but not fetched repeatedly forever.
            prior=self.urls.get(url,{})
            base=j.get('published_at') or prior.get('first_seen_at')
            if not prior.get('payload_sha256') or (base and now()-dt(base)<timedelta(hours=48)):
                jobs.setdefault(url,j)
        due=[j for j in jobs.values() if self.due(j,j.get('interval_seconds',300))]
        # Scheduled releases and feeds always precede baseline-document backlogs.
        due.sort(key=lambda j:(0 if j.get('event_id') else 1 if j['kind']=='feed' else 2, j['url']))
        return due[:24]

    def cycle(self):
        if time.monotonic()-self.last_model_check>3600:self.verify();self.last_model_check=time.monotonic()
        jobs=self.jobs()
        with ThreadPoolExecutor(max_workers=4) as pool:
            for r,body in pool.map(self.fetch,jobs):
                self.emit('observation',r);self.urls[r['url']]=r
                if r.get('new_version') and r['job']['kind'] not in ['feed','calendar']:
                    self.emit('document_version',r);self.versions+=1
                self.discover(r,body)
        status={url:{k:r.get(k) for k in ['status','http_status','response_finished_at','last_success_at','first_seen_at','cohort_role','consecutive_failures']} for url,r in self.urls.items()}
        atomic(OUT/'status.json',{'at':now().isoformat(),'pid':os.getpid(),'started_at':self.start.isoformat(),
            'scope':'source_feasibility_only','document_versions':self.versions,'observed_urls':len(self.urls),
            'journal_records':self.seq,'journal_head_sha256':self.last_hash,'urls':status,
            'model_fixed':True,'market_data_read':False,'labels_or_predictions_computed':False,
            'timeliness_guaranteed':False,'stop_at':self.config['stop_at']})

    def run(self,once):
        while now()<dt(self.config['stop_at']):
            if (OUT/'STOP').exists():self.emit('process_stop',{'reason':'STOP file'});break
            self.cycle()
            if once:break
            time.sleep(5)


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--once',action='store_true');args=parser.parse_args()
    collector=Collector();collector.run(args.once)


if __name__=='__main__':main()
