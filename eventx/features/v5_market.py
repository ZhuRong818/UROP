"""Point-in-time market-only features for the EventX v5 baseline.

This module contains no news inputs.  It deliberately accepts the prediction-time
minute and scheduled-terminal metadata explicitly so the caller can audit that every
value was knowable at prediction time.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from sklearn.preprocessing import SplineTransformer


MARKET_FEATURE_NAMES = (
    "price_logodds",
    "momentum_5m",
    "momentum_30m",
    "momentum_120m",
    "realized_vol_30m",
    "realized_vol_240m",
    "log1p_trade_count_60m",
    "log1p_trade_count_240m",
    "log1p_notional_60m",
    "log1p_notional_240m",
    "log1p_minutes_since_trade",
    "venue_indicator",
    "log1p_minutes_to_scheduled_terminal",
    "terminal_unknown",
    "price_age_minutes",
)

# Low-complexity nonlinearities for price state, momentum, volatility, staleness and
# time to terminal. Count/notional inputs remain as prespecified log-linear terms.
NONLINEAR_COLUMNS = np.asarray((0, 1, 2, 3, 4, 5, 10, 12, 14), dtype=np.int64)


def market_values(
    raw_market_features: np.ndarray,
    market_index: np.ndarray,
    prediction_minute: np.ndarray,
    price_age_minutes: np.ndarray,
    terminal_minutes: np.ndarray,
    terminal_known: np.ndarray,
) -> np.ndarray:
    """Return the auditable 15-column B0-v5N market matrix.

    ``raw_market_features`` must contain the twelve frozen v4 B0 fields in their
    canonical order. Terminal time is treated as missing where it is unknown; a
    scheduled terminal before the prediction time is clipped to zero remaining time.
    """

    raw = np.asarray(raw_market_features, dtype=np.float64)
    markets = np.asarray(market_index, dtype=np.int64)
    minutes = np.asarray(prediction_minute, dtype=np.float64)
    ages = np.asarray(price_age_minutes, dtype=np.float64)
    terminal = np.asarray(terminal_minutes, dtype=np.float64)
    known_by_market = np.asarray(terminal_known, dtype=bool)
    if raw.ndim != 2 or raw.shape[1] < 12:
        raise ValueError("raw_market_features must have at least 12 columns")
    rows = raw.shape[0]
    if any(len(values) != rows for values in (markets, minutes, ages)):
        raise ValueError("row-aligned market inputs have inconsistent lengths")
    if len(terminal) != len(known_by_market):
        raise ValueError("terminal arrays have inconsistent lengths")
    if rows and (markets.min() < 0 or markets.max() >= len(terminal)):
        raise ValueError("market index is outside terminal metadata")

    known = known_by_market[markets]
    remaining = np.maximum(terminal[markets] - minutes, 0.0)
    remaining[~known] = 0.0
    values = raw[:, :12].copy()
    for column in (6, 7, 8, 9, 10):
        values[:, column] = np.log1p(np.maximum(values[:, column], 0.0))
    return np.column_stack(
        (
            values,
            np.log1p(remaining),
            (~known).astype(np.float64),
            np.maximum(ages, 0.0),
        )
    ).astype(np.float32)


@dataclass(frozen=True)
class MarketSplineBasis:
    """Training-fitted spline basis used by the direct B0-v5N candidate."""

    transformer: SplineTransformer
    linear_columns: np.ndarray

    def transform(self, values: np.ndarray) -> np.ndarray:
        matrix = np.asarray(values, dtype=np.float64)
        spline = self.transformer.transform(matrix[:, NONLINEAR_COLUMNS])
        return np.column_stack((matrix[:, self.linear_columns], spline))


def fit_market_spline_basis(
    training_values: np.ndarray,
) -> tuple[MarketSplineBasis, np.ndarray]:
    """Fit the frozen low-degree spline basis on training rows only."""

    matrix = np.asarray(training_values, dtype=np.float64)
    if matrix.ndim != 2 or matrix.shape[1] != len(MARKET_FEATURE_NAMES):
        raise ValueError("unexpected B0-v5N market matrix width")
    transformer = SplineTransformer(
        n_knots=4,
        degree=2,
        knots="quantile",
        extrapolation="linear",
        include_bias=False,
    )
    spline = transformer.fit_transform(matrix[:, NONLINEAR_COLUMNS])
    keep = np.ones(matrix.shape[1], dtype=bool)
    keep[NONLINEAR_COLUMNS] = False
    linear_columns = np.flatnonzero(keep)
    basis = MarketSplineBasis(transformer, linear_columns)
    return basis, np.column_stack((matrix[:, linear_columns], spline))
