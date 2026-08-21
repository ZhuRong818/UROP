"""Freeze the accepted KOL association rule and its independent audit evidence."""

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


def default_paths(root: Path) -> list[Path]:
    return [
        REPO_ROOT / "eventx" / "features" / "kol_association.py",
        REPO_ROOT / "eventx" / "features" / "KOL_BLIND_REVIEW_GUIDE.md",
        root / "curated" / "market_entities.jsonl",
        root / "curated" / "kol_market_assoc.jsonl",
        root / "curated" / "kol_association_report.json",
        root / "audit_v3_blind" / "kol_association_blind_review_adjudicated.jsonl",
        root
        / "audit_v3_blind"
        / "kol_association_disagreement_adjudication_completed.jsonl",
        root / "audit_v3_blind" / "kol_association_disagreement_adjudication_report.json",
    ]


def verify_manifest(path: Path) -> dict[str, Any]:
    manifest = json.loads(path.read_text())
    failures: list[dict[str, str]] = []
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
                    "expected": str(expected["sha256"]),
                    "actual": str(actual["sha256"]),
                }
            )
    return {
        "status": "ok" if not failures else "failed",
        "kol_rule_id": manifest.get("kol_rule_id"),
        "dataset_id": manifest.get("dataset_id"),
        "checked_files": len(manifest["files"]),
        "failures": failures,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Freeze or verify accepted KOL rule v3")
    parser.add_argument("--version", default="v1")
    parser.add_argument("--out", type=Path)
    parser.add_argument("--force", action="store_true")
    parser.add_argument("--verify", action="store_true")
    args = parser.parse_args()

    root = REPO_ROOT / "data" / args.version
    out_path = args.out or root / "curated" / "kol_rule_v3_frozen_manifest.json"
    if args.verify:
        if not out_path.exists():
            raise SystemExit(f"Frozen KOL rule manifest does not exist: {out_path}")
        result = verify_manifest(out_path)
        print(json.dumps(result, indent=2, sort_keys=True))
        if result["status"] != "ok":
            raise SystemExit(1)
        return
    if out_path.exists() and not args.force:
        raise SystemExit(f"Refusing to replace existing freeze without --force: {out_path}")

    toy_freeze_path = root / "toy" / "frozen_manifest.json"
    association_report_path = root / "curated" / "kol_association_report.json"
    audit_report_path = (
        root / "audit_v3_blind" / "kol_association_disagreement_adjudication_report.json"
    )
    for path in (toy_freeze_path, association_report_path, audit_report_path):
        if not path.exists():
            raise SystemExit(f"Missing required input: {path}")

    toy_freeze = json.loads(toy_freeze_path.read_text())
    association_report = json.loads(association_report_path.read_text())
    audit_report = json.loads(audit_report_path.read_text())
    metrics = audit_report["adjudicated_rule_v3_metrics"]
    thresholds = {"precision_min": 0.85, "recall_min": 0.90}
    checks = {
        "association_rule_is_v3": association_report.get("association_rule") == "rule_v3",
        "audit_complete": audit_report.get("status") == "completed",
        "precision_pass": float(metrics["precision"]) >= thresholds["precision_min"],
        "recall_pass": float(metrics["recall"]) >= thresholds["recall_min"],
        "toy_dataset_locked": toy_freeze.get("locked") is True,
    }
    if not all(checks.values()):
        raise SystemExit("Cannot freeze KOL rule; failed checks: " + json.dumps(checks))

    paths = default_paths(root)
    missing = [relative(path) for path in paths if not path.exists()]
    if missing:
        raise SystemExit("Missing freeze inputs: " + ", ".join(missing))
    files = {relative(path): hash_file(path) for path in paths}
    identity_payload = "\n".join(
        f"{name}:{details['sha256']}" for name, details in sorted(files.items())
    )
    rule_id = "eventx-kol-rule-v3-" + hashlib.sha256(identity_payload.encode()).hexdigest()[:20]
    frozen = {
        "freeze_schema": 1,
        "locked": True,
        "status": "accepted_for_b1",
        "accepted_at": datetime.now(UTC).isoformat().replace("+00:00", "Z"),
        "association_rule": "rule_v3",
        "kol_rule_id": rule_id,
        "dataset_id": toy_freeze["dataset_id"],
        "extract_version": association_report["version"],
        "test_cutoff_exclusive": toy_freeze["split_boundaries"]["test_start"],
        "acceptance_policy": {
            **thresholds,
            "decision": "accepted",
            "basis": "independently adjudicated pre-test blind audit",
        },
        "adjudicated_metrics": metrics,
        "checks": checks,
        "association_counts": {
            "associations": association_report["associations"],
            "matched_tweets": association_report["matched_tweets"],
            "selected_markets": association_report["selected_markets"],
        },
        "test_policy": (
            "No test-period examples were inspected or used to develop rule_v3. "
            "The frozen rule may be applied mechanically to test timestamps."
        ),
        "files": files,
    }
    out_path.parent.mkdir(parents=True, exist_ok=True)
    temporary = out_path.with_suffix(out_path.suffix + ".tmp")
    temporary.write_text(json.dumps(frozen, indent=2, sort_keys=True) + "\n")
    temporary.replace(out_path)
    print(json.dumps(frozen, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
