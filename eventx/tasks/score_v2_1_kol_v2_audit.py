"""Score the completed fresh KOL-v2 blind review against its frozen hidden key."""

from __future__ import annotations

import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
from typing import Any

from eventx.settings import REPO_ROOT


ROOT = REPO_ROOT / "data" / "v2_1" / "association" / "kol_v2_audit"
FREEZE = ROOT / "kol_v2_audit_freeze_manifest.json"
KEY = ROOT / "kol_v2_blind_key.jsonl"
BLIND = REPO_ROOT / "eventx" / "release" / "v2_1" / "eventx_v2_1_kol_v2_blind_review.jsonl"
DEFAULT_REVIEW = REPO_ROOT / "eventx" / "release" / "v2_1" / "eventx_v2_1_kol_v2_blind_review_completed.jsonl"
DEFAULT_OUTPUT = ROOT / "kol_v2_audit_report.json"
MIN_PRECISION = 0.85
MIN_RECALL = 0.90
MIN_SUPPORT = 20
VALID_LABELS = {"relevant", "not_relevant", "uncertain"}
VALID_CONFIDENCE = {"high", "medium", "low"}
BLIND_FIELDS = (
    "audit_id",
    "category",
    "document_event_ts",
    "document_metadata",
    "document_source",
    "document_text",
    "market_question",
    "venue",
)


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    rows = []
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
    rows = read_jsonl(path)
    result = {str(row.get("audit_id") or ""): row for row in rows}
    if "" in result or len(result) != len(rows):
        raise ValueError(f"{path} has missing or duplicate audit IDs")
    return result


def load(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text())
    if not isinstance(value, dict):
        raise ValueError(f"{path} must contain an object")
    return value


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def relative(path: Path) -> str:
    return str(path.resolve().relative_to(REPO_ROOT.resolve()))


def atomic_json(path: Path, value: dict[str, Any]) -> None:
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n")
    temporary.replace(path)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--review", type=Path, default=DEFAULT_REVIEW)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()

    freeze = load(FREEZE)
    if freeze.get("status") != "frozen_awaiting_independent_blind_review":
        raise SystemExit("fresh KOL-v2 audit is not frozen for review")
    for path in (KEY, BLIND):
        expected = freeze["frozen_files"][relative(path)]["sha256"]
        if sha256_file(path) != expected:
            raise SystemExit(f"frozen audit input changed: {path}")

    blind = indexed(BLIND)
    key = indexed(KEY)
    review = indexed(args.review)
    if not (set(blind) == set(key) == set(review)):
        raise SystemExit("completed review IDs do not exactly match the frozen audit")

    rows = []
    reviewers: Counter[str] = Counter()
    for audit_id in sorted(key):
        reviewed = review[audit_id]
        if any(reviewed.get(field) != blind[audit_id].get(field) for field in BLIND_FIELDS):
            raise SystemExit(f"{audit_id}: completed review mutated a blinded field")
        label = str(reviewed.get("review_label") or "")
        confidence = str(reviewed.get("review_confidence") or "")
        rationale = str(reviewed.get("review_rationale") or "").strip()
        reviewer = str(reviewed.get("reviewer") or "").strip()
        if label not in VALID_LABELS:
            raise SystemExit(f"{audit_id}: invalid review_label {label!r}")
        if confidence not in VALID_CONFIDENCE:
            raise SystemExit(f"{audit_id}: invalid review_confidence {confidence!r}")
        if not rationale or not reviewer:
            raise SystemExit(f"{audit_id}: rationale and reviewer are required")
        reviewers[reviewer] += 1
        rows.append({**key[audit_id], "review_label": label})

    decided = [row for row in rows if row["review_label"] != "uncertain"]
    counts = Counter((row["rule_prediction"], row["review_label"]) for row in decided)
    tp = counts[("matched", "relevant")]
    fp = counts[("matched", "not_relevant")]
    fn = counts[("hard_unmatched", "relevant")]
    tn = counts[("hard_unmatched", "not_relevant")]
    predicted_matches = tp + fp
    relevant = tp + fn
    precision = tp / predicted_matches if predicted_matches else None
    recall = tp / relevant if relevant else None
    f1 = (
        2 * precision * recall / (precision + recall)
        if precision is not None and recall is not None and precision + recall
        else None
    )
    failures = []
    if len(decided) != len(rows):
        failures.append("unadjudicated uncertain rows remain")
    if predicted_matches < MIN_SUPPORT:
        failures.append("fewer than 20 decided predicted matches")
    if relevant < MIN_SUPPORT:
        failures.append("fewer than 20 review-relevant rows")
    if precision is None or precision < MIN_PRECISION:
        failures.append("precision below 0.85")
    if recall is None or recall < MIN_RECALL:
        failures.append("hard-candidate recall below 0.90")
    accepted = not failures
    report = {
        "association_rule": freeze["association_rule"],
        "confusion": {"false_negative": fn, "false_positive": fp, "true_negative": tn, "true_positive": tp},
        "decided_rows": len(decided),
        "f1": f1,
        "failures": failures,
        "hard_candidate_recall": recall,
        "input_hashes": {
            relative(FREEZE): sha256_file(FREEZE),
            relative(KEY): sha256_file(KEY),
            relative(BLIND): sha256_file(BLIND),
            relative(args.review): sha256_file(args.review),
        },
        "label_blind": True,
        "labels_read": [],
        "minimum_precision": MIN_PRECISION,
        "minimum_recall": MIN_RECALL,
        "precision": precision,
        "predicted_matches": predicted_matches,
        "protocol_id": freeze["protocol_id"],
        "relevant_rows": relevant,
        "reviewers": dict(sorted(reviewers.items())),
        "status": "accepted" if accepted else "failed",
        "uncertain_rows": len(rows) - len(decided),
    }
    atomic_json(args.output, report)
    print(json.dumps(report, indent=2, sort_keys=True))
    if not accepted:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
