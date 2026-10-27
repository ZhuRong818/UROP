"""Reusable primitives for the non-frozen EventX v5 residual-news design."""

from __future__ import annotations

from collections import Counter, deque
import re

import numpy as np


TOKEN = re.compile(r"[a-z0-9]+", re.IGNORECASE)
MINUTE_US = 60 * 1_000_000


def normalized_story_key(headline: str) -> str:
    """Return the auditable exact-headline story key."""

    return " ".join(TOKEN.findall(str(headline).lower()))


def online_story_stages(
    timestamps_us: np.ndarray,
    headlines: list[str],
    publishers: list[str],
    window_minutes: int = 1440,
) -> np.ndarray:
    """Assign lifecycle stages using only reports available at each row.

    Stages are 1=new story, 2=same-publisher/pre-confirmation repetition,
    3=first cross-publisher report, and 4=post-confirmation repetition.
    Distinct publisher labels are not asserted to be editorially independent.
    """

    count = len(timestamps_us)
    if len(headlines) != count or len(publishers) != count:
        raise ValueError("story inputs have different lengths")
    if window_minutes <= 0:
        raise ValueError("window_minutes must be positive")
    output = np.zeros(count, dtype=np.uint8)
    order = np.lexsort((np.arange(count, dtype=np.int64), timestamps_us))
    histories: dict[str, deque[tuple[int, str]]] = {}
    publisher_counts: dict[str, Counter[str]] = {}
    span = int(window_minutes) * MINUTE_US
    for raw_index in order:
        index = int(raw_index)
        key = normalized_story_key(headlines[index])
        if len(key) < 20:
            key = f"short:{index}"
        publisher = " ".join(str(publishers[index]).lower().split())
        timestamp = int(timestamps_us[index])
        history = histories.setdefault(key, deque())
        counts = publisher_counts.setdefault(key, Counter())
        cutoff = timestamp - span
        while history and history[0][0] <= cutoff:
            _expired_time, expired_publisher = history.popleft()
            counts[expired_publisher] -= 1
            if counts[expired_publisher] <= 0:
                del counts[expired_publisher]
        if not history:
            stage = 1
        elif len(counts) < 2 and publisher in counts:
            stage = 2
        elif len(counts) == 1 and publisher not in counts:
            stage = 3
        else:
            stage = 4
        history.append((timestamp, publisher))
        counts[publisher] += 1
        output[index] = stage
    return output


def logit(probability: np.ndarray) -> np.ndarray:
    """Numerically safe logit."""

    values = np.clip(np.asarray(probability, dtype=np.float64), 1e-7, 1 - 1e-7)
    return np.log(values / (1.0 - values))


def sigmoid(value: np.ndarray) -> np.ndarray:
    """Numerically stable sigmoid."""

    values = np.asarray(value, dtype=np.float64)
    output = np.empty_like(values)
    positive = values >= 0
    output[positive] = 1.0 / (1.0 + np.exp(-values[positive]))
    exponent = np.exp(values[~positive])
    output[~positive] = exponent / (1.0 + exponent)
    return output


def gated_residual_probability(
    baseline: np.ndarray,
    exposed: np.ndarray,
    residual_logit: np.ndarray,
    shrinkage: float,
) -> np.ndarray:
    """Apply a residual logit correction while preserving no-news equality."""

    baseline_values = np.asarray(baseline, dtype=np.float64)
    exposure = np.asarray(exposed, dtype=bool)
    correction = np.asarray(residual_logit, dtype=np.float64)
    if baseline_values.shape != exposure.shape or baseline_values.shape != correction.shape:
        raise ValueError("gated residual inputs have different shapes")
    if not 0.0 <= float(shrinkage) <= 1.0:
        raise ValueError("shrinkage must be in [0, 1]")
    output = baseline_values.copy()
    if float(shrinkage) == 0.0:
        return output
    output[exposure] = sigmoid(
        logit(baseline_values[exposure])
        + float(shrinkage) * correction[exposure]
    )
    return output
