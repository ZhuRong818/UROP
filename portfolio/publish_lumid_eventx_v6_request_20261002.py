from __future__ import annotations

import hashlib
import json
from pathlib import Path


root = Path('/Users/zhurong/UROP')
portfolio = root / 'portfolio'
report = portfolio / 'LUMID_EVENTX_V6_SOURCE_REQUEST_20261002.md'
scope = portfolio / 'LUMID_EVENTX_V6_SCOPE_20261002.json'
manifest = portfolio / 'LUMID_EVENTX_V6_HANDOFF_MANIFEST_20261002.json'
state_path = root / 'CURRENT_STATE.md'
progress_path = root / 'docs/progress/2026-10.md'

payload = json.loads(scope.read_text())
assert len(payload['articles']) == 9
assert len(payload['contract_ids']) == 15
assert sum(day['repeated_contract_day_cells'] for day in payload['global_zero_export_days_not_proven_empty']) == 268
assert 'postgres:' not in report.read_text().lower()
assert 'postgres:' not in scope.read_text().lower()

hashes = {
    path.name: hashlib.sha256(path.read_bytes()).hexdigest()
    for path in (report, scope)
}
manifest.write_text(json.dumps({'files_sha256': hashes}, indent=2) + '\n')

state = state_path.read_text()
state_note = (
    '2 October: a send-ready, scoped Lumid V6 evidence request and nine-article/'
    '15-contract JSON attachment are prepared in `portfolio/` and remain unsent. '
    'The frozen 268 unverified zero-export contract-days are two filtered-export '
    'days (17 and 19 May) repeated across 134 contracts. The request asks for '
    'historical feed/page/symbol, article-version, market-status and trade-feed '
    'receipts, with explicit unknowns when unavailable. No source admission; '
    'V6 support remains 0/8,844. Evidence: '
    '`portfolio/LUMID_EVENTX_V6_SOURCE_REQUEST_20261002.md` and '
    '`portfolio/LUMID_EVENTX_V6_SCOPE_20261002.json`.\n\n'
)
if state_note in state:
    raise SystemExit('state note already present')
needle = '## Active objective\n\n'
assert state.count(needle) == 1
state = state.replace(needle, needle + state_note, 1)

progress_entry = (
    '# October 2026 progress\n\n'
    '### 2 October — send-ready Lumid V6 source request\n\n'
    '- Prepared `portfolio/LUMID_EVENTX_V6_SOURCE_REQUEST_20261002.md` and '
    '`portfolio/LUMID_EVENTX_V6_SCOPE_20261002.json` as a standalone request/attachment; '
    'exact file hashes are in `portfolio/LUMID_EVENTX_V6_HANDOFF_MANIFEST_20261002.json`. '
    'No external message was sent. The scope contains nine opened-development '
    'article/run IDs and decision clocks, content hashes, 15 contract IDs, and '
    'two filtered-export days. It contains no market prices, resolutions, article '
    'text, credentials or protected V4 records.\n'
    '- Verified the frozen `data/v6/support_ledger_20260926/ledger.jsonl` SHA-256 '
    'against its manifest. Its 268 `zero_export_rows_not_proven_empty` cells are '
    '134 contracts on 17 May plus the same 134 on 19 May. These are EventX '
    'filtered-export zeros, not proof that Lumid had no articles or that either '
    'source window completed. The request asks for the exact filters and two-day '
    'completion receipts.\n'
    '- The report requests article commit/version semantics, all nine scoped '
    'news-run page/symbol/window records, dated Finnhub roster-filter changes, '
    '135 market-time status cells and historical terms, trade-feed mechanics, '
    'and explicit unavailability where no logs exist. A reported stale replica '
    'and audit-log credential issue are separated as operations/security items. '
    'Tweet-to-market remains outside this V6 scope. No data collection, model '
    'fit, source certification, or predictive admission; V6 remains 0/8,844.\n'
)
if progress_path.exists():
    existing = progress_path.read_text()
    if '### 2 October — send-ready Lumid V6 source request' in existing:
        raise SystemExit('progress entry already present')
    progress_entry = existing.rstrip() + '\n\n' + progress_entry.split('\n\n', 1)[1]

state_path.write_text(state)
progress_path.write_text(progress_entry)
print('Verified handoff, wrote SHA-256 manifest, updated current state and October progress.')
