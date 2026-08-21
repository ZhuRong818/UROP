"""Freeze and authorize the new EventX out-of-time holdout."""

from __future__ import annotations

import argparse
import hashlib
import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from eventx.features.build_kol_features import parse_ts
from eventx.settings import REPO_ROOT
from eventx.tasks.fetch_oot_holdout import DEFAULT_EXTRACT
from eventx.tasks.freeze_toy import hash_file
from eventx.tasks.run_b0 import read_jsonl
from eventx.tasks.run_frozen_b0_oot_final import cadence_match


def relative(path: Path) -> str:
    return str(path.resolve().relative_to(REPO_ROOT.resolve()))


def artifact(path: Path) -> dict[str, Any]:
    return {"path": relative(path), **hash_file(path)}


def verify_manifest(path: Path) -> dict[str, Any]:
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
        failures.append({"artifact": "evaluator", "error": "contract_mismatch"})
    if manifest["holdout_integrity"]["status"] != "untouched":
        failures.append({"artifact": "holdout", "error": "not_untouched"})
    if not manifest["confirmatory_evaluation"]["allowed"]:
        failures.append({"artifact": "evaluation", "error": "not_authorized"})
    return {
        "status": "ok" if not failures else "failed",
        "dataset_id": manifest["dataset_id"],
        "locked": manifest["locked"],
        "holdout_status": manifest["holdout_integrity"]["status"],
        "confirmatory_evaluation_allowed": manifest["confirmatory_evaluation"][
            "allowed"
        ],
        "checked_artifacts": len(manifest["artifacts"]),
        "failures": failures,
    }


def markdown_manifest(manifest: dict[str, Any]) -> str:
    return "\n".join(
        [
            "# EventX out-of-time holdout freeze",
            "",
            f"Dataset: `{manifest['dataset_id']}`  ",
            "Status: **frozen and authorized for one-shot evaluation**.",
            "",
            "## Holdout",
            "",
            f"- Window: `{manifest['holdout_integrity']['start']}` through "
            f"`{manifest['holdout_integrity']['end']}`",
            f"- Evaluation cadence: `{manifest['baseline_contract']['cadence_min']}m`",
            f"- Eligible evaluation rows: "
            f"`{manifest['holdout_integrity']['expected_evaluation_rows']}`",
            f"- Eligible markets: "
            f"`{manifest['holdout_integrity']['expected_evaluation_markets']}`",
            "- Cohort was selected and frozen before this window.",
            "- Label outcomes, prevalence, and metrics were not inspected before freeze.",
            "",
            "## Frozen B0",
            "",
            "- Model: standardized logistic SGD",
            "- Features: the 11 locked market-only features",
            "- Hyperparameters: 8 epochs, learning rate 0.02, L2 0.0001, seed 11",
            f"- Training rows: `{manifest['baseline_contract']['expected_training_rows']}`",
            "- Primary metric: average precision",
            "- Calibration metric: Brier score",
            "",
            "## One-shot rule",
            "",
            "The evaluator is authorized exactly once. It will write a consumption "
            "receipt and refuse any later invocation. Results cannot justify further "
            "feature, eligibility, or hyperparameter changes.",
            "",
        ]
    )


def main() -> None:
    parser = argparse.ArgumentParser(description="Freeze EventX OOT holdout")
    parser.add_argument("--extract", default=DEFAULT_EXTRACT)
    parser.add_argument("--out", type=Path)
    parser.add_argument("--markdown-out", type=Path)
    parser.add_argument("--verify", action="store_true")
    args = parser.parse_args()
    root = REPO_ROOT / "data" / args.extract
    out_path = args.out or root / "frozen_holdout_manifest.json"
    markdown_path = args.markdown_out or root / "frozen_holdout_manifest.md"
    if args.verify:
        if not out_path.exists():
            raise SystemExit(f"Missing OOT freeze manifest: {out_path}")
        result = verify_manifest(out_path)
        print(json.dumps(result, indent=2, sort_keys=True))
        if result["status"] != "ok":
            raise SystemExit(1)
        return
    if out_path.exists():
        raise SystemExit(f"Refusing to replace OOT freeze manifest: {out_path}")
    if (root / "b0_oot_final_result.json").exists() or (
        root / "holdout_consumption_receipt.json"
    ).exists():
        raise SystemExit("Cannot freeze: OOT evaluation output already exists.")

    baseline_path = (
        REPO_ROOT / "data" / "v1" / "toy" / "final_baseline_freeze_manifest.json"
    )
    toy_freeze_path = REPO_ROOT / "data" / "v1" / "toy" / "frozen_manifest.json"
    training_labels_path = REPO_ROOT / "data" / "v1" / "toy" / "labels_30m.jsonl"
    selected_path = REPO_ROOT / "data" / "v1" / "toy" / "selected_markets.jsonl"
    fetch_path = root / "fetch_manifest.json"
    trades_path = root / "raw" / "trades_polymarket.jsonl"
    build_path = root / "holdout" / "build_manifest.json"
    bars_path = root / "holdout" / "bars_with_warmup.jsonl"
    labels_path = root / "holdout" / "labels_30m.jsonl"
    evaluator_path = REPO_ROOT / "eventx" / "tasks" / "run_frozen_b0_oot_final.py"
    fetcher_path = REPO_ROOT / "eventx" / "tasks" / "fetch_oot_holdout.py"
    builder_path = REPO_ROOT / "eventx" / "tasks" / "build_oot_holdout.py"
    freezer_path = Path(__file__).resolve()
    required = [
        baseline_path,
        toy_freeze_path,
        training_labels_path,
        selected_path,
        fetch_path,
        trades_path,
        build_path,
        bars_path,
        labels_path,
        evaluator_path,
        fetcher_path,
        builder_path,
    ]
    missing = [str(path) for path in required if not path.exists()]
    if missing:
        raise SystemExit("Missing OOT freeze inputs: " + ", ".join(missing))

    baseline_freeze = json.loads(baseline_path.read_text())
    toy_freeze = json.loads(toy_freeze_path.read_text())
    fetch = json.loads(fetch_path.read_text())
    build = json.loads(build_path.read_text())
    if baseline_freeze["status"] != "baseline_frozen_confirmatory_holdout_required":
        raise SystemExit("Canonical B0 baseline is not in the expected frozen state.")
    if baseline_freeze["baseline"]["reference"] != "b0_market_only":
        raise SystemExit("Canonical reference is not B0.")
    if build["status"] != "oot_holdout_built_labels_uninspected":
        raise SystemExit("OOT build does not preserve the label seal.")
    if build["label_seal"]["status"] != "values_not_summarized_or_inspected":
        raise SystemExit("OOT labels are not sealed.")
    if hash_file(trades_path)["sha256"] != fetch["artifact"]["sha256"]:
        raise SystemExit("Fresh trade hash mismatch.")
    if hash_file(labels_path)["sha256"] != build["artifacts"]["labels"]["sha256"]:
        raise SystemExit("OOT label hash mismatch.")
    if (
        hash_file(training_labels_path)["sha256"]
        != toy_freeze["files"][relative(training_labels_path)]["sha256"]
    ):
        raise SystemExit("Canonical training labels no longer match the toy freeze.")

    holdout_start = parse_ts(build["window"]["holdout_start"])
    holdout_end = parse_ts(build["window"]["end"])
    cadence_min = int(baseline_freeze["baseline"]["cadence_min"])
    evaluation_rows = 0
    evaluation_markets = set()
    for row in read_jsonl(labels_path):
        timestamp = str(row["ts"])
        if not cadence_match(timestamp, cadence_min) or not int(row["eligible"]):
            continue
        timestamp_dt = parse_ts(timestamp)
        if not holdout_start <= timestamp_dt <= holdout_end:
            raise SystemExit(f"Eligible row outside OOT holdout: {timestamp}")
        evaluation_rows += 1
        evaluation_markets.add(str(row["market_id"]))
    if not evaluation_rows:
        raise SystemExit("No eligible cadence rows in the OOT holdout.")

    artifacts = {
        "canonical_baseline_freeze": artifact(baseline_path),
        "original_toy_freeze": artifact(toy_freeze_path),
        "training_labels": artifact(training_labels_path),
        "frozen_cohort": artifact(selected_path),
        "fresh_fetch_manifest": artifact(fetch_path),
        "fresh_trades": artifact(trades_path),
        "holdout_build_manifest": artifact(build_path),
        "holdout_bars": artifact(bars_path),
        "holdout_labels": artifact(labels_path),
        "fetcher_source": artifact(fetcher_path),
        "builder_source": artifact(builder_path),
        "evaluator_source": artifact(evaluator_path),
        "freezer_source": artifact(freezer_path),
    }
    identity_payload = "\n".join(
        f"{name}:{details['sha256']}" for name, details in sorted(artifacts.items())
    )
    dataset_id = "eventx-oot-" + hashlib.sha256(identity_payload.encode()).hexdigest()[:20]
    manifest = {
        "freeze_schema": 1,
        "locked": True,
        "created_at": datetime.now(UTC).isoformat().replace("+00:00", "Z"),
        "status": "oot_holdout_frozen_one_shot_authorized",
        "dataset_id": dataset_id,
        "parent_dataset_id": toy_freeze["dataset_id"],
        "baseline_contract": baseline_freeze["baseline"],
        "holdout_integrity": {
            "status": "untouched",
            "start": build["window"]["holdout_start"],
            "end": build["window"]["end"],
            "warmup_start": build["window"]["warmup_start"],
            "expected_evaluation_rows": evaluation_rows,
            "expected_evaluation_markets": len(evaluation_markets),
            "cohort_frozen_before_window": True,
            "label_values_inspected_before_freeze": False,
            "prevalence_or_metrics_computed_before_freeze": False,
        },
        "confirmatory_evaluation": {
            "allowed": True,
            "model": "b0_market_only",
            "metrics": {
                "primary": "average_precision",
                "calibration": "brier",
            },
            "evaluator": {
                "path": relative(evaluator_path),
                "sha256": artifacts["evaluator_source"]["sha256"],
            },
            "one_shot_guard": {
                "result_path": relative(root / "b0_oot_final_result.json"),
                "receipt_path": relative(root / "holdout_consumption_receipt.json"),
                "rerun_permitted": False,
            },
        },
        "inputs": {
            "training_labels": {
                "path": relative(training_labels_path),
                "sha256": artifacts["training_labels"]["sha256"],
            },
            "holdout_labels": {
                "path": relative(labels_path),
                "sha256": artifacts["holdout_labels"]["sha256"],
            },
        },
        "artifacts": artifacts,
        "policy": (
            "This holdout may be evaluated exactly once with the frozen B0 evaluator. "
            "No result-driven tuning or new candidate selection is permitted."
        ),
    }
    temporary = out_path.with_suffix(".json.tmp")
    temporary.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n")
    temporary.replace(out_path)
    markdown_path.write_text(markdown_manifest(manifest))
    print(
        json.dumps(
            {
                "status": manifest["status"],
                "dataset_id": manifest["dataset_id"],
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
