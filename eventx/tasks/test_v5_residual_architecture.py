"""Synthetic integrity tests for the EventX v5 residual-news primitives."""

from __future__ import annotations

import json

import numpy as np

from eventx.features.v5_residual import (
    MINUTE_US,
    gated_residual_probability,
    logit,
    online_story_stages,
)


def main() -> None:
    checks: dict[str, bool] = {}

    baseline = np.asarray([0.1, 0.2, 0.7, 0.9], dtype=np.float64)
    exposed = np.asarray([False, True, False, True])
    correction = np.asarray([100.0, 0.5, -100.0, -0.5])
    combined = gated_residual_probability(baseline, exposed, correction, 0.25)
    checks["unexposed_exact_equality"] = bool(
        np.array_equal(combined[~exposed], baseline[~exposed])
    )
    expected = 1.0 / (
        1.0 + np.exp(-(logit(baseline[exposed]) + 0.25 * correction[exposed]))
    )
    checks["exposed_formula"] = bool(
        np.allclose(combined[exposed], expected, atol=1e-14, rtol=0)
    )
    checks["zero_shrinkage_returns_baseline"] = bool(
        np.array_equal(
            gated_residual_probability(baseline, exposed, correction, 0.0),
            baseline,
        )
    )

    times = np.asarray([0, 1, 2, 3], dtype=np.int64) * MINUTE_US
    headline = "Central bank announces a major interest rate decision"
    stages = online_story_stages(
        times,
        [headline, headline, headline, headline],
        ["Publisher A", "Publisher A", "Publisher B", "Publisher C"],
    )
    checks["lifecycle_sequence"] = bool(
        np.array_equal(stages, np.asarray([1, 2, 3, 4], dtype=np.uint8))
    )
    prefix = online_story_stages(
        times[:2],
        [headline, headline],
        ["Publisher A", "Publisher A"],
    )
    checks["future_append_invariance"] = bool(np.array_equal(prefix, stages[:2]))
    expired = online_story_stages(
        np.asarray([0, 1441], dtype=np.int64) * MINUTE_US,
        [headline, headline],
        ["Publisher A", "Publisher B"],
    )
    checks["open_left_window_expiry"] = bool(
        np.array_equal(expired, np.asarray([1, 1], dtype=np.uint8))
    )

    try:
        gated_residual_probability(baseline, exposed, correction, 1.1)
    except ValueError:
        checks["invalid_shrinkage_rejected"] = True
    else:
        checks["invalid_shrinkage_rejected"] = False

    if not all(checks.values()):
        raise AssertionError({key: value for key, value in checks.items() if not value})
    print(json.dumps({"status": "passed", "checks": checks}, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
