"""Metadata-only selection of the V02 live cohort (no quote, trade or price history read).

Rules frozen in REL/protocol.json before this runs. Volume is used only as an
eligibility floor; order among eligible markets is a salted hash, not activity rank.
"""
from datetime import datetime, timedelta, timezone
import hashlib
import json

import httpx

from eventx.tasks.discover_v7_direct_pilot_20261022 import now, write
from eventx.tasks.run_v7_archive_week_pilot_20261025 import EX
from eventx.v7 import forecast_runtime_20261026_v02 as rt

OLD = rt.REPO_ROOT/'data/v7/family_training_20261025_v02/cohort/cohorts.json'
NEWID = rt.REPO_ROOT/'data/v7/new_identity_test_20261026/cohort/cohort.json'


def main():
    p = json.loads(rt.PROTOCOL.read_text())['cohort_rules']
    if rt.COHORT.exists():
        raise RuntimeError('Cohort already frozen')
    old = json.loads(OLD.read_text())
    used = {m['market_id'] for m in old['development50']+old['unseen10']}
    used |= {m['market_id'] for m in json.loads(NEWID.read_text())['new']}
    excluded = set(json.loads(EX.read_text())) | used
    at = datetime.now(timezone.utc)
    min_end = datetime.fromisoformat(p['min_end_date'])
    receipts, pool = [], []
    with httpx.Client(timeout=30) as client:
        for offset in range(0, p['pages']*200, 200):
            q = {'active': 'true', 'closed': 'false', 'limit': 200, 'offset': offset, 'order': 'volume24hr', 'ascending': 'false'}
            r = client.get('https://gamma-api.polymarket.com/markets', params=q)
            receipts.append({'at': now().isoformat(), 'query': q, 'status': r.status_code, 'sha256': hashlib.sha256(r.content).hexdigest()})
            r.raise_for_status()
            pool += r.json()
        eligible, seen_events = [], set()
        for m in pool:
            tokens, outcomes = m.get('clobTokenIds'), m.get('outcomes')
            tokens = json.loads(tokens) if isinstance(tokens, str) else tokens
            outcomes = json.loads(outcomes) if isinstance(outcomes, str) else outcomes
            try:
                start = datetime.fromisoformat(m['startDate'].replace('Z', '+00:00'))
                end = datetime.fromisoformat(m['endDate'].replace('Z', '+00:00'))
            except (KeyError, AttributeError, ValueError):
                continue
            ok = (outcomes == ['Yes', 'No'] and isinstance(tokens, list) and len(tokens) == 2 and m.get('description')
                  and m.get('active') is True and m.get('closed') is False and m.get('acceptingOrders') is True
                  and m.get('enableOrderBook') is True and m.get('events') and m['conditionId'] not in excluded
                  and start < at-timedelta(days=p['min_age_days']) and end >= min_end
                  and float(m.get('volume24hr') or 0) >= p['min_volume24hr'])
            if ok:
                eligible.append((m, tokens))
        eligible.sort(key=lambda x: hashlib.sha256((p['salt']+x[0]['conditionId']).encode()).hexdigest())
        chosen = []
        for m, tokens in eligible:
            ev = {str(e['id']) for e in m['events']}
            if ev & seen_events:
                continue
            r = client.get('https://data-api.polymarket.com/v2/resolutions', params={'condition': m['conditionId']})
            rows = r.json().get('data', []) if r.status_code == 200 else None
            posed = rows is not None and len(rows) == 1 and rows[0].get('status') == 'posed' and not rows[0].get('resolved_at')
            receipts.append({'at': now().isoformat(), 'market_id': m['conditionId'], 'resolution_status': r.status_code,
                             'resolution_posed': posed, 'sha256': hashlib.sha256(r.content).hexdigest()})
            if not posed:
                continue
            seen_events |= ev
            chosen.append({'market_id': m['conditionId'], 'yes_asset_id': str(tokens[0]), 'no_asset_id': str(tokens[1]),
                           'question': m['question'], 'rules': m['description'], 'end_date': m['endDate'],
                           'family': '|'.join(sorted(ev)), 'event_title': m['events'][0].get('title'),
                           'metadata_ingest_ts': now().isoformat(), 'selection': 'metadata_only_hash_order_v02'})
            if len(chosen) == p['size']:
                break
    write(rt.REL/'cohort_selection_receipts.json', {'at': now().isoformat(), 'pool': len(pool), 'eligible': len(eligible),
                                                     'selected': len(chosen), 'requests': receipts})
    rt.COHORT.write_text(''.join(json.dumps(c, sort_keys=True)+'\n' for c in chosen))
    print(json.dumps({'pool': len(pool), 'eligible': len(eligible), 'selected': len(chosen),
                      'questions': [c['question'] for c in chosen]}, indent=1))


if __name__ == '__main__':
    main()
