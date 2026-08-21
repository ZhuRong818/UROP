"""Verify the closed-window EventX v2.1 reconciliation and cohort freeze."""

from __future__ import annotations

import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
from typing import Any, Iterator

from eventx.settings import REPO_ROOT


DEFAULT_PROTOCOL = REPO_ROOT / "eventx" / "release" / "v2_1" / "protocol.json"
DEFAULT_RECONCILIATION = (
    REPO_ROOT / "data" / "v2_1" / "selection" / "reconciled"
    / "reconciliation_manifest.json"
)
DEFAULT_COVERAGE = (
    REPO_ROOT / "data" / "v2_1" / "selection" / "reconciled"
    / "coverage_report.json"
)
DEFAULT_ACTIVITY = REPO_ROOT / "data" / "v2_1" / "selection" / "activity_report.json"
DEFAULT_COHORT = REPO_ROOT / "data" / "v2_1" / "cohort" / "cohort_freeze_manifest.json"
PROHIBITED_FIELDS = {
    "forward_logodds",
    "forward_return",
    "label",
    "metric",
    "prediction",
    "probability_prediction",
    "target",
    "y",
    "y_jump",
}


def load_object(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text())
    if not isinstance(value, dict):
        raise ValueError(f"{path} must contain a JSON object")
    return value


def read_jsonl(path: Path) -> Iterator[dict[str, Any]]:
    with path.open() as handle:
        for line_number, line in enumerate(handle, start=1):
            if not line.strip():
                continue
            value = json.loads(line)
            if not isinstance(value, dict):
                raise ValueError(f"{path}:{line_number} must be a JSON object")
            yield value


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def sha256_line_prefix(path: Path, line_count: int) -> tuple[str, int]:
    digest = hashlib.sha256()
    bytes_read = 0
    with path.open("rb") as handle:
        for index in range(line_count):
            line = handle.readline()
            if not line:
                raise ValueError(f"{path} ended at line {index}; expected {line_count}")
            digest.update(line)
            bytes_read += len(line)
    return digest.hexdigest(), bytes_read


def repo_path(value: str) -> Path:
    path = (REPO_ROOT / value).resolve()
    path.relative_to(REPO_ROOT.resolve())
    return path


def check_label_seal(value: dict[str, Any], name: str, failures: list[str]) -> None:
    if value.get("label_blind") is not True or value.get("labels_read") != []:
        failures.append(f"{name}: label-blind seal is invalid")


def check_hash(
    path: Path,
    specification: dict[str, Any],
    name: str,
    failures: list[str],
) -> None:
    if not path.is_file():
        failures.append(f"{name}: missing {path}")
        return
    if "bytes" in specification and path.stat().st_size != specification["bytes"]:
        failures.append(f"{name}: byte count mismatch")
    if sha256_file(path) != specification.get("sha256"):
        failures.append(f"{name}: SHA-256 mismatch")


def check_hash_map(
    values: dict[str, str],
    name: str,
    failures: list[str],
) -> None:
    for relative, expected in values.items():
        path = repo_path(relative)
        if not path.is_file():
            failures.append(f"{name}: missing {relative}")
        elif sha256_file(path) != expected:
            failures.append(f"{name}: SHA-256 mismatch for {relative}")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--protocol", type=Path, default=DEFAULT_PROTOCOL)
    parser.add_argument("--reconciliation", type=Path, default=DEFAULT_RECONCILIATION)
    parser.add_argument("--coverage", type=Path, default=DEFAULT_COVERAGE)
    parser.add_argument("--activity", type=Path, default=DEFAULT_ACTIVITY)
    parser.add_argument("--cohort", type=Path, default=DEFAULT_COHORT)
    args = parser.parse_args()

    protocol = load_object(args.protocol)
    reconciliation = load_object(args.reconciliation)
    coverage = load_object(args.coverage)
    activity = load_object(args.activity)
    cohort = load_object(args.cohort)
    failures: list[str] = []

    protocol_id = protocol.get("protocol_id")
    selection = protocol.get("windows", {}).get("selection", {})
    selection_start = selection.get("start")
    selection_end = selection.get("end_exclusive")
    for name, value in (
        ("reconciliation", reconciliation),
        ("coverage", coverage),
        ("activity", activity),
        ("cohort", cohort),
    ):
        if value.get("protocol_id") != protocol_id:
            failures.append(f"{name}: protocol ID mismatch")
        check_label_seal(value, name, failures)

    if reconciliation.get("status") != "complete":
        failures.append("reconciliation: status is not complete")
    if reconciliation.get("selection_start") != selection_start:
        failures.append("reconciliation: selection start mismatch")
    if reconciliation.get("selection_end_exclusive") != selection_end:
        failures.append("reconciliation: selection end mismatch")
    for relative, specification in reconciliation.get("outputs", {}).items():
        check_hash(repo_path(relative), specification, f"reconciliation output {relative}", failures)
    check_hash_map(reconciliation.get("input_hashes", {}), "reconciliation input", failures)
    for relative, specification in reconciliation.get("prospective_seed", {}).get(
        "files", {}
    ).items():
        path = repo_path(relative)
        if not path.is_file():
            failures.append(f"prospective seed: missing {relative}")
            continue
        digest, prefix_bytes = sha256_line_prefix(path, int(specification["rows_scanned"]))
        if digest != specification.get("seeded_prefix_sha256"):
            failures.append(f"prospective seed: prefix SHA-256 mismatch for {relative}")
        if prefix_bytes != specification.get("seeded_prefix_bytes"):
            failures.append(f"prospective seed: prefix byte count mismatch for {relative}")

    candidate_counts = coverage.get("candidate_markets", {})
    candidate_total = sum(int(value) for value in candidate_counts.values())
    endpoint_counts = coverage.get("endpoint_status_counts", {})
    if coverage.get("status") != "complete":
        failures.append("coverage: status is not complete")
    if endpoint_counts != {"done": candidate_total}:
        failures.append("coverage: not every candidate endpoint is done")
    if coverage.get("collector_cursor_evidence", {}).get("status") != "complete":
        failures.append("coverage: collector cursors do not cover the cutoff")
    if coverage.get("selection_start") != selection_start:
        failures.append("coverage: selection start mismatch")
    if coverage.get("selection_end_exclusive") != selection_end:
        failures.append("coverage: selection end mismatch")

    check_hash_map(activity.get("input_hashes", {}), "activity input", failures)
    if activity.get("selection_start") != selection_start:
        failures.append("activity: selection start mismatch")
    if activity.get("selection_end_exclusive") != selection_end:
        failures.append("activity: selection end mismatch")
    activity_output = activity.get("output", {})
    if activity_output.get("path"):
        check_hash(
            repo_path(activity_output["path"]),
            activity_output,
            "activity output",
            failures,
        )
    else:
        failures.append("activity: output path is missing")

    check_hash_map(cohort.get("input_hashes", {}), "cohort input", failures)
    if cohort.get("status") != "frozen":
        failures.append("cohort: status is not frozen")
    if cohort.get("selection_end_exclusive") != selection_end:
        failures.append("cohort: selection end mismatch")
    cohort_output = cohort.get("output", {})
    selected_path: Path | None = None
    if cohort_output.get("path"):
        selected_path = repo_path(cohort_output["path"])
        check_hash(selected_path, cohort_output, "cohort output", failures)
    else:
        failures.append("cohort: output path is missing")

    selected_rows: list[dict[str, Any]] = []
    if selected_path is not None and selected_path.is_file():
        selected_rows = list(read_jsonl(selected_path))
    if len(selected_rows) != int(cohort.get("selected_markets", -1)):
        failures.append("cohort: selected row count mismatch")
    maximum = (
        len(protocol.get("cohort", {}).get("venues", []))
        * len(protocol.get("cohort", {}).get("categories", []))
        * int(protocol.get("cohort", {}).get("max_per_venue_category", 0))
    )
    if len(selected_rows) > maximum:
        failures.append("cohort: preregistered maximum exceeded")
    groups: Counter[str] = Counter()
    keys: set[tuple[str, str]] = set()
    for index, row in enumerate(selected_rows, start=1):
        prohibited = PROHIBITED_FIELDS.intersection(key.lower() for key in row)
        if prohibited:
            failures.append(f"cohort row {index}: prohibited fields {sorted(prohibited)}")
        key = (str(row.get("venue") or ""), str(row.get("market_id") or ""))
        if not all(key) or key in keys:
            failures.append(f"cohort row {index}: invalid or duplicate market key {key}")
        keys.add(key)
        groups[f"{key[0]}:{row.get('category')}"] += 1
        if row.get("canonical_side") is not True:
            failures.append(f"cohort row {index}: canonical side is not YES")
    if dict(sorted(groups.items())) != cohort.get("group_counts", {}):
        failures.append("cohort: group counts do not match selected rows")

    output = {
        "candidate_markets_reconciled": candidate_total,
        "checked_reconciliation_outputs": len(reconciliation.get("outputs", {})),
        "failures": failures,
        "label_blind": True,
        "protocol_id": protocol_id,
        "selected_markets": len(selected_rows),
        "status": "ok" if not failures else "failed",
    }
    print(json.dumps(output, indent=2, sort_keys=True))
    if failures:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
