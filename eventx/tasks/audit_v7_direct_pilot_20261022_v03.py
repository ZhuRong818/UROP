"""Freeze a source-only audit of completed or running rehearsal receipts."""
import argparse
from collections import Counter, defaultdict
from datetime import datetime, timezone
from decimal import Decimal
import hashlib
import json
import uuid
from pathlib import Path
from eventx.settings import REPO_ROOT
from eventx.tasks.discover_v7_direct_pilot_20261022 import now, sha, write, verify_originals
BASE = REPO_ROOT/"data/v7/direct_source_pilot_20261022_v03"
RELEASE = REPO_ROOT/"eventx/release/v7/direct_source_pilot_20261022_v03"

def stamp(x):
    if isinstance(x, (int, float)) or str(x).replace('.', '', 1).isdigit():
        v = float(x)
        return v/1000 if v > 1e11 else v
    return datetime.fromisoformat(x.replace('Z', '+00:00')).timestamp()

def fingerprint(r):
    return (str(r.get('token_id', r.get('asset'))), int(stamp(r.get('ts', r.get('timestamp')))),
            str(Decimal(str(r['price'])).normalize()), str(Decimal(str(r['size'])).normalize()), r['side'].upper())

def audit(run):
    for rel, h in json.loads((RELEASE/'implementation_manifest.json').read_text())['locked_files'].items():
        if sha(REPO_ROOT/rel) != h:
            raise RuntimeError('V03 implementation mismatch: '+rel)
    run = run.resolve()
    if not run.is_relative_to(BASE.resolve()):
        raise ValueError('Audit only this source-pilot root')
    out = BASE/'audits'/(now().strftime('%Y%m%dT%H%M%SZ')+'_'+uuid.uuid4().hex[:6])
    out.mkdir(parents=True)
    body = (run/'journal.jsonl').read_bytes()
    body = body[:body.rfind(b'\n')+1]
    (out/'journal.jsonl').write_bytes(body)
    (out/'status.json').write_bytes((run/'status.json').read_bytes())
    (out/'run_contract.json').write_bytes((run/'run_contract.json').read_bytes())
    at = now()
    records = [json.loads(l) for l in body.splitlines() if l]
    head = None
    payload_hashes = set()
    for r in records:
        v = dict(r)
        h = v.pop('record_sha256')
        if v['previous_sha256'] != head or hashlib.sha256(json.dumps(v, sort_keys=True, separators=(',', ':')).encode()).hexdigest() != h:
            raise RuntimeError('Journal chain mismatch')
        head = h
        if r.get('payload_sha256'):
            payload_hashes.add(r['payload_sha256'])
    for h in payload_hashes:
        if sha(run/'objects'/h) != h:
            raise RuntimeError('Payload mismatch')
    def payload(r):
        return json.loads((run/'objects'/r['payload_sha256']).read_text())
    samples = [json.loads(l) for l in (RELEASE/'sample.jsonl').read_text().splitlines()]
    rest = [r for r in records if r['kind']=='rest']
    index = defaultdict(list)
    for r in rest:
        index[r['market_id'], r['cycle'], r['source'], r['endpoint_kind']].append(r)
    summaries = {(r['market_id'], r['cycle'], r['source']): r for r in records if r['kind']=='window_summary'}
    comparisons = []
    for s in samples:
        cid = s['market_id']
        cycles = sorted({r['cycle'] for r in rest if r['market_id']==cid})
        for cycle in cycles:
            a = index[cid, cycle, 'venue', 'trades']
            b = index[cid, cycle, 'lumid', 'trades']
            if not b:
                continue
            c = {'market_id': cid, 'question': s['question'], 'role': s['diagnostic_role'],
                 'family': s.get('family'), 'cycle': cycle, 'status': 'unresolved_paging_or_request',
                 'predictive_eligible': False}
            if len(a)==len(b)==1 and all(r.get('status')=='observed' for r in a+b) and all(
                summaries.get((cid,cycle,source),{}).get('endpoint_window_returned') for source in ['venue','lumid']):
                aw = summaries[cid,cycle,'venue']
                ar = [x for x in payload(a[0])['data'] if aw['start'] <= int(x['timestamp']) <= aw['end']]
                br = payload(b[0])
                ac, bc = Counter(map(fingerprint, ar)), Counter(map(fingerprint, br))
                end = aw['end']
                yes = [x for x in ar if str(x.get('token_id'))==s['yes_asset_id']]
                yes60 = [x for x in yes if end-3600 <= stamp(x['timestamp']) <= end]
                yes240 = [x for x in yes if end-14400 <= stamp(x['timestamp']) <= end]
                latest = max((stamp(x['timestamp']) for x in yes), default=None)
                age = (end-latest)/60 if latest is not None else None
                notional = sum(float(x['price'])*float(x['size']) for x in yes240)
                size240 = sum(float(x['size']) for x in yes240)
                c.update(status='comparable_single_page_window', window_from=aw['start'], window_to=end,
                         venue_print_rows=len(ar), lumid_print_rows=len(br), matching_fingerprints=sum((ac&bc).values()),
                         venue_only_fingerprints=sum((ac-bc).values()), lumid_only_fingerprints=sum((bc-ac).values()),
                         venue_yes_rows=len(yes), venue_yes60=len(yes60), venue_yes240=len(yes240),
                         latest_yes_age_minutes=age, observed_cash_value240=notional, observed_token_size240=size240,
                         historical_model_size_semantics='sum token size, not cash',
                         cash_diagnostic_activity_screen=age is not None and 0<=age<=5 and len(yes60)>=3 and len(yes240)>=3 and notional>=100,
                         observed_activity_screen=age is not None and 0<=age<=5 and len(yes60)>=3 and len(yes240)>=3 and size240>=100)
            books = index[cid,cycle,'venue','book_yes_asset_id']
            quotes = index[cid,cycle,'lumid','quotes']
            meta = index[cid,cycle,'venue','market_metadata']
            if books and books[-1].get('status')=='observed':
                bk = payload(books[-1])
                bids, asks = bk.get('bids', []), bk.get('asks', [])
                c.update(bid_levels=len(bids), ask_levels=len(asks), book_two_sided=bool(bids and asks))
                if bids and asks:
                    bid, ask = max(float(x['price']) for x in bids), min(float(x['price']) for x in asks)
                    c['book_uncrossed'] = bid <= ask
                else:
                    c['book_uncrossed'] = False
                if bk.get('timestamp'):
                    c['book_age_seconds'] = stamp(books[-1]['response_received_at'])-stamp(bk['timestamp'])
            if quotes and quotes[-1].get('status')=='observed':
                c['lumid_quote_rows'] = len(payload(quotes[-1]))
            if meta and meta[-1].get('status')=='observed':
                mv = payload(meta[-1])
                if isinstance(mv,list) and len(mv)==1:
                    m = mv[0]
                    outcomes = m.get('outcomes', [])
                    tokens = m.get('clobTokenIds', [])
                    if isinstance(outcomes,str): outcomes=json.loads(outcomes)
                    if isinstance(tokens,str): tokens=json.loads(tokens)
                    c['current_mapping_matches'] = m.get('conditionId')==cid and outcomes==['Yes','No'] and tokens==[s['yes_asset_id'],s['no_asset_id']]
                    c['current_accepting_orders'] = m.get('acceptingOrders')
                    c['current_closed'] = m.get('closed')
                    c['current_rules_equal_metadata'] = m.get('description')==s.get('rules')
            resolution = index[cid,cycle,'venue','resolution_state']
            if resolution and resolution[-1].get('status')=='observed':
                rv=payload(resolution[-1]).get('data',[])
                c['resolution_rows']=len(rv)
                c['resolution_statuses']=[x.get('status') for x in rv]
                c['terminal_status_certified']=False
            c['activity_control_screen'] = s['diagnostic_role']=='activity_control_candidate' and c.get('venue_yes60',0)>=3 and c.get('book_two_sided',False) and c.get('book_uncrossed',False) and 0<=c.get('book_age_seconds',1e99)<=300
            comparisons.append(c)
    ws, sse = Counter(), Counter()
    for r in records:
        if r['kind']=='ws_frame':
            v = payload(r)
            ws.update(x.get('event_type','unknown') for x in (v if isinstance(v,list) else [v]))
        elif r['kind']=='sse_frame':
            txt = (run/'objects'/r['payload_sha256']).read_text()
            sse.update([next((x[6:].strip() for x in txt.splitlines() if x.startswith('event:')), 'unspecified')])
    gaps = []
    for s in samples:
        times = sorted(stamp(r['available_at']) for r in rest if r['market_id']==s['market_id'] and r['source']=='venue' and r['endpoint_kind']=='trades' and r.get('status')=='observed')
        gaps.append({'market_id':s['market_id'], 'successful_trade_receipts':len(times),
                     'max_between_receipts_seconds':max((b-a for a,b in zip(times,times[1:])),default=None),
                     'latest_receipt_age_seconds':at.timestamp()-times[-1] if times else None})
    contract = json.loads((out/'run_contract.json').read_text())
    source_status = json.loads((REPO_ROOT/'data/v7/official_source_capture_20261018/live/status.json').read_text())
    report = {'created_at':at.isoformat(),'run':str(run.relative_to(REPO_ROOT)),
              'journal_records':len(records),'journal_head_sha256':head,'verified_payloads':len(payload_hashes),
              'production_locks_verified':verify_originals(),'rest_http_counts':dict(Counter(str(r.get('http_status')) for r in rest)),
              'rest_status_counts':dict(Counter(r.get('status') for r in rest)),
              'websocket_event_types':dict(ws),'sse_event_types':dict(sse),
              'stream_disconnects':dict(Counter(r['kind'] for r in records if r['kind'] in ['ws_disconnected','sse_disconnected'])),
              'elapsed_wall_seconds':at.timestamp()-stamp(contract['started_at']),
              'scheduled_stop_at':contract['stop_at'],'smoke_seconds':contract['smoke_seconds'],
              'window_deadline_reached':at.timestamp()>=stamp(contract['stop_at']),
              'capture_continuity_certified':False,'source_completeness_certified':False,
              'comparisons':len(comparisons),'markets':len(samples),
              'macro_candidates':sum(s['diagnostic_role']=='prospective_macro_candidate' for s in samples),
              'candidate_activity_screen_passes_first_cycle':sum(c.get('observed_activity_screen',False) for c in comparisons if c['role']=='prospective_macro_candidate' and c['cycle']==1),
              'original_source_checkpoint':{'at':source_status['at'],'document_versions':source_status['document_versions']},
              'predictive_admissions':0,'models_scored':False,'labels_computed':False,
              'first_observation_blockers':['future reserved release has not occurred','source coverage not established','as-of240m warmup not established by this audit','forward policy pending source rehearsal','actual event/terminal/evidence gates pending'],
              'interpretation':'Bounded source evidence only; fingerprints are print records not unique executions. Current metadata is not historical terminal proof. Activity pass alone is not prediction eligibility.'}
    (out/'market_comparison.jsonl').write_text(''.join(json.dumps(c,sort_keys=True)+'\n' for c in comparisons))
    write(out/'trade_receipt_gaps.json',gaps)
    write(out/'report.json',report)
    write(out/'manifest.json',{'files':{str(p.relative_to(REPO_ROOT)):sha(p) for p in out.iterdir() if p.is_file()},
                              'payloads_root':str((run/'objects').relative_to(REPO_ROOT)),
                              'payload_hashes':sorted(payload_hashes),'implementation_manifest_sha256':sha(RELEASE/'implementation_manifest.json')})
    print(json.dumps({'audit_directory':str(out.relative_to(REPO_ROOT)),'report':report},indent=2))
    return out

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--run',default=str(BASE/'live'))
    audit(Path(parser.parse_args().run))

if __name__=='__main__':
    main()
