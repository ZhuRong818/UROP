"""Calendar/rule diagnosis only; no trade outcomes or predictive eligibility claims."""
import collections
import json
from datetime import datetime,timedelta,timezone
from eventx.settings import REPO_ROOT
from eventx.tasks.prepare_v7_market_capture_20261018 import BASE,RELEASE,sha,write

def dt(s):return datetime.fromisoformat(s.replace('Z','+00:00'))
def main():
 out=BASE/'target_scope'
 if out.exists():raise RuntimeError('Preserve diagnostic version')
 out.mkdir()
 cp=RELEASE/'cohort.jsonl';sp=REPO_ROOT/'eventx/release/v7/original_source_capture_20261018_v02/schedule.json'
 rs=[json.loads(l) for l in cp.read_text().splitlines()];events=json.loads(sp.read_text())['events']
 rows=[];summary=[]
 for e in events:
  if e['event_id'].startswith('fomc_') or dt(e['scheduled_at'])>=dt('2026-11-12T00:00:00Z'):continue
  counts=collections.Counter()
  for r in rs:
   terminal=dt(r['scheduled_release_at']);clock=dt(e['scheduled_at'])
   if terminal<=clock+timedelta(minutes=30):role='exclude_expected_terminal_before_target_end'
   else:role='calendar_only_candidate_needs_relevance_freshness_and_actual_terminal_verification'
   counts[role]+=1
   rows.append({'event_id':e['event_id'],'scheduled_at':e['scheduled_at'],'market_id':r['market_id'],
    'market_episode':r['episode_id'],'expected_terminal_at':r['scheduled_release_at'],'role':role,
    'predictive_admission':False,'news_relevance_reviewed':False})
  summary.append({'event_id':e['event_id'],'scheduled_at':e['scheduled_at'],'counts':dict(counts)})
 (out/'event_market_scope.jsonl').write_text(''.join(json.dumps(r,sort_keys=True)+'\n' for r in rows))
 report={'at':datetime.now(timezone.utc).isoformat(),'cohort_sha256':sha(cp),'official_schedule_sha256':sha(sp),
  'events':summary,'predictive_admitted_rows':0,
  'interpretation':'Each market settles on its own release. Scheduled end_date can be later; do not use it as evidence of a post-release30min target.',
  'context_limitation':'Earlier other releases may concern a still-open contract, but exact-predicate evidence is absent until reviewed. GDP/PCE are simultaneous, not two independent shocks.',
  'unknowns':['actual release/reschedule and terminal clocks','actual freshness/liquidity','source completeness','material relevance/novelty','event dependence/power'],
  'protected_payloads_or_outcomes_read':False}
 write(out/'report.json',report);write(out/'manifest.json',{'files':{str(p.relative_to(REPO_ROOT)):sha(p) for p in out.iterdir() if p.is_file()}})
 print(json.dumps(report,indent=2))
if __name__=='__main__':main()
