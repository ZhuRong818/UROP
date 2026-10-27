"""Publish the prereceipted V6 history checks and update the project handoff."""
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import shutil

ROOT = Path(__file__).resolve().parent.parent
STAGE = ROOT / 'portfolio'
DATA = ROOT / 'data/v6'
NOTE = ROOT / 'eventx/release/v6/HISTORY_SURFACE_CHECK_20260929.md'
STATE = ROOT / 'CURRENT_STATE.md'
LOG = ROOT / 'docs/progress/2026-09.md'
JOBS = {
    'v6_history_surface_inventory_20260928': 'history_surface_inventory_20260928',
    'v6_history_schema_probe_20260928': 'history_schema_probe_20260928',
    'v6_market_history_multiplicity_20260928': 'market_history_multiplicity_20260928',
}


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


for source_name, destination_name in JOBS.items():
    source = STAGE / source_name
    destination = DATA / destination_name
    assert source.is_dir() and not destination.exists(), (source, destination)
    manifest = json.loads((source / 'manifest.json').read_text())
    for name, digest in manifest['outputs'].items():
        assert sha(source / name) == digest, (source, name)

assert (STAGE / 'HISTORY_SURFACE_CHECK_20260929.md').is_file()
assert not NOTE.exists()
state = STATE.read_text()
assert 'Last updated: **2026-09-28 Asia/Singapore**' in state
anchor = '## Active objective\n\n'
assert state.count(anchor) == 1
assert not 'Direct V6 history-surface check' in state
log = LOG.read_text()
assert '### 29 September — V6 Lumid history-surface check' not in log

for source_name, destination_name in JOBS.items():
    shutil.copytree(STAGE / source_name, DATA / destination_name)
shutil.copy2(STAGE / 'HISTORY_SURFACE_CHECK_20260929.md', NOTE)

insert = '''Direct V6 history-surface check completed 29 September. Both visible
catalog and SQL table inventories show no dedicated cursor/status/version-history
table to this read role. All five requested table schemas were readable. A
prereceipted aggregate query found exactly one retained market row for each of
the 15 scoped contracts (14 Polymarket, one Kalshi); no intermediate status or
term revision can be reconstructed from those rows. This is a visibility
limit, not proof that no provider-side logs or changes exist. Request the
historical receipts from Lumid; do not backfill status from current rows.
The request remains unsent pending a destination. No source admission or Jev
run; certified support remains 0/8,844 contract-days. Evidence:
`eventx/release/v6/HISTORY_SURFACE_CHECK_20260929.md` and the three
`data/v6/*history*20260928/` receipt folders.

'''
state = state.replace('Last updated: **2026-09-28 Asia/Singapore**', 'Last updated: **2026-09-29 Asia/Singapore**', 1)
state = state.replace(anchor, anchor + insert, 1)
STATE.write_text(state)

entry = '''\n### 29 September — V6 Lumid history-surface check\n\n- On EventX's configured `https://lum.id/findata`, a prereceipted read-only inventory returned HTTP 200 from both `provenance` and `prediction_markets` catalog table lists and a bounded `information_schema.tables` query. Neither role-visible inventory lists a dedicated cursor-transition, market-status-history or market-version table. This does not rule out provider-side logs. Exact receipt, SQL and response: `data/v6/history_surface_inventory_20260928/`.\n- Five catalog schema GETs and a bounded `information_schema.columns` query returned HTTP 200. The visible `scrape_cursor` holds a current cursor without validity/history fields. Kalshi and Polymarket market rows have `ingest_ts` and source run IDs plus status fields, but no visible version/validity interval. Exact schema receipt: `data/v6/history_schema_probe_20260928/`.\n- A separate prereceipted SQL aggregate restricted to the 15 scoped contract IDs returned 14 Polymarket and one Kalshi row, **one stored row and one source run per contract**. First/last `ingest_ts` match within every ID. A single retained row cannot establish past constancy of question, YES/NO mapping or active/suspended/closed state; `COUNT(DISTINCT status)=1` here is tautological. Exact query and per-ID counts: `data/v6/market_history_multiplicity_20260928/`. These two later probes ran on 29 September UTC despite their stage names.\n- Decision: keep every historical status/version cell unconfirmed pending provider receipts. Current cursor and later retry aggregates still do not certify feed windows by article decision times or clean-zero windows. The 28 September Lumid request remains unsent pending a destination; the source-specific interpretation is `eventx/release/v6/HISTORY_SURFACE_CHECK_20260929.md`. No protected evaluation, Jev run, model fit or source admission; V6 certified predictive support remains 0/8,844 contract-days.\n'''
LOG.write_text(log + entry)
print(json.dumps({'published_at_utc': datetime.now(timezone.utc).isoformat(), 'note': str(NOTE), 'data_folders': [str(DATA / x) for x in JOBS.values()], 'state': str(STATE), 'log': str(LOG)}, indent=2))
