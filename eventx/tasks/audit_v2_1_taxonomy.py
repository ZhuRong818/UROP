"""Prepare adjudication and score the blind EventX v2.1 taxonomy audit."""

from __future__ import annotations

import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
from typing import Any, Iterator

from eventx.settings import REPO_ROOT


DEFAULT_ROOT = REPO_ROOT / "data" / "v2_1" / "taxonomy"
CATEGORIES = ("politics", "crypto", "sports", "macro", "other")
CONFIDENCE = ("high", "medium", "low")


def read_jsonl(path: Path) -> Iterator[dict[str, Any]]:
    with path.open() as handle:
        for line_number, line in enumerate(handle, start=1):
            if not line.strip():
                continue
            value = json.loads(line)
            if not isinstance(value, dict):
                raise ValueError(f"{path}:{line_number} must be a JSON object")
            yield value


def load_unique(path: Path, *, required_ids: list[str]) -> dict[str, dict[str, Any]]:
    rows: dict[str, dict[str, Any]] = {}
    for row in read_jsonl(path):
        audit_id = str(row.get("audit_id") or "")
        if not audit_id or audit_id in rows:
            raise ValueError(f"{path} has missing or duplicate audit_id {audit_id!r}")
        rows[audit_id] = row
    if set(rows) != set(required_ids):
        missing = sorted(set(required_ids) - set(rows))
        extra = sorted(set(rows) - set(required_ids))
        raise ValueError(f"{path} ID mismatch: missing={missing[:5]} extra={extra[:5]}")
    return rows


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def atomic_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    temporary = path.with_suffix(path.suffix + ".tmp")
    with temporary.open("w") as handle:
        for row in rows:
            handle.write(json.dumps(row, sort_keys=True) + "\n")
    temporary.replace(path)


def atomic_json(path: Path, value: dict[str, Any]) -> None:
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n")
    temporary.replace(path)


def validate_review(path: Path, rows: dict[str, dict[str, Any]]) -> None:
    for audit_id, row in rows.items():
        if row.get("label") not in CATEGORIES:
            raise ValueError(f"{path}:{audit_id} invalid label {row.get('label')!r}")
        if row.get("confidence") not in CONFIDENCE:
            raise ValueError(
                f"{path}:{audit_id} invalid confidence {row.get('confidence')!r}"
            )
        if not str(row.get("rationale") or "").strip():
            raise ValueError(f"{path}:{audit_id} missing rationale")


def ratio(numerator: int, denominator: int) -> float | None:
    return numerator / denominator if denominator else None


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=DEFAULT_ROOT)
    args = parser.parse_args()
    root = args.root
    sample_path = root / "blind_review_sample.jsonl"
    key_path = root / "blind_review_key.jsonl"
    reviewer_1_path = root / "reviewer_1.jsonl"
    reviewer_2_path = root / "reviewer_2.jsonl"
    adjudication_path = root / "adjudication.jsonl"

    sample_rows = list(read_jsonl(sample_path))
    ids = [str(row["audit_id"]) for row in sample_rows]
    if len(ids) < 200 or len(ids) != len(set(ids)):
        raise ValueError("blind sample must contain at least 200 unique rows")
    sample = {str(row["audit_id"]): row for row in sample_rows}
    key = load_unique(key_path, required_ids=ids)
    reviewer_1 = load_unique(reviewer_1_path, required_ids=ids)
    reviewer_2 = load_unique(reviewer_2_path, required_ids=ids)
    validate_review(reviewer_1_path, reviewer_1)
    validate_review(reviewer_2_path, reviewer_2)

    agreement = 0
    disagreements: list[dict[str, Any]] = []
    for audit_id in ids:
        first = reviewer_1[audit_id]
        second = reviewer_2[audit_id]
        same = first["label"] == second["label"]
        requires_adjudication = (
            not same
            or first["confidence"] == "low"
            or second["confidence"] == "low"
        )
        agreement += int(same)
        if requires_adjudication:
            source = sample[audit_id]
            disagreements.append(
                {
                    "audit_id": audit_id,
                    "description": source.get("description"),
                    "market_id": source.get("market_id"),
                    "question": source.get("question"),
                    "reviewer_1": {
                        "confidence": first["confidence"],
                        "label": first["label"],
                        "rationale": first["rationale"],
                    },
                    "reviewer_2": {
                        "confidence": second["confidence"],
                        "label": second["label"],
                        "rationale": second["rationale"],
                    },
                    "venue": source.get("venue"),
                }
            )
    adjudication_sample_path = root / "adjudication_sample.jsonl"
    atomic_jsonl(adjudication_sample_path, disagreements)

    preparation = {
        "adjudication_rows": len(disagreements),
        "agreement_rate": agreement / len(ids),
        "agreements": agreement,
        "input_hashes": {
            "blind_review_key.jsonl": sha256_file(key_path),
            "blind_review_sample.jsonl": sha256_file(sample_path),
            "reviewer_1.jsonl": sha256_file(reviewer_1_path),
            "reviewer_2.jsonl": sha256_file(reviewer_2_path),
        },
        "label_blind": True,
        "labels_read": [],
        "review_rows": len(ids),
        "status": "awaiting_adjudication" if disagreements and not adjudication_path.exists() else "ready",
    }
    atomic_json(root / "audit_preparation_report.json", preparation)
    if disagreements and not adjudication_path.exists():
        print(json.dumps(preparation, indent=2, sort_keys=True))
        return

    adjudication: dict[str, dict[str, Any]] = {}
    if disagreements:
        adjudication_ids = [str(row["audit_id"]) for row in disagreements]
        adjudication = load_unique(adjudication_path, required_ids=adjudication_ids)
        validate_review(adjudication_path, adjudication)

    final_labels: dict[str, str] = {}
    for audit_id in ids:
        if audit_id in adjudication:
            final_labels[audit_id] = str(adjudication[audit_id]["label"])
        else:
            final_labels[audit_id] = str(reviewer_1[audit_id]["label"])

    confusion = {
        actual: {predicted: 0 for predicted in CATEGORIES}
        for actual in CATEGORIES
    }
    correct = 0
    for audit_id in ids:
        actual = final_labels[audit_id]
        predicted = str(key[audit_id]["proposed_category"])
        confusion[actual][predicted] += 1
        correct += int(actual == predicted)

    by_category: dict[str, dict[str, Any]] = {}
    precisions: list[float] = []
    recalls: list[float] = []
    for category in CATEGORIES:
        true_positive = confusion[category][category]
        predicted_count = sum(confusion[actual][category] for actual in CATEGORIES)
        actual_count = sum(confusion[category].values())
        precision = ratio(true_positive, predicted_count)
        recall = ratio(true_positive, actual_count)
        if precision is not None:
            precisions.append(precision)
        if recall is not None:
            recalls.append(recall)
        by_category[category] = {
            "actual_review_rows": actual_count,
            "false_negatives": actual_count - true_positive,
            "false_positives": predicted_count - true_positive,
            "precision": precision,
            "predicted_review_rows": predicted_count,
            "recall": recall,
            "review_rows": predicted_count,
            "true_positives": true_positive,
        }

    macro_precision = sum(precisions) / len(precisions)
    macro_recall = sum(recalls) / len(recalls)
    micro = correct / len(ids)
    category_gate = all(
        values["review_rows"] < 20
        or (values["precision"] is not None and values["precision"] >= 0.80)
        for values in by_category.values()
    )
    accepted = (
        macro_precision >= 0.90
        and macro_recall >= 0.90
        and micro >= 0.90
        and category_gate
    )
    report = {
        "adjudication_rows": len(disagreements),
        "by_category": by_category,
        "confusion_matrix_actual_by_predicted": confusion,
        "gates": {
            "category_precision": category_gate,
            "macro_precision_at_least_0_90": macro_precision >= 0.90,
            "macro_recall_at_least_0_90": macro_recall >= 0.90,
            "micro_precision_recall_at_least_0_90": micro >= 0.90,
        },
        "input_hashes": {
            **preparation["input_hashes"],
            **(
                {"adjudication.jsonl": sha256_file(adjudication_path)}
                if disagreements
                else {}
            ),
        },
        "label_blind": True,
        "labels_read": [],
        "overall": {
            "accuracy": micro,
            "macro_precision": macro_precision,
            "macro_recall": macro_recall,
            "micro_precision": micro,
            "micro_recall": micro,
            "precision": macro_precision,
            "recall": macro_recall,
        },
        "review_rows": len(ids),
        "status": "accepted" if accepted else "rejected",
        "taxonomy_version": key[ids[0]]["taxonomy_version"],
    }
    atomic_json(root / "audit_report.json", report)
    print(json.dumps(report, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
