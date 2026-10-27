"""Validate native SNTP selected-packet evidence independently of its exit code."""
import math,re

def selected_packet_check(record):
    raw=record.get('raw','')
    if 'selected:' not in raw:return {'valid':False,'reason':'missing_selected_packet'}
    selected=raw.rsplit('selected:',1)[1]
    h=re.search(r'header:\s*([0-9A-Fa-f]+)',selected)
    s=re.search(r'stratum:.*\((\d+)\)',selected)
    if not h or not s:return {'valid':False,'reason':'missing_header_or_stratum'}
    header=int(h[1],16);stratum=int(s[1])
    if header&7!=4 or header>>6==3 or not 1<=stratum<=15:
        return {'valid':False,'reason':'invalid_server_header_or_stratum'}
    stamps={}
    for k in ['t1','t2','t3','t4']:
        m=re.search(r'^\s*'+k+r':.*\(([-\d.]+)\)',selected,re.M)
        if not m:return {'valid':False,'reason':'missing_four_timestamps'}
        stamps[k]=float(m[1])
    if not all(math.isfinite(v) and v>0 for v in stamps.values()):return {'valid':False,'reason':'invalid_timestamp'}
    if stamps['t4']<stamps['t1'] or stamps['t3']<stamps['t2']:return {'valid':False,'reason':'reversed_clock_exchange'}
    offset=((stamps['t2']-stamps['t1'])+(stamps['t3']-stamps['t4']))/2
    reported=record.get('offset_seconds')
    if reported is None or not math.isfinite(reported) or abs(offset-reported)>2e-6:
        return {'valid':False,'reason':'summary_does_not_match_selected_packet','recomputed_offset_seconds':offset}
    return {'valid':True,'reason':None,'recomputed_offset_seconds':offset,'stratum':stratum}
