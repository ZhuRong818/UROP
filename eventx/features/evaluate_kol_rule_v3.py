"""Compare KOL association rules on both frozen pre-test development audits."""

from __future__ import annotations

import json
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Callable

from eventx.features.kol_association import (
    CASHTAG_RE,
    entities_for,
    match_market_v2,
    match_market_v3,
    parse_ts,
)
from eventx.settings import REPO_ROOT

Matcher = Callable[
    [str, dict[str, list[str]], str, set[str]],
    tuple[list[str], list[str]],
]


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in path.open() if line.strip()]


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


def evaluate(
    rows: list[dict[str, Any]],
    matcher: Matcher,
) -> tuple[dict[str, Any], list[dict[str, Any]], dict[str, dict[str, Any]]]:
    counts: Counter[str] = Counter()
    by_market: dict[str, Counter[str]] = defaultdict(Counter)
    errors: list[dict[str, Any]] = []
    for row in rows:
        text = str(row.get("tweet_text") or row.get("text") or "")
        cashtags = {value.upper() for value in CASHTAG_RE.findall(text)}
        reasons, terms = matcher(
            str(row["question"]),
            entities_for(str(row["question"])),
            text,
            cashtags,
        )
        result = outcome(bool(reasons), row["review_label"] == "relevant")
        counts[result] += 1
        by_market[row["question"]][result] += 1
        if result in {"fp", "fn"}:
            errors.append(
                {
                    "audit_id": row["audit_id"],
                    "question": row["question"],
                    "result": result,
                    "match_reason": reasons,
                    "matched_terms": terms,
                    "review_rationale": row["review_rationale"],
                }
            )
    return (
        metrics(counts),
        errors,
        {
            question: metrics(market_counts)
            for question, market_counts in sorted(by_market.items())
        },
    )


def error_counts_by_market(errors: list[dict[str, Any]]) -> dict[str, dict[str, int]]:
    grouped: dict[str, Counter[str]] = defaultdict(Counter)
    for error in errors:
        grouped[error["question"]][error["result"]] += 1
    return {
        question: dict(sorted(counts.items()))
        for question, counts in sorted(grouped.items())
    }


def main() -> None:
    original_path = (
        REPO_ROOT / "data" / "v1" / "audit"
        / "kol_association_audit_sample.jsonl"
    )
    blind_dir = REPO_ROOT / "data" / "v1" / "audit_v2_blind"
    blind_path = (
        blind_dir / "kol_association_blind_review_completed_reviewer_man.jsonl"
    )
    output_path = blind_dir / "kol_rule_v3_development_evaluation.json"
    original = read_jsonl(original_path)
    blind = read_jsonl(blind_path)
    if any(row.get("review_label") not in {"relevant", "not_relevant"} for row in blind):
        raise SystemExit("The completed blind review contains absent or non-binary labels.")

    frozen = json.loads(
        (REPO_ROOT / "data" / "v1" / "toy" / "frozen_manifest.json").read_text()
    )
    cutoff = parse_ts(frozen["split_boundaries"]["test_start"])
    if cutoff is None:
        raise SystemExit("Frozen manifest has no valid test cutoff.")
    for name, rows in (("original", original), ("blind", blind)):
        outside = [
            row["audit_id"]
            for row in rows
            if (parse_ts(row.get("tweet_ts") or row.get("ts")) or cutoff) >= cutoff
        ]
        if outside:
            raise SystemExit(f"{name} audit includes test-period rows: {outside[:5]}")

    original_v2, original_v2_errors, original_v2_markets = evaluate(
        original, match_market_v2
    )
    original_v3, original_v3_errors, original_v3_markets = evaluate(
        original, match_market_v3
    )
    blind_v2, blind_v2_errors, blind_v2_markets = evaluate(blind, match_market_v2)
    blind_v3, blind_v3_errors, blind_v3_markets = evaluate(blind, match_market_v3)

    blind_v2_error_ids = {
        (error["audit_id"], error["result"]) for error in blind_v2_errors
    }
    blind_v3_error_ids = {
        (error["audit_id"], error["result"]) for error in blind_v3_errors
    }
    report = {
        "dataset_id": frozen["dataset_id"],
        "test_cutoff_exclusive": frozen["split_boundaries"]["test_start"],
        "test_period_examples_used": 0,
        "original_audit": {
            "reviewed_cases": len(original),
            "reviewer": sorted({row.get("reviewer") for row in original}),
            "rule_v2": original_v2,
            "rule_v3": original_v3,
            "rule_v2_by_market": original_v2_markets,
            "rule_v3_by_market": original_v3_markets,
            "rule_v3_errors": original_v3_errors,
        },
        "fresh_blind_audit_used_to_develop_v3": {
            "reviewed_cases": len(blind),
            "reviewer": sorted({row.get("reviewer") for row in blind}),
            "rule_v2": blind_v2,
            "rule_v3": blind_v3,
            "rule_v2_errors_by_market": error_counts_by_market(blind_v2_errors),
            "rule_v3_errors_by_market": error_counts_by_market(blind_v3_errors),
            "rule_v2_by_market": blind_v2_markets,
            "rule_v3_by_market": blind_v3_markets,
            "rule_v3_errors": blind_v3_errors,
            "v2_errors_resolved_by_v3": len(
                blind_v2_error_ids - blind_v3_error_ids
            ),
            "v3_errors_not_present_under_v2": len(
                blind_v3_error_ids - blind_v2_error_ids
            ),
        },
        "rule_v2_error_analysis": {
            "false_positive_categories": {
                "broad_candidate_or_election_context": 26,
                "generic_geopolitical_or_status_context": 12,
                "wrong_album_or_release_object": 2,
                "buried_or_routine_leadership_mention": 2,
            },
            "false_negative_categories": {
                "missing_event_status_synonyms_or_aliases": 14,
                "indirect_country_level_leadership_risk": 1,
            },
        },
        "rule_v3_design_changes": [
            "Require outcome-specific candidate, nomination, succession, or mayoral phrases instead of broad political tokens.",
            "Require Hormuz traffic/status language near Hormuz or Strait mentions, including reopening, flow, vessel, threat, and multilingual normalization terms.",
            "Use withdrawal-specific Lebanon context and high-signal China-Taiwan military or coercion patterns.",
            "Require Cuban regime-change signals, United Russia election-performance terms, and Rihanna own-album signals.",
            "Retain deterministic provenance reasons and terms for every association.",
        ],
        "limitations": [
            "Both audits are now development sets because their labels were inspected while designing rule_v3.",
            "The samples are stratified and the negative rows are hard retrieval candidates, so metrics do not estimate production prevalence.",
            "Each audit has a single semantic reviewer and some residual labels are contestable.",
            "Rule_v3 requires a third untouched blind audit before it can be frozen.",
            "No test-period examples were inspected or used for rule design.",
        ],
    }
    temporary = output_path.with_suffix(output_path.suffix + ".tmp")
    temporary.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")
    temporary.replace(output_path)
    print(json.dumps({
        "dataset_id": report["dataset_id"],
        "original_audit": {
            "rule_v2": original_v2,
            "rule_v3": original_v3,
        },
        "blind_development_audit": {
            "rule_v2": blind_v2,
            "rule_v3": blind_v3,
        },
        "v2_errors_resolved_by_v3": report[
            "fresh_blind_audit_used_to_develop_v3"
        ]["v2_errors_resolved_by_v3"],
        "test_period_examples_used": 0,
    }, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
