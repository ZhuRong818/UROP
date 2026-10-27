"""Frozen, reusable EventX v4 point-in-time news feature primitives."""

from __future__ import annotations

from collections import Counter, deque
import re
from typing import Iterable

import numpy as np


TOKEN = re.compile(r"[a-z0-9]+", re.IGNORECASE)
MINUTE_US = 60 * 1_000_000


def normalized_headline(value: str) -> str:
    """Return the conservative exact-story key used for diffusion proxies."""

    return " ".join(TOKEN.findall(value.lower()))


def normalized_publisher(value: str) -> str:
    """Normalize case and whitespace without attempting subjective entity merges."""

    return " ".join(value.lower().split())


def story_diffusion_counts(
    timestamps_us: np.ndarray,
    headlines: list[str],
    publishers: list[str],
    window_minutes: int = 1440,
) -> tuple[np.ndarray, np.ndarray]:
    """Count prior-and-current exact-headline reports and publishers point in time.

    Inputs may be in arbitrary order. A report at time ``t`` sees only reports with
    timestamps in ``(t-window, t]``. Rows sharing a timestamp are processed in a
    deterministic input-index order and may see earlier same-time rows, which is
    safe because all such reports are available at the prediction time.
    """

    count = len(timestamps_us)
    if len(headlines) != count or len(publishers) != count:
        raise ValueError("diffusion inputs have different lengths")
    if window_minutes <= 0:
        raise ValueError("window_minutes must be positive")
    reports = np.ones(count, dtype=np.uint16)
    distinct = np.ones(count, dtype=np.uint16)
    order = np.lexsort((np.arange(count, dtype=np.int64), timestamps_us))
    histories: dict[str, deque[tuple[int, str]]] = {}
    publisher_counts: dict[str, Counter[str]] = {}
    span = window_minutes * MINUTE_US
    for index in order:
        key = normalized_headline(headlines[int(index)])
        publisher = normalized_publisher(publishers[int(index)])
        if len(key) < 20:
            continue
        history = histories.setdefault(key, deque())
        counts = publisher_counts.setdefault(key, Counter())
        cutoff = int(timestamps_us[int(index)]) - span
        while history and history[0][0] <= cutoff:
            _, expired = history.popleft()
            counts[expired] -= 1
            if counts[expired] <= 0:
                del counts[expired]
        history.append((int(timestamps_us[int(index)]), publisher))
        counts[publisher] += 1
        reports[int(index)] = min(len(history), np.iinfo(np.uint16).max)
        distinct[int(index)] = min(len(counts), np.iinfo(np.uint16).max)
    return reports, distinct


def market_relative_novelty(
    timestamps_us: np.ndarray,
    vectors: np.ndarray,
    prior_documents: int = 20,
    window_minutes: int = 7 * 1440,
) -> np.ndarray:
    """Compute one minus maximum cosine similarity to prior market news.

    ``vectors`` must be row-normalized. Rows must be sorted by point-in-time
    availability. Same-time rows only compare with earlier deterministic rows.
    """

    if len(timestamps_us) != len(vectors):
        raise ValueError("novelty inputs have different lengths")
    if prior_documents <= 0 or window_minutes <= 0:
        raise ValueError("novelty history parameters must be positive")
    if len(timestamps_us) > 1 and np.any(np.diff(timestamps_us) < 0):
        raise ValueError("novelty timestamps must be sorted")
    output = np.ones(len(timestamps_us), dtype=np.float32)
    earliest = 0
    span = window_minutes * MINUTE_US
    for index in range(len(timestamps_us)):
        cutoff = int(timestamps_us[index]) - span
        while earliest < index and int(timestamps_us[earliest]) <= cutoff:
            earliest += 1
        left = max(earliest, index - prior_documents)
        if left < index:
            similarities = vectors[left:index] @ vectors[index]
            maximum = float(np.max(similarities))
            output[index] = 1.0 - min(1.0, max(0.0, maximum))
    return output


def trailing_event_features(
    event_timestamps_us: np.ndarray,
    relevance: np.ndarray,
    novelty: np.ndarray,
    publisher_ids: np.ndarray,
    cross_publisher: np.ndarray,
    grid_timestamps_us: np.ndarray,
    windows_minutes: Iterable[int] = (60, 360, 1440),
) -> np.ndarray:
    """Aggregate v4 news events using the frozen open-left/closed-right clock.

    For each window this returns, in order: relevance mass, novel-relevance
    mass, distinct publishers, and reports whose exact story had appeared at
    two or more publishers by the report's availability time.
    """

    arrays = (relevance, novelty, publisher_ids, cross_publisher)
    if any(len(value) != len(event_timestamps_us) for value in arrays):
        raise ValueError("event feature inputs have different lengths")
    if len(event_timestamps_us) > 1 and np.any(np.diff(event_timestamps_us) < 0):
        raise ValueError("event timestamps must be sorted")
    windows = tuple(int(value) for value in windows_minutes)
    output = np.zeros((len(grid_timestamps_us), 4 * len(windows)), dtype=np.float32)
    relevant = np.asarray(relevance, dtype=np.float64)
    novel_relevant = relevant * np.asarray(novelty, dtype=np.float64)
    diffused = np.asarray(cross_publisher, dtype=np.float64)
    relevance_prefix = np.concatenate(([0.0], np.cumsum(relevant)))
    novel_prefix = np.concatenate(([0.0], np.cumsum(novel_relevant)))
    diffusion_prefix = np.concatenate(([0.0], np.cumsum(diffused)))
    right = np.searchsorted(event_timestamps_us, grid_timestamps_us, side="right")
    for window_index, window in enumerate(windows):
        if window <= 0:
            raise ValueError("feature windows must be positive")
        left = np.searchsorted(
            event_timestamps_us,
            grid_timestamps_us - window * MINUTE_US,
            side="right",
        )
        column = 4 * window_index
        output[:, column] = relevance_prefix[right] - relevance_prefix[left]
        output[:, column + 1] = novel_prefix[right] - novel_prefix[left]
        output[:, column + 3] = diffusion_prefix[right] - diffusion_prefix[left]
        # Event sequences are short per market. The explicit calculation is both
        # auditable and exact; it is not approximated by source counts.
        for row, (start, stop) in enumerate(zip(left, right)):
            if stop > start:
                output[row, column + 2] = len(
                    np.unique(publisher_ids[int(start) : int(stop)])
                )
    return output
