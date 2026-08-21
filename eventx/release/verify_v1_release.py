"""Verify the frozen EventX v1 pilot release and its consumed-holdout guard."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_MANIFEST = REPO_ROOT / "eventx" / "release" / "v1" / "release_manifest.json"


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def load_json(path: Path) -> dict[str, Any]:
    with path.open() as handle:
        value = json.load(handle)
    if not isinstance(value, dict):
        raise ValueError(f"{path} must contain a JSON object")
    return value


def resolve_repo_path(value: str) -> Path:
    path = Path(value)
    if path.is_absolute():
        raise ValueError(f"release paths must be repository-relative: {value}")
    resolved = (REPO_ROOT / path).resolve()
    if not resolved.is_relative_to(REPO_ROOT.resolve()):
        raise ValueError(f"release path escapes repository root: {value}")
    return resolved


def verify_file(name: str, specification: dict[str, Any]) -> list[str]:
    failures: list[str] = []
    relative_path = specification.get("path")
    expected_hash = specification.get("sha256")
    if not isinstance(relative_path, str) or not isinstance(expected_hash, str):
        return [f"{name}: path and sha256 are required"]

    try:
        path = resolve_repo_path(relative_path)
    except ValueError as exc:
        return [f"{name}: {exc}"]

    if not path.is_file():
        return [f"{name}: missing {relative_path}"]

    expected_bytes = specification.get("bytes")
    actual_bytes = path.stat().st_size
    if expected_bytes is not None and actual_bytes != expected_bytes:
        failures.append(
            f"{name}: byte count mismatch for {relative_path}: "
            f"expected {expected_bytes}, found {actual_bytes}"
        )

    actual_hash = sha256_file(path)
    if actual_hash != expected_hash:
        failures.append(
            f"{name}: SHA-256 mismatch for {relative_path}: "
            f"expected {expected_hash}, found {actual_hash}"
        )
    return failures


def verify_state(manifest: dict[str, Any]) -> list[str]:
    failures: list[str] = []
    expected_dataset = manifest.get("dataset_ids", {}).get("out_of_time")

    receipt_path = resolve_repo_path(
        manifest["integrity_guards"]["consumption_receipt"]["path"]
    )
    result_path = resolve_repo_path(manifest["canonical_result"]["path"])
    receipt = load_json(receipt_path)
    result = load_json(result_path)

    if receipt.get("status") != "consumed":
        failures.append("holdout receipt status must be consumed")
    if receipt.get("rerun_permitted") is not False:
        failures.append("holdout receipt must set rerun_permitted to false")
    if receipt.get("dataset_id") != expected_dataset:
        failures.append("holdout receipt dataset_id does not match release manifest")
    if result.get("dataset_id") != expected_dataset:
        failures.append("final result dataset_id does not match release manifest")
    if result.get("status") != "one_shot_oot_confirmatory_evaluation_complete":
        failures.append("final result is not marked one-shot complete")
    if result.get("policy") != manifest["integrity_guards"]["post_evaluation_policy"]:
        failures.append("final result policy does not match the release policy")
    return failures


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--manifest",
        type=Path,
        default=DEFAULT_MANIFEST,
        help="release manifest path (default: eventx/release/v1/release_manifest.json)",
    )
    args = parser.parse_args()

    manifest_path = args.manifest
    if not manifest_path.is_absolute():
        manifest_path = (Path.cwd() / manifest_path).resolve()
    manifest = load_json(manifest_path)

    failures: list[str] = []
    for name, specification in manifest.get("artifacts", {}).items():
        if not isinstance(specification, dict):
            failures.append(f"{name}: artifact specification must be an object")
            continue
        failures.extend(verify_file(name, specification))

    failures.extend(verify_state(manifest))
    output = {
        "checked_artifacts": len(manifest.get("artifacts", {})),
        "dataset_ids": manifest.get("dataset_ids"),
        "distribution_decision": manifest.get("distribution", {}).get("decision"),
        "failures": failures,
        "holdout_state": "consumed",
        "redistribution_cleared": manifest.get("distribution", {}).get(
            "redistribution_cleared"
        ),
        "release_id": manifest.get("release_id"),
        "status": "ok" if not failures else "failed",
    }
    print(json.dumps(output, indent=2, sort_keys=True))
    if failures:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
