"""Append the scoped ok-run argument correction without changing source receipts."""
from pathlib import Path
import shutil

ROOT = Path(__file__).resolve().parent.parent
SOURCE = ROOT / 'portfolio/V6_REPLICA_RECONCILIATION_20260929.md'
TARGET = ROOT / 'eventx/release/v6/V6_REPLICA_RECONCILIATION_20260929.md'
LOG = ROOT / 'docs/progress/2026-09.md'
assert SOURCE.is_file() and TARGET.is_file()
assert 'three FMP `ok` runs already have explicit' in SOURCE.read_text()
assert 'three FMP `ok` runs already have explicit' not in TARGET.read_text()
log = LOG.read_text()
addition = '''\n- Correction to the relayed blanket claim about the four scoped `ok` runs: direct `data/v6/scoped_source_evidence_20260927/lineage.jsonl` has explicit `args.from` and `args.to` for three FMP runs (article IDs 102500031, 152232532, 193693829). Only the fourth, Finnhub article 211869183, has `to` and `n_symbols=7220` without `from`. These request bounds still are not page-completion certificates. The correction is appended to `eventx/release/v6/V6_REPLICA_RECONCILIATION_20260929.md`.\n'''
assert addition.strip() not in log
shutil.copy2(SOURCE, TARGET)
LOG.write_text(log + addition)
print(TARGET)
