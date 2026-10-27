"""Synthetic-only integration and bootstrap screening; immutable evidence output."""

from datetime import datetime, timezone
import hashlib
import io
import json
from pathlib import Path
import platform
import unittest

import numpy as np
from threadpoolctl import threadpool_limits

from eventx.tasks.test_v5_experiment_v1 import integrated_fixture
from eventx.v5_corrected.experiment_v1 import ExperimentTrainer
from eventx.v5_corrected.evaluation_v1 import bootstrap

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "data/v5/experiment_implementation_20260910"


def coverage_screen(trials=100, replicates=1000):
    """Monte Carlo loss-difference processes, not fitted research predictions.

    Positive shifts assess single-contrast power only, not power of all V5 gates.
    Simulations intentionally include multi-day dependence beyond daily blocks.
    """
    nf, nd = 30, 35
    family, day = np.repeat(np.arange(nf), nd), np.tile(np.arange(nd), nf)
    rng = np.random.default_rng(9102026)
    scenarios = {}
    for scenario in ["iid", "family_and_day", "multiday_ar09"]:
        cover, positive, gate_power = [], [], {str(s): [] for s in (0., .001, .003)}
        for trial in range(trials):
            noise = rng.normal(0, .02, (nf, nd))
            if scenario == "family_and_day":
                noise += rng.normal(0, .003, (nf, 1))+rng.normal(0, .006, (1, nd))
            elif scenario == "multiday_ar09":
                process = np.zeros(nd)
                process[0] = rng.normal(0, .01)
                for d in range(1, nd):
                    process[d] = .9*process[d-1]+rng.normal(0, .01*np.sqrt(1-.9**2))
                noise += process[None, :]
            samples = bootstrap(noise.ravel(), family, day, day//7,
                                replicates=replicates, seed=20260909+trial)["all"][:, 0]
            lb, ub = np.quantile(samples, [.025, .975])
            cover.append(lb <= 0 <= ub)
            positive.append(lb > 0)
            for shift, values in gate_power.items():
                s = float(shift)
                values.append(noise.mean()+s >= .001 and lb+s > 0)
        rate = float(np.mean(cover))
        scenarios[scenario] = {"null_95_interval_coverage": rate,
            "coverage_monte_carlo_se": float(np.sqrt(rate*(1-rate)/trials)),
            "null_positive_lower_bound_rate": float(np.mean(positive)),
            "single_contrast_margin_and_ci_pass_rate": {k: float(np.mean(v)) for k, v in gate_power.items()}}
    return {"trials_per_scenario": trials, "replicates_per_trial": replicates,
            "primary_evaluator_replicates": 5000, "synthetic_families": nf, "synthetic_days": nd,
            "full_v5_power_estimate": False, "coverage_certified": False,
            "note": "Screening only; reduced replicate count and hypothetical loss processes, not cohort-specific power",
            "scenarios": scenarios}


def main():
    if OUT.exists():
        raise SystemExit("Validation release already exists; create a new version")
    OUT.mkdir(parents=True)
    modules = ["test_v5_experiment_v1", "test_v5_label_blind_contract", "test_v5_corrected_pipeline",
               "test_algorithm_audit", "test_v5_source_readiness", "test_v5_recovery_requests"]
    suite = unittest.TestSuite(unittest.defaultTestLoader.loadTestsFromName("eventx.tasks."+m) for m in modules)
    buffer = io.StringIO()
    result = unittest.TextTestRunner(stream=buffer, verbosity=2).run(suite)
    (OUT/"tests.txt").write_text(buffer.getvalue())
    if not result.wasSuccessful():
        raise RuntimeError("Tests failed; see retained tests.txt; no release certified")
    print(f"Synthetic/regression tests passed: {result.testsRun}", flush=True)
    source, y, base, oof, tuning, outer = integrated_fixture()
    masked = y.astype(float)
    masked[np.isin(source.index.family, list("GH"))] = np.nan
    trainer = ExperimentTrainer(source, masked, base, oof)
    bundle, valid, predictions, selection = trainer.fit_outer(outer, tuning)
    (OUT/"fit_ledger.json").write_text(json.dumps(trainer.ledger, indent=2)+"\n")
    with threadpool_limits(limits=2):
        screen = coverage_screen()
    (OUT/"bootstrap_screen.json").write_text(json.dumps(screen, indent=2)+"\n")
    print(json.dumps(screen, indent=2), flush=True)
    locked = json.loads((ROOT/"eventx/release/v4/holdout_implementation_manifest.json").read_text())
    checks = [{"path": a["path"], "matches": hashlib.sha256((ROOT/a["path"]).read_bytes()).hexdigest()==a["sha256"]}
              for a in locked["artifacts"]]
    if not all(a["matches"] for a in checks):
        raise RuntimeError("Frozen V4 hash conflict")
    report = {"created_at": datetime.now(timezone.utc).isoformat(), "research_result": False,
        "tests": {"run": result.testsRun, "failures": len(result.failures), "errors": len(result.errors)},
        "integration": {"synthetic_rows": len(y), "outer_rows": len(valid),
            "oof_rows": len(bundle.oof_ids), "diagnostics": bundle.diagnostics,
            "selection": selection, "all_predictions_finite": all(np.isfinite(p).all() for p in predictions.values()),
            "all_arms_share_identical_base_scores": True, "outer_labels_missing_and_unread": True},
        "frozen_v4_hashes": checks, "real_data_admitted": False,
        "candidate_frozen": False, "coverage_certified": False,
        "python": platform.python_version()}
    (OUT/"report.json").write_text(json.dumps(report, indent=2)+"\n")
    files = sorted((ROOT/"eventx/v5_corrected").glob("*.py")) + [Path(__file__),
        ROOT/"eventx/tasks/test_v5_experiment_v1.py",
        ROOT/"eventx/release/v5/MATCHED_CONTROLS_AND_EVALUATION_V1.md", *sorted(OUT.iterdir())]
    (OUT/"manifest.json").write_text(json.dumps({"status": "implementation_evidence_not_research_freeze",
        "artifacts": [{"path": str(p.relative_to(ROOT)), "sha256": hashlib.sha256(p.read_bytes()).hexdigest()}
                      for p in files]}, indent=2)+"\n")
    print("Published synthetic validation: "+str(OUT), flush=True)


if __name__ == "__main__":
    main()
