"""Extract the opened KOL-v1 false positives and false negatives for analysis."""

from __future__ import annotations

from collections import Counter
import hashlib
import json
from pathlib import Path
from typing import Any

from eventx.settings import REPO_ROOT


AUDIT_ROOT = REPO_ROOT / "data" / "v2_1" / "association" / "v1_audit"
REVIEW = REPO_ROOT / "eventx" / "release" / "v2_1" / "eventx_v2_1_blind_review_completed.jsonl"
OUTPUT = AUDIT_ROOT / "kol_error_analysis_rows.jsonl"
REPORT = AUDIT_ROOT / "kol_error_extraction_report.json"


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    with path.open() as handle:
        for line_number, line in enumerate(handle, start=1):
            if not line.strip():
                continue
            value = json.loads(line)
            if not isinstance(value, dict):
                raise ValueError(f"{path}:{line_number} must be an object")
            rows.append(value)
    return rows


def indexed(path: Path) -> dict[str, dict[str, Any]]:
    result: dict[str, dict[str, Any]] = {}
    for row in read_jsonl(path):
        audit_id = str(row.get("audit_id") or "")
        if not audit_id or audit_id in result:
            raise ValueError(f"{path} has a missing or duplicate audit_id")
        result[audit_id] = row
    return result


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def relative(path: Path) -> str:
    return str(path.resolve().relative_to(REPO_ROOT.resolve()))


def atomic_write(path: Path, payload: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(payload)
    temporary.replace(path)


def main() -> None:
    blind_path = AUDIT_ROOT / "association_blind_review.jsonl"
    key_path = AUDIT_ROOT / "association_blind_key.jsonl"
    freeze_path = AUDIT_ROOT / "audit_freeze_manifest.json"
    score_path = AUDIT_ROOT / "association_audit_report.json"
    freeze = json.loads(freeze_path.read_text())
    for path in (blind_path, key_path, REVIEW, score_path):
        expected = freeze["frozen_files"][relative(path)]["sha256"]
        if sha256_file(path) != expected:
            raise SystemExit(f"frozen file hash changed: {path}")

    blind = indexed(blind_path)
    key = indexed(key_path)
    reviewed = indexed(REVIEW)
    errors: list[dict[str, Any]] = []
    for audit_id in sorted(key):
        keyed = key[audit_id]
        review = reviewed[audit_id]
        if keyed["source"] != "kol":
            continue
        error_type = None
        if keyed["rule_prediction"] == "matched" and review["review_label"] == "not_relevant":
            error_type = "false_positive"
        elif keyed["rule_prediction"] == "hard_unmatched" and review["review_label"] == "relevant":
            error_type = "false_negative"
        if error_type is None:
            continue
        public = blind[audit_id]
        errors.append(
            {
                "audit_id": audit_id,
                "category": keyed["category"],
                "content_hash": keyed["content_hash"],
                "doc_id": keyed["doc_id"],
                "document_event_ts": public["document_event_ts"],
                "document_metadata": public["document_metadata"],
                "document_text": public["document_text"],
                "error_type": error_type,
                "evidence": keyed["evidence"],
                "market_id": keyed["market_id"],
                "market_question": public["market_question"],
                "match_reasons": keyed["match_reasons"],
                "match_terms": keyed["match_terms"],
                "pair_id": keyed["pair_id"],
                "review_confidence": review["review_confidence"],
                "review_label": review["review_label"],
                "review_rationale": review["review_rationale"],
                "rule_prediction": keyed["rule_prediction"],
                "venue": keyed["venue"],
            }
        )

    counts = Counter(row["error_type"] for row in errors)
    if counts != Counter({"false_negative": 22, "false_positive": 15}):
        raise SystemExit(f"unexpected KOL error counts: {dict(counts)}")
    atomic_write(OUTPUT, "".join(json.dumps(row, sort_keys=True) + "\n" for row in errors))
    report = {
        "association_rule": "eventx-v2.1-association-rule-v1-candidate",
        "development_only": True,
        "error_counts": dict(sorted(counts.items())),
        "input_hashes": {
            relative(path): sha256_file(path)
            for path in (blind_path, key_path, REVIEW, score_path, freeze_path)
        },
        "output": {"path": relative(OUTPUT), "rows": len(errors), "sha256": sha256_file(OUTPUT)},
        "status": "opened_errors_extracted",
    }
    atomic_write(REPORT, json.dumps(report, indent=2, sort_keys=True) + "\n")
    print(json.dumps(report, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
