"""Synthetic, outcome-free verification of the frozen v4 holdout pipeline."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
import json
from pathlib import Path
import tempfile

import numpy as np

from eventx.tasks.audit_v4_confirmatory_collection import validate_artifact
from eventx.tasks.build_v4_confirmatory_examples import market_examples
from eventx.tasks.evaluate_v4_confirmatory import frozen_predict, two_level_bootstrap
from eventx.tasks.prepare_v3_1_historical_development_arrays import TRADE_DTYPE, sha256_file
from eventx.tasks.prepare_v4_discovery_news_quality import EVENT_DTYPE


def synthetic_market_builder() -> None:
    start = datetime(2030, 1, 1, tzinfo=timezone.utc)
    end = start + timedelta(hours=8)
    rows = []
    for ordinal, minute in enumerate(range(0, 500, 10), start=1):
        price = 0.50 + (0.001 if ordinal % 2 else -0.001)
        if minute >= 220:
            price += 0.12
        rows.append((0, int((start + timedelta(minutes=minute)).timestamp() * 1_000_000), price, 12.0, ordinal))
    trades = np.asarray(rows, dtype=TRADE_DTYPE)
    events = np.empty(0, dtype=EVENT_DTYPE)
    market = {"market_index": 0, "market_group": 2, "terminal_time": (end + timedelta(days=1)).isoformat()}
    baseline = market_examples(market, trades, events, start=start, end=end)
    assert len(baseline) > 0
    assert np.any(baseline["label"] == 1)
    assert np.any(baseline["trade_arrival"] == 1)
    assert np.all(baseline["price_age"] <= 60.0)
    appended = np.concatenate((trades, np.asarray([(
        0,
        int((end + timedelta(hours=2)).timestamp() * 1_000_000),
        0.95,
        500.0,
        len(rows) + 1,
    )], dtype=TRADE_DTYPE)))
    repeated = market_examples(market, appended, events, start=start, end=end)
    assert np.array_equal(baseline, repeated), "post-window trade changed prior rows"


def synthetic_model_application() -> None:
    features = np.zeros((3, 28), dtype=np.float32)
    features[:, 0] = (-1.0, 0.0, 1.0)
    model = {
        "models": {
            "b0": {
                "means": [0.0] * 12,
                "scales": [1.0] * 12,
                "models": [
                    {"intercept": 0.25, "coefficients": [2.0] + [0.0] * 11},
                    {"intercept": 0.25, "coefficients": [2.0] + [0.0] * 11},
                ],
            }
        }
    }
    expected = 1.0 / (1.0 + np.exp(-np.asarray([-1.75, 0.25, 2.25])))
    assert np.allclose(frozen_predict(features, model, "b0"), expected)


def synthetic_bootstrap() -> None:
    markets = np.repeat(np.arange(8, dtype=np.uint32), 200)
    minutes = np.tile(np.arange(0, 1000, 5, dtype=np.int32), 8)
    values = np.full(len(markets), 0.002, dtype=np.float64)
    first = two_level_bootstrap(markets, minutes, values, samples=200, seed=61)
    second = two_level_bootstrap(markets, minutes, values, samples=200, seed=61)
    assert first == second
    assert abs(first["mean"] - 0.002) < 1e-12
    assert first["ci_95_lower"] > 0.0


def synthetic_collection_receipt() -> None:
    with tempfile.TemporaryDirectory() as directory:
        root = Path(directory)
        data, sql, receipt = root / "data.jsonl", root / "query.sql", root / "receipt.json"
        data.write_text('{"x":1}\n', encoding="utf-8")
        sql.write_text("SELECT 1\n", encoding="utf-8")
        receipt.write_text(json.dumps({
            "data_sha256": sha256_file(data),
            "sql_sha256": sha256_file(sql),
            "receipt": {"rowcount": 1},
        }), encoding="utf-8")
        count, _value = validate_artifact(data, sql, receipt)
        assert count == 1


def main() -> None:
    synthetic_market_builder()
    synthetic_model_application()
    synthetic_bootstrap()
    synthetic_collection_receipt()
    print(json.dumps({
        "status": "passed",
        "checks": [
            "label_and_trade_arrival_construction",
            "future_append_invariance",
            "frozen_model_application",
            "two_level_bootstrap_determinism",
            "sealed_partition_receipt_validation",
        ],
        "real_future_holdout_read": False,
    }, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
