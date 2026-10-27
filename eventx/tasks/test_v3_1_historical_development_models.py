"""Synthetic contract tests for the v3.1 fixed learner and bootstrap."""

from __future__ import annotations

import numpy as np

from eventx.tasks.build_v3_1_historical_development_examples import EXAMPLE_DTYPE
from eventx.tasks.run_v3_1_historical_development_models import (
    OOF_DTYPE,
    brier_block_bootstrap,
    fit_seed,
    metrics,
    predict,
    scaler,
)


def main() -> None:
    rng = np.random.default_rng(90210)
    count = 2400
    examples = np.empty(count, dtype=EXAMPLE_DTYPE)
    examples["market"] = np.repeat(np.arange(24, dtype=np.uint32), 100)
    examples["minute"] = np.tile(np.arange(100, dtype=np.int32) * 5, 24)
    examples["venue"] = np.repeat(np.arange(24) % 2, 100)
    examples["group"] = np.repeat(np.arange(24) % 5, 100)
    features = rng.normal(size=(count, 16)).astype(np.float32)
    for column in (6, 7, 8, 9, 12, 13, 14):
        features[:, column] = rng.poisson(3.0, size=count)
    latent = features[:, 0] + 0.8 * features[:, 12] - 2.3
    probability = 1.0 / (1.0 + np.exp(-latent))
    examples["label"] = rng.binomial(1, probability).astype(np.uint8)
    examples["price_age"] = rng.uniform(0, 120, size=count)
    examples["features"] = features
    indices = np.arange(count, dtype=np.int64)
    means, scales = scaler(examples, indices, 16)
    if not np.all(np.isfinite(means)) or not np.all(scales > 0.0):
        raise AssertionError("training-only scaler is invalid")
    model = fit_seed(examples, indices, 16, means, scales, 11, "synthetic")
    scores = predict(model, examples, indices, 16, means, scales)
    result = metrics(examples["label"], scores)
    if not np.all((scores > 0.0) & (scores < 1.0)):
        raise AssertionError("logistic probabilities left the open unit interval")
    if result["average_precision"] is None or result["average_precision"] <= float(
        examples["label"].mean()
    ):
        raise AssertionError("fixed learner did not recover synthetic signal")

    oof = np.empty(count, dtype=OOF_DTYPE)
    oof["market"] = examples["market"]
    oof["minute"] = examples["minute"]
    oof["venue"] = examples["venue"]
    oof["fold"] = 1
    oof["label"] = examples["label"]
    prevalence = float(examples["label"].mean())
    oof["b0"] = prevalence
    oof["b1"] = scores.astype(np.float32)
    oof["price_age"] = examples["price_age"]
    oof["news_1440"] = examples["features"][:, 14]
    oof.sort(order=("market", "minute"), kind="quicksort")
    bootstrap = brier_block_bootstrap(oof)
    if bootstrap["samples"] != 5000 or bootstrap["mean"] <= 0.0:
        raise AssertionError("paired circular Brier bootstrap contract failed")
    print("v3.1 synthetic learner/bootstrap tests passed")


if __name__ == "__main__":
    main()
