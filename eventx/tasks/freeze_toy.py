"""Freeze and verify the leakage-safe EventX toy dataset."""

from __future__ import annotations

import argparse
import hashlib
import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from eventx.settings import REPO_ROOT


def hash_file(path: Path) -> dict[str, Any]:
    digest = hashlib.sha256()
    size = 0
    lines = 0
    with path.open("rb") as handle:
        while chunk := handle.read(8 * 1024 * 1024):
            digest.update(chunk)
            size += len(chunk)
            lines += chunk.count(b"\n")
    result: dict[str, Any] = {"sha256": digest.hexdigest(), "bytes": size}
    if path.suffix == ".jsonl":
        result["rows"] = lines
    return result


def relative(path: Path) -> str:
    return str(path.resolve().relative_to(REPO_ROOT.resolve()))


def default_paths(toy_dir: Path, horizon_min: int) -> list[Path]:
    return [
        toy_dir / "selected_markets.jsonl",
        toy_dir / "market_selection_report.json",
        toy_dir / "bars.jsonl",
        toy_dir / f"labels_{horizon_min}m.jsonl",
        toy_dir / f"splits_{horizon_min}m.jsonl",
        toy_dir / "baseline_sanity.json",
        toy_dir / "manifest.json",
        REPO_ROOT / "eventx" / "config" / "eventx.yaml",
        REPO_ROOT / "eventx" / "tasks" / "select_toy_markets.py",
        REPO_ROOT / "eventx" / "tasks" / "toy_slice.py",
    ]


def dataset_id(files: dict[str, dict[str, Any]]) -> str:
    payload = "\n".join(f"{name}:{details['sha256']}" for name, details in sorted(files.items()))
    return "eventx-toy-" + hashlib.sha256(payload.encode()).hexdigest()[:20]


def verify_manifest(path: Path) -> dict[str, Any]:
    manifest = json.loads(path.read_text())
    failures = []
    for name, expected in manifest["files"].items():
        source = REPO_ROOT / name
        if not source.exists():
            failures.append({"path": name, "error": "missing"})
            continue
        actual = hash_file(source)
        if actual["sha256"] != expected["sha256"]:
            failures.append(
                {
                    "path": name,
                    "error": "sha256_mismatch",
                    "expected": expected["sha256"],
                    "actual": actual["sha256"],
                }
            )
    return {
        "status": "ok" if not failures else "failed",
        "dataset_id": manifest.get("dataset_id"),
        "checked_files": len(manifest["files"]),
        "failures": failures,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Freeze or verify the EventX toy dataset")
    parser.add_argument("--toy-dir", type=Path, default=REPO_ROOT / "data" / "v1" / "toy")
    parser.add_argument("--horizon-min", type=int, default=30)
    parser.add_argument("--out", type=Path)
    parser.add_argument("--force", action="store_true")
    parser.add_argument("--verify", action="store_true")
    args = parser.parse_args()

    out_path = args.out or args.toy_dir / "frozen_manifest.json"
    if args.verify:
        if not out_path.exists():
            raise SystemExit(f"Frozen manifest does not exist: {out_path}")
        result = verify_manifest(out_path)
        print(json.dumps(result, indent=2, sort_keys=True))
        if result["status"] != "ok":
            raise SystemExit(1)
        return

    if out_path.exists() and not args.force:
        raise SystemExit(f"Refusing to replace existing freeze without --force: {out_path}")

    selection_report = json.loads((args.toy_dir / "market_selection_report.json").read_text())
    build_manifest = json.loads((args.toy_dir / "manifest.json").read_text())
    if selection_report.get("selection_basis") != "training_period_only":
        raise SystemExit("Selection report is not training-period-only.")
    if build_manifest.get("selection_basis") != "training_period_only":
        raise SystemExit("Build manifest is not training-period-only.")
    required_splits = {"train", "validation", "test"}
    if not required_splits <= set(build_manifest.get("eligible_split_counts", {})):
        raise SystemExit("Train, validation, and test must all contain eligible rows before freezing.")
    if int(build_manifest.get("selected_outcomes", 0)) != 20:
        raise SystemExit("Expected exactly 20 selected outcomes before freezing.")

    paths = default_paths(args.toy_dir, args.horizon_min)
    missing = [str(path) for path in paths if not path.exists()]
    if missing:
        raise SystemExit("Missing freeze inputs: " + ", ".join(missing))
    files = {relative(path): hash_file(path) for path in paths}
    frozen = {
        "freeze_schema": 1,
        "locked": True,
        "created_at": datetime.now(UTC).isoformat().replace("+00:00", "Z"),
        "dataset_id": dataset_id(files),
        "selection_basis": "training_period_only",
        "cohort_sha256": files[relative(args.toy_dir / "selected_markets.jsonl")]["sha256"],
        "extract_version": build_manifest["extract_version"],
        "window": build_manifest["window"],
        "split_boundaries": build_manifest["split_boundaries"],
        "selected_outcomes": build_manifest["selected_outcomes"],
        "files": files,
    }
    out_path.parent.mkdir(parents=True, exist_ok=True)
    temporary = out_path.with_suffix(out_path.suffix + ".tmp")
    temporary.write_text(json.dumps(frozen, indent=2, sort_keys=True) + "\n")
    temporary.replace(out_path)
    print(json.dumps(frozen, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
