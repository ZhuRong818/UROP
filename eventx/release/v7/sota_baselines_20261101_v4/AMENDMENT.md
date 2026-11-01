# Amendment v4 to sota_baselines_20261101 (compute only, before any baseline score)

- Event: Tier A TabICL crashed on MPS while predicting its first block in chunks of 20,000 rows
  (`RuntimeError: Invalid buffer size: 8.02 GiB`, `data/v7/sota_baselines_20261101/tier_a.log`). No TabICL or
  CatBoost output had been written; TabM and RealMLP outputs (all seven blocks) are kept unchanged.
- Change: TabICL predicts in chunks of 1,000 rows. In TabICL each query row attends only to the training context, so
  predictions do not depend on the chunk size. Model, checkpoint, ensemble, seed and all other rules are unchanged.
- Run: `python -m eventx.tasks.benchmark_v7_sota_baselines_20261101_v4 tier_a --models tabicl catboost`
  (the v1 tier_a skips blocks whose output files exist).
