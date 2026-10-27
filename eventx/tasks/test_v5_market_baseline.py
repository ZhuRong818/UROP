"""Synthetic integrity tests for the EventX B0-v5N market baseline."""

from __future__ import annotations

import json

import numpy as np

from eventx.features.v5_market import (
    MARKET_FEATURE_NAMES,
    fit_market_spline_basis,
    market_values,
)


def synthetic_values(rows: int = 12) -> tuple[np.ndarray, ...]:
    raw = np.zeros((rows, 12), dtype=np.float64)
    raw[:, 0] = np.linspace(-2.0, 2.0, rows)
    raw[:, 1:6] = np.arange(rows * 5, dtype=np.float64).reshape(rows, 5) / 20.0
    raw[:, 6:11] = np.arange(rows * 5, dtype=np.float64).reshape(rows, 5)
    raw[:, 11] = np.arange(rows) % 2
    market = np.arange(rows) % 2
    minute = np.arange(rows, dtype=np.float64) * 5.0
    price_age = np.arange(rows, dtype=np.float64)
    terminal = np.asarray([100.0, 0.0])
    terminal_known = np.asarray([True, False])
    return raw, market, minute, price_age, terminal, terminal_known


def main() -> None:
    checks: dict[str, bool] = {}
    inputs = synthetic_values()
    values = market_values(*inputs)
    checks["canonical_width"] = values.shape == (12, len(MARKET_FEATURE_NAMES))

    # Known terminal time is converted to decreasing point-in-time time remaining.
    known_rows = inputs[1] == 0
    expected = np.log1p(np.maximum(100.0 - inputs[2][known_rows], 0.0))
    checks["terminal_time_point_in_time"] = bool(
        np.allclose(values[known_rows, 12], expected)
        and np.all(values[known_rows, 13] == 0.0)
    )
    unknown_rows = ~known_rows
    checks["unknown_terminal_encoded"] = bool(
        np.all(values[unknown_rows, 12] == 0.0)
        and np.all(values[unknown_rows, 13] == 1.0)
    )

    # Appending later rows cannot alter already-computed market features.
    prefix_inputs = tuple(value[:8] if value.ndim else value for value in inputs[:4])
    prefix = market_values(*prefix_inputs, inputs[4], inputs[5])
    checks["feature_future_append_invariance"] = bool(
        np.array_equal(prefix, values[:8])
    )

    # The spline basis is fitted once on training rows and reused unchanged.
    basis, train_transformed = fit_market_spline_basis(values[:8])
    before = basis.transform(values[8:10])
    after_future_append = basis.transform(values[8:12])[:2]
    checks["training_only_basis_invariance"] = bool(
        np.array_equal(before, after_future_append)
        and train_transformed.shape[0] == 8
    )

    try:
        market_values(*synthetic_values()[:1], *(np.asarray([], dtype=float),) * 5)
    except ValueError:
        checks["shape_validation"] = True
    else:
        checks["shape_validation"] = False

    if not all(checks.values()):
        raise AssertionError({key: value for key, value in checks.items() if not value})
    print(json.dumps({"status": "passed", "checks": checks}, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
