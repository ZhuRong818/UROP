"""Compare retained source snapshots locally; never replace decision-time data."""
from collections import Counter
from decimal import Decimal
import json
from pathlib import Path
from datetime import datetime, timezone
from eventx.tasks.diagnose_v7_execution_accounting_20261022 import (
    ROOT, AUDIT, RUN, PROBE, RELEASE, lines, sha, stamp, economic, write, verify_manifest,
)

OUT = ROOT / 'data/v7/participant_coverage_20261023'

def main():
    OUT.mkdir(exist_ok=False)
    manifests = [AUDIT / 'manifest.json', PROBE / 'manifest.json', RELEASE / 'implementation_manifest.json',
                 ROOT / 'data/v7/local_execution_accounting_20261022/manifest.json']
    verified = {str(p.relative_to(ROOT)): verify_manifest(p) for p in manifests}
    sample = {r['market_id']: r for r in lines(RELEASE / 'sample.jsonl')}
    protected = set(json.loads((ROOT / 'eventx/release/v7/market_capture_20261018/protected_ids.json').read_text()))
    if set(sample) & protected:
        raise RuntimeError('Protected overlap')
    used = {}
    def body(base, r):
        p = base / 'objects' / r['payload_sha256']
        if sha(p) != r['payload_sha256']:
            raise RuntimeError('Payload mismatch')
        used[str(p.relative_to(ROOT))] = sha(p)
        return json.loads(p.read_text())
    records = lines(AUDIT / 'journal.jsonl')
    win = {(r['market_id'], r['source']): r for r in records if r['kind'] == 'window_summary' and r['cycle'] == 1}
    old = {(r['market_id'], r['source']): r for r in records if r['kind'] == 'rest' and r.get('endpoint_kind') == 'trades' and r['cycle'] == 1 and r.get('status') == 'observed'}
    probe = {(r['market_id'], r['taker_only']): r for r in lines(PROBE / 'journal.jsonl') if r.get('status') == 'observed'}
    market_rows, detail = [], []
    for cid, s in sample.items():
        if any(k not in old for k in [(cid, 'venue'), (cid, 'lumid')]):
            continue
        if not all(win[cid, src]['endpoint_window_returned'] for src in ['venue', 'lumid']):
            continue
        av = body(RUN, old[cid, 'venue'])
        p = body(RUN, old[cid, 'lumid'])
        bv = body(PROBE, probe[cid, False])
        bt = body(PROBE, probe[cid, True])
        lower = max(win[cid, src]['start'] for src in ['venue', 'lumid'])
        upper = min(win[cid, src]['end'] for src in ['venue', 'lumid'])
        # When a later first page is truncated, exclude its entire oldest second.
        # This preserves a bounded shared range without pretending the missing page is empty.
        for v in [av, bv, bt]:
            if v['pagination']['next_cursor'] is not None:
                if not v['data']:
                    raise RuntimeError('Empty cursor page')
                lower = max(lower, min(stamp(x) for x in v['data']) + 1)
        if lower > upper:
            market_rows.append({'market_id': cid, 'role': s['diagnostic_role'], 'status': 'no_shared_retained_range'})
            continue
        selected = [[r for r in rr if lower <= stamp(r) <= upper] for rr in [av['data'], p, bv['data'], bt['data']]]
        a, ps, b, t = selected
        def key(v):
            return v['transaction_hash'], economic(v, True)
        ca, cb, ct = [Counter(map(key, rr)) for rr in [a, b, t]]
        same_snapshot_keys = set(cb) & set(ct)
        maker_keys = set(cb) - set(ct)
        # Membership is descriptive. No mapping from these keys to unique executions is asserted.
        role_counts = Counter()
        for r in ps:
            matches = [v for v in b if economic(v, True) == economic(r, True) and str(r['trade_id']).startswith(v['transaction_hash'])]
            kt = {key(v) for v in matches}
            label = ('taker_key_present' if kt & same_snapshot_keys else
                     'maker_inclusive_only_key' if kt & maker_keys else 'not_in_later_snapshot')
            role_counts[label] += 1
            detail.append({'market_id': cid, 'role': s['diagnostic_role'], 'provider_id_sha256': __import__('hashlib').sha256(str(r['trade_id']).encode()).hexdigest(),
                           'classification': label, 'later_matching_rows': len(matches), 'canonical_execution_identity': 'unresolved'})
        cp = Counter(economic(r, True) for r in ps)
        ect = Counter(economic(r, True) for r in t)
        market_rows.append({'market_id': cid, 'role': s['diagnostic_role'], 'status': 'shared_retained_range',
                            'window_start': lower, 'window_end': upper,
                            'earlier_venue_rows': len(a), 'provider_rows': len(ps), 'later_inclusive_rows': len(b), 'later_taker_rows': len(t),
                            'earlier_only_vs_later_inclusive': sum((ca - cb).values()), 'later_only_vs_earlier_inclusive': sum((cb - ca).values()),
                            'later_taker_keys_absent_in_inclusive': sum((ct - cb).values()),
                            'provider_membership': dict(role_counts),
                            'later_taker_rows_not_economically_matched_by_provider': sum((ect - cp).values()),
                            'provider_rows_not_economically_matched_by_later_taker': sum((cp - ect).values()),
                            'unique_executions_certified': False})
    by_role = {}
    for role in sorted({r['role'] for r in market_rows}):
        rr = [r for r in market_rows if r['role'] == role and r['status'] == 'shared_retained_range']
        fields = ['earlier_venue_rows', 'provider_rows', 'later_inclusive_rows', 'later_taker_rows',
                  'earlier_only_vs_later_inclusive', 'later_only_vs_earlier_inclusive', 'later_taker_keys_absent_in_inclusive',
                  'later_taker_rows_not_economically_matched_by_provider', 'provider_rows_not_economically_matched_by_later_taker']
        totals = {k: sum(r[k] for r in rr) for k in fields}
        totals['markets'] = len(rr)
        totals['provider_membership'] = dict(sum((Counter(r['provider_membership']) for r in rr), Counter()))
        by_role[role] = totals
    report = {'at': datetime.now(timezone.utc).isoformat(), 'verified_manifests': verified,
              'by_role': by_role, 'shared_range_markets': sum(r['status'] == 'shared_retained_range' for r in market_rows),
              'purpose': 'Diagnose accounting and coverage across previously captured snapshots, not decision-time input reconstruction.',
              'limits': ['Later probe is approximately one hour later, not simultaneous or proof of exchange completeness.',
                         'Price rounding is the exploratory ten-decimal diagnostic, not an adopted feature transform.',
                         'First-page truncation removes the oldest retained second; bounded shared range is reported for every market.',
                         'Maker-only classification means no matching taker key in the retained later response, not an independently verified participant role.',
                         'No missing forward prices or evidence were fabricated; no model or holdout evaluated.'],
              'models_scored': False, 'predictive_admissions': 0}
    for name, rs in [('market_coverage', market_rows), ('provider_membership', detail)]:
        (OUT / (name + '.jsonl')).write_text(''.join(json.dumps(r, sort_keys=True) + '\n' for r in rs))
    write(OUT / 'report.json', report)
    write(OUT / 'input_payload_hashes.json', used)
    files = list(OUT.iterdir()) + [Path(__file__).resolve()] + manifests
    write(OUT / 'manifest.json', {'files': {str(p.relative_to(ROOT)): sha(p) for p in files}})
    print(json.dumps(report, indent=2))

if __name__ == '__main__':
    main()
