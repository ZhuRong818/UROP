"""Freeze an accepted EventX v2.1 taxonomy audit into the canonical paths."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import shutil
from typing import Any, Iterator

from eventx.settings import REPO_ROOT


DEFAULT_SOURCE = REPO_ROOT / "data" / "v2_1" / "taxonomy_v7"
DEFAULT_OUTPUT = REPO_ROOT / "data" / "v2_1" / "taxonomy"
CATEGORIES = {"politics", "crypto", "sports", "macro", "other"}


def read_jsonl(path: Path) -> Iterator[dict[str, Any]]:
    with path.open() as handle:
        for line_number, line in enumerate(handle, start=1):
            if not line.strip():
                continue
            value = json.loads(line)
            if not isinstance(value, dict):
                raise ValueError(f"{path}:{line_number} must be a JSON object")
            yield value


def load_object(path: Path) -> dict[str, Any]:
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


def relative(path: Path) -> str:
    return str(path.resolve().relative_to(REPO_ROOT.resolve()))


def rfc3339_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def atomic_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    with temporary.open("w") as handle:
        for row in rows:
            handle.write(json.dumps(row, sort_keys=True) + "\n")
    temporary.replace(path)


def atomic_json(path: Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n")
    temporary.replace(path)


def atomic_copy(source: Path, destination: Path) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)
    temporary = destination.with_suffix(destination.suffix + ".tmp")
    shutil.copyfile(source, temporary)
    temporary.replace(destination)


def validate_audit(audit: dict[str, Any]) -> None:
    failures: list[str] = []
    overall = audit.get("overall", {})
    if audit.get("status") != "accepted":
        failures.append("status is not accepted")
    if audit.get("label_blind") is not True or audit.get("labels_read") != []:
        failures.append("audit is not recorded as label-blind")
    if int(audit.get("review_rows", 0)) < 200:
        failures.append("fewer than 200 audit rows")
    if float(overall.get("precision", 0)) < 0.90:
        failures.append("overall precision below 0.90")
    if float(overall.get("recall", 0)) < 0.90:
        failures.append("overall recall below 0.90")
    for category, values in audit.get("by_category", {}).items():
        reviewed = int(values.get("review_rows", 0))
        precision = values.get("precision")
        if reviewed >= 20 and (precision is None or float(precision) < 0.80):
            failures.append(f"{category} precision below 0.80")
    if failures:
        raise ValueError("cannot freeze taxonomy: " + "; ".join(failures))


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, default=DEFAULT_SOURCE)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()
    source = args.source.resolve()
    output = args.output.resolve()

    mapping_path = source / "market_categories.jsonl"
    build_path = source / "taxonomy_build_report.json"
    audit_path = source / "audit_report.json"
    guide_path = REPO_ROOT / "eventx" / "release" / "v2" / "TAXONOMY_GUIDE.md"
    protocol_path = REPO_ROOT / "eventx" / "release" / "v2_1" / "protocol.json"
    build = load_object(build_path)
    audit = load_object(audit_path)
    validate_audit(audit)
    taxonomy_version = str(audit.get("taxonomy_version") or "")
    if not taxonomy_version or build.get("taxonomy_version") != taxonomy_version:
        raise ValueError("taxonomy versions differ between build and audit")
    if build.get("label_blind") is not True or build.get("labels_read") != []:
        raise ValueError("taxonomy build is not recorded as label-blind")
    if build.get("mapping", {}).get("sha256") != sha256_file(mapping_path):
        raise ValueError("mapping hash differs from the frozen build report")

    accepted: list[dict[str, Any]] = []
    keys: set[tuple[str, str]] = set()
    for row in read_jsonl(mapping_path):
        key = (str(row.get("venue") or ""), str(row.get("market_id") or ""))
        if not all(key) or key in keys:
            raise ValueError(f"missing or duplicate market key {key}")
        keys.add(key)
        if row.get("category") not in CATEGORIES:
            raise ValueError(f"invalid category for {key}: {row.get('category')!r}")
        if row.get("taxonomy_version") != taxonomy_version:
            raise ValueError(f"taxonomy version mismatch for {key}")
        frozen = dict(row)
        provenance = dict(frozen.get("provenance") or {})
        provenance.update(
            {
                "audit_path": relative(audit_path),
                "audit_status": "accepted",
                "review_rows": int(audit["review_rows"]),
            }
        )
        frozen["provenance"] = provenance
        frozen["review_status"] = "accepted_independent_blind_audit"
        accepted.append(frozen)

    if len(accepted) != int(build.get("candidate_count", -1)):
        raise ValueError("mapping row count differs from the build report")
    accepted.sort(key=lambda row: (row["venue"], row["market_id"]))
    final_mapping = output / "market_categories.jsonl"
    final_audit = output / "audit_report.json"
    final_build = output / "accepted_taxonomy_build_report.json"
    atomic_jsonl(final_mapping, accepted)
    atomic_copy(audit_path, final_audit)
    atomic_copy(build_path, final_build)

    evidence = [
        guide_path,
        protocol_path,
        mapping_path,
        build_path,
        source / "blind_review_sample.jsonl",
        source / "blind_review_key.jsonl",
        source / "reviewer_1.jsonl",
        source / "reviewer_2.jsonl",
        source / "audit_preparation_report.json",
        source / "audit_report.json",
    ]
    adjudication_path = source / "adjudication.jsonl"
    if adjudication_path.exists():
        evidence.append(adjudication_path)
    manifest = {
        "candidate_count": len(accepted),
        "frozen_at": rfc3339_now(),
        "input_hashes": {relative(path): sha256_file(path) for path in evidence},
        "label_blind": True,
        "labels_read": [],
        "output": {
            "audit_path": relative(final_audit),
            "audit_sha256": sha256_file(final_audit),
            "mapping_path": relative(final_mapping),
            "mapping_sha256": sha256_file(final_mapping),
        },
        "protocol_id": load_object(protocol_path)["protocol_id"],
        "review_rows": int(audit["review_rows"]),
        "status": "accepted_and_frozen",
        "taxonomy_version": taxonomy_version,
    }
    atomic_json(output / "taxonomy_freeze_manifest.json", manifest)
    print(json.dumps(manifest, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
