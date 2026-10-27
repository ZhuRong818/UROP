"""Local source reconciliation; no labels, model loading, or canonical remapping."""
from collections import Counter, defaultdict
from datetime import datetime, timezone
from decimal import Decimal, ROUND_HALF_EVEN
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
BASE = ROOT / 'data/v7/local_execution_accounting_20261022'
AUDIT = ROOT / 'data/v7/direct_source_pilot_20261022_v03/audits/20261022T111727Z_158a60'
RUN = ROOT / 'data/v7/direct_source_pilot_20261022_v03/smoke/7982a689e9014012a3ff8410fd55dad7'
PROBE = ROOT / 'data/v7/execution_identity_20261022/d1ae8e245c3f47b1a7d9160759a52613'
RELEASE = ROOT / 'eventx/release/v7/direct_source_pilot_20261022_v03'
Q = Decimal('0.0000000001')

def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()

def write(p, obj):
    p.write_text(json.dumps(obj, indent=2, sort_keys=True) + '\n')

def lines(p):
    return [json.loads(l) for l in p.read_text().splitlines() if l.strip()]

def stamp(r):
    if 'timestamp' in r:
        return int(r['timestamp'])
    return int(datetime.fromisoformat(r['ts'].replace('Z', '+00:00')).timestamp())

def price(r):
    return Decimal(str(r['price']))

def economic(r, rounded=False):
    p = price(r).quantize(Q, rounding=ROUND_HALF_EVEN) if rounded else price(r)
    return str(r['token_id']), stamp(r), p, Decimal(str(r['size'])), r['side'].upper()

def verify_manifest(p):
    obj = json.loads(p.read_text())
    files = obj.get('files', obj.get('locked_files', {}))
    for rel, h in files.items():
        if sha(ROOT / rel) != h:
            raise RuntimeError('Frozen artifact changed: ' + rel)
    return len(files)

def main():
    BASE.mkdir(exist_ok=False)
    manifests = [AUDIT / 'manifest.json', PROBE / 'manifest.json', RELEASE / 'implementation_manifest.json',
                 ROOT / 'data/v7/autonomous_progress_20261022/manifest.json']
    verified = {str(p.relative_to(ROOT)): verify_manifest(p) for p in manifests}
    samples = {s['market_id']: s for s in lines(RELEASE / 'sample.jsonl')}
    protected = set(json.loads((ROOT / 'eventx/release/v7/market_capture_20261018/protected_ids.json').read_text()))
    if set(samples) & protected:
        raise RuntimeError('Protected overlap')
    records = lines(AUDIT / 'journal.jsonl')
    windows = {(r['market_id'], r['cycle'], r['source']): r for r in records if r['kind'] == 'window_summary'}
    requests = defaultdict(list)
    for r in records:
        if r['kind'] == 'rest' and r.get('endpoint_kind') == 'trades':
            requests[r['market_id'], r['cycle'], r['source']].append(r)
    used_payloads = {}

    def payload(base, receipt):
        p = base / 'objects' / receipt['payload_sha256']
        if sha(p) != receipt['payload_sha256']:
            raise RuntimeError('Raw hash mismatch')
        used_payloads[str(p.relative_to(ROOT))] = sha(p)
        return json.loads(p.read_text())

    reconciled, inventories = [], []
    for cid, cycle in sorted({(c, y) for c, y, _ in requests}):
        keys = [(cid, cycle, s) for s in ['venue', 'lumid']]
        if not all(len(requests[k]) == 1 and requests[k][0].get('status') == 'observed' and windows.get(k, {}).get('endpoint_window_returned') for k in keys):
            continue
        ws = [windows[k] for k in keys]
        lower, upper = max(w['start'] for w in ws), min(w['end'] for w in ws)
        if lower > upper:
            continue
        rs = [requests[k][0] for k in keys]
        vs = payload(RUN, rs[0])['data']
        ps = payload(RUN, rs[1])
        vs = [v for v in vs if lower <= stamp(v) <= upper]
        ps = [p for p in ps if lower <= stamp(p) <= upper]
        if any(str(v['token_id']) not in {samples[cid]['yes_asset_id'], samples[cid]['no_asset_id']} for v in vs + ps):
            raise RuntimeError('Token scope mismatch')
        cv, cp = Counter(economic(v, True) for v in vs), Counter(economic(p, True) for p in ps)
        same_second = defaultdict(list)
        for v in vs:
            if str(v['token_id']) == samples[cid]['yes_asset_id']:
                same_second[stamp(v)].append(v)
        conflicts = [t for t, rr in same_second.items() if len({price(v) for v in rr}) > 1]
        inventories.append({'market_id': cid, 'cycle': cycle, 'role': samples[cid]['diagnostic_role'],
                            'venue_rows': len(vs), 'provider_rows': len(ps),
                            'rounded_multiset_matched_rows': sum((cv & cp).values()),
                            'rounded_venue_only_rows': sum((cv - cp).values()),
                            'rounded_provider_only_rows': sum((cp - cv).values()),
                            'yes_seconds_with_different_prices': len(conflicts),
                            'yes_rows_in_conflicting_seconds': sum(len(same_second[t]) for t in conflicts),
                            'window_start': lower, 'window_end': upper})
        for p in ps:
            exact = [v for v in vs if economic(v) == economic(p)]
            rounded = [v for v in vs if economic(v, True) == economic(p, True)]
            tx = [v for v in rounded if str(p['trade_id']).startswith(v['transaction_hash'])]
            diffs = [abs(price(v) - price(p)) for v in tx]
            reconciled.append({'market_id': cid, 'cycle': cycle, 'role': samples[cid]['diagnostic_role'],
                               'provider_id_sha256': hashlib.sha256(str(p['trade_id']).encode()).hexdigest(),
                               'provider_payload_sha256': rs[1]['payload_sha256'], 'venue_payload_sha256': rs[0]['payload_sha256'],
                               'exact_matches': len(exact), 'rounded_matches': len(rounded),
                               'rounded_with_transaction_prefix_matches': len(tx),
                               'minimum_price_difference_with_prefix': str(min(diffs)) if diffs else None,
                               'explanation': 'exact_decimal_match' if exact else ('price_precision_only_with_transaction_prefix' if tx else 'unresolved'),
                               'unique_execution_certified': False})
    probe_rows = {}
    for r in lines(PROBE / 'journal.jsonl'):
        if r.get('status') == 'observed':
            probe_rows[r['market_id'], r['taker_only']] = payload(PROBE, r)['data']
    contract = json.loads((PROBE / 'contract.json').read_text())
    modes = []
    for cid, s in samples.items():
        counts = {}
        for mode, name in [(False, 'inclusive'), (True, 'taker_only')]:
            rr = [r for r in probe_rows[cid, mode] if contract['window_start'] <= stamp(r) <= contract['cutoff'] and str(r['token_id']) == s['yes_asset_id']]
            counts[name] = {'yes_rows': len(rr), 'yes_token_quantity': str(sum((Decimal(str(r['size'])) for r in rr), Decimal(0))),
                            'distinct_transaction_hashes': len({r['transaction_hash'] for r in rr})}
        modes.append({'market_id': cid, 'role': s['diagnostic_role'], **counts,
                      'yes_count_differs': counts['inclusive']['yes_rows'] != counts['taker_only']['yes_rows'],
                      'unique_execution_certified': False})
    first = [r for r in reconciled if r['cycle'] == 1]
    first_inv = [r for r in inventories if r['cycle'] == 1]
    rounding_only = [r for r in first if r['explanation'] == 'price_precision_only_with_transaction_prefix']
    summary = {'at': datetime.now(timezone.utc).isoformat(), 'verified_manifests': verified,
               'first_cycle_provider_rows': len(first), 'first_cycle_exact_matches': sum(r['exact_matches'] > 0 for r in first),
               'first_cycle_precision_explained': len(rounding_only),
               'first_cycle_precision_explained_markets': len({r['market_id'] for r in rounding_only}),
               'first_cycle_precision_explained_roles': dict(Counter(r['role'] for r in rounding_only)),
               'first_cycle_max_precision_difference': str(max((Decimal(r['minimum_price_difference_with_prefix']) for r in rounding_only), default=Decimal(0))),
               'first_cycle_rounded_with_prefix_matches': sum(r['rounded_with_transaction_prefix_matches'] > 0 for r in first),
               'first_cycle_ambiguous_rounded_prefix_matches': sum(r['rounded_with_transaction_prefix_matches'] > 1 for r in first),
               'first_cycle_multiset_venue_only_rows': sum(r['rounded_venue_only_rows'] for r in first_inv),
               'first_cycle_multiset_provider_only_rows': sum(r['rounded_provider_only_rows'] for r in first_inv),
               'first_cycle_yes_conflicting_seconds': sum(r['yes_seconds_with_different_prices'] for r in first_inv),
               'all_comparable_market_cycles': len(inventories), 'all_provider_row_occurrences': len(reconciled),
               'all_occurrence_explanations': dict(Counter(r['explanation'] for r in reconciled)),
               'all_occurrences_with_no_rounded_prefix_match': sum(r['rounded_with_transaction_prefix_matches'] == 0 for r in reconciled),
               'paired_probe_yes_count_differences_by_role': dict(Counter(r['role'] for r in modes if r['yes_count_differs'])),
               'method': 'Exploratory decimal-price diagnostic: round to ten decimal places using half-even; require exact token, second, size, side and transaction-hash prefix for precision explanation. Inclusive common windows preserve earlier source comparison. No tolerance is adopted in model inputs.',
               'limitations': ['Repeated cycles are not independent events.', 'Source snapshots were fetched separately; data may arrive late.', 'Transaction prefix plus economic agreement is not a unique fill identifier.', 'Maker/taker rows and same-second price order remain unresolved.', 'This is local source diagnosis, not an evaluation or admission.'],
               'model_scored': False, 'labels_computed': False, 'predictive_admissions': 0}
    for name, rows in [('provider_reconciliation', reconciled), ('window_inventory', inventories), ('canonical_yes_modes', modes)]:
        (BASE / (name + '.jsonl')).write_text(''.join(json.dumps(r, sort_keys=True) + '\n' for r in rows))
    write(BASE / 'report.json', summary)
    write(BASE / 'input_payload_hashes.json', used_payloads)
    files = [p for p in BASE.iterdir() if p.is_file()] + [Path(__file__).resolve()] + manifests
    write(BASE / 'manifest.json', {'files': {str(p.relative_to(ROOT)): sha(p) for p in files}})
    print(json.dumps(summary, indent=2))

if __name__ == '__main__':
    main()
