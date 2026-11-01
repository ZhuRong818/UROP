# Amendment v2 to sota_baselines_20261101 (compute only, before any baseline score)

- Change: TabICL `kv_cache=True` -> `kv_cache=False`. Nothing else changes.
- Reason: timed on the 9,212 training rows only (no evaluation row was predicted or scored), TabICL ran at about
  66 ms/row with the cache on this host's MPS device versus about 17 ms/row without it; the cached run would take
  ~9 h for the ~510k evaluation rows and would not finish before the 3 Nov report deadline.
- The cache stores the training context's keys and values; the model, checkpoint (`tabicl-classifier-v1-20250208`),
  ensemble size and seed are unchanged.
- The v1 runner and manifest stay unmodified; `eventx/tasks/benchmark_v7_sota_baselines_20261101_v2.py` imports v1
  and overrides only `tabular('tabicl')`. All phases are run through the v2 entry point.
