"""Explicit time/family folds. All timestamps are integer UTC microseconds."""

from dataclasses import dataclass

import numpy as np

MINUTE_US = 60_000_000
HORIZON_US = 30 * MINUTE_US


@dataclass(frozen=True)
class Fold:
    name: str
    start: int
    end: int
    families: frozenset[str]


@dataclass
class RowIndex:
    decision: np.ndarray
    label_end: np.ndarray
    family: np.ndarray
    family_verified: np.ndarray

    def __post_init__(self):
        self.decision = np.asarray(self.decision)
        self.label_end = np.asarray(self.label_end)
        self.family = np.asarray(self.family, dtype=str)
        self.family_verified = np.asarray(self.family_verified, dtype=bool)
        n = len(self.decision)
        if (not n or any(a.shape != (n,) for a in
                         [self.decision, self.label_end, self.family, self.family_verified])
                or self.decision.dtype.kind not in "iu" or self.label_end.dtype.kind not in "iu"
                or np.any(self.label_end < self.decision + HORIZON_US)):
            raise ValueError("Require aligned UTC-us times and at least a 30-minute label horizon")
        if not self.family_verified.all() or np.any(self.family == ""):
            raise ValueError("Verified event-family mapping required; contract hashes are not a fallback")

    def split(self, parent_ids, fold):
        parent = np.asarray(parent_ids, dtype=int)
        if (len(np.unique(parent)) != len(parent) or np.any(parent < 0)
                or np.any(parent >= len(self.decision))):
            raise ValueError("Invalid parent row IDs")
        if fold.end <= fold.start or not fold.families:
            raise ValueError("Invalid fold window/families")
        held = np.isin(self.family[parent], sorted(fold.families))
        train = parent[(self.label_end[parent] < fold.start) & ~held]
        valid = parent[(self.decision[parent] >= fold.start)
                       & (self.label_end[parent] < fold.end) & held]
        if not len(train) or not len(valid):
            raise ValueError(f"Empty purged training/validation partition: {fold.name}")
        return train, valid

    def available_folds(self, parent_ids, folds):
        """Skip structurally unavailable early folds; log OOF exclusions separately."""
        for fold in folds:
            try:
                train, valid = self.split(parent_ids, fold)
            except ValueError as error:
                if str(error).startswith("Empty purged"):
                    continue
                raise
            yield fold, train, valid
