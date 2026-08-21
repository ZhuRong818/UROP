"""Evaluate KOL association rules on the frozen, pre-test semantic audit."""

from __future__ import annotations

import argparse
import json
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

from eventx.features.kol_association import (
    CASHTAG_RE,
    entities_for,
    match_market_v2 as match_market,
)
from eventx.settings import REPO_ROOT


def ratio(numerator: int, denominator: int) -> float | None:
    return numerator / denominator if denominator else None


def metrics(counts: Counter[str]) -> dict[str, Any]:
    tp = counts["tp"]
    fp = counts["fp"]
    tn = counts["tn"]
    fn = counts["fn"]
    precision = ratio(tp, tp + fp)
    recall = ratio(tp, tp + fn)
    return {
        "tp": tp,
        "fp": fp,
        "tn": tn,
        "fn": fn,
        "precision": precision,
        "recall": recall,
        "f1": (
            2 * precision * recall / (precision + recall)
            if precision is not None and recall is not None and precision + recall
            else None
        ),
    }


def outcome(predicted: bool, relevant: bool) -> str:
    if predicted and relevant:
        return "tp"
    if predicted:
        return "fp"
    if relevant:
        return "fn"
    return "tn"


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Score KOL matcher versions on the frozen pre-test audit"
    )
    parser.add_argument(
        "--audit",
        type=Path,
        default=REPO_ROOT / "data" / "v1" / "audit"
        / "kol_association_audit_sample.jsonl",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=REPO_ROOT / "data" / "v1" / "audit"
        / "kol_rule_v2_evaluation.json",
    )
    args = parser.parse_args()

    rows = [json.loads(line) for line in args.audit.open() if line.strip()]
    if not rows or any(row.get("review_label") is None for row in rows):
        raise SystemExit("The frozen audit is absent or has unreviewed rows.")
    dataset_ids = {row.get("dataset_id") for row in rows}
    cutoffs = {row.get("audit_cutoff_exclusive") for row in rows}
    if len(dataset_ids) != 1 or len(cutoffs) != 1:
        raise SystemExit("Audit rows do not share one frozen dataset and cutoff.")

    counts_v1: Counter[str] = Counter()
    counts_v2: Counter[str] = Counter()
    counts_v2_by_sample: dict[str, Counter[str]] = defaultdict(Counter)
    counts_v2_by_market: dict[str, Counter[str]] = defaultdict(Counter)
    changed: Counter[str] = Counter()
    errors: list[dict[str, Any]] = []
    for row in rows:
        relevant = row["review_label"] == "relevant"
        predicted_v1 = row["sample_type"] == "matched"
        text = str(row.get("text") or "")
        cashtags = {value.upper() for value in CASHTAG_RE.findall(text)}
        reasons, terms = match_market(
            str(row["question"]),
            entities_for(str(row["question"])),
            text,
            cashtags,
        )
        predicted_v2 = bool(reasons)
        result_v1 = outcome(predicted_v1, relevant)
        result_v2 = outcome(predicted_v2, relevant)
        counts_v1[result_v1] += 1
        counts_v2[result_v2] += 1
        counts_v2_by_sample[row["sample_type"]][result_v2] += 1
        counts_v2_by_market[row["question"]][result_v2] += 1
        if predicted_v1 != predicted_v2:
            changed["v1_positive_to_v2_negative" if predicted_v1 else "v1_negative_to_v2_positive"] += 1
        if result_v2 in {"fp", "fn"}:
            errors.append(
                {
                    "audit_id": row["audit_id"],
                    "sample_type": row["sample_type"],
                    "question": row["question"],
                    "result": result_v2,
                    "v2_match_reason": reasons,
                    "v2_matched_terms": terms,
                }
            )

    report = {
        "dataset_id": next(iter(dataset_ids)),
        "audit_cutoff_exclusive": next(iter(cutoffs)),
        "reviewer": sorted({row.get("reviewer") for row in rows}),
        "reviewed_cases": len(rows),
        "class_balance": dict(sorted(Counter(
            row["review_label"] for row in rows
        ).items())),
        "rule_v1": metrics(counts_v1),
        "rule_v2": metrics(counts_v2),
        "rule_v2_by_original_sample_type": {
            sample_type: metrics(counts)
            for sample_type, counts in sorted(counts_v2_by_sample.items())
        },
        "rule_v2_by_market": {
            question: metrics(counts)
            for question, counts in sorted(counts_v2_by_market.items())
        },
        "prediction_changes": dict(sorted(changed.items())),
        "rule_v2_errors": errors,
        "limitations": [
            "Metrics describe the stratified 300-case audit set, not production prevalence.",
            "The negative sample contains hard retrieval candidates, not random unmatched tweets.",
            "Labels were produced by one semantic reviewer and need independent replication.",
            "Rule_v2 was iteratively tightened against this audit, so its scores are development-set estimates rather than a fresh blind validation.",
            "No test-period tweets were reviewed or used to tune rule_v2.",
        ],
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    temporary = args.output.with_suffix(args.output.suffix + ".tmp")
    temporary.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")
    temporary.replace(args.output)
    print(json.dumps({
        "dataset_id": report["dataset_id"],
        "reviewed_cases": report["reviewed_cases"],
        "rule_v1": report["rule_v1"],
        "rule_v2": report["rule_v2"],
        "prediction_changes": report["prediction_changes"],
    }, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
