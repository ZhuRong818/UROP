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
    def __init__(self, version: str, root: Path | None = None) -> None:
        base = (root or (REPO_ROOT / "data")) / version
        self.raw_dir = base / "raw"
        self.ckpt_dir = base / "checkpoints"
        self.raw_dir.mkdir(parents=True, exist_ok=True)
        self.ckpt_dir.mkdir(parents=True, exist_ok=True)
        self.version = version

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
        p = self._ckpt_path(job)
        return json.loads(p.read_text()) if p.exists() else {}

    def get_checkpoint(self, job: str, key: str) -> dict[str, Any] | None:
        return self._load(job).get(key)

    def set_checkpoint(self, job: str, key: str, **fields: Any) -> None:
        state = self._load(job)
        state[key] = {**state.get(key, {}), **fields}
        self._ckpt_path(job).write_text(json.dumps(state, indent=1, default=str))

    def is_done(self, job: str, key: str) -> bool:
        cp = self.get_checkpoint(job, key)
        return bool(cp and cp.get("status") == "done")
