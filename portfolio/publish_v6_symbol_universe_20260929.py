from __future__ import annotations

import hashlib
import json
import shutil
from pathlib import Path


root = Path('/Users/zhurong/UROP')
stage = root / 'portfolio'
data = root / 'data/v6'
folders = (
    'v6_symbol_universe_schema_20260929',
    'v6_symbol_universe_rows_20260929',
    'v6_symbol_universe_counts_20260929',
    'v6_finnhub_universe_transitions_20260929',
)
dest_names = tuple(name.removeprefix('v6_') for name in folders)
memo_source = stage / 'V6_SYMBOL_UNIVERSE_RECONCILIATION_20260929.md'
memo_target = root / 'eventx/release/v6/V6_SYMBOL_UNIVERSE_RECONCILIATION_20260929.md'
state_path = root / 'CURRENT_STATE.md'
progress_path = root / 'docs/progress/2026-09.md'

for source_name, dest_name in zip(folders, dest_names, strict=True):
    source = stage / source_name
    target = data / dest_name
    if target.exists():
        raise SystemExit(f'target already exists: {target}')
    manifest = json.loads((source / 'manifest.json').read_text())
    for name, expected in manifest['outputs'].items():
        actual = hashlib.sha256((source / name).read_bytes()).hexdigest()
        if actual != expected:
            raise SystemExit(f'hash mismatch: {source / name}')

if memo_target.exists():
    raise SystemExit(f'target already exists: {memo_target}')

state = state_path.read_text()
start = state.index('## Active objective\n\n') + len('## Active objective\n\n')
end = state.index('\nDirect V6 history-surface check', start)
new_prefix = (stage / 'V6_SYMBOL_UNIVERSE_STATE_PREFIX_20260929.txt').read_text()
new_state = state[:start] + new_prefix.rstrip() + '\n' + state[end:]

progress = progress_path.read_text()
addition = (stage / 'V6_SYMBOL_UNIVERSE_PROGRESS_20260929.txt').read_text()
if '### 29 September — direct live V6 symbol-universe reconciliation' in progress:
    raise SystemExit('progress section already present')
new_progress = progress.rstrip() + '\n\n' + addition.rstrip() + '\n'

for source_name, dest_name in zip(folders, dest_names, strict=True):
    shutil.copytree(stage / source_name, data / dest_name)
shutil.copy2(memo_source, memo_target)
state_path.write_text(new_state)
progress_path.write_text(new_progress)
print('Published four receipt folders, memo, CURRENT_STATE.md, and 2026-09 progress entry.')
