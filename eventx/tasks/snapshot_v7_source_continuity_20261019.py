"""Record current process checkpoints and journal receipt gaps without changing jobs."""
from datetime import datetime,timezone
import json
from pathlib import Path
from eventx.settings import REPO_ROOT
from eventx.tasks.discover_v7_source_control_20261018 import BASE,sha,write

def dt(s):return datetime.fromisoformat(s.replace('Z','+00:00'))
def main():
 at=datetime.now(timezone.utc);out=BASE/'continuity'/at.strftime('%Y%m%dT%H%M%SZ');out.mkdir(parents=True)
 results={}
 for name,rel in [('original_source','data/v7/official_source_capture_20261018/live'),('market','data/v7/market_cohort_capture_20261018/live')]:
  live=REPO_ROOT/rel;body=(live/'journal.jsonl').read_bytes()
  if body and not body.endswith(b'\n'):body=body[:body.rfind(b'\n')+1]
  jp=out/(name+'_journal.jsonl');jp.write_bytes(body)
  sp=out/(name+'_status.json');sp.write_bytes((live/'status.json').read_bytes());status=json.loads(sp.read_text())
  rows=[json.loads(l) for l in body.splitlines() if l]
  times=[]
  for r in rows:
   t=next((r[k] for k in ['recorded_at','finished_at','at','available_at'] if r.get(k)),None)
   if t:times.append(dt(t))
  gaps=sorted([{'from':a.isoformat(),'to':b.isoformat(),'seconds':(b-a).total_seconds()} for a,b in zip(times,times[1:]) if b>=a],key=lambda r:r['seconds'],reverse=True)
  results[name]={'journal_records':len(rows),'status_at':status['at'],'pid':status['pid'],
   'heartbeat_age_seconds':(at-dt(status['at'])).total_seconds(),'largest_receipt_gaps':gaps[:3],
   'journal_snapshot_sha256':sha(jp),'status_snapshot_sha256':sha(sp)}
 report={'at':at.isoformat(),'sources':results,
  'interpretation':'Gaps between journaled local observations do not prove host sleep or any particular cause. No continuous coverage/first-arrival clock is certified during the gap; late retrieval cannot backdate availability.',
  'production_services_modified':False,'labels_or_predictions_computed':False}
 write(out/'report.json',report)
 previous=REPO_ROOT/'EVENTX_SOURCE_VERIFICATION_20261018.md'
 delivery=REPO_ROOT/'EVENTX_SOURCE_VERIFICATION_20261018_REV2.md'
 if delivery.exists():raise RuntimeError('Preserve report version')
 extra='\n'.join(f"- {k}: PID{v['pid']}, heartbeat `{v['status_at']}`; largest journal observation gap **{v['largest_receipt_gaps'][0]['seconds']}seconds**, `{v['largest_receipt_gaps'][0]['from']}` to `{v['largest_receipt_gaps'][0]['to']}`." for k,v in results.items())
 delivery.write_text(previous.read_text()+f'''
## Revision2:19October continuity check

Actual status check **{at.isoformat()}**. Both original processes are present and current checkpoints are fresh; the finite18October source-comparison results above remain unchanged.

{extra}

The cause of the observation gaps is unverified. Fresh current heartbeats do not certify uninterrupted overnight collection. During these intervals, no timely observation is established; later backfills retain their later local availability clocks. A complete240-minute prospectively observed history cannot be assumed across such a gap. Both jobs were preserved and not restarted or modified by this diagnosis.

This continuity limitation is additional to the measured quote/trade API coverage gaps. It reinforces the decision to keep model development and predictive admission gated. The dated source-comparison findings are not described as continuous coverage of18–19October.

[Continuity evidence](data/v7/source_verification_20261018/continuity/{out.name}/report.json). Revision1 remains unchanged.
''')
 write(out/'manifest.json',{'files':{str(p.relative_to(REPO_ROOT)):sha(p) for p in list(out.iterdir())+[delivery] if p.is_file()}})
 print(json.dumps({'directory':str(out.relative_to(REPO_ROOT)),'report':report},indent=2))
if __name__=='__main__':main()
