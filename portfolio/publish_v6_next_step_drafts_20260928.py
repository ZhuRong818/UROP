"""Publish V6 source request, class-map and Jev development drafts."""
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import shutil

base = Path('/Users/zhurong/UROP')
here = Path(__file__).resolve().parent
release = base / 'eventx/release/v6'
artifact = base / 'data/v6/next_step_drafts_20260928'
state = base / 'CURRENT_STATE.md'
progress = base / 'docs/progress/2026-09.md'
names = (
    'V6_LUMID_EVIDENCE_REQUEST_20260928.md',
    'V6_RELAXED_CLASS_MAP_DRAFT_20260928.md',
    'V6_JEV_DEVELOPMENT_TRIAL_DRAFT_20260928.md',
)
if artifact.exists() or any((release / name).exists() for name in names):
    raise FileExistsError('versioned output already exists')
for name in (*names, 'v6_class_map_draft_20260928.json'):
    if not (here / name).is_file():
        raise FileNotFoundError(here / name)

old = state.read_text()
anchor = '## Active objective\n\n'
if old.count(anchor) != 1:
    raise ValueError('CURRENT_STATE anchor changed')
addition = (
    'V6 next-step drafts completed 28 September: revised nine-article/15-contract\n'
    'Lumid evidence request, explicit five-bucket mapping of 102 opened relaxed\n'
    'labels, and a TypeSafe Jev semantic diagnostic design. The request is NOT\n'
    'SENT; the class map is post-label development only and not audit-frozen;\n'
    'Jev was not run and no article text left the workspace. Historical feed\n'
    'completion and market status remain unknown; 0/8,844 predictive days.\n'
    'Evidence: `eventx/release/v6/V6_LUMID_EVIDENCE_REQUEST_20260928.md`,\n'
    '`eventx/release/v6/V6_RELAXED_CLASS_MAP_DRAFT_20260928.md`,\n'
    '`eventx/release/v6/V6_JEV_DEVELOPMENT_TRIAL_DRAFT_20260928.md`, and\n'
    '`data/v6/next_step_drafts_20260928/`. Next obtain the source receipts;\n'
    'then validate a new class policy on independent reference and assess yield.\n\n'
)
new = old.replace(anchor, anchor + addition, 1)
new = new.replace(
    'Next specify a prospective class map before any linker freeze or new audit,\nand obtain Lumid source receipts.',
    'A post-label development class-map draft now exists but is not audit-frozen;\nobtain Lumid source receipts before linker freeze or new audit.',
    1,
)

entry = (
    '\n### 28 September — V6 source request, relaxed map and Jev diagnostic drafts\n\n'
    '- Revised the unsent Lumid request with three exact June/July run UUIDs visible on EventX SQL/catalog, the current `scope_key=\'\'` cursor, exact five failed article clocks, and four later endpoint successor receipts. It asks the other analyst to align deployment/role/query time and Lumid for per-window historical completion, clean-zero and 15-market status/version receipts **at decision time**. The earlier 27 September request is preserved. No external message was sent. `eventx/release/v6/V6_LUMID_EVIDENCE_REQUEST_20260928.md`.\n'
    '- Wrote a post-label opened-development class-map draft, retaining the original strict primary reference. Across 102 adjudicated relaxed labels: 10 direct hypotheses, 16 material/shared-mechanism boundary cases, 20 shared-context hypotheses, one same-episode/context boundary case and 55 exclusions. These buckets are triage interpretations, not new human gold or independent validation; article/story concentration and source gates remain. Machine-readable map and hash manifest: `data/v6/next_step_drafts_20260928/`; interpretation: `eventx/release/v6/V6_RELAXED_CLASS_MAP_DRAFT_20260928.md`.\n'
    '- Prepared a separate TypeSafe Jev `jev-1.13.0` semantic-classification diagnostic on the fixed opened, score-blinded 102-pair packet. It preserves L0/L1/L2 and keeps clocks, market status, source completeness and forecast math in code. No TypeSafe/Jev key exists in project `.env`; no API call or article upload occurred. The 102 labels were already opened, so any later Jev readout is development only and cannot set an independent audit threshold. `eventx/release/v6/V6_JEV_DEVELOPMENT_TRIAL_DRAFT_20260928.md`.\n'
    '- No source/window certificate, model fit, independent audit, protected/consumed holdout access, or V4 change. V6 certified predictive support remains 0/8,844 contract-days.\n'
)

release.mkdir(parents=True, exist_ok=True)
artifact.mkdir(parents=True, exist_ok=False)
for name in names:
    shutil.copy2(here / name, release / name)
shutil.copy2(here / 'v6_class_map_draft_20260928.json', artifact / 'class_map.json')

def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

manifest = {
    'created_at_utc': datetime.now(timezone.utc).isoformat(),
    'status': 'draft_not_frozen_not_sent',
    'inputs': {
        'data/v6/relaxed_adjudication_20260927/development_labels_102.jsonl': sha(base / 'data/v6/relaxed_adjudication_20260927/development_labels_102.jsonl'),
        'data/v6/context_development_review_20260927/semantic_packet.jsonl': sha(base / 'data/v6/context_development_review_20260927/semantic_packet.jsonl'),
        'data/v6/cursor_successor_probe_20260928/report.json': sha(base / 'data/v6/cursor_successor_probe_20260928/report.json'),
    },
    'outputs': {
        **{f'eventx/release/v6/{name}': sha(release / name) for name in names},
        'data/v6/next_step_drafts_20260928/class_map.json': sha(artifact / 'class_map.json'),
    },
}
(artifact / 'manifest.json').write_text(json.dumps(manifest, indent=2, sort_keys=True) + '\n')
state.write_text(new)
with progress.open('a') as fh:
    fh.write(entry)
print(json.dumps({'outputs': list(manifest['outputs']), 'state_updated': True, 'progress_appended': True}, indent=2))
