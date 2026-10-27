"""Prepare the explicit original-source capture contract before launch."""
from datetime import datetime, timezone
from pathlib import Path
from zoneinfo import ZoneInfo
import hashlib
import json
import plistlib
import sys

ROOT=Path(__file__).resolve().parents[2]
OUT=ROOT/'eventx/release/v7/original_source_capture_20261018_v02'
MODULE='eventx.tasks.collect_v7_original_releases_20261018_v02'
LABEL='com.eventx.original-releases.20261018.v02'

def sha(p):
 with p.open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()
def write(p,x):p.write_text(json.dumps(x,sort_keys=True,indent=2)+'\n')

def main():
 if OUT.exists():raise RuntimeError('Use a new capture version')
 OUT.mkdir(parents=True)
 market=ROOT/'data/v5/market_condition_tuning_20261012'
 manifest=json.loads((market/'manifest.json').read_text())
 for a in manifest['artifacts']:
  if sha(ROOT/a['path'])!=a['sha256']:raise RuntimeError('Market artifact hash changed')
 model=market/'selected_model.joblib'
 sources=[
  {'source_id':'fed_monetary','url':'https://www.federalreserve.gov/feeds/press_monetary.xml','kind':'feed','interval_seconds':60},
  {'source_id':'fed_speeches','url':'https://www.federalreserve.gov/feeds/speeches_and_testimony.xml','kind':'feed','interval_seconds':60},
  {'source_id':'bea_news','url':'https://apps.bea.gov/rss/rss.xml','kind':'feed','interval_seconds':60},
  {'source_id':'bea_schedule','url':'https://www.bea.gov/news/schedule','kind':'calendar','interval_seconds':86400},
 ]
 for name,date,period,title in [('cpi','10142026','SEPTEMBER 2026','CONSUMER PRICE INDEX'),('ppi','10152026','SEPTEMBER 2026','PRODUCER PRICE'),('empsit','10022026','SEPTEMBER 2026','EMPLOYMENT SITUATION')]:
  sources.append({'source_id':'dol_baseline_'+name,'url':f'https://www.dol.gov/newsroom/economicdata/{name}_{date}.pdf','kind':'pdf','interval_seconds':86400,'published_at':f'2026-10-{date[2:4]}T12:30:00+00:00','identity_terms':[title,period]})
 # Preserve blocked BLS diagnostics without hammering a denied endpoint.
 for name in ['cpi','ppi','empsit']:
  sources.append({'source_id':'bls_'+name,'url':f'https://www.bls.gov/news.release/{name}.nr0.htm','kind':'document','interval_seconds':21600})
 bea='https://www.bea.gov/news/schedule';bls='https://www.bls.gov/schedule/2026/';fed='https://www.federalreserve.gov/monetarypolicy/fomccalendars.htm'
 events=[]
 def add(eid,date,hour,title,document,feeds,reference):
  at=datetime.fromisoformat(date+'T'+hour).replace(tzinfo=ZoneInfo('America/New_York')).astimezone(timezone.utc)
  events.append({'event_id':eid,'scheduled_at':at.isoformat(),'name':title,'document':document,'feed_ids':feeds,'calendar_source':reference,
    'clock_limitation':'Announced schedule/standard release time, not authenticated actual first publication; changes require schedule revision.'})
 for name,dates in [('empsit',['2026-11-06','2026-12-04']),('cpi',['2026-11-10','2026-12-10']),('ppi',['2026-11-13','2026-12-15'])]:
  for date in dates:
   day=datetime.fromisoformat(date);month='OCTOBER' if day.month==11 else 'NOVEMBER'
   title={'cpi':'CONSUMER PRICE INDEX','ppi':'PRODUCER PRICE','empsit':'EMPLOYMENT SITUATION'}[name]
   add(name+'_'+date,date,'08:30',title,{'url':f'https://www.dol.gov/newsroom/economicdata/{name}_{day:%m%d%Y}.pdf','kind':'pdf','identity_terms':[title,month+' 2026'],'url_status':'future naming hypothesis based on official recent copies; HTTP/content identity must be checked'},[],bls+f'{day.month:02}_sched.htm')
 for date,period in [('2026-10-29','september'),('2026-11-25','october'),('2026-12-23','november')]:
  add('pce_'+date,date,'08:30','Personal Income and Outlays',{'url':f'https://www.bea.gov/news/2026/personal-income-and-outlays-{period}-2026','kind':'document','identity_terms':['Personal Income and Outlays',period,'2026'],'url_status':'future naming hypothesis; RSS discovery provides observed URLs'},['bea_news'],bea)
 for date in ['2026-10-28','2026-12-09']:
  day=datetime.fromisoformat(date)
  add('fomc_'+date,date,'14:00','FOMC statement',{'url':f'https://www.federalreserve.gov/newsevents/pressreleases/monetary{day:%Y%m%d}a.htm','kind':'document','identity_terms':['Federal','2026'],'url_status':'future naming hypothesis; official feed provides observed URLs'},['fed_monetary','fed_speeches'],fed)
 # BEA GDP release dates share PCE windows. Fetch observed links from the full feed;
 # do not invent a GDP article slug or count simultaneous releases as independent.
 for date,stage in [('2026-10-29','advance'),('2026-11-25','second'),('2026-12-23','third')]:
  add('gdp_'+date,date,'08:30','GDP '+stage+' estimate',{'url':'https://apps.bea.gov/rss/rss.xml','kind':'feed'},['bea_news'],bea)
 events.sort(key=lambda x:(x['scheduled_at'],x['event_id']))
 write(OUT/'schedule.json',{'verified_on':'2026-10-18','timezone':'America/New_York with DST conversion','events':events,'independent_events_claimed':False,'changes':'Daily BEA calendar snapshots retained; BLS calendars verified via web because direct access403. Review reschedules; initial plan is not a guarantee.'})
 contract={'capture_id':'eventx-v7-original-release-source-pilot-20261018-v2','authorization':'User instruction 18 October to capture original releases promptly across more event dates, keeping market model fixed.',
  'scope':'Original-source feasibility and first-observation version capture; not V4, v2, model selection, forecast evaluation or confirmation freeze.',
  'version_note':'V1 prepared but never launched. V2 restores pending feed discoveries from journal on restart and permits bounded allowlisted official redirects/bare bea.gov.',
  'source_change':'Explicit new BLS/DOL, BEA and Federal Reserve source branch. Does not substitute into any Lumid dataset or frozen study.',
  'stop_at':'2027-01-01T00:00:00+00:00','sources':sources,
  'allowed_hosts':['www.bls.gov','www.dol.gov','www.bea.gov','bea.gov','apps.bea.gov','www.federalreserve.gov','federalreserve.gov'],
  'max_payload_bytes':12_000_000,'cadence':'Fed/BEA RSS60s; scheduled release15s for first15m, then60s through1h, hourly through24h. Feed burst15s from2m before to15m after release. Failed requests exponential backoff,401/403>=6h, Retry-After respected.',
  'availability':'available_at is local UTC after response body is durably stored; publisher time/scheduled time is separate. No backdating. Hashes identify HTTP entity payloads after transport decompression, not wire packets.',
  'versions':'Content-addressed raw source bodies, separate extracted text; each changed document links prior payload hash; request/observation journal is append-only SHA256 chained.',
  'first_version':'First observed locally, not certified first public release. Late starts, earlier releases, calendar changes and outages remain flagged.',
  'feed_scope':'All items in the three declared RSS feeds, no topic filtering; official host allowlist. Per-cycle document backlog cap24; queued items retained/reconstructed. RSS truncation and gaps do not establish full coverage.',
  'market_model':{'name':'condition_120k','path':str(model.relative_to(ROOT)),'sha256':sha(model),'retraining':False,'calibration_changed':False,'scoring_performed':False},
  'protected_separation':'No prediction-market endpoints, V4 sealed payload, labels, predictions or holdout consumption. All collected source data are pilot-only; no independent confirmation eligibility implied.',
  'timeliness_target_seconds':60,'timeliness_target_is_guarantee':False,'computer_dependency':'Local user background service; network and awake machine required. No recovery can recreate missed first versions.',
  'failed_partition':'unknown; never zero news; denial receipts retained',
  'next_gate':'After first new releases, count receipt latency, actual versions and distinct release dates. Select nonoverlapping market cohort and freeze feature/inference design separately before later forecast evaluation.'}
 write(OUT/'capture_contract.json',contract)
 plist={'Label':LABEL,'ProgramArguments':['/usr/bin/caffeinate','-i',str(ROOT/'.venv/bin/python'),'-m',MODULE],
  'WorkingDirectory':str(ROOT),'RunAtLoad':True,'KeepAlive':{'SuccessfulExit':False},'ThrottleInterval':60,
  'StandardOutPath':str(ROOT/'data/v7/official_source_capture_20261018/service.stdout.log'),
  'StandardErrorPath':str(ROOT/'data/v7/official_source_capture_20261018/service.stderr.log')}
 with (OUT/(LABEL+'.plist')).open('wb') as f:plistlib.dump(plist,f)
 files=[OUT/'capture_contract.json',OUT/'schedule.json',ROOT/'eventx/tasks/collect_v7_original_releases_20261018_v02.py',Path(__file__),
  ROOT/'eventx/tasks/launch_v7_original_capture_20261018_v02.py',ROOT/'.venv/bin/python',model,market/'selection_receipt.json',market/'manifest.json',OUT/(LABEL+'.plist')]
 write(OUT/'implementation_manifest.json',{'created_at':datetime.now(timezone.utc).isoformat(),'scope':'capture implementation lock, not a forecasting preregistration','locked_files':{str(p.relative_to(ROOT)):sha(p) for p in files}})
 print(json.dumps({'contract':str(OUT),'scheduled_events':len(events),'dates':len({e['scheduled_at'][:10] for e in events}),'model_sha256':sha(model)},indent=2))
if __name__=='__main__':main()
