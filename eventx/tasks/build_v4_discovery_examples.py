"""Build EventX v4 discovery examples with point-in-time news-quality features."""

from __future__ import annotations

from collections import Counter
from datetime import datetime, timezone
import json
import os
from pathlib import Path
from typing import Any

import numpy as np

from eventx.features.v4_news import MINUTE_US, trailing_event_features
from eventx.settings import REPO_ROOT
from eventx.tasks.build_v3_1_historical_development_examples import (
    EXAMPLE_DTYPE as V3_EXAMPLE_DTYPE,
    FEATURE_NAMES as V3_FEATURE_NAMES,
    sha256_file,
)
from eventx.tasks.prepare_v4_discovery_news_quality import EVENT_DTYPE


SOURCE_EXAMPLES = REPO_ROOT / "data/v3_1_historical/primary/development/examples.bin"
SOURCE_MANIFEST = REPO_ROOT / "data/v3_1_historical/primary/development/examples_manifest.json"
QUALITY_EVENTS = REPO_ROOT / "data/v4/discovery/prepared/news_quality_events.bin"
QUALITY_MANIFEST = REPO_ROOT / "data/v4/discovery/prepared/manifest.json"
OUTPUT = REPO_ROOT / "data/v4/discovery/examples"
EXAMPLES = OUTPUT / "examples.bin"
REPORT = OUTPUT / "report.json"
MANIFEST = OUTPUT / "manifest.json"
DEVELOPMENT_START_US = int(
    datetime(2026, 5, 17, tzinfo=timezone.utc).timestamp() * 1_000_000
)
WINDOWS = (60, 360, 1440)
QUALITY_FEATURE_NAMES = tuple(
    f"news_relevance_mass_{window}m" for window in WINDOWS
) + tuple(
    f"news_novel_relevance_mass_{window}m" for window in WINDOWS
) + tuple(
    f"news_distinct_publishers_{window}m" for window in WINDOWS
) + tuple(
    f"news_cross_publisher_reports_{window}m" for window in WINDOWS
)
FEATURE_NAMES = tuple(V3_FEATURE_NAMES) + QUALITY_FEATURE_NAMES
EXAMPLE_DTYPE = np.dtype(
    [
        ("market", "<u4"),
        ("minute", "<i4"),
        ("venue", "u1"),
        ("group", "u1"),
        ("label", "u1"),
        ("price_age", "<f4"),
        ("features", "<f4", (len(FEATURE_NAMES),)),
    ],
    align=False,
)


def relative(path: Path) -> str:
    return str(path.relative_to(REPO_ROOT))


def atomic_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n")
    os.replace(temporary, path)


def verify_manifest(path: Path) -> None:
    manifest = json.loads(path.read_text(encoding="utf-8"))
    for artifact in manifest.get("artifacts", []):
        artifact_path = REPO_ROOT / str(artifact["path"])
        if not artifact_path.is_file() or sha256_file(artifact_path) != str(
            artifact["sha256"]
        ):
            raise RuntimeError(f"hash-lock failure: {artifact_path}")


def offsets(values: np.ndarray, markets: int) -> np.ndarray:
    return np.searchsorted(
        values["market"], np.arange(markets + 1, dtype=np.uint32), side="left"
    )


def reordered_quality(interleaved: np.ndarray) -> np.ndarray:
    output = np.empty_like(interleaved)
    # trailing_event_features emits four measures per window. V4 stores complete
    # feature families contiguously so B2 is an exact prefix nested within B3.
    for measure in range(4):
        for window_index in range(len(WINDOWS)):
            output[:, measure * len(WINDOWS) + window_index] = interleaved[
                :, window_index * 4 + measure
            ]
    return output


def main() -> None:
    if any(path.exists() for path in (EXAMPLES, REPORT, MANIFEST)):
        raise SystemExit("v4 discovery example artifact already exists")
    verify_manifest(SOURCE_MANIFEST)
    verify_manifest(QUALITY_MANIFEST)
    source_count = SOURCE_EXAMPLES.stat().st_size // V3_EXAMPLE_DTYPE.itemsize
    event_count = QUALITY_EVENTS.stat().st_size // EVENT_DTYPE.itemsize
    source = np.memmap(
        SOURCE_EXAMPLES, mode="r", dtype=V3_EXAMPLE_DTYPE, shape=(source_count,)
    )
    events = np.memmap(
        QUALITY_EVENTS, mode="r", dtype=EVENT_DTYPE, shape=(event_count,)
    )
    market_count = int(max(source["market"].max(), events["market"].max())) + 1
    source_offsets = offsets(source, market_count)
    event_offsets = offsets(events, market_count)
    counters: Counter[str] = Counter()
    by_group: Counter[int] = Counter()
    by_venue: Counter[int] = Counter()
    OUTPUT.mkdir(parents=True, exist_ok=True)
    temporary = EXAMPLES.with_suffix(EXAMPLES.suffix + ".tmp")
    with temporary.open("wb") as handle:
        for market in range(market_count):
            rows = source[source_offsets[market] : source_offsets[market + 1]]
            rows = rows[rows["price_age"] <= 30.0]
            if not len(rows):
                continue
            market_events = events[event_offsets[market] : event_offsets[market + 1]]
            grid_us = DEVELOPMENT_START_US + np.asarray(
                rows["minute"], dtype=np.int64
            ) * MINUTE_US
            interleaved = trailing_event_features(
                np.asarray(market_events["timestamp_us"], dtype=np.int64),
                np.asarray(market_events["relevance"], dtype=np.float32),
                np.asarray(market_events["novelty"], dtype=np.float32),
                np.asarray(market_events["publisher"], dtype=np.uint16),
                np.asarray(
                    market_events["diffusion_publishers"] >= 2, dtype=np.uint8
                ),
                grid_us,
                WINDOWS,
            )
            quality = reordered_quality(interleaved)
            output = np.empty(len(rows), dtype=EXAMPLE_DTYPE)
            for field in ("market", "minute", "venue", "group", "label", "price_age"):
                output[field] = rows[field]
            output["features"][:, : len(V3_FEATURE_NAMES)] = rows["features"]
            output["features"][:, len(V3_FEATURE_NAMES) :] = quality
            if not np.all(np.isfinite(output["features"])):
                raise RuntimeError(f"nonfinite v4 feature for market {market}")
            output.tofile(handle)
            counters["rows"] += len(output)
            counters["positives"] += int(output["label"].sum())
            counters["markets_with_rows"] += 1
            counters["rows_with_news_1440m"] += int(
                np.sum(output["features"][:, 14] > 0)
            )
            counters["rows_with_cross_publisher_news_1440m"] += int(
                np.sum(output["features"][:, -1] > 0)
            )
            by_group[int(output["group"][0])] += len(output)
            by_venue[int(output["venue"][0])] += len(output)
            if (market + 1) % 250 == 0:
                print(
                    f"v4 examples {market + 1}/{market_count}; rows={counters['rows']}",
                    flush=True,
                )
    os.replace(temporary, EXAMPLES)
    report = {
        "protocol_id": "eventx-v4-confirmatory-20260902",
        "created_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "status": "discovery_examples_built",
        "historical_interval_outcomes_previously_opened": True,
        "future_confirmatory_holdout_read": False,
        "primary_price_freshness_minutes": 30,
        "rows": counters["rows"],
        "positives": counters["positives"],
        "prevalence": counters["positives"] / counters["rows"],
        "markets_with_rows": counters["markets_with_rows"],
        "rows_with_news_1440m": counters["rows_with_news_1440m"],
        "rows_with_cross_publisher_news_1440m": counters[
            "rows_with_cross_publisher_news_1440m"
        ],
        "rows_by_group": dict(sorted(by_group.items())),
        "rows_by_venue": {"kalshi": by_venue[0], "polymarket": by_venue[1]},
        "nested_feature_families": {
            "b0_market": list(FEATURE_NAMES[:12]),
            "b1_market_plus_volume": list(FEATURE_NAMES[:16]),
            "b2_plus_relevance_novelty": list(FEATURE_NAMES[:22]),
            "b3_plus_cross_publisher_diffusion": list(FEATURE_NAMES),
        },
        "feature_names": list(FEATURE_NAMES),
        "dtype": EXAMPLE_DTYPE.descr,
        "artifact": {
            "path": relative(EXAMPLES),
            "bytes": EXAMPLES.stat().st_size,
            "sha256": sha256_file(EXAMPLES),
        },
        "inputs": [
            {"path": relative(path), "sha256": sha256_file(path)}
            for path in (SOURCE_EXAMPLES, QUALITY_EVENTS)
        ],
    }
    atomic_json(REPORT, report)
    atomic_json(
        MANIFEST,
        {
            "protocol_id": report["protocol_id"],
            "status": report["status"],
            "artifacts": [
                {"path": relative(path), "sha256": sha256_file(path)}
                for path in (EXAMPLES, REPORT, Path(__file__).resolve())
            ],
            "inputs": report["inputs"],
        },
    )
    print(json.dumps({
        "status": report["status"],
        "rows": report["rows"],
        "positives": report["positives"],
        "prevalence": report["prevalence"],
        "markets_with_rows": report["markets_with_rows"],
        "rows_with_news_1440m": report["rows_with_news_1440m"],
        "rows_with_cross_publisher_news_1440m": report[
            "rows_with_cross_publisher_news_1440m"
        ],
    }, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
