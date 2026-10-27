from __future__ import annotations

import hashlib
from pathlib import Path


root = Path('/Users/zhurong/UROP')
state_path = root / 'CURRENT_STATE.md'
log_path = root / 'docs/progress/2026-10.md'
single = root / 'portfolio/LUMID_EVENTX_V6_SINGLE_FILE_REQUEST_20261002.md'
digest = hashlib.sha256(single.read_bytes()).hexdigest()

state = state_path.read_text()
old = (
    '2 October: a send-ready, scoped Lumid V6 evidence request and nine-article/'
    '15-contract JSON attachment are prepared in `portfolio/` and remain unsent. '
    'The frozen 268 unverified zero-export contract-days are two filtered-export '
    'days (17 and 19 May) repeated across 134 contracts. The request asks for '
    'historical feed/page/symbol, article-version, market-status and trade-feed '
    'receipts, with explicit unknowns when unavailable. No source admission; '
    'V6 support remains 0/8,844. Evidence: '
    '`portfolio/LUMID_EVENTX_V6_SOURCE_REQUEST_20261002.md` and '
    '`portfolio/LUMID_EVENTX_V6_SCOPE_20261002.json`.'
)
new = (
    '2 October: one send-ready Lumid V6 report now embeds the exact nine-article/'
    '15-contract scope and remains unsent: '
    '`portfolio/LUMID_EVENTX_V6_SINGLE_FILE_REQUEST_20261002.md`. '
    'It supersedes the two-file handoff for sending. The frozen 268 unverified '
    'zero-export contract-days are two filtered-export days (17 and 19 May) '
    'repeated across 134 contracts. The request asks for historical feed/page/'
    'symbol, article-version, market-status and trade-feed receipts, with '
    'explicit unknowns when unavailable. No source admission; V6 support '
    'remains 0/8,844.'
)
if state.count(old) != 1:
    raise SystemExit('current-state handoff does not match expected prior text')

log = log_path.read_text()
entry = (
    '\n- Consolidated the report and exact scope into the single send-ready '
    '`portfolio/LUMID_EVENTX_V6_SINGLE_FILE_REQUEST_20261002.md` '
    f'(SHA-256 `{digest}`). Parsed its embedded JSON and checked equality with '
    'the verified nine-article/15-contract scope. It needs no separate '
    'attachment and contains no article text, prices, resolutions or '
    'credentials. The earlier two-file handoff remains preserved as history. '
    'No external message was sent.\n'
)
if 'Consolidated the report and exact scope into the single send-ready' in log:
    raise SystemExit('monthly log already records single-file handoff')

state_path.write_text(state.replace(old, new, 1))
log_path.write_text(log.rstrip() + entry)
print('Recorded single-file handoff in current state and October progress.')
