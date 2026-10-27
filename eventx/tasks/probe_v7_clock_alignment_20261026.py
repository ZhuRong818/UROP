"""Read-only independent clocks and official timestamp specifications; never sets time."""
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from datetime import datetime,timezone
import hashlib,json,re,subprocess,time
import httpx
from eventx.tasks.discover_v7_direct_pilot_20261022 import REPO_ROOT,write,sha,now
BASE=REPO_ROOT/'data/v7/clock_alignment_20261026'

def ntp(host):
 at=now().isoformat();m=time.monotonic();r=subprocess.run(['/usr/bin/sntp','-t','3','-n','1','-d',host],capture_output=True,text=True,timeout=8)
 text=r.stdout+'\n'+r.stderr
 match=re.search(r'([+-]\d+\.\d+)\s+\+/-\s+(\d+\.\d+)\s+',text)
 return {'host':host,'requested_at':at,'available_at':now().isoformat(),'elapsed_monotonic':time.monotonic()-m,'exit_code':r.returncode,
  'offset_seconds':float(match[1]) if match else None,'reported_uncertainty_seconds':float(match[2]) if match else None,'raw':text}

def main():
 BASE.mkdir(parents=True,exist_ok=False)
 write(BASE/'plan.json',{'at':now().isoformat(),'ntp_hosts':['time.google.com','time.cloudflare.com','time.apple.com'],'rounds':3,'clob_http_time_requests':12,
  'scope':'Clock-only public requests; no prices, forecasts or labels; no system clock writes','offset_sign':'remote minus local','http_seconds_quantization':'[server_seconds-local_response,server_seconds+1-local_request], not millisecond clock proof'})
 ntps=[]
 with ThreadPoolExecutor(max_workers=3) as pool:
  for i in range(3):
   ntps.extend(list(pool.map(ntp,['time.google.com','time.cloudflare.com','time.apple.com'])))
   time.sleep(.2)
 write(BASE/'ntp.json',ntps)
 receipts=[]
 with httpx.Client(timeout=20) as c:
  for i in range(12):
   start=time.time();mono=time.monotonic();row={'requested_at':datetime.fromtimestamp(start,timezone.utc).isoformat()}
   try:
    r=c.get('https://clob.polymarket.com/time',headers={'Cache-Control':'no-cache'});end=time.time()
    row.update(status=r.status_code,body=r.text,response_at=datetime.fromtimestamp(end,timezone.utc).isoformat(),rtt=time.monotonic()-mono,
      wall_minus_monotonic_elapsed=(end-start)-(time.monotonic()-mono),headers={k:r.headers.get(k) for k in ['date','age','cf-cache-status','cache-control']})
    if r.status_code==200:
     v=float(r.json());row['seconds_offset_interval']=[v-end,v+1-start]
   except Exception as e:row.update(error=type(e).__name__)
   receipts.append(row);time.sleep(.11)
  for name,url in [('asyncapi.json','https://docs.polymarket.com/asyncapi.json'),('clob-openapi.yaml','https://docs.polymarket.com/api-spec/clob-openapi.yaml')]:
   r=c.get(url);(BASE/name).write_bytes(r.content);write(BASE/(name+'.receipt.json'),{'at':now().isoformat(),'url':url,'http_status':r.status_code,'sha256':sha(BASE/name)})
 write(BASE/'http_time.json',receipts)
 good=[r for r in ntps if r['offset_seconds'] is not None and r['exit_code']==0]
 report={'at':now().isoformat(),'ntp_measurements':len(ntps),'ntp_successful':len(good),'ntp_by_host':{h:[{k:r[k] for k in ['requested_at','offset_seconds','reported_uncertainty_seconds']} for r in good if r['host']==h] for h in ['time.google.com','time.cloudflare.com','time.apple.com']},
  'http_success':sum(r.get('status')==200 for r in receipts),'http_intervals':[r['seconds_offset_interval'] for r in receipts if 'seconds_offset_interval' in r],
  'historical_offset_proven':False,'system_clock_modified':False,'prices_or_labels_read':False}
 write(BASE/'report.json',report);paths=list(BASE.iterdir())+[Path(__file__).resolve()]
 write(BASE/'manifest.json',{'files':{str(p.relative_to(REPO_ROOT)):sha(p) for p in paths}})
 print(json.dumps(report,indent=2))
if __name__=='__main__':main()
