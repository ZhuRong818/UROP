from pathlib import Path


path = Path('/Users/zhurong/UROP/CURRENT_STATE.md')
text = path.read_text()
old = (
    '> artifacts for exact values and `docs/progress/2026-09.md` for detailed history.\n\n'
    'Last updated: **2026-09-29 Asia/Singapore**'
)
new = (
    '> artifacts for exact values and `docs/progress/YYYY-MM.md` for detailed history.\n\n'
    'Last updated: **2026-10-02 Asia/Singapore**'
)
if text.count(old) != 1:
    raise SystemExit('header mismatch')
path.write_text(text.replace(old, new, 1))
print('Updated current-state header date and monthly-log pointer.')
