"""Freeze the canonical EventX B0 contract and disclose test-block integrity."""

from __future__ import annotations

import argparse
import json
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

from eventx.features.build_kol_features import parse_ts
from eventx.settings import REPO_ROOT
from eventx.tasks.freeze_toy import hash_file, verify_manifest
from eventx.tasks.run_b1 import MARKET_FEATURES


def relative(path: Path) -> str:
    return str(path.resolve().relative_to(REPO_ROOT.resolve()))


def artifact(path: Path) -> dict[str, Any]:
    return {"path": relative(path), **hash_file(path)}


def verify_final_manifest(path: Path) -> dict[str, Any]:
    manifest = json.loads(path.read_text())
    failures = []
    for name, expected in manifest["artifacts"].items():
        source = REPO_ROOT / expected["path"]
        if not source.exists():
            failures.append({"artifact": name, "error": "missing"})
            continue
        actual = hash_file(source)
        if actual["sha256"] != expected["sha256"]:
            failures.append(
                {
                    "artifact": name,
                    "error": "sha256_mismatch",
                    "expected": expected["sha256"],
                    "actual": actual["sha256"],
                }
            )
    evaluator = manifest["confirmatory_evaluation"]["evaluator"]
    evaluator_path = REPO_ROOT / evaluator["path"]
    if (
        evaluator_path.exists()
        and hash_file(evaluator_path)["sha256"] != evaluator["sha256"]
    ):
        failures.append({"artifact": "guarded_evaluator", "error": "contract_mismatch"})
    if manifest["baseline"]["features"] != MARKET_FEATURES:
        failures.append({"artifact": "baseline", "error": "feature_contract_mismatch"})
    if (
        manifest["holdout_integrity"]["status"]
        == "previously_exposed_noncanonical_b0"
        and manifest["confirmatory_evaluation"]["allowed"]
    ):
        failures.append(
            {
                "artifact": "confirmatory_evaluation",
                "error": "exposed_holdout_cannot_be_authorized",
            }
        )
    return {
        "status": "ok" if not failures else "failed",
        "dataset_id": manifest.get("dataset_id"),
        "locked": manifest.get("locked"),
        "holdout_status": manifest["holdout_integrity"]["status"],
        "confirmatory_evaluation_allowed": manifest["confirmatory_evaluation"][
            "allowed"
        ],
        "checked_artifacts": len(manifest["artifacts"]),
        "failures": failures,
    }


def markdown_manifest(manifest: dict[str, Any]) -> str:
    exposure = manifest["holdout_integrity"]["prior_exposure"]
    test_metrics = exposure["reported_metrics"]["b0_market_only"]
    return "\n".join(
        [
            "# EventX final baseline freeze",
            "",
            f"Dataset: `{manifest['dataset_id']}`  ",
            f"Status: **{manifest['status']}**  ",
            "Baseline reference: **B0 market-only**.",
            "",
            "## Locked decision",
            "",
            "- B0 is the benchmark reference.",
            "- B1 market + core news: rejected for confirmatory promotion.",
            "- B2 market + KOL: rejected.",
            "- B3 market + core news + KOL: rejected.",
            "- No additional candidate may be selected on the frozen development folds.",
            "",
            "## Holdout integrity disclosure",
            "",
            "**The current test block is not untouched.** It was evaluated by an earlier, "
            "noncanonical B0 run before this final freeze.",
            "",
            f"- First known exposure: `{exposure['first_known_exposure_at']}`",
            f"- Exposed test rows: `{test_metrics['rows']}`",
            f"- Reported AP: `{float(test_metrics['average_precision']):.6f}`",
            f"- Reported Brier: `{float(test_metrics['brier']):.6f}`",
            "- Earlier model trained on the original train split only.",
            "- Earlier transform logged notional features but not trade-count features.",
            "",
            "Therefore the guarded evaluator is locked in the **blocked** state for this "
            "dataset. Re-running the block cannot restore confirmatory independence.",
            "",
            "## Canonical B0 contract",
            "",
            f"- Cadence: `{manifest['baseline']['cadence_min']} minutes`",
            f"- Training rows expected: `{manifest['baseline']['expected_training_rows']}`",
            f"- Training end, exclusive: "
            f"`{manifest['baseline']['training_end_exclusive']}`",
            "- Learner: standardized logistic SGD",
            "- Hyperparameters: 8 epochs, learning rate 0.02, L2 0.0001, seed 11",
            "- Primary metric: average precision",
            "- Calibration metric: Brier score",
            "",
            "## Required next step",
            "",
            "Collect and freeze a new out-of-time holdout. Only a new manifest with "
            "`holdout_integrity.status = \"untouched\"` may authorize the guarded "
            "evaluator. The new result must not be used for further tuning.",
            "",
        ]
    )


def main() -> None:
    parser = argparse.ArgumentParser(description="Freeze the final EventX B0 contract")
    parser.add_argument("--toy-freeze", type=Path)
    parser.add_argument("--combined-result", type=Path)
    parser.add_argument("--failure-diagnostic", type=Path)
    parser.add_argument("--prior-b0-result", type=Path)
    parser.add_argument("--out", type=Path)
    parser.add_argument("--markdown-out", type=Path)
    parser.add_argument("--verify", action="store_true")
    args = parser.parse_args()

    root = REPO_ROOT / "data" / "v1" / "toy"
    toy_freeze_path = args.toy_freeze or root / "frozen_manifest.json"
    combined_path = args.combined_result or root / "combined_b3_walk_forward_cv_5m.json"
    diagnostic_path = (
        args.failure_diagnostic or root / "combined_b3_failure_diagnostic.json"
    )
    prior_b0_path = args.prior_b0_result or root / "b0_results.json"
    out_path = args.out or root / "final_baseline_freeze_manifest.json"
    markdown_path = args.markdown_out or root / "final_baseline_freeze_manifest.md"
    evaluator_path = REPO_ROOT / "eventx" / "tasks" / "run_frozen_b0_final.py"
    builder_path = Path(__file__).resolve()
    prior_runner_path = REPO_ROOT / "eventx" / "tasks" / "run_b0.py"

    if args.verify:
        if not out_path.exists():
            raise SystemExit(f"Final baseline freeze does not exist: {out_path}")
        result = verify_final_manifest(out_path)
        print(json.dumps(result, indent=2, sort_keys=True))
        if result["status"] != "ok":
            raise SystemExit(1)
        return
    if out_path.exists():
        raise SystemExit(f"Refusing to replace final baseline freeze: {out_path}")

    toy_verification = verify_manifest(toy_freeze_path)
    if toy_verification["status"] != "ok":
        raise SystemExit("Frozen toy dataset failed integrity verification.")
    toy_freeze = json.loads(toy_freeze_path.read_text())
    combined = json.loads(combined_path.read_text())
    diagnostic = json.loads(diagnostic_path.read_text())
    prior_b0 = json.loads(prior_b0_path.read_text())
    dataset_ids = {
        toy_freeze["dataset_id"],
        combined["dataset_id"],
        diagnostic["dataset_id"],
        prior_b0["dataset_id"],
    }
    if len(dataset_ids) != 1:
        raise SystemExit("Final-freeze inputs do not share one dataset ID.")
    if combined["status"] != "do_not_freeze" or combined["freeze_gate"]["passed"]:
        raise SystemExit("Combined candidate rejection evidence is inconsistent.")
    if (
        diagnostic["decision"]["benchmark_reference"] != "b0_market_only"
        or diagnostic["decision"]["b3"] != "reject"
        or diagnostic["decision"]["new_candidate_on_current_development_set"]
        != "not_justified"
    ):
        raise SystemExit("Failure diagnostic does not lock the expected decision.")
    if "test" not in prior_b0.get("evaluation", {}):
        raise SystemExit("Expected prior B0 test exposure was not found.")

    labels_path = REPO_ROOT / "data" / "v1" / "toy" / "labels_30m.jsonl"
    labels_expected = toy_freeze["files"][relative(labels_path)]
    if hash_file(labels_path)["sha256"] != labels_expected["sha256"]:
        raise SystemExit("Labels artifact no longer matches the toy freeze.")
    test_start = parse_ts(toy_freeze["split_boundaries"]["test_start"])
    purge_min = int(toy_freeze["split_boundaries"]["purge_min"])
    training_end = test_start - timedelta(minutes=purge_min)
    evaluator_artifact = artifact(evaluator_path)
    prior_test_metrics = prior_b0["evaluation"]["test"]
    exposure_time = datetime.fromtimestamp(
        prior_b0_path.stat().st_mtime,
        UTC,
    ).isoformat().replace("+00:00", "Z")

    artifacts = {
        "toy_freeze": artifact(toy_freeze_path),
        "labels": artifact(labels_path),
        "combined_walk_forward": artifact(combined_path),
        "failure_diagnostic": artifact(diagnostic_path),
        "prior_b0_test_result": artifact(prior_b0_path),
        "prior_b0_runner": artifact(prior_runner_path),
        "guarded_final_evaluator": evaluator_artifact,
        "final_freeze_builder": artifact(builder_path),
    }
    manifest = {
        "freeze_schema": 1,
        "locked": True,
        "created_at": datetime.now(UTC).isoformat().replace("+00:00", "Z"),
        "status": "baseline_frozen_confirmatory_holdout_required",
        "dataset_id": toy_freeze["dataset_id"],
        "baseline": {
            "reference": "b0_market_only",
            "model": "standardized_logistic_sgd",
            "features": MARKET_FEATURES,
            "feature_transform": {
                "log1p_prefixes": ["notional_", "trade_count_"],
                "otherwise": "identity",
            },
            "fixed_hyperparameters": {
                "epochs": 8,
                "learning_rate": 0.02,
                "l2": 1.0e-4,
                "shuffle_seed": 11,
            },
            "cadence_min": 5,
            "horizon_min": 30,
            "purge_min": purge_min,
            "training_scope": (
                "all eligible cadence rows strictly before test_start minus horizon"
            ),
            "training_end_exclusive": training_end.isoformat().replace("+00:00", "Z"),
            "expected_training_rows": diagnostic["load_validation"][
                "eligible_pretest_examples"
            ],
            "metrics": {
                "primary": "average_precision",
                "calibration": "brier",
            },
        },
        "candidate_decisions": {
            "b1_market_plus_core_news": "rejected_not_promoted",
            "b2_market_plus_kol": "rejected",
            "b3_market_plus_core_news_plus_kol": "rejected",
            "additional_selection_on_frozen_development_folds": "prohibited",
        },
        "holdout_integrity": {
            "status": "previously_exposed_noncanonical_b0",
            "test_start": toy_freeze["split_boundaries"]["test_start"],
            "prior_exposure": {
                "first_known_exposure_at": exposure_time,
                "artifact": artifacts["prior_b0_test_result"],
                "reported_metrics": prior_test_metrics,
                "differences_from_canonical_contract": [
                    "trained on original train split only (17,538 cadence rows)",
                    "did not train on all 20,702 eligible pre-test cadence rows",
                    "logged notional features but did not log trade-count features",
                ],
            },
            "scientific_consequence": (
                "The block may be reported as descriptive prior evidence but cannot "
                "support a new claim of untouched confirmatory performance."
            ),
        },
        "confirmatory_evaluation": {
            "allowed": False,
            "reason": "current holdout was previously exposed",
            "required_replacement": "new frozen out-of-time holdout",
            "evaluator": {
                "path": evaluator_artifact["path"],
                "sha256": evaluator_artifact["sha256"],
                "one_shot_output_guard": True,
                "requires_holdout_status": "untouched",
            },
        },
        "inputs": {
            "labels": {
                "path": relative(labels_path),
                "sha256": labels_expected["sha256"],
            }
        },
        "artifacts": artifacts,
        "policy": (
            "B0 is frozen as the reference benchmark. The current test block must not "
            "be reused as an untouched confirmation. A new out-of-time holdout must "
            "be frozen before confirmatory evaluation."
        ),
    }
    temporary = out_path.with_suffix(out_path.suffix + ".tmp")
    temporary.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n")
    temporary.replace(out_path)
    markdown_path.write_text(markdown_manifest(manifest))
    print(
        json.dumps(
            {
                "status": manifest["status"],
                "dataset_id": manifest["dataset_id"],
                "baseline": manifest["baseline"],
                "holdout_integrity": manifest["holdout_integrity"],
                "confirmatory_evaluation": manifest["confirmatory_evaluation"],
                "json_output": str(out_path),
                "markdown_output": str(markdown_path),
            },
            indent=2,
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
