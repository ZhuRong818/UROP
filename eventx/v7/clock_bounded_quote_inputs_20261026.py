"""V03: two-clock as-of gates with bounded cross-clock ordering uncertainty.

Raw timestamps are never shifted. This is an engineering tolerance, not a venue SLA.
"""
from bisect import bisect_left,bisect_right
import math
from eventx.v7.source_time_quote_inputs_20261026 import SourceTimeQuoteTape as StrictTape,FEATURES

CONTRACT='source_time_quote14_clock_bound250ms_v3_requires_new_fit'
MAX_SOURCE_LEAD=.250

class SourceTimeQuoteTape(StrictTape):
    def at(self,t):
        k=bisect_right(self.available,t)
        if not k:return None
        latest=self.by_available[k-1]
        # Never use a source clock later than decision time, even within tolerance.
        if latest['timestamp'].timestamp()>t:return None
        if latest['timestamp'].timestamp()-latest['timestamp_received'].timestamp()>MAX_SOURCE_LEAD+1e-9:return None
        i,j=bisect_left(self.sources,t-120),bisect_right(self.sources,t)
        rows=[r for r in self.rows[i:j] if r['timestamp_received'].timestamp()<=t and
              r['timestamp'].timestamp()-r['timestamp_received'].timestamp()<=MAX_SOURCE_LEAD+1e-9]
        if not rows:return None
        source=max(r['timestamp'].timestamp() for r in rows)
        pairs={(None if r['best_bid'] is None else float(r['best_bid']),None if r['best_ask'] is None else float(r['best_ask']))
               for r in rows if r['timestamp'].timestamp()==source}
        if len(pairs)!=1:return None
        bid,ask=next(iter(pairs))
        if bid is None or ask is None or not 0<bid<=ask<1 or ask-bid>.05+1e-12:return None
        return {'midpoint':(bid+ask)/2,'spread':ask-bid}

    def model_record(self,t):
        return {'input_contract':CONTRACT,'feature_names':FEATURES,'features':self.features(t),
                'requires_new_fit':True,'compatible_with_frozen_18_feature_model':False,'compatible_with_v02_model':False}

def clock_health(records,t):
    """Use only the most recent completed probe already available at decision time."""
    probes=[r for r in records if r.get('kind')=='clock_probe' and r['available_epoch']<=t]
    if not probes:return False,['clock_probe_missing']
    p=max(probes,key=lambda r:r['available_epoch'])
    if t-p['available_epoch']>360:return False,['clock_probe_stale']
    good=[r for r in p['measurements'] if r.get('exit_code')==0 and
          r.get('offset_seconds') is not None and r.get('reported_uncertainty_seconds') is not None and
          math.isfinite(r['offset_seconds']) and 0<=r['reported_uncertainty_seconds']<=.1]
    if len({r['host'] for r in good})<2 or not any(r['reported_uncertainty_seconds']<=.02 for r in good):
        return False,['insufficient_precise_independent_clocks']
    low=max(r['offset_seconds']-r['reported_uncertainty_seconds'] for r in good)
    high=min(r['offset_seconds']+r['reported_uncertainty_seconds'] for r in good)
    if low>high:return False,['clock_intervals_disagree']
    if low<-.1 or high>.1:return False,['host_clock_offset_exceeds100ms_budget']
    return True,[]
