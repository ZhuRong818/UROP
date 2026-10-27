from __future__ import annotations

import hashlib
from pathlib import Path


root = Path('/Users/zhurong/UROP')
file_path = root / 'portfolio/LUMID_EVENTX_V6_SINGLE_FILE_REQUEST_20261002.md'
state_path = root / 'CURRENT_STATE.md'
log_path = root / 'docs/progress/2026-10.md'
digest = hashlib.sha256(file_path.read_bytes()).hexdigest()

state = state_path.read_text()
old = '2 October: one send-ready Lumid V6 report now embeds the exact nine-article/'
new = '2 October: one send-ready Lumid V6 bug-triage report embeds the exact nine-article/'
if state.count(old) != 1:
    raise SystemExit('current-state note mismatch')

log = log_path.read_text()
if 'Reframed the single-file Lumid handoff as a bug-triage report' in log:
    raise SystemExit('revision already logged')
entry = (
    '- Reframed the single-file Lumid handoff as a bug-triage report with observed '
    'versus expected behavior, reproduction steps, impact, and separate triage '
    'outcomes for confirmed failures, researcher-reported incidents, and historical '
    'capability gaps. Preserved the exact embedded scope JSON (nine articles, 15 '
    f'contracts); revised SHA-256 `{digest}`. The earlier hash remains in the '
    'log as the pre-revision version. No external message or source admission.\n'
)

state_path.write_text(state.replace(old, new, 1))
log_path.write_text(log.rstrip() + '\n' + entry)
print('Recorded bug-report revision and updated handoff wording.')
