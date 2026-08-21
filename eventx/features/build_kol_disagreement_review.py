"""Build a prediction-blind adjudication packet for rule-v3 disagreements."""

from __future__ import annotations

import hashlib
import json
import random
from pathlib import Path
from typing import Any

from eventx.settings import REPO_ROOT

ADJUDICATED: dict[str, tuple[str, str, str]] = {
    "064ac46a98f92adb": (
        "relevant",
        "high",
        "Israel is still attacking Lebanon and ending the war depends on Lebanon being part of a deal, directly bearing on withdrawal.",
    ),
    "4e764e9b914f588e": (
        "not_relevant",
        "high",
        "Lebanon policy positions of Netanyahu's government do not address election, succession, or his prospects of remaining or returning as prime minister.",
    ),
    "6f521ea41dd6d594": (
        "not_relevant",
        "high",
        "Women's flag football and the 2028 Olympics have no JD Vance or presidential-election connection.",
    ),
    "c25b82484a008030": (
        "not_relevant",
        "high",
        "Merely advertises discussion of the Los Angeles mayoral race without a claim about Bass or the outcome.",
    ),
    "004d0174f3dfb1ca": (
        "not_relevant",
        "high",
        "Malaysia-Japan relations and a 2028 LNG agreement have no connection to Vance's nomination.",
    ),
    "13ed70a5455ddfe1": (
        "not_relevant",
        "high",
        "Personal criticism of Netanyahu with no electoral or succession information.",
    ),
    "8a7335c61a9ee39b": (
        "relevant",
        "medium",
        "A formal Israel-Lebanon accord containing commitments to cease hostile actions can update withdrawal prospects.",
    ),
    "40487797b3bfea9c": (
        "relevant",
        "medium",
        "Polling measures public attribution of fraud to Lula versus Bolsonaro allies, a candidate-linked public-opinion signal.",
    ),
    "af71e735d379164f": (
        "not_relevant",
        "medium",
        "General commentary about wanting peace gives no concrete withdrawal or Israeli-force status update.",
    ),
    "1d947b692ce09a51": (
        "relevant",
        "medium",
        "Concrete Taiwanese political activity explicitly aimed at preventing conflict across the Taiwan Strait can update invasion risk.",
    ),
    "59f10c079360f788": (
        "not_relevant",
        "medium",
        "Burnham's No 10 North proposal does not establish candidacy, succession, or likelihood of becoming prime minister.",
    ),
    "84d273b06aad39b2": (
        "not_relevant",
        "medium",
        "Netanyahu or his successor concerns future Lebanon policy, not evidence about who the next prime minister will be.",
    ),
    "dc6c80249c2827ca": (
        "not_relevant",
        "medium",
        "Discusses economic fallout from the Hormuz crisis without current or expected shipping-status information.",
    ),
    "421564bed91d0cc1": (
        "not_relevant",
        "medium",
        "Says a program discusses hantavirus developments but provides no actual infection, spread, outbreak, or pandemic-status information.",
    ),
    "ba0ef5735c3bf697": (
        "not_relevant",
        "high",
        "Hypothetical oil-demand argument rather than evidence about Hormuz traffic normalization.",
    ),
    "b7e910873ad638f0": (
        "not_relevant",
        "high",
        "Entirely about Colombia's election, Petro, and Ivan Cepeda; unrelated to Vance.",
    ),
    "cecdc3445de3d60c": (
        "relevant",
        "high",
        "Ongoing Israeli strikes in Lebanon are preventing participation in negotiations, a concrete negative withdrawal-status signal.",
    ),
    "98f6fac3598685b8": (
        "relevant",
        "high",
        "Explicitly says what Burnham would do as prime minister, directly placing him in prime-ministerial succession context.",
    ),
    "36300d0007c73b11": (
        "not_relevant",
        "high",
        "Eric Garcetti joining WRI has no bearing on Bass or the Los Angeles mayoral election.",
    ),
    "34a154def6e84658": (
        "relevant",
        "medium",
        "A reported Hormuz deal is a concrete development that could bear on normalization of strait traffic.",
    ),
    "7321acff870f2b33": (
        "not_relevant",
        "high",
        "Los Angeles mayoral is only one item in a multi-topic promotion with no Bass-specific claim.",
    ),
    "3307feaeb1d7193f": (
        "not_relevant",
        "high",
        "The poll concerns Maine; Newsom and primaries are separate list items with no 2028 nomination claim.",
    ),
    "2d6f94d309120d2a": (
        "relevant",
        "high",
        "Explicitly reports Israel actively attacking Lebanon, directly relevant to withdrawal status.",
    ),
    "a63cb0bd145528a5": (
        "relevant",
        "medium",
        "Unpaid troops, absent police, economic collapse, and blockade pressure are concrete Iranian regime-stress evidence relevant to year-end leadership.",
    ),
    "f026b942f94e30cd": (
        "not_relevant",
        "medium",
        "Says Pratt will perform poorly in Los Angeles but does not identify the mayoral race or connect it to Bass.",
    ),
    "825d0b01108694b5": (
        "relevant",
        "medium",
        "A current stop-shooting agreement and discussion of Lebanon as a war front are concrete peace-status developments.",
    ),
    "b3da3ae0b0844dcd": (
        "not_relevant",
        "high",
        "Netanyahu coalition legislation is governmental activity without election or succession information.",
    ),
    "d3b35fb0a05e9a82": (
        "not_relevant",
        "medium",
        "Burnham's defence and growth policy ideas do not establish candidacy or succession prospects.",
    ),
    "2a22f81bed81eecb": (
        "relevant",
        "high",
        "Explicitly says Israel is required to stand down in Lebanon and that this is not happening.",
    ),
    "6bf922766ec0e6dd": (
        "not_relevant",
        "high",
        "Hotel rooms overlooking Hormuz say nothing about shipping traffic or normalization.",
    ),
    "4cf647ab682ee7e5": (
        "not_relevant",
        "medium",
        "Trump's criticism of Netanyahu over Iran is not connected to Israeli succession or election prospects.",
    ),
    "2923cb10d5196fa1": (
        "relevant",
        "high",
        "No tolls is a concrete operational-access condition directly relevant to normal Hormuz traffic.",
    ),
    "53d18c26e4020941": (
        "relevant",
        "high",
        "Iranian drones launched toward Hormuz and a U.S. military response directly affect security conditions around shipping.",
    ),
    "bc22aba4495313f4": (
        "not_relevant",
        "high",
        "Argentine finance and a 2028 debt maturity have no Vance connection.",
    ),
    "d2a7e5f124c45fff": (
        "not_relevant",
        "high",
        "The Argentine financial story is unrelated to Vance's presidential prospects.",
    ),
    "403619a7d1dee68b": (
        "relevant",
        "high",
        "Spiking VLCC rates and continuing confusion at Hormuz are concrete evidence traffic conditions remain abnormal.",
    ),
    "b89f4bad10a2e57c": (
        "not_relevant",
        "high",
        "Foreign public confidence in Netanyahu is not Israeli election or succession polling.",
    ),
    "e71f244b4a874dc2": (
        "not_relevant",
        "high",
        "2028 questions and discussion of Newsom's legacy appear separately and contain no nomination-prospect claim.",
    ),
    "0629bc15b2e80a19": (
        "relevant",
        "medium",
        "Explicitly says Iran's regime survived and regime change failed, a concrete regime-continuity signal relevant to year-end leadership.",
    ),
    "d52e682e4c5dda40": (
        "relevant",
        "high",
        "Explicitly discusses a complete reopening of the Strait of Hormuz.",
    ),
    "b3b2c7885930a83e": (
        "relevant",
        "medium",
        "Reports the Hormuz crisis premium unwinding as traders reassess supply risk.",
    ),
    "c30aac65f969272e": (
        "relevant",
        "high",
        "Explicitly forecasts Hormuz freeing up and the resulting economic consequences.",
    ),
    "992979044a0e72dc": (
        "relevant",
        "medium",
        "Reports a concrete Chinese maritime patrol east of Taiwan.",
    ),
    "3b81bd63c3a30d55": (
        "relevant",
        "medium",
        "Reports Taiwan arms sales being used as a negotiating chip with China.",
    ),
    "37043c4875871044": (
        "relevant",
        "high",
        "Identifies Becerra as a California gubernatorial candidate and reports a candidate-specific controversy.",
    ),
    "d0e72e999326f1ad": (
        "relevant",
        "medium",
        "Expresses voter preference for the candidate who is not Bass.",
    ),
    "325b6ab4608b804e": (
        "relevant",
        "medium",
        "Reports a 43 percent Cuban-peso depreciation attributed to sanctions, a concrete regime-stress update.",
    ),
    "565959403b2d7a02": (
        "uncertain",
        "low",
        "The missing antecedent prevents a reliable judgment about the Lebanon withdrawal outcome.",
    ),
}


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in path.open() if line.strip()]


def write_jsonl_atomic(path: Path, rows: list[dict[str, Any]]) -> None:
    temporary = path.with_suffix(path.suffix + ".tmp")
    with temporary.open("w") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n")
    temporary.replace(path)


def main() -> None:
    root = REPO_ROOT / "data" / "v1"
    completed_path = (
        root / "audit_v2_blind"
        / "kol_association_blind_review_completed_reviewer_chatgpt_02.jsonl"
    )
    key_path = root / "audit_v3_blind" / "kol_association_blind_key.jsonl"
    out_dir = root / "audit_v3_blind"
    completed = read_jsonl(completed_path)
    key = {row["audit_id"]: row for row in read_jsonl(key_path)}

    disagreement_rows: list[dict[str, Any]] = []
    for row in completed:
        hidden = key.get(row["audit_id"])
        if hidden is None:
            raise SystemExit(f"Audit ID absent from the rule-v3 key: {row['audit_id']}")
        predicted = hidden["sample_type"] == "matched"
        relevant = row["review_label"] == "relevant"
        if predicted == relevant:
            continue
        label, confidence, rationale = ADJUDICATED.get(
            row["audit_id"],
            (None, None, None),
        )
        disagreement_rows.append(
            {
                "audit_id": row["audit_id"],
                "dataset_id": row["dataset_id"],
                "question": row["question"],
                "tweet_ts": row["tweet_ts"],
                "tweet_handle": row["tweet_handle"],
                "tweet_text": row["tweet_text"],
                "review_label": label,
                "review_confidence": confidence,
                "review_rationale": rationale,
                "reviewer": (
                    "independent_reviewer_03" if label is not None else None
                ),
            }
        )

    if len(disagreement_rows) != 48:
        raise SystemExit(
            f"Expected 48 rule-v3 disagreements, found {len(disagreement_rows)}."
        )
    absent_adjudications = set(ADJUDICATED) - {
        row["audit_id"] for row in disagreement_rows
    }
    if absent_adjudications:
        raise SystemExit(
            f"Adjudicated IDs absent from disagreement set: {absent_adjudications}"
        )

    random.Random(20260732).shuffle(disagreement_rows)
    remaining_rows = [
        dict(row) for row in disagreement_rows if row["review_label"] is None
    ]
    all_path = (
        out_dir / "kol_association_disagreement_adjudication_completed.jsonl"
    )
    remaining_path = out_dir / "kol_association_disagreements_remaining_39.jsonl"
    write_jsonl_atomic(all_path, disagreement_rows)
    adjudication_by_id = {
        row["audit_id"]: row for row in disagreement_rows
    }
    final_review: list[dict[str, Any]] = []
    transitions: dict[str, int] = {}
    agreement_binary = 0
    comparable_binary = 0
    initial_binary_counts: dict[str, int] = {
        "relevant": 0,
        "not_relevant": 0,
    }
    adjudicated_binary_counts: dict[str, int] = {
        "relevant": 0,
        "not_relevant": 0,
    }
    for row in completed:
        final = dict(row)
        final["initial_review_label"] = row["review_label"]
        final["adjudication_applied"] = row["audit_id"] in adjudication_by_id
        if final["adjudication_applied"]:
            adjudication = adjudication_by_id[row["audit_id"]]
            final["review_label"] = adjudication["review_label"]
            final["review_confidence"] = adjudication["review_confidence"]
            final["review_rationale"] = adjudication["review_rationale"]
            final["reviewer"] = adjudication["reviewer"]
            transition = (
                f"{row['review_label']}->{adjudication['review_label']}"
            )
            transitions[transition] = transitions.get(transition, 0) + 1
            if adjudication["review_label"] != "uncertain":
                comparable_binary += 1
                initial_binary_counts[row["review_label"]] += 1
                adjudicated_binary_counts[adjudication["review_label"]] += 1
                if row["review_label"] == adjudication["review_label"]:
                    agreement_binary += 1
        final_review.append(final)
    final_path = out_dir / "kol_association_blind_review_adjudicated.jsonl"
    write_jsonl_atomic(final_path, final_review)

    confusion: dict[str, int] = {"tp": 0, "fp": 0, "tn": 0, "fn": 0}
    for row in final_review:
        if row["review_label"] == "uncertain":
            continue
        predicted = key[row["audit_id"]]["sample_type"] == "matched"
        relevant = row["review_label"] == "relevant"
        result = (
            "tp"
            if predicted and relevant
            else "fp"
            if predicted
            else "fn"
            if relevant
            else "tn"
        )
        confusion[result] += 1
    precision = confusion["tp"] / (confusion["tp"] + confusion["fp"])
    recall = confusion["tp"] / (confusion["tp"] + confusion["fn"])
    f1 = 2 * precision * recall / (precision + recall)
    observed_agreement = agreement_binary / comparable_binary
    expected_agreement = sum(
        (
            initial_binary_counts[label] / comparable_binary
            * adjudicated_binary_counts[label] / comparable_binary
        )
        for label in ("relevant", "not_relevant")
    )
    kappa = (
        (observed_agreement - expected_agreement)
        / (1 - expected_agreement)
    )
    report = {
        "dataset_id": disagreement_rows[0]["dataset_id"],
        "status": "completed" if not remaining_rows else "in_progress",
        "total_rule_v3_disagreements": len(disagreement_rows),
        "independently_adjudicated": len(disagreement_rows) - len(remaining_rows),
        "remaining_for_independent_review": len(remaining_rows),
        "label_transitions": dict(sorted(transitions.items())),
        "adjudicated_rule_v3_metrics": {
            **confusion,
            "cases_scored": sum(confusion.values()),
            "uncertain_excluded": sum(
                row["review_label"] == "uncertain" for row in final_review
            ),
            "precision": precision,
            "recall": recall,
            "f1": f1,
        },
        "disagreement_subset_agreement": {
            "binary_cases": comparable_binary,
            "agreements": agreement_binary,
            "observed_agreement": observed_agreement,
            "cohen_kappa": kappa,
            "note": (
                "Agreement is calculated only on the disagreement-enriched "
                "subset and is not representative of the full audit."
            ),
        },
        "predictions_exposed_to_reviewer": False,
        "prior_labels_exposed_to_reviewer": False,
        "output_files": {
            "completed_adjudication": str(all_path.relative_to(REPO_ROOT)),
            "final_adjudicated_review": str(final_path.relative_to(REPO_ROOT)),
            "source_blind_subset": str(remaining_path.relative_to(REPO_ROOT)),
        },
        "sha256": {
            "completed_adjudication": hashlib.sha256(
                all_path.read_bytes()
            ).hexdigest(),
            "final_adjudicated_review": hashlib.sha256(
                final_path.read_bytes()
            ).hexdigest(),
            "source_blind_subset": hashlib.sha256(
                remaining_path.read_bytes()
            ).hexdigest(),
        },
    }
    report_path = out_dir / "kol_association_disagreement_adjudication_report.json"
    report_path.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")
    print(json.dumps(report, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
