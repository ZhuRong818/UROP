"""Apply the independent semantic review of the first blind news audit."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Iterator

from eventx.settings import REPO_ROOT

RELEVANT = {
    "91cd13af849d01ab", "d42e12ab6193ed42", "7ed4f9b0128a5ba6",
    "7797646103db5e78", "e3d60260d4223dd1", "8c90346892a8121d",
    "12232475e009cdc6", "77207a9b602e7dfc", "c8e8751bfef41769",
    "b93cfe193f4817df", "0460369907054688", "043875b5fc818da7",
    "32a20e9eca0f8b94", "e077cf61c7ef0b45", "44ad1ebab0bbb930",
    "9f586ef37825d18f", "bba98af174571b5b", "772d22fce93ecc8f",
    "f372c40c33fa7c9e", "7d83d1d762a91a7b", "48d9a9103cf7d00c",
    "dc085081d3d03f3c", "2af92a6e2f4c3575", "50c0925ac543629a",
    "e713e9d6ef3331de", "68dabb98284e534f", "74045a0839b19e08",
    "b6433215ee6d5227", "7ade5dea7649119e", "6f29f64ac475a683",
    "95dc904b70a856d8", "a0ea454c740944ab", "925ecf1e16921b32",
    "fcf5bdae56824f34", "d9908472e3515a3b", "906726c9c5072fea",
    "0b7995b040e1a31f", "ddffabfa2309744f", "49d0815cfa863fa0",
    "6da3a3338d63f0e5", "730f7830bdbbb2ba", "e78af2c90549312b",
    "caf3b49c79fa3a6a", "eca900c54627c006", "d8a1a657a7faaf6f",
    "8d1d4cf0b547d364", "84b5b7605ebd3ede", "2edd6275487b3836",
    "ef87500dd9f1db32", "6778a66c9d081b4d", "c8d33be58a5a4cd3",
    "3c8ce79f4ef25e12", "88538a9e79a6aac9", "b830c6d62710c1bf",
    "323be801c1b7cca4", "b07f0246099267c0", "1296c31b7c2dc752",
    "21c33b4814dd713f", "463f1fddd26c6d73", "9c03c0a00a6cd196",
    "c2fa114fe0d88c13", "a9a467d18f8cbeee", "0f650737e3873f1d",
    "b242e6fcc337f2ba", "8628ad1a312a2a1d", "7ccb5e83b5c3f8af",
    "a5344caf91038977",
}
NOT_RELEVANT = {
    "519b5920f6c468b1", "59e1d99b0824ab66", "2f373b76142ce66e",
    "a490a4cf7d200092", "d4316c27cd5be1b3", "a0fc228a45e9160a",
    "096f34a1a1c1610a", "c67ed04bfabf9213", "770d9767935bf0c6",
    "40a4b0d7d7c8fc3d", "f1aaae2f4fce06ae", "d783a2d75361c511",
    "46a36739c9d8bc64", "67c4a53dfcbf9fff", "259d49fd6800ff84",
    "feca04b03fbeb5d9", "5e261f9734b40db8", "21c9cf1d1702e13c",
    "771cbd9660d0db92", "c721637062291f22", "5a909386af0b7b05",
    "d204696a1121109b", "766f4d4a9912ec2f", "617a5281675a7734",
    "9035e6e1206c2bec", "b7ee1a8f719626f1", "b1bafcdd18b00ba9",
    "afa271504b890c3d", "b89c1f027dc729f2", "fccb1d60e14275a8",
    "6ca751bbae1ae669", "84f0c85dce305789",
}
UNCERTAIN = {"6778bd429e9e2371"}
MEDIUM_CONFIDENCE = {
    "c8e8751bfef41769",
    "74045a0839b19e08",
    "eca900c54627c006",
    "c2fa114fe0d88c13",
}


def read_jsonl(path: Path) -> Iterator[dict[str, Any]]:
    with path.open() as handle:
        for line in handle:
            if line.strip():
                yield json.loads(line)


def main() -> None:
    audit_dir = REPO_ROOT / "data" / "v1" / "audit_news_v1"
    blind_path = audit_dir / "news_association_blind_review.jsonl"
    key_path = audit_dir / "news_association_blind_key.jsonl"
    blind_rows = list(read_jsonl(blind_path))
    labels = {
        **{audit_id: "relevant" for audit_id in RELEVANT},
        **{audit_id: "not_relevant" for audit_id in NOT_RELEVANT},
        **{audit_id: "uncertain" for audit_id in UNCERTAIN},
    }
    blind_ids = {str(row["audit_id"]) for row in blind_rows}
    if blind_ids != set(labels):
        raise SystemExit(
            f"Review mapping mismatch: missing={sorted(blind_ids - set(labels))}, "
            f"extra={sorted(set(labels) - blind_ids)}"
        )
    completed = []
    for row in blind_rows:
        audit_id = str(row["audit_id"])
        label = labels[audit_id]
        if label == "relevant":
            rationale = (
                "The headline or summary contains a concrete status, outcome, candidacy, "
                "or odds update that could update the specified market."
            )
        elif label == "not_relevant":
            rationale = (
                "The available headline and summary do not provide information about the "
                "specified market outcome."
            )
        else:
            rationale = (
                "The headline is compatible with the topic, but the available text lacks "
                "enough detail to determine whether traffic status is actually reported."
            )
        completed.append(
            {
                **row,
                "review_label": label,
                "review_confidence": (
                    "low"
                    if label == "uncertain"
                    else "medium"
                    if audit_id in MEDIUM_CONFIDENCE
                    else "high"
                ),
                "review_rationale": rationale,
                "reviewer": "codex_news_01",
            }
        )
    completed_path = audit_dir / "news_association_blind_review_completed.jsonl"
    with completed_path.open("w") as handle:
        for row in completed:
            handle.write(json.dumps(row, sort_keys=True) + "\n")

    predictions = {
        str(row["audit_id"]): str(row["rule_prediction"]) for row in read_jsonl(key_path)
    }
    tp = fp = tn = fn = uncertain = 0
    for row in completed:
        label = row["review_label"]
        if label == "uncertain":
            uncertain += 1
            continue
        predicted_relevant = predictions[str(row["audit_id"])] == "matched"
        actual_relevant = label == "relevant"
        if predicted_relevant and actual_relevant:
            tp += 1
        elif predicted_relevant:
            fp += 1
        elif actual_relevant:
            fn += 1
        else:
            tn += 1
    precision = tp / (tp + fp) if tp + fp else None
    recall = tp / (tp + fn) if tp + fn else None
    f1 = (
        2 * precision * recall / (precision + recall)
        if precision is not None and recall is not None and precision + recall
        else None
    )
    report = {
        "status": "completed",
        "reviewer": "codex_news_01",
        "blind_during_labeling": True,
        "cases": len(completed),
        "uncertain_excluded": uncertain,
        "confusion_matrix": {"tp": tp, "fp": fp, "tn": tn, "fn": fn},
        "precision": precision,
        "recall_on_hard_retrieval_candidates": recall,
        "f1_on_hard_retrieval_candidates": f1,
        "note": (
            "The unmatched sample contains targeted search candidates, not random global "
            "news, so recall is a hard-negative diagnostic rather than population recall."
        ),
        "completed_review": str(completed_path.resolve().relative_to(REPO_ROOT)),
    }
    (audit_dir / "news_association_review_report.json").write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n"
    )
    print(json.dumps(report, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
