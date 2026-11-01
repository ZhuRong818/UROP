"""Compute-only amendment of benchmark_v7_sota_baselines_20261101 (made before any baseline score).

TabICL with kv_cache=True ran at ~66 ms/row on this host's MPS device versus ~17 ms/row without it (timed on the 9,212
training rows only), which would not finish before the report deadline. kv_cache only caches the training-context
keys/values; it does not change the model, checkpoint or ensemble. Everything else is the frozen v1 protocol, imported
unchanged. See eventx/release/v7/sota_baselines_20261101_v2/AMENDMENT.md.
"""
import eventx.tasks.benchmark_v7_sota_baselines_20261101 as v1
from eventx.tasks.benchmark_v7_sota_baselines_20261101 import *  # noqa: F401,F403

_tabular = v1.tabular


def tabular(name):
    if name == 'tabicl':
        from tabicl import TabICLClassifier
        return TabICLClassifier(checkpoint_version='tabicl-classifier-v1-20250208.ckpt', device='mps', random_state=v1.SEED,
                                kv_cache=False)
    return _tabular(name)


v1.tabular = tabular

if __name__ == '__main__':
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument('phase', choices=['tier_a', 'tier_b_inputs', 'tier_b_forecast', 'tier_c', 'evaluate'])
    ap.add_argument('--models', nargs='*', default=None)
    a = ap.parse_args()
    if a.phase == 'tier_a':
        v1.tier_a(a.models or ['tabm', 'realmlp', 'tabicl', 'catboost'])
    elif a.phase == 'tier_c':
        v1.tier_c(a.models or ['tabm', 'realmlp'])
    else:
        getattr(v1, a.phase)()
