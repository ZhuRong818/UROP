# Amendment v3 to sota_baselines_20261101 (before any baseline score)

Requested by the user on 2 Nov 2026 (local time): "continue, and add Sundial and Time-MoE too".

1. **Tier B2/B3 added.** Sundial (Liu et al., ICML 2025 oral; `thuml/sundial-base-128m`) and Time-MoE (Shi et al.,
   ICLR 2025 spotlight; `Maple728/TimeMoE-50M`), zero-shot, on the same matured-outcome series as Moirai-MoE. Their
   model-hub code was downloaded to `.hf_remote/` and read before use: it imports only torch and transformers and
   does no file, network or process I/O. Hashes of every code and weight file are in this manifest. Run with
   transformers 4.40.1 (the version the code targets) in `.venv-ts`.
2. **Missing context values** are replaced by the mean of the observed values in the same context (neither model
   accepts missing values); a context with no observed value uses the stored global rate.
3. **Population for B2/B3:** the nonoverlapping half-hour grid (t mod 1,800 = 0) of all seven blocks, because of
   measured inference cost (Sundial ~0.1 s/row on MPS with 20 samples; Time-MoE ~0.16 s/row on CPU in float32; ~510k
   rows would take more than a day). Moirai-MoE (still scored on all rows under v1), the online rate and the stack
   are also reported on exactly these rows.
4. **Tier C compute bound:** TabM and RealMLP train on a seeded random 100,000-row subsample of the six-block
   training rows (TabM needed ~800 s for 9,212 rows on this host's CPU). seg_hgb used all rows; this favours seg_hgb.

No timing above used an evaluation row: TabICL, TabM, RealMLP and CatBoost were timed on the 9,212 training rows,
and Sundial and Time-MoE on synthetic series. Tier A and Moirai-MoE had started under v1/v2 when this amendment was
written; their outputs are untouched by it and none had been scored.
