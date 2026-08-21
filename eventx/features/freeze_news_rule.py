"""Freeze the accepted toy-news candidate extract, association rule, and audit."""

from __future__ import annotations

import argparse
import hashlib
import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from eventx.features.build_kol_features import hash_file
from eventx.settings import REPO_ROOT


def relative(path: Path) -> str:
    return str(path.resolve().relative_to(REPO_ROOT.resolve()))


def verify_manifest(path: Path) -> dict[str, Any]:
    manifest = json.loads(path.read_text())
    failures = []
    for name, expected in manifest["files"].items():
        source = REPO_ROOT / name
        if not source.exists():
            failures.append({"path": name, "error": "missing"})
        elif hash_file(source)["sha256"] != expected["sha256"]:
            failures.append({"path": name, "error": "sha256_mismatch"})
    return {
        "status": "ok" if not failures else "failed",
        "news_rule_id": manifest.get("news_rule_id"),
        "dataset_id": manifest.get("dataset_id"),
        "failures": failures,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Freeze or verify EventX news rule v1")
    parser.add_argument("--version", default="v1")
    parser.add_argument("--out", type=Path)
    parser.add_argument("--verify", action="store_true")
    parser.add_argument("--force", action="store_true")
    args = parser.parse_args()

    root = REPO_ROOT / "data" / args.version
    out_path = args.out or root / "curated" / "news_rule_v1_frozen_manifest.json"
    if args.verify:
        result = verify_manifest(out_path)
        print(json.dumps(result, indent=2, sort_keys=True))
        if result["status"] != "ok":
            raise SystemExit(1)
        return
    if out_path.exists() and not args.force:
        raise SystemExit(f"Refusing to replace existing freeze without --force: {out_path}")

    toy_freeze = json.loads((root / "toy" / "frozen_manifest.json").read_text())
    association_report = json.loads(
        (root / "curated" / "news_association_report.json").read_text()
    )
    review_report = json.loads(
        (root / "audit_news_v1" / "news_association_review_report.json").read_text()
    )
    thresholds = {"precision_min": 0.85, "hard_candidate_recall_min": 0.90}
    checks = {
        "toy_dataset_locked": toy_freeze.get("locked") is True,
        "association_rule_is_v1": association_report.get("association_rule")
        == "news_rule_v1_semantic_v3",
        "blind_review_complete": review_report.get("status") == "completed",
        "precision_pass": float(review_report["precision"]) >= thresholds["precision_min"],
        "recall_pass": float(review_report["recall_on_hard_retrieval_candidates"])
        >= thresholds["hard_candidate_recall_min"],
    }
    if not all(checks.values()):
        raise SystemExit("Cannot freeze news rule; failed checks: " + json.dumps(checks))
    paths = [
        REPO_ROOT / "eventx" / "ingest" / "pull.py",
        REPO_ROOT / "eventx" / "features" / "news_association.py",
        root / "raw" / "news_toy_search.jsonl",
        root / "checkpoints" / "news_toy_search.json",
        root / "curated" / "news_market_assoc.jsonl",
        root / "curated" / "news_association_report.json",
        root / "audit_news_v1" / "news_association_blind_review_completed.jsonl",
        root / "audit_news_v1" / "news_association_blind_key.jsonl",
        root / "audit_news_v1" / "news_association_review_report.json",
    ]
    missing = [relative(path) for path in paths if not path.exists()]
    if missing:
        raise SystemExit("Missing freeze inputs: " + ", ".join(missing))
    files = {relative(path): hash_file(path) for path in paths}
    payload = "\n".join(
        f"{name}:{details['sha256']}" for name, details in sorted(files.items())
    )
    manifest = {
        "freeze_schema": 1,
        "locked": True,
        "status": "accepted_for_news_baseline",
        "accepted_at": datetime.now(UTC).isoformat().replace("+00:00", "Z"),
        "association_rule": "news_rule_v1_semantic_v3",
        "news_rule_id": "eventx-news-rule-v1-"
        + hashlib.sha256(payload.encode()).hexdigest()[:20],
        "dataset_id": toy_freeze["dataset_id"],
        "test_cutoff_exclusive": toy_freeze["split_boundaries"]["test_start"],
        "acceptance_policy": {**thresholds, "decision": "accepted"},
        "review_metrics": {
            key: review_report[key]
            for key in (
                "cases",
                "uncertain_excluded",
                "confusion_matrix",
                "precision",
                "recall_on_hard_retrieval_candidates",
                "f1_on_hard_retrieval_candidates",
            )
        },
        "coverage": {
            "retrieval_rows": association_report["retrieval_rows"],
            "unique_articles_in_window": association_report["unique_articles_in_window"],
            "associations": association_report["associations"],
            "markets_with_matches": association_report["markets_with_matches"],
            "mapped_symbol_markets": 0,
        },
        "checks": checks,
        "files": files,
        "test_policy": (
            "Search queries and semantic rule were fixed and audited using pre-test rows "
            "only. The frozen rule may be applied mechanically to later timestamps."
        ),
    }
    out_path.parent.mkdir(parents=True, exist_ok=True)
    temporary = out_path.with_suffix(out_path.suffix + ".tmp")
    temporary.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n")
    temporary.replace(out_path)
    print(json.dumps(manifest, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
