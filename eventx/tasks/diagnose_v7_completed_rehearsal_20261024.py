"""Attribute operational gaps using frozen receipts and bounded host power logs."""
from collections import Counter, defaultdict
from datetime import datetime, timezone
import json
from pathlib import Path
import re
import subprocess
from eventx.tasks.discover_v7_direct_pilot_20261022 import REPO_ROOT, now, sha, write, verify_originals

AUDIT=REPO_ROOT/'data/v7/direct_source_pilot_20261022_v03/audits/20261024T060327Z_808a25'
OUT=REPO_ROOT/'data/v7/completed_rehearsal_diagnosis_20261024'

def stamp(s): return datetime.fromisoformat(s.replace('Z','+00:00')).timestamp()
def iso(t): return datetime.fromtimestamp(t,timezone.utc).isoformat()

def main():
    OUT.mkdir(parents=True,exist_ok=False)
    manifest=json.loads((AUDIT/'manifest.json').read_text())
    for path,h in manifest['files'].items():
        if sha(REPO_ROOT/path)!=h: raise RuntimeError('Audit file hash mismatch')
    locks=verify_originals()
    times=[];trades=defaultdict(list);http=Counter();failures=Counter();cycles=[]
    with (AUDIT/'journal.jsonl').open() as f:
        for line in f:
            r=json.loads(line)
            t=r.get('available_at') or r.get('finished_at') or r.get('at')
            if t: times.append(stamp(t))
            if r['kind']=='cycle_finished': cycles.append(r['duration_seconds'])
            if r['kind']=='rest':
                key=(r['source'],r['endpoint_kind'],str(r.get('http_status')),r['status'])
                http[key]+=1
                if r.get('error_type'):failures[r['error_type']]+=1
                if r['source']=='venue' and r['endpoint_kind']=='trades' and r.get('status')=='observed':
                    trades[r['market_id']].append(stamp(r['available_at']))
    times.sort()
    gaps=sorted([{'start':iso(a),'end':iso(b),'seconds':b-a} for a,b in zip(times,times[1:])],key=lambda x:-x['seconds'])[:10]
    market_gaps=[]
    for cid,ts in trades.items():
        ts.sort();a,b=max(zip(ts,ts[1:]),key=lambda p:p[1]-p[0])
        market_gaps.append({'market_id':cid,'start':iso(a),'end':iso(b),'seconds':b-a})
    market_gaps.sort(key=lambda x:-x['seconds'])
    raw=subprocess.run(['pmset','-g','log'],capture_output=True,text=True,check=True).stdout
    power=[]
    pattern=re.compile(r'^(2026-10-2[34] \d\d:\d\d:\d\d [+-]\d{4}) (Sleep|Wake|DarkWake)\s+\t(.*)$')
    for line in raw.splitlines():
        m=pattern.match(line)
        if not m:continue
        t=datetime.strptime(m[1],'%Y-%m-%d %H:%M:%S %z').timestamp()
        if times[0]-3600<=t<=times[-1]+3600:
            power.append({'at':iso(t),'kind':m[2],'detail':m[3].strip()})
    largest=market_gaps[0];a,b=stamp(largest['start']),stamp(largest['end'])
    overlap=[r for r in power if a-300<=stamp(r['at'])<=b+300]
    clamshell=[r for r in overlap if 'Clamshell' in r['detail']]
    awake=[r for r in overlap if r['kind']=='Wake']
    report={'at':now().isoformat(),'original_locks_verified':locks,'audit':str(AUDIT.relative_to(REPO_ROOT)),
        'journal_records':len(times),'largest_all_journal_gaps':gaps,'largest_market_trade_gap':largest,
        'power_records_in_largest_trade_gap':len(overlap),'clamshell_events_in_largest_gap':clamshell,
        'full_wake_events_in_largest_gap':awake,'request_error_types':dict(failures),
        'endpoint_status_counts':[{'source':k[0],'endpoint':k[1],'http':k[2],'status':k[3],'count':v} for k,v in sorted(http.items())],
        'cycle_duration_median_seconds':sorted(cycles)[len(cycles)//2],
        'interpretation':'Power events overlapping receipt gaps support host-sleep contribution; they do not explain every missing provider trade or all residual delay.',
        'operational_requirement':'For release windows keep the local Mac powered, lid open, awake and connected; scheduled caffeinate does not undo recorded lid sleep.',
        'collection_recovery_rule':'A gap >120s invalidates affected decision windows; resume only after a new valid240m warmup. Backfill remains late.',
        'model_scored':False,'predictive_admissions':0}
    write(OUT/'report.json',report);write(OUT/'market_gaps.json',market_gaps);write(OUT/'power_events.json',power)
    files=list(OUT.iterdir())+[Path(__file__).resolve(),AUDIT/'manifest.json']
    write(OUT/'manifest.json',{'files':{str(p.relative_to(REPO_ROOT)):sha(p) for p in files}})
    print(json.dumps(report,indent=2))

if __name__=='__main__':main()
