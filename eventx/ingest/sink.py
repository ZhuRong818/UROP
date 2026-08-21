"""Append-only JSONL sink + checkpoint state for the frozen extract on disk.

Until Postgres is stood up, pulled rows land in gitignored data/{version}/raw/*.jsonl
(a content-frozen extract, guardrail A3). A per-job checkpoint file makes every pull
resumable (guardrail A2): a killed run picks up from the last recorded cursor.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from eventx.settings import REPO_ROOT


class JsonlSink:
    def __init__(self, version: str, root: Path | None = None, *, flush_every: int = 200) -> None:
        base = (root or (REPO_ROOT / "data")) / version
        self.raw_dir = base / "raw"
        self.ckpt_dir = base / "checkpoints"
        self.raw_dir.mkdir(parents=True, exist_ok=True)
        self.ckpt_dir.mkdir(parents=True, exist_ok=True)
        self.version = version
        # In-memory checkpoint cache. Re-reading/rewriting a per-job file on every call is
        # O(n^2) at 175k-market scale (guardrail A2 batch); we load each job once, mutate in
        # memory, and flush the whole file every `flush_every` updates + on flush()/close().
        # A crash loses at most `flush_every` "done" markers -> those markets re-pull, which
        # is idempotent because raw is frozen and deduped in curation (guardrail A3).
        self._ckpt_cache: dict[str, dict[str, Any]] = {}
        self._dirty: set[str] = set()
        self._flush_every = flush_every
        self._since_flush = 0

    def write(self, name: str, rows: list[dict[str, Any]]) -> int:
        """Append rows to raw/{name}.jsonl. Stamps each with the extract version."""
        if not rows:
            return 0
        path = self.raw_dir / f"{name}.jsonl"
        with path.open("a") as f:
            for r in rows:
                r = {**r, "_extract_version": self.version}
                f.write(json.dumps(r, default=str) + "\n")
        return len(rows)

    # --- checkpoints: one json file per job, mapping key -> state -------------
    def _ckpt_path(self, job: str) -> Path:
        return self.ckpt_dir / f"{job}.json"

    def _load(self, job: str) -> dict[str, Any]:
        if job not in self._ckpt_cache:
            p = self._ckpt_path(job)
            self._ckpt_cache[job] = json.loads(p.read_text()) if p.exists() else {}
        return self._ckpt_cache[job]

    def get_checkpoint(self, job: str, key: str) -> dict[str, Any] | None:
        return self._load(job).get(key)

    def set_checkpoint(self, job: str, key: str, **fields: Any) -> None:
        state = self._load(job)
        state[key] = {**state.get(key, {}), **fields}
        self._dirty.add(job)
        self._since_flush += 1
        if self._since_flush >= self._flush_every:
            self.flush()

    def flush(self) -> None:
        """Persist all dirty checkpoint jobs to disk (atomic per file via tmp+rename)."""
        for job in self._dirty:
            p = self._ckpt_path(job)
            tmp = p.with_suffix(".json.tmp")
            tmp.write_text(json.dumps(self._ckpt_cache[job], indent=1, default=str))
            tmp.replace(p)
        self._dirty.clear()
        self._since_flush = 0

    def is_done(self, job: str, key: str) -> bool:
        cp = self.get_checkpoint(job, key)
        return bool(cp and cp.get("status") == "done")
