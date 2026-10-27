"""Publish the sanitized V6 receipt-sweep interpretation and handoff update."""
from pathlib import Path
import shutil

ROOT = Path(__file__).resolve().parent.parent
STAGE = ROOT / 'portfolio'
NOTE = ROOT / 'eventx/release/v6/V6_SOURCE_RECEIPT_SWEEP_20260929.md'
SECURITY = STAGE / 'LUMID_AUDIT_LOG_SECURITY_HANDOFF_20260929.md'
STATE = ROOT / 'CURRENT_STATE.md'
LOG = ROOT / 'docs/progress/2026-09.md'
assert (STAGE / NOTE.name).is_file() and not NOTE.exists() and SECURITY.is_file()
state = STATE.read_text()
anchor = '## Active objective\n\n'
assert state.count(anchor) == 1
assert 'V6_SOURCE_RECEIPT_SWEEP_20260929.md' not in state
log = LOG.read_text()
assert '### 29 September — V6 receipt-table sweep and sanitized audit-log flag' not in log

insert = '''A user-relayed database receipt-table sweep found no queryable loader-level
page, symbol-roster or historical cursor record; `scrape_cursor` is latest-only
and the API audit log is not a feed receipt. The only remaining historical
feed-coverage candidate is retained loader/collector file logs, which require
findata-owner confirmation. A reported 28 May Finnhub universe change
7,851→7,258 is count-only and its stated 331-symbol drop conflicts with
the arithmetic difference of 593; EventX directly observes 7,258→7,220
later. All failed-window/zero-news and market-status cells stay unknown,
support 0/8,844. A separate credential-bearing audit error was reported;
the sanitized owner handoff contains no secret. Evidence:
`eventx/release/v6/V6_SOURCE_RECEIPT_SWEEP_20260929.md` and
`portfolio/LUMID_AUDIT_LOG_SECURITY_HANDOFF_20260929.md`.

'''
entry = '''\n### 29 September — V6 receipt-table sweep and sanitized audit-log flag\n\n- Researcher-relayed full name-pattern sweep of queryable tables found no loader page, per-symbol roster, per-window completion or append-only cursor records. The only reported candidates were overwrite-only `provenance.scrape_cursor` and `lumid_data_meta.audit_log`, whose rows describe API operations rather than loader pages. This narrows the **visible database**; file logs and other inaccessible retention remain unverified. The remaining owner question is whether `/data/findata/loaders/run.py` and the Finnhub collector wrote retained per-page/symbol/cursor logs for the nine scoped runs. User-relayed aggregate args-shape counts are 1,664 FMP and 837 Finnhub runs on the frozen replica; direct EventX lineage independently confirms the nine scoped shapes.\n- Researcher reports a 28 May 22:30 UTC `n_symbols` change 7,851→7,258 but calls it 331 dropped; arithmetic gives **593**. Record counts and time as relayed, reject the unsupported 331 claim and leave exact roster membership unknown. Direct scoped live lineage later shows 7,258→7,220; the stale replica cannot date that change. The endpoint-wide empty scope key does not establish exact NVDA/MSTR inclusion or full coverage.\n- Five failed article windows remain unknown by decision time. Four `ok` scoped runs also lack page-completion certificates despite three FMP runs having explicit `from`/`to`. The 268 zero-export contract-days and historical market status remain uncertified. No predictive admission; support remains 0/8,844. If retained loader logs are unavailable, preserve the retrospective `unknown` cells and use the prospective-capture plan for a future source-supported study. Interpretation: `eventx/release/v6/V6_SOURCE_RECEIPT_SWEEP_20260929.md`.\n- Researcher reports a plaintext credential-bearing connection string in an API audit-log error. No raw error or secret was copied or queried by EventX. Sanitized owner handoff: `portfolio/LUMID_AUDIT_LOG_SECURITY_HANDOFF_20260929.md`; rotate if valid, restrict/remediate the log and fix error redaction. This is a security issue separate from V6 certification; no message was sent externally.\n'''
shutil.copy2(STAGE / NOTE.name, NOTE)
STATE.write_text(state.replace(anchor, anchor + insert, 1))
LOG.write_text(log + entry)
print(NOTE)
