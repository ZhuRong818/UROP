"""Synthetic contract tests for the v3.1 historical-holdout path."""

from __future__ import annotations

from datetime import timedelta

import numpy as np

from eventx.tasks.build_v3_1_historical_holdout_examples import (
    HOLDOUT_END,
    HOLDOUT_START,
    holdout_market_examples,
)
from eventx.tasks.evaluate_v3_1_historical_holdout import predict_frozen
from eventx.tasks.prepare_v3_1_historical_development_arrays import (
    TRADE_DTYPE,
    timestamp_us,
)


def synthetic_trades(include_future_append: bool = False) -> np.ndarray:
    times = [
        HOLDOUT_START - timedelta(minutes=240) + timedelta(minutes=5 * index)
        for index in range(80)
    ]
    if include_future_append:
        times.append(HOLDOUT_END + timedelta(minutes=5))
    rows = np.empty(len(times), dtype=TRADE_DTYPE)
    for index, value in enumerate(times):
        price = 0.4 + 0.002 * (index % 11)
        if index in {52, 61}:
            price += 0.08
        rows[index] = (0, timestamp_us(value), price, 10.0, index)
    return rows


def main() -> None:
    market = {
        "market_index": 0,
        "market_group": 2,
        "venue": "kalshi",
        "first_trade_ts": (HOLDOUT_START - timedelta(days=2)).isoformat(),
        "terminal_time": None,
    }
    baseline = holdout_market_examples(market, synthetic_trades())
    appended = holdout_market_examples(market, synthetic_trades(True))
    if not len(baseline):
        raise AssertionError("synthetic holdout produced no eligible rows")
    if not np.array_equal(baseline, appended):
        raise AssertionError("future append changed sealed holdout examples")
    if int(baseline["minute"].min()) < 0:
        raise AssertionError("warmup rows leaked into the holdout output")
    if not np.all(baseline["features"][:, 12:] == 0.0):
        raise AssertionError("B0 holdout unexpectedly materialized news features")

    candidate = {
        "candidate": "b0",
        "model": {
            "feature_names": [f"x{index}" for index in range(12)],
            "means": [0.0] * 12,
            "scales": [1.0] * 12,
            "models": [
                {
                    "seed": 11,
                    "coefficients": [0.1] + [0.0] * 11,
                    "intercept": -1.0,
                },
                {
                    "seed": 23,
                    "coefficients": [0.2] + [0.0] * 11,
                    "intercept": -1.1,
                },
                {
                    "seed": 47,
                    "coefficients": [0.3] + [0.0] * 11,
                    "intercept": -1.2,
                },
            ],
        },
    }
    scores = predict_frozen(candidate, baseline)
    if not np.all(np.isfinite(scores)) or not np.all((scores > 0.0) & (scores < 1.0)):
        raise AssertionError("frozen holdout prediction contract failed")
    print("v3.1 synthetic historical-holdout tests passed")


if __name__ == "__main__":
    main()
