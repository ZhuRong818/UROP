"""Synthetic contract tests for v3.1 point-in-time example construction."""

from __future__ import annotations

import numpy as np

from eventx.tasks.build_v3_1_historical_development_examples import (
    DEVELOPMENT_START,
    FEATURE_NAMES,
    MINUTE_US,
    NEWS_DTYPE,
    TRADE_DTYPE,
    market_examples,
)


def at_minute(value: int, seconds: int = 0) -> int:
    return int(DEVELOPMENT_START.timestamp() * 1_000_000) + value * MINUTE_US + seconds * 1_000_000


def main() -> None:
    trades = np.array(
        [
            (0, at_minute(0), 0.40, 50.0, 1),
            (0, at_minute(1), 0.40, 50.0, 2),
            (0, at_minute(2), 0.40, 50.0, 3),
            (0, at_minute(60, 1), 0.60, 50.0, 4),
            (0, at_minute(90), 0.70, 50.0, 5),
            (0, at_minute(241), 0.70, 50.0, 6),
        ],
        dtype=TRADE_DTYPE,
    )
    news = np.array(
        [(0, at_minute(30)), (0, at_minute(60, 1)), (0, at_minute(61))],
        dtype=NEWS_DTYPE,
    )["timestamp_us"]
    market = {
        "market_index": 0,
        "market_group": 3,
        "venue": "kalshi",
        "terminal_time": None,
    }
    rows = market_examples(market, trades, news)
    by_minute = {int(row["minute"]): row for row in rows}
    if 30 not in by_minute or 60 not in by_minute:
        raise AssertionError("expected eligible synthetic grid rows")
    at_60 = by_minute[60]
    features = at_60["features"]
    if not np.isclose(features[FEATURE_NAMES.index("price_logodds")], np.log(0.4 / 0.6)):
        raise AssertionError("trade later within the minute leaked into boundary price")
    if int(features[FEATURE_NAMES.index("trade_count_60m")]) != 2:
        raise AssertionError("left-open 60-minute trade window changed")
    if int(features[FEATURE_NAMES.index("news_article_count_60m")]) != 1:
        raise AssertionError("future within-minute news leaked into the grid boundary")
    if int(features[FEATURE_NAMES.index("news_article_count_360m")]) != 1:
        raise AssertionError("news history count changed")
    future_news = np.append(news, at_minute(1000)).astype(np.int64)
    future_rows = market_examples(market, trades, future_news)
    future_at_60 = {int(row["minute"]): row for row in future_rows}[60]
    if not np.array_equal(at_60["features"], future_at_60["features"]):
        raise AssertionError("future appended news changed an earlier feature row")
    terminal_market = {**market, "terminal_time": "2026-05-17T01:10:00Z"}
    terminal_rows = market_examples(terminal_market, trades, news)
    if any(int(row["minute"]) > 40 for row in terminal_rows):
        raise AssertionError("known terminal horizon exclusion failed")
    contradicted = {**market, "terminal_time": "2026-05-16T00:00:00Z"}
    contradicted_rows = market_examples(contradicted, trades, news)
    if len(contradicted_rows) != len(rows):
        raise AssertionError("contradicted pre-trade terminal was not ignored")
    print("v3.1 synthetic point-in-time example tests passed")


if __name__ == "__main__":
    main()
