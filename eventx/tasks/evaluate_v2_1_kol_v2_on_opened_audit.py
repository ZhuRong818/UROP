"""Development-only evaluation of KOL-v2 on the opened KOL-v1 audit rows."""

from __future__ import annotations

from collections import Counter
import hashlib
import json
from pathlib import Path
from typing import Any

from eventx.features.v2_1_kol_association_v2 import LEXICAL_SPEC, RULE_VERSION, prediction
from eventx.settings import REPO_ROOT


ROOT = REPO_ROOT / "data" / "v2_1" / "association" / "v1_audit"
BLIND = ROOT / "association_blind_review.jsonl"
KEY = ROOT / "association_blind_key.jsonl"
REVIEW = REPO_ROOT / "eventx" / "release" / "v2_1" / "eventx_v2_1_blind_review_completed.jsonl"
RULE_SOURCE = REPO_ROOT / "eventx" / "features" / "v2_1_kol_association_v2.py"
OUTPUT = ROOT / "kol_v2_opened_development_predictions.jsonl"
REPORT = ROOT / "kol_v2_opened_development_report.json"


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    with path.open() as handle:
        return [json.loads(line) for line in handle if line.strip()]


def indexed(path: Path) -> dict[str, dict[str, Any]]:
    rows = read_jsonl(path)
    result = {str(row["audit_id"]): row for row in rows}
    if len(result) != len(rows):
        raise ValueError(f"duplicate audit IDs in {path}")
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
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(payload)
    temporary.replace(path)


def metrics(rows: list[dict[str, Any]], prediction_field: str) -> dict[str, Any]:
    counts = Counter((row[prediction_field], row["review_label"]) for row in rows)
    tp = counts[("matched", "relevant")]
    fp = counts[("matched", "not_relevant")]
    fn = counts[("hard_unmatched", "relevant")]
    tn = counts[("hard_unmatched", "not_relevant")]
    precision = tp / (tp + fp) if tp + fp else None
    recall = tp / (tp + fn) if tp + fn else None
    return {
        "confusion": {"false_negative": fn, "false_positive": fp, "true_negative": tn, "true_positive": tp},
        "f1": 2 * precision * recall / (precision + recall) if precision and recall else None,
        "hard_candidate_recall": recall,
        "precision": precision,
    }


def main() -> None:
    blind = indexed(BLIND)
    key = indexed(KEY)
    review = indexed(REVIEW)
    rows = []
    for audit_id in sorted(key):
        keyed = key[audit_id]
        if keyed["source"] != "kol":
            continue
        v2_prediction, reasons, terms, evidence = prediction(
            str(keyed["market_id"]), str(blind[audit_id]["document_text"])
        )
        rows.append(
            {
                "audit_id": audit_id,
                "market_id": keyed["market_id"],
                "review_label": review[audit_id]["review_label"],
                "text": blind[audit_id]["document_text"],
                "v1_prediction": keyed["rule_prediction"],
                "v2_evidence": evidence,
                "v2_match_reasons": reasons,
                "v2_match_terms": terms,
                "v2_prediction": v2_prediction,
            }
        )
    if len(rows) != 150:
        raise SystemExit(f"expected 150 opened KOL rows, found {len(rows)}")
    atomic_write(OUTPUT, "".join(json.dumps(row, sort_keys=True) + "\n" for row in rows))
    changes = Counter(
        f"{row['v1_prediction']}->{row['v2_prediction']}:{row['review_label']}"
        for row in rows
        if row["v1_prediction"] != row["v2_prediction"]
    )
    report = {
        "candidate_rule": RULE_VERSION,
        "development_only": True,
        "input_hashes": {relative(path): sha256_file(path) for path in (BLIND, KEY, REVIEW)},
        "opened_rows": len(rows),
        "prediction_changes": dict(sorted(changes.items())),
        "source_hashes": {
            relative(RULE_SOURCE): sha256_file(RULE_SOURCE),
            relative(LEXICAL_SPEC): sha256_file(LEXICAL_SPEC),
        },
        "status": "development_diagnostic_not_validation",
        "v1": metrics(rows, "v1_prediction"),
        "v2": metrics(rows, "v2_prediction"),
    }
    atomic_write(REPORT, json.dumps(report, indent=2, sort_keys=True) + "\n")
    print(json.dumps(report, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
