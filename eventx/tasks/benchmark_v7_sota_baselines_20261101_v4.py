"""Compute-only amendment v4 of the SOTA baseline benchmark (before any baseline score).

TabICL crashed on MPS predicting the first block in chunks of 20,000 query rows ("Invalid buffer size: 8.02 GiB" in
scaled_dot_product_attention); no TabICL output was written. TabICL's query rows attend only to the training context,
not to each other, so the chunk size does not change any prediction. v4 predicts TabICL in chunks of 1,000 rows; all
other rules are v1-v3 unchanged. See eventx/release/v7/sota_baselines_20261101_v4/AMENDMENT.md.
"""
import argparse

import eventx.tasks.benchmark_v7_sota_baselines_20261101_v2  # noqa: F401  (TabICL without kv cache)
import eventx.tasks.benchmark_v7_sota_baselines_20261101 as v1

_predict = v1.predict


def predict(model, x, chunk=20000):
    return _predict(model, x, 1000 if type(model).__name__ == 'TabICLClassifier' else chunk)


v1.predict = predict

if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('phase', choices=['tier_a'])
    ap.add_argument('--models', nargs='*', default=['tabicl', 'catboost'])
    v1.tier_a(ap.parse_args().models)
