"""Show usable cached forecast references only while the heartbeat/grid are fresh."""
import json
from eventx.tasks.run_v7_memory_shadow_20261024 import OUT
from eventx.tasks.discover_v7_direct_pilot_20261022 import now
from eventx.v7.quote_experiment_20261024 import stamp

def main():
    status=json.loads((OUT/'status.json').read_text());data=json.loads((OUT/'latest_forecasts.json').read_text());at=now().timestamp()
    fresh=status['phase']=='running' and 0<=at-stamp(status['at'])<=30
    result={'checked_at':now().isoformat(),'service_fresh':fresh,'counts':{k:status[k] for k in ['timely_forecasts','abstentions','missed','outcomes_observed','outcomes_unavailable']},'forecasts':[]}
    for cid,r in data['forecasts'].items():
        available=fresh and at<stamp(r['display_expires_at']) and r['status']=='forecast_recorded'
        result['forecasts'].append({'market_id':cid,**r,'currently_displayable':available,
            'reference_midpoint_30m':r['reference_midpoint_30m'] if available else None,
            'candidate_midpoints_30m':r['candidate_midpoints_30m'] if available else {},
            'display_note':'Research persistence reference; no demonstrated predictive edge' if available else 'No current forecast; inspect status/reasons and wait for a future valid grid'})
    print(json.dumps(result,indent=2))

if __name__=='__main__':main()
