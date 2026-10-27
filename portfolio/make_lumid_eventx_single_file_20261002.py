from __future__ import annotations

import json
from pathlib import Path


folder = Path('/Users/zhurong/UROP/portfolio')
source = folder / 'LUMID_EVENTX_V6_SOURCE_REQUEST_20261002.md'
scope_path = folder / 'LUMID_EVENTX_V6_SCOPE_20261002.json'
target = folder / 'LUMID_EVENTX_V6_SINGLE_FILE_REQUEST_20261002.md'

report = source.read_text()
scope = json.loads(scope_path.read_text())
assert len(scope['articles']) == 9
assert len(scope['contract_ids']) == 15

replacements = {
    '**Attachment:** `LUMID_EVENTX_V6_SCOPE_20261002.json` (nine article/run IDs, nine proposed decision clocks, content hashes, 15 contract IDs, two global zero-export days)':
        '**Scope:** Nine article/run IDs, nine proposed decision clocks, 15 contract IDs, and two filtered-export days; the exact machine-readable list is in Appendix A below.',
    'for the attached scope': 'for the scope in Appendix A',
    'The attached JSON contains the exact scope. The nine article/run pairs are summarized here so the request can be triaged without opening the attachment:':
        'Appendix A contains the exact machine-readable scope. The nine article/run pairs are summarized here:',
    'in the attachment': 'in Appendix A',
    'each attached decision time': 'each listed decision time',
    'the attached decision time': 'the listed decision time',
}
for old, new in replacements.items():
    if old not in report:
        raise SystemExit(f'missing text to replace: {old}')
    report = report.replace(old, new)

report = report.rstrip() + '\n\n## Appendix A. Exact scope (machine-readable)\n\n'
report += 'This JSON is included here so the request needs no separate attachment. '
report += 'It contains identifiers, clocks, content hashes, and provenance hashes; '
report += 'it contains no article text, prices, resolutions, or credentials.\n\n'
report += '```json\n' + json.dumps(scope, indent=2, ensure_ascii=False) + '\n```\n'
target.write_text(report)
print(target)
