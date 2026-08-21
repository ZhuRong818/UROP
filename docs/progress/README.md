# EventX progress-log index

`CURRENT_STATE.md` is the compact canonical startup handoff. It is the only progress
file that must be read at the start of routine EventX work.

Detailed history is stored separately:

- `PROGRESS.md`: legacy detailed archive through 21 August 2026;
- `docs/progress/2026-08.md`: dated updates after the compact-handoff migration; and
- future `docs/progress/YYYY-MM.md` files: append-only monthly history.

When material work occurs:

1. update current facts, integrity state, blockers and next actions in
   `CURRENT_STATE.md`;
2. append detailed evidence and artifact links to the current monthly file;
3. do not rewrite failed historical results;
4. keep large command output in dedicated JSON or reports rather than the handoff; and
5. read historical files only when the current task depends on them.

Frozen manifests and protocols remain authoritative over every progress document.
