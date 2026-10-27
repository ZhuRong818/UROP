"""Pure-Python SNTP probe with raw packet retention (replaces macOS /usr/bin/sntp parsing).

The 26 October V01 rehearsal showed /usr/bin/sntp emitting all-zero "selected" packets
while still printing a summary offset. Here every offset is recomputed from the raw
48-byte server reply and the local transmit/receive wall clocks, so validation needs
no CLI text parsing.
"""
import os
import socket
import struct
import time

NTP_EPOCH = 2208988800
HOSTS = ['time.google.com', 'time.cloudflare.com', 'time.apple.com']


def _ts(raw):
    sec, frac = struct.unpack('!II', raw)
    return sec - NTP_EPOCH + frac / 2**32


def probe(host, timeout=3.0):
    """Return a self-contained receipt; offset = server minus local (seconds)."""
    nonce = os.urandom(8)
    request = bytes([0x23]) + bytes(39) + nonce  # LI=0, VN=4, mode=3; transmit field = nonce
    rec = {'host': host, 'request_hex': request.hex()}
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
            s.settimeout(timeout)
            addr = socket.getaddrinfo(host, 123, socket.AF_INET, socket.SOCK_DGRAM)[0][4]
            t1, m1 = time.time(), time.monotonic()
            s.sendto(request, addr)
            data, _ = s.recvfrom(512)
            t4, m4 = time.time(), time.monotonic()
        rec.update(addr=addr[0], response_hex=data.hex(), t1=t1, t4=t4, monotonic_elapsed=m4 - m1)
    except OSError as e:
        rec.update(error=type(e).__name__)
    return {**rec, **validate(rec)}


def validate(rec):
    """Recompute everything from the retained bytes and local clocks."""
    if 'response_hex' not in rec:
        return {'valid': False, 'reason': 'no_response'}
    data = bytes.fromhex(rec['response_hex'])
    if len(data) < 48:
        return {'valid': False, 'reason': 'short_packet'}
    li, vn, mode, stratum = data[0] >> 6, (data[0] >> 3) & 7, data[0] & 7, data[1]
    if mode != 4 or li == 3 or not 1 <= stratum <= 15 or vn not in (3, 4):
        return {'valid': False, 'reason': 'invalid_header_or_stratum'}
    if data[24:32] != bytes.fromhex(rec['request_hex'])[40:48]:
        return {'valid': False, 'reason': 'originate_mismatch'}
    t2, t3 = _ts(data[32:40]), _ts(data[40:48])
    t1, t4 = rec['t1'], rec['t4']
    if min(t2, t3) <= 0 or t3 < t2 or t4 < t1:
        return {'valid': False, 'reason': 'invalid_timestamps'}
    # Wall elapsed must agree with monotonic elapsed, else a local step hit the exchange.
    if abs((t4 - t1) - rec['monotonic_elapsed']) > .005:
        return {'valid': False, 'reason': 'local_step_during_exchange'}
    delay = (t4 - t1) - (t3 - t2)
    if delay < 0 or delay > .2:
        return {'valid': False, 'reason': 'delay_out_of_range'}
    offset = ((t2 - t1) + (t3 - t4)) / 2
    return {'valid': True, 'reason': None, 'stratum': stratum, 'offset_seconds': offset,
            'half_delay_seconds': delay / 2}


def estimate(measurements):
    """Intersect valid [offset - delay/2, offset + delay/2] intervals (true-offset bounds).

    Requires two distinct hosts, one with half-delay <= 20 ms, agreeing intervals, and a
    residual half-width <= 50 ms. Returns (offset, half_width, reasons).
    """
    good = [m for m in measurements if m.get('valid') and m['half_delay_seconds'] <= .1]
    if len({m['host'] for m in good}) < 2 or not any(m['half_delay_seconds'] <= .02 for m in good):
        return None, None, ['insufficient_precise_independent_clocks']
    low = max(m['offset_seconds'] - m['half_delay_seconds'] for m in good)
    high = min(m['offset_seconds'] + m['half_delay_seconds'] for m in good)
    if low > high:
        return None, None, ['clock_intervals_disagree']
    offset, half = (low + high) / 2, (high - low) / 2
    if half > .05:
        return None, None, ['offset_uncertainty_exceeds50ms']
    if abs(offset) > 2:
        return None, None, ['host_offset_implausible']
    return offset, half, []
