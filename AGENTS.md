# Repository agent instructions

These instructions apply to the entire repository.

## Mandatory startup

Before planning, answering project-status questions, editing code, fetching data, or
running an evaluation:

1. Read `CURRENT_STATE.md` completely.
2. Treat its active objective, integrity state, blockers, locked decisions and next
   actions as the canonical project handoff.
3. Inspect the linked frozen artifact for any metric or decision that materially
   affects the requested task.
4. Read `PROGRESS.md` or `docs/progress/YYYY-MM.md` only when the task requires
   historical detail not present in the compact handoff.
5. Check for a consumption receipt before touching a test or holdout.
6. If `CURRENT_STATE.md` conflicts with a frozen artifact, trust the artifact, stop
   the conflicting action, and correct `CURRENT_STATE.md`.

## Progress maintenance

After any material change, update `CURRENT_STATE.md` in the same task and append the
detailed evidence to the current `docs/progress/YYYY-MM.md` file. Material changes
include:

- a completed or failed data fetch;
- a new dataset, feature, association-rule, or model version;
- a validation, bootstrap, diagnostic, freeze, or final evaluation;
- a changed decision, blocker, integrity state, or next step;
- a long-running job starting, stopping, failing, or completing.

Use exact values from canonical artifacts. Append history rather than erasing failed
experiments. Keep detailed output in JSON or dedicated reports and link it from the
monthly log. Keep `CURRENT_STATE.md` compact—preferably below 200 lines—by moving stale
narrative to the monthly log while preserving current integrity facts and links.

`PROGRESS.md` is the legacy detailed archive through 2026-08-21. Do not append new
routine updates to it.

## Evaluation integrity

- The OOT holdout `eventx-oot-7c4fd487edb3928b9253` is consumed.
- Do not rerun `eventx.tasks.run_frozen_b0_oot_final`.
- Do not tune any model, feature, association rule, eligibility rule, or hyperparameter
  from the OOT result.
- The original v1 test block was previously exposed by a noncanonical B0 and must not
  be described as untouched.
- Do not modify files whose hashes are locked in frozen manifests. Create a new version
  and manifest when a research cycle legitimately continues.

## Working rules

- Preserve unrelated user changes in the dirty worktree.
- Keep secrets in `.env`; never place tokens or credentials in progress files, reports,
  source code, or command output.
- When reporting current fetch status, verify the process/checkpoint state rather than
  relying on an older conversational update.
- Do not begin v2 data collection or model selection unless the user explicitly starts
  that new research cycle.
