"""Publish synthetic-only repair evidence. Never reads research example/label files.

Usage: .venv/bin/python -m eventx.tasks.validate_v5_corrected_implementation
Use --output for a fresh release path; existing artifacts are never overwritten.
"""

import argparse
from contextlib import redirect_stdout
from datetime import datetime, timezone
import hashlib
import io
import json
import os
from pathlib import Path
import platform
import tempfile
import unittest

import numpy as np
import scipy
import sklearn

from eventx.tasks import test_algorithm_audit, test_v5_corrected_pipeline
from eventx.tasks import test_v5_market_baseline, test_v5_residual_architecture
from eventx.tasks.test_v5_corrected_pipeline import fixture
from eventx.v5_corrected import VERSION
from eventx.v5_corrected.pipeline import Candidate, NestedOffsetTrainer, market_model


ROOT = Path(__file__).resolve().parents[2]


def sha256(path):
    with path.open("rb") as handle:
        return hashlib.file_digest(handle, "sha256").hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path,
                        default=ROOT / "data/v5/corrected_implementation_20260908")
    args = parser.parse_args()
    output = args.output.resolve()
    if output.exists():
        raise FileExistsError(f"Refusing to overwrite implementation release: {output}")

    # Hash checks concern frozen CODE and historical model artifacts, not future
    # collections. No evaluator/collector/holdout builder is invoked.
    locked = json.loads((ROOT / "eventx/release/v4/holdout_implementation_manifest.json").read_text())
    frozen_checks = []
    for record in locked["artifacts"]:
        ok = sha256(ROOT / record["path"]) == record["sha256"]
        frozen_checks.append({"path": record["path"], "unchanged": ok})
        if not ok:
            raise RuntimeError(f"Frozen artifact conflict: {record['path']}")

    suite = unittest.TestSuite(
        unittest.defaultTestLoader.loadTestsFromModule(module)
        for module in [test_v5_corrected_pipeline, test_algorithm_audit])
    test_output = io.StringIO()
    result = unittest.TextTestRunner(stream=test_output, verbosity=2).run(suite)
    if not result.wasSuccessful():
        print(test_output.getvalue())
        raise RuntimeError("Synthetic regression suite failed; release not published")
    legacy = {}
    for module in [test_v5_market_baseline, test_v5_residual_architecture]:
        text = io.StringIO()
        with redirect_stdout(text):
            module.main()
        legacy[module.__name__] = json.loads(text.getvalue())

    source, labels, crossfit, tuning, outer = fixture()
    trainer = NestedOffsetTrainer(source, labels, market_model, crossfit)
    model, valid, selection = trainer.fit_outer(
        outer, tuning, [Candidate(0, .1, 0), Candidate(.01, .1, .5)])
    p0, p = model.predict(valid)
    exposed = model.features.transform(valid).exposed
    invariant = bool(np.array_equal(p0[~exposed], p[~exposed]))
    if not invariant:
        raise AssertionError("Unexposed invariance failed")

    report = {
        "version": VERSION, "created_at": datetime.now(timezone.utc).isoformat(),
        "status": "synthetic_implementation_validation_passed",
        "research_result": False, "real_examples_read": 0,
        "holdout_labels_or_predictions_read": False,
        "tests": {"run": result.testsRun, "failures": len(result.failures),
                  "errors": len(result.errors), "skipped": len(result.skipped)},
        "legacy_checks": legacy,
        "frozen_v4_artifacts": frozen_checks,
        "synthetic_integration": {
            "input_rows": len(labels), "outer_rows": len(valid),
            "outer_exposed_rows": int(exposed.sum()),
            "residual_oof_training_rows": len(model.oof_ids),
            "excluded_no_oof_training_rows": len(model.excluded_warmup_ids),
            "unexposed_exact_equality": invariant,
            "offset_solver": model.residual.status_,
            "offset_kkt_residual": model.residual.kkt_residual_,
            "selection": selection,
            "note": "Synthetic tuning losses are software evidence, not EventX research metrics",
        },
        "remaining_requirements": [
            "Verified event-family mapping and new as-of raw-input materialization",
            "Input manifests proving coverage, exact content versions and metadata availability",
            "Frozen semantic warm-up corpus/cutoff, baseline column set and tuning grids",
            "Matched context/timing-control capacity and attribution contract",
            "Label-blind feasibility gate and untouched V5 interval disjoint from protected V4",
        ],
        "environment": {"python": platform.python_version(), "numpy": np.__version__,
                        "scipy": scipy.__version__, "sklearn": sklearn.__version__},
        "lint": "ruff unavailable in existing environment; not installed by this task",
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    stage = Path(tempfile.mkdtemp(prefix=".v5-validation-", dir=output.parent))
    (stage / "report.json").write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")
    (stage / "fit_ledger.json").write_text(json.dumps(trainer.ledger, indent=2, sort_keys=True) + "\n")
    (stage / "tests.txt").write_text(test_output.getvalue())
    sources = sorted((ROOT / "eventx/v5_corrected").glob("*.py")) + [
        Path(__file__).resolve(), Path(test_v5_corrected_pipeline.__file__).resolve(),
        ROOT / "eventx/features/v4_news.py", ROOT / "eventx/features/v2_1_association.py",
        ROOT / "eventx/features/kol_association.py",
    ]
    manifest = {"version": VERSION, "artifact_type": "implementation_not_candidate_freeze",
                "source_artifacts": [{"path": str(path.relative_to(ROOT)), "sha256": sha256(path)}
                                     for path in sources],
                "outputs": [{"path": path.name, "sha256": sha256(path)}
                            for path in sorted(stage.iterdir())]}
    (stage / "manifest.json").write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n")
    if output.exists():
        raise FileExistsError(f"Output appeared during validation; staging retained at {stage}")
    os.rename(stage, output)
    print(json.dumps({"output": str(output), "status": report["status"],
                      "tests": report["tests"], "synthetic_integration": report["synthetic_integration"],
                      "frozen_artifacts_unchanged": len(frozen_checks)}, indent=2))


if __name__ == "__main__":
    main()
