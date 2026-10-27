"""Summarize frozen relaxed-review adjudication as development diagnostics only."""
from collections import Counter
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import sys

from eventx.settings import REPO_ROOT

SOURCE = REPO_ROOT / "data/v6/context_development_review_20260927"
ADJ = REPO_ROOT / "data/v6/relaxed_adjudication_20260927"
OUT = REPO_ROOT / "data/v6/relaxed_adjudication_diagnostic_20260927"
INPUTS = [
    ADJ / "manifest.json", ADJ / "development_labels_102.jsonl",
    ADJ / "assistant_decisions.jsonl", SOURCE / "semantic_packet.jsonl",
    SOURCE / "selection_ledger.jsonl", SOURCE / "source_context.jsonl",
    REPO_ROOT / "eventx/tasks/summarize_v6_relaxed_adjudication_20260927.py",
]


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def rows(path):
    return [json.loads(line) for line in path.read_text().splitlines() if line.strip()]


def write(path, value):
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n")


def stage():
    OUT.mkdir(exist_ok=False)
    write(OUT / "receipt.json", {
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "written_before_diagnostic": True,
        "inputs": {str(p.relative_to(REPO_ROOT)): sha(p) for p in INPUTS},
        "scope": "frozen 102 opened-development relaxed labels only",
    })


def run():
    receipt = json.loads((OUT / "receipt.json").read_text())
    if receipt["inputs"] != {str(p.relative_to(REPO_ROOT)): sha(p) for p in INPUTS}:
        raise ValueError("input hash changed")
    if (OUT / "report.json").exists():
        raise FileExistsError("diagnostic already written")
    adj_manifest = json.loads((ADJ / "manifest.json").read_text())
    if any(sha(REPO_ROOT / p) != h for p, h in adj_manifest["inputs"].items()):
        raise ValueError("adjudication input hash changed")
    if any(sha(ADJ / p) != h for p, h in adj_manifest["outputs"].items()):
        raise ValueError("adjudication output hash changed")
    labels = rows(ADJ / "development_labels_102.jsonl")
    packet = {r["pair_id"]: r for r in rows(SOURCE / "semantic_packet.jsonl")}
    ledger = {r["pair_id"]: r for r in rows(SOURCE / "selection_ledger.jsonl")}
    context = {r["pair_id"]: r for r in rows(SOURCE / "source_context.jsonl")}
    if len(labels) != 102 or len(packet) != 102 or set(packet) != set(ledger) or set(packet) != set(context) or {r["pair_id"] for r in labels} != set(packet):
        raise ValueError("fixed packet scope mismatch")
    by_stratum = {}
    for stratum in sorted({r["stratum"] for r in ledger.values()}):
        subset = [r for r in labels if ledger[r["pair_id"]]["stratum"] == stratum]
        by_stratum[stratum] = {
            "pairs": len(subset),
            "articles": len({ledger[r["pair_id"]]["article_id"] for r in subset}),
            "contracts": len({ledger[r["pair_id"]]["contract_id"] for r in subset}),
            "applicability": dict(Counter(r["relaxed_applicability"] for r in subset)),
        }
    material = [r for r in labels if r["relaxed_applicability"] == "material_predicate_evidence"]
    context_only = [r for r in labels if r["relaxed_applicability"] == "shared_context_only"]
    boundary = [r for r in material if r["relaxed_relation"] == "shared_mechanism_context"]
    report = {
        "scope": "opened-development relaxed-rubric sensitivity; no independent audit or population estimate",
        "pairs": len(labels),
        "unique_articles": len({ledger[r["pair_id"]]["article_id"] for r in labels}),
        "unique_contracts": len({ledger[r["pair_id"]]["contract_id"] for r in labels}),
        "by_stratum": by_stratum,
        "material_predicate_evidence": {
            "pairs": len(material),
            "articles": len({ledger[r["pair_id"]]["article_id"] for r in material}),
            "by_article": dict(Counter(ledger[r["pair_id"]]["article_id"] for r in material)),
            "source_run_status": dict(Counter(context[r["pair_id"]]["article_source_run_status"] for r in material)),
            "shared_mechanism_relation_pairs": len(boundary),
            "shared_mechanism_relation_ids": [r["pair_id"] for r in boundary],
        },
        "shared_context_only": {
            "pairs": len(context_only),
            "direction_supports_no": sum(r["directional_evidence"] == "supports_no" for r in context_only),
            "direction_mixed_or_neutral": sum(r["directional_evidence"] == "mixed_or_neutral" for r in context_only),
        },
        "rubric_boundary_note": "Material predicate evidence plus shared mechanism context occurs in 16 pairs. The submitted relaxed rubric permits broad measured-variable relevance; these repeated article-level judgments need a prospective class mapping before they can serve as positive linker gold. Original agreed labels are preserved.",
        "inference_limits": [
            "54 typed union pairs are complete, but only 24 of 615 candidate abstentions and 24 of 8711 nonretrieved pairs were sampled.",
            "Pair counts reuse articles and contracts and are not independent event or power counts.",
            "Source context supplies no historical content certificate or training-admissible pair; failed source runs cannot establish zero-news windows.",
            "No class mapping, threshold, linker freeze, new audit, or forecast fit follows from this diagnostic.",
        ],
        "predictive_admissions": 0,
    }
    write(OUT / "report.json", report)
    write(OUT / "manifest.json", {"inputs": receipt["inputs"], "outputs": {"report.json": sha(OUT / "report.json")}})
    print(json.dumps(report, indent=2, sort_keys=True))


if __name__ == "__main__":
    {"stage": stage, "run": run}[sys.argv[1]]()
