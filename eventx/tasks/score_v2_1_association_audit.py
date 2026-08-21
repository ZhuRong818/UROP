"""Score a completed blind EventX v2.1 association review against its hidden key."""

from __future__ import annotations

import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
from typing import Any, Iterator

from eventx.settings import REPO_ROOT


DEFAULT_ROOT = REPO_ROOT / "data" / "v2_1" / "association" / "v1_audit"
VALID_LABELS = {"relevant", "not_relevant", "uncertain"}
VALID_CONFIDENCE = {"high", "medium", "low"}
MIN_PRECISION = 0.85
MIN_RECALL = 0.90
MIN_SOURCE_PREDICTED_MATCHES = 20
MIN_SOURCE_RELEVANT = 20


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


def atomic_json(path: Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n")
    temporary.replace(path)


def indexed_rows(path: Path) -> dict[str, dict[str, Any]]:
    rows: dict[str, dict[str, Any]] = {}
    for row in read_jsonl(path):
        audit_id = str(row.get("audit_id") or "")
        if not audit_id or audit_id in rows:
            raise ValueError(f"{path} has a missing or duplicate audit_id {audit_id!r}")
        rows[audit_id] = row
    return rows


def metrics(rows: list[dict[str, Any]]) -> dict[str, Any]:
    decided = [row for row in rows if row["review_label"] != "uncertain"]
    counts = Counter(
        (row["rule_prediction"], row["review_label"])
        for row in decided
    )
    true_positive = counts[("matched", "relevant")]
    false_positive = counts[("matched", "not_relevant")]
    false_negative = counts[("hard_unmatched", "relevant")]
    true_negative = counts[("hard_unmatched", "not_relevant")]
    predicted_matches = true_positive + false_positive
    relevant = true_positive + false_negative
    precision = true_positive / predicted_matches if predicted_matches else None
    recall = true_positive / relevant if relevant else None
    f1 = (
        2 * precision * recall / (precision + recall)
        if precision is not None and recall is not None and precision + recall
        else None
    )
    return {
        "confusion": {
            "false_negative": false_negative,
            "false_positive": false_positive,
            "true_negative": true_negative,
            "true_positive": true_positive,
        },
        "decided_rows": len(decided),
        "f1": f1,
        "hard_candidate_recall": recall,
        "precision": precision,
        "predicted_matches": predicted_matches,
        "relevant_rows": relevant,
        "uncertain_rows": len(rows) - len(decided),
    }


def passes(values: dict[str, Any], *, require_support: bool) -> tuple[bool, list[str]]:
    failures: list[str] = []
    if values["uncertain_rows"]:
        failures.append("unadjudicated uncertain rows remain")
    if require_support and values["predicted_matches"] < MIN_SOURCE_PREDICTED_MATCHES:
        failures.append("fewer than 20 decided predicted matches")
    if require_support and values["relevant_rows"] < MIN_SOURCE_RELEVANT:
        failures.append("fewer than 20 review-relevant rows")
    if values["precision"] is None or values["precision"] < MIN_PRECISION:
        failures.append("precision below 0.85")
    if values["hard_candidate_recall"] is None or values["hard_candidate_recall"] < MIN_RECALL:
        failures.append("hard-candidate recall below 0.90")
    return not failures, failures


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--preparation",
        type=Path,
        default=DEFAULT_ROOT / "association_audit_preparation_report.json",
    )
    parser.add_argument(
        "--key",
        type=Path,
        default=DEFAULT_ROOT / "association_blind_key.jsonl",
    )
    parser.add_argument(
        "--review",
        type=Path,
        default=DEFAULT_ROOT / "association_blind_review_completed.jsonl",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=DEFAULT_ROOT / "association_audit_report.json",
    )
    args = parser.parse_args()

    preparation = load_object(args.preparation)
    expected_key_hash = preparation.get("outputs", {}).get("blind_key", {}).get("sha256")
    if sha256_file(args.key) != expected_key_hash:
        raise SystemExit("hidden key hash does not match the frozen preparation report")
    key = indexed_rows(args.key)
    review = indexed_rows(args.review)
    if set(key) != set(review):
        raise SystemExit("completed review IDs do not exactly match the hidden key")

    combined: list[dict[str, Any]] = []
    reviewers: Counter[str] = Counter()
    for audit_id in sorted(key):
        reviewed = review[audit_id]
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
        combined.append({**key[audit_id], "review_label": label})

    overall = metrics(combined)
    overall_pass, overall_failures = passes(overall, require_support=False)
    by_source: dict[str, dict[str, Any]] = {}
    source_passes = []
    for source in ("news", "kol"):
        values = metrics([row for row in combined if row["source"] == source])
        accepted, failures = passes(values, require_support=True)
        by_source[source] = {**values, "failures": failures, "status": "accepted" if accepted else "failed"}
        source_passes.append(accepted)
    accepted = overall_pass and all(source_passes)
    report = {
        "association_rule": preparation.get("association_rule"),
        "by_source": by_source,
        "failures": overall_failures,
        "input_hashes": {
            relative(args.key): sha256_file(args.key),
            relative(args.preparation): sha256_file(args.preparation),
            relative(args.review): sha256_file(args.review),
        },
        "label_blind": True,
        "labels_read": [],
        "minimum_precision": MIN_PRECISION,
        "minimum_recall": MIN_RECALL,
        "overall": overall,
        "protocol_id": preparation.get("protocol_id"),
        "reviewers": dict(sorted(reviewers.items())),
        "status": "accepted" if accepted else "failed",
    }
    atomic_json(args.output, report)
    print(json.dumps(report, indent=2, sort_keys=True))
    if not accepted:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
