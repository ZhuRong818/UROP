from __future__ import annotations

import hashlib
import json
from collections import Counter
from pathlib import Path


root = Path('/Users/zhurong/UROP')
scope_path = root / 'data/v6/context_development_review_20260927/provider_scope.json'
ledger_path = root / 'data/v6/support_ledger_20260926/ledger.jsonl'
ledger_manifest_path = root / 'data/v6/support_ledger_20260926/manifest.json'
output_path = root / 'portfolio/LUMID_EVENTX_V6_SCOPE_20261002.json'

scope = json.loads(scope_path.read_text())
ledger_manifest = json.loads(ledger_manifest_path.read_text())
actual_ledger_hash = hashlib.sha256(ledger_path.read_bytes()).hexdigest()
assert actual_ledger_hash == ledger_manifest['outputs']['ledger.jsonl']
assert len(scope['articles']) == 9
assert len(scope['contracts']) == 15

zero_rows = [
    json.loads(line)
    for line in ledger_path.open()
    if 'zero_export_rows_not_proven_empty' in line
]
assert all(row['global_news_status'] == 'zero_export_rows_not_proven_empty' for row in zero_rows)
zero_counts = Counter(row['day'] for row in zero_rows)
assert zero_counts == {'2026-05-17': 134, '2026-05-19': 134}

payload = {
    'request': 'EventX V6 historical source evidence',
    'window_start_utc_inclusive': '2026-05-17T00:00:00Z',
    'window_end_utc_exclusive': '2026-07-22T00:00:00Z',
    'articles': [
        {
            'article_id': item['article_id'],
            'source_run_id': item['source_run_id'],
            'source_run_status': item['source_run_status'],
            'proposed_decision_time_utc': item['source_clock'],
            'content_sha256': item['content_sha256'],
        }
        for item in scope['articles']
    ],
    'contract_ids': [item['contract_id'] for item in scope['contracts']],
    'global_zero_export_days_not_proven_empty': [
        {'day_utc': day, 'repeated_contract_day_cells': count}
        for day, count in sorted(zero_counts.items())
    ],
    'provenance': {
        'provider_scope_sha256': hashlib.sha256(scope_path.read_bytes()).hexdigest(),
        'frozen_support_ledger_sha256': actual_ledger_hash,
    },
}
output_path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + '\n')
print(output_path)
