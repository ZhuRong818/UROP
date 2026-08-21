"""Verify the EventX v2 preregistration and its separation from consumed v1."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any

from eventx.settings import REPO_ROOT


DEFAULT_MANIFEST = REPO_ROOT / "eventx" / "release" / "v2" / "preregistration_manifest.json"
V1_RECEIPT = (
    REPO_ROOT
    / "data"
    / "v1_oot_20260723_20260730"
    / "holdout_consumption_receipt.json"
)


def load_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text())
    if not isinstance(value, dict):
        raise ValueError(f"{path} must contain a JSON object")
    return value


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def repo_path(value: str) -> Path:
    path = Path(value)
    if path.is_absolute():
        raise ValueError(f"absolute path is not allowed: {value}")
    resolved = (REPO_ROOT / path).resolve()
    if not resolved.is_relative_to(REPO_ROOT.resolve()):
        raise ValueError(f"path escapes repository root: {value}")
    return resolved


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST)
    args = parser.parse_args()
    manifest_path = args.manifest
    if not manifest_path.is_absolute():
        manifest_path = (Path.cwd() / manifest_path).resolve()
    manifest = load_json(manifest_path)

    failures: list[str] = []
    if manifest.get("preregistration_schema") != 1:
        failures.append("unsupported preregistration manifest schema")
    if manifest.get("locked") is not True:
        failures.append("preregistration manifest must be locked")
    if manifest.get("status") != "preregistered_labels_uninspected":
        failures.append("manifest status is not preregistered_labels_uninspected")

    for name, specification in manifest.get("artifacts", {}).items():
        try:
            path = repo_path(specification["path"])
        except (KeyError, TypeError, ValueError) as exc:
            failures.append(f"{name}: invalid path: {exc}")
            continue
        if not path.is_file():
            failures.append(f"{name}: missing {specification.get('path')}")
            continue
        actual_bytes = path.stat().st_size
        if actual_bytes != specification.get("bytes"):
            failures.append(
                f"{name}: byte count mismatch: expected {specification.get('bytes')}, "
                f"found {actual_bytes}"
            )
        actual_hash = sha256_file(path)
        if actual_hash != specification.get("sha256"):
            failures.append(f"{name}: SHA-256 mismatch")

    protocol_path = repo_path(manifest["protocol"]["path"])
    protocol = load_json(protocol_path)
    if sha256_file(protocol_path) != manifest["protocol"].get("sha256"):
        failures.append("protocol SHA-256 does not match manifest protocol reference")
    if protocol.get("protocol_id") != manifest.get("protocol_id"):
        failures.append("protocol ID does not match manifest")
    if protocol.get("status") != "preregistered_labels_uninspected":
        failures.append("protocol status is not preregistered_labels_uninspected")
    if protocol.get("holdout", {}).get("labels_uninspected") is not True:
        failures.append("v2 holdout labels must be marked uninspected")
    if protocol.get("holdout", {}).get("reruns_permitted") is not False:
        failures.append("v2 holdout reruns must be prohibited")
    label_seal = manifest.get("label_seal", {})
    if label_seal.get("development_labels_created") is not False:
        failures.append("development labels must not exist at preregistration")
    if label_seal.get("development_labels_inspected") is not False:
        failures.append("development labels must be uninspected")
    if label_seal.get("holdout_labels_created") is not False:
        failures.append("holdout labels must not exist at preregistration")
    if label_seal.get("holdout_labels_inspected") is not False:
        failures.append("holdout labels must be uninspected")

    receipt = load_json(V1_RECEIPT)
    prior_v1 = manifest.get("prior_v1_integrity", {})
    if sha256_file(V1_RECEIPT) != prior_v1.get("receipt_sha256"):
        failures.append("v1 receipt SHA-256 does not match preregistration manifest")
    if receipt.get("status") != "consumed" or receipt.get("rerun_permitted") is not False:
        failures.append("v1 receipt does not preserve consumed/no-rerun state")
    if receipt.get("dataset_id") != protocol.get("prior_v1_holdout", {}).get("dataset_id"):
        failures.append("v1 receipt dataset ID does not match v2 protocol")

    output = {
        "checked_artifacts": len(manifest.get("artifacts", {})),
        "failures": failures,
        "labels_inspected": False,
        "protocol_id": protocol.get("protocol_id"),
        "status": "ok" if not failures else "failed",
        "v1_holdout_state": "consumed",
        "v2_holdout_state": "future_reserved_uninspected",
    }
    print(json.dumps(output, indent=2, sort_keys=True))
    if failures:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
