"""Label-free input bridge. Numerical parity does not certify feed equivalence."""
from bisect import bisect_right
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation, ROUND_DOWN
import math
import numpy as np
from eventx.tasks.evaluate_v7_observational_quotes_20261025 import states_from
from eventx.tasks.research_v7_change_probability_20261025 import FEATURES

ARCHIVE_CONTRACT = 'pmxt_archive_receipt_groups_18_v1'
LIVE_CONTRACT = 'venue_ws_durable_receipt_groups_18_candidate_v1'


class InputCompatibilityError(ValueError):
    pass


def require_frozen_model_inputs(contract):
    if contract != ARCHIVE_CONTRACT:
        raise InputCompatibilityError('Live clock/grouping/dedup equivalence is unverified; frozen-model activation blocked')


def decimal4(value):
    """Match exporter Decimal(4) projection; invalid/missing values become invalid zero quotes."""
    try:
        d = Decimal(str(value))
        return d.quantize(Decimal('.0001'), rounding=ROUND_DOWN) if d.is_finite() else Decimal(0)
    except (InvalidOperation, ValueError):
        return Decimal(0)


def project_ws(payload, available_at, received_at, samples):
    """Project only observed fields. No book reconstruction, polling, or clock backdating.

    Return archive-shaped rows but tag them LIVE_CONTRACT: projection is not clock parity.
    All subscription asset IDs must be known, even when NO legs are filtered out.
    """
    available = datetime.fromisoformat(available_at.replace('Z', '+00:00'))
    received = datetime.fromisoformat(received_at.replace('Z', '+00:00'))
    if available.tzinfo is None or received.tzinfo is None or available < received:
        raise InputCompatibilityError('Invalid durable availability clock')
    # Round availability upward to milliseconds, never making a row available early.
    micros = round(available.timestamp() * 1_000_000)
    clock = datetime.fromtimestamp(((micros + 999) // 1000) / 1000, timezone.utc)
    assets = {}
    for s in samples:
        assets[s['yes_asset_id']] = (s['market_id'], True)
        assets[s['no_asset_id']] = (s['market_id'], False)
    output = []
    for msg in payload if isinstance(payload, list) else [payload]:
        if not isinstance(msg, dict):
            raise InputCompatibilityError('Unexpected event schema')
        kind = msg.get('event_type')
        if kind not in {'price_change', 'book', 'last_trade_price', 'tick_size_change'}:
            raise InputCompatibilityError('Unknown event type; review source version')
        try:
            source_ms = int(msg['timestamp'])
            source = datetime.fromtimestamp(source_ms / 1000, timezone.utc)
        except (KeyError, ValueError, TypeError, OverflowError):
            raise InputCompatibilityError('Missing or invalid exchange timestamp')
        if source_ms < 0:
            raise InputCompatibilityError('Negative exchange timestamp')
        legs = msg.get('price_changes') if kind == 'price_change' else [msg]
        if not isinstance(legs, list):
            raise InputCompatibilityError('Missing price-change entries')
        for leg in legs:
            token = str(leg.get('asset_id'))
            if token not in assets or msg.get('market') != assets[token][0]:
                raise InputCompatibilityError('Unknown token or condition mismatch')
            cid, yes = assets[token]
            if not yes:
                continue
            output.append({'market': cid.encode(), 'asset_id': token, 'event_type': kind,
                           'timestamp': source, 'timestamp_received': clock,
                           'best_bid': decimal4(leg.get('best_bid')) if kind == 'price_change' else None,
                           'best_ask': decimal4(leg.get('best_ask')) if kind == 'price_change' else None,
                           '_input_contract': LIVE_CONTRACT})
    return output


class FeatureTape:
    """Single-condition as-of features; days reset exactly as in the frozen builder."""
    def __init__(self, rows, covered_hours=None):
        if len({r['market'] for r in rows}) > 1:
            raise InputCompatibilityError('A feature tape must contain exactly one condition')
        contracts = {r.get('_input_contract', ARCHIVE_CONTRACT) for r in rows}
        if len(contracts) > 1:
            raise InputCompatibilityError('Cannot mix archive and live input contracts')
        self.contract = next(iter(contracts), ARCHIVE_CONTRACT)
        self.states = states_from(rows)
        self.times = [s['at'] for s in self.states]
        self.covered_hours = covered_hours

    def at(self, t, day_start):
        if t < day_start:
            return None
        if self.covered_hours is not None:
            hour = datetime.fromtimestamp(t, timezone.utc).strftime('%Y-%m-%dT%H')
            if hour not in self.covered_hours:
                return None
        i = bisect_right(self.times, t) - 1
        if i < 0:
            return None
        s = self.states[i]
        return s if s['at'] >= day_start and s['valid'] and 0 <= t-s['at'] <= 120 and 0 <= t-s['source'] <= 120 else None

    def features(self, t):
        if not math.isfinite(t):
            raise InputCompatibilityError('Nonfinite decision time')
        day = math.floor(t / 86400) * 86400
        current = self.at(t, day)
        if current is None:
            return None
        mid = current['midpoint']
        hour = (t % 86400) / 3600
        i = bisect_right(self.times, max(t-1800, day-1e-6))
        j = bisect_right(self.times, t)
        valid = sum(s['valid'] for s in self.states[i:j])
        f = [mid, float(np.log(mid/(1-mid))), current['spread'], t-current['source'], t-current['at'],
             np.sin(2*np.pi*hour/24), np.cos(2*np.pi*hour/24), np.log1p(valid), valid/max(1, j-i)]
        for lag in [300, 900, 1800]:
            previous = self.at(t-lag, day)
            delta = mid-previous['midpoint'] if previous else 0.
            f.extend([delta, abs(delta), float(previous is None)])
        assert len(f) == len(FEATURES) and np.isfinite(f).all()
        return list(map(float, f))

    def model_inputs(self, t):
        require_frozen_model_inputs(self.contract)
        if t % 300 or not 1800 <= t % 86400 < 84600:
            raise InputCompatibilityError('Outside frozen five-minute daily decision grid')
        return self.features(t)


def transport_ready(records, t):
    """Additional live readiness guard; not a replacement for the historical features.

    Require a connected stream, a recent application pong, and 30 minutes since
    the latest connect or operational interruption. Inspect records only as of t.
    This detects known disruptions; it cannot prove complete exchange delivery.
    """
    connected = False
    start = None
    pong = None
    for r in records:
        clock = r.get('available_at') or r.get('at')
        if not clock:
            continue
        at = datetime.fromisoformat(clock.replace('Z', '+00:00')).timestamp()
        if at > t:
            continue
        kind = r['kind']
        if kind == 'ws_connected':
            connected, start, pong = True, at, None
        elif kind in {'ws_disconnected', 'process_stopped', 'scope_rejected_stop'} or (kind == 'stream_stopped' and r.get('stream') == 'venue_ws'):
            connected = False
            start = None
        elif kind == 'operational_cycle_gap':
            start = at
        elif kind == 'ws_pong':
            if pong is not None and at-pong > 35:
                start = at
            pong = at
    reasons = []
    if not connected:
        reasons.append('stream_disconnected')
    if pong is None or t-pong > 35:
        reasons.append('pong_missing_or_old')
    if start is None or t-start < 1800:
        reasons.append('transport_history_warming')
    return not reasons, reasons
