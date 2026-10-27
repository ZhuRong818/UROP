"""Candidate shared measurement contract for a NEW classifier; requires refitting.

No receipt-batch counts, message-age values, book interpolation, or target access.
Availability remains a causal gate; different receivers can still see different data.
"""
from bisect import bisect_right, bisect_left
import math
import numpy as np
from eventx.v7.live_quote_inputs_20261026 import InputCompatibilityError

CONTRACT = 'source_time_quote14_v2_requires_new_fit'
FEATURES = ['midpoint', 'logit_midpoint', 'spread', 'hour_sin', 'hour_cos',
            'delta5', 'abs_delta5', 'missing5', 'delta15', 'abs_delta15', 'missing15',
            'delta30', 'abs_delta30', 'missing30']


class SourceTimeQuoteTape:
    def __init__(self, rows):
        if len({r['market'] for r in rows}) > 1:
            raise InputCompatibilityError('Mixed condition identities')
        # Only directly observed price-change BBOs define this NEW quote process.
        self.rows = sorted([r for r in rows if r['event_type'] == 'price_change'],
                           key=lambda r: (r['timestamp'].timestamp(), r['timestamp_received'].timestamp()))
        self.sources = [r['timestamp'].timestamp() for r in self.rows]
        self.by_available = sorted(self.rows, key=lambda r: r['timestamp_received'].timestamp())
        self.available = [r['timestamp_received'].timestamp() for r in self.by_available]

    def at(self, t):
        k = bisect_right(self.available, t)
        if not k:
            return None
        # A future exchange clock on the latest available event is unsafe.
        if self.by_available[k-1]['timestamp'].timestamp() > t:
            return None
        i, j = bisect_left(self.sources, t-120), bisect_right(self.sources, t)
        available = [r for r in self.rows[i:j]
                     if r['timestamp'].timestamp() <= r['timestamp_received'].timestamp() <= t]
        if not available:
            return None
        latest_source = max(r['timestamp'].timestamp() for r in available)
        rr = [r for r in available if r['timestamp'].timestamp() == latest_source]
        # Collapse repeats by value; conflicting same-source-time quotes are unknown.
        pairs = {(None if r['best_bid'] is None else float(r['best_bid']),
                  None if r['best_ask'] is None else float(r['best_ask'])) for r in rr}
        if len(pairs) != 1:
            return None
        bid, ask = next(iter(pairs))
        if bid is None or ask is None or not 0 < bid <= ask < 1 or ask-bid > .05+1e-12:
            return None
        return {'midpoint': (bid+ask)/2, 'spread': ask-bid}

    def features(self, t):
        if not math.isfinite(t) or t % 300 or not 1800 <= t % 86400 < 84600:
            return None
        current = self.at(t)
        if current is None:
            return None
        mid = current['midpoint'];hour = (t % 86400)/3600
        x = [mid, float(np.log(mid/(1-mid))), current['spread'],
             float(np.sin(2*np.pi*hour/24)), float(np.cos(2*np.pi*hour/24))]
        for lag in [300, 900, 1800]:
            previous = self.at(t-lag)
            delta = mid-previous['midpoint'] if previous else 0.
            x.extend([delta, abs(delta), float(previous is None)])
        assert len(x) == len(FEATURES) and np.isfinite(x).all()
        return x

    def model_record(self, t):
        return {'input_contract': CONTRACT, 'feature_names': FEATURES, 'features': self.features(t),
                'requires_new_fit': True, 'compatible_with_frozen_18_feature_model': False}
