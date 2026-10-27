from pathlib import Path
import shutil

base = Path('/Users/zhurong/UROP')
here = Path(__file__).resolve().parent
source = here / 'v6_cursor_probe_20260928'
target = base / 'data/v6/cursor_successor_probe_20260928'
memo = base / 'eventx/release/v6/CURSOR_SUCCESSOR_RECONCILIATION_20260928.md'
state = base / 'CURRENT_STATE.md'
log = base / 'docs/progress/2026-09.md'
if target.exists() or memo.exists():
    raise FileExistsError('versioned output exists')
for name in ('cursor.sql', 'successors.sql', 'receipt.json', 'report.json', 'manifest.json'):
    if not (source / name).exists():
        raise FileNotFoundError(source / name)
old = state.read_text()
anchor = '## Active objective\n\n'
if old.count(anchor) != 1:
    raise ValueError('state insertion point changed')
addition = (
    "Direct same-surface V6 cursor check: `finnhub:company-news` has one\n"
    "endpoint cursor with `scope_key=''`, currently advanced to 28 September,\n"
    "not the relayed 5 June state. Four of five failed runs have a later\n"
    "`ok`/`partial` endpoint run within seven days; the June 23 run has none\n"
    "in that bounded search. All observed successors complete after their\n"
    "proposed decision times and do not prove window coverage. Historical\n"
    "cursor transitions, clean zero receipts and market status remain missing.\n"
    "No source certificate or model fit; certified V6 support remains 0/8,844\n"
    "contract-days. Evidence: `data/v6/cursor_successor_probe_20260928/` and\n"
    "`eventx/release/v6/CURSOR_SUCCESSOR_RECONCILIATION_20260928.md`.\n\n"
)
new = old.replace(anchor, anchor + addition, 1)
new = new.replace('No successor/complete-window\nor market-status certificate follows;',
                  'No complete-window\nor market-status certificate follows;', 1)
new = new.replace('cursor-key lookup for NVDA/MSTR returned zero matching keys; `scope_key` mapping\nand historical per-scope cursor transitions remain unknown.',
                  "cursor-key lookup for NVDA/MSTR returned zero matching keys; a later\nexact endpoint query confirmed `scope_key=''`. Historical cursor transitions remain unknown.", 1)
entry = (
    '\n### 28 September — same-surface endpoint cursor and bounded successor receipts\n\n'
    "- A prereceipted read-only query on EventX's configured `https://lum.id/findata` returned exactly one `finnhub:company-news` cursor with `scope_key=''`. At 13:39:21 UTC, its `last_run_id` was `fd8e77f3-7814-46b5-9a5a-54da94a26545`, `last_data_date=2026-09-28T12:37:40Z`, `last_run_at=2026-09-28T13:10:24.970190Z`, `next_action=delta`, `retry_count=0`. This explains the zero NVDA/MSTR key search and conflicts with the relayed assertion that the current cursor was still at 5 June. The other analyst's API, role, filters and query time remain unknown; this is overwritten current state, not historical state.\n"
    '- A fixed query found the first later `ok`/`partial` endpoint run within seven days for four of five failed runs: May 30 `d8bcb0d0…` → May 30 20:39:52 `78ae76ec…` ok, 34 inserted/0 failed, `to=May 31`; June 1 `c40c9e49…` → June 5 08:10:00 `05f950df…` partial, 285/1, `to=June 5`; June 30 `592ebc42…` and July 2 `86c568d4…` → July 6 18:02:33 `c4c5b4aa…` ok, 1,153/0, `to=July 7`. The June 23 `fd734424…` run had no matching completed successor within seven days. These are endpoint aggregates, not per-window proofs; all successors completed after the proposed decision time.\n'
    '- Exact queries, receipt, result and hashes: `data/v6/cursor_successor_probe_20260928/`; interpretation: `eventx/release/v6/CURSOR_SUCCESSOR_RECONCILIATION_20260928.md`. Keep all five failed windows unknown at decision time. Next align external ledger identity and obtain historical per-window/cursor receipts, clean zero-window receipts and market status/version history. No forecast fit, source admission, holdout or V4 action; V6 certified predictive support remains 0/8,844 contract-days.\n'
    '- “JEV” was searched in the repository and had no project definition; await the full model name or documentation before assessing an opened-development model trial.\n'
)
shutil.copytree(source, target)
shutil.copy2(here / 'v6_cursor_probe_20260928.py', target / 'probe.py')
shutil.copy2(here / 'v6_cursor_reconciliation_20260928.md', memo)
state.write_text(new)
with log.open('a') as fh:
    fh.write(entry)
print(target)
print(memo)
