"""Verify the October-deadline EventX v2.1 preregistration and its lineage."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from eventx.settings import REPO_ROOT
from eventx.tasks.verify_v2_preregistration import (
    V1_RECEIPT,
    load_json,
    repo_path,
    sha256_file,
)


DEFAULT_MANIFEST = (
    REPO_ROOT / "eventx" / "release" / "v2_1" / "preregistration_manifest.json"
)


def verify_artifact(
    name: str,
    specification: dict[str, Any],
    failures: list[str],
) -> None:
    try:
        path = repo_path(specification["path"])
    except (KeyError, TypeError, ValueError) as exc:
        failures.append(f"{name}: invalid path: {exc}")
        return
    if not path.is_file():
        failures.append(f"{name}: missing {specification.get('path')}")
        return
    if path.stat().st_size != specification.get("bytes"):
        failures.append(f"{name}: byte count mismatch")
    if sha256_file(path) != specification.get("sha256"):
        failures.append(f"{name}: SHA-256 mismatch")


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
        failures.append("preregistration manifest is not locked")
    if manifest.get("status") != "preregistered_labels_uninspected":
        failures.append("unexpected manifest status")
    for name, specification in manifest.get("artifacts", {}).items():
        verify_artifact(name, specification, failures)

    protocol_path = repo_path(manifest["protocol"]["path"])
    protocol = load_json(protocol_path)
    if sha256_file(protocol_path) != manifest["protocol"].get("sha256"):
        failures.append("protocol SHA-256 mismatch")
    if protocol.get("protocol_id") != manifest.get("protocol_id"):
        failures.append("protocol ID mismatch")
    if protocol.get("status") != "preregistered_labels_uninspected":
        failures.append("protocol is not label-uninspected")
    if protocol.get("holdout", {}).get("labels_uninspected") is not True:
        failures.append("holdout labels are not sealed")
    if protocol.get("holdout", {}).get("reruns_permitted") is not False:
        failures.append("holdout reruns are not prohibited")
    if protocol.get("deadline", {}).get("completion_at") != "2026-10-31T23:59:59Z":
        failures.append("October completion deadline mismatch")

    prior = protocol.get("prior_protocol", {})
    prior_path = repo_path(prior.get("path", ""))
    if prior.get("status") != "superseded_before_selection_and_labels":
        failures.append("prior protocol supersession state is invalid")
    if not prior_path.is_file() or sha256_file(prior_path) != prior.get("sha256"):
        failures.append("prior protocol lineage hash mismatch")

    label_seal = manifest.get("label_seal", {})
    for key in (
        "development_labels_created",
        "development_labels_inspected",
        "holdout_labels_created",
        "holdout_labels_inspected",
    ):
        if label_seal.get(key) is not False:
            failures.append(f"{key} must be false")

    receipt = load_json(V1_RECEIPT)
    if receipt.get("status") != "consumed" or receipt.get("rerun_permitted") is not False:
        failures.append("v1 holdout state is not consumed/no-rerun")
    if receipt.get("dataset_id") != protocol.get("prior_v1_holdout", {}).get("dataset_id"):
        failures.append("v1 holdout dataset ID mismatch")

    output = {
        "checked_artifacts": len(manifest.get("artifacts", {})),
        "deadline": protocol.get("deadline", {}).get("completion_at"),
        "failures": failures,
        "labels_inspected": False,
        "prior_protocol": prior.get("protocol_id"),
        "protocol_id": protocol.get("protocol_id"),
        "status": "ok" if not failures else "failed",
        "v1_holdout_state": "consumed",
        "v2_1_holdout_state": "future_reserved_uninspected",
    }
    print(json.dumps(output, indent=2, sort_keys=True))
    if failures:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
