"""Direct paired contrasts among completed v5 mechanism-ablation predictions."""

from __future__ import annotations

from datetime import datetime, timezone
import json
import os
from pathlib import Path
from typing import Any

import numpy as np

from eventx.settings import REPO_ROOT
from eventx.tasks.evaluate_v4_confirmatory import two_level_bootstrap
from eventx.tasks.prepare_v3_1_historical_development_arrays import sha256_file
from eventx.tasks.run_v5_mechanism_ablation import PREDICTION_DTYPE
from eventx.tasks.run_v5_residual_feasibility import compare, point_loss, relative


SOURCE = REPO_ROOT / "data/v5/development/mechanism_ablation/predictions.bin"
SOURCE_MANIFEST = REPO_ROOT / "data/v5/development/mechanism_ablation/manifest.json"
OUTPUT = REPO_ROOT / "data/v5/development/mechanism_contrasts"
REPORT = OUTPUT / "report.json"
SUMMARY = OUTPUT / "SUMMARY.md"
MANIFEST = OUTPUT / "manifest.json"
CONTRASTS = (
    ("volume_age_vs_context_only", "context_only", "volume_age"),
    ("quality_age_vs_context_only", "context_only", "quality_age"),
    ("lifecycle_age_vs_context_only", "context_only", "lifecycle_age"),
    ("full_vs_context_only", "context_only", "full"),
    ("full_vs_volume_age", "volume_age", "full"),
)


def atomic_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n")
    os.replace(temporary, path)


def main() -> None:
    if any(path.exists() for path in (REPORT, SUMMARY, MANIFEST)):
        raise SystemExit("v5 mechanism contrasts already exist")
    manifest = json.loads(SOURCE_MANIFEST.read_text(encoding="utf-8"))
    expected = next(
        row["sha256"] for row in manifest["artifacts"] if row["path"] == relative(SOURCE)
    )
    if sha256_file(SOURCE) != expected:
        raise RuntimeError("mechanism prediction hash mismatch")
    count = SOURCE.stat().st_size // PREDICTION_DTYPE.itemsize
    rows = np.memmap(SOURCE, mode="r", dtype=PREDICTION_DTYPE, shape=(count,))
    results = {}
    for offset, (label, baseline, candidate) in enumerate(CONTRASTS):
        result = compare(rows["label"], rows[baseline], rows[candidate])
        improvement = point_loss(rows["label"], rows[baseline]) - point_loss(
            rows["label"], rows[candidate]
        )
        bootstrap = two_level_bootstrap(
            np.asarray(rows["market"]),
            np.asarray(rows["minute"]),
            improvement,
            samples=2000,
            seed=1401 + offset,
        )
        bootstrap["estimand"] = f"{baseline} minus {candidate} log loss"
        results[label] = {
            "baseline": baseline,
            "candidate": candidate,
            "comparison": result,
            "paired_bootstrap": bootstrap,
        }
    report = {
        "experiment_id": "eventx-v5-direct-mechanism-contrasts-20260903",
        "created_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "status": "complete",
        "role": "opened historical mechanism contrasts; not confirmation",
        "future_v4_data_read": False,
        "rows": len(rows),
        "results": results,
    }
    OUTPUT.mkdir(parents=True, exist_ok=True)
    atomic_json(REPORT, report)
    lines = [
        "# EventX v5 direct mechanism contrasts",
        "",
        "Positive values favour the added mechanism over the context-only control.",
        "",
    ]
    for label, value in results.items():
        comparison = value["comparison"]["log_loss_improvement"]
        bootstrap = value["paired_bootstrap"]
        lines.append(
            f"- {label}: `{comparison:.6f}`, interval "
            f"`[{bootstrap['ci_95_lower']:.6f}, {bootstrap['ci_95_upper']:.6f}]`."
        )
    SUMMARY.write_text("\n".join(lines) + "\n", encoding="utf-8")
    atomic_json(
        MANIFEST,
        {
            "experiment_id": report["experiment_id"],
            "status": report["status"],
            "artifacts": [
                {"path": relative(path), "sha256": sha256_file(path)}
                for path in (REPORT, SUMMARY, Path(__file__).resolve())
            ],
            "inputs": [{"path": relative(SOURCE), "sha256": expected}],
        },
    )
    print(json.dumps(report, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
