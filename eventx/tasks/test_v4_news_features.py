"""Synthetic integrity tests for the frozen EventX v4 news features."""

from __future__ import annotations

import json

import numpy as np

from eventx.features.v4_news import (
    MINUTE_US,
    market_relative_novelty,
    normalized_headline,
    story_diffusion_counts,
    trailing_event_features,
)


def main() -> None:
    assert normalized_headline("Fed: Cuts  Rates?!") == "fed cuts rates"

    timestamps = np.asarray([10, 20, 30, 1500], dtype=np.int64) * MINUTE_US
    headlines = [
        "Federal Reserve cuts interest rates today",
        "Federal Reserve cuts interest rates today",
        "Different sufficiently long market headline",
        "Federal Reserve cuts interest rates today",
    ]
    publishers = ["Reuters", "AP", "Reuters", "Bloomberg"]
    reports, publishers_seen = story_diffusion_counts(
        timestamps, headlines, publishers, window_minutes=1440
    )
    assert reports.tolist() == [1, 2, 1, 1]
    assert publishers_seen.tolist() == [1, 2, 1, 1]

    vectors = np.asarray(
        [[1.0, 0.0], [1.0, 0.0], [0.0, 1.0], [1.0, 0.0]],
        dtype=np.float32,
    )
    novelty = market_relative_novelty(
        timestamps, vectors, prior_documents=20, window_minutes=1440
    )
    assert np.allclose(novelty, [1.0, 0.0, 1.0, 1.0])

    grids = np.asarray([20, 30, 31], dtype=np.int64) * MINUTE_US
    relevance = np.asarray([0.8, 0.6, 0.2], dtype=np.float32)
    event_novelty = np.asarray([1.0, 0.5, 1.0], dtype=np.float32)
    publisher_ids = np.asarray([1, 2, 1], dtype=np.uint16)
    diffused = np.asarray([0, 1, 0], dtype=np.uint8)
    features = trailing_event_features(
        timestamps[:3],
        relevance,
        event_novelty,
        publisher_ids,
        diffused,
        grids,
        windows_minutes=(10,),
    )
    # (t-window, t]: at t=20 the event at minute 10 is excluded.
    assert np.allclose(features[0], [0.6, 0.3, 1.0, 1.0])
    assert np.allclose(features[1], [0.2, 0.2, 1.0, 0.0])
    assert np.allclose(features[2], [0.2, 0.2, 1.0, 0.0])

    future_timestamp = np.asarray([10_000], dtype=np.int64) * MINUTE_US
    appended = trailing_event_features(
        np.concatenate((timestamps[:3], future_timestamp)),
        np.concatenate((relevance, np.asarray([1.0], dtype=np.float32))),
        np.concatenate((event_novelty, np.asarray([1.0], dtype=np.float32))),
        np.concatenate((publisher_ids, np.asarray([3], dtype=np.uint16))),
        np.concatenate((diffused, np.asarray([1], dtype=np.uint8))),
        grids,
        windows_minutes=(10,),
    )
    assert np.array_equal(features, appended), "future append changed past features"

    print(json.dumps({
        "status": "passed",
        "tests": [
            "normalization",
            "point_in_time_story_diffusion",
            "market_relative_novelty",
            "open_left_closed_right_windows",
            "future_append_invariance",
        ],
    }, indent=2))


if __name__ == "__main__":
    main()
