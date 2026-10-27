"""Record the researcher-relayed read-replica explanation in V6 handoff."""
from pathlib import Path
import shutil

ROOT = Path(__file__).resolve().parent.parent
STAGED = ROOT / 'portfolio/V6_REPLICA_RECONCILIATION_20260929.md'
NOTE = ROOT / 'eventx/release/v6/V6_REPLICA_RECONCILIATION_20260929.md'
STATE = ROOT / 'CURRENT_STATE.md'
LOG = ROOT / 'docs/progress/2026-09.md'

assert STAGED.is_file() and not NOTE.exists()
state = STATE.read_text()
old = '''Direct 28 September V6 lineage recheck supersedes the relayed claim that
three June/July failed run IDs are missing. On EventX's configured
`https://lum.id/findata`, all three returned HTTP 200 from the catalog **and**
3/3 exact rows from `provenance.runs` SQL; each is a failed
`finnhub:company-news` run. Align the other analyst's deployment, role and query
filters before inferring alternate `/ingest` paths. No complete-window
or market-status certificate follows; 0/8,844 predictive contract-days remain.
Evidence: `data/v6/lineage_surface_conflict_20260928/`,
`data/v6/lineage_sql_surface_20260928/`, and
`eventx/release/v6/LINEAGE_LEDGER_CONFLICT_20260928.md`.
'''
new = '''The earlier June/July run-ledger discrepancy now has a coherent
researcher-reported cause: their cluster-internal read replica stopped near
7 June, while EventX's live SQL/catalog returned all three post-freeze runs.
Two pre-freeze run end times match EventX lineage to the microsecond; the
alternate `/ingest`/tenant inference is withdrawn. The reported snapshot
freeze is not independently queried by EventX. `finnhub:company-news` has
one `scope_key=''` cursor, but scoped `args.n_symbols` changes from 7,258
to 7,220, so per-run symbol/window/page proof remains necessary. Historical
feed completion and market status are still unknown; 0/8,844 predictive
contract-days. Evidence: `eventx/release/v6/V6_REPLICA_RECONCILIATION_20260929.md`,
`data/v6/lineage_sql_surface_20260928/` and
`data/v6/scoped_source_evidence_20260927/lineage.jsonl`.
'''
assert state.count(old) == 1
state = state.replace(old, new)
assert 'V6_REPLICA_RECONCILIATION_20260929.md' not in state.replace(new, '')
log = LOG.read_text()
assert '### 29 September — reported frozen read replica explains V6 ledger disagreement' not in log
entry = '''\n### 29 September — reported frozen read replica explains V6 ledger disagreement\n\n- The researcher reports their cluster-internal `claude-proxy.lumid.svc.cluster.local:8080/data/retrieve` role reads a snapshot with `max(started_at)=2026-06-07T21:18:06Z`, `max(ended_at)=2026-06-07T21:18:22Z`, 16 runs still marked `running`, and a 5 June cursor. The replica/snapshot diagnosis is user-relayed; no raw replica receipt or local JSONL was supplied. Two pre-freeze failed run end times match EventX's direct lineage to the microsecond. EventX's live catalog and SQL have the three post-freeze June/July failed runs. This resolves the differing observations without an alternate `/ingest`/tenant explanation; the latter inference is withdrawn. The 28 September direct receipts remain authoritative for EventX's configured API.\n- A single `finnhub:company-news` `scope_key=''` is consistent across surfaces, but its scoped run `args.n_symbols` is not fixed: 7,258 for May 30, June 1 and June 23; 7,220 for June 30, July 2 and July 9. None of the six run arguments has a `from` bound or symbol list. The overwrite-only cursor cannot recover page history. No per-window completeness/clean-zero receipt follows from this clarification.\n- The researcher's surviving failed-run article with `ingest_ts` inside the run interval supports mid-run row persistence, but does not by itself prove exact commit/client visibility or unchanged article bytes. The frozen EventX `available_at` formula is ≥ `ingest_ts` and equals cleanup time for five failed runs. Retain it as the conservative decision clock while keeping stronger first-visibility claims conditional on stamp/version semantics. Historical market status and term versions remain unknown; EventX's exact 15-ID query found one retained row each.\n- Narrow the source-owner ask to historical page/window/cursor and zero-window receipts by decision time, `ingest_ts`/revision semantics, and market status/version archives. Replica restoration is an operational issue, not a V6 source certificate. Detailed reconciliation: `eventx/release/v6/V6_REPLICA_RECONCILIATION_20260929.md`. The broader 28 September request is preserved unchanged and unsent. No model fit, Jev run, holdout access or predictive admission; V6 remains 0/8,844 supported contract-days.\n'''
shutil.copy2(STAGED, NOTE)
STATE.write_text(state)
LOG.write_text(log + entry)
print(NOTE)
